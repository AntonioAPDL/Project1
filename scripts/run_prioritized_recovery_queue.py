#!/usr/bin/env python3
"""Plan or run the prioritized recovery queue after a checkpoint freeze."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recovery_priority_lib import (
    DEFAULT_RECOVERY_RUN_ROOT,
    GLOFAS_PROJECT_FOCUS_END,
    GLOFAS_PROJECT_FOCUS_START,
    NWM_V12_EXPECTED_YEARS,
    PROJECT_ROOT,
    find_glofas_operational_campaign_root,
    find_hist_family_root,
    find_nwm_full_root,
    find_nwm_v12_run_root,
    list_target_tmux_sessions,
    nwm_v12_phase_status,
    operational_phase_status,
    snapshot_priority_status,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan or run the prioritized recovery queue.")
    parser.add_argument("--mode", choices=["plan", "status", "run"], default="plan")
    parser.add_argument("--recovery-run-root", type=Path, default=DEFAULT_RECOVERY_RUN_ROOT)
    parser.add_argument("--plan-root", type=Path, default=None)
    parser.add_argument("--v31-workers", type=int, default=8)
    parser.add_argument("--v31-passes", type=int, default=6)
    parser.add_argument("--op-splits", type=int, default=6)
    parser.add_argument("--nwm-v12-max-workers", type=int, default=8)
    parser.add_argument("--v40-workers", type=int, default=4)
    parser.add_argument("--v40-passes", type=int, default=6)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--allow-active-sessions", action="store_true")
    return parser.parse_args()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def current_status_bundle(recovery_run_root: Path) -> Dict[str, object]:
    snapshot = snapshot_priority_status(recovery_run_root)
    snapshot["generated_utc"] = datetime.now(timezone.utc).isoformat()
    snapshot["recovery_run_root"] = str(recovery_run_root)
    return snapshot


def plan_root_from_args(args: argparse.Namespace, recovery_run_root: Path) -> Path:
    if args.plan_root is not None:
        return args.plan_root.expanduser().resolve()
    return recovery_run_root / "status" / f"priority_queue_{utc_stamp()}"


def render_readme(plan_root: Path, recovery_run_root: Path, args: argparse.Namespace, snapshot: Dict[str, object]) -> str:
    lanes = snapshot["lanes"]
    return "\n".join(
        [
            "# Prioritized Recovery Queue",
            "",
            f"- generated_utc: `{snapshot['generated_utc']}`",
            f"- recovery_run_root: `{recovery_run_root}`",
            "",
            "## Priority Order",
            "",
            "1. `GLOFAS historical v3.1`",
            "2. `GLOFAS operational forecasts`",
            "3. `NWM retrospective v1.2`",
            "4. `GLOFAS historical v4.0`",
            "",
            "## Why This Order",
            "",
            "- Finish the highest-value GLOFAS historical lane first.",
            "- Then finish the GLOFAS operational archive and extraction while ECMWF context is still warm.",
            "- Then close out the remaining `NWM v1.2` yearly shards and build the final combined table.",
            "- Leave the slower `GLOFAS v4.0` lane for last.",
            "",
            "## Current Snapshot",
            "",
            "| lane | completed | expected | percent |",
            "|---|---:|---:|---:|",
            f"| `glofas_historical_v31` | {lanes['glofas_historical_v31']['completed']} | {lanes['glofas_historical_v31']['expected']} | {lanes['glofas_historical_v31']['percent_complete']:.1f}% |",
            f"| `glofas_operational` | {lanes['glofas_operational']['completed']} | {lanes['glofas_operational']['expected']} | {lanes['glofas_operational']['percent_complete']:.1f}% |",
            f"| `nwm_retrospective_v12` | {lanes['nwm_retrospective_v12']['completed']} | {lanes['nwm_retrospective_v12']['expected']} | {lanes['nwm_retrospective_v12']['percent_complete']:.1f}% |",
            f"| `glofas_historical_v40` | {lanes['glofas_historical_v40']['completed']} | {lanes['glofas_historical_v40']['expected']} | {lanes['glofas_historical_v40']['percent_complete']:.1f}% |",
            "",
            "## Recommended Concurrency",
            "",
            f"- `v31_workers={args.v31_workers}`",
            f"- `op_splits={args.op_splits}`",
            f"- `nwm_v12_max_workers={args.nwm_v12_max_workers}`",
            f"- `v40_workers={args.v40_workers}`",
            "",
            "## Commands",
            "",
            "- Freeze checkpoint: `commands/00_freeze_checkpoint.sh`",
            "- Dry-run stop preview: `commands/05_stop_preview.sh`",
            "- Apply stop: `commands/06_stop_apply.sh`",
            "- One-shot status: `commands/90_status_once.sh`",
            "- Run the sequential queue: `commands/95_run_queue.sh`",
            "",
        ]
    ) + "\n"


def write_command(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def write_plan_bundle(plan_root: Path, recovery_run_root: Path, args: argparse.Namespace) -> Dict[str, object]:
    plan_root.mkdir(parents=True, exist_ok=True)
    snapshot = current_status_bundle(recovery_run_root)
    hist_family_root = find_hist_family_root(recovery_run_root)
    op_campaign_root = find_glofas_operational_campaign_root(recovery_run_root)
    v12_run_root = find_nwm_v12_run_root(recovery_run_root)
    nwm_full_root = find_nwm_full_root(recovery_run_root)
    commands_dir = plan_root / "commands"

    plan_payload = {
        "generated_utc": snapshot["generated_utc"],
        "recovery_run_root": str(recovery_run_root),
        "priority_order": [
            "glofas_historical_v31",
            "glofas_operational",
            "nwm_retrospective_v12",
            "glofas_historical_v40",
        ],
        "settings": {
            "v31_workers": args.v31_workers,
            "v31_passes": args.v31_passes,
            "op_splits": args.op_splits,
            "nwm_v12_max_workers": args.nwm_v12_max_workers,
            "v40_workers": args.v40_workers,
            "v40_passes": args.v40_passes,
            "poll_seconds": args.poll_seconds,
        },
        "roots": {
            "hist_family_root": str(hist_family_root),
            "op_campaign_root": str(op_campaign_root),
            "v12_run_root": str(v12_run_root),
            "nwm_full_root": str(nwm_full_root),
            "plan_root": str(plan_root),
        },
        "snapshot": snapshot,
    }
    (plan_root / "priority_plan.json").write_text(json.dumps(plan_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (plan_root / "README.md").write_text(render_readme(plan_root, recovery_run_root, args, snapshot), encoding="utf-8")

    write_command(
        commands_dir / "00_freeze_checkpoint.sh",
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"cd {PROJECT_ROOT}",
            f"python3 scripts/freeze_recovery_checkpoint.py --recovery-run-root {recovery_run_root}",
        ],
    )
    write_command(
        commands_dir / "05_stop_preview.sh",
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"cd {PROJECT_ROOT}",
            f"python3 scripts/stop_recovery_priority_lanes.py --recovery-run-root {recovery_run_root}",
        ],
    )
    write_command(
        commands_dir / "06_stop_apply.sh",
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"cd {PROJECT_ROOT}",
            f"python3 scripts/stop_recovery_priority_lanes.py --recovery-run-root {recovery_run_root} --apply",
        ],
    )
    write_command(
        commands_dir / "90_status_once.sh",
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"cd {PROJECT_ROOT}",
            f"python3 scripts/run_prioritized_recovery_queue.py --mode status --recovery-run-root {recovery_run_root} --plan-root {plan_root}",
        ],
    )
    write_command(
        commands_dir / "95_run_queue.sh",
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f"cd {PROJECT_ROOT}",
            (
                "python3 scripts/run_prioritized_recovery_queue.py --mode run "
                f"--recovery-run-root {recovery_run_root} --plan-root {plan_root} "
                f"--v31-workers {args.v31_workers} --v31-passes {args.v31_passes} "
                f"--op-splits {args.op_splits} --nwm-v12-max-workers {args.nwm_v12_max_workers} "
                f"--v40-workers {args.v40_workers} --v40-passes {args.v40_passes} "
                f"--poll-seconds {args.poll_seconds}"
            ),
        ],
    )
    return plan_payload


def queue_status_path(plan_root: Path) -> Path:
    return plan_root / "status" / "queue_status.json"


def write_queue_status(plan_root: Path, payload: Dict[str, object]) -> None:
    path = queue_status_path(plan_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_checked(cmd: List[str], log_path: Path | None = None) -> None:
    if log_path is None:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def wait_for_condition(plan_root: Path, label: str, poll_seconds: int, condition_fn, status_fn) -> Dict[str, object]:
    while True:
        snapshot = status_fn()
        write_queue_status(
            plan_root,
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "current_phase": label,
                "snapshot": snapshot,
            },
        )
        if condition_fn(snapshot):
            return snapshot
        print(f"[WAIT] phase={label} snapshot={json.dumps(snapshot, sort_keys=True)}")
        time.sleep(max(1, poll_seconds))


def run_mode(args: argparse.Namespace, recovery_run_root: Path, plan_root: Path) -> int:
    if list_target_tmux_sessions() and not args.allow_active_sessions:
        raise SystemExit(
            "Active target sessions are still running. Freeze a checkpoint, stop them, "
            "or rerun with --allow-active-sessions if that is really what you want."
        )

    write_plan_bundle(plan_root, recovery_run_root, args)
    op_campaign_root = find_glofas_operational_campaign_root(recovery_run_root)
    hist_family_root = find_hist_family_root(recovery_run_root)
    v12_run_root = find_nwm_v12_run_root(recovery_run_root)
    nwm_full_root = find_nwm_full_root(recovery_run_root)
    op_launch_id = op_campaign_root.name
    v12_run_id = v12_run_root.name

    # Phase 1: GLOFAS historical v3.1
    v31_status = current_status_bundle(recovery_run_root)["lanes"]["glofas_historical_v31"]
    if v31_status["completed"] < v31_status["expected"]:
        run_checked(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "ensure_glofas_historical_product_ready.py"),
                "--recovery-family-root",
                str(hist_family_root),
                "--product-id",
                "hist_v31_lisflood_cons",
                "--focus-start",
                GLOFAS_PROJECT_FOCUS_START.isoformat(),
                "--focus-end",
                GLOFAS_PROJECT_FOCUS_END.isoformat(),
                "--workers",
                str(args.v31_workers),
                "--passes",
                str(args.v31_passes),
            ],
            log_path=plan_root / "logs" / "phase_10_glofas_v31.log",
        )

    # Phase 2: GLOFAS operational download + extraction
    op_status = operational_phase_status(op_campaign_root)
    if op_status["completed"] < op_status["expected"]:
        run_checked(
            [
                "bash",
                str(PROJECT_ROOT / "scripts" / "launch_glofas_operational_parallel.sh"),
                str(recovery_run_root),
                op_launch_id,
                str(args.op_splits),
            ],
            log_path=plan_root / "logs" / "phase_20_glofas_operational_launch.log",
        )
        wait_for_condition(
            plan_root,
            "glofas_operational_download",
            args.poll_seconds,
            condition_fn=lambda snap: snap["completed"] >= snap["expected"],
            status_fn=lambda: operational_phase_status(op_campaign_root),
        )

    run_checked(
        ["bash", str(op_campaign_root / "commands" / "run_extract_all.sh")],
        log_path=plan_root / "logs" / "phase_21_glofas_operational_extract.log",
    )
    run_checked(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "check_glofas_operational_parallel_extract_health.py"),
            "--campaign-root",
            str(op_campaign_root),
            "--out-json",
            str(op_campaign_root / "health_checks" / "parallel_extract_health.json"),
        ],
        log_path=plan_root / "logs" / "phase_22_glofas_operational_extract_health.log",
    )

    # Phase 3: NWM v1.2 resume + combine + audit
    v12_status = nwm_v12_phase_status(v12_run_root)
    if v12_status["completed"] < v12_status["expected"]:
        remaining = max(1, v12_status["expected"] - v12_status["completed"])
        workers = min(args.nwm_v12_max_workers, remaining)
        run_checked(
            [
                "bash",
                str(PROJECT_ROOT / "scripts" / "run_nwm_v12_full_point_extraction.sh"),
                v12_run_id,
                str(workers),
                "log1p_cms",
                str(nwm_full_root),
            ],
            log_path=plan_root / "logs" / "phase_30_nwm_v12_launch.log",
        )
        wait_for_condition(
            plan_root,
            "nwm_retrospective_v12",
            args.poll_seconds,
            condition_fn=lambda snap: snap["completed"] >= snap["expected"],
            status_fn=lambda: nwm_v12_phase_status(v12_run_root),
        )

    run_checked(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "nwm_retrospective_concat_yearly_shards.py"),
            "--input-dir",
            str(v12_run_root / "point_series" / "v12_yearly"),
            "--out-csv",
            str(v12_run_root / "point_series" / "v12_full_daily.csv"),
            "--out-meta",
            str(v12_run_root / "logs" / "v12_full_daily.meta.json"),
            "--version",
            "1.2",
            "--expected-start",
            "1993-01-01",
            "--expected-end",
            "2017-12-31",
        ],
        log_path=plan_root / "logs" / "phase_31_nwm_v12_concat.log",
    )
    run_checked(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "nwm_retrospective_audit_point_series.py"),
            "--inputs",
            str(v12_run_root / "point_series" / "v12_full_daily.csv"),
            "--labels",
            "v12_full",
            "--expected-start",
            "1993-01-01",
            "--expected-end",
            "2017-12-31",
            "--out-summary-csv",
            str(v12_run_root / "audits" / "v12_full_audit_summary.csv"),
            "--out-missing-dir",
            str(v12_run_root / "audits" / "v12_full_missing"),
            "--out-summary-json",
            str(v12_run_root / "audits" / "v12_full_audit_summary.json"),
        ],
        log_path=plan_root / "logs" / "phase_32_nwm_v12_audit.log",
    )

    # Phase 4: GLOFAS historical v4.0
    v40_status = current_status_bundle(recovery_run_root)["lanes"]["glofas_historical_v40"]
    if v40_status["completed"] < v40_status["expected"]:
        run_checked(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "ensure_glofas_historical_product_ready.py"),
                "--recovery-family-root",
                str(hist_family_root),
                "--product-id",
                "hist_v40_lisflood_cons",
                "--focus-start",
                GLOFAS_PROJECT_FOCUS_START.isoformat(),
                "--focus-end",
                GLOFAS_PROJECT_FOCUS_END.isoformat(),
                "--workers",
                str(args.v40_workers),
                "--passes",
                str(args.v40_passes),
            ],
            log_path=plan_root / "logs" / "phase_40_glofas_v40.log",
        )

    write_queue_status(
        plan_root,
        {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "current_phase": "complete",
            "snapshot": current_status_bundle(recovery_run_root),
        },
    )
    return 0


def main() -> int:
    args = parse_args()
    recovery_run_root = args.recovery_run_root.expanduser().resolve()
    plan_root = plan_root_from_args(args, recovery_run_root)

    if args.mode == "status":
        payload = current_status_bundle(recovery_run_root)
        if args.plan_root:
            write_queue_status(plan_root, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.mode == "plan":
        payload = write_plan_bundle(plan_root, recovery_run_root, args)
        print(json.dumps({"ok": True, "plan_root": str(plan_root), "priority_plan": str(plan_root / "priority_plan.json")}, indent=2))
        return 0

    return run_mode(args, recovery_run_root, plan_root)


if __name__ == "__main__":
    raise SystemExit(main())
