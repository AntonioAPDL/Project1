#!/usr/bin/env python3
"""Forensics comparison for weighted_time_series_custom*.csv artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare weighted_time_series_custom.csv vs "
            "weighted_time_series_custom_filled.csv and emit a structured report."
        )
    )
    parser.add_argument(
        "--custom",
        default="weighted_time_series_custom.csv",
        help="Path to weighted_time_series_custom.csv",
    )
    parser.add_argument(
        "--filled",
        default="weighted_time_series_custom_filled.csv",
        help="Path to weighted_time_series_custom_filled.csv",
    )
    parser.add_argument(
        "--out-json",
        default="repro/reports/weighted_custom_filled_forensics.json",
        help="Output JSON report path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    custom_path = Path(args.custom)
    filled_path = Path(args.filled)
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    custom = pd.read_csv(custom_path)
    filled = pd.read_csv(filled_path)

    if "target_date" not in custom.columns or "target_date" not in filled.columns:
        raise ValueError("Both inputs must contain a 'target_date' column.")

    custom["target_date"] = custom["target_date"].astype(str)
    filled["target_date"] = filled["target_date"].astype(str)

    ensemble_cols = [c for c in custom.columns if c != "target_date"]
    if ensemble_cols != [c for c in filled.columns if c != "target_date"]:
        raise ValueError("Ensemble-member columns differ between inputs.")

    custom_dates = set(custom["target_date"])
    filled_dates = set(filled["target_date"])
    common_dates = sorted(custom_dates & filled_dates)
    extra_in_filled = sorted(filled_dates - custom_dates)
    extra_in_custom = sorted(custom_dates - filled_dates)

    custom_common = (
        custom[custom["target_date"].isin(common_dates)]
        .sort_values("target_date")
        .reset_index(drop=True)
    )
    filled_common = (
        filled[filled["target_date"].isin(common_dates)]
        .sort_values("target_date")
        .reset_index(drop=True)
    )

    cvals = custom_common[ensemble_cols].astype(float)
    fvals = filled_common[ensemble_cols].astype(float)

    mask_na_to_val = cvals.isna() & ~fvals.isna()
    mask_val_to_na = ~cvals.isna() & fvals.isna()
    mask_both_not_na = ~cvals.isna() & ~fvals.isna()
    mask_value_changed = mask_both_not_na & ~np.isclose(cvals, fvals, equal_nan=True)

    per_date_changes = (
        mask_value_changed.sum(axis=1).rename("changed_cells").to_frame()
    )
    per_date_changes["target_date"] = custom_common["target_date"].values
    top_changed_dates = (
        per_date_changes.sort_values("changed_cells", ascending=False)
        .head(10)
        .to_dict(orient="records")
    )

    report = {
        "inputs": {
            "custom": str(custom_path),
            "filled": str(filled_path),
        },
        "shape": {
            "custom": list(custom.shape),
            "filled": list(filled.shape),
        },
        "date_ranges": {
            "custom_min": custom["target_date"].min(),
            "custom_max": custom["target_date"].max(),
            "filled_min": filled["target_date"].min(),
            "filled_max": filled["target_date"].max(),
            "common_dates_count": len(common_dates),
            "extra_dates_in_filled_count": len(extra_in_filled),
            "extra_dates_in_custom_count": len(extra_in_custom),
            "extra_dates_in_filled_first5": extra_in_filled[:5],
            "extra_dates_in_filled_last5": extra_in_filled[-5:],
        },
        "cell_differences_on_common_dates": {
            "na_to_value": int(mask_na_to_val.sum().sum()),
            "value_to_na": int(mask_val_to_na.sum().sum()),
            "value_changed_non_na": int(mask_value_changed.sum().sum()),
        },
        "top_changed_dates": top_changed_dates,
        "first_row": {
            "custom": custom.iloc[0].to_dict(),
            "filled": filled.iloc[0].to_dict(),
        },
    }

    out_path.write_text(json.dumps(report, indent=2))
    print(f"Wrote forensics report: {out_path}")
    print(
        "Summary:",
        json.dumps(report["cell_differences_on_common_dates"], sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
