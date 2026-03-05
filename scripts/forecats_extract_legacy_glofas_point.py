#!/usr/bin/env python3
"""Extract nearest valid point time series from legacy GloFAS global NetCDF.

This implementation avoids loading the full 3D cube to locate the nearest
valid cell. It builds a sampled-time spatial validity mask (start/mid/end),
then extracts the full-time point series for the selected grid cell.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import xarray as xr


def to_0_360(lon):
    arr = np.mod(np.asarray(lon, dtype="float64"), 360.0)
    arr = np.where(np.isclose(arr, 360.0), 0.0, arr)
    if np.isscalar(lon):
        return float(arr)
    return arr


def to_m180_180(lon_0_360: float) -> float:
    return ((lon_0_360 + 180.0) % 360.0) - 180.0


def haversine_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    r = 6371.0
    lat1r = np.deg2rad(lat1)
    lon1r = np.deg2rad(lon1)
    lat2r = np.deg2rad(lat2)
    lon2r = np.deg2rad(lon2)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2.0) ** 2
    return 2.0 * r * np.arcsin(np.sqrt(a))


def resolve_coords(ds: xr.Dataset) -> Tuple[str, str, str]:
    lat_name = ""
    lon_name = ""
    for cand in ["latitude", "lat"]:
        if cand in ds.coords:
            lat_name = cand
            break
    for cand in ["longitude", "lon"]:
        if cand in ds.coords:
            lon_name = cand
            break
    if not lat_name or not lon_name:
        raise ValueError("Could not resolve latitude/longitude coordinate names")

    # Prefer standard discharge variable names if present.
    for cand in ["dis24", "dis", "discharge", "streamflow"]:
        if cand in ds.data_vars:
            return lat_name, lon_name, cand

    if not ds.data_vars:
        raise ValueError("Dataset has no data variables")
    return lat_name, lon_name, list(ds.data_vars)[0]


def _time_dim_name(da: xr.DataArray) -> str:
    for cand in ["time", "valid_time", "date"]:
        if cand in da.dims:
            return cand
    for dim in da.dims:
        if dim not in {"lat", "latitude", "lon", "longitude"}:
            return dim
    raise ValueError("Could not resolve time dimension name")


def _valid_mask_2d(values_2d: np.ndarray, fill_value: float | None) -> np.ndarray:
    mask = np.isfinite(values_2d)
    if fill_value is not None:
        mask &= values_2d != fill_value
    return mask


def nearest_valid_cell_sampled_mask(
    da: xr.DataArray,
    lat_name: str,
    lon_name: str,
    target_lat: float,
    target_lon: float,
) -> Tuple[int, int, float, int]:
    lats = da[lat_name].values
    lons = da[lon_name].values

    tdim = _time_dim_name(da)
    nt = int(da.sizes[tdim])
    if nt < 1:
        raise ValueError("Time dimension is empty")
    sample_idx = sorted({0, nt // 2, nt - 1})

    fill_value = da.encoding.get("_FillValue")
    if fill_value is None:
        fill_value = da.attrs.get("_FillValue")
    if fill_value is None:
        fill_value = da.attrs.get("missing_value")
    fill_value = float(fill_value) if fill_value is not None else None

    valid = np.ones((lats.size, lons.size), dtype=bool)
    for k in sample_idx:
        slice_2d = da.isel({tdim: k}).values
        valid &= _valid_mask_2d(slice_2d, fill_value)

    valid_count = int(valid.sum())
    if valid_count == 0:
        raise ValueError("No valid cells found in sampled-time validity mask")

    lat2d = np.repeat(lats[:, None], lons.size, axis=1)
    lon2d = np.repeat(lons[None, :], lats.size, axis=0)
    dist = haversine_km(target_lat, to_0_360(target_lon), lat2d, to_0_360(lon2d))
    dist = np.where(valid, dist, np.inf)

    lat_i, lon_i = np.unravel_index(int(np.argmin(dist)), dist.shape)
    return int(lat_i), int(lon_i), float(dist[lat_i, lon_i]), valid_count


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Extract nearest non-NaN legacy GloFAS point series")
    ap.add_argument("--input-nc", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-meta", type=Path, required=True)
    ap.add_argument("--lat", type=float, default=37.0443931)
    ap.add_argument("--lon", type=float, default=-122.072464)
    ap.add_argument("--var", default="", help="Optional variable override")
    ap.add_argument("--start-date", default="", help="Optional YYYY-MM-DD inclusive")
    ap.add_argument("--end-date", default="", help="Optional YYYY-MM-DD inclusive")
    ap.add_argument(
        "--cell-mode",
        choices=("sampled_mask",),
        default="sampled_mask",
        help="Strategy to resolve nearest valid cell.",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    print(f"[INFO] opening dataset: {args.input_nc}")
    ds = xr.open_dataset(args.input_nc)

    lat_name, lon_name, auto_var = resolve_coords(ds)
    var = args.var.strip() if args.var.strip() else auto_var
    if var not in ds.data_vars:
        raise ValueError(f"Variable {var!r} not found in dataset")

    da = ds[var]

    lat_i, lon_i, dist_km, valid_count = nearest_valid_cell_sampled_mask(
        da=da,
        lat_name=lat_name,
        lon_name=lon_name,
        target_lat=args.lat,
        target_lon=args.lon,
    )
    print(
        "[INFO] selected cell "
        f"lat_idx={lat_i} lon_idx={lon_i} lat={float(ds[lat_name].values[lat_i]):.6f} "
        f"lon={float(ds[lon_name].values[lon_i]):.6f} distance_km={dist_km:.3f} "
        f"sampled_valid_cells={valid_count}"
    )

    print("[INFO] reading full-time point series (this may take time for large chunked NetCDF)...")
    series = da.isel({lat_name: lat_i, lon_name: lon_i})

    # Normalize time axis name.
    time_name = ""
    for cand in ["time", "valid_time", "date"]:
        if cand in series.coords:
            time_name = cand
            break
    if not time_name:
        raise ValueError("No supported time coordinate found (time/valid_time/date)")

    t = pd.to_datetime(series[time_name].values)
    y = series.values.astype("float64")

    df = pd.DataFrame({"date": t, "discharge_cms": y})
    print(f"[INFO] extracted raw rows={df.shape[0]}")
    if args.start_date:
        df = df[df["date"] >= pd.Timestamp(args.start_date)]
    if args.end_date:
        df = df[df["date"] <= pd.Timestamp(args.end_date)]

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)

    df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_csv(args.out_csv, index=False)

    cell_lat = float(ds[lat_name].values[lat_i])
    cell_lon_raw = float(ds[lon_name].values[lon_i])
    meta: Dict[str, object] = {
        "input_nc": str(args.input_nc),
        "variable": var,
        "lat_coord_name": lat_name,
        "lon_coord_name": lon_name,
        "target_lat": args.lat,
        "target_lon": args.lon,
        "cell_mode": args.cell_mode,
        "sampled_mask_valid_cells": valid_count,
        "cell_lat_index": lat_i,
        "cell_lon_index": lon_i,
        "cell_lat": cell_lat,
        "cell_lon_raw": cell_lon_raw,
        "cell_lon_m180_180": to_m180_180(cell_lon_raw) if cell_lon_raw >= 0 else cell_lon_raw,
        "distance_km": dist_km,
        "n_rows": int(df.shape[0]),
        "start_date": df["date"].min().strftime("%Y-%m-%d") if not df.empty else "",
        "end_date": df["date"].max().strftime("%Y-%m-%d") if not df.empty else "",
    }
    args.out_meta.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    print(f"[OK] wrote {args.out_csv} rows={meta['n_rows']}")
    print(f"[OK] wrote {args.out_meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
