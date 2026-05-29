#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "exdqlm_keep_latent_diag_20260529_prepared"
)
DEFAULT_MATRIX_PLAN = DEFAULT_ARTIFACT_ROOT / "control" / "latent_diag_matrix" / "latent_diag_matrix_plan.csv"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "he2_exdqlm_multivar_keep_latent_diag_overnight_20260529"
PHASE_PARALLEL_DEFAULTS = {"A": 2, "B": 4, "C": 2}


def utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def local_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run the staged exDQLM multivar keep latent diagnostic ladder."
    )
    ap.add_argument("--matrix-plan", default=str(DEFAULT_MATRIX_PLAN))
    ap.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    ap.add_argument("--report-root", default=str(DEFAULT_REPORT_ROOT))
    ap.add_argument("--phases", default="A,B,C", help="Comma-separated phases to run in order.")
    ap.add_argument("--poll-seconds", type=int, default=60)
    ap.add_argument("--phase-parallel", action="append", default=[], help="Override as PHASE=N, e.g. A=2.")
    ap.add_argument("--resume", action="store_true", help="Skip rows with existing terminal status in phase_status.csv.")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def phase_parallel(args: argparse.Namespace) -> dict[str, int]:
    out = dict(PHASE_PARALLEL_DEFAULTS)
    for item in args.phase_parallel:
        if "=" not in item:
            raise ValueError(f"--phase-parallel must be PHASE=N, got {item!r}")
        phase, raw_n = item.split("=", 1)
        phase = phase.strip()
        n = int(raw_n)
        if n < 1:
            raise ValueError(f"parallel count must be >=1 for phase {phase}")
        out[phase] = n
    return out


def ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def status_path(control_dir: Path) -> Path:
    return control_dir / "phase_status.csv"


def load_existing_status(control_dir: Path) -> dict[str, dict[str, Any]]:
    path = status_path(control_dir)
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    out: dict[str, dict[str, Any]] = {}
    for row in df.to_dict(orient="records"):
        out[str(row["run_id"])] = row
    return out


def append_status(control_dir: Path, row: dict[str, Any]) -> None:
    path = status_path(control_dir)
    exists = path.exists()
    fields = [
        "timestamp",
        "phase",
        "cutoff",
        "grid_spec_id",
        "q_label",
        "run_id",
        "status",
        "pid",
        "returncode",
        "started_at",
        "finished_at",
        "config_path",
        "log_path",
        "run_root",
        "message",
    ]
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fields})


def latest_status_frame(control_dir: Path) -> pd.DataFrame:
    path = status_path(control_dir)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=str).fillna("")
    if df.empty:
        return df
    return df.groupby("run_id", as_index=False, sort=False).tail(1)


def write_live_status(control_dir: Path, report_root: Path, message: str) -> None:
    latest = latest_status_frame(control_dir)
    lines = [
        "# exDQLM Multivar Keep Latent Diagnostic Ladder Live Status",
        "",
        f"- updated: `{utc_now()}`",
        f"- message: {message}",
        f"- control_dir: `{control_dir}`",
        f"- report_root: `{report_root}`",
        "",
    ]
    if latest.empty:
        lines.append("No rows have started yet.")
    else:
        counts = latest["status"].value_counts().to_dict()
        lines.extend(["## Counts", "", "| status | rows |", "| --- | ---: |"])
        for status, count in sorted(counts.items()):
            lines.append(f"| `{status}` | {count} |")
        lines.extend(["", "## Rows", "", "| phase | q | cutoff | spec | status | pid | return | log |", "| --- | --- | --- | --- | --- | ---: | ---: | --- |"])
        for row in latest.to_dict(orient="records"):
            lines.append(
                "| {phase} | {q_label} | {cutoff} | {grid_spec_id} | {status} | {pid} | {returncode} | `{log_path}` |".format(
                    **row
                )
            )
    text = "\n".join(lines) + "\n"
    (control_dir / "LIVE_STATUS.md").write_text(text, encoding="utf-8")
    ensure_dirs(report_root)
    (report_root / "LIVE_STATUS.md").write_text(text, encoding="utf-8")


