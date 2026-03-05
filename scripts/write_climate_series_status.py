#!/usr/bin/env python3
"""Write a compact status CSV for climate point time-series outputs.

Output contains one row per variable (ppt, soil) with current coverage stats.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd


@dataclass(frozen=True)
class SeriesSpec:
    variable: str
    csv_path: Path
    value_column: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write climate series status CSV.")
    parser.add_argument("--root-dir", type=Path, required=True)
    parser.add_argument("--target-date", type=str, default="")
    parser.add_argument("--output-csv", type=Path, default=None)
    return parser.parse_args()


def parse_target_date(raw: str) -> date:
    if raw.strip():
        return pd.Timestamp(raw).date()
    return datetime.utcnow().date()


def summarize_series(spec: SeriesSpec, target_date: date, stamp_utc: str) -> dict:
    if not spec.csv_path.exists():
        return {
            "variable": spec.variable,
            "csv_path": str(spec.csv_path),
            "rows": "0",
            "min_date": "",
            "max_date": "",
            "target_date": target_date.isoformat(),
            "target_reached": "NO",
            "lag_days": "",
            "value_column": spec.value_column,
            "latest_value": "",
            "updated_at_utc": stamp_utc,
        }

    df = pd.read_csv(spec.csv_path)
    if "Date" not in df.columns:
        return {
            "variable": spec.variable,
            "csv_path": str(spec.csv_path),
            "rows": "0",
            "min_date": "",
            "max_date": "",
            "target_date": target_date.isoformat(),
            "target_reached": "NO",
            "lag_days": "",
            "value_column": spec.value_column,
            "latest_value": "",
            "updated_at_utc": stamp_utc,
        }

    dates = pd.to_datetime(df["Date"], errors="coerce")
    valid = df.loc[dates.notna()].copy()
    if valid.empty:
        return {
            "variable": spec.variable,
            "csv_path": str(spec.csv_path),
            "rows": "0",
            "min_date": "",
            "max_date": "",
            "target_date": target_date.isoformat(),
            "target_reached": "NO",
            "lag_days": "",
            "value_column": spec.value_column,
            "latest_value": "",
            "updated_at_utc": stamp_utc,
        }

    valid["Date"] = pd.to_datetime(valid["Date"], errors="coerce")
    valid = valid.dropna(subset=["Date"]).sort_values("Date")
    rows = len(valid)
    min_date = valid["Date"].iloc[0].date()
    max_date = valid["Date"].iloc[-1].date()

    latest_value: Optional[str] = ""
    if spec.value_column in valid.columns:
        latest_raw = pd.to_numeric(valid[spec.value_column], errors="coerce").iloc[-1]
        if pd.notna(latest_raw):
            latest_value = f"{float(latest_raw):.6f}"

    target_reached = max_date >= target_date
    lag_days = 0 if target_reached else (target_date - max_date).days

    return {
        "variable": spec.variable,
        "csv_path": str(spec.csv_path),
        "rows": str(rows),
        "min_date": min_date.isoformat(),
        "max_date": max_date.isoformat(),
        "target_date": target_date.isoformat(),
        "target_reached": "YES" if target_reached else "NO",
        "lag_days": str(lag_days),
        "value_column": spec.value_column,
        "latest_value": latest_value,
        "updated_at_utc": stamp_utc,
    }


def write_output(output_csv: Path, rows: List[dict]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "variable",
        "csv_path",
        "rows",
        "min_date",
        "max_date",
        "target_date",
        "target_reached",
        "lag_days",
        "value_column",
        "latest_value",
        "updated_at_utc",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    root_dir = args.root_dir.resolve()
    target_date = parse_target_date(args.target_date)
    output_csv = (
        args.output_csv.resolve()
        if args.output_csv
        else (root_dir / "climate_series_status.csv").resolve()
    )

    specs = [
        SeriesSpec(
            variable="ppt",
            csv_path=(root_dir / "prism_precipitation_santa_cruz_1987_2023.csv"),
            value_column="PRCP_mm",
        ),
        SeriesSpec(
            variable="soil",
            csv_path=(root_dir / "soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv"),
            value_column="Daily_Avg_Soil_Moisture",
        ),
        SeriesSpec(
            variable="soil_nwm_soil_m",
            csv_path=(root_dir / "soil_moisture_data/nwm_soil_moisture_big_trees_daily_1987_present.csv"),
            value_column="NWM_SOIL_M",
        ),
        SeriesSpec(
            variable="soil_nwm_soil_w",
            csv_path=(root_dir / "soil_moisture_data/nwm_soil_moisture_big_trees_daily_1987_present.csv"),
            value_column="NWM_SOIL_W",
        ),
    ]

    stamp_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [summarize_series(spec, target_date, stamp_utc) for spec in specs]
    write_output(output_csv, rows)

    print(f"[OK] wrote status CSV: {output_csv}")
    for row in rows:
        print(
            f"[OK] {row['variable']}: rows={row['rows']} "
            f"max_date={row['max_date'] or 'NA'} target_reached={row['target_reached']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
