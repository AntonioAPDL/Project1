#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import signal
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from multimodel_v8_lib import (
    CUTOFFS,
    HEAVY_CUTOFF,
    ROOT,
    artifact_disk_free_gb,
    control_dir,
    load_yaml,
    matrix_report_dir,
    resolve_artifact_root,
    runs_dir,
    v8_compare_dir,
    v8_run_id,
)

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


def install_signal_logging(log_handle) -> None:
    def _handler(signum, _frame) -> None:
        try:
            signame = signal.Signals(signum).name
        except Exception:
            signame = f"SIG{signum}"
        print(
            f"[{utc_now()}] controller signal signame={signame} signum={signum}",
            file=log_handle,
            flush=True,
        )
        raise SystemExit(128 + int(signum))

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(sig, _handler)
        except Exception:
            continue


def stage_status(manifest_path: Path) -> tuple[str, str]:
    if not manifest_path.exists():
        return "not_started", "not_started"
    try:
        manifest = load_yaml(manifest_path)
    except Exception:
        return "manifest", "pending"
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


def disk_free_gb(artifact_root: str | Path | None = None) -> float:
    return artifact_disk_free_gb(artifact_root)


def memory_available_gb() -> float | None:
    """Return MemAvailable from /proc/meminfo when available."""
    meminfo = Path("/proc/meminfo")
    try:
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                parts = line.split()
                if len(parts) >= 2:
                    return float(parts[1]) / 1024.0 / 1024.0
    except Exception:
        return None
    return None


def pgrep_active_v8(artifact_root: str | Path | None = None) -> list[dict[str, str]]:
    proc = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True, text=True, check=True)
    rows_by_config: dict[str, dict[str, str]] = {}
    artifact_root_str = str(Path(artifact_root).resolve()) if artifact_root is not None else None
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
        if artifact_root_str is not None:
            try:
                resolved_cfg = str(Path(config_key).resolve())
            except Exception:
                resolved_cfg = config_key
            if not resolved_cfg.startswith(artifact_root_str + os.sep):
                continue
        rows_by_config.setdefault(config_key, {"pid": m.group(1), "command": command})
    return list(rows_by_config.values())


def manifest_path_for(run_id: str, artifact_root: str | Path | None = None) -> Path:
    return runs_dir(artifact_root) / run_id / "run_manifest.yaml"


def load_matrix_metadata(matrix_dir: Path) -> dict[str, Any]:
    path = matrix_dir / "matrix_metadata.yaml"
    if not path.exists():
        return {}
    try:
        data = load_yaml(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def compare_ready(cutoff: str, epsilon: str, artifact_root: str | Path | None = None) -> bool:
    outdir = v8_compare_dir(cutoff, epsilon, artifact_root)
    return outdir.exists() and REQUIRED_COMPARE_FILES.issubset({p.name for p in outdir.iterdir() if p.is_file()})


def run_passed(run_id: str, artifact_root: str | Path | None = None) -> bool:
    _phase, status = stage_status(manifest_path_for(run_id, artifact_root))
    return status == "pass"


def run_failed(run_id: str, artifact_root: str | Path | None = None) -> bool:
    _phase, status = stage_status(manifest_path_for(run_id, artifact_root))
    return status == "fail"


def run_terminal_for_matrix(run_id: str, artifact_root: str | Path | None = None, continue_on_fail: bool = False) -> bool:
    _phase, status = stage_status(manifest_path_for(run_id, artifact_root))
    return status == "pass" or (continue_on_fail and status == "fail")


def run_started(run_id: str, artifact_root: str | Path | None = None) -> bool:
    return manifest_path_for(run_id, artifact_root).exists()


def build_compare_bundle(
    cutoff: str,
    epsilon: str,
    matrix_dir: Path,
    log_handle,
    artifact_root: str | Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    metadata = metadata or {}
    compare_builder = str(metadata.get("compare_builder", "") or "").strip()
    if compare_builder:
        builder_path = Path(compare_builder)
        if not builder_path.is_absolute():
            builder_path = ROOT / builder_path
        cmd = [
            "python3",
            str(builder_path),
            "--cutoff",
            cutoff,
            "--epsilon",
            epsilon,
            "--matrix-dir",
            str(matrix_dir),
            "--outdir",
            str(v8_compare_dir(cutoff, epsilon, artifact_root)),
        ]
        if artifact_root is not None:
            cmd.extend(["--artifact-root", str(artifact_root)])
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=log_handle, stderr=subprocess.STDOUT)
        return

    baseline_l1 = v8_run_id(cutoff, "epsTT", "l1")
    baseline_l2 = v8_run_id(cutoff, "epsTT", "l2")
    cmd = [
        "python3",
        "scripts/build_multimodel_v8_compare_bundle.py",
        "--cutoff", cutoff,
        "--epsilon", epsilon,
        "--baseline-l1-run", baseline_l1,
        "--baseline-l2-run", baseline_l2,
        "--outdir", str(v8_compare_dir(cutoff, epsilon, artifact_root)),
    ]
    if artifact_root is not None:
        cmd.extend(["--artifact-root", str(artifact_root)])
    if epsilon != "epsTT":
        cmd.extend(["--mv-l1-run", v8_run_id(cutoff, epsilon, "l1_mv")])
        cmd.extend(["--mv-l2-run", v8_run_id(cutoff, epsilon, "l2_mv")])
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=log_handle, stderr=subprocess.STDOUT)


