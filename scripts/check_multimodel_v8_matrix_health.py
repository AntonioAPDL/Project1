#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from multimodel_v8_lib import artifact_disk_free_gb, control_dir, load_yaml, matrix_report_dir, resolve_artifact_root, runs_dir

STAGE_ORDER = ["forecats", "data_prep_shared", "fit", "post", "validate", "report"]


def _iso_mtime(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _latest_stage_log_mtime(run_root: Path, stage: str, fallback: Path | None) -> str:
    candidates: list[Path] = []
    stage_dir = run_root / stage
    if stage_dir.exists():
        candidates.extend(p for p in stage_dir.rglob("*.log") if p.is_file())
    if fallback and fallback.exists():
        candidates.append(fallback)
    if not candidates:
        return ""
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    return _iso_mtime(newest)


def _stage_view(manifest: dict[str, Any], run_root: Path) -> tuple[str, str, str, str, str]:
    stages = manifest.get("stages", {}) if isinstance(manifest, dict) else {}
    latest_log = None
    for stage in STAGE_ORDER:
        entry = stages.get(stage, {}) if isinstance(stages, dict) else {}
        if not isinstance(entry, dict):
            continue
        log_path = Path(str(entry.get("log_path", ""))) if entry.get("log_path") else None
        if log_path and log_path.exists():
            if latest_log is None or log_path.stat().st_mtime > latest_log.stat().st_mtime:
                latest_log = log_path
        status = str(entry.get("status", "")).strip().lower()
        if status in {"pending", "fail"}:
            return (
                stage,
                status,
                str(entry.get("started_at_utc", "") or ""),
                str(entry.get("finished_at_utc", "") or ""),
                _latest_stage_log_mtime(run_root, stage, latest_log or log_path),
            )
    report_entry = stages.get("report", {}) if isinstance(stages, dict) else {}
    status = str(report_entry.get("status", "")).strip().lower() if isinstance(report_entry, dict) else ""
    if status == "pass":
        log_path = Path(str(report_entry.get("log_path", ""))) if report_entry.get("log_path") else latest_log
        return (
            "report",
            "pass",
            str(manifest.get("timestamps", {}).get("started_at_utc", "") or ""),
            str(manifest.get("timestamps", {}).get("finished_at_utc", "") or ""),
            _latest_stage_log_mtime(run_root, "report", log_path or latest_log),
        )
    return (
        "unknown",
        status or "unknown",
        str(manifest.get("timestamps", {}).get("started_at_utc", "") or ""),
        str(manifest.get("timestamps", {}).get("finished_at_utc", "") or ""),
        _iso_mtime(latest_log),
    )


def build_status(matrix_dir: Path, artifact_root: str | Path | None = None) -> pd.DataFrame:
    plan = pd.read_csv(matrix_dir / "matrix_plan.csv")
    for col in ("cutoff", "epsilon", "lane", "run_id"):
        if col in plan.columns:
            plan[col] = plan[col].astype(str)
    if "cutoff" in plan.columns:
        plan["cutoff"] = plan["cutoff"].str.zfill(8)
    rows = []
    active_runs_dir = runs_dir(artifact_root)
    free_gb = artifact_disk_free_gb(artifact_root)
    for _, row in plan.iterrows():
        manifest_path = active_runs_dir / str(row["run_id"]) / "run_manifest.yaml"
        if manifest_path.exists():
            manifest = load_yaml(manifest_path)
            phase, status, started_at, finished_at, latest_log_mtime = _stage_view(manifest, manifest_path.parent)
            note = ""
            if status == "pass":
                note = "closed"
            elif status == "pending":
                note = "in_progress"
            elif status == "fail":
                note = "failed"
        else:
            phase, status, started_at, finished_at, latest_log_mtime = "not_started", "not_started", "", "", ""
            note = "manifest_missing"
        rows.append({
            "cutoff": row["cutoff"],
            "epsilon": row["epsilon"],
            "lane": row["lane"],
            "run_id": row["run_id"],
            "phase": phase,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "manifest_path": str(manifest_path),
            "latest_log_mtime": latest_log_mtime,
            "disk_free_gb": free_gb,
            "note": note,
        })
    df = pd.DataFrame(rows).sort_values(["cutoff", "epsilon", "lane"]).reset_index(drop=True)
    return df


def write_status_markdown(df: pd.DataFrame, out_path: Path) -> None:
    lines = ["# v8 matrix status", ""]
    summary = df.groupby(["status"]).size().reset_index(name="n")
    lines.append("## Counts")
    for _, row in summary.iterrows():
        lines.append(f"- {row['status']}: {int(row['n'])}")
    lines.append("")
    lines.append("## Active or incomplete")
    incomplete = df.loc[df["status"] != "pass"]
    if incomplete.empty:
        lines.append("- None.")
    else:
        for _, row in incomplete.iterrows():
            lines.append(
                f"- `{row['run_id']}`: phase={row['phase']}, status={row['status']}, latest_log_mtime={row['latest_log_mtime']}, note={row['note']}"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Check health of v8 multimodel matrix runs.")
    ap.add_argument("--matrix-dir")
    ap.add_argument("--artifact-root")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    artifact_root = resolve_artifact_root(args.artifact_root)
    matrix_dir = Path(args.matrix_dir) if args.matrix_dir else (control_dir(artifact_root) if args.artifact_root else matrix_report_dir("20260401"))
    df = build_status(matrix_dir, artifact_root=artifact_root if args.artifact_root else None)
    df.to_csv(matrix_dir / "matrix_status.csv", index=False)
    write_status_markdown(df, matrix_dir / "matrix_status.md")
    print(matrix_dir / "matrix_status.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
