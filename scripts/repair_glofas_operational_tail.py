#!/usr/bin/env python3
"""Plan or apply a targeted retry for the stuck tail of a parallel GLOFAS operational campaign."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recovery_priority_lib import (
    DEFAULT_RECOVERY_RUN_ROOT,
    PROJECT_ROOT,
    SITE_LAT,
    SITE_LON,
    find_glofas_operational_campaign_root,
    operational_latest_problem_rows,
    operational_phase_status,
    snapshot_priority_status,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage or apply a targeted GLOFAS operational tail repair.")
    parser.add_argument("--recovery-run-root", type=Path, default=None)
    parser.add_argument("--campaign-root", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--apply", action="store_true", help="Launch targeted tmux retry sessions. Default is plan-only.")
    parser.add_argument(
        "--skip-freeze-checkpoint",
        action="store_true",
        help="Do not freeze a fresh recovery checkpoint before applying the retry.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_roots(args: argparse.Namespace) -> tuple[Path | None, Path]:
    recovery_run_root = args.recovery_run_root
    campaign_root = args.campaign_root
    if recovery_run_root is None and campaign_root is None:
        recovery_run_root = DEFAULT_RECOVERY_RUN_ROOT
    if recovery_run_root is not None:
        recovery_run_root = recovery_run_root.expanduser().resolve()
    if campaign_root is None:
        if recovery_run_root is None:
            raise ValueError("campaign-root or recovery-run-root is required")
        campaign_root = find_glofas_operational_campaign_root(recovery_run_root)
    campaign_root = campaign_root.expanduser().resolve()
    return recovery_run_root, campaign_root


def group_problem_rows(problem_rows: Sequence[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in problem_rows:
        grouped[row["split_id"]].append(row)
    return dict(sorted(grouped.items()))


def write_command(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def render_readme(
    out_dir: Path,
    campaign_root: Path,
    recovery_run_root: Path | None,
    phase_status: Dict[str, object],
    problem_rows: Sequence[Dict[str, str]],
    grouped: Dict[str, List[Dict[str, str]]],
) -> str:
    lines = [
        "# GLOFAS Operational Tail Repair",
        "",
        f"- generated_utc: `{datetime.now(timezone.utc).isoformat()}`",
        f"- campaign_root: `{campaign_root}`",
        f"- recovery_run_root: `{recovery_run_root}`" if recovery_run_root is not None else "- recovery_run_root: `(not provided)`",
        "",
        "## Why This Exists",
        "",
        "- The prioritized queue is blocked at the operational download gate.",
        "- Completed operational GRIB issue dates are already durable on disk and should not be redone.",
        "- This bundle retries only the latest non-done issue dates from the split manifests.",
        "",
        "## Current Status",
        "",
        f"- completed: `{phase_status['completed']} / {phase_status['expected']}`",
        f"- touched: `{phase_status['touched']}`",
        f"- percent_complete: `{phase_status['percent_complete']:.1f}%`",
        f"- latest_problem_count: `{len(problem_rows)}`",
        "",
        "## Problem Tail",
        "",
        "| split | issue_date | latest_status | hydrological_model | note |",
        "|---|---|---|---|---|",
    ]
    for row in problem_rows:
        note = row["notes"].replace("\n", " ")
        if len(note) > 120:
            note = note[:117] + "..."
        lines.append(
            f"| `{row['split_id']}` | `{row['issue_date']}` | `{row['status']}` | `{row['hydrological_model']}` | `{note}` |"
        )
    if not problem_rows:
        lines.append("| `(none)` |  |  |  | queue tail is clear |")
    lines.extend(
        [
            "",
            "## Planned Retry Sessions",
            "",
        ]
    )
    if grouped:
        for split_id, rows in grouped.items():
            issues = ", ".join(row["issue_date"] for row in rows)
            lines.append(f"- `{split_id}` -> `{issues}`")
    else:
        lines.append("- `(none)`")
    lines.extend(
        [
            "",
            "## Commands",
            "",
            "- Freeze checkpoint: `commands/00_freeze_checkpoint.sh`",
            "- Launch all retries: `commands/15_retry_all.sh`",
            "- Refresh operational health: `commands/20_refresh_parallel_health.sh`",
            "",
            "## Expected Outcome",
            "",
            "- Successful retries append `downloaded` rows to the existing split manifests.",
            "- New non-empty GRIBs appear under the existing campaign download root.",
            "- The live prioritized queue controller should then observe `1176 / 1176` and advance to `NWM v1.2` without a full relaunch.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def tmux_has_session(name: str) -> bool:
    proc = subprocess.run(["tmux", "has-session", "-t", name], capture_output=True, check=False)
    return proc.returncode == 0


def launch_tmux(session_name: str, command_path: Path, stdout_log: Path) -> Dict[str, object]:
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    if tmux_has_session(session_name):
        return {"session_name": session_name, "launched": False, "reason": "already_exists"}
    proc = subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, f"bash \"{command_path}\" |& tee \"{stdout_log}\""],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "session_name": session_name,
        "launched": proc.returncode == 0,
        "stdout_log": str(stdout_log),
        "stderr": proc.stderr.strip(),
    }


def freeze_checkpoint(recovery_run_root: Path) -> Dict[str, object]:
    proc = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "freeze_recovery_checkpoint.py"),
            "--recovery-run-root",
            str(recovery_run_root),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def stage_bundle(
    out_dir: Path,
    recovery_run_root: Path | None,
    campaign_root: Path,
    phase_status: Dict[str, object],
    problem_rows: Sequence[Dict[str, str]],
) -> Dict[str, object]:
    grouped = group_problem_rows(problem_rows)
    plans_dir = out_dir / "plans"
    commands_dir = out_dir / "commands"
    logs_dir = out_dir / "logs"
    status_dir = out_dir / "status"
    plans_dir.mkdir(parents=True, exist_ok=True)
    commands_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    status_dir.mkdir(parents=True, exist_ok=True)

    problem_csv = plans_dir / "latest_problem_issue_dates.csv"
    with problem_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "split_id",
                "issue_date",
                "status",
                "hydrological_model",
                "path",
                "req_id",
                "timestamp_utc",
                "notes",
                "manifest_path",
            ],
        )
        writer.writeheader()
        for row in problem_rows:
            writer.writerow(row)

    retry_commands: List[Path] = []
    retry_sessions: List[str] = []
    bundle_id = out_dir.name
    for split_id, rows in grouped.items():
        intervals_path = plans_dir / f"{split_id}_retry_intervals.csv"
        issue_dates_path = plans_dir / f"{split_id}_retry_issue_dates.txt"
        with intervals_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["start", "end"])
            writer.writeheader()
            for row in rows:
                writer.writerow({"start": row["issue_date"], "end": row["issue_date"]})
        issue_dates_path.write_text("".join(f"{row['issue_date']}\n" for row in rows), encoding="utf-8")

        retry_cmd = commands_dir / f"10_retry_{split_id}.sh"
        split_manifest = campaign_root / "manifests" / f"{split_id}_download_manifest.csv"
        split_log = logs_dir / f"{split_id}_download_internal.log"
        write_command(
            retry_cmd,
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"cd {PROJECT_ROOT}",
                (
                    "python3 glofas_operational_mediumrange_download_point.py "
                    "--run "
                    f"--intervals-file {intervals_path} "
                    f"--out-root {campaign_root / 'outputs' / 'download_root'} "
                    f"--manifest-path {split_manifest} "
                    f"--log-path {split_log} "
                    f"--lat {SITE_LAT} "
                    f"--lon {SITE_LON} "
                    "--verbose"
                ),
            ],
        )
        retry_commands.append(retry_cmd)
        retry_sessions.append(f"{split_id}_{bundle_id}")

    refresh_health_cmd = commands_dir / "20_refresh_parallel_health.sh"
    write_command(
        refresh_health_cmd,
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"cd {PROJECT_ROOT}",
            (
                "python3 scripts/check_glofas_operational_parallel_health.py "
                f"--campaign-root {campaign_root} "
                f"--out-json {campaign_root / 'health_checks' / 'parallel_download_health.json'}"
            ),
        ],
    )
    if recovery_run_root is not None:
        write_command(
            commands_dir / "00_freeze_checkpoint.sh",
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"cd {PROJECT_ROOT}",
                f"python3 scripts/freeze_recovery_checkpoint.py --recovery-run-root {recovery_run_root}",
            ],
        )

    retry_all_cmd = commands_dir / "15_retry_all.sh"
    write_command(
        retry_all_cmd,
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            *[f"bash {cmd}" for cmd in retry_commands],
            f"bash {refresh_health_cmd}",
        ]
        if retry_commands
        else [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "echo 'No retry commands were generated.'",
            f"bash {refresh_health_cmd}",
        ],
    )

    plan_payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "recovery_run_root": str(recovery_run_root) if recovery_run_root is not None else None,
        "campaign_root": str(campaign_root),
        "out_dir": str(out_dir),
        "current_phase_status": phase_status,
        "latest_problem_count": len(problem_rows),
        "latest_problem_rows": list(problem_rows),
        "retry_split_count": len(grouped),
        "retry_splits": {split_id: [row["issue_date"] for row in rows] for split_id, rows in grouped.items()},
        "retry_session_names": retry_sessions,
    }
    (out_dir / "repair_plan.json").write_text(json.dumps(plan_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(
        render_readme(out_dir, campaign_root, recovery_run_root, phase_status, problem_rows, grouped),
        encoding="utf-8",
    )
    return plan_payload


def main() -> int:
    args = parse_args()
    recovery_run_root, campaign_root = resolve_roots(args)
    phase_status = operational_phase_status(campaign_root)
    problem_rows = operational_latest_problem_rows(campaign_root)
    out_dir = (
        args.out_dir.expanduser().resolve()
        if args.out_dir is not None
        else campaign_root / "status" / f"operational_tail_repair_{utc_stamp()}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_payload = stage_bundle(out_dir, recovery_run_root, campaign_root, phase_status, problem_rows)

    if not args.apply:
        print(json.dumps({"ok": True, "mode": "plan", "out_dir": str(out_dir), **plan_payload}, indent=2))
        return 0

    checkpoint_result = None
    if recovery_run_root is not None and not args.skip_freeze_checkpoint:
        checkpoint_result = freeze_checkpoint(recovery_run_root)

    launches: List[Dict[str, object]] = []
    for session_name in plan_payload["retry_session_names"]:
        split_id = session_name.split("_", 2)[0] + "_" + session_name.split("_", 2)[1]
        command_path = out_dir / "commands" / f"10_retry_{split_id}.sh"
        stdout_log = out_dir / "logs" / f"{split_id}_stdout.log"
        launches.append(launch_tmux(session_name, command_path, stdout_log))

    applied_payload = {
        "ok": True,
        "mode": "apply",
        "out_dir": str(out_dir),
        "campaign_root": str(campaign_root),
        "checkpoint_result": checkpoint_result,
        "launches": launches,
        "latest_problem_count": len(problem_rows),
    }
    (out_dir / "status" / "apply_result.json").write_text(
        json.dumps(applied_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "status" / "tmux_sessions.txt").write_text(
        "".join(f"{entry['session_name']}\n" for entry in launches if entry.get("launched") or entry.get("reason") == "already_exists"),
        encoding="utf-8",
    )
    print(json.dumps(applied_payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
