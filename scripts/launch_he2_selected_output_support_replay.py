#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "unified_runs_selected_output_support_20260609" / (
    "multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_"
    "authoritative_support_r3_20260609.yaml"
)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def git_value(args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def expected_run_root(cfg: dict[str, Any]) -> Path:
    run = cfg.get("run", {})
    if not isinstance(run, dict):
        raise ValueError("config.run must be a mapping")
    run_id = str(run.get("run_id", "")).strip()
    run_root = str(run.get("run_root", "")).strip()
    if not run_id or not run_root:
        raise ValueError("config must define run.run_id and run.run_root")
    return Path(run_root).expanduser().resolve() / run_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch the isolated HE2 selected-output support replay as a detached process."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-existing-run-root",
        action="store_true",
        help="Allow launch when the expected run root already exists. Use only for intentional overwrite/retry configs.",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Missing replay config: {config_path}")
    cfg = load_yaml(config_path)
    run_root = expected_run_root(cfg)
    run_id = run_root.name
    if run_root.exists() and not args.allow_existing_run_root:
        raise FileExistsError(
            f"Refusing to launch because expected run root already exists: {run_root}. "
            "Generate a new tag or pass --allow-existing-run-root intentionally."
        )

    replay_root = run_root.parent.parent
    log_dir = args.log_dir.resolve() if args.log_dir is not None else replay_root / "control" / "logs"
    state_dir = replay_root / "control" / "launch_state"
    log_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(ROOT / "scripts" / "run_unified_with_cleanup.sh"),
        "--config",
        str(config_path),
    ]
    stdout_path = log_dir / f"{run_id}.out"
    stderr_path = log_dir / f"{run_id}.err"
    launch_payload: dict[str, Any] = {
        "launched_at_utc": iso_now(),
        "repo_root": str(ROOT),
        "git_head": git_value(["rev-parse", "HEAD"]),
        "git_branch": git_value(["branch", "--show-current"]),
        "git_status_short": git_value(["status", "--short"]),
        "config": str(config_path),
        "run_id": run_id,
        "expected_run_root": str(run_root),
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "command": cmd,
        "cleanup_after_post": True,
    }

    if args.dry_run:
        print(json.dumps(launch_payload, indent=2, sort_keys=True))
        return 0

    env = os.environ.copy()
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    with stdout_path.open("ab") as stdout_handle, stderr_path.open("ab") as stderr_handle:
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=stdout_handle,
            stderr=stderr_handle,
            env=env,
            start_new_session=True,
        )

    time.sleep(2)
    launch_payload["pid"] = proc.pid
    launch_payload["initial_returncode"] = proc.poll()
    launch_json = state_dir / "last_selected_output_support_replay_launch.json"
    launch_json.write_text(json.dumps(launch_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (state_dir / "selected_output_support_replay.pid").write_text(f"{proc.pid}\n", encoding="utf-8")
    print(json.dumps(launch_payload, indent=2, sort_keys=True))
    if launch_payload["initial_returncode"] not in (None, 0):
        print(f"Replay exited immediately; inspect {stdout_path} and {stderr_path}", file=sys.stderr)
        return int(launch_payload["initial_returncode"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
