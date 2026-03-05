#!/usr/bin/env python3
"""Build NWM retrospective soil-moisture point daily series (SOIL_M / SOIL_W).

This script extracts one grid-cell point from NWM retrospective v3.0 LDAS Zarr,
computes daily means from the native sub-daily cadence, and writes only the
final daily point CSV (low disk footprint).
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import fsspec
import numpy as np
import pandas as pd
import xarray as xr


DEFAULT_ZARR_URL = "s3://noaa-nwm-retrospective-3-0-pds/CONUS/zarr/ldasout.zarr"
DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464
DEFAULT_START_DATE = "1987-01-01"


@dataclass
class ExtractionMeta:
    zarr_url: str
    target_latitude: float
    target_longitude: float
    selected_x_index: int
    selected_y_index: int
    selected_x: float
    selected_y: float
    projected_x: float
    projected_y: float
    distance_m: float
    requested_start_date: str
    requested_end_date: str
    effective_start_date: str
    effective_end_date: str
    soil_layer_index: int
    rows_out: int
    created_utc: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Extract daily NWM retrospective SOIL_M / SOIL_W point series."
    )
    p.add_argument("--zarr-url", default=DEFAULT_ZARR_URL)
    p.add_argument("--lat", type=float, default=DEFAULT_LAT)
    p.add_argument("--lon", type=float, default=DEFAULT_LON)
    p.add_argument("--start-date", default=DEFAULT_START_DATE)
    p.add_argument(
        "--end-date",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="Inclusive end date (UTC) YYYY-MM-DD.",
    )
    p.add_argument(
        "--soil-layer-index",
        type=int,
        default=0,
        help="Layer index for SOIL_M / SOIL_W in soil_layers_stag dimension (0-based).",
    )
    p.add_argument(
        "--max-search-radius-cells",
        type=int,
        default=20,
        help="Search radius to find nearest non-NaN cell if nearest cell is missing.",
    )
    p.add_argument("--out-csv", required=True)
    p.add_argument("--out-meta", required=True)
    return p.parse_args()


def _forward_lcc(
    lat_deg: float,
    lon_deg: float,
    lat1_deg: float,
    lat2_deg: float,
    lat0_deg: float,
    lon0_deg: float,
    earth_radius_m: float,
) -> Tuple[float, float]:
    """Project WGS84-like lat/lon into NWM Lambert Conformal grid meters."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    lat1 = math.radians(lat1_deg)
    lat2 = math.radians(lat2_deg)
    lat0 = math.radians(lat0_deg)
    lon0 = math.radians(lon0_deg)

    n = math.log(math.cos(lat1) / math.cos(lat2)) / math.log(
        math.tan(math.pi / 4.0 + lat2 / 2.0) / math.tan(math.pi / 4.0 + lat1 / 2.0)
    )
    f = (math.cos(lat1) * (math.tan(math.pi / 4.0 + lat1 / 2.0) ** n)) / n
    rho = earth_radius_m * f / (math.tan(math.pi / 4.0 + lat / 2.0) ** n)
    rho0 = earth_radius_m * f / (math.tan(math.pi / 4.0 + lat0 / 2.0) ** n)
    x = rho * math.sin(n * (lon - lon0))
    y = rho0 - rho * math.cos(n * (lon - lon0))
    return x, y


def _safe_scalar(da: xr.DataArray) -> float:
    raw = da.values
    if np.isscalar(raw):
        return float(raw)
    arr = np.asarray(raw).reshape(-1)
    return float(arr[0])


def _distance_m(x0: float, y0: float, x1: float, y1: float) -> float:
    return float(math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2))


def _cell_value_at_time(
    ds: xr.Dataset,
    var_name: str,
    time_sel: np.datetime64,
    ix: int,
    iy: int,
    soil_layer_index: int,
) -> float:
    da = ds[var_name].sel(time=time_sel)
    if "soil_layers_stag" in da.dims:
        da = da.isel(soil_layers_stag=soil_layer_index)
    da = da.isel(x=ix, y=iy)
    return _safe_scalar(da)


