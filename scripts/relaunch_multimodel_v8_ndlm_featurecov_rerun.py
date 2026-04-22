#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "config" / "multimodel_v8_ndlm_featurecov_rerun_postfix_20260421.template.yaml"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def read_launch_settings(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        settings[key.strip()] = value.strip()
    return settings


def find_queue_controllers(matrix_dir: Path) -> list[dict[str, str]]:
    proc = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True, text=True, check=True)
    matrix_key = str(matrix_dir)
    matches: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or "scripts/run_multimodel_v8_queue.py" not in line or matrix_key not in line:
            continue
        m = re.match(r"^(\d+)\s+(.*)$", line)
        if not m:
            continue
        matches.append({"pid": m.group(1), "command": m.group(2)})
    return matches


def current_run_processes(run_id_prefix: str) -> list[dict[str, str]]:
    proc = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True, text=True, check=True)
    rows: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or run_id_prefix not in line:
            continue
        m = re.match(r"^(\d+)\s+(.*)$", line)
        if not m:
            continue
        rows.append({"pid": m.group(1), "command": m.group(2)})
    return rows


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def signal_and_wait(pids: list[int], sig: signal.Signals, timeout_seconds: int) -> list[int]:
    remaining = []
    for pid in pids:
        try:
            os.kill(pid, sig)
            remaining.append(pid)
        except ProcessLookupError:
            continue
    deadline = time.time() + timeout_seconds
    while remaining and time.time() < deadline:
        remaining = [pid for pid in remaining if process_exists(pid)]
        if remaining:
            time.sleep(1)
    return remaining


def archive_tree(src: Path, archive_dst: Path) -> None:
    if src.exists():
        archive_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(archive_dst))


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Stop, archive, rebuild, validate, and relaunch the NDLM featurecov rerun campaign."
    )
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    template_path = Path(args.template).resolve()
    template = load_yaml(template_path)
    campaign = template.get("campaign", {})
    matrix_dir = Path(campaign["matrix_dir"]).resolve()
    artifact_root = Path(campaign["artifact_root"]).resolve()
    config_output_dir = (ROOT / campaign["config_output_dir"]).resolve()
    run_id_prefix = f"_v8_{campaign['spec_id']}_"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_root = artifact_root / "relaunch_archive" / stamp

    status_snapshot: dict[str, Any] = {}
    status_path = matrix_dir / "matrix_status.csv"
    if status_path.exists():
        df = pd.read_csv(status_path)
        status_snapshot = {
            "counts": df["status"].value_counts().to_dict(),
            "pending_run_ids": sorted(df.loc[df["status"] == "pending", "run_id"].astype(str).tolist()),
            "passed_run_ids": sorted(df.loc[df["status"] == "pass", "run_id"].astype(str).tolist()),
        }

    controllers = find_queue_controllers(matrix_dir)
    run_processes = current_run_processes(run_id_prefix)

    plan_lines = [
        "# NDLM Featurecov Postfix Relaunch Plan",
        "",
        f"- generated_at_utc: `{utc_now()}`",
        f"- template: `{template_path}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- config_output_dir: `{config_output_dir}`",
        f"- archive_root: `{archive_root}`",
        "",
        "## Live State Before Relaunch",
        "",
        f"- queue controllers: `{len(controllers)}`",
        f"- run processes matching postfix campaign: `{len(run_processes)}`",
    ]
    if status_snapshot:
        counts = status_snapshot["counts"]
        plan_lines.extend(
            [
                f"- passed rows: `{counts.get('pass', 0)}`",
                f"- pending rows: `{counts.get('pending', 0)}`",
                f"- not_started rows: `{counts.get('not_started', 0)}`",
                f"- failed rows: `{counts.get('fail', 0)}`",
            ]
        )
    plan_lines.extend(
        [
            "",
            "## Requested Relaunch Contract",
            "",
            "- one core per model row",
            "- fifteen campaign rows allowed concurrently",
            "- no heavy-cutoff serialization for this NDLM postfix campaign",
            "- current partial campaign will be archived before rebuilding",
        ]
    )
    write_markdown(archive_root / "relaunch_plan.md", plan_lines)

    if args.dry_run:
        print(json.dumps({
            "template": str(template_path),
            "artifact_root": str(artifact_root),
            "matrix_dir": str(matrix_dir),
            "config_output_dir": str(config_output_dir),
            "archive_root": str(archive_root),
            "controllers": controllers,
            "run_processes": run_processes,
            "status_snapshot": status_snapshot,
        }, indent=2))
        return 0

    controller_pids = [int(row["pid"]) for row in controllers]
    still_running = signal_and_wait(controller_pids, signal.SIGTERM, timeout_seconds=20)
    if still_running:
        still_running = signal_and_wait(still_running, signal.SIGKILL, timeout_seconds=10)
    if still_running:
        raise RuntimeError(f"Could not stop queue controller pids={still_running}")

    run_pids = sorted({int(row["pid"]) for row in run_processes})
    still_running = signal_and_wait(run_pids, signal.SIGTERM, timeout_seconds=30)
    if still_running:
        still_running = signal_and_wait(still_running, signal.SIGKILL, timeout_seconds=10)
    if still_running:
        raise RuntimeError(f"Could not stop campaign run pids={still_running}")

    if config_output_dir.exists():
        shutil.copytree(config_output_dir, archive_root / "generated_configs", dirs_exist_ok=True)

    archive_tree(artifact_root / "runs", archive_root / "runs")
    archive_tree(artifact_root / "reports", archive_root / "reports")
    archive_tree(artifact_root / "control", archive_root / "control")
    if config_output_dir.exists():
        shutil.rmtree(config_output_dir)

    subprocess.run(
        [
            "python3",
            "scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py",
            "--config",
            str(template_path),
        ],
        cwd=ROOT,
        check=True,
    )

    if not args.skip_validate:
        subprocess.run(
            [
                "python3",
                "scripts/validate_ndlm_featurecov_rerun_prelaunch.py",
                "--config",
                str(template_path),
            ],
            cwd=ROOT,
            check=True,
        )

    launch_cmd = [
        "python3",
        "scripts/launch_multimodel_v8_ndlm_featurecov_rerun.py",
        "--template",
        str(template_path),
    ]
    if args.skip_validate:
        launch_cmd.append("--skip-validate")

    launch_proc = subprocess.run(
        launch_cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    new_pid = int(launch_proc.stdout.strip().splitlines()[-1])

    relaunch_summary = {
        "generated_at_utc": utc_now(),
        "template": str(template_path),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "archive_root": str(archive_root),
        "stopped_controller_pids": controller_pids,
        "stopped_run_pids": run_pids,
        "new_controller_pid": new_pid,
    }
    (matrix_dir / "controller_state").mkdir(parents=True, exist_ok=True)
    (matrix_dir / "controller_state" / "last_relaunch.json").write_text(
        json.dumps(relaunch_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_markdown(
        matrix_dir / "controller_state" / f"relaunch_plan_{stamp}.md",
        plan_lines + ["", "## Relaunch Result", "", f"- new_controller_pid: `{new_pid}`"],
    )

    print(new_pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
