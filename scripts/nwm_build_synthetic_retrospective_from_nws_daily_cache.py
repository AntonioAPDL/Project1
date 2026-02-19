#!/usr/bin/env python3
"""Build a strict day+1 synthetic NWS retrospective from daily cache files.

Definition:
  For each cutoff date c, read:
    forecast_cache/nws/cutoff_date=YYYY-MM-DD/nws_members.csv
  Keep only target_date == c + 1 day (strict one-step in daily space),
  then average across available member_* columns.

This ensures synthetic values are directly comparable to the plotted
NWS daily forecast objects in the forecats pipeline.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List

import pandas as pd


@dataclass
class CutoffResult:
    cutoff_date: date
    target_date: date | None
    value: float | None
    members_used: int
    status: str
    note: str = ""


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Build strict day+1 synthetic retrospective from "
            "daily NWS forecast cache files."
        )
    )
    p.add_argument(
        "--nws-cache-root",
        default=(
            "data/forecats_cache/site=11160500/"
            "run_id=latest/forecast_cache/nws"
        ),
        help="Root directory containing cutoff_date=*/nws_members.csv files.",
    )
    p.add_argument(
        "--out-csv",
        default=(
            "data/nwm_synthetic_retrospective/point_series/"
            "nws_synthetic_retro_ensemble_mean_daily.csv"
        ),
        help="Output CSV path (columns: date, discharge_cms).",
    )
    p.add_argument(
        "--out-meta",
        default=(
            "data/nwm_synthetic_retrospective/point_series/"
            "nws_synthetic_retro_ensemble_mean_daily.meta.json"
        ),
        help="Output metadata JSON path.",
    )
    p.add_argument(
        "--out-diagnostics-csv",
        default=(
            "data/nwm_synthetic_retrospective/point_series/"
            "nws_synthetic_retro_day1_diagnostics.csv"
        ),
        help="Per-cutoff diagnostics CSV path.",
    )
    p.add_argument(
        "--value-col",
        default="discharge_cms",
        help="Value column name in output CSV.",
    )
    p.add_argument(
        "--start-date",
        default=None,
        help="Optional inclusive date filter (YYYY-MM-DD) on output date.",
    )
    p.add_argument(
        "--end-date",
        default=None,
        help="Optional inclusive date filter (YYYY-MM-DD) on output date.",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress.",
    )
    return p.parse_args()


def _iter_cutoff_files(root: Path) -> Iterable[Path]:
    return sorted(root.glob("cutoff_date=*/nws_members.csv"))


def _cutoff_from_path(p: Path) -> date:
    token = p.parent.name
    # token looks like cutoff_date=YYYY-MM-DD
    return date.fromisoformat(token.split("=", 1)[1])


def _member_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if c.startswith("member_")]


def _process_cutoff_file(p: Path) -> CutoffResult:
    cutoff = _cutoff_from_path(p)
    expected_target = cutoff + timedelta(days=1)
    try:
        df = pd.read_csv(p)
    except Exception as exc:  # pragma: no cover
        return CutoffResult(
            cutoff_date=cutoff,
            target_date=None,
            value=None,
            members_used=0,
            status="error_read",
            note=str(exc),
        )

    if "target_date" not in df.columns:
        return CutoffResult(
            cutoff_date=cutoff,
            target_date=None,
            value=None,
            members_used=0,
            status="missing_target_date",
            note="target_date column not found",
        )

    mcols = _member_columns(df)
    if not mcols:
        return CutoffResult(
            cutoff_date=cutoff,
            target_date=None,
            value=None,
            members_used=0,
            status="missing_member_columns",
            note="no member_* columns found",
        )

    df = df.copy()
    df["target_date"] = pd.to_datetime(df["target_date"], errors="coerce").dt.date
    row = df.loc[df["target_date"] == expected_target]
    if row.empty:
        return CutoffResult(
            cutoff_date=cutoff,
            target_date=expected_target,
            value=None,
            members_used=0,
            status="missing_day_plus_1",
            note="target_date == cutoff+1 not found",
        )

    vals = row.iloc[0][mcols].apply(pd.to_numeric, errors="coerce")
    members_used = int(vals.notna().sum())
    if members_used == 0:
        return CutoffResult(
            cutoff_date=cutoff,
            target_date=expected_target,
            value=None,
            members_used=0,
            status="all_nan_members",
            note="all member values are NaN for day+1 row",
        )

    return CutoffResult(
        cutoff_date=cutoff,
        target_date=expected_target,
        value=float(vals.mean(skipna=True)),
        members_used=members_used,
        status="ok",
    )


def main() -> int:
    args = _parse_args()

    root = Path(args.nws_cache_root)
    out_csv = Path(args.out_csv)
    out_meta = Path(args.out_meta)
    out_diag = Path(args.out_diagnostics_csv)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)
    out_diag.parent.mkdir(parents=True, exist_ok=True)

    files = list(_iter_cutoff_files(root))
    if not files:
        raise FileNotFoundError(
            f"No files found under {root} matching cutoff_date=*/nws_members.csv"
        )

    results: List[CutoffResult] = []
    for p in files:
        r = _process_cutoff_file(p)
        results.append(r)
        if args.verbose and r.status != "ok":
            print(
                f"[WARN] cutoff={r.cutoff_date.isoformat()} "
                f"status={r.status} note={r.note}"
            )

    diag_rows = [
        {
            "cutoff_date": r.cutoff_date.isoformat(),
            "target_date": r.target_date.isoformat() if r.target_date else "",
            "synthetic_value": r.value,
            "members_used": r.members_used,
            "status": r.status,
            "note": r.note,
        }
        for r in results
    ]
    diag_df = pd.DataFrame(diag_rows).sort_values(["cutoff_date"])
    diag_df.to_csv(out_diag, index=False)

    ok_rows = [r for r in results if r.status == "ok" and r.value is not None]
    series_df = pd.DataFrame(
        {
            "date": [r.target_date.isoformat() for r in ok_rows if r.target_date],
            args.value_col: [r.value for r in ok_rows if r.target_date],
        }
    ).sort_values("date")

    # Resolve occasional duplicate target dates by keeping the latest cutoff.
    if not series_df.empty:
        ok_meta = pd.DataFrame(
            {
                "date": [r.target_date.isoformat() for r in ok_rows if r.target_date],
                "cutoff_date": [
                    r.cutoff_date.isoformat() for r in ok_rows if r.target_date
                ],
                args.value_col: [r.value for r in ok_rows if r.target_date],
            }
        ).sort_values(["date", "cutoff_date"])
        series_df = (
            ok_meta.groupby("date", as_index=False).tail(1)[["date", args.value_col]]
        ).sort_values("date")

    if args.start_date:
        sd = pd.to_datetime(args.start_date).date()
        series_df = series_df.loc[pd.to_datetime(series_df["date"]).dt.date >= sd]
    if args.end_date:
        ed = pd.to_datetime(args.end_date).date()
        series_df = series_df.loc[pd.to_datetime(series_df["date"]).dt.date <= ed]

    series_df.to_csv(out_csv, index=False)

    meta = {
        "builder": "nwm_build_synthetic_retrospective_from_nws_daily_cache.py",
        "definition": (
            "strict daily one-step synthetic: for each cutoff c, use "
            "target_date=c+1 row from nws_members.csv and average across member_*"
        ),
        "nws_cache_root": str(root),
        "input_files_total": len(files),
        "ok_rows": int((diag_df["status"] == "ok").sum()),
        "non_ok_rows": int((diag_df["status"] != "ok").sum()),
        "status_counts": {
            k: int(v) for k, v in diag_df["status"].value_counts().items()
        },
        "value_col": args.value_col,
        "rows_written": int(len(series_df)),
        "coverage_start": None if series_df.empty else str(series_df["date"].min()),
        "coverage_end": None if series_df.empty else str(series_df["date"].max()),
        "start_date_filter": args.start_date,
        "end_date_filter": args.end_date,
    }
    with out_meta.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[OK] wrote {out_csv}")
    print(f"[OK] wrote {out_meta}")
    print(f"[OK] wrote {out_diag}")
    print(
        f"[INFO] rows={meta['rows_written']} "
        f"coverage={meta['coverage_start']}..{meta['coverage_end']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
