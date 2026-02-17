#!/usr/bin/env python3
"""Compare two point time series on overlap dates and emit diff metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Compare two CSV point series on overlap dates")
    ap.add_argument("--left-csv", type=Path, required=True)
    ap.add_argument("--right-csv", type=Path, required=True)
    ap.add_argument("--left-label", default="left")
    ap.add_argument("--right-label", default="right")
    ap.add_argument("--date-col", default="date")
    ap.add_argument("--value-col", default="discharge_cms")
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    return ap.parse_args()


def load_series(path: Path, date_col: str, value_col: str, label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if date_col not in df.columns or value_col not in df.columns:
        raise ValueError(f"{path}: missing required columns {date_col}/{value_col}")
    out = df[[date_col, value_col]].copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out[value_col] = pd.to_numeric(out[value_col], errors="coerce")
    out = out.dropna(subset=[date_col, value_col]).drop_duplicates(subset=[date_col])
    out = out.rename(columns={value_col: f"value_{label}"})
    return out


def main() -> int:
    args = parse_args()

    left = load_series(args.left_csv, args.date_col, args.value_col, args.left_label)
    right = load_series(args.right_csv, args.date_col, args.value_col, args.right_label)

    merged = left.merge(right, on=args.date_col, how="inner")
    merged = merged.sort_values(args.date_col).reset_index(drop=True)

    lcol = f"value_{args.left_label}"
    rcol = f"value_{args.right_label}"
    merged["diff"] = merged[lcol] - merged[rcol]
    merged["abs_diff"] = merged["diff"].abs()

    if merged.empty:
        summary = {
            "left_csv": str(args.left_csv),
            "right_csv": str(args.right_csv),
            "left_label": args.left_label,
            "right_label": args.right_label,
            "n_overlap": 0,
            "status": "no_overlap",
        }
    else:
        x = merged["diff"].to_numpy(dtype=float)
        mae = float(np.mean(np.abs(x)))
        rmse = float(np.sqrt(np.mean(x ** 2)))
        max_abs = float(np.max(np.abs(x)))
        mean_diff = float(np.mean(x))
        corr = float(np.corrcoef(merged[lcol], merged[rcol])[0, 1]) if len(merged) > 1 else float("nan")
        summary = {
            "left_csv": str(args.left_csv),
            "right_csv": str(args.right_csv),
            "left_label": args.left_label,
            "right_label": args.right_label,
            "n_overlap": int(len(merged)),
            "date_start": merged[args.date_col].min().strftime("%Y-%m-%d"),
            "date_end": merged[args.date_col].max().strftime("%Y-%m-%d"),
            "mae": mae,
            "rmse": rmse,
            "max_abs_diff": max_abs,
            "mean_diff": mean_diff,
            "corr_pearson": corr,
            "diff_q05": float(np.quantile(x, 0.05)),
            "diff_q50": float(np.quantile(x, 0.50)),
            "diff_q95": float(np.quantile(x, 0.95)),
            "status": "ok",
        }

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)

    merged_out = merged.copy()
    if not merged_out.empty:
        merged_out[args.date_col] = merged_out[args.date_col].dt.strftime("%Y-%m-%d")
    merged_out.to_csv(args.out_csv, index=False)
    args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(f"[OK] overlap rows={summary['n_overlap']} status={summary['status']}")
    print(f"[OK] wrote {args.out_csv}")
    print(f"[OK] wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
