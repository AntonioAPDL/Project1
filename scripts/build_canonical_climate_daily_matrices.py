#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from canonical_climate_indices_lib import (
    ROOT,
    canonical_paths,
    interpolate_monthly_to_daily,
    load_config,
    monthly_wide_to_long,
    package_versions,
    raw_daily_matrix_path,
    render_postprocess_review,
    snapshot_config,
    standardized_daily_matrix_path,
    standardize_daily_matrix,
    utc_now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build canonical daily raw and standardized climate-index matrices.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "canonical_gdpc_master_covariate.yaml",
        help="Canonical climate-index config.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config.resolve())
    paths = canonical_paths(cfg)

    canonical_start = cfg["canonical_window"]["start_date"]
    canonical_end = cfg["canonical_window"]["end_date"]
    linear_tail_days = int(cfg["postprocess"]["interpolation"]["linear_tail_days"])
    ddof = int(cfg["postprocess"]["standardization"]["ddof"])
    require_end_month = bool(cfg["postprocess"]["interpolation"].get("require_monthly_coverage_through_end_month", True))
    end_month = cfg["monthly_source_window"]["end_month"]

    combined: pd.DataFrame | None = None
    per_index_coverage: list[dict[str, object]] = []

    for item in cfg["indices"]:
        index_id = item["index_id"]
        monthly_csv = paths.monthly_csv_root / f"{index_id}.csv"
        if not monthly_csv.exists():
            raise SystemExit(f"Missing monthly source CSV for {index_id}: {monthly_csv}. Run the download step first.")
        monthly_wide = pd.read_csv(monthly_csv)
        monthly_long = monthly_wide_to_long(
            monthly_wide,
            start_month=cfg["monthly_source_window"]["start_month"],
            end_month=end_month,
        )
        if require_end_month and monthly_long["month_start"].max() < pd.Timestamp(end_month):
            raise SystemExit(
                f"Monthly coverage for {index_id} ends at {monthly_long['month_start'].max().strftime('%Y-%m-%d')}, "
                f"which is earlier than required end month {end_month}."
            )
        daily = interpolate_monthly_to_daily(
            monthly_long,
            start_date=canonical_start,
            end_date=canonical_end,
            linear_tail_days=linear_tail_days,
        ).rename(columns={"value": index_id})
        combined = daily if combined is None else combined.merge(daily, on="time", how="outer")
        per_index_coverage.append(
            {
                "index_id": index_id,
                "month_start_min": monthly_long["month_start"].min().strftime("%Y-%m-%d"),
                "month_start_max": monthly_long["month_start"].max().strftime("%Y-%m-%d"),
                "monthly_rows": int(len(monthly_long)),
                "daily_min": str(daily["time"].min()),
                "daily_max": str(daily["time"].max()),
                "missing_daily": int(daily[index_id].isna().sum()),
            }
        )

    assert combined is not None
    combined = combined.sort_values("time").reset_index(drop=True)
    if combined.isna().any().any():
        missing_cols = [col for col in combined.columns if combined[col].isna().any()]
        raise SystemExit(f"Combined daily matrix contains missing values after interpolation: {missing_cols}")

    raw_path = raw_daily_matrix_path(cfg, paths)
    combined.to_csv(raw_path, index=False)

    standardized, standardization_stats = standardize_daily_matrix(combined, date_col="time", ddof=ddof)
    std_path = standardized_daily_matrix_path(cfg, paths)
    standardized.to_csv(std_path, index=False)

    validation = {
        "generated_at_utc": utc_now_iso(),
        "config_path": str(args.config.resolve()),
        "lineage_version": cfg["version"],
        "artifact_root": str(paths.root),
        "canonical_window": {"start_date": canonical_start, "end_date": canonical_end},
        "daily_row_count": int(len(combined)),
        "column_count": int(len(combined.columns) - 1),
        "index_ids": [item["index_id"] for item in cfg["indices"]],
        "raw_daily_matrix_path": str(raw_path),
        "standardized_daily_matrix_path": str(std_path),
        "interpolation": {
            "method": cfg["postprocess"]["interpolation"]["method"],
            "linear_tail_days": linear_tail_days,
            "require_monthly_coverage_through_end_month": require_end_month,
        },
        "standardization": {
            "method": cfg["postprocess"]["standardization"]["method"],
            "ddof": ddof,
        },
        "per_index_coverage": per_index_coverage,
        "standardization_stats": standardization_stats,
        "package_versions": package_versions(),
    }
    write_json(paths.metadata_root / "validation_summary.json", validation)
    snapshot_config(args.config.resolve(), paths.metadata_root / "canonical_gdpc_build_config.yaml")
    write_json(
        paths.metadata_root / "build_metadata.json",
        {
            "generated_at_utc": utc_now_iso(),
            "config_path": str(args.config.resolve()),
            "lineage_version": cfg["version"],
            "artifact_root": str(paths.root),
            "canonical_window": {"start_date": canonical_start, "end_date": canonical_end},
            "package_versions": package_versions(),
            "python_session": {
                "python_executable": sys.executable,
                "driver_script": str(Path(__file__).resolve()),
            },
            "outputs": {
                "raw_daily_matrix": str(raw_path),
                "standardized_daily_matrix": str(std_path),
                "validation_summary": str(paths.metadata_root / 'validation_summary.json'),
            },
        },
    )
    render_postprocess_review(cfg, validation, standardization_stats, paths)
    print(f"[OK] wrote raw daily matrix: {raw_path}")
    print(f"[OK] wrote standardized daily matrix: {std_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
