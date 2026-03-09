#!/usr/bin/env python3
"""Build a non-destructive GEFS + NWM forecast handoff cache from extracted CSVs.

The output mirrors the repo's forecast-cache pattern:
  <handoff_root>/
    site=<usgs_site>/
      run_id=<run_id>/
        forecast_cache/
          gefs/issue_date=YYYY-MM-DD/variable=<...>/gefs_members.csv
          nwm/init_date=YYYY-MM-DD/product_family=<...>/variable=<...>/nwm_members.csv
        catalogs/
          gefs_catalog.csv
          nwm_catalog.csv
        handoff_meta.json

Each members CSV preserves native lead-time resolution and includes:
  init_date, cycle_hour, lead_hours, target_time_utc, target_date, member_*
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd


DEFAULT_RUN_DIR = "repro/gefs_nwm_forecast_runs/gefs_nwm_forecast_manifest_20260307T023425Z"
DEFAULT_SITE_CONFIG = "config/forecats_pipeline.template.yaml"
DEFAULT_HEALTH_JSON = "health_checks/forecast_extract_health.json"
DEFAULT_OUT_SUBDIR = "handoff_forecasts"


try:
    import yaml
except Exception as exc:  # pragma: no cover
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Consolidate finished GEFS + NWM forecast extracts into handoff caches.")
    p.add_argument("--manifest-run-dir", default=DEFAULT_RUN_DIR)
    p.add_argument("--site-config", default=DEFAULT_SITE_CONFIG)
    p.add_argument("--health-json", default=DEFAULT_HEALTH_JSON)
    p.add_argument("--gefs-extract-subdir", default="extract_gefs_full")
    p.add_argument("--nwm-extract-subdir", default="extract_full")
    p.add_argument("--out-subdir", default=DEFAULT_OUT_SUBDIR)
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_site(path: Path) -> Dict[str, Any]:
    if yaml is None:  # pragma: no cover
        raise RuntimeError(f"PyYAML import failed: {YAML_IMPORT_ERROR}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    site = cfg.get("site") or {}
    return {
        "usgs_site": str(site.get("usgs_site", "11160500")),
        "lat": float(site.get("lat", 37.0443931)),
        "lon": float(site.get("lon", -122.072464)),
    }


def load_health(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("all_health_pass", False):
        raise SystemExit(f"Health check is not clean: {path}")
    return payload


def slugify(text: str) -> str:
    text = str(text).strip()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "na"


def ensure_fresh_dir(path: Path, overwrite: bool) -> None:
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise SystemExit(f"Output directory already exists and is non-empty: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def member_sort_key(col: str) -> Tuple[int, int, str]:
    if col == "member_det":
        return (0, -1, col)
    m = re.fullmatch(r"member_(\d+)", col)
    if m:
        return (1, int(m.group(1)), col)
    m = re.fullmatch(r"member_mem(\d+)", col)
    if m:
        return (2, int(m.group(1)), col)
    return (9, math.inf, col)


def add_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["init_datetime_utc"] = pd.to_datetime(out["init_date"]) + pd.to_timedelta(out["cycle_hour"].astype(int), unit="h")
    out["target_time_utc"] = out["init_datetime_utc"] + pd.to_timedelta(out["lead_hours"].astype(int), unit="h")
    out["target_time_utc"] = pd.to_datetime(out["target_time_utc"], utc=True)
    out["target_date"] = out["target_time_utc"].dt.strftime("%Y-%m-%d")
    out["target_time_utc"] = out["target_time_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return out


def map_gefs_member(member_code: str) -> str:
    if member_code == "gec00":
        return "member_00"
    return f"member_{int(str(member_code)[-2:]):02d}"


def map_nwm_member(member_code: str) -> str:
    code = str(member_code)
    if code == "det":
        return "member_det"
    return f"member_{slugify(code)}"


def unique_steps(leads: Sequence[int]) -> str:
    vals = sorted({int(x) for x in leads})
    if len(vals) < 2:
        return ""
    diffs = sorted({b - a for a, b in zip(vals[:-1], vals[1:])})
    return ",".join(str(x) for x in diffs)


def build_wide_matrix(
    df: pd.DataFrame,
    row_cols: List[str],
    member_col: str,
) -> pd.DataFrame:
    dupes = df.duplicated(subset=row_cols + [member_col], keep=False)
    if bool(dupes.any()):
        raise RuntimeError(f"Duplicate member rows found for key columns: {row_cols + [member_col]}")

    wide = (
        df.pivot(index=row_cols, columns=member_col, values="value")
        .reset_index()
    )
    member_cols = [c for c in wide.columns if str(c).startswith("member_")]
    wide = wide[row_cols + sorted(member_cols, key=member_sort_key)]
    wide = wide.sort_values(row_cols, kind="mergesort").reset_index(drop=True)
    return wide


def write_catalog(path: Path, rows: List[Dict[str, Any]]) -> None:
    pd.DataFrame(rows).sort_values(["init_date", "product_family", "short_name", "level_descriptor"], kind="mergesort").to_csv(path, index=False)


def consolidate_gefs(df: pd.DataFrame, forecast_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    counts_by_date: Dict[str, int] = {}
    df = add_time_columns(df)
    df["member_col"] = df["member_code"].map(map_gefs_member)
    row_cols = ["init_date", "cycle_hour", "lead_hours", "target_time_utc", "target_date"]

    group_cols = ["init_date", "short_name", "level_descriptor", "depth_top_m", "depth_bottom_m"]
    for key, sub in df.groupby(group_cols, dropna=False, sort=True):
        init_date, short_name, level_descriptor, depth_top_m, depth_bottom_m = key
        variable_slug = slugify(f"{short_name}__{level_descriptor}")
        out_dir = forecast_root / "gefs" / f"issue_date={init_date}" / f"variable={variable_slug}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "gefs_members.csv"
        wide = build_wide_matrix(sub, row_cols=row_cols, member_col="member_col")
        wide.to_csv(out_path, index=False)

        member_cols = [c for c in wide.columns if c.startswith("member_")]
        counts_by_date[str(init_date)] = counts_by_date.get(str(init_date), 0) + 1
        rows.append(
            {
                "source": "GEFS",
                "init_date": str(init_date),
                "product_family": "all_members",
                "short_name": str(short_name),
                "level_descriptor": str(level_descriptor),
                "units": str(sub["units"].dropna().iloc[0]) if sub["units"].notna().any() else "",
                "layer_index": "",
                "file_path": str(out_path),
                "rows_written": int(len(wide)),
                "member_columns": len(member_cols),
                "member_column_names": ",".join(member_cols),
                "lead_hours_min": int(sub["lead_hours"].min()),
                "lead_hours_max": int(sub["lead_hours"].max()),
                "lead_step_hours": unique_steps(sub["lead_hours"].tolist()),
                "target_time_min_utc": str(wide["target_time_utc"].iloc[0]),
                "target_time_max_utc": str(wide["target_time_utc"].iloc[-1]),
                "depth_top_m": "" if pd.isna(depth_top_m) else float(depth_top_m),
                "depth_bottom_m": "" if pd.isna(depth_bottom_m) else float(depth_bottom_m),
            }
        )

    summary = {
        "files_written": int(len(rows)),
        "variable_groups_per_init_date": counts_by_date,
    }
    return rows, summary


def consolidate_nwm(df: pd.DataFrame, forecast_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    counts_by_date: Dict[str, int] = {}
    df = add_time_columns(df)
    df["member_col"] = df["member_code"].map(map_nwm_member)
    row_cols = ["init_date", "cycle_hour", "lead_hours", "target_time_utc", "target_date"]

    group_cols = ["init_date", "product_family", "short_name", "level_descriptor", "layer_index"]
    for key, sub in df.groupby(group_cols, dropna=False, sort=True):
        init_date, product_family, short_name, level_descriptor, layer_index = key
        variable_bits = [str(short_name), str(level_descriptor)]
        if not pd.isna(layer_index):
            variable_bits.append(f"layer_{int(layer_index)}")
        variable_slug = slugify("__".join(variable_bits))
        out_dir = (
            forecast_root
            / "nwm"
            / f"init_date={init_date}"
            / f"product_family={product_family}"
            / f"variable={variable_slug}"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "nwm_members.csv"
        wide = build_wide_matrix(sub, row_cols=row_cols, member_col="member_col")
        wide.to_csv(out_path, index=False)

        member_cols = [c for c in wide.columns if c.startswith("member_")]
        counts_by_date[str(init_date)] = counts_by_date.get(str(init_date), 0) + 1
        rows.append(
            {
                "source": "NWM",
                "init_date": str(init_date),
                "product_family": str(product_family),
                "short_name": str(short_name),
                "level_descriptor": str(level_descriptor),
                "units": str(sub["units"].dropna().iloc[0]) if sub["units"].notna().any() else "",
                "layer_index": "" if pd.isna(layer_index) else int(layer_index),
                "file_path": str(out_path),
                "rows_written": int(len(wide)),
                "member_columns": len(member_cols),
                "member_column_names": ",".join(member_cols),
                "lead_hours_min": int(sub["lead_hours"].min()),
                "lead_hours_max": int(sub["lead_hours"].max()),
                "lead_step_hours": unique_steps(sub["lead_hours"].tolist()),
                "target_time_min_utc": str(wide["target_time_utc"].iloc[0]),
                "target_time_max_utc": str(wide["target_time_utc"].iloc[-1]),
                "depth_top_m": "",
                "depth_bottom_m": "",
            }
        )

    summary = {
        "files_written": int(len(rows)),
        "variable_groups_per_init_date": counts_by_date,
    }
    return rows, summary


def main() -> int:
    args = parse_args()
    run_dir = Path(args.manifest_run_dir).resolve()
    site = load_site(Path(args.site_config).resolve())
    health = load_health(run_dir / args.health_json)

    handoff_root = run_dir / args.out_subdir / f"site={site['usgs_site']}" / f"run_id={run_dir.name}"
    ensure_fresh_dir(handoff_root, overwrite=bool(args.overwrite))
    forecast_root = handoff_root / "forecast_cache"
    catalog_root = handoff_root / "catalogs"
    forecast_root.mkdir(parents=True, exist_ok=True)
    catalog_root.mkdir(parents=True, exist_ok=True)

    gefs_path = run_dir / args.gefs_extract_subdir / "gefs" / "gefs_point_series.csv"
    nwm_path = run_dir / args.nwm_extract_subdir / "nwm" / "nwm_point_series.csv"
    gefs_df = pd.read_csv(gefs_path)
    nwm_df = pd.read_csv(nwm_path)

    gefs_catalog_rows, gefs_summary = consolidate_gefs(gefs_df, forecast_root)
    nwm_catalog_rows, nwm_summary = consolidate_nwm(nwm_df, forecast_root)

    gefs_catalog_path = catalog_root / "gefs_catalog.csv"
    nwm_catalog_path = catalog_root / "nwm_catalog.csv"
    write_catalog(gefs_catalog_path, gefs_catalog_rows)
    write_catalog(nwm_catalog_path, nwm_catalog_rows)

    meta = {
        "created_utc": now_utc_iso(),
        "manifest_run_dir": str(run_dir),
        "handoff_root": str(handoff_root),
        "site": site,
        "health_json": str((run_dir / args.health_json).resolve()),
        "health_pass": bool(health.get("all_health_pass", False)),
        "source_extracts": {
            "GEFS": str(gefs_path.resolve()),
            "NWM": str(nwm_path.resolve()),
        },
        "catalogs": {
            "GEFS": str(gefs_catalog_path.resolve()),
            "NWM": str(nwm_catalog_path.resolve()),
        },
        "summaries": {
            "GEFS": gefs_summary,
            "NWM": nwm_summary,
        },
    }
    meta_path = handoff_root / "handoff_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"[OK] wrote {gefs_catalog_path}")
    print(f"[OK] wrote {nwm_catalog_path}")
    print(f"[OK] wrote {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
