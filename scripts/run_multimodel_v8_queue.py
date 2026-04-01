#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from multimodel_v8_lib import CUTOFFS, HEAVY_CUTOFF, ROOT, RUNS_DIR, matrix_report_dir, v8_compare_dir, v8_run_id

REQUIRED_COMPARE_FILES = {
    "crps_forecast_summary_all_models.csv",
    "crps_input_health_all_models.csv",
    "model_coverage.csv",
    "figure_manifest.csv",
    "source_provenance.csv",
    "summary.md",
}
PILOT_CUTOFF = "20211112"
PILOT_EPSILONS = ["epsTT", "eps30"]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


def stage_status(manifest_path: Path) -> tuple[str, str]:
    if not manifest_path.exists():
        return "not_started", "not_started"
    manifest = load_yaml(manifest_path)
    stages = manifest.get("stages", {}) if isinstance(manifest, dict) else {}
    for stage in ["forecats", "data_prep_shared", "fit", "post", "validate", "report"]:
        entry = stages.get(stage, {}) if isinstance(stages, dict) else {}
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "")).strip().lower()
        if status in {"pending", "fail"}:
            return stage, status
    report_entry = stages.get("report", {}) if isinstance(stages, dict) else {}
    status = str(report_entry.get("status", "")).strip().lower() if isinstance(report_entry, dict) else ""
    if status == "pass":
        return "report", "pass"
    return "unknown", status or "unknown"


def disk_free_gb() -> float:
    return round(shutil.disk_usage(ROOT).free / (1024 ** 3), 1)


def pgrep_active_v8() -> list[dict[str, str]]:
    proc = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True, text=True, check=True)
    rows_by_config: dict[str, dict[str, str]] = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # Real R invocations look like:
        #   R ... --file=scripts/unified_run.R --args --config <cfg>
        if "scripts/unified_run.R" not in line or "--config" not in line or "_v8_" not in line:
            continue
        m = re.match(r"^(\d+)\s+(.*)$", line)
        if not m:
            continue
        command = m.group(2)
        cfg_match = re.search(r"--config\s+(\S+multimodel_[^\s]+_v8_[^\s]+\.ya?ml)", command)
        config_key = cfg_match.group(1) if cfg_match else command
        rows_by_config.setdefault(config_key, {"pid": m.group(1), "command": command})
    return list(rows_by_config.values())


def manifest_path_for(run_id: str) -> Path:
    return RUNS_DIR / run_id / "run_manifest.yaml"


def compare_ready(cutoff: str, epsilon: str) -> bool:
    outdir = v8_compare_dir(cutoff, epsilon)
    return outdir.exists() and REQUIRED_COMPARE_FILES.issubset({p.name for p in outdir.iterdir() if p.is_file()})


def run_passed(run_id: str) -> bool:
    _phase, status = stage_status(manifest_path_for(run_id))
    return status == "pass"


def run_failed(run_id: str) -> bool:
    _phase, status = stage_status(manifest_path_for(run_id))
    return status == "fail"


def run_started(run_id: str) -> bool:
    return manifest_path_for(run_id).exists()


def build_compare_bundle(cutoff: str, epsilon: str, matrix_dir: Path, log_handle) -> None:
    baseline_l1 = v8_run_id(cutoff, "epsTT", "l1")
    baseline_l2 = v8_run_id(cutoff, "epsTT", "l2")
    cmd = [
        "python3",
        "scripts/build_multimodel_v8_compare_bundle.py",
        "--cutoff", cutoff,
        "--epsilon", epsilon,
        "--baseline-l1-run", baseline_l1,
        "--baseline-l2-run", baseline_l2,
        "--outdir", str(v8_compare_dir(cutoff, epsilon)),
    ]
    if epsilon != "epsTT":
        cmd.extend(["--mv-l1-run", v8_run_id(cutoff, epsilon, "l1_mv")])
        cmd.extend(["--mv-l2-run", v8_run_id(cutoff, epsilon, "l2_mv")])
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=log_handle, stderr=subprocess.STDOUT)


def maybe_build_compares(cells: list[tuple[str, str]], matrix_dir: Path, log_handle) -> None:
    for cutoff, epsilon in cells:
        if compare_ready(cutoff, epsilon):
            continue
        required_runs = [v8_run_id(cutoff, "epsTT", "l1"), v8_run_id(cutoff, "epsTT", "l2")]
        if epsilon != "epsTT":
            required_runs.extend([v8_run_id(cutoff, epsilon, "l1_mv"), v8_run_id(cutoff, epsilon, "l2_mv")])
        if all(run_passed(run_id) for run_id in required_runs):
            print(f"[{utc_now()}] building compare bundle cutoff={cutoff} epsilon={epsilon}", file=log_handle, flush=True)
            build_compare_bundle(cutoff, epsilon, matrix_dir, log_handle)


