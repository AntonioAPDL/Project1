#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def status_fieldnames(existing_rows: list[dict[str, str]]) -> list[str]:
    preferred = [
        "cutoff",
        "lane",
        "run_id",
        "phase",
        "status",
        "started_at",
        "finished_at",
        "returncode",
        "config_path",
        "run_root",
        "log_path",
        "note",
    ]
    extras: list[str] = []
    for row in existing_rows:
        for key in row:
            if key not in preferred and key not in extras:
                extras.append(key)
    return preferred + extras


def update_status(status_path: Path, run_id: str, **updates: Any) -> None:
    rows = read_csv_rows(status_path) if status_path.exists() else []
    fieldnames = status_fieldnames(rows)
    found = False
    for row in rows:
        if row.get("run_id") == run_id:
            row.update({key: str(value) for key, value in updates.items()})
            found = True
            break
    if not found:
        row = {"run_id": run_id, **{key: str(value) for key, value in updates.items()}}
        rows.append(row)
    for key in updates:
        if key not in fieldnames:
            fieldnames.append(key)
    write_csv_rows(status_path, rows, fieldnames)


def refresh_monitor(artifact_root: Path, matrix_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "python3",
            "scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py",
            "--artifact-root",
            str(artifact_root),
            "--matrix-dir",
            str(matrix_dir),
            "--out-dir",
            str(out_dir),
            "--once",
        ],
        cwd=ROOT,
        check=False,
    )


def launch_row(row: dict[str, str], log_dir: Path, cleanup_rdata_after_post: bool, dry_run: bool) -> tuple[subprocess.Popen[str], Any]:
    run_id = row["run_id"]
    config_path = Path(row["config_path"])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_id}.log"
    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "CLEANUP_RDATA_AFTER_POST": "1" if cleanup_rdata_after_post else "0",
    })
    cmd = ["Rscript", "--vanilla", "scripts/unified_run.R", "--config", str(config_path)]
    if dry_run:
        cmd.append("--dry-run")
    handle = log_path.open("w", encoding="utf-8")
    handle.write(f"[matrix_runner] started_at_utc={utc_now()} cwd={ROOT}\n")
    handle.write(f"[matrix_runner] command={' '.join(cmd)}\n")
    handle.write(f"[matrix_runner] cleanup_rdata_after_post={env['CLEANUP_RDATA_AFTER_POST']}\n")
    handle.flush()
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc, handle


def run_matrix(args: argparse.Namespace) -> int:
    matrix_dir = Path(args.matrix_dir).resolve()
    artifact_root = Path(args.artifact_root).resolve()
    report_dir = Path(args.report_dir).resolve()
    plan_path = matrix_dir / "matrix_plan.csv"
    status_path = matrix_dir / "matrix_status.csv"
    rows = read_csv_rows(plan_path)
    if args.only_run_id:
        selected = set(args.only_run_id)
        rows = [row for row in rows if row.get("run_id") in selected]
    if not rows:
        raise ValueError(f"No matrix rows selected from {plan_path}")

    log_dir = report_dir / ("dry_run_logs" if args.dry_run else "run_logs")
    monitor_dir = report_dir / ("dry_run_monitor" if args.dry_run else "monitor")
    pending = list(rows)
    running: dict[str, tuple[subprocess.Popen[str], Any, dict[str, str]]] = {}
    completed: list[int] = []
    last_monitor = 0.0

    while pending or running:
        while pending and len(running) < args.workers:
            row = pending.pop(0)
            run_id = row["run_id"]
            log_path = log_dir / f"{run_id}.log"
            update_status(
                status_path,
                run_id,
                phase="dry_run" if args.dry_run else "running",
                status="running",
                started_at=utc_now(),
                finished_at="",
                returncode="",
                log_path=str(log_path),
                config_path=row.get("config_path", ""),
                run_root=row.get("run_root", ""),
                note=row.get("role", ""),
            )
            proc, handle = launch_row(row, log_dir, args.cleanup_rdata_after_post, args.dry_run)
            running[run_id] = (proc, handle, row)

        now = time.monotonic()
        if args.monitor_interval_seconds >= 0 and (now - last_monitor >= args.monitor_interval_seconds):
            refresh_monitor(artifact_root, matrix_dir, monitor_dir)
            last_monitor = now

        for run_id, (proc, handle, row) in list(running.items()):
            returncode = proc.poll()
            if returncode is None:
                continue
            handle.write(f"\n[matrix_runner] finished_at_utc={utc_now()} returncode={returncode}\n")
            handle.close()
            status = "pass" if returncode == 0 else "fail"
            update_status(
                status_path,
                run_id,
                phase="dry_run_complete" if args.dry_run else "complete",
                status=status,
                finished_at=utc_now(),
                returncode=returncode,
                log_path=str(log_dir / f"{run_id}.log"),
                config_path=row.get("config_path", ""),
                run_root=row.get("run_root", ""),
            )
            completed.append(returncode)
            del running[run_id]

        if running:
            time.sleep(args.poll_seconds)

    refresh_monitor(artifact_root, matrix_dir, monitor_dir)
    if completed and all(code == 0 for code in completed):
        return 0
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a prepared exDQLM near-zero gamma/sigma matrix.")
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    parser.add_argument("--monitor-interval-seconds", type=float, default=60.0)
    parser.add_argument("--cleanup-rdata-after-post", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-run-id", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")
    return run_matrix(args)


if __name__ == "__main__":
    raise SystemExit(main())