def choose_cell(
    ds: xr.Dataset,
    var_name: str,
    target_x: float,
    target_y: float,
    soil_layer_index: int,
    max_radius_cells: int,
    sample_time: np.datetime64,
) -> Tuple[int, int]:
    x_vals = np.asarray(ds["x"].values, dtype=float)
    y_vals = np.asarray(ds["y"].values, dtype=float)

    ix0 = int(np.argmin(np.abs(x_vals - target_x)))
    iy0 = int(np.argmin(np.abs(y_vals - target_y)))

    try:
        v0 = _cell_value_at_time(ds, var_name, sample_time, ix0, iy0, soil_layer_index)
        if np.isfinite(v0):
            return ix0, iy0
    except Exception:
        pass

    best: Optional[Tuple[float, int, int]] = None
    nx = len(x_vals)
    ny = len(y_vals)
    for radius in range(1, max_radius_cells + 1):
        x_lo = max(0, ix0 - radius)
        x_hi = min(nx - 1, ix0 + radius)
        y_lo = max(0, iy0 - radius)
        y_hi = min(ny - 1, iy0 + radius)
        for ix in range(x_lo, x_hi + 1):
            for iy in range(y_lo, y_hi + 1):
                if abs(ix - ix0) != radius and abs(iy - iy0) != radius:
                    continue
                try:
                    vv = _cell_value_at_time(ds, var_name, sample_time, ix, iy, soil_layer_index)
                except Exception:
                    continue
                if not np.isfinite(vv):
                    continue
                d = _distance_m(target_x, target_y, float(x_vals[ix]), float(y_vals[iy]))
                if best is None or d < best[0]:
                    best = (d, ix, iy)
        if best is not None:
            return best[1], best[2]

    return ix0, iy0


def extract_daily_var(
    ds: xr.Dataset,
    var_name: str,
    ix: int,
    iy: int,
    start_date: str,
    end_date: str,
    soil_layer_index: int,
    out_col: str,
) -> pd.DataFrame:
    da = ds[var_name].isel(x=ix, y=iy).sel(time=slice(start_date, end_date))
    if "soil_layers_stag" in da.dims:
        da = da.isel(soil_layers_stag=soil_layer_index)

    df = da.to_dataframe(name=out_col).reset_index()
    df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
    df[out_col] = pd.to_numeric(df[out_col], errors="coerce")
    df = df.dropna(subset=["time"])
    df["Date"] = df["time"].dt.tz_convert(None).dt.floor("D")
    out = (
        df.groupby("Date", as_index=False)[out_col]
        .mean()
        .sort_values("Date")
    )
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    return out


