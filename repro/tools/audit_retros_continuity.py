#!/usr/bin/env python3
"""Audit continuity for retrospective/historical/reanalysis point-series inputs.

Outputs three CSV reports under repro/reports/ by default:
  1) retros_source_continuity_audit.csv
  2) retros_series_continuity_audit.csv
  3) retros_source_vs_cache_consistency.csv
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class SeriesSpec:
    source_id: str
    source_label: str
    path: Path
    date_col: str
    value_col: str


DEFAULT_SERIES_SPECS = (
    SeriesSpec(
        source_id="baseline_glofas",
        source_label="GloFAS retrospective (baseline)",
        path=Path("retros_2023-06-01.csv"),
        date_col="Date",
        value_col="GloFAS",
    ),
    SeriesSpec(
        source_id="baseline_nws3_0",
        source_label="NWS retrospective v3.0 (baseline)",
        path=Path("retros_2023-06-01.csv"),
        date_col="Date",
        value_col="NWS3.0",
    ),
    SeriesSpec(
        source_id="glofas_hist_v21_htessel_cons",
        source_label="GloFAS historical v2.1 (HTESSEL-LISFLOOD, consolidated)",
        path=Path("data/glofas_historical_consolidated_point/point_series/hist_v21_htessel_cons_bigtrees.csv"),
        date_col="date",
        value_col="discharge_cms",
    ),
    SeriesSpec(
        source_id="glofas_hist_v31_lisflood_cons",
        source_label="GloFAS historical v3.1 (LISFLOOD, consolidated)",
        path=Path("data/glofas_historical_consolidated_point/point_series/hist_v31_lisflood_cons_bigtrees.csv"),
        date_col="date",
        value_col="discharge_cms",
    ),
    SeriesSpec(
        source_id="glofas_hist_v40_lisflood_cons",
        source_label="GloFAS historical v4.0 (LISFLOOD, consolidated)",
        path=Path("data/glofas_historical_consolidated_point/point_series/hist_v40_lisflood_cons_bigtrees.csv"),
        date_col="date",
        value_col="discharge_cms",
    ),
    SeriesSpec(
        source_id="glofas_legacy_reanalysis_v30",
        source_label="GloFAS legacy reanalysis v3.0",
        path=Path("data/glofas_legacy_global/point_series/dis_1980_2018_v3_legacy_bigtrees.csv"),
        date_col="date",
        value_col="discharge_cms",
    ),
)


def audit_continuity_frame(df: pd.DataFrame, date_col: str, value_col: str) -> dict:
    g = df[[date_col, value_col]].copy()
    g.columns = ["date", "value"]
    g["date"] = pd.to_datetime(g["date"], errors="coerce")
    g = g.dropna(subset=["date"]).sort_values("date")

    if g.empty:
        return {
            "n_rows": 0,
            "start": "",
            "end": "",
            "n_expected_daily": 0,
            "n_missing_dates": 0,
            "n_duplicate_dates": 0,
            "n_nan_values": 0,
            "first_missing": "",
            "last_missing": "",
            "first_20_missing": "",
        }

    start = g["date"].min()
    end = g["date"].max()
    expected = pd.date_range(start, end, freq="D")
    present = pd.DatetimeIndex(g["date"].unique()).sort_values()
    missing = expected.difference(present)

    return {
        "n_rows": int(len(g)),
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "n_expected_daily": int(len(expected)),
        "n_missing_dates": int(len(missing)),
        "n_duplicate_dates": int(g.duplicated(subset=["date"]).sum()),
        "n_nan_values": int(pd.isna(g["value"]).sum()),
        "first_missing": missing[0].date().isoformat() if len(missing) else "",
        "last_missing": missing[-1].date().isoformat() if len(missing) else "",
        "first_20_missing": "|".join(d.date().isoformat() for d in missing[:20]) if len(missing) else "",
    }


def audit_source_series(specs: Iterable[SeriesSpec]) -> pd.DataFrame:
    rows = []
    for spec in specs:
        row = {
            "source_id": spec.source_id,
            "source_label": spec.source_label,
            "path": str(spec.path),
            "exists": spec.path.exists(),
        }
        if not spec.path.exists():
            rows.append(row)
            continue

        df = pd.read_csv(spec.path)
        if spec.date_col not in df.columns or spec.value_col not in df.columns:
            row["error"] = "missing_required_columns"
            rows.append(row)
            continue

        row.update(audit_continuity_frame(df, spec.date_col, spec.value_col))
        rows.append(row)

    out = pd.DataFrame(rows)
    return out.sort_values("source_id")


def audit_cache_series(cache_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(cache_csv, parse_dates=["date"])
    req = ["source_id", "source_label", "source_family", "date", "discharge_cms"]
    missing_cols = [c for c in req if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Cache file missing required columns: {missing_cols}")

    rows = []
    for (sid, slab, sfam), g in df.groupby(["source_id", "source_label", "source_family"], dropna=False):
        continuity = audit_continuity_frame(g, "date", "discharge_cms")
        rows.append(
            {
                "source_id": sid,
                "source_label": slab,
                "source_family": sfam,
                **continuity,
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["source_family", "source_label"])


def compare_source_vs_cache(source_df: pd.DataFrame, cache_df: pd.DataFrame) -> pd.DataFrame:
    cache_agg = cache_df[["source_id", "n_rows", "start", "end"]].rename(
        columns={"n_rows": "cache_rows", "start": "cache_start", "end": "cache_end"}
    )
    merged = source_df.merge(cache_agg, on="source_id", how="left")
    merged["same_row_count"] = merged["n_rows"] == merged["cache_rows"]
    merged["same_start"] = merged["start"] == merged["cache_start"]
    merged["same_end"] = merged["end"] == merged["cache_end"]
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit continuity for retrospective/historical/reanalysis series.")
    parser.add_argument(
        "--cache-csv",
        default="data/forecats_cache/site=11160500/run_id=20260206_paper_default_latest/cache/retros_daily_cms.csv",
        help="Path to retros cache CSV built by scripts/forecats_batch.R render mode.",
    )
    parser.add_argument(
        "--out-dir",
        default="repro/reports",
        help="Directory where audit CSV outputs will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache_csv = Path(args.cache_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not cache_csv.exists():
        raise FileNotFoundError(f"Missing cache CSV: {cache_csv}")

    source_df = audit_source_series(DEFAULT_SERIES_SPECS)
    cache_df = audit_cache_series(cache_csv)
    consistency_df = compare_source_vs_cache(source_df, cache_df)

    p_source = out_dir / "retros_source_continuity_audit.csv"
    p_cache = out_dir / "retros_series_continuity_audit.csv"
    p_consistency = out_dir / "retros_source_vs_cache_consistency.csv"

    source_df.to_csv(p_source, index=False)
    cache_df.to_csv(p_cache, index=False)
    consistency_df.to_csv(p_consistency, index=False)

    print(f"[OK] wrote {p_source}")
    print(f"[OK] wrote {p_cache}")
    print(f"[OK] wrote {p_consistency}")


if __name__ == "__main__":
    main()
