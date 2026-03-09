#!/usr/bin/env python3
"""Run one-date GEFS + NWM point extraction smoke tests from dry-run manifests.

This helper intentionally stays small:
- It reuses existing repo location logic for NWM Lambert-grid cell selection.
- It reuses the existing GRIB nearest-valid-cell logic for GEFS.
- It downloads only a few representative files/messages needed for a one-date
  point extraction smoke test.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cfgrib
import numpy as np
import pandas as pd
import xarray as xr


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_nwm_retro_soil_point_series import _forward_lcc, choose_cell  # noqa: E402
from forecats_extract_glofas_batch import pick_cell  # noqa: E402


DEFAULT_SITE_CONFIG = "config/forecats_pipeline.template.yaml"
DEFAULT_GEFS_DATE = "2021-01-23"
DEFAULT_NWM_DATE = "2021-11-12"
GEFS_CF_VAR_MAP = {"APCP": "tp", "SOILW": "soilw"}


try:
    import yaml
except Exception as exc:  # pragma: no cover
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


@dataclass(frozen=True)
class GefsIndexEntry:
    record_number: int
    offset: int
    short_name: str
    level_descriptor: str
    raw_line: str


@dataclass(frozen=True)
class SiteInfo:
    usgs_site: str
    lat: float
    lon: float


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one-date GEFS + NWM point extraction smoke tests.")
    p.add_argument(
        "--manifest-run-dir",
        required=True,
        help="Run directory produced by build_gefs_nwm_forecast_manifest.py.",
    )
    p.add_argument("--site-config", default=DEFAULT_SITE_CONFIG)
    p.add_argument("--gefs-init-date", default=DEFAULT_GEFS_DATE)
    p.add_argument("--nwm-init-date", default=DEFAULT_NWM_DATE)
    p.add_argument("--gefs-cycle", type=int, default=0)
    p.add_argument("--nwm-cycle", type=int, default=0)
    p.add_argument("--max-search-radius-cells", type=int, default=20)
    return p.parse_args()


def load_site(path: Path) -> SiteInfo:
    if yaml is None:  # pragma: no cover
        raise RuntimeError(f"PyYAML import failed: {YAML_IMPORT_ERROR}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    site = cfg.get("site") or {}
    return SiteInfo(
        usgs_site=str(site.get("usgs_site", "11160500")),
        lat=float(site.get("lat", 37.0443931)),
        lon=float(site.get("lon", -122.072464)),
    )


def latest_manifest_csv(run_dir: Path, name: str) -> Path:
    path = run_dir / "manifests" / name
    if not path.exists():
        raise SystemExit(f"Required manifest missing: {path}")
    return path


def url_read_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode("utf-8")


def head_content_length(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as resp:
        value = resp.headers.get("Content-Length")
    if value is None:
        raise RuntimeError(f"Content-Length missing for {url}")
    return int(value)


def download_file(url: str, out_path: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as resp, out_path.open("wb") as fh:
        fh.write(resp.read())


def fetch_byte_range(url: str, start: int, end: int) -> bytes:
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def parse_gefs_idx(idx_text: str) -> List[GefsIndexEntry]:
    entries: List[GefsIndexEntry] = []
    for line in idx_text.splitlines():
        parts = line.split(":")
        if len(parts) < 5:
            continue
        entries.append(
            GefsIndexEntry(
                record_number=int(parts[0]),
                offset=int(parts[1]),
                short_name=parts[3],
                level_descriptor=parts[4],
                raw_line=line,
            )
        )
    return entries


def write_gefs_subset(file_url: str, idx_entries: List[GefsIndexEntry], wanted_rows: pd.DataFrame, out_path: Path) -> None:
    content_length = head_content_length(file_url)
    lookup: Dict[Tuple[str, str], GefsIndexEntry] = {
        (entry.short_name, entry.level_descriptor): entry for entry in idx_entries
    }
    offset_by_record = {entry.record_number: entry.offset for entry in idx_entries}
    matched_ranges: List[Tuple[int, int]] = []

    for row in wanted_rows.itertuples(index=False):
        key = (str(row.short_name), str(row.level_descriptor))
        entry = lookup.get(key)
        if entry is None:
            raise RuntimeError(f"Missing GEFS idx match for {key} in {file_url}.idx")
        next_offset = offset_by_record.get(entry.record_number + 1, content_length)
        matched_ranges.append((entry.offset, next_offset - 1))

    matched_ranges = sorted(set(matched_ranges))
    with out_path.open("wb") as fh:
        for start, end in matched_ranges:
            fh.write(fetch_byte_range(file_url, start, end))


def open_cfgrib_sets(path: Path) -> Dict[str, xr.Dataset]:
    out: Dict[str, xr.Dataset] = {}
    for ds in cfgrib.open_datasets(str(path), backend_kwargs={"indexpath": ""}):
        for var_name in ds.data_vars:
            out[var_name] = ds
    return out


def safe_scalar(value: Any) -> float:
    arr = np.asarray(value).reshape(-1)
    return float(arr[0])


def compute_distance_m(x0: float, y0: float, x1: float, y1: float) -> float:
    return float(math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2))


def nearest_xy_indices(ds: xr.Dataset, target_x: float, target_y: float) -> Tuple[int, int]:
    x_vals = np.asarray(ds["x"].values, dtype=float)
    y_vals = np.asarray(ds["y"].values, dtype=float)
    ix = int(np.argmin(np.abs(x_vals - target_x)))
    iy = int(np.argmin(np.abs(y_vals - target_y)))
    return ix, iy


def nwm_target_xy(ds: xr.Dataset, site: SiteInfo) -> Tuple[float, float]:
    crs = ds["crs"]
    return _forward_lcc(
        site.lat,
        site.lon,
        float(np.asarray(crs.attrs["standard_parallel"])[0]),
        float(np.asarray(crs.attrs["standard_parallel"])[1]),
        float(crs.attrs["latitude_of_projection_origin"]),
        float(crs.attrs["longitude_of_central_meridian"]),
        float(crs.attrs["earth_radius"]),
    )


def select_nwm_land_sample(df: pd.DataFrame, init_date: str, cycle_hour: int, product_family: str) -> pd.DataFrame:
    member_code = "det" if product_family == "short_range_land" else "mem1"
    lead_hour = 1 if product_family == "short_range_land" else 3 if product_family == "medium_range_land" else 24
    rows = df[
        (df["init_date"] == init_date)
        & (df["cycle_hour"] == cycle_hour)
        & (df["product_family"] == product_family)
        & (df["member_code"] == member_code)
        & (df["lead_hours"] == lead_hour)
    ].copy()
    if rows.empty:
        raise RuntimeError(f"No NWM sample rows found for {product_family} {init_date} cycle={cycle_hour}")
    return rows.sort_values(["short_name", "layer_index", "level_descriptor"], kind="mergesort")


def select_nwm_forcing_sample(df: pd.DataFrame, init_date: str, cycle_hour: int, product_family: str) -> pd.DataFrame:
    rows = df[
        (df["init_date"] == init_date)
        & (df["cycle_hour"] == cycle_hour)
        & (df["product_family"] == product_family)
        & (df["lead_hours"] == 1)
        & (df["short_name"] == "RAINRATE")
    ].copy()
    if rows.empty:
        raise RuntimeError(f"No NWM sample rows found for {product_family} {init_date} cycle={cycle_hour}")
    return rows


def select_gefs_sample(df: pd.DataFrame, init_date: str, cycle_hour: int, product_family: str) -> pd.DataFrame:
    rows = df[
        (df["init_date"] == init_date)
        & (df["cycle_hour"] == cycle_hour)
        & (df["member_code"] == "gec00")
        & (df["product_family"] == product_family)
        & (df["lead_hours"] == 3)
    ].copy()
    if rows.empty:
        raise RuntimeError(f"No GEFS sample rows found for {product_family} {init_date} cycle={cycle_hour:02d}")
    return rows.sort_values(["short_name", "depth_top_m", "level_descriptor"], kind="mergesort")


def run_gefs_smoke(
    df: pd.DataFrame,
    site: SiteInfo,
    out_dir: Path,
    init_date: str,
    cycle_hour: int,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    rows_a = select_gefs_sample(df, init_date=init_date, cycle_hour=cycle_hour, product_family="pgrb2ap5")
    rows_b = select_gefs_sample(df, init_date=init_date, cycle_hour=cycle_hour, product_family="pgrb2bp5")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_rows: List[Dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="gefs_point_smoke_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        subset_a = tmpdir_path / "gefs_pgrb2a_subset.grib2"
        subset_b = tmpdir_path / "gefs_pgrb2b_subset.grib2"

        idx_a = parse_gefs_idx(url_read_text(rows_a["object_url"].iloc[0] + ".idx"))
        idx_b = parse_gefs_idx(url_read_text(rows_b["object_url"].iloc[0] + ".idx"))
        write_gefs_subset(rows_a["object_url"].iloc[0], idx_a, rows_a, subset_a)
        write_gefs_subset(rows_b["object_url"].iloc[0], idx_b, rows_b, subset_b)

        ds_a = open_cfgrib_sets(subset_a)
        ds_b = open_cfgrib_sets(subset_b)
        soil_ds = ds_a["soilw"]
        lat_i, lon_i, dist_km = pick_cell(soil_ds, site.lat, site.lon, "soilw", cell_policy="nearest_valid")
        cell_lat = float(soil_ds["latitude"].values[lat_i])
        cell_lon = float(soil_ds["longitude"].values[lon_i])

        for row in rows_a.itertuples(index=False):
            cf_var = GEFS_CF_VAR_MAP[row.short_name]
            ds = ds_a[cf_var]
            da = ds[cf_var].isel(latitude=lat_i, longitude=lon_i)
            out_rows.append(
                {
                    "source": "GEFS",
                    "init_date": row.init_date,
                    "cycle_hour": int(row.cycle_hour),
                    "member_code": row.member_code,
                    "lead_hours": int(row.lead_hours),
                    "product_family": row.product_family,
                    "short_name": row.short_name,
                    "level_descriptor": row.level_descriptor,
                    "layer_index": None,
                    "value": safe_scalar(da.values),
                    "units": da.attrs.get("units", ""),
                    "cell_lat": cell_lat,
                    "cell_lon": cell_lon,
                    "dist_km": dist_km,
                    "file_url": row.object_url,
                }
            )

        deep_soil_ds = ds_b["soilw"]
        for row in rows_b.itertuples(index=False):
            da = deep_soil_ds["soilw"].sel(depthBelowLandLayer=float(row.depth_top_m)).isel(latitude=lat_i, longitude=lon_i)
            out_rows.append(
                {
                    "source": "GEFS",
                    "init_date": row.init_date,
                    "cycle_hour": int(row.cycle_hour),
                    "member_code": row.member_code,
                    "lead_hours": int(row.lead_hours),
                    "product_family": row.product_family,
                    "short_name": row.short_name,
                    "level_descriptor": row.level_descriptor,
                    "layer_index": None,
                    "value": safe_scalar(da.values),
                    "units": da.attrs.get("units", ""),
                    "cell_lat": cell_lat,
                    "cell_lon": cell_lon,
                    "dist_km": dist_km,
                    "file_url": row.object_url,
                }
            )

    out_df = pd.DataFrame(out_rows).sort_values(["product_family", "short_name", "level_descriptor"], kind="mergesort")
    out_path = out_dir / "gefs_point_smoke.csv"
    out_df.to_csv(out_path, index=False)
    meta = {
        "site_lat": site.lat,
        "site_lon": site.lon,
        "selected_lat_index": int(lat_i),
        "selected_lon_index": int(lon_i),
        "selected_cell_lat": cell_lat,
        "selected_cell_lon": cell_lon,
        "selected_cell_lon_m180_180": ((cell_lon + 180.0) % 360.0) - 180.0,
        "selected_cell_dist_km": dist_km,
        "rows_out": int(len(out_df)),
        "output_csv": str(out_path),
    }
    (out_dir / "gefs_point_smoke_meta.json").write_text(json.dumps(meta, indent=2))
    return out_df, meta


def run_nwm_smoke(
    df: pd.DataFrame,
    site: SiteInfo,
    out_dir: Path,
    init_date: str,
    cycle_hour: int,
    max_radius_cells: int,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    sample_frames = [
        select_nwm_land_sample(df, init_date=init_date, cycle_hour=cycle_hour, product_family="short_range_land"),
        select_nwm_land_sample(df, init_date=init_date, cycle_hour=cycle_hour, product_family="medium_range_land"),
        select_nwm_land_sample(df, init_date=init_date, cycle_hour=cycle_hour, product_family="long_range_land"),
        select_nwm_forcing_sample(df, init_date=init_date, cycle_hour=cycle_hour, product_family="short_range_forcing"),
        select_nwm_forcing_sample(df, init_date=init_date, cycle_hour=cycle_hour, product_family="medium_range_forcing"),
    ]
    sample_df = pd.concat(sample_frames, ignore_index=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_rows: List[Dict[str, Any]] = []
    grid_meta: Dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="nwm_point_smoke_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        files_by_url: Dict[str, Path] = {}
        for url, sub_df in sample_df.groupby("object_url", sort=False):
            key = sub_df["object_key"].iloc[0]
            local_path = tmpdir_path / Path(key).name
            download_file(url, local_path)
            files_by_url[url] = local_path

        medium_ref_rows = sample_df[
            (sample_df["product_family"] == "medium_range_land") & (sample_df["short_name"] == "SOILSAT_TOP")
        ].copy()
        if medium_ref_rows.empty:
            raise RuntimeError("Medium-range land SOILSAT_TOP sample missing.")

        with xr.open_dataset(files_by_url[medium_ref_rows["object_url"].iloc[0]]) as ds_ref:
            target_x, target_y = nwm_target_xy(ds_ref, site)
            sample_time = ds_ref["time"].values[0]
            ref_ix, ref_iy = choose_cell(
                ds_ref,
                "SOILSAT_TOP",
                target_x,
                target_y,
                soil_layer_index=0,
                max_radius_cells=max_radius_cells,
                sample_time=sample_time,
            )
            ref_x = float(np.asarray(ds_ref["x"].values)[ref_ix])
            ref_y = float(np.asarray(ds_ref["y"].values)[ref_iy])
            ref_dist_m = compute_distance_m(target_x, target_y, ref_x, ref_y)
            grid_meta = {
                "target_x": target_x,
                "target_y": target_y,
                "reference_ix": ref_ix,
                "reference_iy": ref_iy,
                "reference_x": ref_x,
                "reference_y": ref_y,
                "reference_distance_m": ref_dist_m,
            }

        for url, sub_df in sample_df.groupby("object_url", sort=False):
            local_path = files_by_url[url]
            with xr.open_dataset(local_path) as ds:
                for row in sub_df.itertuples(index=False):
                    if row.short_name in {"SOILSAT_TOP", "SOIL_M"}:
                        ix, iy = choose_cell(
                            ds,
                            row.short_name,
                            grid_meta["target_x"],
                            grid_meta["target_y"],
                            soil_layer_index=int(row.layer_index) if pd.notna(row.layer_index) else 0,
                            max_radius_cells=max_radius_cells,
                            sample_time=ds["time"].values[0],
                        )
                    else:
                        ix, iy = nearest_xy_indices(ds, grid_meta["reference_x"], grid_meta["reference_y"])

                    da = ds[row.short_name]
                    if "soil_layers_stag" in da.dims and pd.notna(row.layer_index):
                        da = da.isel(soil_layers_stag=int(row.layer_index))
                    if "time" in da.dims:
                        da = da.isel(time=0)
                    da = da.isel(x=ix, y=iy)
                    x_val = float(np.asarray(ds["x"].values)[ix])
                    y_val = float(np.asarray(ds["y"].values)[iy])
                    out_rows.append(
                        {
                            "source": "NWM",
                            "init_date": row.init_date,
                            "cycle_hour": int(row.cycle_hour),
                            "member_code": row.member_code,
                            "lead_hours": int(row.lead_hours),
                            "product_family": row.product_family,
                            "short_name": row.short_name,
                            "level_descriptor": row.level_descriptor,
                            "layer_index": int(row.layer_index) if pd.notna(row.layer_index) else None,
                            "value": safe_scalar(da.values),
                            "units": da.attrs.get("units", ""),
                            "selected_ix": int(ix),
                            "selected_iy": int(iy),
                            "selected_x": x_val,
                            "selected_y": y_val,
                            "distance_m": compute_distance_m(grid_meta["target_x"], grid_meta["target_y"], x_val, y_val),
                            "file_url": row.object_url,
                        }
                    )

    out_df = pd.DataFrame(out_rows).sort_values(
        ["product_family", "short_name", "layer_index", "lead_hours"], kind="mergesort"
    )
    out_path = out_dir / "nwm_point_smoke.csv"
    out_df.to_csv(out_path, index=False)
    meta = {
        "site_lat": site.lat,
        "site_lon": site.lon,
        "rows_out": int(len(out_df)),
        "output_csv": str(out_path),
        "grid_reference": grid_meta,
    }
    (out_dir / "nwm_point_smoke_meta.json").write_text(json.dumps(meta, indent=2))
    return out_df, meta


def main() -> int:
    args = parse_args()
    run_dir = Path(args.manifest_run_dir).resolve()
    site = load_site(Path(args.site_config))

    gefs_manifest_path = latest_manifest_csv(run_dir, "gefs_manifest.csv")
    nwm_manifest_path = latest_manifest_csv(run_dir, "nwm_manifest.csv")
    smoke_dir = run_dir / "smoke"
    gefs_out_dir = smoke_dir / "gefs"
    nwm_out_dir = smoke_dir / "nwm"

    gefs_df = pd.read_csv(gefs_manifest_path)
    nwm_df = pd.read_csv(nwm_manifest_path)

    gefs_point_df, gefs_meta = run_gefs_smoke(
        gefs_df,
        site=site,
        out_dir=gefs_out_dir,
        init_date=args.gefs_init_date,
        cycle_hour=int(args.gefs_cycle),
    )
    nwm_point_df, nwm_meta = run_nwm_smoke(
        nwm_df,
        site=site,
        out_dir=nwm_out_dir,
        init_date=args.nwm_init_date,
        cycle_hour=int(args.nwm_cycle),
        max_radius_cells=int(args.max_search_radius_cells),
    )

    summary = {
        "run_dir": str(run_dir),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "site": asdict(site),
        "gefs": gefs_meta,
        "nwm": nwm_meta,
    }
    summary_path = smoke_dir / "smoke_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    print(f"[OK] wrote {gefs_out_dir / 'gefs_point_smoke.csv'} rows={len(gefs_point_df)}")
    print(f"[OK] wrote {nwm_out_dir / 'nwm_point_smoke.csv'} rows={len(nwm_point_df)}")
    print(f"[OK] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
