#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEEP_ARTIFACT_ROOT = (
    ROOT.parent / "project1_ucsc_phd_runtime" / "multimodel_v8_he2_dqlm_multivar_al_keep_from_exal_winners_20260602"
)
DEFAULT_DROP_ARTIFACT_ROOT = (
    ROOT.parent
    / "project1_ucsc_phd_runtime"
    / "multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602"
)
DEFAULT_SESSION = "he2_exal_drop_q50repair_20260602"
DEFAULT_STATUS_NAME = "drop_after_al_keep_handoff_status.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def matrix_dir(artifact_root: Path) -> Path:
    return artifact_root / "control" / "publication_relaunch_matrix"


def status_path(drop_artifact_root: Path) -> Path:
    return matrix_dir(drop_artifact_root) / DEFAULT_STATUS_NAME


def read_status_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def summarize_matrix(matrix_path: Path) -> dict[str, Any]:
    rows = read_status_rows(matrix_path)
    statuses = [str(row.get("status", "")).strip().lower() for row in rows]
    phases = [str(row.get("phase", "")).strip().lower() for row in rows]
    if not matrix_path.exists():
        state = "missing"
    elif not rows:
        state = "not_started"
    elif any(status == "fail" for status in statuses):
        state = "failed"
    elif statuses and all(status == "pass" for status in statuses):
        state = "passed"
    elif any(status in {"pending", "running", "in_progress"} for status in statuses + phases):
        state = "running"
    else:
        state = "not_started"
    return {
        "path": str(matrix_path),
        "state": state,
        "rows": len(rows),
        "pass": sum(1 for status in statuses if status == "pass"),
        "fail": sum(1 for status in statuses if status == "fail"),
        "pending": sum(1 for status in statuses if status == "pending"),
        "statuses": sorted(set(statuses)),
        "phases": sorted(set(phases)),
    }


def active_unified_count(artifact_root: Path) -> int:
    proc = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True, text=True, check=True)
    needle = str(artifact_root.resolve())
    count = 0
    for line in proc.stdout.splitlines():
        if "scripts/unified_run.R" in line and "--config" in line and needle in line:
            count += 1
    return count


def tmux_has_session(session: str) -> bool:
    proc = subprocess.run(["tmux", "has-session", "-t", session], capture_output=True, text=True, check=False)
    return proc.returncode == 0


def validate_drop_package(drop_artifact_root: Path) -> dict[str, Any]:
    cmd = [
        "python3",
        "scripts/validate_he2_exdqlm_multivar_drop_current_prelaunch.py",
        "--artifact-root",
        str(drop_artifact_root),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": "\n".join(proc.stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(proc.stderr.splitlines()[-20:]),
    }


def launch_tmux_session(session: str, launch_script: Path, stdout_log: Path) -> dict[str, Any]:
    if tmux_has_session(session):
        return {"ok": False, "detail": f"tmux session already exists: {session}"}
    if not launch_script.exists():
        return {"ok": False, "detail": f"missing launch script: {launch_script}"}
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    command = f"bash {shlex.quote(str(launch_script))} |& tee {shlex.quote(str(stdout_log))}"
    proc = subprocess.run(
        ["tmux", "new-session", "-d", "-s", session, command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "session": session,
        "command": command,
        "stdout_log": str(stdout_log),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def write_status(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def handoff_once(
    keep_artifact_root: Path,
    drop_artifact_root: Path,
    session: str,
    *,
    dry_run: bool = False,
    active_count: Callable[[Path], int] = active_unified_count,
    validate_drop: Callable[[Path], dict[str, Any]] = validate_drop_package,
    launch_session: Callable[[str, Path, Path], dict[str, Any]] = launch_tmux_session,
    has_session: Callable[[str], bool] = tmux_has_session,
) -> dict[str, Any]:
    keep_matrix = summarize_matrix(matrix_dir(keep_artifact_root) / "matrix_status.csv")
    drop_matrix = summarize_matrix(matrix_dir(drop_artifact_root) / "matrix_status.csv")
    active_keep = active_count(keep_artifact_root)
    active_drop = active_count(drop_artifact_root)
    payload: dict[str, Any] = {
        "checked_at_utc": utc_now(),
        "state": "waiting",
        "keep_artifact_root": str(keep_artifact_root),
        "drop_artifact_root": str(drop_artifact_root),
        "drop_tmux_session": session,
        "keep_matrix": keep_matrix,
        "drop_matrix": drop_matrix,
        "active_keep_unified_run_count": active_keep,
        "active_drop_unified_run_count": active_drop,
        "dry_run": dry_run,
    }

    if keep_matrix["state"] == "failed":
        payload["state"] = "keep_failed"
        return payload
    if keep_matrix["state"] != "passed":
        payload["state"] = "waiting_for_keep"
        return payload
    if active_keep > 0:
        payload["state"] = "waiting_for_keep_processes_to_exit"
        return payload
    if drop_matrix["state"] == "failed":
        payload["state"] = "drop_matrix_failed_not_launching"
        return payload
    if drop_matrix["state"] == "passed":
        payload["state"] = "drop_already_completed"
        return payload
    if active_drop > 0 or has_session(session):
        payload["state"] = "drop_already_active"
        return payload

    validation = validate_drop(drop_artifact_root)
    payload["drop_validation"] = validation
    if not validation.get("ok"):
        payload["state"] = "drop_validation_failed_not_launching"
        return payload

    launch_script = matrix_dir(drop_artifact_root) / "launch_current_drop.sh"
    stdout_log = matrix_dir(drop_artifact_root) / "run_logs" / "drop_queue_tmux_stdout.log"
    if dry_run:
        payload["state"] = "drop_launch_dry_run_ready"
        payload["launch_script"] = str(launch_script)
        payload["stdout_log"] = str(stdout_log)
        return payload

    launch = launch_session(session, launch_script, stdout_log)
    payload["launch"] = launch
    payload["state"] = "drop_launched" if launch.get("ok") else "drop_launch_failed"
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch current-code exAL-M-T0 drop only after AL-M-T1 keep finishes.")
    parser.add_argument("--keep-artifact-root", type=Path, default=DEFAULT_KEEP_ARTIFACT_ROOT)
    parser.add_argument("--drop-artifact-root", type=Path, default=DEFAULT_DROP_ARTIFACT_ROOT)
    parser.add_argument("--session", default=DEFAULT_SESSION)
    parser.add_argument("--poll-seconds", type=int, default=300)
    parser.add_argument("--timeout-seconds", type=int, default=72 * 60 * 60)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    deadline = time.time() + args.timeout_seconds
    out_path = status_path(args.drop_artifact_root)
    while True:
        payload = handoff_once(
            args.keep_artifact_root.resolve(),
            args.drop_artifact_root.resolve(),
            args.session,
            dry_run=args.dry_run,
        )
        write_status(out_path, payload)
        print(json.dumps(payload, sort_keys=True), flush=True)
        state = payload["state"]
        if state in {
            "drop_launched",
            "drop_already_active",
            "drop_already_completed",
            "drop_launch_dry_run_ready",
        }:
            return 0
        if state in {
            "keep_failed",
            "drop_matrix_failed_not_launching",
            "drop_validation_failed_not_launching",
            "drop_launch_failed",
        }:
            return 1
        if args.once:
            return 2
        if time.time() >= deadline:
            payload["state"] = "timeout"
            payload["timed_out_at_utc"] = utc_now()
            write_status(out_path, payload)
            return 2
        time.sleep(max(args.poll_seconds, 30))


if __name__ == "__main__":
    raise SystemExit(main())
