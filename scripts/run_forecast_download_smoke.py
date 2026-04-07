#!/usr/bin/env python3
"""Run a bounded, reproducible smoke test for `forecast_download.py`."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml


DEFAULT_CONFIG = Path("config/recovery_site11160500.yaml")
DEFAULT_NWS_CONFIG = Path("config/nws_operational_latest.yaml")
DEFAULT_ISSUE_DATE = "2019-06-18"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the forecast_download.py smoke suite.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--nws-config", type=Path, default=DEFAULT_NWS_CONFIG)
    parser.add_argument("--recovery-run-root", type=Path, default=None)
    parser.add_argument("--issue-date", default=DEFAULT_ISSUE_DATE)
    parser.add_argument("--post-days", type=int, default=28)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def resolve_recovery_run_root(cfg: Dict[str, Any], explicit: Path | None) -> Path:
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
    family_root = root / "family=nws_operational_results_archive"
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


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    lat1r = math.radians(lat1)
    lon1r = math.radians(lon1)
    lat2r = math.radians(lat2)
    lon2r = math.radians(lon2)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon / 2.0) ** 2
    return 2.0 * r * math.asin(math.sqrt(a))


def main() -> int:
    args = parse_args()
    cfg = load_yaml(args.config)
    nws_cfg = load_yaml(args.nws_config)
    recovery_run_root = resolve_recovery_run_root(cfg, args.recovery_run_root)
    family_root = ensure_family_root(recovery_run_root)
    smoke_id = f"site11160500_forecast_download_smoke_{now_utc()}"
    smoke_root = family_root / "smoke" / smoke_id
    results_root = smoke_root / "outputs"
    extract_root = smoke_root / "forecast_cache" / "nws"
    dry_run_dir = smoke_root / "runs" / "forecast_download_dry_run"
    initial_run_dir = smoke_root / "runs" / "forecast_download_initial"
    rerun_dir = smoke_root / "runs" / "forecast_download_rerun"
    results_pkl = results_root / "results_smoke.pkl"
    suite_manifest_path = smoke_root / "suite_manifest.json"
    health_json = smoke_root / "health_checks" / "forecast_download_smoke_health.json"
    dates_file = smoke_root / "manifests" / "cutoff_dates.txt"
    alignment_json = smoke_root / "provenance" / "site_alignment.json"

    site = cfg["site"]
    nws_site = nws_cfg["site"]
    lat = float(site["lat"])
    lon = float(site["lon"])
    site_code = str(site["usgs_site"])
    issue_date = str(args.issue_date)
    write_text(dates_file, issue_date + "\n")

    alignment = {
        "recovery_site": site,
        "nws_site": nws_site,
        "site_code_matches": str(nws_site.get("usgs_site")) == site_code,
        "lat_matches": abs(float(nws_site.get("lat")) - lat) < 1e-9,
        "lon_matches": abs(float(nws_site.get("lon")) - lon) < 1e-9,
        "operational_feature_id": int(nws_site.get("feature_id")),
        "target_distance_km": haversine_km(lat, lon, float(nws_site.get("lat")), float(nws_site.get("lon"))),
    }
    alignment_json.parent.mkdir(parents=True, exist_ok=True)
    alignment_json.write_text(json.dumps(alignment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not alignment["site_code_matches"] or not alignment["lat_matches"] or not alignment["lon_matches"]:
        raise SystemExit(f"Site mismatch between {args.config} and {args.nws_config}; see {alignment_json}")

    common = [
        sys.executable,
        "forecast_download.py",
        "--config",
        str(args.config),
        "--start-date",
        issue_date,
        "--end-date",
        issue_date,
        "--results-out",
        str(results_pkl),
        "--max-workers",
        "2",
        "--progress-every",
        "20",
        "--blob-retries",
        "3",
        "--retry-backoff-sec",
        "1.0",
        "--verbose",
    ]
    dry_cmd = common + ["--run-dir", str(dry_run_dir), "--dry-run"]
    initial_cmd = common + ["--run-dir", str(initial_run_dir), "--run"]
    rerun_cmd = common + ["--run-dir", str(rerun_dir), "--run"]
    extract_cmd = [
        sys.executable,
        "scripts/forecats_extract_nws_batch.py",
        "--pkl",
        str(results_pkl),
        "--dates-file",
        str(dates_file),
        "--out-root",
        str(extract_root),
        "--post-days",
        str(int(args.post_days)),
        "--parse-issue-hour",
        "--issue-lookback-days",
        "40",
        "--weighting-scheme",
        "latest",
        "--verbose",
    ]
    health_cmd = [
        sys.executable,
        "scripts/check_forecast_download_health.py",
        "--run-dir",
        str(rerun_dir),
        "--results-pkl",
        str(results_pkl),
        "--extract-root",
        str(extract_root),
        "--expected-site-code",
        site_code,
        "--expected-lat",
        str(lat),
        "--expected-lon",
        str(lon),
        "--expected-feature-id",
        str(int(nws_site.get("feature_id"))),
        "--min-results",
        "80",
        "--expected-cutoff-date",
        issue_date,
        "--out-json",
        str(health_json),
    ]

    suite_manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "recovery_run_root": str(recovery_run_root),
        "family_root": str(family_root),
        "smoke_root": str(smoke_root),
        "issue_date": issue_date,
        "site": site,
        "nws_site": nws_site,
        "results_pkl": str(results_pkl),
        "commands": {
            "forecast_download_dry_run": dry_cmd,
            "forecast_download_initial": initial_cmd,
            "forecast_download_rerun": rerun_cmd,
            "extract_nws_batch": extract_cmd,
            "health": health_cmd,
        },
    }
    suite_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    suite_manifest_path.write_text(json.dumps(suite_manifest, indent=2) + "\n", encoding="utf-8")

    run_and_log(dry_cmd, smoke_root / "logs" / "forecast_download_dry_run.log")
    run_and_log(initial_cmd, smoke_root / "logs" / "forecast_download_initial.log")
    run_and_log(rerun_cmd, smoke_root / "logs" / "forecast_download_rerun.log")
    run_and_log(extract_cmd, smoke_root / "logs" / "extract_nws_batch.log")
    run_and_log(health_cmd, smoke_root / "logs" / "health.log")

    print(json.dumps({"ok": True, "smoke_root": str(smoke_root), "health_json": str(health_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
