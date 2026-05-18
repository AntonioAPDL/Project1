#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from multimodel_v8_lib import load_yaml, resolve_artifact_root, runs_dir


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_mtime(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_quantile_label(token: str | int | None) -> str | None:
    if token in (None, ""):
        return None
    value = str(token).strip().lower()
    if value.startswith("q="):
        value = value.split("=", 1)[1]
    if value.startswith("q"):
        value = value[1:]
    if "." in value:
        q = float(value)
        if q > 1.0:
            q = q / 100.0
        return f"{int(round(q * 100)):02d}"
    return f"{int(value):02d}"


def stage_status(manifest_path: Path) -> tuple[str, str]:
    if not manifest_path.exists():
        return "not_started", "not_started"
    manifest = load_yaml(manifest_path)
    stages = manifest.get("stages", {}) if isinstance(manifest, dict) else {}
    for stage in ["forecats", "data_prep_shared", "fit", "post", "validate", "report"]:
        entry = stages.get(stage, {}) if isinstance(stages, dict) else {}
        status = str(entry.get("status", "")).strip().lower() if isinstance(entry, dict) else ""
        if status in {"pending", "fail"}:
            return stage, status
    report_entry = stages.get("report", {}) if isinstance(stages, dict) else {}
    report_status = str(report_entry.get("status", "")).strip().lower() if isinstance(report_entry, dict) else ""
    if report_status == "pass":
        return "report", "pass"
    return "unknown", report_status or "unknown"


@dataclass
class ProcessSnapshot:
    pid: int
    ppid: int
    state: str
    etimes: int
    pcpu: float
    pmem: float
    command: str
    wchar: int
    write_bytes: int


def sample_proc_io(pid: int) -> tuple[int, int]:
    io_path = Path("/proc") / str(pid) / "io"
    if not io_path.exists():
        return 0, 0
    values: dict[str, int] = {}
    for raw_line in io_path.read_text(encoding="utf-8").splitlines():
        key, _, value = raw_line.partition(":")
        key = key.strip()
        value = value.strip()
        if key and value.isdigit():
            values[key] = int(value)
    return values.get("wchar", 0), values.get("write_bytes", 0)


def parse_ps_rows() -> list[dict[str, str]]:
    proc = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,state=,etimes=,pcpu=,pmem=,command="],
        capture_output=True,
        text=True,
        check=True,
    )
    rows: list[dict[str, str]] = []
    pattern = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\S+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(.*)$")
    for line in proc.stdout.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        rows.append(
            {
                "pid": match.group(1),
                "ppid": match.group(2),
                "state": match.group(3),
                "etimes": match.group(4),
                "pcpu": match.group(5),
                "pmem": match.group(6),
                "command": match.group(7),
            }
        )
    return rows


def _collect_descendant_pids(seed_pids: set[int], rows: list[dict[str, str]]) -> set[int]:
    by_parent: dict[int, set[int]] = {}
    for row in rows:
        by_parent.setdefault(int(row["ppid"]), set()).add(int(row["pid"]))
    out = set(seed_pids)
    frontier = list(seed_pids)
    while frontier:
        pid = frontier.pop()
        for child in by_parent.get(pid, set()):
            if child in out:
                continue
            out.add(child)
            frontier.append(child)
    return out


def collect_process_snapshots(match_token: str, sample_seconds: int) -> list[ProcessSnapshot]:
    first_ps = parse_ps_rows()
    seed_pids = {int(row["pid"]) for row in first_ps if match_token in row["command"]}
    tracked_pids = _collect_descendant_pids(seed_pids, first_ps)
    first_rows = [row for row in first_ps if int(row["pid"]) in tracked_pids]
    if not first_rows:
        return []
    first_io = {int(row["pid"]): sample_proc_io(int(row["pid"])) for row in first_rows}
    time.sleep(max(sample_seconds, 0))
    second_ps = parse_ps_rows()
    second_tracked = _collect_descendant_pids(seed_pids, second_ps)
    second_rows = {int(row["pid"]): row for row in second_ps if int(row["pid"]) in second_tracked}
    snapshots: list[ProcessSnapshot] = []
    for pid, first in first_io.items():
        row = second_rows.get(pid)
        if row is None:
            continue
        second_wchar, second_write_bytes = sample_proc_io(pid)
        snapshots.append(
            ProcessSnapshot(
                pid=pid,
                ppid=int(row["ppid"]),
                state=row["state"],
                etimes=int(row["etimes"]),
                pcpu=float(row["pcpu"]),
                pmem=float(row["pmem"]),
                command=row["command"],
                wchar=second_wchar - first[0],
                write_bytes=second_write_bytes - first[1],
            )
        )
    return snapshots


