#!/usr/bin/env python3
"""Extract target-point daily series from GloFAS historical campaign ZIP shards.

Input is the campaign output tree, e.g.:
  data/glofas_historical_consolidated_point/hist_v31_lisflood_cons/year=YYYY/month=MM/*.zip

Each zip is expected to contain one GRIB file (typically data.grib) with dis24 on a
small bbox grid over daily time steps.
"""

from __future__ import annotations

import argparse
import json
import math
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr


def to_0_360(lon: float) -> float:
    lon = lon % 360.0
    return 0.0 if abs(lon - 360.0) < 1e-12 else lon


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


def pick_var(ds: xr.Dataset, var: str) -> str:
    if var and var in ds.data_vars:
        return var
    if "dis24" in ds.data_vars:
        return "dis24"
    if not ds.data_vars:
        raise ValueError("Dataset has no data variables")
    return list(ds.data_vars)[0]


def pick_cell(da: xr.DataArray, target_lat: float, target_lon: float, policy: str) -> Tuple[int, int, float]:
    if policy not in {"nearest_valid", "nearest_any"}:
        raise ValueError(f"Unknown policy: {policy}")

    lats = da["latitude"].values
    lons = da["longitude"].values
    lat2d = np.repeat(lats[:, None], lons.size, axis=1)
    lon2d = np.repeat(lons[None, :], lats.size, axis=0)
    dist = haversine_km(target_lat, to_0_360(target_lon), lat2d, lon2d)

    if policy == "nearest_valid":
        arr = da.values
        finite_any = np.isfinite(arr).any(axis=0)
        if not finite_any.any():
            raise RuntimeError("No finite values in any grid cell")
        dist = np.where(finite_any, dist, np.inf)

    lat_i, lon_i = np.unravel_index(int(np.argmin(dist)), dist.shape)
    return int(lat_i), int(lon_i), float(dist[lat_i, lon_i])


def find_grib_in_zip(z: zipfile.ZipFile) -> str:
    names = z.namelist()
    for n in names:
        nl = n.lower()
        if nl.endswith(".grib") or nl.endswith(".grib2"):
            return n
    for n in names:
        nl = n.lower()
        if nl.endswith(".nc") or nl.endswith(".nc4"):
            return n
    if len(names) == 1:
        return names[0]
    raise RuntimeError(f"Could not identify GRIB/NetCDF payload in zip entries: {names[:10]}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Extract point daily series from historical campaign ZIP shards")
    ap.add_argument("--campaign-root", type=Path, required=True)
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-meta", type=Path, required=True)
    ap.add_argument("--lat", type=float, default=37.0443931)
    ap.add_argument("--lon", type=float, default=-122.072464)
    ap.add_argument("--var", default="dis24")
    ap.add_argument("--cell-policy", default="nearest_valid", choices=["nearest_valid", "nearest_any"])
    ap.add_argument("--start-date", default="")
    ap.add_argument("--end-date", default="")
    ap.add_argument("--verbose", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    zips = sorted(args.campaign_root.rglob("*.zip"))
    if not zips:
        raise SystemExit(f"No zip shards found under {args.campaign_root}")

    lat_i: Optional[int] = None
    lon_i: Optional[int] = None
    dist_km: Optional[float] = None
    cell_lat: Optional[float] = None
    cell_lon_raw: Optional[float] = None
    var_name: Optional[str] = None
    ref_zip: Optional[Path] = None

    rows: List[pd.DataFrame] = []

    for i, zpath in enumerate(zips, start=1):
        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(zpath) as zf:
                payload = find_grib_in_zip(zf)
                extracted = Path(zf.extract(payload, td))

            ds = xr.open_dataset(str(extracted), engine="cfgrib", backend_kwargs={"indexpath": ""})
            v = pick_var(ds, args.var)
            da = ds[v]

            if lat_i is None or lon_i is None:
                li, lj, dk = pick_cell(da, args.lat, args.lon, args.cell_policy)
                lat_i, lon_i, dist_km = li, lj, dk
                cell_lat = float(da["latitude"].values[lat_i])
                cell_lon_raw = float(da["longitude"].values[lon_i])
                var_name = v
                ref_zip = zpath

            # Time coordinate in historical shards is daily over month.
            tname = "time" if "time" in da.coords else ("valid_time" if "valid_time" in da.coords else None)
            if tname is None:
                raise RuntimeError(f"No time coordinate found in shard: {zpath}")

            t = pd.to_datetime(da[tname].values)
            y = da.isel(latitude=lat_i, longitude=lon_i).values.astype("float64")
            out = pd.DataFrame(
                {
                    "date": t,
                    "discharge_cms": y,
                    "source_zip": str(zpath),
                }
            )
            rows.append(out)

        if args.verbose and (i % 50 == 0 or i == len(zips)):
            print(f"[INFO] processed {i}/{len(zips)} shards")

    df = pd.concat(rows, ignore_index=True)
    df = df.dropna(subset=["date", "discharge_cms"]).sort_values("date").drop_duplicates(subset=["date"], keep="last")

    if args.start_date:
        df = df[df["date"] >= pd.Timestamp(args.start_date)]
    if args.end_date:
        df = df[df["date"] <= pd.Timestamp(args.end_date)]

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)

    out_csv = df.copy()
    out_csv["date"] = out_csv["date"].dt.strftime("%Y-%m-%d")
    out_csv.to_csv(args.out_csv, index=False)

    meta: Dict[str, object] = {
        "campaign_root": str(args.campaign_root),
        "n_zip_shards": len(zips),
        "variable": var_name,
        "target_lat": args.lat,
        "target_lon": args.lon,
        "cell_policy": args.cell_policy,
        "cell_lat_index": lat_i,
        "cell_lon_index": lon_i,
        "cell_lat": cell_lat,
        "cell_lon_raw": cell_lon_raw,
        "cell_lon_m180_180": to_m180_180(cell_lon_raw) if cell_lon_raw is not None and cell_lon_raw >= 0 else cell_lon_raw,
        "distance_km": dist_km,
        "reference_zip": str(ref_zip) if ref_zip else "",
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
