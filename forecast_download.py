#!/usr/bin/env python3
"""Recover or rebuild the historical NWS/NWM point-forecast archive (`results.pkl`).

This script is the modernized, recovery-safe successor to the original ad hoc
`forecast_download.py`. It keeps the historical `results.pkl` key/value layout
used elsewhere in the repository while adding:

- explicit CLI configuration
- reproducible planning / dry-run mode
- resumable atomic pickle writes with backup files
- progress JSON + failed-blob ledger
- bootstrap feature resolution from either `saved_data.pkl`, a hydrofabric GDB,
  or an explicit `--feature-id`
- external run directories for logs/manifests/status

The stored pickle format remains:
  {"nwm.YYYYMMDD/.../file.nc": <streamflow_cms_float>, ...}
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import pickle
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import xarray as xr
from google.cloud import storage

try:
    import geopandas as gpd
    from pyproj import Transformer
    from shapely.geometry import Point
except Exception:
    gpd = None
    Transformer = None
    Point = None

try:
    import yaml
except Exception:
    yaml = None


DEFAULT_CONFIG_PATH = Path("config/recovery_site11160500.yaml")
DEFAULT_SAVED_DATA_PKL = Path(
    "data/recovery_bootstrap/muscat_backup_20260406/Project/Input/NWS-Coordinates/saved_data.pkl"
)
DEFAULT_HYDROFABRIC_GDB = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/bootstrap_recovered/"
    "muscat_backup_20260406/Project/Input/NWS-Coordinates/NWM_v3_hydrofabric.gdb"
)
DEFAULT_START_DATE = "2018-09-17"
DEFAULT_END_DATE = "2024-02-20"
DEFAULT_SITE_CODE = "11160500"
DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464
DEFAULT_PROGRESS_EVERY = 100
DEFAULT_MAX_WORKERS = 5
DEFAULT_BLOB_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SEC = 1.0
NWM_BUCKET = "national-water-model"
EXCLUDE_DATE = date(2019, 3, 10)
THREAD_LOCAL = threading.local()
NETCDF_LOCK = threading.Lock()


@dataclass(frozen=True)
class SiteSpec:
    site_code: str
    lat: float
    lon: float
    name: str = "San Lorenzo / Big Trees"


@dataclass(frozen=True)
class BootstrapResolution:
    feature_id: int
    feature_source: str
    saved_data_pkl: str = ""
    hydrofabric_gdb: str = ""
    saved_data_closest_lon: Optional[float] = None
    saved_data_closest_lat: Optional[float] = None
    saved_data_closest_x: Optional[float] = None
    saved_data_closest_y: Optional[float] = None


@dataclass(frozen=True)
class BlobPlanRow:
    blob_name: str
    issue_date: str
    issue_hour: int
    ensemble_member: int
    lead_time_h: int
    already_in_results: bool


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or extend the historical NWS/NWM point archive results.pkl")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--site-code", default="")
    parser.add_argument("--lat", type=float, default=float("nan"))
    parser.add_argument("--lon", type=float, default=float("nan"))
    parser.add_argument("--feature-id", type=int, default=None)
    parser.add_argument("--saved-data-pkl", type=Path, default=DEFAULT_SAVED_DATA_PKL)
    parser.add_argument("--hydrofabric-gdb", type=Path, default=DEFAULT_HYDROFABRIC_GDB)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--results-out", type=Path, default=None)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument("--progress-every", type=int, default=DEFAULT_PROGRESS_EVERY)
    parser.add_argument("--blob-retries", type=int, default=DEFAULT_BLOB_RETRIES)
    parser.add_argument("--retry-backoff-sec", type=float, default=DEFAULT_RETRY_BACKOFF_SEC)
    parser.add_argument("--max-blobs", type=int, default=None)
    parser.add_argument("--overwrite-results", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true", help="Download missing blobs and write a pickle archive.")
    mode.add_argument("--dry-run", action="store_true", help="Write planning artifacts only; no downloads.")
    return parser.parse_args()


def load_site_defaults(config_path: Path) -> SiteSpec:
    if yaml is not None and config_path.exists():
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        site = payload.get("site") or {}
        return SiteSpec(
            site_code=str(site.get("usgs_site") or DEFAULT_SITE_CODE),
            lat=float(site.get("lat") or DEFAULT_LAT),
            lon=float(site.get("lon") or DEFAULT_LON),
            name=str(site.get("name") or "San Lorenzo / Big Trees"),
        )
    return SiteSpec(site_code=DEFAULT_SITE_CODE, lat=DEFAULT_LAT, lon=DEFAULT_LON)


def resolve_site_spec(args: argparse.Namespace) -> SiteSpec:
    cfg_site = load_site_defaults(args.config)
    site_code = args.site_code or cfg_site.site_code
    lat = cfg_site.lat if args.lat != args.lat else float(args.lat)
    lon = cfg_site.lon if args.lon != args.lon else float(args.lon)
    return SiteSpec(site_code=site_code, lat=lat, lon=lon, name=cfg_site.name)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def setup_logger(log_path: Path, verbose: bool) -> logging.Logger:
    ensure_dir(log_path.parent)
    logger = logging.getLogger("forecast_download")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO if verbose else logging.WARNING)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def parse_ymd(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def construct_blob_names(start_date: date, end_date: date) -> List[str]:
    blob_names: List[str] = []
    current = start_date
    while current <= end_date:
        if current == EXCLUDE_DATE:
            current += timedelta(days=1)
            continue

        date_str = current.strftime("%Y%m%d")
        if current >= date(2021, 4, 21):
            lead_times: Iterable[int] = range(1, 241)
        else:
            lead_times = range(3, 241, 3)

        if current < date(2019, 6, 19):
            for lead_time in lead_times:
                blob_names.append(f"nwm.{date_str}/medium_range/nwm.t00z.medium_range.channel_rt.f{lead_time:03}.conus.nc")
        else:
            for ensemble_num in range(1, 8):
                ensemble_dir = f"medium_range_mem{ensemble_num}"
                max_lead_time = 240 if ensemble_num == 1 else 204
                for lead_time in lead_times:
                    if lead_time <= max_lead_time:
                        blob_names.append(
                            f"nwm.{date_str}/{ensemble_dir}/"
                            f"nwm.t12z.medium_range.channel_rt_{ensemble_num}.f{lead_time:03}.conus.nc"
                        )
        current += timedelta(days=1)
    return blob_names


def parse_blob_name(blob_name: str) -> Tuple[str, int, int, int]:
    parts = blob_name.split("/")
    issue_date = datetime.strptime(parts[0].split(".", 1)[1], "%Y%m%d").date().isoformat()
    ensemble_member = 1
    if len(parts) > 1 and "mem" in parts[1]:
        ensemble_member = int(parts[1].split("mem", 1)[1])
    filename = parts[-1]
    issue_hour = 12 if ".t12z." in filename else 0
    lead_time_h = int(filename.split(".f", 1)[1].split(".", 1)[0])
    return issue_date, issue_hour, ensemble_member, lead_time_h


def write_plan_manifest(path: Path, blob_names: Sequence[str], existing_keys: Sequence[str]) -> None:
    ensure_dir(path.parent)
    existing = set(existing_keys)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["blob_name", "issue_date", "issue_hour", "ensemble_member", "lead_time_h", "already_in_results"],
        )
        writer.writeheader()
        for blob_name in blob_names:
            issue_date, issue_hour, ensemble_member, lead_time_h = parse_blob_name(blob_name)
            row = BlobPlanRow(
                blob_name=blob_name,
                issue_date=issue_date,
                issue_hour=issue_hour,
                ensemble_member=ensemble_member,
                lead_time_h=lead_time_h,
                already_in_results=blob_name in existing,
            )
            writer.writerow(asdict(row))


def atomic_write_json(path: Path, payload: Dict[str, object]) -> None:
    ensure_dir(path.parent)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def load_existing_results(path: Path, overwrite_results: bool, logger: logging.Logger) -> Dict[str, float]:
    if overwrite_results:
        logger.info("Starting fresh results set because --overwrite-results was requested.")
        return {}

    backup_path = path.with_suffix(path.suffix + ".bak")
    for candidate in (path, backup_path):
        if not candidate.exists():
            continue
        try:
            with candidate.open("rb") as handle:
                payload = pickle.load(handle)
            if isinstance(payload, dict):
                logger.info("Loaded %d existing keys from %s", len(payload), candidate)
                return payload
        except Exception as exc:
            logger.warning("Failed to load %s: %s", candidate, exc)
    logger.info("No existing results archive found at %s; starting empty.", path)
    return {}


def save_results(data: Dict[str, float], path: Path) -> None:
    ensure_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    backup_path = path.with_suffix(path.suffix + ".bak")
    try:
        with os.fdopen(fd, "wb") as handle:
            pickle.dump(data, handle)
        os.replace(tmp_name, path)
        shutil.copyfile(path, backup_path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def load_saved_data_resolution(saved_data_path: Path) -> BootstrapResolution:
    with saved_data_path.open("rb") as handle:
        payload = pickle.load(handle)
    return BootstrapResolution(
        feature_id=int(payload["closest_feature"]),
        feature_source="saved_data_pkl",
        saved_data_pkl=str(saved_data_path),
        saved_data_closest_lon=float(payload.get("closest_lon")) if payload.get("closest_lon") is not None else None,
        saved_data_closest_lat=float(payload.get("closest_lat")) if payload.get("closest_lat") is not None else None,
        saved_data_closest_x=float(payload.get("closest_x")) if payload.get("closest_x") is not None else None,
        saved_data_closest_y=float(payload.get("closest_y")) if payload.get("closest_y") is not None else None,
    )


def compute_feature_from_hydrofabric(hydrofabric_gdb: Path, site: SiteSpec) -> BootstrapResolution:
    if gpd is None or Transformer is None or Point is None:
        raise RuntimeError("geopandas/pyproj/shapely are required to resolve feature_id from hydrofabric_gdb")
    gdf = gpd.read_file(hydrofabric_gdb, driver="FileGDB", layer="nwm_reaches_conus")
    gdf_projected = gdf.to_crs(epsg=5070)
    gdf_projected = gdf_projected.rename(columns={"ID": "feature_id"})
    gdf_projected["centroid"] = gdf_projected.geometry.centroid
    transformer = Transformer.from_crs(4326, 5070, always_xy=True)
    target_x, target_y = transformer.transform(site.lon, site.lat)
    target_point = Point(target_x, target_y)
    gdf_projected["distance_to_target"] = gdf_projected["centroid"].apply(lambda point: point.distance(target_point))
    row = gdf_projected.loc[gdf_projected["distance_to_target"].idxmin()]
    centroid = row["centroid"]
    reverse_transformer = Transformer.from_crs(5070, 4326, always_xy=True)
    closest_lon, closest_lat = reverse_transformer.transform(centroid.x, centroid.y)
    return BootstrapResolution(
        feature_id=int(row["feature_id"]),
        feature_source="hydrofabric_gdb",
        hydrofabric_gdb=str(hydrofabric_gdb),
        saved_data_closest_lon=float(closest_lon),
        saved_data_closest_lat=float(closest_lat),
        saved_data_closest_x=float(centroid.x),
        saved_data_closest_y=float(centroid.y),
    )


def resolve_feature(site: SiteSpec, feature_id: Optional[int], saved_data_pkl: Path, hydrofabric_gdb: Path) -> BootstrapResolution:
    if feature_id is not None:
        return BootstrapResolution(feature_id=int(feature_id), feature_source="explicit_feature_id")
    if saved_data_pkl.exists():
        return load_saved_data_resolution(saved_data_pkl)
    if hydrofabric_gdb.exists():
        return compute_feature_from_hydrofabric(hydrofabric_gdb, site)
    raise RuntimeError(
        "Unable to resolve feature_id. Provide --feature-id explicitly or ensure --saved-data-pkl or --hydrofabric-gdb exists."
    )


def get_nwm_bucket():
    bucket = getattr(THREAD_LOCAL, "nwm_bucket", None)
    if bucket is None:
        client = storage.Client.create_anonymous_client()
        bucket = client.bucket(NWM_BUCKET)
        THREAD_LOCAL.nwm_bucket = bucket
    return bucket


def extract_value_from_blob(blob_name: str, feature_id: int, blob_retries: int, retry_backoff_sec: float) -> float:
    last_exc: Optional[Exception] = None
    for attempt_idx in range(1, int(blob_retries) + 1):
        try:
            bucket = get_nwm_bucket()
            blob = bucket.blob(blob_name)
            with tempfile.NamedTemporaryFile(suffix=".nc") as temp_file:
                blob.download_to_filename(temp_file.name)
                # netCDF readers can segfault under concurrent threaded access; keep downloads
                # concurrent but serialize the short local open/select/close section.
                with NETCDF_LOCK:
                    with xr.open_dataset(temp_file.name) as dataset:
                        value = dataset.sel(feature_id=int(feature_id))["streamflow"].values.item()
            return float(value)
        except Exception as exc:  # pragma: no cover - exercised via higher-level smoke, not unit tests
            last_exc = exc
            if attempt_idx >= int(blob_retries):
                break
            time.sleep(float(retry_backoff_sec) * attempt_idx)
    assert last_exc is not None
    raise last_exc


def append_failed_row(path: Path, blob_name: str, error: str) -> None:
    ensure_dir(path.parent)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp_utc", "blob_name", "error"])
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "blob_name": blob_name,
                "error": error[:5000],
            }
        )


def build_run_paths(run_dir: Path) -> Dict[str, Path]:
    paths = {
        "run_dir": run_dir,
        "log_path": run_dir / "logs" / "forecast_download.log",
        "plan_manifest": run_dir / "manifests" / "blob_plan.csv",
        "bootstrap_json": run_dir / "provenance" / "bootstrap_resolution.json",
        "status_json": run_dir / "status" / "progress.json",
        "summary_json": run_dir / "status" / "run_summary.json",
        "failed_csv": run_dir / "status" / "failed_blobs.csv",
        "commands_txt": run_dir / "commands" / "invocation.txt",
    }
    for path in paths.values():
        if path.suffix:
            ensure_dir(path.parent)
        else:
            ensure_dir(path)
    return paths


def write_invocation(path: Path) -> None:
    ensure_dir(path.parent)
    path.write_text(" ".join(shlex_quote(arg) for arg in os.sys.argv) + "\n", encoding="utf-8")


def shlex_quote(raw: str) -> str:
    if not raw:
        return "''"
    if all(ch.isalnum() or ch in "._/-=:" for ch in raw):
        return raw
    return "'" + raw.replace("'", "'\"'\"'") + "'"


def progress_payload(
    *,
    site: SiteSpec,
    results_out: Path,
    bootstrap: BootstrapResolution,
    start_date: str,
    end_date: str,
    total_planned: int,
    existing_before_run: int,
    pending_this_run: int,
    completed_this_run: int,
    error_count: int,
    dry_run: bool,
    max_blobs: Optional[int],
) -> Dict[str, object]:
    return {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "site": asdict(site),
        "results_out": str(results_out),
        "bootstrap": asdict(bootstrap),
        "start_date": start_date,
        "end_date": end_date,
        "total_planned": total_planned,
        "existing_before_run": existing_before_run,
        "pending_this_run": pending_this_run,
        "completed_this_run": completed_this_run,
        "error_count": error_count,
        "dry_run": dry_run,
        "max_blobs": max_blobs,
    }


def run_download(
    *,
    site: SiteSpec,
    blob_names: Sequence[str],
    results_out: Path,
    bootstrap: BootstrapResolution,
    run_paths: Dict[str, Path],
    dry_run: bool,
    overwrite_results: bool,
    max_workers: int,
    progress_every: int,
    blob_retries: int,
    retry_backoff_sec: float,
    max_blobs: Optional[int],
    logger: logging.Logger,
) -> int:
    existing_results = load_existing_results(results_out, overwrite_results=overwrite_results, logger=logger)
    pending = [blob_name for blob_name in blob_names if blob_name not in existing_results]
    if max_blobs is not None:
        pending = pending[: int(max_blobs)]

    write_plan_manifest(run_paths["plan_manifest"], blob_names, existing_results.keys())
    atomic_write_json(run_paths["bootstrap_json"], asdict(bootstrap))

    total_planned = len(blob_names)
    existing_before_run = len(existing_results)
    pending_this_run = len(pending)

    initial_progress = progress_payload(
        site=site,
        results_out=results_out,
        bootstrap=bootstrap,
        start_date=parse_blob_name(blob_names[0])[0] if blob_names else "",
        end_date=parse_blob_name(blob_names[-1])[0] if blob_names else "",
        total_planned=total_planned,
        existing_before_run=existing_before_run,
        pending_this_run=pending_this_run,
        completed_this_run=0,
        error_count=0,
        dry_run=dry_run,
        max_blobs=max_blobs,
    )
    atomic_write_json(run_paths["status_json"], initial_progress)

    if dry_run:
        summary = dict(initial_progress)
        summary["status"] = "dry_run_complete"
        atomic_write_json(run_paths["summary_json"], summary)
        logger.info("Dry-run planned %d blobs (%d already present, %d pending).", total_planned, existing_before_run, pending_this_run)
        return 0

    completed_this_run = 0
    error_count = 0
    if not pending:
        summary = dict(initial_progress)
        summary["status"] = "already_complete"
        atomic_write_json(run_paths["summary_json"], summary)
        logger.info("No pending blobs remain for %s", results_out)
        return 0

    logger.info(
        "Starting download: total_planned=%d existing_before_run=%d pending_this_run=%d feature_id=%d workers=%d blob_retries=%d",
        total_planned,
        existing_before_run,
        pending_this_run,
        bootstrap.feature_id,
        max_workers,
        blob_retries,
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_blob = {
            executor.submit(
                extract_value_from_blob,
                blob_name,
                bootstrap.feature_id,
                blob_retries,
                retry_backoff_sec,
            ): blob_name
            for blob_name in pending
        }
        for future in as_completed(future_to_blob):
            blob_name = future_to_blob[future]
            try:
                value = future.result()
                existing_results[blob_name] = value
                completed_this_run += 1
            except Exception as exc:
                error_count += 1
                append_failed_row(run_paths["failed_csv"], blob_name, repr(exc))
                logger.error("Failed %s: %s", blob_name, exc)

            checkpoint = completed_this_run + error_count
            if checkpoint % progress_every == 0 or checkpoint == pending_this_run:
                save_results(existing_results, results_out)
                status = progress_payload(
                    site=site,
                    results_out=results_out,
                    bootstrap=bootstrap,
                    start_date=parse_blob_name(blob_names[0])[0] if blob_names else "",
                    end_date=parse_blob_name(blob_names[-1])[0] if blob_names else "",
                    total_planned=total_planned,
                    existing_before_run=existing_before_run,
                    pending_this_run=pending_this_run,
                    completed_this_run=completed_this_run,
                    error_count=error_count,
                    dry_run=False,
                    max_blobs=max_blobs,
                )
                atomic_write_json(run_paths["status_json"], status)
                logger.info(
                    "Progress: processed=%d/%d ok=%d errors=%d total_results=%d",
                    checkpoint,
                    pending_this_run,
                    completed_this_run,
                    error_count,
                    len(existing_results),
                )

    save_results(existing_results, results_out)
    summary = progress_payload(
        site=site,
        results_out=results_out,
        bootstrap=bootstrap,
        start_date=parse_blob_name(blob_names[0])[0] if blob_names else "",
        end_date=parse_blob_name(blob_names[-1])[0] if blob_names else "",
        total_planned=total_planned,
        existing_before_run=existing_before_run,
        pending_this_run=pending_this_run,
        completed_this_run=completed_this_run,
        error_count=error_count,
        dry_run=False,
        max_blobs=max_blobs,
    )
    summary["status"] = "run_complete" if error_count == 0 else "run_complete_with_errors"
    summary["results_count_after_run"] = len(existing_results)
    atomic_write_json(run_paths["summary_json"], summary)
    logger.info("Run complete: ok=%d errors=%d results_count=%d", completed_this_run, error_count, len(existing_results))
    return 0 if error_count == 0 else 1


def derive_run_dir(args: argparse.Namespace, results_out: Optional[Path]) -> Path:
    if args.run_dir is not None:
        return args.run_dir.resolve()
    if results_out is not None:
        return results_out.resolve().parent / f"forecast_download_run_{now_utc()}"
    return Path("/tmp") / f"forecast_download_run_{now_utc()}"


def main() -> int:
    args = parse_args()
    dry_run = bool(args.dry_run or (not args.run))
    site = resolve_site_spec(args)

    start_date = parse_ymd(args.start_date)
    end_date = parse_ymd(args.end_date)
    if end_date < start_date:
        raise SystemExit("end-date must be on or after start-date")

    results_out = args.results_out.resolve() if args.results_out is not None else None
    if not dry_run and results_out is None:
        raise SystemExit("--results-out is required when --run is used")
    if results_out is None:
        results_out = Path("results.pkl").resolve()

    run_dir = derive_run_dir(args, results_out)
    run_paths = build_run_paths(run_dir)
    write_invocation(run_paths["commands_txt"])
    logger = setup_logger(run_paths["log_path"], verbose=args.verbose)

    logger.info("Site: %s lat=%.7f lon=%.7f", site.site_code, site.lat, site.lon)
    logger.info("Dates: %s -> %s", start_date.isoformat(), end_date.isoformat())
    logger.info("results_out=%s run_dir=%s dry_run=%s", results_out, run_dir, dry_run)

    bootstrap = resolve_feature(
        site=site,
        feature_id=args.feature_id,
        saved_data_pkl=args.saved_data_pkl.resolve(),
        hydrofabric_gdb=args.hydrofabric_gdb.resolve(),
    )
    logger.info("Resolved feature_id=%d via %s", bootstrap.feature_id, bootstrap.feature_source)

    blob_names = construct_blob_names(start_date, end_date)
    logger.info("Planned blob count: %d", len(blob_names))

    return run_download(
        site=site,
        blob_names=blob_names,
        results_out=results_out,
        bootstrap=bootstrap,
        run_paths=run_paths,
        dry_run=dry_run,
        overwrite_results=args.overwrite_results,
        max_workers=int(args.max_workers),
        progress_every=int(args.progress_every),
        blob_retries=int(args.blob_retries),
        retry_backoff_sec=float(args.retry_backoff_sec),
        max_blobs=args.max_blobs,
        logger=logger,
    )


if __name__ == "__main__":
    raise SystemExit(main())