def collect_report(artifact_root: Path, report_root: Path, label: str, log_path: Path) -> int:
    out_dir = report_root / label
    ensure_dirs(out_dir)
    cmd = [
        "python3",
        "scripts/report_he2_exdqlm_multivar_keep_latent_diagnostics.py",
        "--root",
        str(artifact_root),
        "--out-dir",
        str(out_dir),
    ]
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"[{utc_now()}] report_start label={label} cmd={' '.join(cmd)}\n")
        proc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        log.write(f"[{utc_now()}] report_done label={label} returncode={proc.returncode}\n")
    return int(proc.returncode)


def cleanup_rdata(run_root: Path, log_path: Path) -> int:
    removed = 0
    with log_path.open("a", encoding="utf-8") as log:
        for pattern in ("*.RData", "*.rdata", "*.Rda", "*.rda"):
            for path in run_root.rglob(pattern):
                try:
                    size = path.stat().st_size
                    path.unlink()
                    removed += 1
                    log.write(f"[{utc_now()}] removed_rdata path={path} bytes={size}\n")
                except Exception as exc:
                    log.write(f"[{utc_now()}] remove_rdata_failed path={path} error={exc}\n")
    return removed


def run_root_for(row: dict[str, Any]) -> Path:
    artifact_root = Path(str(row["artifact_root"]))
    return artifact_root / "runs" / str(row["run_id"])


def launch_process(row: dict[str, Any], log_path: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    cmd = ["Rscript", "--vanilla", "scripts/unified_run.R", "--config", str(row["config_path"])]
    fh = log_path.open("w", encoding="utf-8")
    fh.write(f"[{utc_now()}] launch cmd={' '.join(cmd)}\n")
    fh.flush()
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, env=env)
    proc._ladder_log_fh = fh  # type: ignore[attr-defined]
    return proc


def close_proc_log(proc: subprocess.Popen) -> None:
    fh = getattr(proc, "_ladder_log_fh", None)
    if fh is not None:
        try:
            fh.flush()
            fh.close()
        except Exception:
            pass


def run_phase(
    phase: str,
    rows: list[dict[str, Any]],
    max_parallel: int,
    control_dir: Path,
    report_root: Path,
    artifact_root: Path,
    poll_seconds: int,
    resume: bool,
    dry_run: bool,
) -> None:
    existing = load_existing_status(control_dir)
    queue = []
    for row in rows:
        run_id = str(row["run_id"])
        prev = existing.get(run_id, {})
        if resume and prev.get("status") in {"pass", "fail"}:
            continue
        queue.append(row)

    running: dict[str, dict[str, Any]] = {}
    phase_log = control_dir / f"phase_{phase}.log"
    write_live_status(control_dir, report_root, f"phase {phase} queued={len(queue)} running=0")

    if dry_run:
        for row in queue:
            append_status(control_dir, {
                **row,
                "timestamp": utc_now(),
                "status": "dry_run",
                "message": "not launched",
                "run_root": str(run_root_for(row)),
            })
        write_live_status(control_dir, report_root, f"phase {phase} dry-run complete")
        return

    while queue or running:
        while queue and len(running) < max_parallel:
            row = queue.pop(0)
            run_id = str(row["run_id"])
            log_path = control_dir / "run_logs" / f"{run_id}.log"
            ensure_dirs(log_path.parent)
            started_at = utc_now()
            proc = launch_process(row, log_path)
            running[run_id] = {
                "row": row,
                "proc": proc,
                "log_path": log_path,
                "started_at": started_at,
            }
            append_status(control_dir, {
                **row,
                "timestamp": utc_now(),
                "status": "running",
                "pid": proc.pid,
                "started_at": started_at,
                "config_path": row["config_path"],
                "log_path": str(log_path),
                "run_root": str(run_root_for(row)),
            })

        write_live_status(
            control_dir,
            report_root,
            f"phase {phase} queued={len(queue)} running={len(running)}",
        )
        time.sleep(max(5, int(poll_seconds)))

        for run_id, info in list(running.items()):
            proc: subprocess.Popen = info["proc"]
            rc = proc.poll()
            if rc is None:
                continue
            close_proc_log(proc)
            row = info["row"]
            finished_at = utc_now()
            status = "pass" if rc == 0 else "fail"
            run_root = run_root_for(row)
            removed = cleanup_rdata(run_root, info["log_path"])
            append_status(control_dir, {
                **row,
                "timestamp": utc_now(),
                "status": status,
                "pid": proc.pid,
                "returncode": rc,
                "started_at": info["started_at"],
                "finished_at": finished_at,
                "config_path": row["config_path"],
                "log_path": str(info["log_path"]),
                "run_root": str(run_root),
                "message": f"removed_rdata={removed}",
            })
            running.pop(run_id)

        collect_report(artifact_root, report_root, f"phase_{phase}_latest", phase_log)

    collect_report(artifact_root, report_root, f"phase_{phase}_final", phase_log)
    write_live_status(control_dir, report_root, f"phase {phase} complete")


