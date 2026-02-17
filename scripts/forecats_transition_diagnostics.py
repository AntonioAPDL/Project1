#!/usr/bin/env python3
"""Compute pre/post window diagnostics around configured transition dates."""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Transition diagnostics for a single point series")
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--date-col", default="date")
    ap.add_argument("--value-col", default="discharge_cms")
    ap.add_argument("--transition-date", action="append", required=True, help="YYYY-MM-DD; repeatable")
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    return ap.parse_args()


def stats(x: np.ndarray) -> dict[str, float | int]:
    if x.size == 0:
        return {
            "n": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "std": float("nan"),
            "q05": float("nan"),
            "q95": float("nan"),
        }
    return {
        "n": int(x.size),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "std": float(np.std(x, ddof=1)) if x.size > 1 else float("nan"),
        "q05": float(np.quantile(x, 0.05)),
        "q95": float(np.quantile(x, 0.95)),
    }


def main() -> int:
    args = parse_args()
    df = pd.read_csv(args.csv)
    if args.date_col not in df.columns or args.value_col not in df.columns:
        raise ValueError(f"Missing required columns {args.date_col}/{args.value_col}")

    df = df[[args.date_col, args.value_col]].copy()
    df[args.date_col] = pd.to_datetime(df[args.date_col], errors="coerce")
    df[args.value_col] = pd.to_numeric(df[args.value_col], errors="coerce")
    df = df.dropna(subset=[args.date_col, args.value_col]).sort_values(args.date_col).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for td_str in args.transition_date:
        td = pd.Timestamp(td_str)
        pre_start = td - timedelta(days=args.window_days)
        pre_end = td - timedelta(days=1)
        post_start = td
        post_end = td + timedelta(days=args.window_days - 1)

        pre = df[(df[args.date_col] >= pre_start) & (df[args.date_col] <= pre_end)][args.value_col].to_numpy(dtype=float)
        post = df[(df[args.date_col] >= post_start) & (df[args.date_col] <= post_end)][args.value_col].to_numpy(dtype=float)

        s_pre = stats(pre)
        s_post = stats(post)

        row = {
            "transition_date": td.strftime("%Y-%m-%d"),
            "window_days": int(args.window_days),
            "pre_start": pre_start.strftime("%Y-%m-%d"),
            "pre_end": pre_end.strftime("%Y-%m-%d"),
            "post_start": post_start.strftime("%Y-%m-%d"),
            "post_end": post_end.strftime("%Y-%m-%d"),
            "n_pre": s_pre["n"],
            "n_post": s_post["n"],
            "pre_mean": s_pre["mean"],
            "post_mean": s_post["mean"],
            "pre_median": s_pre["median"],
            "post_median": s_post["median"],
            "pre_std": s_pre["std"],
            "post_std": s_post["std"],
            "pre_q05": s_pre["q05"],
            "post_q05": s_post["q05"],
            "pre_q95": s_pre["q95"],
            "post_q95": s_post["q95"],
            "delta_mean": (s_post["mean"] - s_pre["mean"]) if s_pre["n"] > 0 and s_post["n"] > 0 else float("nan"),
            "delta_median": (s_post["median"] - s_pre["median"]) if s_pre["n"] > 0 and s_post["n"] > 0 else float("nan"),
        }
        rows.append(row)

    out_df = pd.DataFrame(rows)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out_csv, index=False)

    summary = {
        "input_csv": str(args.csv),
        "date_col": args.date_col,
        "value_col": args.value_col,
        "window_days": int(args.window_days),
        "n_transitions": int(len(rows)),
        "transitions": rows,
    }
    args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(f"[OK] transitions={len(rows)}")
    print(f"[OK] wrote {args.out_csv}")
    print(f"[OK] wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
