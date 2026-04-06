#!/usr/bin/env python3
"""Validate GEFS + NWM forecast point extraction outputs.

Supports two modes:
- `full`: validate completed extraction outputs against the full manifests
- `smoke`: validate bounded smoke outputs written by
  `scripts/gefs_nwm_point_smoke_extract.py`
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


DEFAULT_RUN_DIR = "repro/gefs_nwm_forecast_runs/gefs_nwm_forecast_manifest_20260307T023425Z"
DEFAULT_GEFS_OUT_SUBDIR = "extract_gefs_full"
DEFAULT_NWM_OUT_SUBDIR = "extract_full"
DEFAULT_MODE = "full"

GEFS_KEY_COLS = [
    "init_date",
    "cycle_hour",
    "member_code",
    "product_family",
    "lead_hours",
    "short_name",
    "level_descriptor",
    "object_url",
]

NWM_KEY_COLS = [
    "init_date",
    "cycle_hour",
    "member_code",
    "product_family",
    "lead_hours",
    "short_name",
    "level_descriptor",
    "layer_index",
    "object_url",
]

GEFS_SMOKE_REQUIRED_COLS = [
    "source",
    "init_date",
    "cycle_hour",
    "member_code",
    "lead_hours",
    "product_family",
    "short_name",
    "level_descriptor",
    "value",
    "units",
    "file_url",
]

NWM_SMOKE_REQUIRED_COLS = [
    "source",
    "init_date",
    "cycle_hour",
    "member_code",
    "lead_hours",
    "product_family",
    "short_name",
    "level_descriptor",
    "value",
    "units",
    "distance_m",
    "file_url",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Health-check GEFS + NWM point extraction outputs.")
    p.add_argument("--manifest-run-dir", default=DEFAULT_RUN_DIR)
    p.add_argument("--gefs-out-subdir", default=DEFAULT_GEFS_OUT_SUBDIR)
    p.add_argument("--nwm-out-subdir", default=DEFAULT_NWM_OUT_SUBDIR)
    p.add_argument(
        "--sources",
        default="gefs,nwm",
        help="Comma-separated subset of sources to validate: gefs,nwm.",
    )
    p.add_argument("--mode", choices=["full", "smoke"], default=DEFAULT_MODE)
    p.add_argument(
        "--out-json",
        default="",
        help="Optional explicit health summary JSON path. Defaults under <run_dir>/health_checks/.",
    )
    return p.parse_args()


def normalize_sources(text: str) -> List[str]:
    allowed = {"gefs", "nwm"}
    out = [item.strip().lower() for item in str(text).split(",") if item.strip()]
    if not out:
        raise SystemExit("No sources requested.")
    invalid = [item for item in out if item not in allowed]
    if invalid:
        raise SystemExit(f"Unsupported source(s): {invalid}")
    return out


def normalize_key_frame(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    out = df.loc[:, cols].copy()
    for col in cols:
        if col in {"cycle_hour", "lead_hours"}:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64").astype(str)
        elif col == "layer_index":
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64").astype(str)
        else:
            out[col] = out[col].astype(str)
    return out


def date_count_mismatches(manifest_df: pd.DataFrame, output_df: pd.DataFrame) -> List[Dict[str, Any]]:
    manifest_counts = (
        manifest_df.groupby(["init_date"], dropna=False)
        .size()
        .rename("expected_rows")
        .reset_index()
    )
    output_counts = (
        output_df.groupby(["init_date"], dropna=False)
        .size()
        .rename("actual_rows")
        .reset_index()
    )
    merged = manifest_counts.merge(output_counts, on="init_date", how="outer").fillna(0)
    merged["expected_rows"] = merged["expected_rows"].astype(int)
    merged["actual_rows"] = merged["actual_rows"].astype(int)
    mismatches = merged[merged["expected_rows"] != merged["actual_rows"]].copy()
    return mismatches.to_dict("records")


def check_source(
    source: str,
    manifest_path: Path,
    output_root: Path,
    key_cols: List[str],
) -> Dict[str, Any]:
    manifest_df = pd.read_csv(manifest_path)
    output_df = pd.read_csv(output_root / f"{source.lower()}_point_series.csv")
    status_df = pd.read_csv(output_root / f"{source.lower()}_file_status.csv")
    failure_path = output_root / f"{source.lower()}_row_failures.csv"
    failure_df = pd.read_csv(failure_path) if failure_path.exists() else pd.DataFrame()

    manifest_keys = normalize_key_frame(manifest_df, key_cols)
    output_keys = normalize_key_frame(output_df, key_cols)
    merged = manifest_keys.merge(output_keys.drop_duplicates(), on=key_cols, how="outer", indicator=True)

    missing_rows = int((merged["_merge"] == "left_only").sum())
    extra_rows = int((merged["_merge"] == "right_only").sum())
    duplicate_output_rows = int(output_keys.duplicated(subset=key_cols).sum())
    duplicate_status_rows = int(status_df.duplicated(subset=["object_url"]).sum())
    null_value_rows = int(pd.to_numeric(output_df["value"], errors="coerce").isna().sum())
    status_counts = {str(k): int(v) for k, v in status_df["status"].value_counts(dropna=False).to_dict().items()}
    per_date_mismatches = date_count_mismatches(manifest_df, output_df)

    expected_files = int(manifest_df["object_url"].nunique())
    expected_rows = int(len(manifest_df))
    actual_status_rows = int(len(status_df))
    actual_rows = int(len(output_df))
    failure_rows = int(len(failure_df))

    health_pass = all(
        [
            expected_files == actual_status_rows,
            expected_rows == actual_rows,
            failure_rows == 0,
            missing_rows == 0,
            extra_rows == 0,
            duplicate_output_rows == 0,
            duplicate_status_rows == 0,
            null_value_rows == 0,
            set(status_counts.keys()) == {"ok"},
            status_counts.get("ok", 0) == expected_files,
            len(per_date_mismatches) == 0,
        ]
    )

    return {
        "source": source,
        "mode": "full",
        "manifest_path": str(manifest_path),
        "output_root": str(output_root),
        "expected_files": expected_files,
        "expected_rows": expected_rows,
        "actual_status_rows": actual_status_rows,
        "actual_rows": actual_rows,
        "failure_rows": failure_rows,
        "missing_rows_vs_manifest": missing_rows,
        "extra_rows_vs_manifest": extra_rows,
        "duplicate_output_rows": duplicate_output_rows,
        "duplicate_status_rows": duplicate_status_rows,
        "null_value_rows": null_value_rows,
        "status_counts": status_counts,
        "per_date_mismatches": per_date_mismatches,
        "health_pass": health_pass,
    }


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_smoke_source(
    source: str,
    smoke_root: Path,
    csv_name: str,
    meta_name: str,
    required_cols: List[str],
    smoke_summary: Dict[str, Any],
) -> Dict[str, Any]:
    source_key = source.lower()
    csv_path = smoke_root / source_key / csv_name
    meta_path = smoke_root / source_key / meta_name

    output_exists = csv_path.exists()
    meta_exists = meta_path.exists()
    rows_out = 0
    duplicate_rows = 0
    null_value_rows = 0
    missing_required_cols: List[str] = []
    columns: List[str] = []
    sample_init_dates: List[str] = []

    if output_exists:
        output_df = pd.read_csv(csv_path)
        rows_out = int(len(output_df))
        duplicate_rows = int(output_df.duplicated().sum())
        columns = [str(c) for c in output_df.columns.tolist()]
        missing_required_cols = [col for col in required_cols if col not in output_df.columns]
        if "value" in output_df.columns:
            null_value_rows = int(pd.to_numeric(output_df["value"], errors="coerce").isna().sum())
        if "init_date" in output_df.columns:
            sample_init_dates = sorted({str(x) for x in output_df["init_date"].dropna().astype(str).tolist()})

    meta = load_json(meta_path) if meta_exists else {}
    summary_meta = smoke_summary.get(source_key, {}) if isinstance(smoke_summary, dict) else {}

    expected_rows_meta = meta.get("rows_out")
    expected_rows_summary = summary_meta.get("rows_out")
    row_match_meta = expected_rows_meta is None or int(expected_rows_meta) == rows_out
    row_match_summary = expected_rows_summary is None or int(expected_rows_summary) == rows_out

    if source == "GEFS":
        distance_value = meta.get("selected_cell_dist_km")
        distance_field = "selected_cell_dist_km"
    else:
        distance_value = (meta.get("grid_reference") or {}).get("reference_distance_m")
        distance_field = "reference_distance_m"

    distance_is_finite = pd.notna(distance_value)

    health_pass = all(
        [
            output_exists,
            meta_exists,
            rows_out > 0,
            duplicate_rows == 0,
            null_value_rows == 0,
            len(missing_required_cols) == 0,
            row_match_meta,
            row_match_summary,
            bool(distance_is_finite),
        ]
    )

    return {
        "source": source,
        "mode": "smoke",
        "smoke_root": str(smoke_root),
        "output_csv": str(csv_path),
        "output_meta": str(meta_path),
        "output_exists": output_exists,
        "meta_exists": meta_exists,
        "rows_out": rows_out,
        "duplicate_rows": duplicate_rows,
        "null_value_rows": null_value_rows,
        "columns": columns,
        "missing_required_cols": missing_required_cols,
        "sample_init_dates": sample_init_dates,
        "expected_rows_meta": expected_rows_meta,
        "expected_rows_summary": expected_rows_summary,
        "row_match_meta": row_match_meta,
        "row_match_summary": row_match_summary,
        "distance_field": distance_field,
        "distance_value": distance_value,
        "health_pass": health_pass,
    }


def main() -> int:
    args = parse_args()
    run_dir = Path(args.manifest_run_dir).resolve()
    requested_sources = normalize_sources(args.sources)

    if args.mode == "full":
        source_summaries: Dict[str, Dict[str, Any]] = {}
        if "gefs" in requested_sources:
            source_summaries["GEFS"] = check_source(
                "GEFS",
                manifest_path=run_dir / "manifests" / "gefs_manifest.csv",
                output_root=run_dir / args.gefs_out_subdir / "gefs",
                key_cols=GEFS_KEY_COLS,
            )
        if "nwm" in requested_sources:
            source_summaries["NWM"] = check_source(
                "NWM",
                manifest_path=run_dir / "manifests" / "nwm_manifest.csv",
                output_root=run_dir / args.nwm_out_subdir / "nwm",
                key_cols=NWM_KEY_COLS,
            )
        summary = {
            "manifest_run_dir": str(run_dir),
            "mode": args.mode,
            "requested_sources": requested_sources,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "sources": source_summaries,
        }
    else:
        smoke_root = run_dir / "smoke"
        smoke_summary_path = smoke_root / "smoke_summary.json"
        smoke_summary = load_json(smoke_summary_path) if smoke_summary_path.exists() else {}
        source_summaries = {}
        if "gefs" in requested_sources:
            source_summaries["GEFS"] = check_smoke_source(
                "GEFS",
                smoke_root=smoke_root,
                csv_name="gefs_point_smoke.csv",
                meta_name="gefs_point_smoke_meta.json",
                required_cols=GEFS_SMOKE_REQUIRED_COLS,
                smoke_summary=smoke_summary,
            )
        if "nwm" in requested_sources:
            source_summaries["NWM"] = check_smoke_source(
                "NWM",
                smoke_root=smoke_root,
                csv_name="nwm_point_smoke.csv",
                meta_name="nwm_point_smoke_meta.json",
                required_cols=NWM_SMOKE_REQUIRED_COLS,
                smoke_summary=smoke_summary,
            )
        summary = {
            "manifest_run_dir": str(run_dir),
            "mode": args.mode,
            "requested_sources": requested_sources,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "smoke_summary_path": str(smoke_summary_path),
            "smoke_summary_exists": smoke_summary_path.exists(),
            "sources": source_summaries,
        }

    summary["all_health_pass"] = all(src["health_pass"] for src in summary["sources"].values())

    out_json = Path(args.out_json).resolve() if args.out_json else run_dir / "health_checks" / "forecast_extract_health.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"[OK] wrote {out_json}")
    return 0 if summary["all_health_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
