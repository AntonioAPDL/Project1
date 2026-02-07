#!/usr/bin/env python3
"""
Extract per-issue-date GloFAS forecast ensembles from downloaded GRIBs.

This is the high-throughput companion to `forecats_build_glofas_weighted.py`:
- It does *no* cross-issue weighting itself.
- It extracts the raw ensemble members (control + perturbed) for each issue_date
  and writes a small CSV:

    out_root/
      cell.json
      issue_date=YYYY-MM-DD/
        glofas_members.csv   # target_date + member_00..member_50 (cms)

The batch renderer (`scripts/forecats_batch.R`) can then copy these cached
files into each per-cutoff bundle and plot without reopening GRIBs.

Conventions are consistent with the existing pipeline:
- discharge in raw cms (m^3/s)
- target_date = issue_date + step_hours - shift_days
- for a cutoff_date == issue_date, forecast window is:
    forecast_start = cutoff_date + 1 day
    forecast_end   = cutoff_date + post_days
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr


def _to_0_360(lon: float) -> float:
    lon = lon % 360.0
    return 0.0 if abs(lon - 360.0) < 1e-12 else lon


def _to_m180_180(lon_0_360: float) -> float:
    return ((lon_0_360 + 180.0) % 360.0) - 180.0


def _haversine_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    r = 6371.0
    lat1r = np.deg2rad(lat1)
    lon1r = np.deg2rad(lon1)
    lat2r = np.deg2rad(lat2)
    lon2r = np.deg2rad(lon2)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2.0) ** 2
    return 2.0 * r * np.arcsin(np.sqrt(a))


def open_cf_pf(grib_path: Path, data_type: str) -> xr.Dataset:
    # indexpath='' avoids writing *.idx files.
    return xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={"indexpath": "", "filter_by_keys": {"dataType": data_type}},
    )


def _pick_var(ds: xr.Dataset, var: str) -> str:
    if var in ds.data_vars:
        return var
    return list(ds.data_vars)[0]


def pick_cell(ds_cf: xr.Dataset, target_lat: float, target_lon: float, var: str, cell_policy: str) -> Tuple[int, int, float]:
    if cell_policy not in {"nearest_valid", "nearest_any"}:
        raise ValueError(f"Unknown cell_policy: {cell_policy}")

    da = ds_cf[var]
    lats = da["latitude"].values
    lons = da["longitude"].values

    lat2d = np.repeat(lats[:, None], lons.size, axis=1)
    lon2d = np.repeat(lons[None, :], lats.size, axis=0)

    target_lon_0360 = _to_0_360(target_lon)
    dist = _haversine_km(target_lat, target_lon_0360, lat2d, lon2d)

    if cell_policy == "nearest_valid":
        finite_any = np.isfinite(da.values).any(axis=0)
        if not finite_any.any():
            raise RuntimeError("No finite values found anywhere in the GRIB (all NaN).")
        dist = np.where(finite_any, dist, np.inf)

    lat_i, lon_i = np.unravel_index(int(np.argmin(dist)), dist.shape)
    return int(lat_i), int(lon_i), float(dist[lat_i, lon_i])


@dataclass(frozen=True)
class CellInfo:
    target_lat: float
    target_lon: float
    var: str
    issue_date_ref: str
    grib_path_ref: str
    lat_i: int
    lon_i: int
    cell_lat: float
    cell_lon_0_360: float
    cell_lon_m180_180: float
    dist_km: float


def find_issue_grib(grib_root: Path, issue_date: date) -> Optional[Path]:
    d = grib_root / f"issue_date={issue_date.isoformat()}"
    if not d.exists():
        return None
    candidates = sorted(d.glob("*.grib"))
    if not candidates:
        return None
    ds = issue_date.isoformat()
    for p in candidates:
        if ds in p.name:
            return p
    return candidates[0]


def compute_step_hours(ds_cf: xr.Dataset) -> np.ndarray:
    step = ds_cf["step"].values
    return (step / np.timedelta64(1, "h")).astype(int)


def extract_issue_long(
    grib_path: Path,
    lat_i: int,
    lon_i: int,
    var: str,
    shift_days: int,
    control_dtype: str,
    perturbed_dtype: str,
) -> pd.DataFrame:
    ds_cf = open_cf_pf(grib_path, data_type=control_dtype)
    var = _pick_var(ds_cf, var)
    ds_pf = open_cf_pf(grib_path, data_type=perturbed_dtype)

    step_hours = compute_step_hours(ds_cf)
    issue_time = pd.Timestamp(ds_cf["time"].values).to_pydatetime()
    issue_date = issue_time.date()

    target_dates = pd.to_datetime(issue_date) + pd.to_timedelta(step_hours, unit="h") - pd.Timedelta(days=shift_days)
    target_dates_str = target_dates.strftime("%Y-%m-%d").to_numpy()

    cf_vals = ds_cf[var].isel(latitude=lat_i, longitude=lon_i).values.astype("float64")
    if cf_vals.ndim != 1:
        cf_vals = np.ravel(cf_vals)
    cf_member = np.zeros(cf_vals.size, dtype=int)

    pf_da = ds_pf[var].isel(latitude=lat_i, longitude=lon_i)
    pf_vals = pf_da.values.astype("float64")
    if pf_vals.ndim != 2:
        pf_vals = np.reshape(pf_vals, (pf_vals.shape[0], -1))
    pf_numbers = ds_pf["number"].values.astype(int)

    n_num, n_step = pf_vals.shape
    pf_member = np.repeat(pf_numbers, n_step)
    pf_lead = np.tile(step_hours, n_num)
    pf_target = np.tile(target_dates_str, n_num)
    pf_val = pf_vals.reshape(-1)

    out = pd.DataFrame(
        {
            "issue_date": issue_date.isoformat(),
            "target_date": np.concatenate([target_dates_str, pf_target]),
            "member": np.concatenate([cf_member, pf_member]),
            "lead_time_h": np.concatenate([step_hours, pf_lead]),
            "discharge_cms": np.concatenate([cf_vals, pf_val]),
        }
    )
    return out


def read_dates(path: Path) -> List[date]:
    out: List[date] = []
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(datetime.strptime(s, "%Y-%m-%d").date())
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grib-root", required=True, type=Path)
    ap.add_argument("--dates-file", required=True, type=Path, help="One cutoff/issue date per line (YYYY-MM-DD).")
    ap.add_argument("--out-root", required=True, type=Path)
    ap.add_argument("--lat", required=True, type=float)
    ap.add_argument("--lon", required=True, type=float)
    ap.add_argument("--var", default="dis24", type=str)
    ap.add_argument("--control-dtype", default="cf", type=str)
    ap.add_argument("--perturbed-dtype", default="pf", type=str)
    ap.add_argument("--cell-policy", default="nearest_valid", choices=["nearest_valid", "nearest_any"])
    ap.add_argument("--shift-days", default=1, type=int)
    ap.add_argument("--post-days", default=28, type=int, help="plot_post_days; forecast_end = cutoff + post_days")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    dates = read_dates(args.dates_file)
    if not dates:
        raise SystemExit("dates-file is empty")

    args.out_root.mkdir(parents=True, exist_ok=True)

    # Pick a reference issue_date GRIB to lock the grid cell.
    ref_grib = None
    ref_issue = None
    for d in dates:
        ref_grib = find_issue_grib(args.grib_root, d)
        if ref_grib is not None:
            ref_issue = d
            break
    if ref_grib is None or ref_issue is None:
        raise SystemExit(f"No GRIB found for any provided issue_date under {args.grib_root}")

    ds_cf_ref = open_cf_pf(ref_grib, data_type=args.control_dtype)
    var = _pick_var(ds_cf_ref, args.var)
    lat_i, lon_i, dist_km = pick_cell(ds_cf_ref, args.lat, args.lon, var, cell_policy=args.cell_policy)
    cell_lat = float(ds_cf_ref["latitude"].values[lat_i])
    cell_lon = float(ds_cf_ref["longitude"].values[lon_i])

    cell = CellInfo(
        target_lat=args.lat,
        target_lon=args.lon,
        var=var,
        issue_date_ref=ref_issue.isoformat(),
        grib_path_ref=str(ref_grib),
        lat_i=lat_i,
        lon_i=lon_i,
        cell_lat=cell_lat,
        cell_lon_0_360=cell_lon,
        cell_lon_m180_180=_to_m180_180(cell_lon),
        dist_km=dist_km,
    )
    # In batch mode we often shard extraction over multiple processes that share the same out_root.
    # Avoid racy concurrent writes unless the user explicitly requested overwrite.
    cell_path = args.out_root / "cell.json"
    if args.overwrite or (not cell_path.exists()):
        cell_path.write_text(json.dumps(asdict(cell), indent=2, sort_keys=True))

    n_ok = 0
    n_skip = 0
    n_missing = 0

    for cutoff in dates:
        out_dir = args.out_root / f"issue_date={cutoff.isoformat()}"
        out_path = out_dir / "glofas_members.csv"
        if out_path.exists() and not args.overwrite:
            n_skip += 1
            continue

        grib_path = find_issue_grib(args.grib_root, cutoff)
        if grib_path is None:
            n_missing += 1
            if args.verbose:
                print(f"[MISS] {cutoff.isoformat()} (no GRIB found)")
            continue

        df_long = extract_issue_long(
            grib_path=grib_path,
            lat_i=lat_i,
            lon_i=lon_i,
            var=var,
            shift_days=int(args.shift_days),
            control_dtype=args.control_dtype,
            perturbed_dtype=args.perturbed_dtype,
        )

        forecast_start = cutoff + timedelta(days=1)
        forecast_end = cutoff + timedelta(days=int(args.post_days))

        df_long = df_long[
            (df_long["target_date"] >= forecast_start.isoformat()) & (df_long["target_date"] <= forecast_end.isoformat())
        ]

        # Wide: target_date x member -> discharge_cms
        wide = (
            df_long.pivot(index="target_date", columns="member", values="discharge_cms")
            .sort_index()
            .reindex(pd.date_range(forecast_start, forecast_end, freq="D").strftime("%Y-%m-%d"))
        )

        # Rename members to member_00..member_50
        wide = wide.rename(columns={int(c): f"member_{int(c):02d}" for c in wide.columns})
        wide.index.name = "target_date"

        out_dir.mkdir(parents=True, exist_ok=True)
        wide.reset_index().to_csv(out_path, index=False)
        n_ok += 1

        if args.verbose and (n_ok % 50 == 0):
            print(f"[OK] wrote {n_ok} issue_dates ... (latest {cutoff.isoformat()})")

    if args.verbose:
        print(f"[DONE] ok={n_ok} skipped={n_skip} missing={n_missing} out_root={args.out_root}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
