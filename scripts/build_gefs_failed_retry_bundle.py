#!/usr/bin/env python3
"""Build a compact GEFS retry bundle from failed extraction ledger rows.

This creates a manifest-run-like directory that contains only the failed GEFS
object URLs from a completed extraction. It is designed for targeted retry
passes with lower concurrency and higher retry counts.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_BASE_OUT_SUBDIR = "extract_gefs_full"
DEFAULT_ERROR_SUBSTRING = "503: Slow Down"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build a GEFS retry bundle from failed file ledgers.")
    p.add_argument("--base-manifest-run-dir", required=True, help="Original manifest run dir.")
    p.add_argument("--retry-run-dir", required=True, help="Output retry bundle directory.")
    p.add_argument("--base-out-subdir", default=DEFAULT_BASE_OUT_SUBDIR)
    p.add_argument(
        "--error-substring",
        default=DEFAULT_ERROR_SUBSTRING,
        help="Optional error substring filter; only failed status rows whose error contains this text are retried.",
    )
    p.add_argument(
        "--include-all-failed",
        action="store_true",
        help="Ignore --error-substring and include every failed GEFS object URL.",
    )
    return p.parse_args()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Required CSV missing: {path}")
    return pd.read_csv(path)


def require_columns(df: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise SystemExit(f"{label} is missing required column(s): {missing}")


def sort_if_possible(df: pd.DataFrame, preferred_cols: list[str]) -> pd.DataFrame:
    cols = [col for col in preferred_cols if col in df.columns]
    if not cols or df.empty:
        return df
    return df.sort_values(cols, kind="mergesort")


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> int:
    args = parse_args()
    base_run_dir = Path(args.base_manifest_run_dir).resolve()
    retry_run_dir = Path(args.retry_run_dir).resolve()
    base_out_root = base_run_dir / args.base_out_subdir / "gefs"

    status_path = base_out_root / "gefs_file_status.csv"
    failure_path = base_out_root / "gefs_row_failures.csv"
    manifest_path = base_run_dir / "manifests" / "gefs_manifest.csv"

    status_df = read_csv(status_path)
    failure_df = pd.read_csv(failure_path) if failure_path.exists() else pd.DataFrame()
    manifest_df = read_csv(manifest_path)
    require_columns(status_df, ["object_url", "status", "error"], "GEFS status ledger")
    require_columns(manifest_df, ["object_url"], "GEFS manifest")
    if not failure_df.empty:
        require_columns(failure_df, ["object_url"], "GEFS failure ledger")

    duplicate_status_urls = int(status_df["object_url"].astype(str).duplicated().sum())
    if duplicate_status_urls:
        raise SystemExit(
            f"GEFS status ledger contains {duplicate_status_urls} duplicate object_url row(s); "
            "repair the base extract health before building a retry bundle."
        )

    failed_status = status_df[status_df["status"].astype(str) != "ok"].copy()
    if not args.include_all_failed:
        err = failed_status["error"].fillna("").astype(str)
        failed_status = failed_status[err.str.contains(str(args.error_substring), regex=False)].copy()

    if failed_status.empty:
        raise SystemExit("No failed GEFS status rows matched the retry selection.")

    failed_urls = set(failed_status["object_url"].astype(str))
    retry_manifest = manifest_df[manifest_df["object_url"].astype(str).isin(failed_urls)].copy()
    if retry_manifest.empty:
        raise SystemExit("Retry manifest would be empty after filtering original manifest by failed URLs.")
    failed_status = sort_if_possible(
        failed_status,
        ["init_date", "cycle_hour", "member_code", "product_family", "object_url"],
    )
    retry_manifest = sort_if_possible(
        retry_manifest,
        ["init_date", "cycle_hour", "member_number", "product_family", "lead_hours", "short_name", "object_url"],
    )

    retry_failure_df = pd.DataFrame()
    if not failure_df.empty and "object_url" in failure_df.columns:
        retry_failure_df = failure_df[failure_df["object_url"].astype(str).isin(failed_urls)].copy()
        retry_failure_df = sort_if_possible(
            retry_failure_df,
            ["init_date", "cycle_hour", "member_code", "product_family", "lead_hours", "short_name", "object_url"],
        )

    manifests_dir = retry_run_dir / "manifests"
    provenance_dir = retry_run_dir / "provenance"
    smoke_dir = retry_run_dir / "smoke"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    provenance_dir.mkdir(parents=True, exist_ok=True)
    (smoke_dir / "gefs").mkdir(parents=True, exist_ok=True)
    (smoke_dir / "nwm").mkdir(parents=True, exist_ok=True)

    retry_manifest_path = manifests_dir / "gefs_manifest.csv"
    retry_manifest.to_csv(retry_manifest_path, index=False)
    failed_status.to_csv(provenance_dir / "failed_gefs_status_rows.csv", index=False)
    if not retry_failure_df.empty:
        retry_failure_df.to_csv(provenance_dir / "failed_gefs_row_failures.csv", index=False)

    copy_if_exists(base_run_dir / "smoke" / "smoke_summary.json", smoke_dir / "smoke_summary.json")
    copy_if_exists(base_run_dir / "smoke" / "gefs" / "gefs_point_smoke_meta.json", smoke_dir / "gefs" / "gefs_point_smoke_meta.json")
    copy_if_exists(base_run_dir / "smoke" / "nwm" / "nwm_point_smoke_meta.json", smoke_dir / "nwm" / "nwm_point_smoke_meta.json")

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "base_manifest_run_dir": str(base_run_dir),
        "retry_run_dir": str(retry_run_dir),
        "base_out_subdir": args.base_out_subdir,
        "selection": {
            "include_all_failed": bool(args.include_all_failed),
            "error_substring": None if args.include_all_failed else str(args.error_substring),
        },
        "failed_status_rows_selected": int(len(failed_status)),
        "failed_object_urls_selected": int(len(failed_urls)),
        "failed_init_dates_selected": sorted({str(x) for x in failed_status.get("init_date", pd.Series(dtype=str)).dropna().astype(str).tolist()}),
        "retry_manifest_rows": int(len(retry_manifest)),
        "retry_manifest_unique_urls": int(retry_manifest["object_url"].nunique()),
        "row_failures_subset": int(len(retry_failure_df)),
        "retry_manifest_csv": str(retry_manifest_path),
        "failed_status_csv": str(provenance_dir / "failed_gefs_status_rows.csv"),
        "failed_row_failures_csv": str(provenance_dir / "failed_gefs_row_failures.csv") if not retry_failure_df.empty else "",
    }
    (provenance_dir / "retry_bundle_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"[OK] wrote {retry_manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
