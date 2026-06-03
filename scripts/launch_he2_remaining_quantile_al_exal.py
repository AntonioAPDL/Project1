#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_dqlm_multivar_al_drop_from_exal_drop import (  # noqa: E402
    DEFAULT_ARTIFACT_ROOT as AL_DROP_ROOT,
    build_package as build_al_drop_package,
)


UNIVAR_TEMPLATE = ROOT / "config" / "he2_bayesian_publication_relaunch_univar_al_exal_20260603.template.yaml"
UNIVAR_BATCH = ROOT / "config" / "he2_relaunch_batches" / "univar_al_exal_publication_relaunch_20260603.yaml"
UNIVAR_ROOT = ROOT.parent / "project1_ucsc_phd_runtime" / "multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603"
REPORT_DIR = ROOT / "reports" / "he2_remaining_quantile_al_exal_launch_20260603"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload if isinstance(payload, dict) else {}


def run_checked(cmd: list[str], *, label: str, outdir: Path) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    (outdir / f"{label}.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (outdir / f"{label}.stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed with returncode={proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def start_controller(
    *,
    label: str,
    artifact_root: Path,
    matrix_dir: Path,
    ordinary_max_concurrent: int,
    heavy_cutoff_max_concurrent: int,
    poll_seconds: int,
    dry_run: bool,
) -> dict[str, Any]:
    state_dir = matrix_dir / "controller_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    pid_file = state_dir / "controller.pid"
    stdout_path = state_dir / "controller.stdout.log"
    stderr_path = state_dir / "controller.stderr.log"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except Exception:
            pid = -1
        if pid > 0 and pid_alive(pid):
            return {
                "label": label,
                "status": "already_running",
                "pid": pid,
                "pid_file": str(pid_file),
                "matrix_dir": str(matrix_dir),
                "artifact_root": str(artifact_root),
            }
    cmd = [
        "python3",
        "scripts/run_multimodel_v8_queue.py",
        "--matrix-dir",
        str(matrix_dir),
        "--artifact-root",
        str(artifact_root),
        "--ordinary-max-concurrent",
        str(ordinary_max_concurrent),
        "--pause-free-gb",
        "25.0",
        "--launch-free-gb",
        "35.0",
        "--heavy-free-gb",
        "35.0",
        "--pause-mem-gb",
        "0.0",
        "--launch-mem-gb",
        "0.0",
        "--heavy-mem-gb",
        "0.0",
        "--heavy-cutoff-max-concurrent",
        str(heavy_cutoff_max_concurrent),
        "--poll-seconds",
        str(poll_seconds),
        "--continue-on-fail",
        "--skip-compares",
        "--no-heavy-cutoff-blocks-ordinary",
    ]
    if dry_run:
        return {
            "label": label,
            "status": "dry_run",
            "cmd": cmd,
            "matrix_dir": str(matrix_dir),
            "artifact_root": str(artifact_root),
        }
    stdout_handle = stdout_path.open("ab")
    stderr_handle = stderr_path.open("ab")
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=stdout_handle,
        stderr=stderr_handle,
        start_new_session=True,
        close_fds=True,
    )
    pid_file.write_text(str(proc.pid) + "\n", encoding="utf-8")
    return {
        "label": label,
        "status": "launched",
        "pid": proc.pid,
        "pid_file": str(pid_file),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "cmd": cmd,
        "matrix_dir": str(matrix_dir),
        "artifact_root": str(artifact_root),
    }


def build_univar(outdir: Path) -> dict[str, str]:
    cmd = [
        "python3",
        "scripts/build_he2_bayesian_publication_relaunch_configs.py",
        "--config",
        str(UNIVAR_TEMPLATE),
        "--batch-file",
        str(UNIVAR_BATCH),
        "--profile",
        "disk_guarded_parallel",
    ]
    proc = run_checked(cmd, label="build_univar_al_exal", outdir=outdir)
    parsed: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key.strip() in {"artifact_root", "matrix_dir", "config_output_dir", "generated_configs", "plan_rows"}:
                parsed[key.strip()] = value.strip()
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Build, validate, and launch remaining HE2 AL/exAL quantile publication runs.")
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    launch_summary: dict[str, Any] = {
        "timestamp_utc": utc_now(),
        "dry_run": bool(args.dry_run),
        "skip_validation": bool(args.skip_validation),
        "controllers": [],
        "builds": {},
    }

    al_drop_metadata = build_al_drop_package(AL_DROP_ROOT.resolve(), reset_status=True)
    launch_summary["builds"]["al_drop"] = al_drop_metadata
    if not args.skip_validation:
        run_checked(
            [
                "python3",
                "scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py",
                "--artifact-root",
                str(AL_DROP_ROOT),
            ],
            label="validate_al_drop_from_exal_drop",
            outdir=REPORT_DIR,
        )
    al_drop_matrix = Path(al_drop_metadata["matrix_dir"])
    launch_summary["controllers"].append(
        start_controller(
            label="AL-M-T0",
            artifact_root=AL_DROP_ROOT.resolve(),
            matrix_dir=al_drop_matrix,
            ordinary_max_concurrent=2,
            heavy_cutoff_max_concurrent=2,
            poll_seconds=args.poll_seconds,
            dry_run=args.dry_run,
        )
    )

    if args.skip_validation:
        univar_build = build_univar(REPORT_DIR)
    else:
        run_checked(
            [
                "python3",
                "scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py",
                "--config",
                str(UNIVAR_TEMPLATE),
                "--batch-file",
                str(UNIVAR_BATCH),
                "--profile",
                "disk_guarded_parallel",
                "--outdir",
                str(UNIVAR_ROOT / "control" / "prelaunch_validation_20260603"),
            ],
            label="validate_univar_al_exal",
            outdir=REPORT_DIR,
        )
        metadata = load_yaml(UNIVAR_ROOT / "control" / "publication_relaunch_matrix" / "matrix_metadata.yaml")
        univar_build = {
            "artifact_root": str(UNIVAR_ROOT),
            "matrix_dir": str(UNIVAR_ROOT / "control" / "publication_relaunch_matrix"),
            "config_output_dir": str(UNIVAR_ROOT / "control" / "generated_configs"),
            "plan_rows": str(metadata.get("request", {}).get("selection", {}).get("families", "")),
        }
    launch_summary["builds"]["univar_al_exal"] = univar_build
    univar_matrix = UNIVAR_ROOT / "control" / "publication_relaunch_matrix"
    launch_summary["controllers"].append(
        start_controller(
            label="AL-U-T1_exAL-U-T1",
            artifact_root=UNIVAR_ROOT.resolve(),
            matrix_dir=univar_matrix,
            ordinary_max_concurrent=2,
            heavy_cutoff_max_concurrent=2,
            poll_seconds=args.poll_seconds,
            dry_run=args.dry_run,
        )
    )

    (REPORT_DIR / "launch_summary.json").write_text(json.dumps(launch_summary, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# HE2 Remaining Quantile AL/exAL Launch Summary",
        "",
        f"- timestamp_utc: `{launch_summary['timestamp_utc']}`",
        f"- dry_run: `{launch_summary['dry_run']}`",
        f"- skip_validation: `{launch_summary['skip_validation']}`",
        "",
        "## Controllers",
        "",
    ]
    for item in launch_summary["controllers"]:
        lines.append(
            f"- `{item['label']}`: `{item['status']}` pid=`{item.get('pid', '')}` matrix=`{item['matrix_dir']}`"
        )
    (REPORT_DIR / "LAUNCH_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(launch_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
