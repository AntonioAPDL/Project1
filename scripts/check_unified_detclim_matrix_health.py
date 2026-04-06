#!/usr/bin/env python3
"""Compact health check across matrix batch launches."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = ROOT / "repro" / "runs"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_tsv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def load_manifest_stages(run_root: Path) -> Dict[str, str]:
    manifest = run_root / "run_manifest.yaml"
    if not manifest.exists():
        return {}
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    stages = data.get("stages") or {}
    if not isinstance(stages, dict):
        return {}
    out: Dict[str, str] = {}
    for name in ("forecats", "data_prep_shared", "fit", "post"):
        node = stages.get(name)
        if isinstance(node, dict):
            out[name] = str(node.get("status", ""))
    return out


def count_files(root: Path, pattern: str) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob(pattern))


def find_active_pids(run_id: str) -> List[int]:
    try:
        out = subprocess.check_output(["ps", "-eo", "pid=,command="], text=True)
    except Exception:
        return []
    pids: List[int] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid_txt, cmd = line.split(maxsplit=1)
            pid = int(pid_txt)
        except Exception:
            continue
        if run_id in cmd and ("unified_run.R" in cmd or "run_unified_detclim_cutoff_batches.sh" in cmd):
            pids.append(pid)
    return sorted(set(pids))


def summarize_batch(batch_root: Path) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
    status_rows = read_tsv(batch_root / "status.tsv")
    status_by_run: Dict[str, str] = {}
    for row in status_rows:
        run_id = row.get("run_id", "")
        status = row.get("status", "")
        if run_id:
            status_by_run[run_id] = status

    planned: List[Dict[str, str]] = []
    plan_path = batch_root / "batch_plan.txt"
    if plan_path.exists():
        for line in plan_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split(maxsplit=2)
            if len(parts) == 3:
                planned.append({"batch": parts[0], "run_id": parts[1], "config": parts[2]})

    started_runs = set()
    runner_log = batch_root / "runner.log"
    if runner_log.exists():
        pat = re.compile(r"Starting\\s+(multimodel_[A-Za-z0-9_]+)\\s+from")
        for line in runner_log.read_text(encoding="utf-8", errors="replace").splitlines():
            m = pat.search(line)
            if m:
                started_runs.add(m.group(1))

    run_rows: List[Dict[str, str]] = []
    for item in planned:
        run_id = item["run_id"]
        status = status_by_run.get(run_id, "pending")
        run_root = RUNS_ROOT / run_id
        stages = load_manifest_stages(run_root)
        post_root = run_root / "post" / "outputs" / run_id
        pids = find_active_pids(run_id)

        not_started = status == "pending" and run_id not in started_runs and not pids
        if not_started:
            stage_sig = "-"
            figures_total = "na"
            figures_keep = "na"
            rdata_count = "na"
        else:
            stage_sig = "/".join(
                [
                    stages.get("forecats", "-")[:1],
                    stages.get("data_prep_shared", "-")[:1],
                    stages.get("fit", "-")[:1],
                    stages.get("post", "-")[:1],
                ]
            )
            figures_total = str(count_files(post_root, "*.png"))
            figures_keep = str(count_files(post_root, "*keep*.png"))
            rdata_count = str(count_files(run_root, "*.RData") + count_files(run_root, "*.rdata"))

        run_rows.append(
            {
                "run_id": run_id,
                "status": status,
                "stage_sig": stage_sig,
                "active_pids": ",".join(str(p) for p in pids) if pids else "",
                "rdata": rdata_count,
                "fig_png": figures_total,
                "fig_keep": figures_keep,
                "run_root": str(run_root),
            }
        )

    meta = {
        "batch_root": str(batch_root),
        "runner_log": str(batch_root / "runner.log"),
        "status_tsv": str(batch_root / "status.tsv"),
    }
    return run_rows, meta


def render_markdown(matrix_root: Path, rows: List[Dict[str, str]]) -> str:
    lines = [
        "# Matrix Health Snapshot",
        "",
        f"- generated_at_utc: `{utc_now()}`",
        f"- matrix_root: `{matrix_root}`",
        "",
        "| suffix | run_id | status | stages(F/D/Fit/P) | active_pids | .RData | png | keep_png |",
        "|---|---|---|---|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {suffix} | {run_id} | {status} | {stage_sig} | {active_pids} | {rdata} | {fig_png} | {fig_keep} |".format(
                suffix=row.get("suffix", ""),
                run_id=row.get("run_id", ""),
                status=row.get("status", ""),
                stage_sig=row.get("stage_sig", ""),
                active_pids=row.get("active_pids", ""),
                rdata=row.get("rdata", "0"),
                fig_png=row.get("fig_png", "0"),
                fig_keep=row.get("fig_keep", "0"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-root", required=True, help="Path to unified_detclim_matrix_<ts> directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matrix_root = Path(args.matrix_root).resolve()
    batches = read_tsv(matrix_root / "batches.tsv")
    if not batches:
      print(f"No batches.tsv found or empty under {matrix_root}")
      return 2

    all_rows: List[Dict[str, str]] = []
    batch_meta: List[Dict[str, str]] = []
    for batch in batches:
        suffix = batch.get("suffix", "")
        batch_root = Path(batch.get("batch_root", ""))
        run_rows, meta = summarize_batch(batch_root)
        batch_meta.append(meta)
        for row in run_rows:
            row["suffix"] = suffix if suffix else "base"
            all_rows.append(row)

    payload = {
        "generated_at_utc": utc_now(),
        "matrix_root": str(matrix_root),
        "batches": batch_meta,
        "runs": all_rows,
    }

    out_json = matrix_root / "matrix_health_snapshot.json"
    out_md = matrix_root / "matrix_health_snapshot.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out_md.write_text(render_markdown(matrix_root, all_rows), encoding="utf-8")

    print(f"WROTE {out_json}")
    print(f"WROTE {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
