#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from check_multimodel_v8_matrix_health import build_status  # noqa: E402
from multimodel_v8_lib import artifact_disk_free_gb, resolve_artifact_root  # noqa: E402
from run_multimodel_v8_queue import pgrep_active_v8, utc_now  # noqa: E402

DEFAULT_SAFE_ORDINARY_MAX = 6
STATE_DIRNAME = "controller_state"


def read_launch_settings(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise ValueError(f"Invalid launch settings line: {raw_line!r}")
        settings[key.strip()] = value.strip()
    return settings


def find_queue_controllers(matrix_dir: Path) -> list[dict[str, str]]:
    proc = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True, text=True, check=True)
    matches: list[dict[str, str]] = []
    matrix_key = str(matrix_dir)
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or "scripts/run_multimodel_v8_queue.py" not in line or matrix_key not in line:
            continue
        m = re.match(r"^(\d+)\s+(.*)$", line)
        if not m:
            continue
        matches.append({"pid": m.group(1), "command": m.group(2)})
    return matches


def extract_run_id_from_command(command: str) -> str | None:
    cfg_match = re.search(r"--config\s+(\S+multimodel_[^\s]+\.ya?ml)", command)
    if not cfg_match:
        return None
    return Path(cfg_match.group(1)).stem


def active_run_ids() -> list[str]:
    run_ids = []
    for row in pgrep_active_v8():
        run_id = extract_run_id_from_command(row["command"])
        if run_id:
            run_ids.append(run_id)
    return sorted(set(run_ids))


def choose_ordinary_max_concurrent(
    configured_value: int,
    requested_value: int | None,
    safe_cap: int,
) -> int:
    if requested_value is not None:
        return max(1, int(requested_value))
    return max(1, min(int(configured_value), int(safe_cap)))


def controller_state_dir(matrix_dir: Path) -> Path:
    return matrix_dir / STATE_DIRNAME


def collect_relaunch_snapshot(matrix_dir: Path, artifact_root: Path | None) -> dict[str, Any]:
    df = build_status(matrix_dir, artifact_root=artifact_root)
    counts = df["status"].value_counts().to_dict()
    pending_runs = sorted(df.loc[df["status"] == "pending", "run_id"].astype(str).tolist())
    failed_runs = sorted(df.loc[df["status"] == "fail", "run_id"].astype(str).tolist())
    active_ids = active_run_ids()
    orphan_pending = sorted(set(pending_runs) - set(active_ids))
    active_without_pending = sorted(set(active_ids) - set(pending_runs))
    return {
        "generated_at_utc": utc_now(),
        "matrix_dir": str(matrix_dir),
        "artifact_root": str(artifact_root) if artifact_root else "",
        "total_rows": int(len(df)),
        "counts": {
            "pass": int(counts.get("pass", 0)),
            "pending": int(counts.get("pending", 0)),
            "fail": int(counts.get("fail", 0)),
            "not_started": int(counts.get("not_started", 0)),
        },
        "active_run_ids": active_ids,
        "pending_run_ids": pending_runs,
        "failed_run_ids": failed_runs,
        "orphan_pending_run_ids": orphan_pending,
        "active_without_pending_run_ids": active_without_pending,
        "disk_free_gb": float(artifact_disk_free_gb(artifact_root)),
    }


