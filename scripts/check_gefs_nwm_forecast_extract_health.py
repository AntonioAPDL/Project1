#!/usr/bin/env python3
"""Validate GEFS + NWM forecast point extraction outputs against manifests."""

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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Health-check GEFS + NWM point extraction outputs.")
    p.add_argument("--manifest-run-dir", default=DEFAULT_RUN_DIR)
    p.add_argument("--gefs-out-subdir", default=DEFAULT_GEFS_OUT_SUBDIR)
    p.add_argument("--nwm-out-subdir", default=DEFAULT_NWM_OUT_SUBDIR)
    p.add_argument(
        "--out-json",
        default="",
        help="Optional explicit health summary JSON path. Defaults under <run_dir>/health_checks/.",
    )
    return p.parse_args()


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


def main() -> int:
    args = parse_args()
    run_dir = Path(args.manifest_run_dir).resolve()

    summary = {
        "manifest_run_dir": str(run_dir),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "GEFS": check_source(
                "GEFS",
                manifest_path=run_dir / "manifests" / "gefs_manifest.csv",
                output_root=run_dir / args.gefs_out_subdir / "gefs",
                key_cols=GEFS_KEY_COLS,
            ),
            "NWM": check_source(
                "NWM",
                manifest_path=run_dir / "manifests" / "nwm_manifest.csv",
                output_root=run_dir / args.nwm_out_subdir / "nwm",
                key_cols=NWM_KEY_COLS,
            ),
        },
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