def latest_log_mtime(path: Path | None) -> str:
    return iso_mtime(path)


def classify_liveness(
    *,
    stage: str,
    status: str,
    process_found: bool,
    state: str,
    pcpu: float,
    log_age_seconds: float | None,
    wchar_delta: int,
    write_delta: int,
    health_exists: bool,
    rdata_exists: bool,
    cpu_active_threshold: float = 20.0,
    cpu_stall_threshold: float = 5.0,
    stall_log_age_seconds: float = 1800.0,
) -> str:
    if status == "pass":
        return "row_complete"
    if status == "fail":
        return "row_failed"
    if health_exists:
        return "submodel_complete"
    if not process_found:
        return "likely_stalled"
    if pcpu >= cpu_active_threshold:
        return "active_cpu_bound"
    if wchar_delta > 0 or write_delta > 0:
        return "active_io_bound"
    if state.startswith("R"):
        return "active_compute"
    if log_age_seconds is not None and log_age_seconds <= stall_log_age_seconds:
        return "quiet_recent"
    if pcpu < cpu_stall_threshold and wchar_delta == 0 and write_delta == 0:
        return "likely_stalled"
    return "quiet_watch"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Audit liveness of a HE2 publication relaunch row or quantile submodel.")
    ap.add_argument("--artifact-root", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--run-root", default="")
    ap.add_argument("--quantile", default="")
    ap.add_argument("--sample-seconds", type=int, default=5)
    return ap.parse_args()


def resolve_run_root(args: argparse.Namespace) -> Path:
    if args.run_root:
        return Path(args.run_root).resolve()
    if not args.run_id:
        raise ValueError("either --run-root or --run-id is required")
    artifact_root = resolve_artifact_root(args.artifact_root or None)
    return (runs_dir(artifact_root if args.artifact_root else None) / args.run_id).resolve()


def main() -> int:
    args = parse_args()
    run_root = resolve_run_root(args)
    run_id = run_root.name
    manifest_path = run_root / "run_manifest.yaml"
    stage, status = stage_status(manifest_path)

    quantile_label = normalize_quantile_label(args.quantile)
    match_token = run_id
    fit_log_path: Path | None = None
    health_path: Path | None = None
    rdata_path: Path | None = None
    if quantile_label:
        q_root = run_root / "fit" / "exdqlm_multivar" / "keep" / f"q={quantile_label}"
        fit_log_path = q_root / "logs" / "fit.log"
        health_path = q_root / "outputs" / "multivar_forecast_health.txt"
        q_num = str(int(quantile_label))
        rdata_path = q_root / "outputs" / f"DISC_variables_{q_num}_exAL_synth_DISC.RData"
        match_token = str(q_root / "outputs")

    snapshots = collect_process_snapshots(match_token, args.sample_seconds)
    primary = max(snapshots, key=lambda item: item.pcpu, default=None)
    log_age_seconds: float | None = None
    if fit_log_path and fit_log_path.exists():
        log_age_seconds = max(0.0, datetime.now(timezone.utc).timestamp() - fit_log_path.stat().st_mtime)

    classification = classify_liveness(
        stage=stage,
        status=status,
        process_found=primary is not None,
        state=primary.state if primary else "",
        pcpu=primary.pcpu if primary else 0.0,
        log_age_seconds=log_age_seconds,
        wchar_delta=primary.wchar if primary else 0,
        write_delta=primary.write_bytes if primary else 0,
        health_exists=bool(health_path and health_path.exists()),
        rdata_exists=bool(rdata_path and rdata_path.exists()),
    )

    payload: dict[str, Any] = {
        "audited_at_utc": utc_now(),
        "run_id": run_id,
        "run_root": str(run_root),
        "stage": stage,
        "status": status,
        "quantile": quantile_label,
        "fit_log_path": str(fit_log_path) if fit_log_path else "",
        "fit_log_mtime_utc": latest_log_mtime(fit_log_path),
        "fit_log_age_seconds": log_age_seconds,
        "health_path": str(health_path) if health_path else "",
        "health_exists": bool(health_path and health_path.exists()),
        "rdata_path": str(rdata_path) if rdata_path else "",
        "rdata_exists": bool(rdata_path and rdata_path.exists()),
        "classification": classification,
        "processes": [
            {
                "pid": snap.pid,
                "ppid": snap.ppid,
                "state": snap.state,
                "etimes": snap.etimes,
                "pcpu": snap.pcpu,
                "pmem": snap.pmem,
                "wchar_delta": snap.wchar,
                "write_bytes_delta": snap.write_bytes,
                "command": snap.command,
            }
            for snap in snapshots
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
