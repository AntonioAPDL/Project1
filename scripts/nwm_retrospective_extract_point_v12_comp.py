#!/usr/bin/env python3
"""Extract a single-point NWM v1.2 retrospective streamflow series from CHRTOUT .comp files.

This script is designed for metadata-safe and pilot workflows:
- It reads only requested hours.
- It can cap processing with --max-hours for quick validation.
- It supports fixed feature_id or nearest-feature selection on first successful file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import netCDF4
import numpy as np
import pandas as pd

from flow_scale import TRANSFORM_SCALES, forward_transform_cms, inverse_transform_to_cms


@dataclass
class ExtractionMeta:
    version: str
    bucket: str
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
    requested_hours: int
    downloaded_hours: int
    missing_hours: int
    rows_out: int
    max_hours: int
    created_utc: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Extract NWM v1.2 retrospective point streamflow from nwm-archive CHRTOUT .comp files."
    )
    p.add_argument("--bucket", default="nwm-archive", help="S3 bucket name.")
    p.add_argument("--version", default="1.2", help="NWM version label.")
    p.add_argument("--lat", type=float, required=True, help="Target latitude.")
    p.add_argument("--lon", type=float, required=True, help="Target longitude.")
    p.add_argument("--start-date", required=True, help="Start date YYYY-MM-DD (inclusive).")
    p.add_argument("--end-date", required=True, help="End date YYYY-MM-DD (inclusive).")
    p.add_argument("--feature-id", type=int, default=None, help="Optional fixed feature_id.")
    p.add_argument("--var", default="streamflow", help="Variable name in CHRTOUT files.")
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
    p.add_argument(
        "--max-hours",
        type=int,
        default=0,
        help="Optional cap for processed hours (0 means all requested hours).",
    )
    p.add_argument(
        "--aws-retries",
        type=int,
        default=4,
        help="Retries per hourly S3 copy attempt.",
    )
    p.add_argument(
        "--retry-sleep-sec",
        type=float,
        default=2.0,
        help="Sleep seconds between retries.",
    )
    p.add_argument(
        "--missing-hours-csv",
        default="",
        help="Optional output CSV path for missing-hour keys.",
    )
    p.add_argument("--out-csv", required=True, help="Output CSV path.")
    p.add_argument("--out-meta", required=True, help="Output metadata JSON path.")
    return p.parse_args()


def s3_key_for_hour(ts: pd.Timestamp) -> str:
    return f"{ts:%Y}/{ts:%Y%m%d%H}00.CHRTOUT_DOMAIN1.comp"


def aws_cp_no_sign_request(src: str, dst: str, retries: int, retry_sleep_sec: float) -> bool:
    import time

    cmd = ["aws", "s3", "cp", "--no-sign-request", src, dst]
    attempts = max(1, retries)
    for i in range(attempts):
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if p.returncode == 0:
            return True
        if i < attempts - 1:
            time.sleep(max(0.0, retry_sleep_sec))
    return False


def find_feature_index(
    ds: netCDF4.Dataset,
    target_lat: float,
    target_lon: float,
    requested_feature_id: Optional[int],
) -> Dict[str, float]:
    feature_ids = np.asarray(ds.variables["feature_id"][:]).astype(np.int64)

    if requested_feature_id is not None:
        idx = np.where(feature_ids == requested_feature_id)[0]
        if len(idx) == 0:
            raise ValueError(f"feature_id={requested_feature_id} not found in this file.")
        feature_idx = int(idx[0])
    else:
        if "latitude" not in ds.variables or "longitude" not in ds.variables:
            raise ValueError("latitude/longitude variables are required for nearest-feature lookup.")
        lat_arr = np.asarray(ds.variables["latitude"][:], dtype=float)
        lon_arr = np.asarray(ds.variables["longitude"][:], dtype=float)
        dist = np.sqrt((lat_arr - target_lat) ** 2 + (lon_arr - target_lon) ** 2)
        feature_idx = int(np.argmin(dist))

    if "latitude" in ds.variables and "longitude" in ds.variables:
        selected_lat = float(np.asarray(ds.variables["latitude"][:], dtype=float)[feature_idx])
        selected_lon = float(np.asarray(ds.variables["longitude"][:], dtype=float)[feature_idx])
    else:
        selected_lat = float("nan")
        selected_lon = float("nan")

    distance_deg = (
        float(np.sqrt((selected_lat - target_lat) ** 2 + (selected_lon - target_lon) ** 2))
        if np.isfinite(selected_lat) and np.isfinite(selected_lon)
        else float("nan")
    )

    return {
        "feature_idx": feature_idx,
        "feature_id": int(feature_ids[feature_idx]),
        "feature_latitude": selected_lat,
        "feature_longitude": selected_lon,
        "distance_deg": distance_deg,
    }


def main() -> int:
    args = parse_args()
    out_csv = Path(args.out_csv)
    out_meta = Path(args.out_meta)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp(args.start_date)
    end = pd.Timestamp(args.end_date) + pd.Timedelta(hours=23)
    hourly = pd.date_range(start, end, freq="h")
    if args.max_hours > 0:
        hourly = hourly[: args.max_hours]

    feature_info: Optional[Dict[str, float]] = None
    rows: List[Dict[str, object]] = []
    missing: List[Dict[str, str]] = []

    with tempfile.TemporaryDirectory(prefix="nwm_v12_comp_") as tmpdir:
        tmp_path = Path(tmpdir) / "hour.comp"
        for ts in hourly:
            key = s3_key_for_hour(ts)
            src = f"s3://{args.bucket}/{key}"
            ok = aws_cp_no_sign_request(
                src=src,
                dst=str(tmp_path),
                retries=int(args.aws_retries),
                retry_sleep_sec=float(args.retry_sleep_sec),
            )
            if not ok:
                missing.append({"datetime_utc": ts.isoformat(), "s3_key": key})
                continue

            try:
                ds = netCDF4.Dataset(str(tmp_path), mode="r")
            except Exception:
                missing.append({"datetime_utc": ts.isoformat(), "s3_key": key})
                continue

            try:
                if feature_info is None:
                    feature_info = find_feature_index(ds, args.lat, args.lon, args.feature_id)

                if args.var not in ds.variables:
                    raise ValueError(f"Variable '{args.var}' not found in {key}")

                stream = np.asarray(ds.variables[args.var][:], dtype=float)
                value = float(stream[int(feature_info["feature_idx"])])
                rows.append(
                    {
                        "datetime_utc": ts,
                        "streamflow_cms": value,
                        "version": args.version,
                        "feature_id": int(feature_info["feature_id"]),
                        "feature_latitude": float(feature_info["feature_latitude"]),
                        "feature_longitude": float(feature_info["feature_longitude"]),
                        "target_latitude": float(args.lat),
                        "target_longitude": float(args.lon),
                        "distance_deg": float(feature_info["distance_deg"]),
                    }
                )
            finally:
                ds.close()

    if len(rows) == 0:
        raise RuntimeError("No rows extracted. Check bucket access, dates, and variable.")

    df = pd.DataFrame(rows).sort_values("datetime_utc")
    if args.aggregate == "daily":
        df["work_value"] = forward_transform_cms(df["streamflow_cms"], args.aggregation_scale)
        daily_work = (
            df.assign(date=pd.to_datetime(df["datetime_utc"]).dt.floor("D"))
            .groupby("date", as_index=False)["work_value"]
            .mean()
            .rename(columns={"work_value": "mean_work_value"})
        )
        out = (
            df.assign(date=pd.to_datetime(df["datetime_utc"]).dt.floor("D"))
            .groupby("date", as_index=False)["streamflow_cms"]
            .mean()
            .rename(columns={"streamflow_cms": "mean_raw_cms"})
            .assign(
                version=args.version,
                feature_id=int(feature_info["feature_id"]),
                feature_latitude=float(feature_info["feature_latitude"]),
                feature_longitude=float(feature_info["feature_longitude"]),
                target_latitude=float(args.lat),
                target_longitude=float(args.lon),
                distance_deg=float(feature_info["distance_deg"]),
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
        out = df[
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

    if args.missing_hours_csv:
        miss_path = Path(args.missing_hours_csv)
        miss_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(missing).to_csv(miss_path, index=False)

    meta = ExtractionMeta(
        version=args.version,
        bucket=args.bucket,
        variable=args.var,
        selected_feature_id=int(feature_info["feature_id"]),
        selected_feature_index=int(feature_info["feature_idx"]),
        selected_latitude=float(feature_info["feature_latitude"]),
        selected_longitude=float(feature_info["feature_longitude"]),
        target_latitude=float(args.lat),
        target_longitude=float(args.lon),
        distance_deg=float(feature_info["distance_deg"]),
        start_date=args.start_date,
        end_date=args.end_date,
        aggregate=args.aggregate,
        aggregation_scale=args.aggregation_scale,
        requested_hours=int(len(hourly)),
        downloaded_hours=int(len(df)),
        missing_hours=int(len(missing)),
        rows_out=int(len(out)),
        max_hours=int(args.max_hours),
        created_utc=datetime.now(timezone.utc).isoformat(),
    )
    out_meta.write_text(json.dumps(asdict(meta), indent=2))

    print(f"[OK] wrote {out_csv} ({len(out)} rows)")
    print(f"[OK] wrote {out_meta}")
    if args.missing_hours_csv:
        print(f"[OK] wrote {args.missing_hours_csv} ({len(missing)} missing hours)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
