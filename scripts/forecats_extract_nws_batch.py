#!/usr/bin/env python3
"""
Extract per-cutoff-date NWS/NWM forecast ensembles from `results.pkl`.

Writes, for each cutoff_date, a small CSV:

  out_root/
    cutoff_date=YYYY-MM-DD/
      nws_members.csv   # target_date + member_01..member_07 (cms)

This is designed for high-throughput batch rendering:
- Load and parse `results.pkl` once per process.
- Loop over many cutoff dates and write per-date forecast matrices.

Semantics match `scripts/forecats_build_nws_weighted.py`:
- Filter to issue_date <= cutoff_date (no peeking).
- For each (target_date, target_hour, ensemble):
    - latest  : pick the most recent issue_datetime
    - paper   : age weights ~(r_days+1)^-alpha on log1p(cms)
    - notebook: lead-time weights ~1/(lead_time_h^exponent[ensemble]) on log1p(cms)
- Then average across target_hour to daily (simple mean).
- Store outputs in raw cms (m^3/s).

Performance notes:
- This implementation uses a single parsed DataFrame covering the full requested
  (issue_date, target_date) span, and then filters per cutoff_date.
- For very large `results.pkl`, run this in shards (use multiple tmux sessions).
"""

from __future__ import annotations

import argparse
import pickle
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


ISSUE_DATE_RE = re.compile(r"^(?:nwm|nwm2|nwmv3|nwmv2)\.(\d{8})/")
LEAD_RE = re.compile(r"\.f(\d{1,3})\.")
ISSUE_HOUR_RE = re.compile(r"\.t(\d{2})z\.")


def parse_exponents(spec: str) -> Dict[int, float]:
    out: Dict[int, float] = {}
    if not spec:
        return out
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"Bad exponent chunk: {chunk!r} (expected k=v)")
        k, v = chunk.split("=", 1)
        out[int(k.strip())] = float(v.strip())
    return out


def parse_key(key: str, parse_issue_hour: bool) -> Optional[Tuple[str, int, int, int]]:
    m = ISSUE_DATE_RE.search(key)
    if not m:
        return None
    yyyymmdd = m.group(1)
    issue_date = datetime.strptime(yyyymmdd, "%Y%m%d").date().isoformat()

    parts = key.split("/")
    if len(parts) < 3:
        return None

    ensemble_part = parts[1]
    if "mem" in ensemble_part:
        try:
            ensemble_number = int(ensemble_part.split("mem", 1)[1])
        except Exception:
            return None
    else:
        ensemble_number = 1

    m_lead = LEAD_RE.search(parts[2])
    if not m_lead:
        return None
    lead_time_h = int(m_lead.group(1))

    issue_hour = 0
    if parse_issue_hour:
        m_h = ISSUE_HOUR_RE.search(parts[2])
        if m_h:
            issue_hour = int(m_h.group(1))

    return issue_date, issue_hour, ensemble_number, lead_time_h


