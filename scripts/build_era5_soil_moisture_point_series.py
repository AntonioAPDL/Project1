#!/usr/bin/env python3
"""Download ERA5-Land soil moisture and build point time-series CSVs.

This script combines download + post-processing in one pass:
1) Request monthly ERA5-Land NetCDF files.
2) Extract nearest-point hourly `swvl1` series.
3) Aggregate daily mean series.
4) Remove monthly NetCDF files by default so only CSV outputs remain.
"""

from __future__ import annotations

import argparse
import calendar
from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import zipfile

import cdsapi
import pandas as pd
import xarray as xr


DEFAULT_START_YEAR = 1987
DEFAULT_END_YEAR = 2023
DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464
DEFAULT_CDS_URL = "https://cds.climate.copernicus.eu/api"

# Use a small but stable bbox that always intersects ERA5-Land grid cells.
DEFAULT_NORTH = 37.2
DEFAULT_WEST = -122.2
DEFAULT_SOUTH = 36.9
DEFAULT_EAST = -121.9


@dataclass
class Config:
    start_date: date
    end_date: date
    lat: float
    lon: float
    north: float
    west: float
    south: float
    east: float
    tmp_dir: Path
    daily_csv: Path
    hourly_csv: Optional[Path]
    keep_monthly: bool
    overwrite: bool
    strict: bool
    dry_run: bool
    cds_url: str
    cds_key: Optional[str]


