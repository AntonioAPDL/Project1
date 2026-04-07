#!/usr/bin/env python3
"""Smoke-test the 6-way parallel GLOFAS operational split workflow."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import yaml

DEFAULT_CONFIG = Path("config/recovery_site11160500.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded smoke test for the parallel GLOFAS operational split workflow.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--recovery-run-root", type=Path, default=None)
    parser.add_argument("--num-splits", type=int, default=6)
    parser.add_argument("--smoke-days-per-split", type=int, default=1)
    parser.add_argument("--post-days", type=int, default=28)
    return parser.parse_args()


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def run_and_log(cmd: List[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("[CMD] " + " ".join(cmd) + "\n")
        handle.flush()
        proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, check=False, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"Command failed with code {proc.returncode}: {' '.join(cmd)}\nSee log: {log_path}")


def combine_manifests(manifest_paths: Iterable[Path], out_path: Path) -> None:
    rows: List[dict] = []
    fieldnames: List[str] = []
    for path in manifest_paths:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames and not fieldnames:
                fieldnames = list(reader.fieldnames)
            for row in reader:
                rows.append(row)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        if not fieldnames:
            fieldnames = ["issue_date", "status", "path", "req_id", "hydrological_model", "notes", "timestamp_utc"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config)
    recovery_run_root = resolve_recovery_run_root(cfg, args.recovery_run_root)
    family_root = recovery_run_root / "family=glofas_operational_forecasts"
    smoke_root = family_root / "smoke" / f"site11160500_glofas_operational_parallel_smoke_{now_utc()}"
    download_root = smoke_root / "download_root"
    extract_root = smoke_root / "forecast_cache" / "glofas"
    plan_root = smoke_root / "plan"
    manifest_dir = smoke_root / "manifests"
    log_dir = smoke_root / "logs"
    health_dir = smoke_root / "health_checks"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    health_dir.mkdir(parents=True, exist_ok=True)

    build_plan_cmd = [
        sys.executable,
        "scripts/build_glofas_operational_split_plan.py",
        "--out-dir",
        str(plan_root),
        "--num-splits",
        str(int(args.num_splits)),
        "--smoke-days-per-split",
        str(int(args.smoke_days_per_split)),
    ]
    run_and_log(build_plan_cmd, log_dir / "build_plan.log")

    split_summary = plan_root / "split_summary.csv"
    split_ids: List[str] = []
    with split_summary.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            split_ids.append(row["split_id"])

    site = cfg["site"]
    lat = str(float(site["lat"]))
    lon = str(float(site["lon"]))

    def split_manifest(split_id: str) -> Path:
        return manifest_dir / f"{split_id}_download_manifest.csv"

    def split_log(split_id: str, phase: str) -> Path:
        return log_dir / f"{split_id}_{phase}.log"

    for phase in ["initial", "rerun"]:
        for split_id in split_ids:
            intervals_file = plan_root / "splits" / f"{split_id}_intervals.csv"
            cmd = [
                sys.executable,
                "glofas_operational_mediumrange_download_point.py",
                "--run",
                "--intervals-file",
                str(intervals_file),
                "--out-root",
                str(download_root),
                "--manifest-path",
                str(split_manifest(split_id)),
                "--log-path",
                str(log_dir / f"{split_id}_download_internal.log"),
                "--lat",
                lat,
                "--lon",
                lon,
                "--verbose",
            ]
            run_and_log(cmd, split_log(split_id, phase))
        combine_manifests((split_manifest(split_id) for split_id in split_ids), download_root / "manifests" / "download_manifest.csv")
        if phase == "initial":
            extractor = [
                sys.executable,
                "scripts/forecats_extract_glofas_batch.py",
                "--grib-root",
                str(download_root / "grib"),
                "--dates-file",
                str(plan_root / "all_issue_dates.txt"),
                "--out-root",
                str(extract_root),
                "--lat",
                lat,
                "--lon",
                lon,
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
            run_and_log(extractor, log_dir / "extract_initial.log")
        else:
            extractor_rerun = [
                sys.executable,
                "scripts/forecats_extract_glofas_batch.py",
                "--grib-root",
                str(download_root / "grib"),
                "--dates-file",
                str(plan_root / "all_issue_dates.txt"),
                "--out-root",
                str(extract_root),
                "--lat",
                lat,
                "--lon",
                lon,
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
            run_and_log(extractor_rerun, log_dir / "extract_rerun.log")

    parallel_health_json = health_dir / "parallel_split_health.json"
    run_and_log(
        [
            sys.executable,
            "scripts/check_glofas_operational_parallel_health.py",
            "--campaign-root",
            str(smoke_root),
            "--out-json",
            str(parallel_health_json),
        ],
        log_dir / "parallel_health.log",
    )
    rerunaware_health_json = health_dir / "glofas_operational_forecast_health_rerunaware.json"
    run_and_log(
        [
            sys.executable,
            "scripts/check_glofas_operational_forecast_health.py",
            "--download-root",
            str(download_root),
            "--extract-root",
            str(extract_root),
            "--dates-file",
            str(plan_root / "all_issue_dates.txt"),
            "--post-days",
            str(int(args.post_days)),
            "--out-json",
            str(rerunaware_health_json),
            "--extract-rerun-log",
            str(log_dir / "extract_rerun.log"),
        ],
        log_dir / "rerunaware_health.log",
    )

    summary = {
        "ok": True,
        "smoke_root": str(smoke_root),
        "parallel_health_json": str(parallel_health_json),
        "rerunaware_health_json": str(rerunaware_health_json),
    }
    (smoke_root / "suite_manifest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
