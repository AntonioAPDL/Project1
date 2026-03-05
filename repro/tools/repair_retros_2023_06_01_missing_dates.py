#!/usr/bin/env python3
"""Repair calendar gaps in retros_2023-06-01.csv using authoritative local sources.

Target file schema (log1p cms):
  Date, USGS, NWS3.0, GloFAS

Backfill sources:
  - USGS: usgs_daily_avg.csv (Daily_Avg_Log_Streamflow)
  - NWS3.0: nws_daily_avg.csv (Daily_Avg_Log_Streamflow)
  - GloFAS: data/glofas_historical_consolidated_point/point_series/
            hist_v40_lisflood_cons_bigtrees.csv (discharge_cms -> log1p)
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--retros-csv", default="retros_2023-06-01.csv")
    p.add_argument("--usgs-csv", default="usgs_daily_avg.csv")
    p.add_argument("--nws-csv", default="nws_daily_avg.csv")
    p.add_argument(
        "--glofas-v40-csv",
        default="data/glofas_historical_consolidated_point/point_series/hist_v40_lisflood_cons_bigtrees.csv",
    )
    p.add_argument("--out-csv", default=None, help="Default: <retros-csv>.repaired.csv")
    p.add_argument("--inplace", action="store_true", help="Overwrite --retros-csv (creates .bak first).")
    p.add_argument("--strict", action="store_true", help="Fail if GloFAS v40 mismatch on overlap.")
    return p.parse_args()


def _load_log_daily(path: Path, date_col: str, value_col: str, out_col: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=[date_col])
    return (
        df[[date_col, value_col]]
        .rename(columns={date_col: "Date", value_col: out_col})
        .dropna(subset=["Date"])
        .assign(Date=lambda x: pd.to_datetime(x["Date"]).dt.normalize())
    )


def main() -> None:
    args = parse_args()
    retros_path = Path(args.retros_csv)
    if not retros_path.exists():
        raise FileNotFoundError(f"Missing retros file: {retros_path}")

    out_path = Path(args.out_csv) if args.out_csv else retros_path.with_suffix(".repaired.csv")

    retro = pd.read_csv(retros_path, parse_dates=["Date"]).sort_values("Date")
    required_cols = {"Date", "USGS", "NWS3.0", "GloFAS"}
    if not required_cols.issubset(retro.columns):
        raise ValueError(f"{retros_path} missing required columns: {sorted(required_cols - set(retro.columns))}")

    full = pd.date_range(retro["Date"].min(), retro["Date"].max(), freq="D")
    missing = full.difference(pd.DatetimeIndex(retro["Date"]))
    if len(missing) == 0:
        print("[OK] No missing dates found; nothing to repair.")
        return

    usgs = _load_log_daily(Path(args.usgs_csv), "Date", "Daily_Avg_Log_Streamflow", "USGS")
    nws = _load_log_daily(Path(args.nws_csv), "Date", "Daily_Avg_Log_Streamflow", "NWS3.0")

    g_v40_raw = pd.read_csv(Path(args.glofas_v40_csv), parse_dates=["date"])
    g_v40 = (
        g_v40_raw[["date", "discharge_cms"]]
        .rename(columns={"date": "Date"})
        .assign(Date=lambda x: pd.to_datetime(x["Date"]).dt.normalize())
        .assign(GloFAS=lambda x: np.log(x["discharge_cms"] + 1.0))
        [["Date", "GloFAS"]]
    )

    # Consistency check: legacy GloFAS and v40 should match exactly on overlap.
    overlap = retro[["Date", "GloFAS"]].merge(g_v40, on="Date", how="inner", suffixes=("_retro", "_v40"))
    if len(overlap) > 0:
        max_abs = float(np.max(np.abs(overlap["GloFAS_retro"] - overlap["GloFAS_v40"])))
        print(f"[INFO] GloFAS overlap check vs v40: n={len(overlap)} max_abs_diff={max_abs:.12g}")
        if args.strict and max_abs > 1e-10:
            raise RuntimeError(f"Strict mode: GloFAS overlap mismatch too large ({max_abs})")

    patch_dates = pd.DataFrame({"Date": pd.to_datetime(missing)})
    patch = patch_dates.merge(usgs, on="Date", how="left").merge(nws, on="Date", how="left").merge(g_v40, on="Date", how="left")
    missing_cols = [c for c in ["USGS", "NWS3.0", "GloFAS"] if patch[c].isna().any()]
    if missing_cols:
        bad = patch[patch[missing_cols].isna().any(axis=1)]
        raise RuntimeError(f"Unable to backfill all missing dates; missing columns={missing_cols}; rows={bad.to_dict(orient='records')}")

    repaired = (
        pd.concat([retro, patch], ignore_index=True)
        .drop_duplicates(subset=["Date"], keep="first")
        .sort_values("Date")
        .reset_index(drop=True)
    )

    # Post-check
    full2 = pd.date_range(repaired["Date"].min(), repaired["Date"].max(), freq="D")
    miss2 = full2.difference(pd.DatetimeIndex(repaired["Date"]))
    if len(miss2) != 0:
        raise RuntimeError(f"Repair failed; still missing dates: {[d.date().isoformat() for d in miss2]}")

    repaired.to_csv(out_path, index=False)
    print(f"[OK] wrote repaired file: {out_path}")
    print(f"[INFO] repaired rows: {len(repaired)} (added {len(patch)})")
    print("[INFO] filled dates:", ",".join(d.date().isoformat() for d in missing))

    if args.inplace:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = retros_path.with_suffix(f".backup_{ts}.csv")
        retros_path.replace(backup)
        out_path.replace(retros_path)
        print(f"[OK] inplace update complete. backup={backup} updated={retros_path}")


if __name__ == "__main__":
    main()
