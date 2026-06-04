#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = (
    ROOT.parent
    / "project1_ucsc_phd_runtime"
    / "multimodel_v8_he2_dqlm_multivar_al_drop_diagnostics_highdf_eps365_cf1_representative_20260603"
)
EXPECTED_SPEC_ID = "highdf_eps365_cf1_al_m_t0_20260603"
EXPECTED_EXPERIMENT_SCOPE = "a0"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no launch rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_manifest_status(run_root: Path, run_id: str) -> str:
    manifest_path = run_root / "runs" / run_id / "run_manifest.yaml"
    if not manifest_path.exists():
        return "not_started"
    try:
        manifest = load_yaml(manifest_path)
    except Exception:
        return "manifest_unreadable"
    stages = manifest.get("stages", {}) if isinstance(manifest, dict) else {}
    for stage in ["forecats", "data_prep_shared", "fit", "post", "validate", "report"]:
        entry = stages.get(stage, {}) if isinstance(stages, dict) else {}
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "") or "").strip().lower()
        if status in {"pending", "fail"}:
            return f"{stage}_{status}"
    report = stages.get("report", {}) if isinstance(stages, dict) else {}
    report_status = str(report.get("status", "") or "").strip().lower() if isinstance(report, dict) else ""
    return "report_pass" if report_status == "pass" else (report_status or "unknown")


def active_config_processes() -> dict[str, dict[str, str]]:
    proc = subprocess.run(["ps", "-eo", "pid=,command="], text=True, capture_output=True, check=True)
    active: dict[str, dict[str, str]] = {}
    for line in proc.stdout.splitlines():
        if "scripts/unified_run.R" not in line or "--config" not in line:
            continue
        match = re.match(r"^\s*(\d+)\s+(.*)$", line)
        if not match:
            continue
        pid, command = match.groups()
        cfg_match = re.search(r"--config\s+(\S+\.ya?ml)", command)
        if not cfg_match:
            continue
        try:
            config_path = str(Path(cfg_match.group(1)).resolve())
        except Exception:
            config_path = cfg_match.group(1)
        active[config_path] = {"pid": pid, "command": command}
    return active


