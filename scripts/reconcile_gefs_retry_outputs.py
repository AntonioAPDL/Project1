#!/usr/bin/env python3
"""Reconcile a GEFS retry pass into a new non-destructive merged output root."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd


DEFAULT_BASE_OUT_SUBDIR = "extract_gefs_full"
DEFAULT_RETRY_OUT_SUBDIR = "extract_gefs_retry"
DEFAULT_RECONCILED_OUT_SUBDIR = "extract_gefs_full_reconciled"
POINT_SORT_COLS = [
    "init_date",
    "cycle_hour",
    "member_number",
    "lead_hours",
    "product_family",
    "short_name",
    "level_descriptor",
    "object_url",
]
STATUS_SORT_COLS = [
    "init_date",
    "cycle_hour",
    "member_code",
    "product_family",
    "lead_hours_min",
    "object_url",
]
FAILURE_SORT_COLS = [
    "init_date",
    "cycle_hour",
    "member_code",
    "product_family",
    "lead_hours",
    "short_name",
    "level_descriptor",
    "object_url",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reconcile a GEFS retry pass into a new merged output root.")
    p.add_argument("--base-manifest-run-dir", required=True)
    p.add_argument("--retry-run-dir", required=True)
    p.add_argument("--base-out-subdir", default=DEFAULT_BASE_OUT_SUBDIR)
    p.add_argument("--retry-out-subdir", default=DEFAULT_RETRY_OUT_SUBDIR)
    p.add_argument("--reconciled-out-subdir", default=DEFAULT_RECONCILED_OUT_SUBDIR)
    return p.parse_args()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Required CSV missing: {path}")
    return pd.read_csv(path)


def sort_if_possible(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    usable = [col for col in cols if col in df.columns]
    if not usable or df.empty:
        return df
    return df.sort_values(usable, kind="mergesort").reset_index(drop=True)


def maybe_read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def main() -> int:
    args = parse_args()
    base_run_dir = Path(args.base_manifest_run_dir).resolve()
    retry_run_dir = Path(args.retry_run_dir).resolve()

    base_root = base_run_dir / args.base_out_subdir / "gefs"
    retry_root = retry_run_dir / args.retry_out_subdir / "gefs"
    reconciled_root = base_run_dir / args.reconciled_out_subdir / "gefs"
    reconciled_root.mkdir(parents=True, exist_ok=True)

    base_series = read_csv(base_root / "gefs_point_series.csv")
    base_status = read_csv(base_root / "gefs_file_status.csv")
    base_failures = maybe_read(base_root / "gefs_row_failures.csv")

    retry_series = read_csv(retry_root / "gefs_point_series.csv")
    retry_status = read_csv(retry_root / "gefs_file_status.csv")
    retry_failures = maybe_read(retry_root / "gefs_row_failures.csv")

    retry_urls = set(retry_status["object_url"].astype(str))
    retry_ok_urls = set(retry_status.loc[retry_status["status"].astype(str) == "ok", "object_url"].astype(str))

    merged_series = pd.concat(
        [
            base_series[~base_series["object_url"].astype(str).isin(retry_ok_urls)].copy(),
            retry_series.copy(),
        ],
        ignore_index=True,
    )
    merged_status = pd.concat(
        [
            base_status[~base_status["object_url"].astype(str).isin(retry_urls)].copy(),
            retry_status.copy(),
        ],
        ignore_index=True,
    )

    base_fail_keep = base_failures
    if not base_failures.empty and "object_url" in base_failures.columns:
        base_fail_keep = base_failures[~base_failures["object_url"].astype(str).isin(retry_urls)].copy()
    merged_failures = pd.concat([base_fail_keep, retry_failures.copy()], ignore_index=True)

    merged_series = sort_if_possible(merged_series, POINT_SORT_COLS)
    merged_status = sort_if_possible(merged_status, STATUS_SORT_COLS)
    merged_failures = sort_if_possible(merged_failures, FAILURE_SORT_COLS)

    series_path = reconciled_root / "gefs_point_series.csv"
    status_path = reconciled_root / "gefs_file_status.csv"
    failure_path = reconciled_root / "gefs_row_failures.csv"
    merged_series.to_csv(series_path, index=False)
    merged_status.to_csv(status_path, index=False)
    if merged_failures.empty:
        if failure_path.exists():
            failure_path.unlink()
    else:
        merged_failures.to_csv(failure_path, index=False)

    unresolved_status = merged_status[merged_status["status"].astype(str) != "ok"].copy()
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "base_manifest_run_dir": str(base_run_dir),
        "retry_run_dir": str(retry_run_dir),
        "base_out_subdir": args.base_out_subdir,
        "retry_out_subdir": args.retry_out_subdir,
        "reconciled_out_subdir": args.reconciled_out_subdir,
        "retry_urls_considered": int(len(retry_urls)),
        "retry_urls_recovered_ok": int(len(retry_ok_urls)),
        "base_status_rows": int(len(base_status)),
        "base_failure_rows": int(len(base_failures)),
        "retry_status_rows": int(len(retry_status)),
        "retry_failure_rows": int(len(retry_failures)),
        "reconciled_status_rows": int(len(merged_status)),
        "reconciled_failure_rows": int(len(merged_failures)),
        "reconciled_output_rows": int(len(merged_series)),
        "reconciled_failed_status_rows": int(len(unresolved_status)),
        "series_csv": str(series_path),
        "status_csv": str(status_path),
        "failure_csv": str(failure_path) if failure_path.exists() else "",
    }
    (reconciled_root.parent / "gefs_reconciliation_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    print(f"[OK] wrote {series_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
