#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "unified_runs_selected_output_support_20260609" / (
    "multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_"
    "authoritative_support_r3_20260609.yaml"
)

SUPPORT_FILES = [
    "authoritative_usgs_quantile_dynamics_summary.csv",
    "authoritative_usgs_quantile_dynamics_summary.rds",
    "authoritative_component_summary.csv",
    "authoritative_component_summary.rds",
    "authoritative_selected_support_lineage.csv",
    "authoritative_selected_support_manifest.json",
]


def load_yaml_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload if isinstance(payload, dict) else {}


def load_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def expected_run_root(config_path: Path) -> Path:
    cfg = load_yaml_optional(config_path)
    run = cfg.get("run", {})
    run_id = str(run.get("run_id", "")).strip()
    runs_root = str(run.get("run_root", "")).strip()
    if not run_id or not runs_root:
        raise ValueError(f"Could not resolve run root from config: {config_path}")
    return Path(runs_root).expanduser().resolve() / run_id


def pid_alive(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stage_summary(manifest: dict[str, Any]) -> str:
    stages = manifest.get("stages", {})
    if not isinstance(stages, dict) or not stages:
        return "no_manifest_stages"
    parts = []
    for name in ["forecats", "data_prep_shared", "fit", "post", "validate", "report"]:
        stage = stages.get(name, {})
        status = stage.get("status", "missing") if isinstance(stage, dict) else "missing"
        parts.append(f"{name}:{status}")
    return ", ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize the isolated HE2 selected-output support replay.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config_path = args.config.resolve()
    run_root = expected_run_root(config_path)
    replay_root = run_root.parent.parent
    state_dir = replay_root / "control" / "launch_state"
    launch = load_json_optional(state_dir / "last_selected_output_support_replay_launch.json")
    pid = launch.get("pid")
    pid_int = int(pid) if isinstance(pid, int) or (isinstance(pid, str) and pid.isdigit()) else None
    manifest = load_yaml_optional(run_root / "run_manifest.yaml")
    output_root = run_root / "post" / "outputs" / run_root.name
    support_state = {name: (output_root / name).exists() for name in SUPPORT_FILES}
    rdata_count = len(list(run_root.rglob("*.RData"))) + len(list(run_root.rglob("*.rdata")))
    payload = {
        "config": str(config_path),
        "run_id": run_root.name,
        "run_root": str(run_root),
        "pid": pid_int,
        "pid_alive": pid_alive(pid_int),
        "manifest_exists": (run_root / "run_manifest.yaml").exists(),
        "finished_at_utc": manifest.get("timestamps", {}).get("finished_at_utc") if manifest else None,
        "stages": stage_summary(manifest),
        "output_root": str(output_root),
        "support_files_present": support_state,
        "support_complete": all(support_state.values()),
        "rdata_count_under_run": rdata_count,
        "stdout_log": launch.get("stdout_log", ""),
        "stderr_log": launch.get("stderr_log", ""),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("| Field | Value |")
        print("|---|---|")
        for key in [
            "run_id",
            "pid",
            "pid_alive",
            "manifest_exists",
            "finished_at_utc",
            "stages",
            "support_complete",
            "rdata_count_under_run",
            "output_root",
            "stdout_log",
            "stderr_log",
        ]:
            print(f"| `{key}` | `{payload[key]}` |")
    if payload["support_complete"]:
        return 0
    if payload["pid_alive"]:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
