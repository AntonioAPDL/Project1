#!/usr/bin/env python3
"""Build metadata-only GEFS + NWM forecast manifests for target dates.

This script does not download bulk forecast data. It lists public cloud objects,
builds exact dry-run retrieval manifests, and writes summary metadata under a
run-scoped repro directory.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


try:
    import yaml
except Exception as exc:  # pragma: no cover
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


DEFAULT_TARGET_DATES = [
    "2021-01-23",
    "2021-11-12",
    "2021-12-21",
    "2022-05-11",
    "2022-12-25",
]
DEFAULT_RUN_ROOT = "repro/gefs_nwm_forecast_runs"
DEFAULT_SITE_CONFIG = "config/forecats_pipeline.template.yaml"
GEFS_BUCKET = "noaa-gefs-pds"
GEFS_HTTP_ROOT = "https://noaa-gefs-pds.s3.amazonaws.com"
NWM_BUCKET = "national-water-model"
NWM_HTTP_ROOT = "https://storage.googleapis.com/national-water-model"

GEFS_FILE_RE = re.compile(
    r"^(?P<member_code>gec00|gep\d{2})\.t(?P<cycle>\d{2})z\.(?P<family_token>pgrb2[ab])\.0p50\.f(?P<lead>\d{3})$"
)
S3_PREFIX_RE = re.compile(r"^\s*PRE\s+([^/]+)/\s*$")
NWM_MEDIUM_PREFIX_RE = re.compile(r"medium_range_mem(?P<member>\d+)/$")
NWM_LONG_PREFIX_RE = re.compile(r"long_range_mem(?P<member>\d+)/$")
NWM_SHORT_LAND_RE = re.compile(
    r"^nwm\.(?P<date>\d{8})/short_range/nwm\.t(?P<cycle>\d{2})z\.short_range\.land\.f(?P<lead>\d{3})\.conus\.nc$"
)
NWM_SHORT_FORCING_RE = re.compile(
    r"^nwm\.(?P<date>\d{8})/forcing_short_range/nwm\.t(?P<cycle>\d{2})z\.short_range\.forcing\.f(?P<lead>\d{3})\.conus\.nc$"
)
NWM_MEDIUM_LAND_RE = re.compile(
    r"^nwm\.(?P<date>\d{8})/medium_range_mem(?P<member>\d+)/nwm\.t(?P<cycle>\d{2})z\.medium_range\.land_(?P=member)\.f(?P<lead>\d{3})\.conus\.nc$"
)
NWM_MEDIUM_FORCING_RE = re.compile(
    r"^nwm\.(?P<date>\d{8})/forcing_medium_range/nwm\.t(?P<cycle>\d{2})z\.medium_range\.forcing\.f(?P<lead>\d{3})\.conus\.nc$"
)
NWM_LONG_LAND_RE = re.compile(
    r"^nwm\.(?P<date>\d{8})/long_range_mem(?P<member>\d+)/nwm\.t(?P<cycle>\d{2})z\.long_range\.land_(?P=member)\.f(?P<lead>\d{3})\.conus\.nc$"
)

GEFS_FAMILY_SPECS: Dict[str, List[Dict[str, Any]]] = {
    "pgrb2ap5": [
        {
            "short_name": "SOILW",
            "level_descriptor": "0-0.1 m below ground",
            "depth_top_m": 0.0,
            "depth_bottom_m": 0.1,
            "layer_index": None,
            "selection_role": "soil",
            "lead_min_hours": 0,
        },
        {
            "short_name": "APCP",
            "level_descriptor": "surface",
            "depth_top_m": None,
            "depth_bottom_m": None,
            "layer_index": None,
            "selection_role": "precip",
            "lead_min_hours": 3,
        },
    ],
    "pgrb2bp5": [
        {
            "short_name": "SOILW",
            "level_descriptor": "0.1-0.4 m below ground",
            "depth_top_m": 0.1,
            "depth_bottom_m": 0.4,
            "layer_index": None,
            "selection_role": "soil",
            "lead_min_hours": 0,
        },
        {
            "short_name": "SOILW",
            "level_descriptor": "0.4-1 m below ground",
            "depth_top_m": 0.4,
            "depth_bottom_m": 1.0,
            "layer_index": None,
            "selection_role": "soil",
            "lead_min_hours": 0,
        },
        {
            "short_name": "SOILW",
            "level_descriptor": "1-2 m below ground",
            "depth_top_m": 1.0,
            "depth_bottom_m": 2.0,
            "layer_index": None,
            "selection_role": "soil",
            "lead_min_hours": 0,
        },
    ],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build metadata-only GEFS + NWM forecast manifests.")
    p.add_argument(
        "--run-root",
        default=DEFAULT_RUN_ROOT,
        help="Root directory for run-scoped manifest outputs.",
    )
    p.add_argument(
        "--run-id",
        default="",
        help="Optional fixed run_id. If omitted, generated from UTC timestamp.",
    )
    p.add_argument(
        "--dates",
        default=",".join(DEFAULT_TARGET_DATES),
        help="Comma-separated initialization dates (YYYY-MM-DD).",
    )
    p.add_argument(
        "--site-config",
        default=DEFAULT_SITE_CONFIG,
        help="YAML config that provides canonical site metadata.",
    )
    p.add_argument(
        "--gefs-cycle",
        default="00",
        help="GEFS cycle to manifest (`00`, `06`, `12`, `18`, or `all`).",
    )
    p.add_argument(
        "--nwm-cycle",
        default="00",
        help="NWM cycle to manifest (`00`, `06`, `12`, `18`, or `all`).",
    )
    return p.parse_args()


def now_utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_target_dates(text: str) -> List[str]:
    dates = [x.strip() for x in text.split(",") if x.strip()]
    if not dates:
        raise SystemExit("No target dates provided.")
    normalized = []
    for value in dates:
        normalized.append(datetime.strptime(value, "%Y-%m-%d").date().isoformat())
    return normalized


def load_site(path: Path) -> Dict[str, Any]:
    if yaml is None:  # pragma: no cover
        raise RuntimeError(f"PyYAML import failed: {YAML_IMPORT_ERROR}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    site = cfg.get("site") or {}
    return {
        "usgs_site": site.get("usgs_site", "11160500"),
        "lat": float(site.get("lat", 37.0443931)),
        "lon": float(site.get("lon", -122.072464)),
    }


def run_cmd(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def list_s3_prefixes(uri: str) -> List[str]:
    cmd = ["aws", "s3", "ls", "--no-sign-request", uri]
    proc = run_cmd(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"S3 prefix listing failed for {uri}: {proc.stderr.strip()}")
    out: List[str] = []
    for line in (proc.stdout or "").splitlines():
        m = S3_PREFIX_RE.match(line)
        if m:
            out.append(m.group(1))
    return out


def list_s3_files(uri: str) -> List[str]:
    cmd = ["aws", "s3", "ls", "--no-sign-request", uri]
    proc = run_cmd(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"S3 file listing failed for {uri}: {proc.stderr.strip()}")
    files: List[str] = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "PRE":
            continue
        files.append(parts[-1])
    return files


def gcs_api_call(bucket: str, params: Dict[str, str]) -> Dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o?{query}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.load(resp)


def list_gcs_prefixes(bucket: str, prefix: str) -> List[str]:
    data = gcs_api_call(bucket, {"prefix": prefix, "delimiter": "/"})
    return sorted(data.get("prefixes") or [])


def list_gcs_objects(bucket: str, prefix: str) -> List[str]:
    names: List[str] = []
    page_token = ""
    while True:
        params = {"prefix": prefix, "maxResults": "1000"}
        if page_token:
            params["pageToken"] = page_token
        data = gcs_api_call(bucket, params)
        for item in data.get("items") or []:
            names.append(item["name"])
        page_token = data.get("nextPageToken", "")
        if not page_token:
            break
    return names


def cycle_matches(found_cycle: str, wanted_cycle: str) -> bool:
    return wanted_cycle == "all" or found_cycle == wanted_cycle


def parse_member_code(member_code: str) -> Dict[str, Any]:
    if member_code == "gec00":
        return {"member_kind": "control", "member_number": 0}
    return {"member_kind": "perturbed", "member_number": int(member_code[-2:])}


def append_gefs_rows(
    rows: List[Dict[str, Any]],
    init_date: str,
    cycle_hour: int,
    family_name: str,
    filename: str,
) -> None:
    match = GEFS_FILE_RE.match(filename)
    if not match:
        return
    lead_hours = int(match.group("lead"))
    member_code = match.group("member_code")
    member_meta = parse_member_code(member_code)
    ymd = init_date.replace("-", "")
    key = f"gefs.{ymd}/{cycle_hour:02d}/atmos/{family_name}/{filename}"
    url = f"{GEFS_HTTP_ROOT}/{key}"

    for spec in GEFS_FAMILY_SPECS[family_name]:
        if lead_hours < int(spec["lead_min_hours"]):
            continue
        rows.append(
            {
                "source": "GEFS",
                "init_date": init_date,
                "cycle_hour": cycle_hour,
                "member_code": member_code,
                "member_number": member_meta["member_number"],
                "member_kind": member_meta["member_kind"],
                "product_family": family_name,
                "file_token": match.group("family_token"),
                "lead_hours": lead_hours,
                "lead_tag": f"f{lead_hours:03d}",
                "short_name": spec["short_name"],
                "level_descriptor": spec["level_descriptor"],
                "depth_top_m": spec["depth_top_m"],
                "depth_bottom_m": spec["depth_bottom_m"],
                "layer_index": spec["layer_index"],
                "selection_role": spec["selection_role"],
                "file_name": filename,
                "object_key": key,
                "object_url": url,
                "storage_backend": "aws_s3",
            }
        )


def build_gefs_manifest(target_dates: Iterable[str], wanted_cycle: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    families = ["pgrb2ap5", "pgrb2bp5"]

    for init_date in target_dates:
        ymd = init_date.replace("-", "")
        cycle_values = [wanted_cycle]
        if wanted_cycle == "all":
            cycle_prefixes = list_s3_prefixes(f"s3://{GEFS_BUCKET}/gefs.{ymd}/")
            cycle_values = sorted(x for x in cycle_prefixes if x.isdigit())
        for cycle in cycle_values:
            cycle_int = int(cycle)
            for family_name in families:
                prefix = f"s3://{GEFS_BUCKET}/gefs.{ymd}/{cycle}/atmos/{family_name}/"
                for filename in list_s3_files(prefix):
                    if filename.endswith(".idx"):
                        continue
                    append_gefs_rows(rows, init_date=init_date, cycle_hour=cycle_int, family_name=family_name, filename=filename)

    return rows


def add_nwm_land_rows(
    rows: List[Dict[str, Any]],
    *,
    init_date: str,
    cycle_hour: int,
    member_code: str,
    member_number: int,
    member_kind: str,
    product_family: str,
    key: str,
    file_name: str,
    lead_hours: int,
) -> None:
    url = f"{NWM_HTTP_ROOT}/{key}"
    rows.append(
        {
            "source": "NWM",
            "init_date": init_date,
            "cycle_hour": cycle_hour,
            "member_code": member_code,
            "member_number": member_number,
            "member_kind": member_kind,
            "product_family": product_family,
            "file_token": Path(file_name).stem,
            "lead_hours": lead_hours,
            "lead_tag": f"f{lead_hours:03d}",
            "short_name": "SOILSAT_TOP",
            "level_descriptor": "top-soil saturation fraction",
            "depth_top_m": None,
            "depth_bottom_m": None,
            "layer_index": None,
            "selection_role": "soil_cross_range",
            "file_name": file_name,
            "object_key": key,
            "object_url": url,
            "storage_backend": "gcs",
        }
    )
    if product_family == "medium_range_land":
        for layer_index in range(4):
            rows.append(
                {
                    "source": "NWM",
                    "init_date": init_date,
                    "cycle_hour": cycle_hour,
                    "member_code": member_code,
                    "member_number": member_number,
                    "member_kind": member_kind,
                    "product_family": product_family,
                    "file_token": Path(file_name).stem,
                    "lead_hours": lead_hours,
                    "lead_tag": f"f{lead_hours:03d}",
                    "short_name": "SOIL_M",
                    "level_descriptor": f"soil_layers_stag={layer_index}",
                    "depth_top_m": None,
                    "depth_bottom_m": None,
                    "layer_index": layer_index,
                    "selection_role": "soil_medium_only",
                    "file_name": file_name,
                    "object_key": key,
                    "object_url": url,
                    "storage_backend": "gcs",
                }
            )


def add_nwm_precip_rows(
    rows: List[Dict[str, Any]],
    *,
    init_date: str,
    cycle_hour: int,
    product_family: str,
    key: str,
    file_name: str,
    lead_hours: int,
) -> None:
    rows.append(
        {
            "source": "NWM",
            "init_date": init_date,
            "cycle_hour": cycle_hour,
            "member_code": "det",
            "member_number": 0,
            "member_kind": "deterministic",
            "product_family": product_family,
            "file_token": Path(file_name).stem,
            "lead_hours": lead_hours,
            "lead_tag": f"f{lead_hours:03d}",
            "short_name": "RAINRATE",
            "level_descriptor": "surface forcing",
            "depth_top_m": None,
            "depth_bottom_m": None,
            "layer_index": None,
            "selection_role": "precip",
            "file_name": file_name,
            "object_key": key,
            "object_url": f"{NWM_HTTP_ROOT}/{key}",
            "storage_backend": "gcs",
        }
    )


def build_nwm_manifest(target_dates: Iterable[str], wanted_cycle: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for init_date in target_dates:
        ymd = init_date.replace("-", "")
        date_prefix = f"nwm.{ymd}/"
        prefixes = list_gcs_prefixes(NWM_BUCKET, date_prefix)

        short_names = list_gcs_objects(NWM_BUCKET, f"{date_prefix}short_range/")
        for key in short_names:
            file_name = key.split("/")[-1]
            m = NWM_SHORT_LAND_RE.match(key)
            if not m or not cycle_matches(m.group("cycle"), wanted_cycle):
                continue
            lead_hours = int(m.group("lead"))
            add_nwm_land_rows(
                rows,
                init_date=init_date,
                cycle_hour=int(m.group("cycle")),
                member_code="det",
                member_number=0,
                member_kind="deterministic",
                product_family="short_range_land",
                key=key,
                file_name=file_name,
                lead_hours=lead_hours,
            )

        short_forcing_names = list_gcs_objects(NWM_BUCKET, f"{date_prefix}forcing_short_range/")
        for key in short_forcing_names:
            file_name = key.split("/")[-1]
            m = NWM_SHORT_FORCING_RE.match(key)
            if not m or not cycle_matches(m.group("cycle"), wanted_cycle):
                continue
            add_nwm_precip_rows(
                rows,
                init_date=init_date,
                cycle_hour=int(m.group("cycle")),
                product_family="short_range_forcing",
                key=key,
                file_name=file_name,
                lead_hours=int(m.group("lead")),
            )

        medium_members = sorted(
            int(m.group("member"))
            for prefix in prefixes
            for m in [NWM_MEDIUM_PREFIX_RE.search(prefix)]
            if m is not None
        )
        for member in medium_members:
            names = list_gcs_objects(NWM_BUCKET, f"{date_prefix}medium_range_mem{member}/")
            for key in names:
                file_name = key.split("/")[-1]
                m = NWM_MEDIUM_LAND_RE.match(key)
                if not m or not cycle_matches(m.group("cycle"), wanted_cycle):
                    continue
                add_nwm_land_rows(
                    rows,
                    init_date=init_date,
                    cycle_hour=int(m.group("cycle")),
                    member_code=f"mem{member}",
                    member_number=member,
                    member_kind="ensemble_member",
                    product_family="medium_range_land",
                    key=key,
                    file_name=file_name,
                    lead_hours=int(m.group("lead")),
                )

        medium_forcing_names = list_gcs_objects(NWM_BUCKET, f"{date_prefix}forcing_medium_range/")
        for key in medium_forcing_names:
            file_name = key.split("/")[-1]
            m = NWM_MEDIUM_FORCING_RE.match(key)
            if not m or not cycle_matches(m.group("cycle"), wanted_cycle):
                continue
            add_nwm_precip_rows(
                rows,
                init_date=init_date,
                cycle_hour=int(m.group("cycle")),
                product_family="medium_range_forcing",
                key=key,
                file_name=file_name,
                lead_hours=int(m.group("lead")),
            )

        long_members = sorted(
            int(m.group("member"))
            for prefix in prefixes
            for m in [NWM_LONG_PREFIX_RE.search(prefix)]
            if m is not None
        )
        for member in long_members:
            names = list_gcs_objects(NWM_BUCKET, f"{date_prefix}long_range_mem{member}/")
            for key in names:
                file_name = key.split("/")[-1]
                m = NWM_LONG_LAND_RE.match(key)
                if not m or not cycle_matches(m.group("cycle"), wanted_cycle):
                    continue
                add_nwm_land_rows(
                    rows,
                    init_date=init_date,
                    cycle_hour=int(m.group("cycle")),
                    member_code=f"mem{member}",
                    member_number=member,
                    member_kind="ensemble_member",
                    product_family="long_range_land",
                    key=key,
                    file_name=file_name,
                    lead_hours=int(m.group("lead")),
                )

    return rows


def write_manifest(rows: List[Dict[str, Any]], path: Path) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        df.to_csv(path, index=False)
        return df
    sort_cols = [
        "init_date",
        "cycle_hour",
        "product_family",
        "member_number",
        "lead_hours",
        "short_name",
        "layer_index",
        "level_descriptor",
    ]
    df = df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
    df.to_csv(path, index=False)
    return df


def summarize(df: pd.DataFrame, keys: List[str]) -> Dict[str, int]:
    if df.empty:
        return {}
    counts = Counter()
    for row in df[keys].itertuples(index=False, name=None):
        label = "|".join(str(x) for x in row)
        counts[label] += 1
    return dict(sorted(counts.items()))


def main() -> int:
    args = parse_args()
    target_dates = parse_target_dates(args.dates)
    run_id = args.run_id or f"gefs_nwm_forecast_manifest_{now_utc_tag()}"
    run_dir = Path(args.run_root) / run_id
    manifests_dir = run_dir / "manifests"
    logs_dir = run_dir / "logs"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    site = load_site(Path(args.site_config))

    gefs_rows = build_gefs_manifest(target_dates, wanted_cycle=args.gefs_cycle)
    nwm_rows = build_nwm_manifest(target_dates, wanted_cycle=args.nwm_cycle)

    gefs_manifest_path = manifests_dir / "gefs_manifest.csv"
    nwm_manifest_path = manifests_dir / "nwm_manifest.csv"
    summary_path = manifests_dir / "manifest_summary.json"

    gefs_df = write_manifest(gefs_rows, gefs_manifest_path)
    nwm_df = write_manifest(nwm_rows, nwm_manifest_path)

    summary = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "target_dates": target_dates,
        "site": site,
        "preferences": {
            "gefs_cycle_scope": args.gefs_cycle,
            "gefs_member_scope": "control + all perturbed members",
            "gefs_soil_scope": "all SOILW layers from pgrb2a + pgrb2b",
            "nwm_cycle_scope": args.nwm_cycle,
            "nwm_soil_cross_range": "SOILSAT_TOP",
            "nwm_soil_medium_only": "SOIL_M layers 0..3",
            "nwm_precip": "RAINRATE",
        },
        "outputs": {
            "gefs_manifest_csv": str(gefs_manifest_path),
            "nwm_manifest_csv": str(nwm_manifest_path),
        },
        "counts": {
            "gefs_rows": int(len(gefs_df)),
            "nwm_rows": int(len(nwm_df)),
            "gefs_files": int(gefs_df["object_key"].nunique()) if not gefs_df.empty else 0,
            "nwm_files": int(nwm_df["object_key"].nunique()) if not nwm_df.empty else 0,
            "gefs_members_by_date": summarize(
                gefs_df.drop_duplicates(["init_date", "member_code"]) if not gefs_df.empty else gefs_df,
                ["init_date", "member_code"],
            ),
            "nwm_product_rows": summarize(nwm_df, ["product_family", "short_name"]) if not nwm_df.empty else {},
            "nwm_members_by_product": summarize(
                nwm_df.drop_duplicates(["product_family", "member_code"]) if not nwm_df.empty else nwm_df,
                ["product_family", "member_code"],
            ),
        },
        "notes": [
            "Manifest is metadata-only and does not download forecast files.",
            "GEFS APCP rows start at lead hour 3 because sampled f000 inventory exposed SOILW but not APCP.",
            "NWM manifest includes SOILSAT_TOP across short/medium/long land products.",
            "NWM manifest includes SOIL_M layers 0..3 for medium-range land only.",
            "NWM precipitation rows come from forcing_short_range and forcing_medium_range only.",
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2))

    print(f"[OK] run_id={run_id}")
    print(f"[OK] wrote {gefs_manifest_path} rows={len(gefs_df)} files={summary['counts']['gefs_files']}")
    print(f"[OK] wrote {nwm_manifest_path} rows={len(nwm_df)} files={summary['counts']['nwm_files']}")
    print(f"[OK] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
