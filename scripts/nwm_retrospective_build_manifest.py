#!/usr/bin/env python3
"""Build metadata and local-inventory manifests for NWM retrospective extraction.

This is metadata-first and does not download bulk model data.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class VersionSource:
    version: str
    bucket: str
    region: str
    format_hint: str
    access_path: str
    expected_start: str
    expected_end: str
    extraction_mode: str


VERSION_SOURCES: List[VersionSource] = [
    VersionSource(
        version="3.0",
        bucket="noaa-nwm-retrospective-3-0-pds",
        region="us-east-1",
        format_hint="zarr+netcdf",
        access_path="s3://noaa-nwm-retrospective-3-0-pds/CONUS/zarr/chrtout.zarr",
        expected_start="1979-02-01",
        expected_end="2023-01-31",
        extraction_mode="zarr",
    ),
    VersionSource(
        version="2.1",
        bucket="noaa-nwm-retrospective-2-1-zarr-pds",
        region="us-east-1",
        format_hint="zarr",
        access_path="s3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr",
        expected_start="1979-02-01",
        expected_end="2020-12-31",
        extraction_mode="zarr",
    ),
    VersionSource(
        version="2.0",
        bucket="noaa-nwm-retro-v2-zarr-pds",
        region="us-west-2",
        format_hint="zarr",
        access_path="s3://noaa-nwm-retro-v2-zarr-pds",
        expected_start="1993-01-01",
        expected_end="2018-12-31",
        extraction_mode="zarr",
    ),
    VersionSource(
        version="1.2",
        bucket="nwm-archive",
        region="us-east-1",
        format_hint="netcdf-comp",
        access_path="s3://nwm-archive/YYYY/YYYYMMDDHH00.CHRTOUT_DOMAIN1.comp",
        expected_start="1993-01-01",
        expected_end="2017-12-31",
        extraction_mode="netcdf_comp",
    ),
]


LOCAL_KNOWN = {
    "3.0": Path("11160500_nws_retro.csv"),
    "2.1": Path("11160500_nws_retro_old.csv"),
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_cmd(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def parse_local_known_overrides(values: List[str]) -> Dict[str, Path]:
    overrides: Dict[str, Path] = {}
    for raw in values:
        if "=" not in raw:
            raise SystemExit(
                f"Invalid --local-known value {raw!r}. Expected VERSION=/absolute/or/relative/path.csv"
            )
        version, path_text = raw.split("=", 1)
        version = version.strip()
        path_text = path_text.strip()
        if not version or not path_text:
            raise SystemExit(
                f"Invalid --local-known value {raw!r}. Expected VERSION=/absolute/or/relative/path.csv"
            )
        overrides[version] = Path(path_text)
    return overrides


def probe_bucket(bucket: str) -> Dict[str, object]:
    cmd = ["aws", "s3", "ls", "--no-sign-request", f"s3://{bucket}/"]
    p = run_cmd(cmd)
    return {
        "cmd": " ".join(cmd),
        "returncode": p.returncode,
        "stdout_head": "\n".join((p.stdout or "").splitlines()[:30]),
        "stderr_head": "\n".join((p.stderr or "").splitlines()[:20]),
    }


def daily_inventory_for_csv(path: Path) -> Dict[str, object]:
    out: Dict[str, object] = {
        "exists": path.exists(),
        "rows_raw": 0,
        "start_raw": "",
        "end_raw": "",
        "daily_rows": 0,
        "daily_expected": 0,
        "daily_missing_n": 0,
        "daily_duplicate_n": 0,
        "nan_streamflow_n": 0,
        "feature_id": "",
        "latitude": "",
        "longitude": "",
    }
    if not path.exists():
        return out

    df = pd.read_csv(path)
    if "Date" not in df.columns or "streamflow" not in df.columns:
        out["error"] = "missing_Date_or_streamflow"
        return out

    dt = pd.to_datetime(df["Date"], errors="coerce")
    vals = pd.to_numeric(df["streamflow"], errors="coerce")
    work = pd.DataFrame({"datetime": dt, "streamflow": vals}).dropna(subset=["datetime"])
    work = work.sort_values("datetime")

    if work.empty:
        return out

    out["rows_raw"] = int(len(work))
    out["start_raw"] = str(work["datetime"].iloc[0])
    out["end_raw"] = str(work["datetime"].iloc[-1])
    out["nan_streamflow_n"] = int(work["streamflow"].isna().sum())

    day = work.assign(date=work["datetime"].dt.floor("D")).groupby("date", as_index=False)["streamflow"].mean()
    idx = pd.date_range(day["date"].min(), day["date"].max(), freq="D")
    missing = idx.difference(pd.DatetimeIndex(day["date"]))

    out["daily_rows"] = int(len(day))
    out["daily_expected"] = int(len(idx))
    out["daily_missing_n"] = int(len(missing))
    out["daily_duplicate_n"] = int(day.duplicated(subset=["date"]).sum())

    for c in ["feature_id", "latitude", "longitude"]:
        if c in df.columns:
            u = df[c].dropna().unique()
            if len(u) > 0:
                out[c] = str(u[0])

    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build NWM retrospective source and local inventory manifests.")
    p.add_argument(
        "--run-root",
        default="repro/nwm_retrospective_runs",
        help="Root directory for run artifacts.",
    )
    p.add_argument(
        "--run-id",
        default="",
        help="Optional fixed run_id. If omitted, generated from UTC timestamp.",
    )
    p.add_argument(
        "--local-known",
        action="append",
        default=[],
        help=(
            "Optional override/addition for known local artifacts in the form "
            "VERSION=/path/to/file.csv. May be provided multiple times."
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id or f"nwm_retrospective_campaign_{now_utc()}"
    run_dir = Path(args.run_root) / run_id
    manifests_dir = run_dir / "manifests"
    logs_dir = run_dir / "logs"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    source_manifest_path = manifests_dir / "version_source_manifest.csv"
    local_inventory_path = manifests_dir / "local_inventory.csv"
    probe_json_path = logs_dir / "bucket_probes.json"
    summary_json_path = manifests_dir / "manifest_summary.json"

    # 1) Version source manifest.
    with source_manifest_path.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "version",
                "bucket",
                "region",
                "format_hint",
                "access_path",
                "expected_start",
                "expected_end",
                "extraction_mode",
            ],
        )
        w.writeheader()
        for s in VERSION_SOURCES:
            w.writerow(s.__dict__)

    # 2) Bucket probes.
    probes = {s.version: probe_bucket(s.bucket) for s in VERSION_SOURCES}
    probe_json_path.write_text(json.dumps(probes, indent=2))

    # 3) Local inventory.
    local_known = dict(LOCAL_KNOWN)
    local_known.update(parse_local_known_overrides(list(args.local_known)))

    rows = []
    for s in VERSION_SOURCES:
        p = local_known.get(s.version)
        row: Dict[str, object] = {
            "version": s.version,
            "local_path": str(p) if p is not None else "",
            "exists": False,
            "rows_raw": 0,
            "start_raw": "",
            "end_raw": "",
            "daily_rows": 0,
            "daily_expected": 0,
            "daily_missing_n": 0,
            "daily_duplicate_n": 0,
            "nan_streamflow_n": 0,
            "feature_id": "",
            "latitude": "",
            "longitude": "",
        }
        if p is not None:
            inv = daily_inventory_for_csv(p)
            row.update(inv)
        rows.append(row)
    pd.DataFrame(rows).to_csv(local_inventory_path, index=False)

    summary = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest_csv": str(source_manifest_path),
        "local_inventory_csv": str(local_inventory_path),
        "bucket_probes_json": str(probe_json_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2))

    print(f"[OK] run_id={run_id}")
    print(f"[OK] wrote {source_manifest_path}")
    print(f"[OK] wrote {local_inventory_path}")
    print(f"[OK] wrote {probe_json_path}")
    print(f"[OK] wrote {summary_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
