#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


PROGRESS_RE = re.compile(
    r"\[gamsig_progress\].*?iter=(\d+).*?elbo=([^\s]+).*?"
    r"sigma_exp=([^\s]+).*?gamma_exp=([^\s]+).*?state_norm_sq=([^\s]+)"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload if isinstance(payload, dict) else {}


def active_config_processes() -> dict[str, str]:
    proc = subprocess.run(["ps", "-eo", "pid=,command="], text=True, capture_output=True, check=True)
    active: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "scripts/unified_run.R" not in line or "--config" not in line:
            continue
        match = re.match(r"^\s*(\d+)\s+(.*)$", line)
        cfg_match = re.search(r"--config\s+(\S+\.ya?ml)", line)
        if not match or not cfg_match:
            continue
        active[str(Path(cfg_match.group(1)).resolve())] = match.group(1)
    return active


def stage_status(run_root: Path) -> tuple[str, str, str]:
    manifest_path = run_root / "run_manifest.yaml"
    if not manifest_path.exists():
        return "not_started", "", ""
    try:
        manifest = load_yaml(manifest_path)
    except Exception as exc:
        return "manifest_unreadable", "", str(exc)
    stages = manifest.get("stages", {})
    if not isinstance(stages, dict):
        return "manifest_no_stages", "", ""
    data = stages.get("data_prep_shared", {}) if isinstance(stages.get("data_prep_shared", {}), dict) else {}
    fit = stages.get("fit", {}) if isinstance(stages.get("fit", {}), dict) else {}
    return str(data.get("status", "")), str(fit.get("status", "")), str(fit.get("message", ""))


def parse_progress(fit_log: Path) -> dict[str, str]:
    out = {"iter": "", "elbo": "", "sigma": "", "gamma": "", "state_norm_sq": "", "fit_log_tail": ""}
    if not fit_log.exists():
        return out
    try:
        lines = fit_log.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return out
    for line in reversed(lines[-2000:]):
        match = PROGRESS_RE.search(line)
        if match:
            out.update(
                {
                    "iter": match.group(1),
                    "elbo": match.group(2),
                    "sigma": match.group(3),
                    "gamma": match.group(4),
                    "state_norm_sq": match.group(5),
                }
            )
            return out
    out["fit_log_tail"] = next((line.strip() for line in reversed(lines) if line.strip()), "")[:120]
    return out


def terminal_health(run_root: Path, q_label: str) -> dict[str, str]:
    path = run_root / "fit" / f"q={q_label}" / "outputs" / "multivar_terminal_state_health.csv"
    if not path.exists():
        return {
            "terminal_health_exists": "False",
            "terminal_violation_n": "",
            "state_norm_sq_per_T": "",
            "transfer_level_max_abs": "",
            "max_abs_history_exps": "",
        }
    try:
        rows = read_csv(path)
    except Exception:
        rows = []
    row = rows[0] if rows else {}
    return {
        "terminal_health_exists": "True",
        "terminal_violation_n": row.get("violation_n", ""),
        "state_norm_sq_per_T": row.get("state_norm_sq_per_T", ""),
        "transfer_level_max_abs": row.get("transfer_level_max_abs", ""),
        "max_abs_history_exps": row.get("max_abs_history_exps", ""),
    }


def collect_root(root: Path, active: dict[str, str]) -> list[dict[str, Any]]:
    manifest_path = root / "control" / "diagnostic_matrix" / "diagnostic_launch_manifest.csv"
    if not manifest_path.exists():
        return []
    rows = read_csv(manifest_path)
    out: list[dict[str, Any]] = []
    for row in rows:
        q_label = row.get("lane", "").replace("q", "")
        run_root = root / "runs" / row["run_id"]
        data_status, fit_status, fit_message = stage_status(run_root)
        fit_log = run_root / "fit" / f"q={q_label}" / "logs" / "fit.log"
        progress = parse_progress(fit_log)
        health = terminal_health(run_root, q_label)
        out.append(
            {
                "root": root.name,
                "experiment_id": row.get("experiment_id", ""),
                "cutoff": row.get("cutoff", ""),
                "lane": row.get("lane", ""),
                "data_status": data_status,
                "fit_status": fit_status,
                "pid": active.get(str(Path(row["config_path"]).resolve()), ""),
                "iter": progress["iter"],
                "elbo": progress["elbo"],
                "sigma": progress["sigma"],
                "gamma": progress["gamma"],
                "state_norm_sq": progress["state_norm_sq"],
                "fit_log_tail": progress["fit_log_tail"],
                "fit_message": fit_message,
                **health,
                "run_id": row.get("run_id", ""),
                "config_path": row.get("config_path", ""),
            }
        )
    return out


def write_markdown(path: Path, rows: list[dict[str, Any]], roots: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    active_n = sum(1 for row in rows if row.get("pid"))
    fail_n = sum(1 for row in rows if row.get("fit_status") == "fail")
    pass_n = sum(1 for row in rows if row.get("fit_status") == "pass")
    lines = [
        "# HE2 AL-M-T0 Diagnostic Ladder Live Status",
        "",
        f"- generated_at_utc: `{utc_now()}`",
        f"- roots: `{len(roots)}`",
        f"- rows: `{len(rows)}`",
        f"- active: `{active_n}`",
        f"- fit_pass: `{pass_n}`",
        f"- fit_fail: `{fail_n}`",
        "",
        "| root | experiment | cutoff | q | fit | pid | iter | elbo | sigma | gamma | state norm sq | terminal health |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        health = "yes" if row.get("terminal_health_exists") == "True" else ""
        lines.append(
            f"| `{row['root']}` | `{row['experiment_id']}` | {row['cutoff']} | {row['lane']} | "
            f"{row['fit_status']} | {row['pid']} | {row['iter']} | {row['elbo']} | {row['sigma']} | "
            f"{row['gamma']} | {row['state_norm_sq']} | {health} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor HE2 AL-M-T0 targeted diagnostic ladder roots.")
    parser.add_argument("--root", type=Path, action="append", required=True)
    parser.add_argument("--outdir", type=Path, default=Path("reports/he2_al_m_t0_transfer_ladder_live_20260604"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = [root.resolve() for root in args.root]
    active = active_config_processes()
    rows: list[dict[str, Any]] = []
    for root in roots:
        rows.extend(collect_root(root, active))
    outdir = args.outdir.resolve()
    write_csv(outdir / "diagnostic_ladder_live_status.csv", rows)
    write_markdown(outdir / "DIAGNOSTIC_LADDER_LIVE_STATUS.md", rows, roots)
    print(json.dumps({"rows": len(rows), "outdir": str(outdir), "active": sum(1 for row in rows if row.get("pid"))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
