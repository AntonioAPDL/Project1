#!/usr/bin/env python3
"""
Build a *weighted* daily NWS/NWM medium-range forecast ensemble at a single point from `results.pkl`.

This script implements the weighting logic present in `Retro-Analysis.ipynb`, but as a
reusable CLI tool for the forecats bundle workflow.

Core logic (matches notebook intent):
- Parse `results.pkl` (a dict {path_key: value_at_point}).
- For each record, derive:
    issue_date (YYYY-MM-DD) from key prefix: nwm.YYYYMMDD/...
    ensemble_number from the path component containing "mem" (defaults to 1)
    lead_time_h from filename token "fXXX"
    (optional) issue_cycle_hour from filename token "t00z"/"t12z"
- Compute:
    target_time = issue_datetime + lead_time_h hours
    target_date = date(target_time)
    target_hour = hour(target_time)   (to preserve the notebook's (Target_Time, Ensemble) grouping)
- Filter to:
    issue_date <= cutoff_date
    forecast_start_date <= target_date <= forecast_end_date

Weighting schemes

This tool supports two weighting schemes so we can compare "notebook-mode" vs
"paper-mode" in a controlled way.

1) notebook-mode (default)
   Weight within each (target_date, target_hour, ensemble) by lead time:
     w_raw = 1 / (lead_time_h ** exponent[ensemble])
   Normalize within the group and compute a weighted average on transformed(cms).

2) paper-mode
   Weight within each (target_date, target_hour, ensemble) by "age" r (days before
   cutoff T), matching the paper's intent that forecasts issued closer to T receive
   higher weights:
     r_days = cutoff_date - issue_date
     w_raw  = 1 / (r_days + 1) ** alpha
   Normalize within the group and compute a weighted average on transformed(cms).

In both modes, we then compute a simple (unweighted) daily average per (target_date, ensemble)
by averaging over target_hour.

Outputs are written in raw cms by inverting from the working transform scale.

Important:
- `results.pkl` keys include multiple run cycles (t00z/t12z). The original notebook
  sometimes ignored the cycle hour; this script supports both behaviors:
    --parse-issue-hour (true)  : parse t??z from filename
    --parse-issue-hour (false) : treat issue time as 00Z (compat mode)
"""

from __future__ import annotations

import argparse
import pickle
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from flow_scale import TRANSFORM_SCALES, forward_transform_cms, inverse_transform_to_cms


# NOTE: use raw strings with single backslashes for regex escapes.
# These keys look like:
#   nwm.YYYYMMDD/medium_range_mem3/nwm.t12z.medium_range.channel_rt_1.f003.conus.nc
ISSUE_DATE_RE = re.compile(r"^(?:nwm|nwm2|nwmv3|nwmv2)\.(\d{8})/")
LEAD_RE = re.compile(r"\.f(\d{1,3})\.")
ISSUE_HOUR_RE = re.compile(r"\.t(\d{2})z\.")


