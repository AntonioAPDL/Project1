#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "publication_replay_representatives_20260506"
OUT_DIR = REPO_ROOT / "reports" / "publication_replay"
OUT_CSV = OUT_DIR / "publication_representative_status.csv"
OUT_MD = OUT_DIR / "publication_representative_status.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh live status for publication representative replays.")
    parser.add_argument("--slugs", nargs="*", help="Subset of representative slugs to inspect.")
    return parser.parse_args()


def is_pid_active(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def tail_text(path: Path, lines: int = 80) -> str:
    if not path.exists():
        return ""
    data = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(data[-lines:])


def active_run_root_pids(run_root: Path) -> list[int]:
    proc = subprocess.run(
        ["pgrep", "-f", str(run_root)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    pids: list[int] = []
    for raw in proc.stdout.split():
        try:
            pid = int(raw)
        except ValueError:
            continue
        if pid == os.getpid():
            continue
        if is_pid_active(pid):
            pids.append(pid)
    return sorted(set(pids))


def classify_run(run_root: Path, matrix_dir: Path) -> tuple[str, str]:
    active_pids = active_run_root_pids(run_root)

    state_dir = matrix_dir / "controller_state"
    runner_pid = None
    pid_path = state_dir / "runner.pid"
    if pid_path.exists():
        try:
            runner_pid = int(pid_path.read_text(encoding="utf-8").strip())
        except ValueError:
            runner_pid = None

    report_summary = run_root / "report" / "summary.json"
    if report_summary.exists():
        try:
            payload = json.loads(report_summary.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        validation_status = str(payload.get("validation_status", "")).strip().lower()
        if is_pid_active(runner_pid) or active_pids:
            if is_pid_active(runner_pid):
                return "RUNNING", f"report summary present but direct runner still active pid={runner_pid}"
            return "RUNNING", f"report summary present but run-root workers still active pids={','.join(str(pid) for pid in active_pids[:5])}"
        if validation_status == "pass":
            return "PASS", "report summary present with validation_status=pass"
        return "REPORT_PRESENT", f"report summary present with validation_status={validation_status or 'missing'}"
    if is_pid_active(runner_pid):
        return "RUNNING", f"direct runner active pid={runner_pid}"
    if active_pids:
        return "RUNNING", f"run-root workers active pids={','.join(str(pid) for pid in active_pids[:5])}"

    fit_stage_log = run_root / "fit" / "logs" / "fit_stage.log"
    fit_stage_tail = tail_text(fit_stage_log)
    if "Error:" in fit_stage_tail:
        return "FAIL", fit_stage_tail.splitlines()[-1]

    q20_log = run_root / "fit" / "exdqlm_multivar" / "keep" / "q=20" / "logs" / "fit.log"
    q20_tail = tail_text(q20_log)
    if "Error:" in q20_tail:
        return "FAIL", q20_tail.splitlines()[-1]

    univar_q05_log = run_root / "fit" / "exdqlm_univar" / "q=05" / "logs" / "univar_legacy.log"
    univar_tail = tail_text(univar_q05_log)
    if "Error" in univar_tail or "Execution halted" in univar_tail:
        return "FAIL", univar_tail.splitlines()[-1]

    if fit_stage_log.exists():
        return "INCOMPLETE", "fit started but no report summary yet"
    return "NOT_STARTED", "run_root has no fit/report evidence yet"


def inspect_template(path: Path) -> dict[str, str]:
    template_cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    debug_cfg = template_cfg.get("debug_publication_replay") or {}
    campaign_cfg = template_cfg.get("campaign") or {}
    config_output_dir = Path(str(campaign_cfg["config_output_dir"])).resolve()
    generated_configs = sorted(config_output_dir.glob("*.yaml"))
    generated_cfg = yaml.safe_load(generated_configs[0].read_text(encoding="utf-8")) if generated_configs else {}
    run_cfg = generated_cfg.get("run") or {}
    run_root_parent = Path(str(run_cfg.get("run_root", ""))).resolve()
    run_id = str(run_cfg.get("run_id", ""))
    run_root = run_root_parent / run_id
    matrix_dir = Path(str(campaign_cfg["matrix_dir"])).resolve()
    status, note = classify_run(run_root, matrix_dir)
    return {
        "slug": path.stem.replace(".template", ""),
        "cutoff": str(debug_cfg.get("cutoff_display", debug_cfg.get("cutoff", ""))),
        "manuscript_label": str(debug_cfg.get("manuscript_label", "")),
        "campaign_lineage": str(debug_cfg.get("campaign_lineage", "")),
        "source_r_version": str(debug_cfg.get("source_r_version", "")),
        "runtime_profile": str(debug_cfg.get("source_runtime_profile", "")),
        "run_id": run_id,
        "run_root": str(run_root),
        "status": status,
        "note": note,
    }


def write_outputs(rows: list[dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "slug",
        "cutoff",
        "manuscript_label",
        "campaign_lineage",
        "source_r_version",
        "runtime_profile",
        "run_id",
        "run_root",
        "status",
        "note",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Publication Representative Replay Status",
        "",
        "| Slug | Cutoff | Label | Lineage | Source R | Runtime profile | Status | Note |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['slug']}` | {row['cutoff']} | `{row['manuscript_label']}` | "
            f"`{row['campaign_lineage']}` | `{row['source_r_version'] or 'unknown'}` | "
            f"`{row['runtime_profile']}` | {row['status']} | {row['note']} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    templates = sorted(CONFIG_DIR.glob("*.template.yaml"))
    if args.slugs:
        selected = set(args.slugs)
        templates = [path for path in templates if path.stem.replace(".template", "") in selected]
    if not templates:
        raise SystemExit("No representative replay templates selected.")
    rows = [inspect_template(path) for path in templates]
    write_outputs(rows)
    for row in rows:
        print(f"{row['slug']}: {row['status']} - {row['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
