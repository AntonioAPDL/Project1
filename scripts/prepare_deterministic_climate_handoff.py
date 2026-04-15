#!/usr/bin/env python3
"""Resume/build the deterministic-climate handoff from an existing GEFS+NWM manifest run.

This orchestrator is meant for the all-9 feature-covariate relaunch. It:

1. Reuses the best available GEFS extract subdir.
2. Runs the missing NWM extraction if needed.
3. Validates the combined GEFS+NWM outputs.
4. Builds the downstream handoff cache consumed by deterministic climate substitution.
5. Optionally updates the feature-covariate campaign template with the resolved handoff root.

The script is config-driven so the exact run directory, extract subdirs, and
downstream campaign config are recorded in versioned YAML.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "config/deterministic_climate_handoff.site11160500.yaml"


try:
    import yaml
except Exception as exc:  # pragma: no cover
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare the deterministic-climate handoff from an existing manifest run.")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--dry-run", action="store_true", help="Plan only; do not run extraction, health, or handoff steps.")
    p.add_argument("--force-nwm", action="store_true", help="Re-run the NWM extraction even if an output CSV already exists.")
    p.add_argument(
        "--skip-campaign-sync",
        action="store_true",
        help="Do not patch the downstream feature-covariate campaign template with the resolved handoff root.",
    )
    return p.parse_args()


def load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:  # pragma: no cover
        raise RuntimeError(f"PyYAML import failed: {YAML_IMPORT_ERROR}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise SystemExit(f"YAML config must load to a mapping: {path}")
    return payload


def resolve_repo_path(value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(str(value))
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def resolve_run_path(run_dir: Path, value: str) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path.resolve()
    return (run_dir / path).resolve()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def select_existing_extract_subdir(run_dir: Path, subdirs: Sequence[str], required_relpath: str) -> str:
    for subdir in subdirs:
        candidate = run_dir / subdir / required_relpath
        if candidate.exists():
            return str(subdir)
    raise SystemExit(
        "No valid extract subdir found. Checked: "
        + ", ".join(f"{subdir}/{required_relpath}" for subdir in subdirs)
    )


def load_site_config(path: Path) -> Dict[str, Any]:
    payload = load_yaml(path)
    site = payload.get("site") or {}
    return {
        "usgs_site": str(site.get("usgs_site", "11160500")),
        "lat": float(site.get("lat", 37.0443931)),
        "lon": float(site.get("lon", -122.072464)),
    }


def handoff_root_for(run_dir: Path, out_subdir: str, usgs_site: str) -> Path:
    return (run_dir / out_subdir / f"site={usgs_site}" / f"run_id={run_dir.name}").resolve()


def command_to_str(cmd: Sequence[str]) -> str:
    return " ".join(str(part) for part in cmd)


def run_command(cmd: Sequence[str]) -> None:
    subprocess.run([str(part) for part in cmd], cwd=REPO_ROOT, check=True)


def sync_campaign_handoff_root(config_path: Path, handoff_root: Path) -> None:
    payload = load_yaml(config_path)
    inputs = payload.setdefault("inputs", {})
    det = inputs.setdefault("deterministic_climate", {})
    det["handoff_root"] = str(handoff_root)
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def build_plan(cfg: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    config_path = resolve_repo_path(args.config)
    if config_path is None or not config_path.exists():
        raise SystemExit(f"Config file not found: {args.config}")

    run_dir = resolve_repo_path(cfg.get("manifest_run_dir"))
    if run_dir is None or not run_dir.exists():
        raise SystemExit(f"Manifest run directory not found: {cfg.get('manifest_run_dir')}")

    site_config = resolve_repo_path(cfg.get("site_config"))
    if site_config is None or not site_config.exists():
        raise SystemExit(f"Site config not found: {cfg.get('site_config')}")
    site = load_site_config(site_config)

    gefs_cfg = cfg.get("gefs") or {}
    gefs_subdir = select_existing_extract_subdir(
        run_dir=run_dir,
        subdirs=gefs_cfg.get("preferred_extract_subdirs") or [],
        required_relpath="gefs/gefs_point_series.csv",
    )

    nwm_cfg = cfg.get("nwm") or {}
    nwm_subdir = str(nwm_cfg.get("extract_subdir", "extract_full"))
    nwm_csv = run_dir / nwm_subdir / "nwm" / "nwm_point_series.csv"
    need_nwm_extract = bool(args.force_nwm or not nwm_csv.exists())

    health_cfg = cfg.get("health") or {}
    health_out = resolve_run_path(run_dir, str(health_cfg.get("out_json", "health_checks/forecast_extract_health_detclim_ready.json")))
    health_rel = str(health_out.relative_to(run_dir))

    handoff_cfg = cfg.get("handoff") or {}
    handoff_out_subdir = str(handoff_cfg.get("out_subdir", "handoff_forecasts"))
    handoff_root = handoff_root_for(run_dir, handoff_out_subdir, site["usgs_site"])

    campaign_cfg = cfg.get("campaign_sync") or {}
    campaign_config_path = resolve_repo_path(campaign_cfg.get("config_path")) if campaign_cfg.get("enabled", False) else None

    nwm_extract_cmd = [
        "python3",
        str(REPO_ROOT / "scripts" / "extract_gefs_nwm_forecast_points.py"),
        "--manifest-run-dir",
        str(run_dir),
        "--out-subdir",
        nwm_subdir,
        "--sources",
        "nwm",
        "--nwm-workers",
        str(int(nwm_cfg.get("workers", 16))),
        "--batch-size",
        str(int(nwm_cfg.get("batch_size", 256))),
        "--nwm-file-retries",
        str(int(nwm_cfg.get("file_retries", 3))),
    ]
    if args.force_nwm:
        nwm_extract_cmd.append("--overwrite")

    health_cmd = [
        "python3",
        str(REPO_ROOT / "scripts" / "check_gefs_nwm_forecast_extract_health.py"),
        "--manifest-run-dir",
        str(run_dir),
        "--mode",
        "full",
        "--sources",
        "gefs,nwm",
        "--gefs-out-subdir",
        gefs_subdir,
        "--nwm-out-subdir",
        nwm_subdir,
        "--out-json",
        str(health_out),
    ]

    handoff_cmd = [
        "python3",
        str(REPO_ROOT / "scripts" / "consolidate_gefs_nwm_forecast_handoff.py"),
        "--manifest-run-dir",
        str(run_dir),
        "--site-config",
        str(site_config),
        "--health-json",
        health_rel,
        "--gefs-extract-subdir",
        gefs_subdir,
        "--nwm-extract-subdir",
        nwm_subdir,
        "--out-subdir",
        handoff_out_subdir,
    ]
    if bool(handoff_cfg.get("overwrite", True)):
        handoff_cmd.append("--overwrite")

    return {
        "config_path": str(config_path),
        "manifest_run_dir": str(run_dir),
        "site_config": str(site_config),
        "site": site,
        "selected_gefs_extract_subdir": gefs_subdir,
        "selected_nwm_extract_subdir": nwm_subdir,
        "nwm_output_csv": str(nwm_csv),
        "need_nwm_extract": need_nwm_extract,
        "health_out_json": str(health_out),
        "handoff_root": str(handoff_root),
        "campaign_sync_enabled": bool(campaign_cfg.get("enabled", False)),
        "campaign_config_path": str(campaign_config_path) if campaign_config_path else None,
        "commands": {
            "nwm_extract": nwm_extract_cmd,
            "health_check": health_cmd,
            "build_handoff": handoff_cmd,
        },
    }


def write_summary(run_dir: Path, payload: Dict[str, Any]) -> Path:
    summary_dir = run_dir / "handoff_prep"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "detclim_handoff_prepare_summary.json"
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return summary_path


def main() -> int:
    args = parse_args()
    config_path = resolve_repo_path(args.config)
    cfg = load_yaml(config_path)
    plan = build_plan(cfg, args)
    run_dir = Path(plan["manifest_run_dir"])

    summary: Dict[str, Any] = {
        "created_utc": now_utc_iso(),
        "dry_run": bool(args.dry_run),
        "force_nwm": bool(args.force_nwm),
        "plan": plan,
        "steps": [],
        "success": False,
    }

    if args.dry_run:
        summary["steps"].append({"step": "dry_run", "status": "planned"})
        summary_path = write_summary(run_dir, summary)
        print(json.dumps(summary, indent=2))
        print(f"[OK] wrote {summary_path}")
        return 0

    if plan["need_nwm_extract"]:
        cmd = plan["commands"]["nwm_extract"]
        run_command(cmd)
        summary["steps"].append({"step": "nwm_extract", "status": "ran", "command": command_to_str(cmd)})
    else:
        summary["steps"].append({"step": "nwm_extract", "status": "skipped_existing"})

    health_cmd = plan["commands"]["health_check"]
    run_command(health_cmd)
    summary["steps"].append({"step": "health_check", "status": "ran", "command": command_to_str(health_cmd)})

    handoff_cmd = plan["commands"]["build_handoff"]
    run_command(handoff_cmd)
    summary["steps"].append({"step": "build_handoff", "status": "ran", "command": command_to_str(handoff_cmd)})

    if plan["campaign_sync_enabled"] and not args.skip_campaign_sync:
        campaign_config_path = Path(plan["campaign_config_path"])
        sync_campaign_handoff_root(campaign_config_path, Path(plan["handoff_root"]))
        summary["steps"].append(
            {
                "step": "campaign_sync",
                "status": "ran",
                "config_path": str(campaign_config_path),
                "handoff_root": plan["handoff_root"],
            }
        )
    elif plan["campaign_sync_enabled"]:
        summary["steps"].append({"step": "campaign_sync", "status": "skipped_by_flag"})

    summary["success"] = True
    summary_path = write_summary(run_dir, summary)
    print(json.dumps(summary, indent=2))
    print(f"[OK] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