def read_dates(path: Path) -> List[date]:
    out: List[date] = []
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(datetime.strptime(s, "%Y-%m-%d").date())
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", required=True, type=Path)
    ap.add_argument("--dates-file", required=True, type=Path, help="One cutoff date per line (YYYY-MM-DD).")
    ap.add_argument("--out-root", required=True, type=Path)
    ap.add_argument("--post-days", default=28, type=int)
    ap.add_argument("--parse-issue-hour", action="store_true")
    ap.add_argument("--issue-lookback-days", type=int, default=40)
    ap.add_argument(
        "--weighting-scheme",
        default="latest",
        choices=["latest", "paper", "notebook"],
    )
    ap.add_argument("--alpha", default=1.0, type=float)
    ap.add_argument("--exponents", default="", type=str, help='Notebook-mode: e.g. "1=0,2=0.3,...".')
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cutoff_dates = read_dates(args.dates_file)
    if not cutoff_dates:
        raise SystemExit("dates-file is empty")

    args.out_root.mkdir(parents=True, exist_ok=True)

    exponents: Dict[int, float] = {}
    if args.weighting_scheme == "notebook":
        exponents = parse_exponents(args.exponents)
        if not exponents:
            raise SystemExit("notebook weighting requires --exponents")

    # Global parse bounds to reduce memory:
    min_cutoff = min(cutoff_dates)
    max_cutoff = max(cutoff_dates)
    issue_min_global = min_cutoff - timedelta(days=int(args.issue_lookback_days))
    issue_max_global = max_cutoff
    target_min_global = min_cutoff + timedelta(days=1)
    target_max_global = max_cutoff + timedelta(days=int(args.post_days))

    if args.verbose:
        print(f"[INFO] loading {args.pkl} ...")
    with args.pkl.open("rb") as f:
        data = pickle.load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected dict in pickle, got {type(data)}")

    rows: List[Tuple[str, int, str, int, int, int, float]] = []
    parsed = 0
    kept = 0
    for k, v in data.items():
        parsed += 1
        parsed_key = parse_key(k, parse_issue_hour=args.parse_issue_hour)
        if parsed_key is None:
            continue
        issue_date_iso, issue_hour, ens, lead_h = parsed_key
        issue_d = datetime.strptime(issue_date_iso, "%Y-%m-%d").date()
        if issue_d < issue_min_global or issue_d > issue_max_global:
            continue
        if args.weighting_scheme == "notebook" and ens not in exponents:
            continue

        issue_dt = datetime(issue_d.year, issue_d.month, issue_d.day, int(issue_hour), 0, 0)
        target_dt = issue_dt + timedelta(hours=int(lead_h))
        target_d = target_dt.date()
        if target_d < target_min_global or target_d > target_max_global:
            continue

        try:
            val = float(v)
        except Exception:
            continue

        rows.append((issue_date_iso, int(issue_hour), target_d.isoformat(), int(target_dt.hour), int(ens), int(lead_h), val))
        kept += 1

    if not rows:
        raise SystemExit("No rows matched the global window. Check dates and input pickle.")

    df_all = pd.DataFrame(
        rows,
        columns=["issue_date", "issue_hour", "target_date", "target_hour", "ensemble", "lead_time_h", "value_cms"],
    )
    df_all["issue_dt"] = pd.to_datetime(df_all["issue_date"]) + pd.to_timedelta(df_all["issue_hour"].astype(int), unit="h")
    df_all["log1p_cms"] = np.log1p(df_all["value_cms"].astype("float64"))

    if args.verbose:
        print(f"[INFO] parsed_keys={parsed} kept_rows={kept} df_rows={len(df_all)}")

    n_ok = 0
    n_skip = 0

    for cutoff in cutoff_dates:
        out_dir = args.out_root / f"cutoff_date={cutoff.isoformat()}"
        out_path = out_dir / "nws_members.csv"
        if out_path.exists() and not args.overwrite:
            n_skip += 1
            continue

        forecast_start = cutoff + timedelta(days=1)
        forecast_end = cutoff + timedelta(days=int(args.post_days))
        issue_min = cutoff - timedelta(days=int(args.issue_lookback_days))

        df = df_all[
            (df_all["issue_dt"] <= pd.Timestamp(cutoff) + pd.Timedelta(hours=23))  # include whole cutoff day
            & (df_all["issue_dt"] >= pd.Timestamp(issue_min))
            & (df_all["target_date"] >= forecast_start.isoformat())
            & (df_all["target_date"] <= forecast_end.isoformat())
        ].copy()

        if df.empty:
            # Still write a full-index empty frame for downstream stability.
            full_idx = pd.date_range(start=forecast_start, end=forecast_end, freq="D").strftime("%Y-%m-%d")
            out_df = pd.DataFrame({"target_date": full_idx})
            out_dir.mkdir(parents=True, exist_ok=True)
            out_df.to_csv(out_path, index=False)
            n_ok += 1
            continue

        if args.weighting_scheme == "latest":
            issue_ts = pd.Series(df["issue_dt"].values, index=df.index)
            issue_max = issue_ts.groupby([df["target_date"], df["target_hour"], df["ensemble"]]).transform("max")
            keep = (issue_ts == issue_max) & np.isfinite(df["log1p_cms"].to_numpy())
            df = df.loc[keep].copy()
            df["w_raw"] = 1.0
        elif args.weighting_scheme == "paper":
            issue_d = pd.to_datetime(df["issue_date"])
            r_days = (pd.Timestamp(cutoff) - issue_d).dt.days.astype("float64")
            df["w_raw"] = 1.0 / np.power(r_days + 1.0, float(args.alpha))
        elif args.weighting_scheme == "notebook":
            lead = df["lead_time_h"].astype("float64").replace(0.0, 1.0)
            expo = df["ensemble"].map(lambda e: exponents[int(e)]).astype("float64")
            df["w_raw"] = 1.0 / np.power(lead, expo)
        else:
            raise SystemExit(f"Unknown weighting-scheme: {args.weighting_scheme}")

        denom = df.groupby(["target_date", "target_hour", "ensemble"])["w_raw"].transform("sum")
        df["w"] = df["w_raw"] / denom
        df["w_log1p"] = df["w"] * df["log1p_cms"]

        w_by_time = (
            df.groupby(["target_date", "target_hour", "ensemble"], as_index=False)["w_log1p"]
            .sum()
            .rename(columns={"w_log1p": "weighted_log1p"})
        )

        daily = (
            w_by_time.groupby(["target_date", "ensemble"], as_index=False)["weighted_log1p"]
            .mean()
            .rename(columns={"weighted_log1p": "daily_weighted_log1p"})
        )
        daily["value_cms"] = np.expm1(daily["daily_weighted_log1p"].astype("float64"))

        wide = daily.pivot(index="target_date", columns="ensemble", values="value_cms").sort_index()
        full_idx = pd.date_range(start=forecast_start, end=forecast_end, freq="D").strftime("%Y-%m-%d")
        wide = wide.reindex(full_idx)
        wide = wide.rename(columns={int(c): f"member_{int(c):02d}" for c in wide.columns})
        wide.index.name = "target_date"

        out_dir.mkdir(parents=True, exist_ok=True)
        wide.reset_index().to_csv(out_path, index=False)
        n_ok += 1

        if args.verbose and (n_ok % 50 == 0):
            print(f"[OK] wrote {n_ok} cutoffs ... (latest {cutoff.isoformat()})")

    if args.verbose:
        print(f"[DONE] ok={n_ok} skipped={n_skip} out_root={args.out_root}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

