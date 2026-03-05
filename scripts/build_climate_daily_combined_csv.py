#!/usr/bin/env python3
"""Build a clean combined daily climate CSV (ppt + ERA5 soil + NWM soil)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge canonical PPT, ERA5 soil, and NWM soil daily CSVs into one table."
    )
    parser.add_argument("--ppt-csv", type=Path, required=True)
    parser.add_argument("--soil-csv", type=Path, required=True, help="ERA5 soil daily CSV.")
    parser.add_argument(
        "--nwm-soil-csv",
        type=Path,
        default=Path("soil_moisture_data/nwm_soil_moisture_big_trees_daily_1987_present.csv"),
        help="Optional NWM retrospective soil daily CSV.",
    )
    parser.add_argument("--output-csv", type=Path, required=True)
    return parser.parse_args()


def load_ppt(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "Date" not in df.columns:
        raise SystemExit(f"Missing Date column in PPT CSV: {path}")
    if "PRCP_mm" not in df.columns:
        raise SystemExit(f"Missing PRCP_mm column in PPT CSV: {path}")

    out = df[["Date", "PRCP_mm"]].copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out["PRCP_mm"] = pd.to_numeric(out["PRCP_mm"], errors="coerce")
    out = out.dropna(subset=["Date"]).sort_values("Date")
    out = out.drop_duplicates(subset=["Date"], keep="last")
    out = out.rename(columns={"PRCP_mm": "daily_avg_ppt"})
    return out


def load_soil(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "Date" not in df.columns:
        raise SystemExit(f"Missing Date column in soil CSV: {path}")
    if "Daily_Avg_Soil_Moisture" not in df.columns:
        raise SystemExit(f"Missing Daily_Avg_Soil_Moisture column in soil CSV: {path}")

    out = df[["Date", "Daily_Avg_Soil_Moisture"]].copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out["Daily_Avg_Soil_Moisture"] = pd.to_numeric(out["Daily_Avg_Soil_Moisture"], errors="coerce")
    out = out.dropna(subset=["Date"]).sort_values("Date")
    out = out.drop_duplicates(subset=["Date"], keep="last")
    out = out.rename(columns={"Daily_Avg_Soil_Moisture": "daily_avg_soil_ERA5"})
    return out


def load_nwm_soil(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Date", "daily_avg_soil_NWM_SOIL_M", "daily_avg_soil_NWM_SOIL_W"])

    df = pd.read_csv(path)
    if "Date" not in df.columns:
        raise SystemExit(f"Missing Date column in NWM soil CSV: {path}")

    keep_cols = ["Date"]
    if "NWM_SOIL_M" in df.columns:
        keep_cols.append("NWM_SOIL_M")
    if "NWM_SOIL_W" in df.columns:
        keep_cols.append("NWM_SOIL_W")
    if len(keep_cols) == 1:
        return pd.DataFrame(columns=["Date", "daily_avg_soil_NWM_SOIL_M", "daily_avg_soil_NWM_SOIL_W"])

    out = df[keep_cols].copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    if "NWM_SOIL_M" in out.columns:
        out["NWM_SOIL_M"] = pd.to_numeric(out["NWM_SOIL_M"], errors="coerce")
    if "NWM_SOIL_W" in out.columns:
        out["NWM_SOIL_W"] = pd.to_numeric(out["NWM_SOIL_W"], errors="coerce")
    out = out.dropna(subset=["Date"]).sort_values("Date")
    out = out.drop_duplicates(subset=["Date"], keep="last")
    out = out.rename(
        columns={
            "NWM_SOIL_M": "daily_avg_soil_NWM_SOIL_M",
            "NWM_SOIL_W": "daily_avg_soil_NWM_SOIL_W",
        }
    )
    if "daily_avg_soil_NWM_SOIL_M" not in out.columns:
        out["daily_avg_soil_NWM_SOIL_M"] = pd.NA
    if "daily_avg_soil_NWM_SOIL_W" not in out.columns:
        out["daily_avg_soil_NWM_SOIL_W"] = pd.NA
    return out[["Date", "daily_avg_soil_NWM_SOIL_M", "daily_avg_soil_NWM_SOIL_W"]]


def main() -> int:
    args = parse_args()
    ppt_csv = args.ppt_csv.resolve()
    soil_csv = args.soil_csv.resolve()
    nwm_soil_csv = args.nwm_soil_csv.resolve()
    output_csv = args.output_csv.resolve()

    if not ppt_csv.exists():
        raise SystemExit(f"PPT CSV not found: {ppt_csv}")
    if not soil_csv.exists():
        raise SystemExit(f"Soil CSV not found: {soil_csv}")

    ppt = load_ppt(ppt_csv)
    soil = load_soil(soil_csv)
    nwm_soil = load_nwm_soil(nwm_soil_csv)

    merged = pd.merge(ppt, soil, on="Date", how="outer")
    merged = pd.merge(merged, nwm_soil, on="Date", how="outer")
    merged = merged.sort_values("Date")
    merged = merged.rename(columns={"Date": "timestamp"})
    merged["timestamp"] = merged["timestamp"].dt.strftime("%Y-%m-%d")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(
        output_csv,
        index=False,
        columns=[
            "timestamp",
            "daily_avg_ppt",
            "daily_avg_soil_ERA5",
            "daily_avg_soil_NWM_SOIL_M",
            "daily_avg_soil_NWM_SOIL_W",
        ],
    )

    print(f"[OK] wrote combined CSV: {output_csv} rows={len(merged)}")
    if len(merged) > 0:
        print(
            "[OK] range: "
            f"{merged['timestamp'].iloc[0]} .. {merged['timestamp'].iloc[-1]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
