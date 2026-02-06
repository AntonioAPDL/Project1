#!/usr/bin/env python3
"""
Build a *weighted* daily GloFAS forecast ensemble at a single point from downloaded GRIBs.

This is the "raw -> weighted" step that historically produced `weighted_time_series.csv`,
but generalized to any cutoff_date and output bundle directory.

Key conventions (matches `glofas_forecasts.ipynb` in default mode):
- Extract raw discharge (cms) from GRIB shortName `dis24` at a chosen grid cell.
- Transform values with log1p(cms).
- For each (target_date, member), compute a weighted average over contributing forecasts:
    weights = lead_time_hours ** power   (power < 0 => shorter lead gets more weight)
    normalized within each (target_date, member)
    weighted_avg_log1p = sum(weights * log1p(value))
- Store outputs in raw cms by inverting: cms = expm1(weighted_avg_log1p).

Paper-mode support:

- In the paper, weights are described as a function of "age" r (days before the cutoff T),
  rather than a function of lead time. To compare "paper-mode" vs "notebook-mode"
  apples-to-apples, we implement paper-mode as:

    weights = (r_days + 1) ** (-alpha)   where r_days = cutoff_date - issue_date

  and still compute the weighted average on the log1p scale (so only the weight kernel
  differs, not the value transform).

Target-date convention (matches notebook):
    target_date = issue_date + lead_time - shift_days
where shift_days defaults to 1 day.

Notes:
- We avoid cfgrib index files by setting backend_kwargs={"indexpath": ""}.
- We support a simple per-issue-date cache under --cache-dir (npz files),
  intended to be bundle/run specific.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr


def _to_0_360(lon: float) -> float:
    lon = lon % 360.0
    return 0.0 if abs(lon - 360.0) < 1e-12 else lon


def _to_m180_180(lon_0_360: float) -> float:
    return ((lon_0_360 + 180.0) % 360.0) - 180.0


def _haversine_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    # Vectorized haversine. Inputs in degrees.
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
    # Fall back to first variable if caller passed a wrong shortName.
    return list(ds.data_vars)[0]


def pick_cell(
    ds_cf: xr.Dataset, target_lat: float, target_lon: float, var: str, cell_policy: str
) -> Tuple[int, int, float]:
    """
    Choose a grid cell for point extraction.

    Policies:
    - nearest_valid: nearest cell that is finite for at least one lead time (avoid river-mask NaNs).
    - nearest_any  : nearest cell purely by distance (matches older notebook logic that didn't mask NaNs).
    """
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
        # Shape: (step, lat, lon)
        finite_any = np.isfinite(da.values).any(axis=0)
        if not finite_any.any():
            raise RuntimeError("No finite values found anywhere in the bbox (all NaN).")
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
    # Prefer file containing the date in its name (if present).
    ds = issue_date.isoformat()
    for p in candidates:
        if ds in p.name:
            return p
    return candidates[0]


def compute_step_hours(ds_cf: xr.Dataset) -> np.ndarray:
    step = ds_cf["step"].values
    # step is timedelta64; convert to hours int.
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
    # Issue time in GRIB is a scalar coord.
    issue_time = pd.Timestamp(ds_cf["time"].values).to_pydatetime()
    issue_date = issue_time.date()

    target_dates = pd.to_datetime(issue_date) + pd.to_timedelta(step_hours, unit="h") - pd.Timedelta(days=shift_days)
    target_dates_str = target_dates.strftime("%Y-%m-%d").to_numpy()

    cf_vals = ds_cf[var].isel(latitude=lat_i, longitude=lon_i).values.astype("float64")
    if cf_vals.ndim != 1:
        cf_vals = np.ravel(cf_vals)
    cf_member = np.zeros(cf_vals.size, dtype=int)

    # Perturbed: number x step
    pf_da = ds_pf[var].isel(latitude=lat_i, longitude=lon_i)
    pf_vals = pf_da.values.astype("float64")
    if pf_vals.ndim != 2:
        pf_vals = np.reshape(pf_vals, (pf_vals.shape[0], -1))
    pf_numbers = ds_pf["number"].values.astype(int)

    # Long-form for pf (number-major flatten)
    n_num, n_step = pf_vals.shape
    pf_member = np.repeat(pf_numbers, n_step)
    pf_lead = np.tile(step_hours, n_num)
    pf_target = np.tile(target_dates_str, n_num)
    pf_val = pf_vals.reshape(-1)

    # Long-form for control (member 0)
    cf_lead = step_hours
    cf_target = target_dates_str
    cf_val = cf_vals

    out = pd.DataFrame(
        {
            "issue_date": issue_date.isoformat(),
            "target_date": np.concatenate([cf_target, pf_target]),
            "lead_time_h": np.concatenate([cf_lead, pf_lead]),
            "member": np.concatenate([cf_member, pf_member]),
            "discharge_cms": np.concatenate([cf_val, pf_val]),
        }
    )
    return out


def cache_path(cache_dir: Path, issue_date: str) -> Path:
    return cache_dir / f"issue_date={issue_date}.npz"


def load_issue_cache(npz_path: Path) -> pd.DataFrame:
    # Cache files are generated locally by this script. Use allow_pickle=True for
    # backward compatibility with older caches that stored object arrays.
    z = np.load(npz_path, allow_pickle=False)
    try:
        issue_date = z["issue_date"].astype(str)
        target_date = z["target_date"].astype(str)
    except ValueError:
        z.close()
        z = np.load(npz_path, allow_pickle=True)
        issue_date = z["issue_date"].astype(str)
        target_date = z["target_date"].astype(str)
    return pd.DataFrame(
        {
            "issue_date": issue_date,
            "target_date": target_date,
            "lead_time_h": z["lead_time_h"].astype(int),
            "member": z["member"].astype(int),
            "discharge_cms": z["discharge_cms"].astype("float64"),
        }
    )


def write_issue_cache(npz_path: Path, df: pd.DataFrame) -> None:
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        npz_path,
        # Force fixed-width unicode to avoid object arrays in .npz.
        issue_date=np.asarray(df["issue_date"].astype(str).to_numpy(), dtype="U10"),
        target_date=np.asarray(df["target_date"].astype(str).to_numpy(), dtype="U10"),
        lead_time_h=df["lead_time_h"].astype(int).to_numpy(),
        member=df["member"].astype(int).to_numpy(),
        discharge_cms=df["discharge_cms"].astype("float64").to_numpy(),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grib-root", required=True, type=Path)
    ap.add_argument("--cutoff-date", required=True, type=str, help="YYYY-MM-DD")
    ap.add_argument("--forecast-start-date", required=True, type=str, help="YYYY-MM-DD")
    ap.add_argument("--forecast-end-date", required=True, type=str, help="YYYY-MM-DD")
    ap.add_argument("--lat", required=True, type=float)
    ap.add_argument("--lon", required=True, type=float)
    ap.add_argument("--var", default="dis24", type=str)
    ap.add_argument("--control-dtype", default="cf", type=str)
    ap.add_argument("--perturbed-dtype", default="pf", type=str)
    ap.add_argument(
        "--cell-policy",
        default="nearest_valid",
        choices=["nearest_valid", "nearest_any"],
        help="Grid-cell selection policy for point extraction.",
    )
    ap.add_argument(
        "--weighting-scheme",
        default="paper",
        choices=["notebook", "paper", "latest"],
        help=(
            "Weighting scheme: "
            "'notebook' (lead-time power on log1p), "
            "'paper' (age-based power on log1p), or "
            "'latest' (alpha->inf: pick the most recent issue_date per (target_date, member))."
        ),
    )
    ap.add_argument("--power", default=-1.001, type=float)
    ap.add_argument("--alpha", default=1.0, type=float, help="Paper-mode exponent alpha (weights ~ (r_days+1)^-alpha).")
    ap.add_argument("--shift-days", default=1, type=int)
    ap.add_argument("--cache-dir", default=None, type=Path)
    ap.add_argument("--cell-json", required=True, type=Path)
    ap.add_argument("--out-csv", required=True, type=Path)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cutoff = datetime.strptime(args.cutoff_date, "%Y-%m-%d").date()
    forecast_start = datetime.strptime(args.forecast_start_date, "%Y-%m-%d").date()
    forecast_end = datetime.strptime(args.forecast_end_date, "%Y-%m-%d").date()

    if forecast_start > forecast_end:
        raise SystemExit("forecast-start-date must be <= forecast-end-date")

    if args.out_csv.exists() and not (args.overwrite):
        if args.verbose:
            print(f"[SKIP] out exists: {args.out_csv}")
        return 0

    # Pick a reference issue_date GRIB at/near cutoff to lock the grid cell.
    ref_grib = find_issue_grib(args.grib_root, cutoff)
    ref_issue = cutoff
    if ref_grib is None:
        # Walk backwards up to 60 days to find an available file.
        for dd in range(1, 61):
            cand = cutoff - timedelta(days=dd)
            ref_grib = find_issue_grib(args.grib_root, cand)
            if ref_grib is not None:
                ref_issue = cand
                break
    if ref_grib is None:
        raise SystemExit(f"No GRIB found at or before cutoff_date={cutoff.isoformat()} under {args.grib_root}")

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
    args.cell_json.parent.mkdir(parents=True, exist_ok=True)
    args.cell_json.write_text(json.dumps(asdict(cell), indent=2, sort_keys=True))

    # Determine the issue-date window that can contribute to the requested target_date window.
    #
    # target_date = issue_date + lead_days - shift_days
    # max(target_date) for an issue_date is issue_date + max_lead_days - shift_days.
    # For any contribution, we need:
    #   issue_date + max_lead_days - shift_days >= forecast_start
    # => issue_date >= forecast_start - (max_lead_days - shift_days)
    step_hours = compute_step_hours(ds_cf_ref)
    max_lead_days = int(np.max(step_hours) // 24)
    issue_start = forecast_start - timedelta(days=max_lead_days - int(args.shift_days))
    if issue_start > cutoff:
        issue_start = cutoff
    issue_dates = [issue_start + timedelta(days=i) for i in range((cutoff - issue_start).days + 1)]

    if args.verbose:
        print(f"[INFO] ref_issue_date={ref_issue.isoformat()} var={var} picked_cell=({cell_lat:.5f},{cell_lon:.5f}) dist_km={dist_km:.2f}")
        print(f"[INFO] scanning issue_dates: {issue_start.isoformat()}..{cutoff.isoformat()} (n={len(issue_dates)})")

    cache_dir = args.cache_dir
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)

    dfs: List[pd.DataFrame] = []
    missing: List[str] = []
    for d in issue_dates:
        grib_path = find_issue_grib(args.grib_root, d)
        if grib_path is None:
            missing.append(d.isoformat())
            continue

        if cache_dir is not None:
            npz = cache_path(cache_dir, d.isoformat())
            if npz.exists() and not args.overwrite:
                df_issue = load_issue_cache(npz)
            else:
                df_issue = extract_issue_long(
                    grib_path=grib_path,
                    lat_i=lat_i,
                    lon_i=lon_i,
                    var=var,
                    shift_days=args.shift_days,
                    control_dtype=args.control_dtype,
                    perturbed_dtype=args.perturbed_dtype,
                )
                write_issue_cache(npz, df_issue)
        else:
            df_issue = extract_issue_long(
                grib_path=grib_path,
                lat_i=lat_i,
                lon_i=lon_i,
                var=var,
                shift_days=args.shift_days,
                control_dtype=args.control_dtype,
                perturbed_dtype=args.perturbed_dtype,
            )

        # Filter to target_date window early to keep memory small.
        df_issue = df_issue[
            (df_issue["target_date"] >= forecast_start.isoformat()) & (df_issue["target_date"] <= forecast_end.isoformat())
        ]
        if not df_issue.empty:
            dfs.append(df_issue)

    if not dfs:
        raise SystemExit("No forecast values found in the requested target_date window. Check dates and downloads.")

    df = pd.concat(dfs, ignore_index=True)

    # Weighting always happens on log1p scale for comparability.
    df["log1p_cms"] = np.log1p(df["discharge_cms"].astype("float64"))
    if args.weighting_scheme == "notebook":
        lead = df["lead_time_h"].astype("float64").replace(0.0, 1.0)
        df["w_raw"] = np.power(lead, args.power)
    elif args.weighting_scheme == "paper":
        # Allow alpha <= 0 for sensitivity experiments:
        # - alpha = 0   -> uniform weights across issue_dates
        # - alpha < 0   -> older issue_dates receive *more* weight
        # These are not "paper default" but are useful for diagnostics.
        # Age in days relative to cutoff (T in the paper): r_days = T - issue_date.
        issue_dt = pd.to_datetime(df["issue_date"], format="%Y-%m-%d", errors="coerce")
        r_days = (pd.Timestamp(cutoff) - issue_dt).dt.days.astype("float64")
        df["w_raw"] = 1.0 / np.power(r_days + 1.0, args.alpha)
    elif args.weighting_scheme == "latest":
        # Equivalent to alpha -> +inf in paper-mode:
        # pick the most recent issue_date within each (target_date, member) group.
        issue_dt = pd.to_datetime(df["issue_date"], format="%Y-%m-%d", errors="coerce")
        r_days = (pd.Timestamp(cutoff) - issue_dt).dt.days.astype("float64")
        # Keep only rows with minimal r_days per group.
        r_min = r_days.groupby([df["target_date"], df["member"]]).transform("min")
        keep = (r_days == r_min) & np.isfinite(df["log1p_cms"].to_numpy())
        df = df.loc[keep].copy()
        # If there are any ties, average them uniformly (rare; mostly a no-op).
        df["w_raw"] = 1.0
    else:
        raise SystemExit(f"Unknown weighting_scheme: {args.weighting_scheme}")

    # Normalize within (target_date, member) and compute weighted mean on log1p scale.
    denom = df.groupby(["target_date", "member"])["w_raw"].transform("sum")
    df["w"] = df["w_raw"] / denom
    df["w_log1p"] = df["w"] * df["log1p_cms"]

    out_log1p = (
        df.groupby(["target_date", "member"], as_index=False)["w_log1p"]
        .sum()
        .pivot(index="target_date", columns="member", values="w_log1p")
        .sort_index()
    )

    # Ensure full date coverage in the requested window.
    full_idx = pd.date_range(start=forecast_start, end=forecast_end, freq="D").strftime("%Y-%m-%d")
    out_log1p = out_log1p.reindex(full_idx)

    out_cms = np.expm1(out_log1p)

    # Column naming: member_00..member_50
    cols: Dict[int, str] = {int(m): f"member_{int(m):02d}" for m in out_cms.columns}
    out_cms = out_cms.rename(columns=cols)
    out_cms.index.name = "target_date"

    out_df = out_cms.reset_index()
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out_csv, index=False)

    if args.verbose:
        print(f"[OK] wrote {args.out_csv} rows={len(out_df)} cols={len(out_df.columns)}")
        if missing:
            print(f"[WARN] missing issue_dates (no GRIB dir/file): {len(missing)} (example: {missing[:5]})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
