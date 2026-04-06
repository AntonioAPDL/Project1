#!/usr/bin/env python3
"""Extract GEFS + NWM forecast point series from dry-run manifests.

This is the heavy-retrieval companion to the metadata-only manifest builder and
the one-date smoke extractor:
- GEFS reads only the needed GRIB message byte ranges for each manifest file.
- NWM reads remote NetCDF/HDF files via range-backed HTTP access and extracts
  only the needed point or small nearest-valid search window.

The script is resumable at the per-file level. It writes:
- point-series CSVs
- per-file status ledgers
- per-row failure ledgers
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import fsspec
import h5py
import numpy as np
import pandas as pd
import xarray as xr


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_nwm_retro_soil_point_series import choose_cell  # noqa: E402
from gefs_nwm_point_smoke_extract import (  # noqa: E402
    compute_distance_m,
    open_cfgrib_sets,
    parse_gefs_idx,
    safe_scalar,
    url_read_text,
    write_gefs_subset,
)


DEFAULT_RUN_DIR = "repro/gefs_nwm_forecast_runs/gefs_nwm_forecast_manifest_20260307T023425Z"
DEFAULT_OUT_SUBDIR = "extract"
GEFS_CF_VAR_MAP = {"APCP": "tp", "SOILW": "soilw"}
NWM_SOIL_VARS = {"SOILSAT_TOP", "SOIL_M"}

GEFS_OUTPUT_COLUMNS = [
    "source",
    "init_date",
    "cycle_hour",
    "member_code",
    "member_number",
    "member_kind",
    "product_family",
    "lead_hours",
    "lead_tag",
    "short_name",
    "level_descriptor",
    "depth_top_m",
    "depth_bottom_m",
    "layer_index",
    "selection_role",
    "value",
    "units",
    "selected_lat_index",
    "selected_lon_index",
    "selected_cell_lat",
    "selected_cell_lon_0_360",
    "selected_cell_lon_m180_180",
    "selected_cell_dist_km",
    "file_name",
    "object_key",
    "object_url",
    "storage_backend",
]

NWM_OUTPUT_COLUMNS = [
    "source",
    "init_date",
    "cycle_hour",
    "member_code",
    "member_number",
    "member_kind",
    "product_family",
    "lead_hours",
    "lead_tag",
    "short_name",
    "level_descriptor",
    "depth_top_m",
    "depth_bottom_m",
    "layer_index",
    "selection_role",
    "value",
    "units",
    "selected_ix",
    "selected_iy",
    "selected_x",
    "selected_y",
    "distance_m",
    "file_name",
    "object_key",
    "object_url",
    "storage_backend",
]

STATUS_COLUMNS = [
    "source",
    "object_url",
    "object_key",
    "init_date",
    "cycle_hour",
    "member_code",
    "product_family",
    "lead_hours_min",
    "lead_hours_max",
    "rows_requested",
    "rows_extracted",
    "rows_failed",
    "status",
    "error",
    "processed_utc",
]

FAILURE_COLUMNS = [
    "source",
    "object_url",
    "object_key",
    "init_date",
    "cycle_hour",
    "member_code",
    "product_family",
    "lead_hours",
    "short_name",
    "level_descriptor",
    "layer_index",
    "error",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract GEFS + NWM point series from manifests.")
    p.add_argument(
        "--manifest-run-dir",
        default=DEFAULT_RUN_DIR,
        help="Run directory produced by build_gefs_nwm_forecast_manifest.py.",
    )
    p.add_argument(
        "--out-subdir",
        default=DEFAULT_OUT_SUBDIR,
        help="Output subdirectory inside the manifest run dir.",
    )
    p.add_argument(
        "--sources",
        default="gefs,nwm",
        help="Comma-separated subset of sources to run: gefs,nwm.",
    )
    p.add_argument("--gefs-workers", type=int, default=16)
    p.add_argument("--nwm-workers", type=int, default=12)
    p.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Number of files to dispatch per batch.",
    )
    p.add_argument("--gefs-file-retries", type=int, default=3)
    p.add_argument("--nwm-file-retries", type=int, default=3)
    p.add_argument(
        "--max-search-radius-cells",
        type=int,
        default=20,
        help="Nearest-valid search radius for NWM soil variables.",
    )
    p.add_argument(
        "--nwm-block-size",
        type=int,
        default=4 * 1024 * 1024,
        help="HTTP read-ahead block size for remote NWM files.",
    )
    p.add_argument(
        "--max-gefs-files",
        type=int,
        default=0,
        help="Optional cap on GEFS files for a partial run.",
    )
    p.add_argument(
        "--max-nwm-files",
        type=int,
        default=0,
        help="Optional cap on NWM files for a partial run.",
    )
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_sources(text: str) -> List[str]:
    allowed = {"gefs", "nwm"}
    out = [item.strip().lower() for item in text.split(",") if item.strip()]
    if not out:
        raise SystemExit("No sources requested.")
    invalid = [item for item in out if item not in allowed]
    if invalid:
        raise SystemExit(f"Unsupported source(s): {invalid}")
    return out


def manifest_path(run_dir: Path, name: str) -> Path:
    path = run_dir / "manifests" / name
    if not path.exists():
        raise SystemExit(f"Required manifest missing: {path}")
    return path


def smoke_meta_path(run_dir: Path, rel: str) -> Path:
    path = run_dir / "smoke" / rel
    if not path.exists():
        raise SystemExit(f"Required smoke metadata missing: {path}")
    return path


def cleanup_outputs(paths: Sequence[Path]) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def append_rows(path: Path, rows: List[Dict[str, Any]], columns: Sequence[str]) -> None:
    if not rows:
        return
    df = pd.DataFrame(rows)
    df = df.reindex(columns=columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    df.to_csv(path, mode="a", header=write_header, index=False)


def load_processed_urls(status_path: Path) -> set[str]:
    if not status_path.exists():
        return set()
    df = pd.read_csv(status_path, usecols=["object_url"])
    return set(df["object_url"].astype(str))


def dataframe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return df.to_dict("records")


def batch_iter(items: Sequence[Dict[str, Any]], batch_size: int) -> Iterable[Sequence[Dict[str, Any]]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def group_manifest_object_urls(df: pd.DataFrame, max_files: int) -> List[str]:
    urls = df["object_url"].astype(str).drop_duplicates().tolist()
    if max_files > 0:
        return urls[:max_files]
    return urls


def task_from_group(grouped: Any, object_url: str) -> Dict[str, Any]:
    sub_df = grouped.get_group(object_url)
    rec0 = sub_df.iloc[0]
    return {
        "object_url": object_url,
        "object_key": str(rec0["object_key"]),
        "rows": dataframe_records(sub_df),
    }


def nwm_decode_attr(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return nwm_decode_attr(value.item())
        return ",".join(nwm_decode_attr(x) for x in value.tolist())
    return str(value)


def nwm_attr_scalar(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return None
        return nwm_attr_scalar(value.reshape(-1)[0])
    if isinstance(value, (bytes, str)):
        try:
            return float(value)
        except Exception:
            return None
    try:
        return float(value)
    except Exception:
        return None


def nwm_read_scaled(dataset: h5py.Dataset, indexer: Any) -> np.ndarray:
    raw = np.asarray(dataset[indexer])
    arr = raw.astype(float, copy=True)

    fill_candidates = [
        nwm_attr_scalar(dataset.attrs.get("_FillValue")),
        nwm_attr_scalar(dataset.attrs.get("missing_value")),
    ]
    for fill_value in fill_candidates:
        if fill_value is not None:
            arr[arr == fill_value] = np.nan

    scale_factor = nwm_attr_scalar(dataset.attrs.get("scale_factor"))
    add_offset = nwm_attr_scalar(dataset.attrs.get("add_offset"))
    if scale_factor is None:
        scale_factor = 1.0
    if add_offset is None:
        add_offset = 0.0
    if scale_factor != 1.0 or add_offset != 0.0:
        arr = arr * scale_factor + add_offset

    return arr


def nwm_window_dataset(
    h5: h5py.File,
    short_name: str,
    x_vals: np.ndarray,
    y_vals: np.ndarray,
    center_ix: int,
    center_iy: int,
    radius: int,
    layer_index: int | None,
) -> Tuple[xr.Dataset, int, int]:
    x_lo = max(0, center_ix - radius)
    x_hi = min(len(x_vals) - 1, center_ix + radius)
    y_lo = max(0, center_iy - radius)
    y_hi = min(len(y_vals) - 1, center_iy + radius)
    time_val = np.asarray(h5["time"][0]).reshape(1)

    if short_name == "SOIL_M":
        if layer_index is None:
            raise RuntimeError("SOIL_M row missing layer_index.")
        var = nwm_read_scaled(
            h5[short_name],
            (0, slice(y_lo, y_hi + 1), int(layer_index), slice(x_lo, x_hi + 1)),
        )
    else:
        var = nwm_read_scaled(
            h5[short_name],
            (0, slice(y_lo, y_hi + 1), slice(x_lo, x_hi + 1)),
        )

    ds = xr.Dataset(
        {
            short_name: (("time", "y", "x"), var[None, :, :]),
        },
        coords={
            "time": time_val,
            "y": np.asarray(y_vals[y_lo : y_hi + 1], dtype=float),
            "x": np.asarray(x_vals[x_lo : x_hi + 1], dtype=float),
        },
    )
    return ds, x_lo, y_lo


def worker_extract_gefs(task: Dict[str, Any], cell_meta: Dict[str, Any]) -> Dict[str, Any]:
    rows_df = pd.DataFrame(task["rows"])
    out_rows: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    error_text = ""
    max_attempts = max(1, int(cell_meta.get("_file_retries", 3)))
    for attempt in range(1, max_attempts + 1):
        try:
            idx_entries = parse_gefs_idx(url_read_text(task["object_url"] + ".idx"))
            with tempfile.TemporaryDirectory(prefix="gefs_point_extract_") as tmpdir:
                subset_path = Path(tmpdir) / "subset.grib2"
                write_gefs_subset(task["object_url"], idx_entries, rows_df, subset_path)
                ds_by_var = open_cfgrib_sets(subset_path)

                for row in rows_df.itertuples(index=False):
                    try:
                        cf_var = GEFS_CF_VAR_MAP[str(row.short_name)]
                        if cf_var not in ds_by_var:
                            raise RuntimeError(f"Missing cfgrib variable {cf_var!r} in subset.")
                        da = ds_by_var[cf_var][cf_var]
                        if str(row.short_name) == "SOILW" and "depthBelowLandLayer" in da.dims and pd.notna(row.depth_top_m):
                            depth_vals = np.asarray(da["depthBelowLandLayer"].values, dtype=float)
                            depth_index = int(np.argmin(np.abs(depth_vals - float(row.depth_top_m))))
                            da = da.isel(depthBelowLandLayer=depth_index)
                        da = da.isel(
                            latitude=int(cell_meta["selected_lat_index"]),
                            longitude=int(cell_meta["selected_lon_index"]),
                        )
                        out_rows.append(
                            {
                                **row._asdict(),
                                "value": safe_scalar(da.values),
                                "units": str(da.attrs.get("units", "")),
                                "selected_lat_index": int(cell_meta["selected_lat_index"]),
                                "selected_lon_index": int(cell_meta["selected_lon_index"]),
                                "selected_cell_lat": float(cell_meta["selected_cell_lat"]),
                                "selected_cell_lon_0_360": float(cell_meta["selected_cell_lon"]),
                                "selected_cell_lon_m180_180": float(cell_meta["selected_cell_lon_m180_180"]),
                                "selected_cell_dist_km": float(cell_meta["selected_cell_dist_km"]),
                            }
                        )
                    except Exception as exc:  # pragma: no cover - network/data dependent
                        failures.append(
                            {
                                "source": "GEFS",
                                "object_url": task["object_url"],
                                "object_key": task["object_key"],
                                "init_date": row.init_date,
                                "cycle_hour": row.cycle_hour,
                                "member_code": row.member_code,
                                "product_family": row.product_family,
                                "lead_hours": row.lead_hours,
                                "short_name": row.short_name,
                                "level_descriptor": row.level_descriptor,
                                "layer_index": row.layer_index,
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )
            break
        except Exception as exc:  # pragma: no cover - network/data dependent
            error_text = f"{type(exc).__name__}: {exc}"
            if attempt >= max_attempts:
                for row in rows_df.itertuples(index=False):
                    failures.append(
                        {
                            "source": "GEFS",
                            "object_url": task["object_url"],
                            "object_key": task["object_key"],
                            "init_date": row.init_date,
                            "cycle_hour": row.cycle_hour,
                            "member_code": row.member_code,
                            "product_family": row.product_family,
                            "lead_hours": row.lead_hours,
                            "short_name": row.short_name,
                            "level_descriptor": row.level_descriptor,
                            "layer_index": row.layer_index,
                            "error": f"{error_text} (attempts={attempt})",
                        }
                    )
            else:
                out_rows = []
                failures = []
                time.sleep(0.5 * attempt)

    rec0 = rows_df.iloc[0]
    status = "ok"
    if failures and out_rows:
        status = "partial"
    elif failures:
        status = "failed"
    return {
        "rows": out_rows,
        "failures": failures,
        "status": {
            "source": "GEFS",
            "object_url": task["object_url"],
            "object_key": task["object_key"],
            "init_date": rec0["init_date"],
            "cycle_hour": int(rec0["cycle_hour"]),
            "member_code": rec0["member_code"],
            "product_family": rec0["product_family"],
            "lead_hours_min": int(rows_df["lead_hours"].min()),
            "lead_hours_max": int(rows_df["lead_hours"].max()),
            "rows_requested": int(len(rows_df)),
            "rows_extracted": int(len(out_rows)),
            "rows_failed": int(len(failures)),
            "status": status,
            "error": error_text,
            "processed_utc": now_utc_iso(),
        },
    }


def worker_extract_nwm(
    task: Dict[str, Any],
    grid_meta: Dict[str, Any],
    max_radius_cells: int,
    block_size: int,
    file_retries: int,
) -> Dict[str, Any]:
    rows_df = pd.DataFrame(task["rows"])
    out_rows: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    error_text = ""

    max_attempts = max(1, int(file_retries))
    for attempt in range(1, max_attempts + 1):
        try:
            opener = fsspec.open(
                task["object_url"],
                mode="rb",
                block_size=block_size,
                cache_type="readahead",
            )
            with opener as fobj, h5py.File(fobj, "r") as h5:
                x_vals = np.asarray(h5["x"][:], dtype=float)
                y_vals = np.asarray(h5["y"][:], dtype=float)
                ref_ix = int(grid_meta["reference_ix"])
                ref_iy = int(grid_meta["reference_iy"])

                for row in rows_df.itertuples(index=False):
                    try:
                        if row.short_name not in h5:
                            raise RuntimeError(f"Variable {row.short_name!r} missing in file.")

                        units = nwm_decode_attr(h5[row.short_name].attrs.get("units"))
                        if row.short_name in NWM_SOIL_VARS:
                            layer_index = int(row.layer_index) if pd.notna(row.layer_index) else None
                            window_ds, x_offset, y_offset = nwm_window_dataset(
                                h5,
                                short_name=str(row.short_name),
                                x_vals=x_vals,
                                y_vals=y_vals,
                                center_ix=ref_ix,
                                center_iy=ref_iy,
                                radius=max_radius_cells,
                                layer_index=layer_index,
                            )
                            local_ix, local_iy = choose_cell(
                                window_ds,
                                str(row.short_name),
                                float(grid_meta["target_x"]),
                                float(grid_meta["target_y"]),
                                soil_layer_index=0,
                                max_radius_cells=max_radius_cells,
                                sample_time=window_ds["time"].values[0],
                            )
                            ix = int(x_offset + local_ix)
                            iy = int(y_offset + local_iy)
                            var_slice = np.asarray(window_ds[str(row.short_name)].isel(time=0).values, dtype=float)
                            value = float(var_slice[local_iy, local_ix])
                        else:
                            ix = ref_ix
                            iy = ref_iy
                            value = float(nwm_read_scaled(h5[str(row.short_name)], (0, iy, ix)).reshape(-1)[0])

                        x_val = float(x_vals[ix])
                        y_val = float(y_vals[iy])
                        out_rows.append(
                            {
                                **row._asdict(),
                                "value": value,
                                "units": units,
                                "selected_ix": ix,
                                "selected_iy": iy,
                                "selected_x": x_val,
                                "selected_y": y_val,
                                "distance_m": compute_distance_m(
                                    float(grid_meta["target_x"]),
                                    float(grid_meta["target_y"]),
                                    x_val,
                                    y_val,
                                ),
                            }
                        )
                    except Exception as exc:  # pragma: no cover - network/data dependent
                        failures.append(
                            {
                                "source": "NWM",
                                "object_url": task["object_url"],
                                "object_key": task["object_key"],
                                "init_date": row.init_date,
                                "cycle_hour": row.cycle_hour,
                                "member_code": row.member_code,
                                "product_family": row.product_family,
                                "lead_hours": row.lead_hours,
                                "short_name": row.short_name,
                                "level_descriptor": row.level_descriptor,
                                "layer_index": row.layer_index,
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )
            break
        except Exception as exc:  # pragma: no cover - network/data dependent
            error_text = f"{type(exc).__name__}: {exc}"
            if attempt >= max_attempts:
                for row in rows_df.itertuples(index=False):
                    failures.append(
                        {
                            "source": "NWM",
                            "object_url": task["object_url"],
                            "object_key": task["object_key"],
                            "init_date": row.init_date,
                            "cycle_hour": row.cycle_hour,
                            "member_code": row.member_code,
                            "product_family": row.product_family,
                            "lead_hours": row.lead_hours,
                            "short_name": row.short_name,
                            "level_descriptor": row.level_descriptor,
                            "layer_index": row.layer_index,
                            "error": f"{error_text} (attempts={attempt})",
                        }
                    )
            else:
                out_rows = []
                failures = []
                time.sleep(0.5 * attempt)

    rec0 = rows_df.iloc[0]
    status = "ok"
    if failures and out_rows:
        status = "partial"
    elif failures:
        status = "failed"
    return {
        "rows": out_rows,
        "failures": failures,
        "status": {
            "source": "NWM",
            "object_url": task["object_url"],
            "object_key": task["object_key"],
            "init_date": rec0["init_date"],
            "cycle_hour": int(rec0["cycle_hour"]),
            "member_code": rec0["member_code"],
            "product_family": rec0["product_family"],
            "lead_hours_min": int(rows_df["lead_hours"].min()),
            "lead_hours_max": int(rows_df["lead_hours"].max()),
            "rows_requested": int(len(rows_df)),
            "rows_extracted": int(len(out_rows)),
            "rows_failed": int(len(failures)),
            "status": status,
            "error": error_text,
            "processed_utc": now_utc_iso(),
        },
    }


def run_batches(
    source_name: str,
    grouped_manifest: Any,
    object_urls: List[str],
    total_rows_expected: int,
    workers: int,
    batch_size: int,
    worker_fn: Any,
    worker_args: Tuple[Any, ...],
    output_path: Path,
    status_path: Path,
    failure_path: Path,
    output_columns: Sequence[str],
) -> Dict[str, Any]:
    started = time.time()
    total_files = len(object_urls)
    written_rows = 0
    written_failures = 0
    written_status = 0

    with ProcessPoolExecutor(max_workers=workers) as pool:
        for batch_number, batch_urls in enumerate(batch_iter(object_urls, batch_size), start=1):
            batch_out_rows: List[Dict[str, Any]] = []
            batch_failures: List[Dict[str, Any]] = []
            batch_statuses: List[Dict[str, Any]] = []
            batch = [task_from_group(grouped_manifest, object_url) for object_url in batch_urls]
            futures = {pool.submit(worker_fn, task, *worker_args): task for task in batch}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - executor edge case
                    error_text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
                    for row in task["rows"]:
                        batch_failures.append(
                            {
                                "source": source_name.upper(),
                                "object_url": task["object_url"],
                                "object_key": task["object_key"],
                                "init_date": row["init_date"],
                                "cycle_hour": row["cycle_hour"],
                                "member_code": row["member_code"],
                                "product_family": row["product_family"],
                                "lead_hours": row["lead_hours"],
                                "short_name": row["short_name"],
                                "level_descriptor": row["level_descriptor"],
                                "layer_index": row["layer_index"],
                                "error": error_text,
                            }
                        )
                    row0 = task["rows"][0]
                    batch_statuses.append(
                        {
                            "source": source_name.upper(),
                            "object_url": task["object_url"],
                            "object_key": task["object_key"],
                            "init_date": row0["init_date"],
                            "cycle_hour": int(row0["cycle_hour"]),
                            "member_code": row0["member_code"],
                            "product_family": row0["product_family"],
                            "lead_hours_min": int(min(row["lead_hours"] for row in task["rows"])),
                            "lead_hours_max": int(max(row["lead_hours"] for row in task["rows"])),
                            "rows_requested": int(len(task["rows"])),
                            "rows_extracted": 0,
                            "rows_failed": int(len(task["rows"])),
                            "status": "failed",
                            "error": error_text,
                            "processed_utc": now_utc_iso(),
                        }
                    )
                    continue

                batch_out_rows.extend(result["rows"])
                batch_failures.extend(result["failures"])
                batch_statuses.append(result["status"])
            append_rows(output_path, batch_out_rows, output_columns)
            append_rows(failure_path, batch_failures, FAILURE_COLUMNS)
            append_rows(status_path, batch_statuses, STATUS_COLUMNS)

            written_rows += len(batch_out_rows)
            written_failures += len(batch_failures)
            written_status += len(batch_statuses)
            processed_files = min(batch_number * batch_size, total_files)
            elapsed = time.time() - started
            rate = processed_files / elapsed if elapsed > 0 else float("nan")
            print(
                f"[{source_name.upper()}] batch {batch_number} processed_files={processed_files}/{total_files} "
                f"rows_out={written_rows} failures={written_failures} rate_files_per_sec={rate:.3f}",
                flush=True,
            )

    elapsed = time.time() - started
    return {
        "source": source_name.upper(),
        "files_processed": total_files,
        "rows_expected": total_rows_expected,
        "rows_written": written_rows,
        "failure_rows_written": written_failures,
        "status_rows_written": written_status,
        "elapsed_seconds": elapsed,
    }


def prepare_tasks(
    manifest_df: pd.DataFrame,
    status_path: Path,
    max_files: int,
    overwrite: bool,
) -> Tuple[pd.DataFrame, List[str], int]:
    if overwrite:
        processed_urls: set[str] = set()
    else:
        processed_urls = load_processed_urls(status_path)

    if processed_urls:
        manifest_df = manifest_df[~manifest_df["object_url"].astype(str).isin(processed_urls)].copy()

    object_urls = group_manifest_object_urls(manifest_df, max_files=max_files)
    if max_files > 0 and len(object_urls) < manifest_df["object_url"].nunique():
        total_rows_expected = int(manifest_df[manifest_df["object_url"].astype(str).isin(set(object_urls))].shape[0])
    else:
        total_rows_expected = int(len(manifest_df))
    return manifest_df, object_urls, total_rows_expected


def source_output_paths(out_root: Path, source_name: str) -> Dict[str, Path]:
    source_dir = out_root / source_name
    return {
        "dir": source_dir,
        "output_csv": source_dir / f"{source_name}_point_series.csv",
        "status_csv": source_dir / f"{source_name}_file_status.csv",
        "failure_csv": source_dir / f"{source_name}_row_failures.csv",
        "summary_json": source_dir / f"{source_name}_summary.json",
    }


def write_summary(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_dir = Path(args.manifest_run_dir).resolve()
    out_root = (run_dir / args.out_subdir).resolve()
    sources = normalize_sources(args.sources)

    gefs_meta: Optional[Dict[str, Any]] = None
    nwm_meta: Optional[Dict[str, Any]] = None
    nwm_grid_meta: Optional[Dict[str, Any]] = None

    if "gefs" in sources:
        gefs_meta = read_json(smoke_meta_path(run_dir, "gefs/gefs_point_smoke_meta.json"))
    if "nwm" in sources:
        nwm_meta = read_json(smoke_meta_path(run_dir, "nwm/nwm_point_smoke_meta.json"))
        nwm_grid_meta = dict(nwm_meta["grid_reference"])

    top_summary_path = out_root / "extract_summary.json"
    if top_summary_path.exists() and not args.overwrite:
        summaries = read_json(top_summary_path)
    else:
        summaries = {}
    summaries.update(
        {
            "run_dir": str(run_dir),
            "out_root": str(out_root),
            "requested_sources": sorted(set((summaries.get("requested_sources") or []) + sources)),
        }
    )
    if "created_utc" not in summaries:
        summaries["created_utc"] = now_utc_iso()
    summaries["last_updated_utc"] = now_utc_iso()

    if "gefs" in sources:
        paths = source_output_paths(out_root, "gefs")
        if args.overwrite:
            cleanup_outputs([paths["output_csv"], paths["status_csv"], paths["failure_csv"], paths["summary_json"]])
        gefs_df = pd.read_csv(manifest_path(run_dir, "gefs_manifest.csv"))
        gefs_df = gefs_df.sort_values(
            ["init_date", "cycle_hour", "member_number", "lead_hours", "product_family", "short_name"],
            kind="mergesort",
        )
        gefs_df, gefs_object_urls, gefs_rows_expected = prepare_tasks(
            gefs_df,
            status_path=paths["status_csv"],
            max_files=int(args.max_gefs_files),
            overwrite=bool(args.overwrite),
        )
        gefs_summary = run_batches(
            source_name="gefs",
            grouped_manifest=gefs_df.groupby("object_url", sort=False),
            object_urls=gefs_object_urls,
            total_rows_expected=gefs_rows_expected,
            workers=max(1, int(args.gefs_workers)),
            batch_size=max(1, int(args.batch_size)),
            worker_fn=worker_extract_gefs,
            worker_args=({**gefs_meta, "_file_retries": int(args.gefs_file_retries)},),
            output_path=paths["output_csv"],
            status_path=paths["status_csv"],
            failure_path=paths["failure_csv"],
            output_columns=GEFS_OUTPUT_COLUMNS,
        )
        gefs_summary["output_csv"] = str(paths["output_csv"])
        gefs_summary["status_csv"] = str(paths["status_csv"])
        gefs_summary["failure_csv"] = str(paths["failure_csv"])
        gefs_summary["selection_meta"] = gefs_meta
        write_summary(paths["summary_json"], gefs_summary)
        summaries["gefs"] = gefs_summary

    if "nwm" in sources:
        paths = source_output_paths(out_root, "nwm")
        if args.overwrite:
            cleanup_outputs([paths["output_csv"], paths["status_csv"], paths["failure_csv"], paths["summary_json"]])
        nwm_df = pd.read_csv(manifest_path(run_dir, "nwm_manifest.csv"))
        nwm_df = nwm_df.sort_values(
            ["init_date", "cycle_hour", "member_number", "lead_hours", "product_family", "short_name", "layer_index"],
            kind="mergesort",
        )
        nwm_df, nwm_object_urls, nwm_rows_expected = prepare_tasks(
            nwm_df,
            status_path=paths["status_csv"],
            max_files=int(args.max_nwm_files),
            overwrite=bool(args.overwrite),
        )
        nwm_summary = run_batches(
            source_name="nwm",
            grouped_manifest=nwm_df.groupby("object_url", sort=False),
            object_urls=nwm_object_urls,
            total_rows_expected=nwm_rows_expected,
            workers=max(1, int(args.nwm_workers)),
            batch_size=max(1, int(args.batch_size)),
            worker_fn=worker_extract_nwm,
            worker_args=(
                nwm_grid_meta,
                int(args.max_search_radius_cells),
                int(args.nwm_block_size),
                int(args.nwm_file_retries),
            ),
            output_path=paths["output_csv"],
            status_path=paths["status_csv"],
            failure_path=paths["failure_csv"],
            output_columns=NWM_OUTPUT_COLUMNS,
        )
        nwm_summary["output_csv"] = str(paths["output_csv"])
        nwm_summary["status_csv"] = str(paths["status_csv"])
        nwm_summary["failure_csv"] = str(paths["failure_csv"])
        nwm_summary["selection_meta"] = nwm_meta
        write_summary(paths["summary_json"], nwm_summary)
        summaries["nwm"] = nwm_summary

    write_summary(top_summary_path, summaries)
    print(f"[OK] wrote {top_summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