def write_pilot_summary(matrix_dir: Path) -> None:
    tt_dir = v8_compare_dir(PILOT_CUTOFF, "epsTT")
    eps30_dir = v8_compare_dir(PILOT_CUTOFF, "eps30")
    tt_cov = pd.read_csv(tt_dir / "model_coverage.csv")
    eps_cov = pd.read_csv(eps30_dir / "model_coverage.csv")
    eps_prov = pd.read_csv(eps30_dir / "source_provenance.csv")
    tt_crps = pd.read_csv(tt_dir / "crps_forecast_summary_all_models.csv")
    eps_crps = pd.read_csv(eps30_dir / "crps_forecast_summary_all_models.csv")
    merged = tt_crps[["model_id", "mean_crps"]].merge(
        eps_crps[["model_id", "mean_crps"]], on="model_id", suffixes=("_tt", "_eps30")
    )
    mv = merged.loc[merged["model_id"].str.contains("multivar")].copy()
    mv["abs_diff"] = (mv["mean_crps_tt"] - mv["mean_crps_eps30"]).abs()
    differing = mv.loc[mv["abs_diff"] > 1e-12, "model_id"].tolist()
    inv_source_ok = all(
        eps_prov.loc[~eps_prov["model_id"].str.contains("multivar"), "source_type"] == "baseline_tt"
    )
    mv_source_ok = all(
        eps_prov.loc[eps_prov["model_id"].str.contains("multivar"), "source_type"] == "epsilon_specific_mv"
    )
    lines = [
        "# v8 pilot summary",
        "",
        f"- Cutoff: `{PILOT_CUTOFF}`",
        f"- TT bundle exported models: {int((tt_cov['export_status'] == 'exported').sum())}/9",
        f"- eps30 bundle exported models: {int((eps_cov['export_status'] == 'exported').sum())}/9",
        f"- Invariant rows sourced from TT baseline: `{inv_source_ok}`",
        f"- Multivariate rows sourced from eps30 mv lanes: `{mv_source_ok}`",
        f"- Multivariate rows differing between TT and eps30: `{', '.join(differing) if differing else 'none'}`",
        "",
        "## Mean CRPS deltas for multivariate rows",
    ]
    for _, row in mv.sort_values("model_id").iterrows():
        lines.append(
            f"- `{row['model_id']}`: TT={float(row['mean_crps_tt']):.6f}, eps30={float(row['mean_crps_eps30']):.6f}, abs_diff={float(row['abs_diff']):.6f}"
        )
    (matrix_dir / "pilot_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_final_summary(matrix_dir: Path, cells: list[tuple[str, str]]) -> None:
    built = [f"multimodel_{cutoff}_v8_{epsilon}_compare" for cutoff, epsilon in cells if compare_ready(cutoff, epsilon)]
    lines = [
        "# v8 matrix summary",
        "",
        f"- Generated: {utc_now()}",
        f"- Compare bundles built: {len(built)}/{len(cells)}",
    ]
    for name in built:
        lines.append(f"- `{name}`")
    (matrix_dir / "final_matrix_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def launch_allowed(candidate: pd.Series, active: list[dict[str, str]], free_gb: float, ordinary_max_concurrent: int, pause_free_gb: float, launch_free_gb: float, heavy_free_gb: float) -> tuple[bool, str]:
    if free_gb < pause_free_gb:
        return False, f"paused: free_gb={free_gb} below pause threshold {pause_free_gb}"
    active_count = len(active)
    active_heavy = any(f"multimodel_{HEAVY_CUTOFF}_v8_" in row["command"] for row in active)
    if candidate["cutoff"] == HEAVY_CUTOFF:
        if active_count > 0:
            return False, "heavy cutoff waits until no other v8 lane is active"
        if free_gb <= heavy_free_gb:
            return False, f"heavy cutoff requires free_gb>{heavy_free_gb}, observed {free_gb}"
        return True, ""
    if active_heavy:
        return False, "ordinary cutoff waits while heavy cutoff is active"
    if active_count >= ordinary_max_concurrent:
        return False, f"active_count={active_count} reached ordinary concurrency limit {ordinary_max_concurrent}"
    if free_gb <= launch_free_gb:
        return False, f"ordinary lane requires free_gb>{launch_free_gb}, observed {free_gb}"
    return True, ""


def launch_run(config_path: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as handle:
        proc = subprocess.Popen(
            ["bash", "scripts/run_unified_with_cleanup.sh", "--config", str(config_path)],
            cwd=ROOT,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return proc.pid


def refresh_health(matrix_dir: Path, log_handle) -> None:
    subprocess.run(["python3", "scripts/check_multimodel_v8_matrix_health.py", "--matrix-dir", str(matrix_dir)], cwd=ROOT, stdout=log_handle, stderr=subprocess.STDOUT, check=True)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run disciplined v8 multimodel queue.")
    ap.add_argument("--matrix-dir", default=str(matrix_report_dir("20260401")))
    ap.add_argument("--pilot-only", action="store_true")
    ap.add_argument("--ordinary-max-concurrent", type=int, default=2)
    ap.add_argument("--pause-free-gb", type=float, default=180)
    ap.add_argument("--launch-free-gb", type=float, default=220)
    ap.add_argument("--heavy-free-gb", type=float, default=240)
    ap.add_argument("--poll-seconds", type=int, default=60)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    matrix_dir = Path(args.matrix_dir)
    plan = pd.read_csv(matrix_dir / "matrix_plan.csv")
    for col in ("cutoff", "epsilon", "lane", "run_id", "config_path"):
        if col in plan.columns:
            plan[col] = plan[col].astype(str)
    if "cutoff" in plan.columns:
        plan["cutoff"] = plan["cutoff"].str.zfill(8)
    if args.pilot_only:
        plan = plan.loc[(plan["cutoff"] == PILOT_CUTOFF) & (plan["epsilon"].isin(PILOT_EPSILONS))].copy()
        compare_cells = [(PILOT_CUTOFF, eps) for eps in PILOT_EPSILONS]
    else:
        compare_cells = [(cutoff, epsilon) for cutoff, _ in CUTOFFS for epsilon in ["epsTT", "eps30", "eps90", "eps180", "eps360"]]
    plan = plan.sort_values(["order_index", "lane"]).reset_index(drop=True)
    queue_log = matrix_dir / "queue.log"
    queue_log.parent.mkdir(parents=True, exist_ok=True)

    with queue_log.open("a", encoding="utf-8") as log_handle:
        print(f"[{utc_now()}] controller start pilot_only={args.pilot_only}", file=log_handle, flush=True)
        while True:
            refresh_health(matrix_dir, log_handle)
            maybe_build_compares(compare_cells, matrix_dir, log_handle)

            # Fail fast if any planned run failed.
            for _, row in plan.iterrows():
                if run_failed(str(row["run_id"])):
                    print(f"[{utc_now()}] aborting: run failed {row['run_id']}", file=log_handle, flush=True)
                    return 1

            all_runs_pass = all(run_passed(str(row["run_id"])) for _, row in plan.iterrows())
            all_compares_ready = all(compare_ready(cutoff, epsilon) for cutoff, epsilon in compare_cells)
            if all_runs_pass and all_compares_ready:
                if args.pilot_only:
                    write_pilot_summary(matrix_dir)
                write_final_summary(matrix_dir, compare_cells)
                print(f"[{utc_now()}] controller complete pilot_only={args.pilot_only}", file=log_handle, flush=True)
                return 0

            active = pgrep_active_v8()
            free_gb = disk_free_gb()
            launched = False
            for _, row in plan.iterrows():
                run_id = str(row["run_id"])
                phase, status = stage_status(manifest_path_for(run_id))
                if status == "pass":
                    continue
                if status == "pending":
                    continue
                if status == "fail":
                    continue
                allowed, note = launch_allowed(
                    candidate=row,
                    active=active,
                    free_gb=free_gb,
                    ordinary_max_concurrent=args.ordinary_max_concurrent,
                    pause_free_gb=args.pause_free_gb,
                    launch_free_gb=args.launch_free_gb,
                    heavy_free_gb=args.heavy_free_gb,
                )
                if not allowed:
                    continue
                log_path = matrix_dir / "run_logs" / f"{run_id}.log"
                pid = launch_run(Path(str(row["config_path"])), log_path)
                print(
                    f"[{utc_now()}] launched run_id={run_id} pid={pid} cutoff={row['cutoff']} epsilon={row['epsilon']} lane={row['lane']} free_gb={free_gb}",
                    file=log_handle,
                    flush=True,
                )
                launched = True
                break

            if not launched:
                print(f"[{utc_now()}] idle wait free_gb={free_gb} active={len(active)}", file=log_handle, flush=True)
            time.sleep(max(args.poll_seconds, 5))


if __name__ == "__main__":
    raise SystemExit(main())