def main() -> int:
    args = parse_args()

    out_csv = Path(args.out_csv).resolve()
    out_meta = Path(args.out_meta).resolve()
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)

    mapper = fsspec.get_mapper(args.zarr_url, anon=True)
    ds = xr.open_zarr(mapper, consolidated=True)

    required_vars = ["SOIL_M", "SOIL_W"]
    for vv in required_vars:
        if vv not in ds.data_vars:
            raise SystemExit(f"Required variable missing in dataset: {vv}")
    if "x" not in ds.coords or "y" not in ds.coords or "time" not in ds.coords:
        raise SystemExit("Dataset missing required coords x/y/time.")
    if "crs" not in ds.data_vars:
        raise SystemExit("Dataset missing 'crs' variable needed for projection mapping.")

    tmin = pd.Timestamp(ds["time"].min().values).date()
    tmax = pd.Timestamp(ds["time"].max().values).date()
    req_start = pd.Timestamp(args.start_date).date()
    req_end = pd.Timestamp(args.end_date).date()
    if req_start > req_end:
        raise SystemExit("--start-date must be <= --end-date")

    eff_start = max(req_start, tmin)
    eff_end = min(req_end, tmax)
    if eff_start > eff_end:
        empty = pd.DataFrame(columns=["Date", "NWM_SOIL_M", "NWM_SOIL_W"])
        empty.to_csv(out_csv, index=False)
        meta = ExtractionMeta(
            zarr_url=args.zarr_url,
            target_latitude=float(args.lat),
            target_longitude=float(args.lon),
            selected_x_index=-1,
            selected_y_index=-1,
            selected_x=float("nan"),
            selected_y=float("nan"),
            projected_x=float("nan"),
            projected_y=float("nan"),
            distance_m=float("nan"),
            requested_start_date=req_start.isoformat(),
            requested_end_date=req_end.isoformat(),
            effective_start_date="",
            effective_end_date="",
            soil_layer_index=int(args.soil_layer_index),
            rows_out=0,
            created_utc=datetime.now(timezone.utc).isoformat(),
        )
        out_meta.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")
        print(f"[WARN] Requested range outside dataset availability: {tmin} .. {tmax}")
        print(f"[OK] wrote empty {out_csv}")
        print(f"[OK] wrote {out_meta}")
        return 0

    crs = ds["crs"].attrs
    earth_radius = float(crs.get("earth_radius", 6370000.0))
    std_parallel = crs.get("standard_parallel", [30.0, 60.0])
    if isinstance(std_parallel, (int, float)):
        lat1 = float(std_parallel)
        lat2 = float(std_parallel)
    else:
        lat1 = float(std_parallel[0])
        lat2 = float(std_parallel[1])
    lat0 = float(crs.get("latitude_of_projection_origin", 40.0))
    lon0 = float(crs.get("longitude_of_central_meridian", -97.0))

    target_x, target_y = _forward_lcc(
        lat_deg=float(args.lat),
        lon_deg=float(args.lon),
        lat1_deg=lat1,
        lat2_deg=lat2,
        lat0_deg=lat0,
        lon0_deg=lon0,
        earth_radius_m=earth_radius,
    )

    sample_time = np.datetime64(pd.Timestamp(eff_start).isoformat())
    ix, iy = choose_cell(
        ds=ds,
        var_name="SOIL_M",
        target_x=target_x,
        target_y=target_y,
        soil_layer_index=int(args.soil_layer_index),
        max_radius_cells=int(args.max_search_radius_cells),
        sample_time=sample_time,
    )

    x_sel = float(ds["x"].values[ix])
    y_sel = float(ds["y"].values[iy])
    dist_m = _distance_m(target_x, target_y, x_sel, y_sel)

    d_m = extract_daily_var(
        ds=ds,
        var_name="SOIL_M",
        ix=ix,
        iy=iy,
        start_date=eff_start.isoformat(),
        end_date=eff_end.isoformat(),
        soil_layer_index=int(args.soil_layer_index),
        out_col="NWM_SOIL_M",
    )
    d_w = extract_daily_var(
        ds=ds,
        var_name="SOIL_W",
        ix=ix,
        iy=iy,
        start_date=eff_start.isoformat(),
        end_date=eff_end.isoformat(),
        soil_layer_index=int(args.soil_layer_index),
        out_col="NWM_SOIL_W",
    )

    out = pd.merge(d_m, d_w, on="Date", how="outer")
    out = out.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
    out.to_csv(out_csv, index=False)

    meta = ExtractionMeta(
        zarr_url=args.zarr_url,
        target_latitude=float(args.lat),
        target_longitude=float(args.lon),
        selected_x_index=int(ix),
        selected_y_index=int(iy),
        selected_x=x_sel,
        selected_y=y_sel,
        projected_x=target_x,
        projected_y=target_y,
        distance_m=dist_m,
        requested_start_date=req_start.isoformat(),
        requested_end_date=req_end.isoformat(),
        effective_start_date=eff_start.isoformat(),
        effective_end_date=eff_end.isoformat(),
        soil_layer_index=int(args.soil_layer_index),
        rows_out=int(len(out)),
        created_utc=datetime.now(timezone.utc).isoformat(),
    )
    out_meta.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")

    print(f"[OK] wrote {out_csv} rows={len(out)}")
    if len(out) > 0:
        print(f"[OK] date range: {out['Date'].iloc[0]} .. {out['Date'].iloc[-1]}")
    print(f"[OK] selected grid index: x={ix}, y={iy}, distance_m={dist_m:.3f}")
    print(f"[OK] wrote {out_meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

