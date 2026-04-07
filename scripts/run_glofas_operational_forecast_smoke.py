#!/usr/bin/env python3
"""Run a bounded, reproducible GLOFAS operational forecast smoke suite."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import yaml


DEFAULT_CONFIG = Path("config/recovery_site11160500.yaml")
DEFAULT_DATES = ["2020-01-16", "2022-12-25"]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the GLOFAS operational forecast smoke suite.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--recovery-run-root", type=Path, default=None)
    parser.add_argument("--dates", nargs="*", default=DEFAULT_DATES)
    parser.add_argument("--post-days", type=int, default=28)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_recovery_run_root(cfg: dict, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    site_id = str(cfg["site"]["usgs_site"])
    runtime_root = Path(cfg["runtime"]["root"]).resolve()
    campaign_slug = str(cfg["runtime"]["campaign_slug"])
    site_root = runtime_root / campaign_slug / f"site={site_id}"
    candidates = sorted(site_root.glob("recovery_run=*"))
    if not candidates:
        raise SystemExit(f"No recovery_run=* directories found under {site_root}")
    return candidates[-1]


def ensure_family_root(root: Path) -> Path:
    family_root = root / "family=glofas_operational_forecasts"
    for subdir in ["manifests", "logs", "outputs", "smoke", "health_checks", "audits", "provenance"]:
        (family_root / subdir).mkdir(parents=True, exist_ok=True)
    return family_root


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_and_log(cmd: List[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("[CMD] " + " ".join(cmd) + "\n")
        handle.flush()
        proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, check=False, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"Command failed with code {proc.returncode}: {' '.join(cmd)}\nSee log: {log_path}")


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config)
    recovery_run_root = resolve_recovery_run_root(cfg, args.recovery_run_root)
    family_root = ensure_family_root(recovery_run_root)
    smoke_id = f"site11160500_glofas_operational_forecast_smoke_{now_utc()}"
    smoke_root = family_root / "smoke" / smoke_id
    download_root = smoke_root / "download_root"
    extract_root = smoke_root / "forecast_cache" / "glofas"
    suite_manifest_path = smoke_root / "suite_manifest.json"
    health_json = smoke_root / "health_checks" / "glofas_operational_forecast_health.json"
    dates_file = smoke_root / "manifests" / "issue_dates.txt"
    intervals_file = smoke_root / "manifests" / "intervals.txt"

    site = cfg["site"]
    lat = float(site["lat"])
    lon = float(site["lon"])
    issue_dates = [str(value) for value in args.dates]
    write_text(dates_file, "\n".join(issue_dates) + "\n")
    write_text(intervals_file, "\n".join(f"{value} {value}" for value in issue_dates) + "\n")

    downloader = [
        sys.executable,
        "glofas_operational_mediumrange_download_point.py",
        "--run",
        "--intervals-file",
        str(intervals_file),
        "--out-root",
        str(download_root),
        "--lat",
        str(lat),
        "--lon",
        str(lon),
        "--verbose",
    ]
    extractor = [
        sys.executable,
        "scripts/forecats_extract_glofas_batch.py",
        "--grib-root",
        str(download_root / "grib"),
        "--dates-file",
        str(dates_file),
        "--out-root",
        str(extract_root),
        "--lat",
        str(lat),
        "--lon",
        str(lon),
        "--var",
        "dis24",
        "--control-dtype",
        "cf",
        "--perturbed-dtype",
        "pf",
        "--cell-policy",
        "nearest_valid",
        "--shift-days",
        "1",
        "--post-days",
        str(int(args.post_days)),
        "--verbose",
    ]
    health = [
        sys.executable,
        "scripts/check_glofas_operational_forecast_health.py",
        "--download-root",
        str(download_root),
        "--extract-root",
        str(extract_root),
        "--dates-file",
        str(dates_file),
        "--post-days",
        str(int(args.post_days)),
        "--out-json",
        str(health_json),
        "--extract-rerun-log",
        str(smoke_root / "logs" / "extract_rerun.log"),
    ]

    suite_manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "recovery_run_root": str(recovery_run_root),
        "family_root": str(family_root),
        "smoke_root": str(smoke_root),
        "issue_dates": issue_dates,
        "site": site,
        "commands": {
            "download_initial": downloader,
            "extract_initial": extractor,
            "download_rerun": downloader,
            "extract_rerun": extractor,
            "health": health,
        },
    }
    suite_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    suite_manifest_path.write_text(json.dumps(suite_manifest, indent=2) + "\n", encoding="utf-8")

    run_and_log(downloader, smoke_root / "logs" / "download_initial.log")
    run_and_log(extractor, smoke_root / "logs" / "extract_initial.log")
    run_and_log(downloader, smoke_root / "logs" / "download_rerun.log")
    run_and_log(extractor, smoke_root / "logs" / "extract_rerun.log")
    run_and_log(health, smoke_root / "logs" / "health.log")

    print(json.dumps({"ok": True, "smoke_root": str(smoke_root), "health_json": str(health_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
