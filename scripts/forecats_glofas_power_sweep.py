#!/usr/bin/env python3
"""
Fast sweep over GloFAS lead-time weighting powers using an existing cache directory.

This avoids re-opening GRIBs by reusing the per-issue-date .npz caches produced by
scripts/forecats_build_glofas_weighted.py (which store discharge_cms per lead/member/target_date).

Output:
- CSV of power -> error metrics vs an "old/truth" wide forecast file (assumed log1p scale by default).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def parse_issue_date_from_cache_name(name: str) -> Optional[str]:
    m = re.match(r"^issue_date=(\d{4}-\d{2}-\d{2})\.npz$", name)
    return m.group(1) if m else None


def load_cache_dir(cache_dir: Path) -> pd.DataFrame:
    dfs: List[pd.DataFrame] = []
    for p in sorted(cache_dir.iterdir()):
        if p.suffix != ".npz":
            continue
        z = np.load(p, allow_pickle=True)
        dfs.append(
            pd.DataFrame(
                {
                    "issue_date": z["issue_date"].astype(str),
                    "target_date": z["target_date"].astype(str),
                    "lead_time_h": z["lead_time_h"].astype(int),
                    "member": z["member"].astype(int),
                    "discharge_cms": z["discharge_cms"].astype("float64"),
                }
            )
        )
    if not dfs:
        raise SystemExit(f"No .npz files found in cache_dir={cache_dir}")
    return pd.concat(dfs, ignore_index=True)


def load_old(old_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(old_csv)
    df["target_date"] = pd.to_datetime(df["target_date"]).dt.strftime("%Y-%m-%d")
    # rename digit cols to member_XX
    ren: Dict[str, str] = {}
    for c in df.columns:
        if c.isdigit():
            ren[c] = f"member_{int(c):02d}"
    df = df.rename(columns=ren)
    cols = ["target_date"] + [f"member_{i:02d}" for i in range(51)]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise SystemExit(f"Old file missing columns: {missing[:5]} (n={len(missing)})")
    return df[cols]


def wide_from_long(df_long: pd.DataFrame, power: float) -> pd.DataFrame:
    df = df_long.copy()
    df["log1p_cms"] = np.log1p(df["discharge_cms"].astype("float64"))
    lead = df["lead_time_h"].astype("float64").replace(0.0, 1.0)
    df["w_raw"] = np.power(lead, power)
    denom = df.groupby(["target_date", "member"])["w_raw"].transform("sum")
    df["w"] = df["w_raw"] / denom
    df["w_log1p"] = df["w"] * df["log1p_cms"]
    out = (
        df.groupby(["target_date", "member"], as_index=False)["w_log1p"]
        .sum()
        .pivot(index="target_date", columns="member", values="w_log1p")
        .sort_index()
    )
    out = out.rename(columns={int(c): f"member_{int(c):02d}" for c in out.columns})
    out = out.reset_index().rename(columns={"index": "target_date"})
    return out


def metrics(old: pd.DataFrame, new: pd.DataFrame) -> Dict[str, float]:
    # Compare on log1p scale; both inputs are log1p
    cols = [c for c in old.columns if c.startswith("member_")]
    m = old.merge(new, on="target_date", suffixes=("_old", "_new"), how="inner")
    if len(m) == 0:
        return {"n_dates": 0, "rmse": float("nan"), "mae": float("nan"), "corr_mean": float("nan")}
    a = m[[c + "_old" for c in cols]].to_numpy(float)
    b = m[[c + "_new" for c in cols]].to_numpy(float)
    mask = np.isfinite(a) & np.isfinite(b)
    rmse = float(np.sqrt(np.mean((a[mask] - b[mask]) ** 2))) if mask.any() else float("nan")
    mae = float(np.mean(np.abs(a[mask] - b[mask]))) if mask.any() else float("nan")
    am = np.nanmean(a, axis=1)
    bm = np.nanmean(b, axis=1)
    corr = float(np.corrcoef(am, bm)[0, 1]) if np.isfinite(am).sum() > 2 else float("nan")
    return {"n_dates": int(len(m)), "rmse": rmse, "mae": mae, "corr_mean": corr}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True, type=Path)
    ap.add_argument("--old-csv", required=True, type=Path)
    ap.add_argument("--old-scale", default="log1p_cms", choices=["log1p_cms"])
    ap.add_argument("--date-start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--date-end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--powers", required=True, help="Comma-separated list, e.g. -0.5,-1.0,-1.5")
    ap.add_argument("--out-csv", required=True, type=Path)
    args = ap.parse_args()

    df_long = load_cache_dir(args.cache_dir)
    df_long = df_long[(df_long["target_date"] >= args.date_start) & (df_long["target_date"] <= args.date_end)].copy()
    old = load_old(args.old_csv)
    old = old[(old["target_date"] >= args.date_start) & (old["target_date"] <= args.date_end)].copy()

    powers = [float(x.strip()) for x in args.powers.split(",") if x.strip()]
    rows = []
    for p in powers:
        new = wide_from_long(df_long, power=p)
        rows.append({"power": p, **metrics(old, new)})

    out = pd.DataFrame(rows).sort_values("rmse")
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out_csv, index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

