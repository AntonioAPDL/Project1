#!/usr/bin/env python3
"""
Download GloFAS operational medium-range ensemble forecasts (GRIB) for a point-area box.

Key design choices:
- No pandas/pygrib dependency (downloader only).
- Idempotent downloads (skip if file exists and non-empty unless --overwrite).
- Structured output layout + manifest CSV for reproducibility.
- Default date coverage = NWM/NWS "7-member available" blocks intersected with
  the common window 2019-11-05 → 2023-01-31.

Example:
  python3 glofas_operational_mediumrange_download_grib.py --dry-run
  python3 glofas_operational_mediumrange_download_grib.py --run
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    import cdsapi  # type: ignore
except Exception as e:
    cdsapi = None  # type: ignore


# -----------------------------
# Defaults (edit if needed)
# -----------------------------

DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464  # keep in [-180, 180]
DEFAULT_BUFFER_DEG = 1.0

DEFAULT_OUT_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd/data/glofas_operational_medium_range")

# NWM/NWS "7-member available" blocks clipped to 2019-11-05 → 2023-01-31
DEFAULT_INTERVALS = [
    ("2019-11-05", "2020-03-11"),
    ("2020-03-17", "2020-07-28"),
    ("2020-07-30", "2020-11-13"),
    ("2020-11-15", "2022-07-13"),
    ("2022-07-15", "2023-01-31"),
]

DATASET_NAME = "cems-glofas-forecast"
SYSTEM_VERSION = "operational"
VARIABLE = "river_discharge_in_the_last_24_hours"
PRODUCT_TYPE = ["control_forecast", "ensemble_perturbed_forecasts"]
LEADTIME_HOUR = [f"{h:d}" for h in range(24, 721, 24)]  # 24..720 step 24


# -----------------------------
# Helpers
# -----------------------------

@dataclass(frozen=True)
class Interval:
    start: date
    end: date  # inclusive

    def iter_days(self) -> Iterable[date]:
        d = self.start
        while d <= self.end:
            yield d
            d += timedelta(days=1)


def parse_ymd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def choose_hydrological_model(issue_date: date) -> str:
    # From your original logic:
    # before 2021-05-26 -> htessel_lisflood; else lisflood
    lisflood_start = date(2021, 5, 26)
    return "htessel_lisflood" if issue_date < lisflood_start else "lisflood"


def area_bbox(lat: float, lon: float, buffer_deg: float) -> List[float]:
    # Keep the same geometry you used previously (2*buffer in lat, buffer in lon)
    north = lat + 2.0 * buffer_deg
    west = lon - buffer_deg
    south = lat - 2.0 * buffer_deg
    east = lon + buffer_deg
    return [north, west, south, east]


def short_hash(d: Dict) -> str:
    payload = json.dumps(d, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:10]


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def is_nonempty_file(p: Path) -> bool:
    return p.exists() and p.is_file() and p.stat().st_size > 0


def build_request(issue: date, lat: float, lon: float, buffer_deg: float) -> Tuple[Dict, str]:
    model = choose_hydrological_model(issue)
    area = area_bbox(lat, lon, buffer_deg)
    req = {
        "system_version": SYSTEM_VERSION,
        "hydrological_model": model,
        "product_type": PRODUCT_TYPE,
        "variable": VARIABLE,
        "year": f"{issue.year:04d}",
        "month": f"{issue.month:02d}",
        "day": f"{issue.day:02d}",
        "leadtime_hour": LEADTIME_HOUR,
        "format": "grib",
        "area": area,
    }
    # Stable request id for naming/traceability
    req_id = f"{SYSTEM_VERSION}_{model}_{issue.isoformat()}_{short_hash(req)}"
    return req, req_id


def default_output_path(out_root: Path, issue: date, req_id: str) -> Path:
    # Organized partitioned structure:
    #   .../grib/issue_date=YYYY-MM-DD/<req_id>.grib
    issue_dir = out_root / "grib" / f"issue_date={issue.isoformat()}"
    ensure_dir(issue_dir)
    return issue_dir / f"{req_id}.grib"


def manifest_path(out_root: Path, explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        ensure_dir(explicit.parent)
        return explicit
    ensure_dir(out_root / "manifests")
    return out_root / "manifests" / "download_manifest.csv"


def log_path(out_root: Path, explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        ensure_dir(explicit.parent)
        return explicit
    ensure_dir(out_root / "logs")
    return out_root / "logs" / "download.log"


def setup_logger(logfile: Path, verbose: bool) -> logging.Logger:
    logger = logging.getLogger(f"glofas_download:{logfile}")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if re-imported
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO if verbose else logging.WARNING)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


def append_manifest_row(mpath: Path, row: Dict[str, str]) -> None:
    exists = mpath.exists()
    with mpath.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


# -----------------------------
# Main download routine
# -----------------------------

def run_download(
    intervals: List[Interval],
    lat: float,
    lon: float,
    buffer_deg: float,
    out_root: Path,
    manifest_file: Optional[Path],
    log_file: Optional[Path],
    dry_run: bool,
    overwrite: bool,
    verbose: bool,
) -> None:
    ensure_dir(out_root)
    logger = setup_logger(log_path(out_root, log_file), verbose)
    mpath = manifest_path(out_root, manifest_file)

    if cdsapi is None:
        raise RuntimeError(
            "cdsapi import failed. Install it in the interpreter you are using:\n"
            "  python3 -m pip install --user cdsapi\n"
            "or inside your venv:\n"
            "  python -m pip install cdsapi"
        )

    # Create client once
    client = cdsapi.Client()

    total = sum((i.end - i.start).days + 1 for i in intervals)
    logger.info(f"Planned issue dates: {total} days across {len(intervals)} intervals.")
    logger.info(f"Output root: {out_root}")
    logger.info(f"Target (lat, lon) = ({lat}, {lon}), buffer_deg = {buffer_deg}")
    logger.info(f"Dry-run: {dry_run} | Overwrite: {overwrite}")

    for interval in intervals:
        logger.info(f"Interval: {interval.start.isoformat()} → {interval.end.isoformat()}")

        for issue in interval.iter_days():
            req, req_id = build_request(issue, lat, lon, buffer_deg)
            out_file = default_output_path(out_root, issue, req_id)

            status = "planned"
            msg = ""

            if is_nonempty_file(out_file) and not overwrite:
                status = "skipped_exists"
                msg = "file exists"
                logger.info(f"[SKIP] {issue.isoformat()} -> {out_file}")
                append_manifest_row(
                    mpath,
                    {
                        "issue_date": issue.isoformat(),
                        "status": status,
                        "path": str(out_file),
                        "req_id": req_id,
                        "hydrological_model": req["hydrological_model"],
                        "notes": msg,
                        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
                    },
                )
                continue

            if dry_run:
                logger.info(f"[DRY] {issue.isoformat()} -> {out_file}")
                append_manifest_row(
                    mpath,
                    {
                        "issue_date": issue.isoformat(),
                        "status": status,
                        "path": str(out_file),
                        "req_id": req_id,
                        "hydrological_model": req["hydrological_model"],
                        "notes": "dry-run",
                        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
                    },
                )
                continue

            # Persist request metadata next to the file (reproducibility)
            meta_path = out_file.with_suffix(".request.json")
            try:
                ensure_dir(out_file.parent)

                # Write request metadata first
                with meta_path.open("w") as f:
                    json.dump(req, f, indent=2, sort_keys=True)

                logger.info(f"[GET] {issue.isoformat()} -> {out_file}")
                client.retrieve(DATASET_NAME, req, str(out_file))

                # Validate non-empty
                if not is_nonempty_file(out_file):
                    status = "error_empty"
                    msg = "download produced empty file"
                    logger.error(f"[ERR] {issue.isoformat()} empty file: {out_file}")
                else:
                    status = "downloaded"
                    msg = "ok"
                    logger.info(f"[OK ] {issue.isoformat()} saved: {out_file} ({out_file.stat().st_size} bytes)")

            except Exception as e:
                status = "error_exception"
                msg = repr(e)
                logger.exception(f"[ERR] {issue.isoformat()} failed: {e}")

                # If partially created file, keep it for inspection but mark as error
            finally:
                append_manifest_row(
                    mpath,
                    {
                        "issue_date": issue.isoformat(),
                        "status": status,
                        "path": str(out_file),
                        "req_id": req_id,
                        "hydrological_model": req["hydrological_model"],
                        "notes": msg[:5000],
                        "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
                    },
                )


def load_intervals_from_file(path: Path) -> List[Interval]:
    """
    File format: two columns (start,end) either CSV with header or whitespace separated.
    Dates must be YYYY-MM-DD. End is inclusive.
    """
    intervals: List[Interval] = []
    text = path.read_text().strip().splitlines()
    if not text:
        return intervals

    # Try CSV first
    if "," in text[0]:
        import csv as _csv
        reader = _csv.DictReader(text)
        for row in reader:
            intervals.append(Interval(parse_ymd(row["start"]), parse_ymd(row["end"])))
        return intervals

    # Otherwise whitespace separated
    for line in text:
        if not line.strip() or line.strip().startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Bad interval line: {line!r} (expected: 'YYYY-MM-DD YYYY-MM-DD')")
        intervals.append(Interval(parse_ymd(parts[0]), parse_ymd(parts[1])))
    return intervals


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=DEFAULT_LAT)
    p.add_argument("--lon", type=float, default=DEFAULT_LON)
    p.add_argument("--buffer-deg", type=float, default=DEFAULT_BUFFER_DEG)
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)

    g = p.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="Do not download; only plan + write manifest.")
    g.add_argument("--run", action="store_true", help="Perform downloads.")

    p.add_argument("--overwrite", action="store_true", help="Redownload even if file exists.")
    p.add_argument("--verbose", action="store_true", help="More stdout logging.")

    p.add_argument(
        "--intervals-file",
        type=Path,
        default=None,
        help="Optional file with intervals. If not set, uses built-in NWM 7-member blocks.",
    )
    p.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="Optional manifest CSV path. Useful when running multiple disjoint splits in parallel.",
    )
    p.add_argument(
        "--log-path",
        type=Path,
        default=None,
        help="Optional log file path. Useful when running multiple disjoint splits in parallel.",
    )

    args = p.parse_args()

    dry_run = args.dry_run or (not args.run)  # default to dry-run unless --run

    if args.intervals_file is None:
        intervals = [Interval(parse_ymd(a), parse_ymd(b)) for a, b in DEFAULT_INTERVALS]
    else:
        intervals = load_intervals_from_file(args.intervals_file)
        if not intervals:
            raise ValueError(f"No intervals found in {args.intervals_file}")

    run_download(
        intervals=intervals,
        lat=args.lat,
        lon=args.lon,
        buffer_deg=args.buffer_deg,
        out_root=args.out_root,
        manifest_file=args.manifest_path,
        log_file=args.log_path,
        dry_run=dry_run,
        overwrite=args.overwrite,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