def write_final_summary(control_dir: Path, report_root: Path, phases: list[str]) -> None:
    latest = latest_status_frame(control_dir)
    summary_path = report_root / "FINAL_SUMMARY.md"
    lines = [
        "# exDQLM Multivar Keep Latent Diagnostic Ladder Final Summary",
        "",
        f"- completed_at: `{utc_now()}`",
        f"- phases_requested: `{','.join(phases)}`",
        f"- status_csv: `{status_path(control_dir)}`",
        f"- live_status: `{report_root / 'LIVE_STATUS.md'}`",
        "",
    ]
    if latest.empty:
        lines.append("No run rows were executed.")
    else:
        counts = latest["status"].value_counts().to_dict()
        lines.extend(["## Status Counts", "", "| status | rows |", "| --- | ---: |"])
        for status, count in sorted(counts.items()):
            lines.append(f"| `{status}` | {count} |")
        lines.extend(["", "## Run Rows", "", "| phase | q | cutoff | spec | status | return |", "| --- | --- | --- | --- | --- | ---: |"])
        for row in latest.to_dict(orient="records"):
            lines.append(
                f"| {row['phase']} | {row['q_label']} | {row['cutoff']} | {row['grid_spec_id']} | {row['status']} | {row['returncode']} |"
            )
    lines.extend([
        "",
        "## Report Directories",
        "",
    ])
    for path in sorted(report_root.glob("phase_*")):
        if path.is_dir():
            lines.append(f"- `{path}`")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    matrix_plan = Path(args.matrix_plan).expanduser().resolve()
    artifact_root = Path(args.artifact_root).expanduser().resolve()
    report_root = Path(args.report_root).expanduser().resolve()
    control_dir = artifact_root / "control" / "overnight_ladder"
    ensure_dirs(control_dir, control_dir / "run_logs", report_root)

    phases = [p.strip() for p in str(args.phases).split(",") if p.strip()]
    parallel = phase_parallel(args)
    matrix = pd.read_csv(matrix_plan, dtype=str).fillna("")
    matrix["phase"] = matrix["phase"].astype(str)

    (control_dir / "controller.pid").write_text(str(os.getpid()) + "\n", encoding="utf-8")
    (control_dir / "controller_started_at.txt").write_text(utc_now() + "\n", encoding="utf-8")
    write_live_status(control_dir, report_root, "controller starting")

    for phase in phases:
        phase_rows = matrix[matrix["phase"] == phase].to_dict(orient="records")
        if not phase_rows:
            append_status(control_dir, {
                "timestamp": utc_now(),
                "phase": phase,
                "status": "skip",
                "message": "no rows for phase",
            })
            continue
        run_phase(
            phase=phase,
            rows=phase_rows,
            max_parallel=parallel.get(phase, 1),
            control_dir=control_dir,
            report_root=report_root,
            artifact_root=artifact_root,
            poll_seconds=max(5, int(args.poll_seconds)),
            resume=bool(args.resume),
            dry_run=bool(args.dry_run),
        )

    collect_report(artifact_root, report_root, "all_phases_final", control_dir / "final_report.log")
    write_final_summary(control_dir, report_root, phases)
    write_live_status(control_dir, report_root, "all requested phases complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
