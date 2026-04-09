#!/usr/bin/env python3
"""Stop the current recovery priority lanes after a checkpoint has been frozen."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recovery_priority_lib import (
    DEFAULT_RECOVERY_RUN_ROOT,
    list_target_tmux_sessions,
    list_v31_histfix_refill_pids,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stop the active recovery lanes targeted for rerouting.")
    parser.add_argument("--recovery-run-root", type=Path, default=DEFAULT_RECOVERY_RUN_ROOT)
    parser.add_argument("--apply", action="store_true", help="Actually stop sessions/processes. Default is dry-run.")
    parser.add_argument("--grace-seconds", type=int, default=2)
    return parser.parse_args()


def tmux_has_session(name: str) -> bool:
    proc = subprocess.run(["tmux", "has-session", "-t", name], capture_output=True, check=False)
    return proc.returncode == 0


def stop_tmux_session(name: str, grace_seconds: int) -> None:
    if not tmux_has_session(name):
        return
    subprocess.run(["tmux", "send-keys", "-t", name, "C-c"], check=False)
    time.sleep(max(0, grace_seconds))
    if tmux_has_session(name):
        subprocess.run(["tmux", "kill-session", "-t", name], check=False)


def stop_pid(pid: int) -> None:
    subprocess.run(["kill", str(pid)], check=False)


def main() -> int:
    args = parse_args()
    sessions = list_target_tmux_sessions()
    refill_pids = list_v31_histfix_refill_pids()
    payload = {
        "apply": bool(args.apply),
        "tmux_sessions": sessions,
        "v31_refill_pids": refill_pids,
        "notes": [
            "Dry-run is the default.",
            "This stop script only targets the recovery lanes being rerouted.",
            "Run freeze_recovery_checkpoint.py immediately before --apply.",
        ],
    }
    if not args.apply:
        print(json.dumps(payload, indent=2))
        return 0

    for session in sessions:
        stop_tmux_session(session, args.grace_seconds)
    for pid in refill_pids:
        stop_pid(pid)

    print(json.dumps({"ok": True, "stopped_tmux_sessions": sessions, "stopped_v31_refill_pids": refill_pids}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