def compare_cells_from_plan(plan: pd.DataFrame) -> list[tuple[str, str]]:
    ordered = plan.sort_values(["order_index", "lane"]).loc[:, ["cutoff", "epsilon"]].drop_duplicates()
    return [(str(row["cutoff"]), str(row["epsilon"])) for _, row in ordered.iterrows()]


def maybe_build_compares(
    cells: list[tuple[str, str]],
    plan: pd.DataFrame,
    matrix_dir: Path,
    log_handle,
    artifact_root: str | Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    for cutoff, epsilon in cells:
        if compare_ready(cutoff, epsilon, artifact_root):
            continue
        cell_plan = plan.loc[(plan["cutoff"] == cutoff) & (plan["epsilon"] == epsilon)].copy()
        required_runs = [str(run_id) for run_id in cell_plan["run_id"].astype(str).tolist()]
        if len(required_runs) < 1:
            continue
        if all(run_passed(run_id, artifact_root) for run_id in required_runs):
            print(f"[{utc_now()}] building compare bundle cutoff={cutoff} epsilon={epsilon}", file=log_handle, flush=True)
            build_compare_bundle(
                cutoff,
                epsilon,
                matrix_dir,
                log_handle,
                artifact_root,
                metadata=metadata,
            )


def write_pilot_summary(matrix_dir: Path, artifact_root: str | Path | None = None) -> None:
    tt_dir = v8_compare_dir(PILOT_CUTOFF, "epsTT", artifact_root)
    eps30_dir = v8_compare_dir(PILOT_CUTOFF, "eps30", artifact_root)
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


def write_final_summary(matrix_dir: Path, cells: list[tuple[str, str]], artifact_root: str | Path | None = None) -> None:
    built = [f"multimodel_{cutoff}_v8_{epsilon}_compare" for cutoff, epsilon in cells if compare_ready(cutoff, epsilon, artifact_root)]
    lines = [
        "# v8 matrix summary",
        "",
        f"- Generated: {utc_now()}",
        f"- Compare bundles built: {len(built)}/{len(cells)}",
    ]
    for name in built:
        lines.append(f"- `{name}`")
    (matrix_dir / "final_matrix_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def launch_allowed(
    candidate: pd.Series,
    active: list[dict[str, str]],
    free_gb: float,
    ordinary_max_concurrent: int,
    pause_free_gb: float,
    launch_free_gb: float,
    heavy_free_gb: float,
    heavy_cutoff_max_concurrent: int = 1,
    heavy_cutoff_blocks_ordinary: bool = True,
    mem_available_gb: float | None = None,
    pause_mem_gb: float = 0.0,
    launch_mem_gb: float = 0.0,
    heavy_mem_gb: float | None = None,
) -> tuple[bool, str]:
    if free_gb < pause_free_gb:
        return False, f"paused: free_gb={free_gb} below pause threshold {pause_free_gb}"
    if mem_available_gb is not None and pause_mem_gb > 0 and mem_available_gb < pause_mem_gb:
        return False, f"paused: mem_available_gb={mem_available_gb} below pause threshold {pause_mem_gb}"
    active_count = len(active)
    active_heavy_count = sum(1 for row in active if f"multimodel_{HEAVY_CUTOFF}_v8_" in row["command"])
    heavy_required_mem_gb = launch_mem_gb if heavy_mem_gb is None else heavy_mem_gb
    if candidate["cutoff"] == HEAVY_CUTOFF:
        active_ordinary_count = active_count - active_heavy_count
        if heavy_cutoff_blocks_ordinary and active_ordinary_count > 0:
            return False, "heavy cutoff waits until no ordinary v8 lane is active"
        if active_count >= ordinary_max_concurrent:
            return False, f"active_count={active_count} reached ordinary concurrency limit {ordinary_max_concurrent}"
        if active_heavy_count >= heavy_cutoff_max_concurrent:
            return False, f"heavy cutoff reached concurrency limit {heavy_cutoff_max_concurrent}"
        if free_gb <= heavy_free_gb:
            return False, f"heavy cutoff requires free_gb>{heavy_free_gb}, observed {free_gb}"
        if mem_available_gb is not None and heavy_required_mem_gb > 0 and mem_available_gb <= heavy_required_mem_gb:
            return False, f"heavy cutoff requires mem_available_gb>{heavy_required_mem_gb}, observed {mem_available_gb}"
        return True, ""
    if heavy_cutoff_blocks_ordinary and active_heavy_count > 0:
        return False, "ordinary cutoff waits while heavy cutoff is active"
    if active_count >= ordinary_max_concurrent:
        return False, f"active_count={active_count} reached ordinary concurrency limit {ordinary_max_concurrent}"
    if free_gb <= launch_free_gb:
        return False, f"ordinary lane requires free_gb>{launch_free_gb}, observed {free_gb}"
    if mem_available_gb is not None and launch_mem_gb > 0 and mem_available_gb <= launch_mem_gb:
        return False, f"ordinary lane requires mem_available_gb>{launch_mem_gb}, observed {mem_available_gb}"
    return True, ""


def launch_run(config_path: Path, log_path: Path, cleanup_rdata_after_post: bool = True) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    runner = "scripts/run_unified_with_cleanup.sh" if cleanup_rdata_after_post else "scripts/run_unified_without_cleanup.sh"
    with log_path.open("ab") as handle:
        proc = subprocess.Popen(
            ["bash", runner, "--config", str(config_path)],
            cwd=ROOT,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return proc.pid


def refresh_health(matrix_dir: Path, log_handle, artifact_root: str | Path | None = None) -> None:
    cmd = ["python3", "scripts/check_multimodel_v8_matrix_health.py", "--matrix-dir", str(matrix_dir)]
    if artifact_root is not None:
        cmd.extend(["--artifact-root", str(artifact_root)])
    completed = subprocess.run(cmd, cwd=ROOT, stdout=log_handle, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0:
        print(
            f"[{utc_now()}] health refresh warning returncode={completed.returncode}; continuing queue loop",
            file=log_handle,
            flush=True,
        )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run disciplined v8 multimodel queue.")
    ap.add_argument("--matrix-dir")
    ap.add_argument("--artifact-root")
    ap.add_argument("--pilot-only", action="store_true")
    ap.add_argument("--ordinary-max-concurrent", type=int, default=2)
    ap.add_argument("--pause-free-gb", type=float, default=180)
    ap.add_argument("--launch-free-gb", type=float, default=220)
    ap.add_argument("--heavy-free-gb", type=float, default=240)
    ap.add_argument("--pause-mem-gb", type=float, default=0.0)
    ap.add_argument("--launch-mem-gb", type=float, default=0.0)
    ap.add_argument("--heavy-mem-gb", type=float, default=None)
    ap.add_argument("--heavy-cutoff-max-concurrent", type=int, default=1)
    ap.add_argument("--no-heavy-cutoff-blocks-ordinary", action="store_true")
    ap.add_argument("--continue-on-fail", action="store_true")
    ap.add_argument("--skip-compares", action="store_true")
    ap.add_argument("--no-cleanup", action="store_true", help="Retain .RData after post by using run_unified_without_cleanup.sh.")
    ap.add_argument("--poll-seconds", type=int, default=60)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    artifact_root = resolve_artifact_root(args.artifact_root)
    matrix_dir = Path(args.matrix_dir) if args.matrix_dir else (control_dir(artifact_root) if args.artifact_root else matrix_report_dir("20260401"))
    plan = pd.read_csv(matrix_dir / "matrix_plan.csv")
    for col in ("cutoff", "epsilon", "lane", "run_id", "config_path"):
        if col in plan.columns:
            plan[col] = plan[col].astype(str)
    if "cutoff" in plan.columns:
        plan["cutoff"] = plan["cutoff"].str.zfill(8)
    if args.pilot_only:
        plan = plan.loc[(plan["cutoff"] == PILOT_CUTOFF) & (plan["epsilon"].isin(PILOT_EPSILONS))].copy()
        compare_cells = compare_cells_from_plan(plan)
    elif args.skip_compares:
        compare_cells = []
    else:
        compare_cells = compare_cells_from_plan(plan)
    plan = plan.sort_values(["order_index", "lane"]).reset_index(drop=True)
    queue_log = matrix_dir / "queue.log"
    queue_log.parent.mkdir(parents=True, exist_ok=True)

    with queue_log.open("a", encoding="utf-8") as log_handle:
        install_signal_logging(log_handle)
        print(
            f"[{utc_now()}] controller start pilot_only={args.pilot_only} artifact_root={artifact_root} "
            f"cleanup_rdata_after_post={not args.no_cleanup}",
            file=log_handle,
            flush=True,
        )
        metadata = load_matrix_metadata(matrix_dir)
        exit_code = 0
        try:
            while True:
                refresh_health(matrix_dir, log_handle, artifact_root if args.artifact_root else None)
                if not args.skip_compares:
                    maybe_build_compares(
                        compare_cells,
                        plan,
                        matrix_dir,
                        log_handle,
                        artifact_root if args.artifact_root else None,
                        metadata=metadata,
                    )

                for _, row in plan.iterrows():
                    if (not args.continue_on_fail) and run_failed(str(row["run_id"]), artifact_root if args.artifact_root else None):
                        print(f"[{utc_now()}] aborting: run failed {row['run_id']}", file=log_handle, flush=True)
                        exit_code = 1
                        return exit_code

                all_runs_terminal = all(
                    run_terminal_for_matrix(
                        str(row["run_id"]),
                        artifact_root if args.artifact_root else None,
                        continue_on_fail=args.continue_on_fail,
                    )
                    for _, row in plan.iterrows()
                )
                all_compares_ready = args.skip_compares or all(
                    compare_ready(cutoff, epsilon, artifact_root if args.artifact_root else None)
                    for cutoff, epsilon in compare_cells
                )
                if all_runs_terminal and all_compares_ready:
                    if args.pilot_only:
                        write_pilot_summary(matrix_dir, artifact_root if args.artifact_root else None)
                    write_final_summary(matrix_dir, compare_cells, artifact_root if args.artifact_root else None)
                    print(f"[{utc_now()}] controller complete pilot_only={args.pilot_only}", file=log_handle, flush=True)
                    exit_code = 0
                    return exit_code

                active = pgrep_active_v8(artifact_root if args.artifact_root else None)
                free_gb = disk_free_gb(artifact_root if args.artifact_root else None)
                mem_gb = memory_available_gb()
                launched = False
                for _, row in plan.iterrows():
                    run_id = str(row["run_id"])
                    _phase, status = stage_status(manifest_path_for(run_id, artifact_root if args.artifact_root else None))
                    if status == "pass":
                        continue
                    if status == "pending":
                        continue
                    if status == "fail":
                        continue
                    allowed, _note = launch_allowed(
                        candidate=row,
                        active=active,
                        free_gb=free_gb,
                        ordinary_max_concurrent=args.ordinary_max_concurrent,
                        pause_free_gb=args.pause_free_gb,
                        launch_free_gb=args.launch_free_gb,
                        heavy_free_gb=args.heavy_free_gb,
                        heavy_cutoff_max_concurrent=args.heavy_cutoff_max_concurrent,
                        heavy_cutoff_blocks_ordinary=not args.no_heavy_cutoff_blocks_ordinary,
                        mem_available_gb=mem_gb,
                        pause_mem_gb=args.pause_mem_gb,
                        launch_mem_gb=args.launch_mem_gb,
                        heavy_mem_gb=args.heavy_mem_gb,
                    )
                    if not allowed:
                        continue
                    log_path = matrix_dir / "run_logs" / f"{run_id}.log"
                    pid = launch_run(
                        Path(str(row["config_path"])),
                        log_path,
                        cleanup_rdata_after_post=not args.no_cleanup,
                    )
                    print(
                        f"[{utc_now()}] launched run_id={run_id} pid={pid} cutoff={row['cutoff']} epsilon={row['epsilon']} lane={row['lane']} free_gb={free_gb} mem_available_gb={mem_gb}",
                        file=log_handle,
                        flush=True,
                    )
                    launched = True
                    break

                if not launched:
                    print(f"[{utc_now()}] idle wait free_gb={free_gb} mem_available_gb={mem_gb} active={len(active)}", file=log_handle, flush=True)
                time.sleep(max(args.poll_seconds, 5))
        except KeyboardInterrupt:
            exit_code = 130
            print(f"[{utc_now()}] controller interrupted", file=log_handle, flush=True)
        except SystemExit as exc:
            code = exc.code
            exit_code = int(code) if isinstance(code, int) else 1
            print(f"[{utc_now()}] controller exit requested code={exit_code}", file=log_handle, flush=True)
        except Exception as exc:
            exit_code = 1
            print(
                f"[{utc_now()}] controller exception type={type(exc).__name__} message={exc}",
                file=log_handle,
                flush=True,
            )
            traceback.print_exc(file=log_handle)
        finally:
            print(f"[{utc_now()}] controller stop exit_code={exit_code}", file=log_handle, flush=True)
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
