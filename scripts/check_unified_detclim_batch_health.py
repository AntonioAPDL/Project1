#!/usr/bin/env python3
"""Summarize ordered deterministic-covariate batch health."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


ERROR_PATTERNS = [
    re.compile(r".*\[FORECAST_CUBE_EMPTY\].*"),
    re.compile(r"^\s*Error\b.*"),
    re.compile(r".*stage failed.*"),
    re.compile(r".*Execution halted.*"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--batch-root", required=True, help="Path to unified_detclim_batches_<timestamp> directory")
    return p.parse_args()


def read_statuses(path: Path) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            run_id = (row.get("run_id") or "").strip()
            if run_id:
                out[run_id] = {k: (v or "").strip() for k, v in row.items()}
    return out


def read_plan(path: Path) -> List[Dict[str, str]]:
    runs: List[Dict[str, str]] = []
    if not path.exists():
        return runs
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=2)
        if len(parts) != 3:
            continue
        batch, run_id, cfg_rel = parts
        runs.append({"batch": batch, "run_id": run_id, "config": cfg_rel})
    return runs


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def tail_lines(path: Path, n: int = 40) -> List[str]:
    text = read_text(path)
    if not text:
        return []
    return text.splitlines()[-n:]


def find_error_signature(paths: List[Path]) -> Optional[Dict[str, str]]:
    for path in paths:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for pattern in ERROR_PATTERNS:
            for line in reversed(lines):
                stripped = line.strip()
                if pattern.match(stripped):
                    return {"path": str(path.resolve()), "line": stripped}
    return None


def load_detclim_summary(run_root: Path) -> Dict[str, object]:
    summary_path = run_root / "inputs" / "shared" / "deterministic_climate" / "deterministic_climate_summary.txt"
    out: Dict[str, object] = {
        "summary_path": str(summary_path.resolve()),
        "exists": summary_path.exists(),
    }
    if not summary_path.exists():
        return out
    for line in summary_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def infer_stage_state(run_root: Path) -> Dict[str, str]:
    manifest_path = run_root / "run_manifest.yaml"
    out = {
        "run_manifest_exists": str(manifest_path.exists()).lower(),
        "validate_compare_exists": str((run_root / "validate" / "compare_report.json").exists()).lower(),
        "report_summary_exists": str((run_root / "report" / "summary.json").exists()).lower(),
    }
    return out


def run_health(batch_root: Path) -> Dict[str, object]:
    status_map = read_statuses(batch_root / "status.tsv")
    planned = read_plan(batch_root / "batch_plan.txt")
    runner_tail = tail_lines(batch_root / "runner.log", n=60)

    runs: List[Dict[str, object]] = []
    active_run_id: Optional[str] = None
    failed_run_id: Optional[str] = None
    for item in planned:
        run_id = item["run_id"]
        run_root = batch_root.parents[1] / "runs" / run_id
        status_row = status_map.get(run_id)
        recorded_status = status_row["status"] if status_row else "pending"
        if recorded_status.startswith("fail") and failed_run_id is None:
            failed_run_id = run_id

        log_path = batch_root / f"{run_id}.log"
        post_keep_log = run_root / "post" / "logs" / "post_runner_keep.log"
        post_log = run_root / "post" / "logs" / "post_runner.log"
        run_log_error = find_error_signature([post_keep_log, post_log, log_path])
        if recorded_status == "pending" and log_path.exists() and active_run_id is None:
            active_run_id = run_id
        runs.append(
            {
                "batch": item["batch"],
                "run_id": run_id,
                "config": item["config"],
                "status": recorded_status,
                "log_path": str(log_path.resolve()),
                "log_exists": log_path.exists(),
                "log_tail": tail_lines(log_path, n=25),
                "run_root": str(run_root.resolve()),
                "run_root_exists": run_root.exists(),
                "stage_artifacts": infer_stage_state(run_root) if run_root.exists() else {},
                "deterministic_climate": load_detclim_summary(run_root) if run_root.exists() else {"exists": False},
                "error_signature": run_log_error,
            }
        )

    return {
        "generated_at_utc": utc_now(),
        "batch_root": str(batch_root.resolve()),
        "runner_log": str((batch_root / "runner.log").resolve()),
        "status_tsv": str((batch_root / "status.tsv").resolve()),
        "active_run_id": active_run_id,
        "failed_run_id": failed_run_id,
        "runner_tail": runner_tail,
        "runs": runs,
    }


def write_outputs(batch_root: Path, payload: Dict[str, object]) -> None:
    out_json = batch_root / "batch_health_snapshot.json"
    out_md = batch_root / "batch_health_snapshot.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Batch Health Snapshot",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- batch_root: `{payload['batch_root']}`",
        f"- active_run_id: `{payload.get('active_run_id')}`",
        f"- failed_run_id: `{payload.get('failed_run_id')}`",
        "",
        "## Runner Tail",
        "",
    ]
    runner_tail = payload.get("runner_tail", []) or []
    if runner_tail:
        lines.extend([f"- `{line}`" for line in runner_tail])
    else:
        lines.append("- none")

    lines.extend(["", "## Runs", ""])
    for run in payload.get("runs", []):
        run = dict(run)
        lines.extend(
            [
                f"### {run['run_id']}",
                "",
                f"- batch: `{run['batch']}`",
                f"- status: `{run['status']}`",
                f"- log_path: `{run['log_path']}`",
                f"- run_root: `{run['run_root']}`",
            ]
        )
        det = run.get("deterministic_climate", {}) or {}
        lines.extend(
            [
                f"- deterministic_climate.exists: `{det.get('exists', False)}`",
                f"- deterministic_climate.precip_source: `{det.get('precip_source', 'NA')}`",
                f"- deterministic_climate.soil_source: `{det.get('soil_source', 'NA')}`",
                f"- deterministic_climate.horizon_days: `{det.get('horizon_days', 'NA')}`",
            ]
        )
        err = run.get("error_signature")
        if err:
            lines.extend(
                [
                    f"- error_path: `{err['path']}`",
                    f"- error_line: `{err['line']}`",
                ]
            )
        else:
            lines.append("- error_line: `none detected`")
        lines.append("")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    batch_root = Path(args.batch_root).resolve()
    payload = run_health(batch_root)
    write_outputs(batch_root, payload)
    print(f"WROTE {batch_root / 'batch_health_snapshot.json'}")
    print(f"WROTE {batch_root / 'batch_health_snapshot.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