def write_relaunch_plan(
    matrix_dir: Path,
    snapshot: dict[str, Any],
    settings: dict[str, Any],
    queue_cmd: list[str],
    existing_controllers: list[dict[str, str]],
) -> Path:
    state_dir = controller_state_dir(matrix_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    plan_path = state_dir / f"relaunch_plan_{stamp}.md"
    counts = snapshot["counts"]
    active_runs = snapshot["active_run_ids"]
    orphan_pending = snapshot["orphan_pending_run_ids"]
    lines = [
        "# Featurecov cf1 epsilon relaunch plan",
        "",
        f"- Generated: `{snapshot['generated_at_utc']}`",
        f"- Matrix dir: `{snapshot['matrix_dir']}`",
        f"- Artifact root: `{snapshot['artifact_root']}`",
        "",
        "## Snapshot",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Passed | {counts['pass']} |",
        f"| Pending | {counts['pending']} |",
        f"| Failed | {counts['fail']} |",
        f"| Not started | {counts['not_started']} |",
        f"| Active fits detected | {len(active_runs)} |",
        f"| Orphan pending rows | {len(orphan_pending)} |",
        f"| Free disk (GB) | {snapshot['disk_free_gb']:.1f} |",
        "",
        "## Guardrails",
        "",
        f"- Existing queue controllers detected: `{len(existing_controllers)}`",
        f"- Effective ordinary concurrency: `{settings['ordinary_max_concurrent']}`",
        f"- Pause threshold: `{settings['pause_free_gb']}` GB",
        f"- Launch threshold: `{settings['launch_free_gb']}` GB",
        f"- Heavy threshold: `{settings['heavy_free_gb']}` GB",
        f"- Poll seconds: `{settings['poll_seconds']}`",
        "",
        "## Active Fits",
        "",
    ]
    if active_runs:
        lines.extend([f"- `{run_id}`" for run_id in active_runs])
    else:
        lines.append("- None.")
    lines.extend(["", "## Orphan Pending Rows", ""])
    if orphan_pending:
        lines.extend([f"- `{run_id}`" for run_id in orphan_pending])
    else:
        lines.append("- None.")
    lines.extend([
        "",
        "## Relaunch Command",
        "",
        "```bash",
        " ".join(queue_cmd),
        "```",
        "",
    ])
    plan_path.write_text("\n".join(lines), encoding="utf-8")
    return plan_path


def write_launch_metadata(matrix_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = controller_state_dir(matrix_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "last_relaunch.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def wait_for_controller_registration(matrix_dir: Path, pid: int, timeout_seconds: int = 20) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        controllers = find_queue_controllers(matrix_dir)
        if any(int(row["pid"]) == pid for row in controllers):
            return True
        if not process_exists(pid):
            return False
        time.sleep(1)
    return False


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Safely relaunch the active featurecov cf1 epsilon queue controller.")
    ap.add_argument("--matrix-dir", required=True)
    ap.add_argument("--artifact-root")
    ap.add_argument("--launch-settings-env")
    ap.add_argument("--ordinary-max-concurrent", type=int)
    ap.add_argument("--safe-ordinary-cap", type=int, default=DEFAULT_SAFE_ORDINARY_MAX)
    ap.add_argument("--pause-free-gb", type=float)
    ap.add_argument("--launch-free-gb", type=float)
    ap.add_argument("--heavy-free-gb", type=float)
    ap.add_argument("--poll-seconds", type=int)
    ap.add_argument("--allow-orphan-pending", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    matrix_dir = Path(args.matrix_dir).resolve()
    launch_settings_path = (
        Path(args.launch_settings_env).resolve()
        if args.launch_settings_env
        else (matrix_dir / "launch_settings.env").resolve()
    )
    if not matrix_dir.exists():
        raise FileNotFoundError(f"Matrix dir does not exist: {matrix_dir}")
    if not launch_settings_path.exists():
        raise FileNotFoundError(f"Launch settings file does not exist: {launch_settings_path}")

    settings = read_launch_settings(launch_settings_path)
    artifact_root_value = args.artifact_root or settings.get("ARTIFACT_ROOT", "")
    artifact_root = Path(resolve_artifact_root(artifact_root_value)).resolve() if artifact_root_value else None
    effective_settings = {
        "ordinary_max_concurrent": choose_ordinary_max_concurrent(
            configured_value=int(settings.get("ORDINARY_MAX_CONCURRENT", DEFAULT_SAFE_ORDINARY_MAX)),
            requested_value=args.ordinary_max_concurrent,
            safe_cap=args.safe_ordinary_cap,
        ),
        "pause_free_gb": float(args.pause_free_gb if args.pause_free_gb is not None else settings.get("PAUSE_FREE_GB", 180.0)),
        "launch_free_gb": float(args.launch_free_gb if args.launch_free_gb is not None else settings.get("LAUNCH_FREE_GB", 220.0)),
        "heavy_free_gb": float(args.heavy_free_gb if args.heavy_free_gb is not None else settings.get("HEAVY_FREE_GB", 240.0)),
        "poll_seconds": int(args.poll_seconds if args.poll_seconds is not None else settings.get("POLL_SECONDS", 60)),
    }

    existing_controllers = find_queue_controllers(matrix_dir)
    snapshot = collect_relaunch_snapshot(matrix_dir, artifact_root)
    queue_cmd = [
        "python3",
        "scripts/run_multimodel_v8_queue.py",
        "--matrix-dir",
        str(matrix_dir),
        "--artifact-root",
        str(artifact_root),
        "--ordinary-max-concurrent",
        str(effective_settings["ordinary_max_concurrent"]),
        "--pause-free-gb",
        str(effective_settings["pause_free_gb"]),
        "--launch-free-gb",
        str(effective_settings["launch_free_gb"]),
        "--heavy-free-gb",
        str(effective_settings["heavy_free_gb"]),
        "--poll-seconds",
        str(effective_settings["poll_seconds"]),
    ]
    plan_path = write_relaunch_plan(matrix_dir, snapshot, effective_settings, queue_cmd, existing_controllers)

    if existing_controllers:
        print(f"Refusing relaunch: {len(existing_controllers)} queue controller(s) already active.", file=sys.stderr)
        print(f"plan_path={plan_path}")
        return 2
    if snapshot["counts"]["fail"] > 0:
        print("Refusing relaunch: failed rows are present in the matrix.", file=sys.stderr)
        print(f"plan_path={plan_path}")
        return 3
    if snapshot["orphan_pending_run_ids"] and not args.allow_orphan_pending:
        print("Refusing relaunch: orphan pending rows detected with no active fit process.", file=sys.stderr)
        print(f"plan_path={plan_path}")
        return 4

    state_dir = controller_state_dir(matrix_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    controller_log = state_dir / "controller_stdout.log"
    pid_path = state_dir / "controller.pid"

    launch_payload = {
        "generated_at_utc": utc_now(),
        "plan_path": str(plan_path),
        "matrix_dir": str(matrix_dir),
        "artifact_root": str(artifact_root),
        "effective_settings": effective_settings,
        "snapshot": snapshot,
        "queue_cmd": queue_cmd,
    }
    metadata_path = write_launch_metadata(matrix_dir, launch_payload)

    if args.dry_run:
        print(f"dry_run=1")
        print(f"plan_path={plan_path}")
        print(f"metadata_path={metadata_path}")
        return 0

    with controller_log.open("ab") as handle:
        proc = subprocess.Popen(
            queue_cmd,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    pid_path.write_text(f"{proc.pid}\n", encoding="utf-8")

    if not wait_for_controller_registration(matrix_dir, proc.pid):
        print("Queue relaunch did not register an active controller process.", file=sys.stderr)
        print(f"plan_path={plan_path}")
        print(f"metadata_path={metadata_path}")
        return 5

    print(f"launched_pid={proc.pid}")
    print(f"plan_path={plan_path}")
    print(f"metadata_path={metadata_path}")
    print(f"controller_log={controller_log}")
    print(f"controller_pid_file={pid_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
