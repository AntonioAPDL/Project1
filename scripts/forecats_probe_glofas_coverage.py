#!/usr/bin/env python3
"""Lightweight EWDS probe for GloFAS historical/forecast/reforecast coverage checks.

Purpose:
- Run small metadata-driven download probes (or dry-run plans) for the three
  GloFAS products.
- Record success/failure per request to support coverage-window investigation
  without bulk transfers.

This script is intentionally conservative:
- One small request per product by default.
- Small spatial area around a target point.
- Short leadtime request for forecast/reforecast (24h).
- Default reforecast probe date is pinned to a known-valid EWDS response date.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence


DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464
DEFAULT_BUFFER_DEG = 0.2
DEFAULT_PROBE_DATE = "2023-03-27"
DEFAULT_REFORECAST_DATE = "2021-01-04"


@dataclass(frozen=True)
class ProbeCase:
    case_id: str
    dataset: str
    request: Dict[str, object]


def parse_date(raw: str) -> date:
    return datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()


def area_bbox(lat: float, lon: float, buffer_deg: float) -> List[float]:
    return [lat + buffer_deg, lon - buffer_deg, lat - buffer_deg, lon + buffer_deg]


def build_default_cases(
    probe_date: date,
    reforecast_date: date,
    lat: float,
    lon: float,
    buffer_deg: float,
) -> List[ProbeCase]:
    area = area_bbox(lat, lon, buffer_deg)

    hist_req: Dict[str, object] = {
        "system_version": ["version_4_0"],
        "hydrological_model": ["lisflood"],
        "product_type": ["consolidated"],
        "variable": ["river_discharge_in_the_last_24_hours"],
        "hyear": [f"{probe_date.year:04d}"],
        "hmonth": [f"{probe_date.month:02d}"],
        "hday": [f"{probe_date.day:02d}"],
        "data_format": "grib2",
        "download_format": "zip",
        "area": area,
    }

    fc_req: Dict[str, object] = {
        "system_version": ["operational"],
        "hydrological_model": ["lisflood"],
        "product_type": ["control_forecast"],
        "variable": ["river_discharge_in_the_last_24_hours"],
        "year": [f"{probe_date.year:04d}"],
        "month": [f"{probe_date.month:02d}"],
        "day": [f"{probe_date.day:02d}"],
        "leadtime_hour": ["24"],
        "data_format": "grib2",
        "download_format": "zip",
        "area": area,
    }

    rf_req: Dict[str, object] = {
        "system_version": ["version_4_0"],
        "hydrological_model": ["lisflood"],
        "product_type": ["control_reforecast"],
        "variable": ["river_discharge_in_the_last_24_hours"],
        "hyear": [f"{reforecast_date.year:04d}"],
        "hmonth": [f"{reforecast_date.month:02d}"],
        "hday": [f"{reforecast_date.day:02d}"],
        "leadtime_hour": ["24"],
        "data_format": "grib2",
        "download_format": "zip",
        "area": area,
    }

    return [
        ProbeCase(case_id="historical_smoke", dataset="cems-glofas-historical", request=hist_req),
        ProbeCase(case_id="forecast_smoke", dataset="cems-glofas-forecast", request=fc_req),
        ProbeCase(case_id="reforecast_smoke", dataset="cems-glofas-reforecast", request=rf_req),
    ]


def load_cases_from_json(path: Path) -> List[ProbeCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("cases-json must contain a list of case objects")
    out: List[ProbeCase] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"cases-json item #{i} must be an object")
        try:
            case_id = str(item["case_id"]).strip()
            dataset = str(item["dataset"]).strip()
            request = item["request"]
        except KeyError as exc:
            raise ValueError(f"cases-json item #{i} missing key: {exc}") from exc
        if not case_id or not dataset or not isinstance(request, dict):
            raise ValueError(f"cases-json item #{i} has invalid values")
        out.append(ProbeCase(case_id=case_id, dataset=dataset, request=request))
    return out


def setup_logger(log_file: Path, verbose: bool) -> logging.Logger:
    logger = logging.getLogger("glofas_probe")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO if verbose else logging.WARNING)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def write_manifest_row(manifest_path: Path, row: Dict[str, object]) -> None:
    exists = manifest_path.exists()
    with manifest_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            w.writeheader()
        w.writerow(row)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run lightweight EWDS probe requests for GloFAS coverage investigation"
    )
    ap.add_argument(
        "--out-root",
        type=Path,
        default=Path("repro") / "glofas_probe_runs",
        help="Directory for probe outputs/logs/manifests",
    )
    ap.add_argument(
        "--probe-date",
        default=DEFAULT_PROBE_DATE,
        help="Date used for historical + forecast smoke case (YYYY-MM-DD)",
    )
    ap.add_argument(
        "--reforecast-date",
        default=DEFAULT_REFORECAST_DATE,
        help="Date used for reforecast smoke case (YYYY-MM-DD)",
    )
    ap.add_argument("--lat", type=float, default=DEFAULT_LAT)
    ap.add_argument("--lon", type=float, default=DEFAULT_LON)
    ap.add_argument("--buffer-deg", type=float, default=DEFAULT_BUFFER_DEG)
    ap.add_argument(
        "--cases-json",
        type=Path,
        default=None,
        help="Optional JSON file with explicit case list; overrides built-in smoke cases",
    )
    ap.add_argument(
        "--run",
        action="store_true",
        help="Execute EWDS retrievals. Without this flag, only dry-run planning is performed.",
    )
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    return ap.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    probe_date = parse_date(args.probe_date)
    reforecast_date = parse_date(args.reforecast_date)

    run_id = datetime.utcnow().strftime("probe_%Y%m%dT%H%M%SZ")
    run_dir = args.out_root / run_id
    downloads_dir = run_dir / "downloads"
    logs_dir = run_dir / "logs"
    manifests_dir = run_dir / "manifests"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logger(logs_dir / "probe.log", verbose=args.verbose)
    manifest_path = manifests_dir / "probe_manifest.csv"

    if args.cases_json is not None:
        cases = load_cases_from_json(args.cases_json)
    else:
        cases = build_default_cases(
            probe_date=probe_date,
            reforecast_date=reforecast_date,
            lat=args.lat,
            lon=args.lon,
            buffer_deg=args.buffer_deg,
        )

    # Persist resolved case requests for reproducibility.
    (run_dir / "cases_resolved.json").write_text(
        json.dumps(
            [
                {"case_id": c.case_id, "dataset": c.dataset, "request": c.request}
                for c in cases
            ],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    logger.info("Run directory: %s", run_dir)
    logger.info("Mode: %s", "run" if args.run else "dry-run")
    logger.info("Cases: %d", len(cases))

    client = None
    if args.run:
        try:
            import cdsapi  # type: ignore

            client = cdsapi.Client()
        except Exception as exc:
            logger.error("Unable to initialize cdsapi.Client(): %s", exc)
            return 2

    for case in cases:
        out_path = downloads_dir / f"{case.case_id}.zip"
        status = "planned"
        err: Optional[str] = None
        bytes_out: Optional[int] = None

        if out_path.exists() and out_path.stat().st_size > 0 and not args.overwrite:
            status = "skipped_exists"
            bytes_out = int(out_path.stat().st_size)
            logger.info("[SKIP] %s -> %s", case.case_id, out_path)
        elif not args.run:
            status = "dry_run"
            logger.info("[DRY] %s dataset=%s", case.case_id, case.dataset)
        else:
            assert client is not None
            try:
                logger.info("[RUN] %s dataset=%s", case.case_id, case.dataset)
                client.retrieve(case.dataset, case.request).download(str(out_path))
                status = "ok"
                bytes_out = int(out_path.stat().st_size) if out_path.exists() else None
                logger.info("[OK] %s bytes=%s", case.case_id, bytes_out)
            except Exception as exc:
                status = "error"
                err = str(exc)
                logger.error("[ERR] %s: %s", case.case_id, err)

        write_manifest_row(
            manifest_path,
            {
                "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "run_id": run_id,
                "case_id": case.case_id,
                "dataset": case.dataset,
                "status": status,
                "bytes": bytes_out,
                "output_path": str(out_path),
                "error": err,
                "request_json": json.dumps(case.request, sort_keys=True),
            },
        )

    logger.info("Completed. Manifest: %s", manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
