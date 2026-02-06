#!/usr/bin/env python3
"""
Quicklook a downloaded GloFAS GRIB by:
1) selecting the closest *non-missing* grid cell to a target (lat, lon), and
2) plotting readable ensemble time series, and optionally
3) producing a per-lead-time heatmap movie-frame set over the bbox.

Notes / gotchas handled:
- Many grid cells inside the bbox are masked (NaN) because they are not on the river network.
- Longitudes in GRIB are typically 0..360 (degrees_east); users often think in -180..180.
"""

from __future__ import annotations

import argparse
import math
import json
from pathlib import Path
from typing import Tuple

import warnings
import numpy as np
import xarray as xr


def _to_0_360(lon: float) -> float:
    lon = lon % 360.0
    # Keep 360 mapped to 0 for consistency
    return 0.0 if abs(lon - 360.0) < 1e-12 else lon


def _to_m180_180(lon_0_360: np.ndarray) -> np.ndarray:
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


def open_cf_pf(grib_path: Path) -> Tuple[xr.Dataset, xr.Dataset]:
    # indexpath='' avoids creating *.idx files in shared filesystems.
    ds_cf = xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={"indexpath": "", "filter_by_keys": {"dataType": "cf"}},
    )
    ds_pf = xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={"indexpath": "", "filter_by_keys": {"dataType": "pf"}},
    )
    return ds_cf, ds_pf