def validate_matrix(
    matrix_dir: Path,
    expected_spec_id: str,
    expected_experiment_scope: str,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    metadata_path = matrix_dir / "diagnostic_matrix_metadata.yaml"
    guard_path = matrix_dir / "NO_LAUNCH_GUARD.txt"
    matrix_plan_path = matrix_dir / "matrix_plan.csv"
    diagnostic_plan_path = matrix_dir / "diagnostic_matrix_plan.csv"
    if not metadata_path.exists():
        raise FileNotFoundError(f"missing diagnostic metadata: {metadata_path}")
    if not guard_path.exists():
        raise FileNotFoundError(f"missing no-launch guard: {guard_path}")
    if not matrix_plan_path.exists():
        raise FileNotFoundError(f"missing queue-compatible matrix_plan.csv: {matrix_plan_path}")
    if not diagnostic_plan_path.exists():
        raise FileNotFoundError(f"missing diagnostic matrix: {diagnostic_plan_path}")
    metadata = load_yaml(metadata_path)
    if metadata.get("lane_scope") != "representative":
        raise ValueError(f"launcher is scoped to representative diagnostics, found lane_scope={metadata.get('lane_scope')}")
    if metadata.get("requires_user_discount_decision") is not False:
        raise ValueError("diagnostic spec still requires a user discount decision")
    spec_id = (metadata.get("discount_spec") or {}).get("spec_id")
    if spec_id != expected_spec_id:
        raise ValueError(f"unexpected spec_id={spec_id}; expected {expected_spec_id}")
    experiment_scope = metadata.get("experiment_scope", "a0")
    if experiment_scope != expected_experiment_scope:
        raise ValueError(
            f"unexpected experiment_scope={experiment_scope}; expected {expected_experiment_scope}"
        )
    rows = read_csv(matrix_plan_path)
    expected_rows = 20 if expected_experiment_scope == "ladder" else 4
    if len(rows) != expected_rows:
        raise ValueError(
            f"representative diagnostic launch expects {expected_rows} rows for {expected_experiment_scope}, "
            f"found {len(rows)}"
        )
    for row in rows:
        if row.get("spec_id") != expected_spec_id:
            raise ValueError(f"unexpected row spec: {row}")
        if row.get("experiment_id", "") == "":
            raise ValueError(f"missing experiment_id: {row}")
        if row.get("run_scope") != "diagnostic_single_quantile_fit_only":
            raise ValueError(f"unexpected run_scope: {row}")
        config_path = Path(row["config_path"])
        if not config_path.exists():
            raise FileNotFoundError(f"missing config: {config_path}")
    return metadata, rows


def launch_row(row: dict[str, str], matrix_dir: Path) -> int:
    log_path = matrix_dir / "run_logs" / f"{row['run_id']}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as handle:
        proc = subprocess.Popen(
            ["bash", "scripts/run_unified_without_cleanup.sh", "--config", row["config_path"]],
            cwd=ROOT,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return int(proc.pid)


def write_launch_readme(matrix_dir: Path, launch_rows: list[dict[str, Any]], dry_run: bool) -> None:
    launched = [row for row in launch_rows if row["launch_action"] == "launched"]
    skipped = [row for row in launch_rows if row["launch_action"] != "launched"]
    lines = [
        "# AL-M-T0 Representative Diagnostic Launch",
        "",
        f"- generated_at_utc: `{utc_now()}`",
        f"- dry_run: `{dry_run}`",
        f"- launched: `{len(launched)}`",
        f"- skipped_or_dry_run: `{len(skipped)}`",
        "- cleanup: `disabled` via `scripts/run_unified_without_cleanup.sh`",
        "",
        "## Rows",
        "",
    ]
    for row in launch_rows:
        lines.append(
            f"- `{row['run_id']}`: action={row['launch_action']}, pid={row['pid']}, "
            f"cutoff={row['cutoff']}, lane={row['lane']}, prior_status={row['prior_status']}"
        )
    (matrix_dir / "LAUNCHED_REPRESENTATIVE_DIAGNOSTICS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the 4 guarded AL-M-T0 representative diagnostics.")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--matrix-dir", type=Path)
    parser.add_argument("--expected-spec-id", default=EXPECTED_SPEC_ID)
    parser.add_argument(
        "--expected-experiment-scope",
        choices=["a0", "a1", "a2", "a3", "a4", "ladder"],
        default=EXPECTED_EXPERIMENT_SCOPE,
    )
    parser.add_argument("--max-concurrent", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-relaunch-failed", action="store_true")
    parser.add_argument("--confirm-launch", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_root = args.artifact_root.resolve()
    matrix_dir = args.matrix_dir.resolve() if args.matrix_dir else artifact_root / "control" / "diagnostic_matrix"
    if args.max_concurrent < 1:
        raise ValueError("--max-concurrent must be positive")
    if not args.dry_run and not args.confirm_launch:
        raise ValueError("real launches require --confirm-launch")
    metadata, rows = validate_matrix(matrix_dir, args.expected_spec_id, args.expected_experiment_scope)
    active = active_config_processes()
    launch_rows: list[dict[str, Any]] = []
    launched_count = 0
    for row in rows:
        config_key = str(Path(row["config_path"]).resolve())
        prior_status = run_manifest_status(artifact_root, row["run_id"])
        active_info = active.get(config_key)
        action = "pending"
        pid = ""
        if active_info:
            action = "already_active"
            pid = active_info["pid"]
        elif prior_status.endswith("_pending"):
            action = "manifest_pending"
        elif prior_status.endswith("_fail") and not args.force_relaunch_failed:
            action = "manifest_failed_skip"
        elif prior_status in {"report_pass", "fit_pass"} or prior_status.endswith("_pass"):
            action = "already_terminal"
        elif launched_count >= args.max_concurrent:
            action = "max_concurrent_not_launched"
        elif args.dry_run:
            action = "dry_run"
        else:
            pid = str(launch_row(row, matrix_dir))
            action = "launched"
            launched_count += 1
        launch_rows.append(
            {
                "launched_at_utc": utc_now(),
                "run_id": row["run_id"],
                "cutoff": row["cutoff"],
                "lane": row["lane"],
                "config_path": row["config_path"],
                "spec_id": row["spec_id"],
                "experiment_id": row.get("experiment_id", ""),
                "transfer_feature_mode": row.get("transfer_feature_mode", ""),
                "transfer_feature_scaling": row.get("transfer_feature_scaling", ""),
                "prior_status": prior_status,
                "launch_action": action,
                "pid": pid,
                "log_path": str(matrix_dir / "run_logs" / f"{row['run_id']}.log"),
                "artifact_root": str(artifact_root),
            }
        )
    write_csv(matrix_dir / "diagnostic_launch_manifest.csv", launch_rows)
    launch_metadata = {
        "generated_at_utc": utc_now(),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "expected_spec_id": args.expected_spec_id,
        "expected_experiment_scope": args.expected_experiment_scope,
        "source_experiment_scope": metadata.get("experiment_scope", "a0"),
        "source_metadata_generated_at_utc": metadata.get("generated_at_utc", ""),
        "dry_run": bool(args.dry_run),
        "confirm_launch": bool(args.confirm_launch),
        "max_concurrent": int(args.max_concurrent),
        "launched": sum(1 for row in launch_rows if row["launch_action"] == "launched"),
        "rows": len(launch_rows),
        "cleanup_rdata_after_post": False,
    }
    (matrix_dir / "diagnostic_launch_metadata.json").write_text(json.dumps(launch_metadata, indent=2) + "\n", encoding="utf-8")
    write_launch_readme(matrix_dir, launch_rows, args.dry_run)
    print(json.dumps(launch_metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