def parse_exponents(spec: str) -> Dict[int, float]:
    """
    Parse exponents from "1=0,2=0.3,3=0.6" into {1:0.0, 2:0.3, ...}.
    """
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
    """
    Returns (issue_date_iso, issue_hour, ensemble_number, lead_time_h).
    issue_hour is 0..23.
    """
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

    # lead time from filename
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", required=True, type=Path)
    ap.add_argument("--cutoff-date", required=True, type=str, help="YYYY-MM-DD")
    ap.add_argument("--forecast-start-date", required=True, type=str, help="YYYY-MM-DD")
    ap.add_argument("--forecast-end-date", required=True, type=str, help="YYYY-MM-DD")
    ap.add_argument(
        "--weighting-scheme",
        default="latest",
        choices=["notebook", "paper", "latest"],
        help=(
            "Weighting scheme: "
            "'notebook' (lead-time exponents), "
            "'paper' (age-based alpha), or "
            "'latest' (alpha->inf: pick the most recent issue_datetime per (target_date, target_hour, ensemble))."
        ),
    )
    ap.add_argument(
        "--exponents",
        default="",
        type=str,
        help='Notebook-mode: e.g. "1=0,2=0.3,3=0.6,4=0.9,5=1.2,6=1.5,7=1.8" (ignored in paper-mode).',
    )
    ap.add_argument("--alpha", default=1.0, type=float, help="Paper-mode exponent alpha (weights ~ (r_days+1)^-alpha).")
    ap.add_argument("--parse-issue-hour", action="store_true")
    ap.add_argument("--issue-lookback-days", type=int, default=40, help="Skip issue_dates older than cutoff-lookback (speed).")
    ap.add_argument(
        "--aggregation-scale",
        default="log1p_cms",
        choices=list(TRANSFORM_SCALES),
        help="Working scale for weighting/hourly->daily averaging.",
    )
    ap.add_argument("--out-csv", required=True, type=Path)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.out_csv.exists() and not args.overwrite:
        if args.verbose:
            print(f"[SKIP] out exists: {args.out_csv}")
        return 0

    cutoff = datetime.strptime(args.cutoff_date, "%Y-%m-%d").date()
    forecast_start = datetime.strptime(args.forecast_start_date, "%Y-%m-%d").date()
    forecast_end = datetime.strptime(args.forecast_end_date, "%Y-%m-%d").date()
    if forecast_start > forecast_end:
        raise SystemExit("forecast-start-date must be <= forecast-end-date")

    exponents: Dict[int, float] = {}
    if args.weighting_scheme == "notebook":
        exponents = parse_exponents(args.exponents)
        if not exponents:
            raise SystemExit("notebook-mode requires --exponents (parsed empty; check format)")
    elif args.weighting_scheme == "paper":
        # Allow alpha <= 0 for sensitivity experiments:
        # - alpha = 0   -> uniform weights across issue_dates
        # - alpha < 0   -> older issue_dates receive *more* weight
        # These are not "paper default" but are useful for diagnostics.
        pass
    elif args.weighting_scheme == "latest":
        # Equivalent to alpha -> +inf in paper-mode.
        pass
    else:
        raise SystemExit(f"Unknown --weighting-scheme: {args.weighting_scheme}")

    issue_min = cutoff - timedelta(days=int(args.issue_lookback_days))

    if args.verbose:
        print(
            f"[INFO] weighting_scheme={args.weighting_scheme} alpha={args.alpha} "
            f"aggregation_scale={args.aggregation_scale} parse_issue_hour={args.parse_issue_hour}"
        )
        if args.weighting_scheme == "notebook":
            print(f"[INFO] exponents: {args.exponents}")
        print(f"[INFO] loading {args.pkl} ...")
    with args.pkl.open("rb") as f:
        data = pickle.load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected dict in pickle, got {type(data)}")

    rows: List[Tuple[str, int, str, int, int, int, float]] = []
    # (issue_date, issue_hour, target_date, target_hour, ensemble, lead_time_h, value_cms)
    kept = 0
    parsed = 0
    for k, v in data.items():
        parsed += 1
        parsed_key = parse_key(k, parse_issue_hour=args.parse_issue_hour)
        if parsed_key is None:
            continue
        issue_date_iso, issue_hour, ens, lead_h = parsed_key

        # Fast date window skip before doing datetime arithmetic
        issue_d = datetime.strptime(issue_date_iso, "%Y-%m-%d").date()
        if issue_d < issue_min or issue_d > cutoff:
            continue
        if args.weighting_scheme == "notebook" and ens not in exponents:
            continue

        issue_dt = datetime(issue_d.year, issue_d.month, issue_d.day, issue_hour, 0, 0)
        target_dt = issue_dt + timedelta(hours=int(lead_h))
        target_date = target_dt.date()
        if target_date < forecast_start or target_date > forecast_end:
            continue

        # Values should be float-like; keep as float.
        try:
            val = float(v)
        except Exception:
            continue

        rows.append((issue_date_iso, int(issue_hour), target_date.isoformat(), int(target_dt.hour), int(ens), int(lead_h), val))
        kept += 1

    if not rows:
        raise SystemExit("No rows matched the requested window. Check dates/exponents/parse settings.")

    df = pd.DataFrame(
        rows,
        columns=["issue_date", "issue_hour", "target_date", "target_hour", "ensemble", "lead_time_h", "value_cms"],
    )

    # Weighting on configured transform scale.
    df["work_value"] = forward_transform_cms(df["value_cms"].astype("float64"), args.aggregation_scale)
    if args.weighting_scheme == "notebook":
        lead = df["lead_time_h"].astype("float64").replace(0.0, 1.0)
        expo = df["ensemble"].map(lambda e: exponents[int(e)]).astype("float64")
        df["w_raw"] = 1.0 / np.power(lead, expo)
    elif args.weighting_scheme == "paper":
        issue_dt = pd.to_datetime(df["issue_date"])
        r_days = (pd.Timestamp(cutoff) - issue_dt).dt.days.astype("float64")
        df["w_raw"] = 1.0 / np.power(r_days + 1.0, float(args.alpha))
    elif args.weighting_scheme == "latest":
        # Equivalent to alpha -> +inf:
        # for each (target_date, target_hour, ensemble), keep only the most recent issue_datetime.
        issue_dt = pd.to_datetime(df["issue_date"]) + pd.to_timedelta(df["issue_hour"].astype(int), unit="h")
        issue_ts = pd.Series(issue_dt.values, index=df.index)
        issue_max = issue_ts.groupby([df["target_date"], df["target_hour"], df["ensemble"]]).transform("max")
        keep = (issue_ts == issue_max) & np.isfinite(df["work_value"].to_numpy())
        df = df.loc[keep].copy()
        df["w_raw"] = 1.0
    else:
        raise SystemExit(f"Unknown weighting_scheme: {args.weighting_scheme}")

    denom = df.groupby(["target_date", "target_hour", "ensemble"])["w_raw"].transform("sum")
    df["w"] = df["w_raw"] / denom
    df["w_work"] = df["w"] * df["work_value"]

    # Weighted average per target_time (date+hour) + ensemble
    w_by_time = (
        df.groupby(["target_date", "target_hour", "ensemble"], as_index=False)["w_work"]
        .sum()
        .rename(columns={"w_work": "weighted_work"})
    )

    # Daily average across target_hour
    daily = (
        w_by_time.groupby(["target_date", "ensemble"], as_index=False)["weighted_work"]
        .mean()
        .rename(columns={"weighted_work": "daily_weighted_work"})
    )

    daily["value_cms"] = inverse_transform_to_cms(
        daily["daily_weighted_work"].astype("float64"),
        args.aggregation_scale,
    )

    wide = daily.pivot(index="target_date", columns="ensemble", values="value_cms").sort_index()

    # Full date coverage
    full_idx = pd.date_range(start=forecast_start, end=forecast_end, freq="D").strftime("%Y-%m-%d")
    wide = wide.reindex(full_idx)

    # Column naming: member_01..member_07
    wide = wide.rename(columns={int(c): f"member_{int(c):02d}" for c in wide.columns})
    wide.index.name = "target_date"

    out_df = wide.reset_index()
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out_csv, index=False)

    if args.verbose:
        print(f"[OK] wrote {args.out_csv} rows={len(out_df)} cols={len(out_df.columns)} parsed_keys={parsed} kept_rows={kept}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
