#!/usr/bin/env python3
"""Audit continuity, missing dates, and NaNs for retrospective point-series CSV files."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd


@dataclass
class AuditRow:
    label: str
    path: str
    exists: bool
    rows_raw: int
    date_col: str
    value_col: str
    start_date: str
    end_date: str
    expected_start: str
    expected_end: str
    daily_rows: int
    expected_days: int
    missing_days: int
    subdaily_extra_rows: int
    nan_values: int


DATE_COL_CANDIDATES = ("date", "Date", "datetime_utc", "datetime", "time")
VALUE_COL_CANDIDATES = ("streamflow_cms", "streamflow", "value", "discharge_cms")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit NWM retrospective point-series continuity.")
    p.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="CSV paths to audit.",
    )
    p.add_argument(
        "--labels",
        nargs="*",
        default=None,
        help="Optional labels aligned with --inputs. Defaults to file stem.",
    )
    p.add_argument("--expected-start", default="", help="Optional expected start date YYYY-MM-DD.")
    p.add_argument("--expected-end", default="", help="Optional expected end date YYYY-MM-DD.")
    p.add_argument(
        "--out-summary-csv",
        required=True,
        help="Summary CSV output path.",
    )
    p.add_argument(
        "--out-missing-dir",
        required=True,
        help="Directory where per-series missing date CSV files are written.",
    )
    p.add_argument(
        "--out-summary-json",
        default="",
        help="Optional summary JSON output path.",
    )
    return p.parse_args()


def detect_columns(df: pd.DataFrame) -> Tuple[str, str]:
    date_col = ""
    value_col = ""
    for c in DATE_COL_CANDIDATES:
        if c in df.columns:
            date_col = c
            break
    for c in VALUE_COL_CANDIDATES:
        if c in df.columns:
            value_col = c
            break
    if not date_col:
        raise ValueError(f"No date column found. Expected one of {DATE_COL_CANDIDATES}")
    if not value_col:
        raise ValueError(f"No value column found. Expected one of {VALUE_COL_CANDIDATES}")
    return date_col, value_col


def audit_single(
    label: str,
    path: Path,
    expected_start: Optional[str],
    expected_end: Optional[str],
    missing_dir: Path,
) -> AuditRow:
    if not path.exists():
        return AuditRow(
            label=label,
            path=str(path),
            exists=False,
            rows_raw=0,
            date_col="",
            value_col="",
            start_date="",
            end_date="",
            expected_start=expected_start or "",
            expected_end=expected_end or "",
            daily_rows=0,
            expected_days=0,
            missing_days=0,
            subdaily_extra_rows=0,
            nan_values=0,
        )

    df = pd.read_csv(path)
    date_col, value_col = detect_columns(df)
    dt = pd.to_datetime(df[date_col], errors="coerce")
    vals = pd.to_numeric(df[value_col], errors="coerce")
    work = pd.DataFrame({"date": dt.dt.floor("D"), "value": vals})
    work = work.dropna(subset=["date"]).sort_values("date")

    if work.empty:
        raise ValueError(f"No valid date rows after parsing in {path}")

    start = pd.Timestamp(expected_start) if expected_start else work["date"].iloc[0]
    end = pd.Timestamp(expected_end) if expected_end else work["date"].iloc[-1]
    expected_idx = pd.date_range(start, end, freq="D")

    grouped = work.groupby("date", as_index=False)["value"].mean()
    present_idx = pd.DatetimeIndex(grouped["date"])
    missing_idx = expected_idx.difference(present_idx)
    subdaily_extra_rows = int(len(work) - len(grouped))
    nan_values = int(work["value"].isna().sum())

    missing_out = missing_dir / f"{label}_missing_dates.csv"
    pd.DataFrame({"missing_date": missing_idx}).to_csv(missing_out, index=False)

    return AuditRow(
        label=label,
        path=str(path),
        exists=True,
        rows_raw=int(len(df)),
        date_col=date_col,
        value_col=value_col,
        start_date=str(grouped["date"].iloc[0].date()),
        end_date=str(grouped["date"].iloc[-1].date()),
        expected_start=str(start.date()),
        expected_end=str(end.date()),
        daily_rows=int(len(grouped)),
        expected_days=int(len(expected_idx)),
        missing_days=int(len(missing_idx)),
        subdaily_extra_rows=subdaily_extra_rows,
        nan_values=nan_values,
    )


def main() -> int:
    args = parse_args()
    paths = [Path(p) for p in args.inputs]
    labels = args.labels or [p.stem for p in paths]
    if len(labels) != len(paths):
        raise ValueError("Length of --labels must match --inputs when provided.")

    summary_path = Path(args.out_summary_csv)
    missing_dir = Path(args.out_missing_dir)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    missing_dir.mkdir(parents=True, exist_ok=True)

    rows: List[AuditRow] = []
    for label, path in zip(labels, paths):
        row = audit_single(
            label=label,
            path=path,
            expected_start=args.expected_start or None,
            expected_end=args.expected_end or None,
            missing_dir=missing_dir,
        )
        rows.append(row)

    out_df = pd.DataFrame([r.__dict__ for r in rows])
    out_df.to_csv(summary_path, index=False)
    print(f"[OK] wrote {summary_path}")

    if args.out_summary_json:
        payload = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "rows": [r.__dict__ for r in rows],
        }
        out_json = Path(args.out_summary_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(payload, indent=2))
        print(f"[OK] wrote {out_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