def pick_nearest_valid_cell(ds_cf: xr.Dataset, target_lat: float, target_lon: float, var: str) -> Tuple[int, int, float]:
    da = ds_cf[var]
    if "number" in da.dims:
        da = da.isel(number=0)

    # Mask: cell is valid if it has at least one finite value across lead times.
    finite_any = np.isfinite(da.values).any(axis=0)  # lat/lon
    if not finite_any.any():
        raise RuntimeError("No finite values found anywhere in the bbox (unexpected).")

    lats = da["latitude"].values
    lons = da["longitude"].values

    # Build 2D lat/lon grids matching finite_any
    lat2d = np.repeat(lats[:, None], lons.size, axis=1)
    lon2d = np.repeat(lons[None, :], lats.size, axis=0)

    # Ensure target lon matches GRIB convention (0..360)
    target_lon_0360 = _to_0_360(target_lon)

    dist = _haversine_km(target_lat, target_lon_0360, lat2d, lon2d)
    dist = np.where(finite_any, dist, np.inf)
    lat_i, lon_i = np.unravel_index(int(np.argmin(dist)), dist.shape)
    return int(lat_i), int(lon_i), float(dist[lat_i, lon_i])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grib", required=True, type=Path, help="Path to a downloaded *.grib file.")
    ap.add_argument("--lat", type=float, default=37.0443931, help="Target latitude (default: downloader default).")
    ap.add_argument("--lon", type=float, default=-122.072464, help="Target longitude (default: downloader default).")
    ap.add_argument("--var", type=str, default="dis24", help="Variable name in GRIB (default: dis24).")
    ap.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output PNG path for the ensemble time-series plot.",
    )
    ap.add_argument(
        "--heatmap-dir",
        type=Path,
        default=None,
        help="If set, write one heatmap PNG per lead time into this directory.",
    )
    ap.add_argument(
        "--heatmap-stat",
        type=str,
        default="pf_median",
        choices=["pf_median", "pf_mean", "control"],
        help="Field to heatmap at each lead time.",
    )
    ap.add_argument(
        "--heatmap-log1p",
        action="store_true",
        help="Apply log1p scaling to heatmap values to improve contrast.",
    )
    ap.add_argument(
        "--heatmap-vmin",
        type=float,
        default=None,
        help="Fixed heatmap vmin (in plotted units; after optional log1p).",
    )
    ap.add_argument(
        "--heatmap-vmax",
        type=float,
        default=None,
        help="Fixed heatmap vmax (in plotted units; after optional log1p).",
    )
    ap.add_argument(
        "--heatmap-scale-file",
        type=Path,
        default=None,
        help=(
            "Optional JSON file storing {'vmin': ..., 'vmax': ...} to enforce a consistent scale "
            "across different issue_dates/runs. If missing, it will be created from this run."
        ),
    )
    ap.add_argument(
        "--heatmap-lon-180",
        action="store_true",
        help="Plot longitudes on [-180, 180] axis (recommended for Western Hemisphere).",
    )
    ap.add_argument(
        "--dpi",
        type=int,
        default=250,
        help="DPI for saved figures.",
    )
    args = ap.parse_args()

    ds_cf, ds_pf = open_cf_pf(args.grib)
    var = args.var
    if var not in ds_cf.data_vars:
        var = list(ds_cf.data_vars)[0]

    lat_i, lon_i, dist_km = pick_nearest_valid_cell(ds_cf, args.lat, args.lon, var)
    lat = float(ds_cf["latitude"].values[lat_i])
    lon = float(ds_cf["longitude"].values[lon_i])

    cf = ds_cf[var]
    if "number" in cf.dims:
        cf = cf.isel(number=0)
    cf_ts = cf.isel(latitude=lat_i, longitude=lon_i).values.astype("float64")  # step

    pf_ts = ds_pf[var].isel(latitude=lat_i, longitude=lon_i).values.astype("float64")  # number/step

    # Lead times in hours
    step_hours = (ds_cf["step"].values / np.timedelta64(1, "h")).astype(int)

    # Plot: readable but includes all members (thin) + envelope + median + control.
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#222222",
            "axes.labelcolor": "#222222",
            "xtick.color": "#222222",
            "ytick.color": "#222222",
            "axes.grid": True,
            "grid.color": "#e6e6e6",
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    fig = plt.figure(figsize=(11.5, 5.5))
    ax = fig.add_subplot(1, 1, 1)

    # Ensemble members
    for i in range(pf_ts.shape[0]):
        ax.plot(step_hours, pf_ts[i, :], color="#2a6fdb", alpha=0.12, lw=0.6, zorder=1)

    pf_q10 = np.nanquantile(pf_ts, 0.10, axis=0)
    pf_q90 = np.nanquantile(pf_ts, 0.90, axis=0)
    pf_med = np.nanmedian(pf_ts, axis=0)

    ax.fill_between(step_hours, pf_q10, pf_q90, color="#2a6fdb", alpha=0.18, label="pf 10-90%", zorder=2)
    ax.plot(step_hours, pf_med, color="#0b3d91", lw=2.0, label="pf median", zorder=3)
    ax.plot(step_hours, cf_ts, color="#111111", lw=2.2, label="control", zorder=4)

    ax.set_xlabel("Lead time (hours)")
    ax.set_ylabel(var)
    ax.set_title(
        f"Nearest non-NaN cell to ({args.lat:.5f}, {args.lon:.5f}) is ({lat:.5f}, {(_to_0_360(args.lon)):.5f} lon conv.)\n"
        f"Picked cell: ({lat:.5f}, {lon:.5f}) (dist ~{dist_km:.1f} km)"
    )
    ax.legend(loc="upper left", frameon=False, ncol=3, fontsize=9)
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=args.dpi)
    plt.close(fig)

    # Small stdout summary (safe; no secrets)
    print("picked_cell:", {"lat": lat, "lon_grib_0_360": lon, "dist_km": round(dist_km, 2)})
    print("finite_steps_control:", int(np.isfinite(cf_ts).sum()), "/", int(cf_ts.size))

    # Optional: heatmaps per lead time (one image per step).
    if args.heatmap_dir is not None:
        args.heatmap_dir.mkdir(parents=True, exist_ok=True)

        # Choose field to heatmap: control, pf median, or pf mean.
        if args.heatmap_stat == "control":
            field = cf.values.astype("float64")  # step/lat/lon
            field_label = "control"
        else:
            pf_cube = ds_pf[var].values.astype("float64")  # number/step/lat/lon
            if args.heatmap_stat == "pf_mean":
                field = np.nanmean(pf_cube, axis=0)
                field_label = "pf mean"
            else:
                # Many grid cells are masked (all-NaN across members). That's expected; suppress noise.
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message="All-NaN slice encountered")
                    field = np.nanmedian(pf_cube, axis=0)
                field_label = "pf median"

        # Apply optional log1p scaling for better contrast and to avoid domination by large rivers.
        plot_field = np.log1p(field) if args.heatmap_log1p else field

        # Color scale:
        # - If --heatmap-vmin/--heatmap-vmax are provided: use them (fixed across runs).
        # - Else if --heatmap-scale-file exists: load it (fixed across runs).
        # - Else: compute a robust scale from this run and (optionally) persist it.
        finite = np.isfinite(plot_field)
        if not finite.any():
            raise RuntimeError("Heatmap field has no finite values.")

        vmin = None
        vmax = None
        if (args.heatmap_vmin is not None) or (args.heatmap_vmax is not None):
            if args.heatmap_vmin is None or args.heatmap_vmax is None:
                raise ValueError("Provide both --heatmap-vmin and --heatmap-vmax, or neither.")
            vmin = float(args.heatmap_vmin)
            vmax = float(args.heatmap_vmax)
        elif args.heatmap_scale_file is not None and args.heatmap_scale_file.exists():
            with args.heatmap_scale_file.open("r") as f:
                scale = json.load(f)
            vmin = float(scale["vmin"])
            vmax = float(scale["vmax"])
        else:
            vmax = float(np.nanquantile(plot_field[finite], 0.99))
            vmin = float(np.nanquantile(plot_field[finite], 0.01))
            # Keep vmin at 0 if the distribution is non-negative-ish.
            if vmin > 0:
                vmin = 0.0
            if args.heatmap_scale_file is not None:
                args.heatmap_scale_file.parent.mkdir(parents=True, exist_ok=True)
                with args.heatmap_scale_file.open("w") as f:
                    json.dump({"vmin": vmin, "vmax": vmax}, f, indent=2, sort_keys=True)

        lats = ds_cf["latitude"].values
        lons_0_360 = ds_cf["longitude"].values
        tlat = float(args.lat)
        tlon = float(_to_0_360(args.lon))
        # Nearest non-NaN cell (the picked river pixel)
        picked_lat = float(lat)
        picked_lon_0_360 = float(lon)

        import matplotlib.pyplot as plt

        cmap = mpl.colormaps.get_cmap("viridis").copy()
        # NaNs fully transparent
        cmap.set_bad((1, 1, 1, 0))

        # Optional lon conversion for plotting only.
        if args.heatmap_lon_180:
            lons_plot = _to_m180_180(lons_0_360)
            # Ensure increasing for pcolormesh
            order = np.argsort(lons_plot)
            lons_plot = lons_plot[order]
        else:
            lons_plot = lons_0_360
            order = slice(None)

        tlon_plot = float(_to_m180_180(np.array([tlon]))[0]) if args.heatmap_lon_180 else float(tlon)
        picked_lon_plot = (
            float(_to_m180_180(np.array([picked_lon_0_360]))[0]) if args.heatmap_lon_180 else float(picked_lon_0_360)
        )

        for si, sh in enumerate(step_hours):
            fig = plt.figure(figsize=(8.2, 7.0))
            ax = fig.add_subplot(1, 1, 1)

            frame = np.ma.masked_invalid(plot_field[si, :, :])
            if not isinstance(order, slice):
                frame = frame[:, order]
            im = ax.pcolormesh(lons_plot, lats, frame, cmap=cmap, shading="auto", vmin=vmin, vmax=vmax)

            # Markers:
            # - red dot: requested target location
            # - green dot: nearest non-NaN (picked) grid cell to target (river pixel)
            ax.plot(
                [tlon_plot],
                [tlat],
                marker="o",
                markersize=6,
                color="red",
                markeredgecolor="white",
                markeredgewidth=0.8,
            )
            ax.plot(
                [picked_lon_plot],
                [picked_lat],
                marker="o",
                markersize=6,
                color="#1b9e77",
                markeredgecolor="white",
                markeredgewidth=0.8,
            )

            ax.set_xlabel("Longitude (deg)" + (" [-180, 180]" if args.heatmap_lon_180 else " [0, 360]"))
            ax.set_ylabel("Latitude (deg)")
            ax.set_title(f"{field_label} {var} | lead={int(sh)}h" + (" | log1p" if args.heatmap_log1p else ""))
            ax.set_aspect("equal", adjustable="box")

            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label(("log1p(" + var + ")" if args.heatmap_log1p else var))

            fig.tight_layout()
            out = args.heatmap_dir / f"heatmap_{field_label.replace(' ', '_')}_{var}_lead{int(sh):03d}h.png"
            fig.savefig(out, dpi=args.dpi)
            plt.close(fig)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
