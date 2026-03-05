#!/usr/bin/env python3
"""
Build a synthetic NWS/NWM retrospective from forecast ensembles in results.pkl.

Compatibility target:
- Mirrors the "latest" NWS extraction semantics used by scripts/forecats_extract_nws_batch.py
  for (target_date, target_hour, ensemble) latest selection.
- Aggregates in a configurable transform space, then back-transforms to raw cms.

Definition:
1) Parse forecast values from medium-range products in results.pkl.
2) For each (target_date, target_hour, ensemble), keep the latest issue_dt.
3) Aggregate across ensemble members at each (target_date, target_hour).
4) Aggregate across target_hour to produce a daily synthetic retrospective.

Output CSV:
  date, discharge_cms
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from flow_scale import TRANSFORM_SCALES, forward_transform_cms, inverse_transform_to_cms


ISSUE_DATE_RE = re.compile(r"^(?:nwm|nwm2|nwmv3|nwmv2)\.(\d{8})/")
ISSUE_HOUR_RE = re.compile(r"\.t(\d{2})z\.")
LEAD_RE = re.compile(r"\.f(\d{1,3})\.")


def parse_key(key: str, parse_issue_hour: bool) -> Optional[Tuple[str, int, int, int, str]]:
    m = ISSUE_DATE_RE.search(key)
    if not m:
        return None

    yyyymmdd = m.group(1)
    issue_date = datetime.strptime(yyyymmdd, "%Y%m%d").date().isoformat()
    parts = key.split("/")
    if len(parts) < 3:
        return None

    product = parts[1]
    if "mem" in product:
        try:
            ensemble_number = int(product.split("mem", 1)[1])
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

    return issue_date, issue_hour, ensemble_number, lead_time_h, product


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-meta", type=Path, required=True)
    ap.add_argument(
        "--product-prefix",
        default="medium_range",
        help="Include products where parts[1] starts with this prefix (default: medium_range).",
    )
    parse_group = ap.add_mutually_exclusive_group()
    parse_group.add_argument(
        "--parse-issue-hour",
        dest="parse_issue_hour",
        action="store_true",
        help="Parse issue hour from filename (.tHHz).",
    )
    parse_group.add_argument(
        "--no-parse-issue-hour",
        dest="parse_issue_hour",
        action="store_false",
        help="Force issue hour to 00 for all records (matches batch config defaults).",
    )
    ap.set_defaults(parse_issue_hour=False)
    ap.add_argument(
        "--aggregation-space",
        choices=list(TRANSFORM_SCALES),
        default="log1p_cms",
        help="Space used for ensemble/hour averaging (default: log1p_cms).",
    )
    ap.add_argument(
        "--strict-one-step",
        action="store_true",
        help="Use only one-step lead forecasts for synthetic retrospective construction.",
    )
    ap.add_argument(
        "--one-step-lead-hours",
        type=int,
        default=1,
        help="Lead hour used when --strict-one-step is enabled (default: 1).",
    )
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.verbose:
        print(f"[INFO] loading {args.pkl} ...")
    with args.pkl.open("rb") as f:
        data = pickle.load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected dict in pickle, got {type(data)}")

    rows = []
    parsed = 0
    kept = 0
    for k, v in data.items():
        parsed += 1
        parsed_key = parse_key(k, parse_issue_hour=args.parse_issue_hour)
        if parsed_key is None:
            continue
        issue_date_iso, issue_hour, ens, lead_h, product = parsed_key
        if not product.startswith(args.product_prefix):
            continue
        try:
            val = float(v)
        except Exception:
            continue
        issue_d = datetime.strptime(issue_date_iso, "%Y-%m-%d")
        issue_dt = issue_d + timedelta(hours=int(issue_hour))
        target_dt = issue_dt + timedelta(hours=int(lead_h))
        rows.append(
            (
                issue_dt,
                target_dt.date().isoformat(),
                int(target_dt.hour),
                int(ens),
                int(lead_h),
                float(val),
                product,
            )
        )
        kept += 1

    if not rows:
        raise SystemExit("No rows parsed from pickle for requested product-prefix.")

    df = pd.DataFrame(
        rows,
        columns=["issue_dt", "target_date", "target_hour", "ensemble", "lead_time_h", "value_cms", "product"],
    )
    df = df[np.isfinite(df["value_cms"].to_numpy())].copy()
    df["work_value"] = forward_transform_cms(df["value_cms"].astype("float64"), args.aggregation_space)

    if args.strict_one_step:
        df = df[df["lead_time_h"] == int(args.one_step_lead_hours)].copy()
        if df.empty:
            raise SystemExit(
                "No rows available after strict one-step filter. "
                "Check --one-step-lead-hours or parsing settings."
            )

    # Latest issue per (target_date, target_hour, ensemble)
    issue_max = df.groupby(["target_date", "target_hour", "ensemble"])["issue_dt"].transform("max")
    df_latest = df[df["issue_dt"] == issue_max].copy()

    # Aggregate across ensembles, then daily across target_hour, in transform space.
    hourly = (
        df_latest.groupby(["target_date", "target_hour"], as_index=False)
        .agg(mean_work_value=("work_value", "mean"), n_ensemble=("ensemble", "nunique"))
    )
    daily = (
        hourly.groupby("target_date", as_index=False)
        .agg(mean_work_value=("mean_work_value", "mean"), n_hour=("target_hour", "nunique"))
        .rename(columns={"target_date": "date"})
    )
    daily["discharge_cms"] = inverse_transform_to_cms(daily["mean_work_value"].astype("float64"), args.aggregation_space)
    daily["date"] = pd.to_datetime(daily["date"]).dt.date.astype(str)
    daily = daily.sort_values("date").reset_index(drop=True)

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    daily[["date", "discharge_cms"]].to_csv(args.out_csv, index=False)

    meta = {
        "pkl": str(args.pkl),
        "product_prefix": args.product_prefix,
        "parse_issue_hour": bool(args.parse_issue_hour),
        "aggregation_space": str(args.aggregation_space),
        "strict_one_step": bool(args.strict_one_step),
        "one_step_lead_hours": int(args.one_step_lead_hours),
        "parsed_keys": int(parsed),
        "kept_rows": int(kept),
        "rows_after_latest_select": int(len(df_latest)),
        "daily_rows": int(len(daily)),
        "coverage_start": daily["date"].iloc[0] if len(daily) else None,
        "coverage_end": daily["date"].iloc[-1] if len(daily) else None,
        "ensemble_min_per_hour": int(hourly["n_ensemble"].min()) if len(hourly) else None,
        "ensemble_max_per_hour": int(hourly["n_ensemble"].max()) if len(hourly) else None,
    }
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(meta, indent=2) + "\n")

    if args.verbose:
        print(f"[OK] wrote {args.out_csv} ({len(daily)} rows)")
        print(f"[OK] wrote {args.out_meta}")
        print(
            f"[INFO] coverage={meta['coverage_start']} to {meta['coverage_end']} "
            f"rows_after_latest_select={meta['rows_after_latest_select']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
