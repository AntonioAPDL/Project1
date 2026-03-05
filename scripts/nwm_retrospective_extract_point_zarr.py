#!/usr/bin/env python3
"""Extract a single-point NWM retrospective streamflow series from a Zarr source."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import fsspec
import numpy as np
import pandas as pd
import xarray as xr

from flow_scale import TRANSFORM_SCALES, forward_transform_cms, inverse_transform_to_cms


@dataclass
class ExtractionMeta:
    version: str
    zarr_url: str
    variable: str
    selected_feature_id: int
    selected_feature_index: int
    selected_latitude: float
    selected_longitude: float
    target_latitude: float
    target_longitude: float
    distance_deg: float
    start_date: str
    end_date: str
    aggregate: str
    aggregation_scale: str
    rows_out: int
    created_utc: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract NWM retrospective point series from a public Zarr store.")
    p.add_argument("--zarr-url", required=True, help="Zarr URL (s3://...).")
    p.add_argument("--version", required=True, help="NWM version label (e.g., 2.0, 2.1, 3.0).")
    p.add_argument("--lat", type=float, required=True, help="Target latitude.")
    p.add_argument("--lon", type=float, required=True, help="Target longitude.")
    p.add_argument("--start-date", required=True, help="Start date YYYY-MM-DD.")
    p.add_argument("--end-date", required=True, help="End date YYYY-MM-DD.")
    p.add_argument("--feature-id", type=int, default=None, help="Optional fixed feature_id.")
    p.add_argument("--var", default="streamflow", help="Streamflow variable name.")
    p.add_argument(
        "--aggregate",
        choices=("hourly", "daily"),
        default="daily",
        help="Output aggregation level.",
    )
    p.add_argument(
        "--aggregation-scale",
        choices=list(TRANSFORM_SCALES),
        default="log1p_cms",
        help="Transform scale used when --aggregate=daily.",
    )
    p.add_argument("--out-csv", required=True, help="Output CSV path.")
    p.add_argument("--out-meta", required=True, help="Output metadata JSON path.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_csv = Path(args.out_csv)
    out_meta = Path(args.out_meta)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)

    mapper = fsspec.get_mapper(args.zarr_url, anon=True)
    ds = xr.open_zarr(mapper, consolidated=True)

    if args.var not in ds.data_vars:
        vars_avail = sorted(list(ds.data_vars))
        raise ValueError(f"Variable '{args.var}' not found. Available variables: {vars_avail}")

    if "feature_id" not in ds.coords and "feature_id" not in ds.variables:
        raise ValueError("feature_id coordinate not found in dataset.")
    if "latitude" not in ds.variables or "longitude" not in ds.variables:
        raise ValueError("latitude/longitude coordinates are required but missing.")

    feature_ids = np.asarray(ds["feature_id"].values)
    lat_arr = np.asarray(ds["latitude"].values, dtype=float)
    lon_arr = np.asarray(ds["longitude"].values, dtype=float)

    if args.feature_id is not None:
        idx = np.where(feature_ids == args.feature_id)[0]
        if len(idx) == 0:
            raise ValueError(f"feature_id={args.feature_id} not present in dataset.")
        feature_idx = int(idx[0])
    else:
        dist = np.sqrt((lat_arr - args.lat) ** 2 + (lon_arr - args.lon) ** 2)
        feature_idx = int(np.argmin(dist))

    selected_feature_id = int(feature_ids[feature_idx])
    selected_lat = float(lat_arr[feature_idx])
    selected_lon = float(lon_arr[feature_idx])
    distance_deg = float(np.sqrt((selected_lat - args.lat) ** 2 + (selected_lon - args.lon) ** 2))

    da = ds[args.var].isel(feature_id=feature_idx).sel(time=slice(args.start_date, args.end_date))
    df = da.to_dataframe(name="streamflow_cms").reset_index()[["time", "streamflow_cms"]]
    df["streamflow_cms"] = pd.to_numeric(df["streamflow_cms"], errors="coerce")
    df = df.dropna(subset=["time"])

    if args.aggregate == "daily":
        df["date"] = pd.to_datetime(df["time"]).dt.floor("D")
        df["work_value"] = forward_transform_cms(df["streamflow_cms"], args.aggregation_scale)
        daily_work = (
            df.groupby("date", as_index=False)["work_value"]
            .mean()
            .rename(columns={"work_value": "mean_work_value"})
        )
        out = (
            df.groupby("date", as_index=False)["streamflow_cms"]
            .mean()
            .rename(columns={"streamflow_cms": "mean_raw_cms"})
            .assign(
                version=args.version,
                feature_id=selected_feature_id,
                feature_latitude=selected_lat,
                feature_longitude=selected_lon,
                target_latitude=float(args.lat),
                target_longitude=float(args.lon),
                distance_deg=distance_deg,
            )
        )
        out = out.merge(daily_work, on="date", how="left")
        out["streamflow_cms"] = inverse_transform_to_cms(
            out["mean_work_value"].to_numpy(dtype="float64"),
            args.aggregation_scale,
        )
        out = out[
            [
                "date",
                "streamflow_cms",
                "version",
                "feature_id",
                "feature_latitude",
                "feature_longitude",
                "target_latitude",
                "target_longitude",
                "distance_deg",
            ]
        ]
    else:
        out = (
            df.rename(columns={"time": "datetime_utc"})
            .assign(
                version=args.version,
                feature_id=selected_feature_id,
                feature_latitude=selected_lat,
                feature_longitude=selected_lon,
                target_latitude=float(args.lat),
                target_longitude=float(args.lon),
                distance_deg=distance_deg,
            )
        )
        out = out[
            [
                "datetime_utc",
                "streamflow_cms",
                "version",
                "feature_id",
                "feature_latitude",
                "feature_longitude",
                "target_latitude",
                "target_longitude",
                "distance_deg",
            ]
        ]

    out.to_csv(out_csv, index=False)

    meta = ExtractionMeta(
        version=args.version,
        zarr_url=args.zarr_url,
        variable=args.var,
        selected_feature_id=selected_feature_id,
        selected_feature_index=feature_idx,
        selected_latitude=selected_lat,
        selected_longitude=selected_lon,
        target_latitude=float(args.lat),
        target_longitude=float(args.lon),
        distance_deg=distance_deg,
        start_date=args.start_date,
        end_date=args.end_date,
        aggregate=args.aggregate,
        aggregation_scale=args.aggregation_scale,
        rows_out=int(len(out)),
        created_utc=datetime.now(timezone.utc).isoformat(),
    )
    out_meta.write_text(json.dumps(asdict(meta), indent=2))

    print(f"[OK] wrote {out_csv} ({len(out)} rows)")
    print(f"[OK] wrote {out_meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
