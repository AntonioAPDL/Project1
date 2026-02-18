#!/usr/bin/env python3
"""Build a unified daily NWM retrospective table across versions."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Optional

import pandas as pd


VERSION_TO_COL = {
    "1.2": "NWS1.2",
    "2.0": "NWS2.0",
    "2.1": "NWS2.1",
    "3.0": "NWS3.0",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build unified NWM retrospective daily table.")
    p.add_argument("--v12", default="", help="Path to v1.2 daily CSV (optional).")
    p.add_argument("--v20", default="", help="Path to v2.0 daily CSV (optional).")
    p.add_argument("--v21", default="", help="Path to v2.1 daily CSV (optional).")
    p.add_argument("--v30", default="", help="Path to v3.0 daily CSV (optional).")
    p.add_argument("--out-csv", required=True, help="Output unified CSV path.")
    return p.parse_args()


def load_series(path: str, col_name: str) -> Optional[pd.DataFrame]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None

    df = pd.read_csv(p)
    date_col = "date" if "date" in df.columns else ("Date" if "Date" in df.columns else "")
    value_col = (
        "streamflow_cms" if "streamflow_cms" in df.columns else ("streamflow" if "streamflow" in df.columns else "")
    )
    if not date_col or not value_col:
        raise ValueError(f"{p}: expected date/date-like and streamflow columns.")

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df[date_col], errors="coerce").dt.floor("D"),
            col_name: pd.to_numeric(df[value_col], errors="coerce"),
        }
    ).dropna(subset=["date"])
    out = out.groupby("date", as_index=False)[col_name].mean()
    return out


def main() -> int:
    args = parse_args()
    inputs: Dict[str, str] = {
        "1.2": args.v12,
        "2.0": args.v20,
        "2.1": args.v21,
        "3.0": args.v30,
    }

    merged: Optional[pd.DataFrame] = None
    for version, path in inputs.items():
        col = VERSION_TO_COL[version]
        series = load_series(path, col)
        if series is None:
            continue
        merged = series if merged is None else merged.merge(series, on="date", how="outer")

    if merged is None:
        raise RuntimeError("No valid inputs were provided.")

    merged = merged.sort_values("date")
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_csv, index=False)
    print(f"[OK] wrote {out_csv} ({len(merged)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