def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        description="Build ERA5-Land soil-moisture point series with low disk footprint."
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="",
        help="Inclusive start date (YYYY-MM-DD). Overrides --start-year when provided.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="",
        help="Inclusive end date (YYYY-MM-DD). Overrides --end-year when provided.",
    )
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR)
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT)
    parser.add_argument("--lon", type=float, default=DEFAULT_LON)
    parser.add_argument("--north", type=float, default=DEFAULT_NORTH)
    parser.add_argument("--west", type=float, default=DEFAULT_WEST)
    parser.add_argument("--south", type=float, default=DEFAULT_SOUTH)
    parser.add_argument("--east", type=float, default=DEFAULT_EAST)
    parser.add_argument(
        "--tmp-dir",
        type=Path,
        default=Path("soil_moisture_data/.tmp_era5"),
        help="Temporary download directory for monthly NetCDF files.",
    )
    parser.add_argument(
        "--daily-csv",
        type=Path,
        default=Path("soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv"),
    )
    parser.add_argument(
        "--hourly-csv",
        type=Path,
        default=None,
        help="Optional hourly output CSV path. Omit to write only daily series.",
    )
    parser.add_argument("--keep-monthly", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail immediately on first monthly download/process error.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned requests and exit.")
    parser.add_argument(
        "--cds-url",
        type=str,
        default=DEFAULT_CDS_URL,
        help=f"CDS API URL (default: {DEFAULT_CDS_URL})",
    )
    parser.add_argument(
        "--cds-key",
        type=str,
        default="",
        help="CDS API key. If omitted, uses CDSAPI_KEY env var or ~/.cdsapirc key.",
    )

    args = parser.parse_args()
    start_date, end_date = validate_args(args)

    return Config(
        start_date=start_date,
        end_date=end_date,
        lat=args.lat,
        lon=args.lon,
        north=args.north,
        west=args.west,
        south=args.south,
        east=args.east,
        tmp_dir=args.tmp_dir.resolve(),
        daily_csv=args.daily_csv.resolve(),
        hourly_csv=args.hourly_csv.resolve() if args.hourly_csv else None,
        keep_monthly=args.keep_monthly,
        overwrite=args.overwrite,
        strict=args.strict,
        dry_run=args.dry_run,
        cds_url=args.cds_url,
        cds_key=args.cds_key.strip() if args.cds_key else None,
    )


def _parse_date_or_die(value: str, flag: str) -> date:
    try:
        return pd.Timestamp(value).date()
    except Exception as exc:  # pragma: no cover - defensive parsing guard
        raise SystemExit(f"Invalid {flag}: {value} ({exc})")


def validate_args(args: argparse.Namespace) -> Tuple[date, date]:
    if args.start_date:
        start_date = _parse_date_or_die(args.start_date, "--start-date")
    else:
        start_date = date(args.start_year, 1, 1)

    if args.end_date:
        end_date = _parse_date_or_die(args.end_date, "--end-date")
    else:
        end_date = date(args.end_year, 12, 31)

    if start_date > end_date:
        raise SystemExit("Start date must be <= end date.")

    if not (-90.0 <= args.lat <= 90.0):
        raise SystemExit("--lat must be in [-90, 90]")
    if not (-180.0 <= args.lon <= 180.0):
        raise SystemExit("--lon must be in [-180, 180]")
    if args.north < args.south:
        raise SystemExit("Expected --north >= --south")
    if args.daily_csv is None:
        raise SystemExit("--daily-csv is required")
    if not args.cds_url:
        raise SystemExit("--cds-url must be non-empty")
    return start_date, end_date


def month_chunks(start_date: date, end_date: date) -> Iterable[Tuple[date, date]]:
    cursor = date(start_date.year, start_date.month, 1)
    while cursor <= end_date:
        n_days = calendar.monthrange(cursor.year, cursor.month)[1]
        month_end = date(cursor.year, cursor.month, n_days)
        chunk_start = max(start_date, cursor)
        chunk_end = min(end_date, month_end)
        yield chunk_start, chunk_end
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def build_request(chunk_start: date, chunk_end: date, cfg: Config) -> Dict[str, object]:
    year = chunk_start.year
    month = chunk_start.month
    days = [f"{d:02d}" for d in range(chunk_start.day, chunk_end.day + 1)]
    hours = [f"{h:02d}:00" for h in range(24)]
    return {
        "product_type": "reanalysis",
        "variable": "volumetric_soil_water_layer_1",
        "year": f"{year:04d}",
        "month": f"{month:02d}",
        "day": days,
        "time": hours,
        "area": [cfg.north, cfg.west, cfg.south, cfg.east],
        "data_format": "netcdf",
    }


def choose_time_column(df: pd.DataFrame) -> str:
    for col in ("valid_time", "time"):
        if col in df.columns:
            return col
    raise RuntimeError("No valid time column found (expected 'valid_time' or 'time').")


def extract_monthly_series(nc_path: Path, target_lat: float, target_lon: float) -> pd.DataFrame:
    ds = xr.open_dataset(nc_path, engine="netcdf4")
    try:
        if "swvl1" not in ds.data_vars:
            available = ", ".join(ds.data_vars)
            raise RuntimeError(f"Expected variable 'swvl1' not found. Available: {available}")

        point = ds.sel(latitude=target_lat, longitude=target_lon, method="nearest")
        df = point["swvl1"].to_dataframe().reset_index()
        tcol = choose_time_column(df)
        out = df[[tcol, "swvl1"]].rename(columns={tcol: "Date", "swvl1": "Soil_Moisture"})
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
        out["Soil_Moisture"] = pd.to_numeric(out["Soil_Moisture"], errors="coerce")
        out = out.dropna(subset=["Date", "Soil_Moisture"]).sort_values("Date")
        return out
    finally:
        ds.close()


def resolve_payload_file(monthly_file: Path) -> Tuple[Path, Optional[Path]]:
    """Return a dataset path and optional extraction directory for cleanup.

    CDS can return ZIP payloads even when target filename ends with .nc.
    """
    if not monthly_file.exists():
        raise FileNotFoundError(f"Downloaded file not found: {monthly_file}")

    with monthly_file.open("rb") as fh:
        sig = fh.read(4)
    is_zip = sig.startswith(b"PK")

    if not is_zip:
        return monthly_file, None

    extract_dir = monthly_file.parent / f"{monthly_file.stem}_unzipped"
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(monthly_file, "r") as zf:
        members = [m for m in zf.namelist() if not m.endswith("/")]
        if not members:
            raise RuntimeError(f"ZIP payload has no files: {monthly_file}")
        preferred = [m for m in members if m.lower().endswith((".nc", ".nc4"))]
        member = preferred[0] if preferred else members[0]
        extracted_path = Path(zf.extract(member, path=extract_dir))

    return extracted_path, extract_dir


def append_hourly_csv(csv_path: Path, chunk_df: pd.DataFrame) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    chunk_df.to_csv(csv_path, mode="a", index=False, header=write_header)


def update_daily_accumulators(daily_sum: Dict[date, float], daily_count: Dict[date, int], chunk_df: pd.DataFrame) -> None:
    day_series = chunk_df["Date"].dt.date
    grouped = chunk_df.assign(Day=day_series).groupby("Day")["Soil_Moisture"].agg(["sum", "count"]).reset_index()

    for _, row in grouped.iterrows():
        day = row["Day"]
        daily_sum[day] = daily_sum.get(day, 0.0) + float(row["sum"])
        daily_count[day] = daily_count.get(day, 0) + int(row["count"])


def build_daily_frame(daily_sum: Dict[date, float], daily_count: Dict[date, int]) -> pd.DataFrame:
    days = sorted(daily_sum)
    values = []
    for day in days:
        denom = daily_count.get(day, 0)
        if denom <= 0:
            continue
        values.append((day.isoformat(), daily_sum[day] / float(denom)))
    return pd.DataFrame(values, columns=["Date", "Daily_Avg_Soil_Moisture"])


def maybe_prepare_outputs(cfg: Config) -> None:
    cfg.daily_csv.parent.mkdir(parents=True, exist_ok=True)
    cfg.tmp_dir.mkdir(parents=True, exist_ok=True)

    if cfg.hourly_csv:
        cfg.hourly_csv.parent.mkdir(parents=True, exist_ok=True)

    if not cfg.overwrite:
        if cfg.daily_csv.exists():
            raise SystemExit(f"Output exists: {cfg.daily_csv}. Use --overwrite to replace it.")
        if cfg.hourly_csv and cfg.hourly_csv.exists():
            raise SystemExit(f"Output exists: {cfg.hourly_csv}. Use --overwrite to replace it.")
    else:
        if cfg.daily_csv.exists():
            cfg.daily_csv.unlink()
        if cfg.hourly_csv and cfg.hourly_csv.exists():
            cfg.hourly_csv.unlink()


def resolve_cds_key(explicit_key: Optional[str]) -> Optional[str]:
    if explicit_key:
        return explicit_key

    env_key = os.environ.get("CDSAPI_KEY", "").strip()
    if env_key:
        return env_key

    rc_path = Path.home() / ".cdsapirc"
    if not rc_path.exists():
        return None

    for line in rc_path.read_text(encoding="utf-8").splitlines():
        line_s = line.strip()
        if line_s.startswith("key:"):
            return line_s.split(":", 1)[1].strip()
    return None


def is_cds_no_data_error(message: str) -> bool:
    msg = message.lower()
    indicators = (
        "none of the data you have requested is available yet",
        "latest date available",
        "multiadapternodataerror",
        "no data available",
    )
    return any(token in msg for token in indicators)


def main() -> int:
    cfg = parse_args()
    chunks = list(month_chunks(cfg.start_date, cfg.end_date))
    cds_key = resolve_cds_key(cfg.cds_key)

    print(f"[INFO] ERA5 monthly chunks to process: {len(chunks)}")
    print(f"[INFO] Date window: {cfg.start_date.isoformat()} .. {cfg.end_date.isoformat()}")
    print(f"[INFO] Target point: lat={cfg.lat:.7f} lon={cfg.lon:.6f}")
    print(f"[INFO] Area: north={cfg.north}, west={cfg.west}, south={cfg.south}, east={cfg.east}")
    print(f"[INFO] Daily CSV: {cfg.daily_csv}")
    print(f"[INFO] Hourly CSV: {cfg.hourly_csv if cfg.hourly_csv else '(disabled)'}")
    print(f"[INFO] Temp dir: {cfg.tmp_dir}")
    print(f"[INFO] keep_monthly={cfg.keep_monthly}")
    print(f"[INFO] CDS URL: {cfg.cds_url}")

    if cfg.dry_run:
        for chunk_start, chunk_end in chunks:
            print(f"[DRY-RUN] request {chunk_start.isoformat()} .. {chunk_end.isoformat()}")
        return 0

    maybe_prepare_outputs(cfg)

    client_kwargs = {"url": cfg.cds_url}
    if cds_key:
        client_kwargs["key"] = cds_key
    client = cdsapi.Client(**client_kwargs)
    daily_sum: Dict[date, float] = {}
    daily_count: Dict[date, int] = {}
    failures: List[Tuple[date, date, str]] = []
    processed = 0

    for chunk_start, chunk_end in chunks:
        req = build_request(chunk_start, chunk_end, cfg)
        monthly_file = cfg.tmp_dir / f"soil_moisture_big_trees_{chunk_start.year:04d}_{chunk_start.month:02d}_{chunk_start.day:02d}_{chunk_end.day:02d}.nc"
        extracted_dir: Optional[Path] = None

        try:
            print(f"[INFO] Downloading {chunk_start.isoformat()} .. {chunk_end.isoformat()}")
            client.retrieve("reanalysis-era5-land", req, str(monthly_file))
            payload_file, extracted_dir = resolve_payload_file(monthly_file)
            chunk_df = extract_monthly_series(payload_file, cfg.lat, cfg.lon)
            chunk_df = chunk_df[(chunk_df["Date"] >= pd.Timestamp(chunk_start)) & (chunk_df["Date"] <= pd.Timestamp(chunk_end))]
            if chunk_df.empty:
                raise RuntimeError("Monthly extraction returned no rows.")

            if cfg.hourly_csv:
                append_hourly_csv(cfg.hourly_csv, chunk_df)
            update_daily_accumulators(daily_sum, daily_count, chunk_df)
            processed += 1

        except Exception as exc:
            msg = str(exc)
            failures.append((chunk_start, chunk_end, msg))
            print(f"[ERROR] {chunk_start.isoformat()} .. {chunk_end.isoformat()}: {msg}")
            if cfg.strict:
                raise
        finally:
            if monthly_file.exists() and not cfg.keep_monthly:
                monthly_file.unlink()
            if extracted_dir is not None and extracted_dir.exists() and not cfg.keep_monthly:
                for item in sorted(extracted_dir.rglob("*"), reverse=True):
                    if item.is_file():
                        item.unlink(missing_ok=True)
                    elif item.is_dir():
                        item.rmdir()
                extracted_dir.rmdir()

    daily_df = build_daily_frame(daily_sum, daily_count)
    if daily_df.empty:
        if failures and all(is_cds_no_data_error(msg) for _, _, msg in failures):
            pd.DataFrame(columns=["Date", "Daily_Avg_Soil_Moisture"]).to_csv(cfg.daily_csv, index=False)
            print("[WARN] No new ERA5 rows are available yet for the requested window.")
            print(f"[OK] wrote empty daily CSV: {cfg.daily_csv}")
            print(f"[OK] processed chunks: {processed}/{len(chunks)}")
            return 0
        raise SystemExit("No daily rows produced; aborting.")

    daily_df.to_csv(cfg.daily_csv, index=False)

    print(f"[OK] wrote daily CSV: {cfg.daily_csv} rows={len(daily_df)}")
    print(f"[OK] processed chunks: {processed}/{len(chunks)}")
    print(f"[OK] daily range: {daily_df['Date'].min()} .. {daily_df['Date'].max()}")

    if failures:
        print(f"[WARN] failures: {len(failures)} chunk(s)")
        for chunk_start, chunk_end, msg in failures[:10]:
            print(f"[WARN] {chunk_start.isoformat()} .. {chunk_end.isoformat()}: {msg}")
        if len(failures) > 10:
            print(f"[WARN] ... {len(failures) - 10} additional failures not shown")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
