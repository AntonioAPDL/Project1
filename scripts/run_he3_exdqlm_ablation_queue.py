#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from he3_exdqlm_ablation_lib import HEAVY_CUTOFF, build_status_frame, write_status_markdown
from multimodel_v8_lib import ROOT, artifact_disk_free_gb, load_yaml


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def install_signal_logging(log_handle) -> None:
    def _handler(signum, _frame) -> None:
        signame = signal.Signals(signum).name if signum in signal.Signals else f"SIG{signum}"
        print(f"[{utc_now()}] controller signal signame={signame} signum={signum}", file=log_handle, flush=True)
        raise SystemExit(128 + int(signum))

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(sig, _handler)
        except Exception:
            continue


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run the HE3 exdqlm multivar ablation queue controller.")
    ap.add_argument("--matrix-dir", required=True)
    ap.add_argument("--artifact-root", required=True)
    ap.add_argument("--ordinary-max-concurrent", type=int, default=4)
    ap.add_argument("--heavy-cutoff-max-concurrent", type=int, default=1)
    ap.add_argument("--pause-free-gb", type=float, default=180.0)
    ap.add_argument("--launch-free-gb", type=float, default=220.0)
    ap.add_argument("--heavy-free-gb", type=float, default=240.0)
    ap.add_argument("--poll-seconds", type=int, default=60)
    return ap.parse_args()


def detect_active_run_ids(plan: pd.DataFrame) -> list[str]:
    run_ids = set(plan.loc[plan["launch_mode"] == "launch", "run_id"].astype(str))
    config_to_run_id = {
        str(Path(path).resolve()): str(run_id)
        for run_id, path in plan.loc[plan["launch_mode"] == "launch", ["run_id", "config_path"]].itertuples(index=False)
        if str(path).strip()
    }
    proc = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True, text=True, check=True)
    active: set[str] = set()
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if not line or "scripts/unified_run.R" not in line or "--config" not in line:
            continue
        cfg_match = re.search(r"--config\s+(\S+\.ya?ml)", line)
        if not cfg_match:
            continue
        cfg_path = str(Path(cfg_match.group(1)).resolve())
        run_id = config_to_run_id.get(cfg_path)
        if run_id in run_ids:
            active.add(run_id)
    return sorted(active)


def launch_run(config_path: Path, log_handle) -> int:
    cmd = [
        "bash",
        "-lc",
        f"cd {ROOT} && scripts/run_unified_with_cleanup.sh --config {config_path}",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(
        f"[{utc_now()}] launch pid={proc.pid} config={config_path}",
        file=log_handle,
        flush=True,
    )
    return int(proc.pid)


def refresh_status(matrix_dir: Path, artifact_root: Path, plan: pd.DataFrame) -> pd.DataFrame:
    status = build_status_frame(plan, artifact_root)
    status.to_csv(matrix_dir / "matrix_status.csv", index=False)
    write_status_markdown(status, matrix_dir / "matrix_status.md")
    return status


def run_completion_cmd(cmd: list[str], log_handle) -> None:
    print(f"[{utc_now()}] completion cmd={' '.join(cmd)}", file=log_handle, flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=log_handle, stderr=subprocess.STDOUT)


def maybe_complete(matrix_dir: Path, log_handle) -> None:
    summary_cmd = [
        "python3",
        "scripts/build_he3_exdqlm_ablation_summary.py",
        "--matrix-dir",
        str(matrix_dir),
    ]
    run_completion_cmd(summary_cmd, log_handle)

    audit_cmd = [
        "python3",
        "scripts/audit_he3_exdqlm_ablation.py",
        "--matrix-dir",
        str(matrix_dir),
    ]
    run_completion_cmd(audit_cmd, log_handle)

    metadata = load_yaml(matrix_dir / "matrix_metadata.yaml")
    article_sync = metadata.get("article_sync", {}) if isinstance(metadata, dict) else {}
    if isinstance(article_sync, dict) and bool(article_sync.get("enabled", False)):
        sync_cmd = [
            "python3",
            "scripts/sync_he3_ablation_article_tables.py",
            "--matrix-dir",
            str(matrix_dir),
        ]
        article_root = str(article_sync.get("article_root", "")).strip()
        corrections_root = str(article_sync.get("corrections_root", "")).strip()
        if article_root:
            sync_cmd.extend(["--article-root", article_root])
        if corrections_root:
            sync_cmd.extend(["--corrections-root", corrections_root])
        run_completion_cmd(sync_cmd, log_handle)


def main() -> int:
    args = parse_args()
    matrix_dir = Path(args.matrix_dir).resolve()
    artifact_root = Path(args.artifact_root).resolve()
    plan = pd.read_csv(matrix_dir / "matrix_plan.csv")
    plan["cutoff"] = plan["cutoff"].astype(str).str.zfill(8)
    log_path = matrix_dir / "queue.log"
    orphan_streak: dict[str, int] = {}

    with log_path.open("a", encoding="utf-8") as log_handle:
        install_signal_logging(log_handle)
        print(
            f"[{utc_now()}] controller start matrix_dir={matrix_dir} artifact_root={artifact_root}",
            file=log_handle,
            flush=True,
        )
        try:
            while True:
                status = refresh_status(matrix_dir, artifact_root, plan)
                launch_rows = plan.merge(
                    status.loc[:, ["run_id", "variant", "status", "phase"]],
                    on=["run_id", "variant"],
                    how="left",
                )
                launch_rows = launch_rows[launch_rows["launch_mode"] == "launch"].copy()
                active_run_ids = detect_active_run_ids(plan)
                counts = status["status"].value_counts().to_dict()
                free_gb = artifact_disk_free_gb(artifact_root)

                pending_rows = launch_rows[launch_rows["status"] == "pending"].copy()
                orphan_pending = sorted(set(pending_rows["run_id"].astype(str)) - set(active_run_ids))
                for run_id in list(orphan_streak):
                    if run_id not in orphan_pending:
                        orphan_streak.pop(run_id, None)
                for run_id in orphan_pending:
                    orphan_streak[run_id] = orphan_streak.get(run_id, 0) + 1
                persistent_orphans = sorted(run_id for run_id, streak in orphan_streak.items() if streak >= 2)
                if persistent_orphans:
                    raise RuntimeError(f"Orphan pending HE3 rows detected: {persistent_orphans}")

                if any(status["status"] == "fail"):
                    failed = status[status["status"] == "fail"]["run_id"].astype(str).tolist()
                    raise RuntimeError(f"HE3 queue aborting because rows failed: {failed}")

                incomplete_launch = launch_rows[launch_rows["status"] != "pass"].copy()
                if incomplete_launch.empty and not active_run_ids:
                    print(f"[{utc_now()}] controller complete", file=log_handle, flush=True)
                    maybe_complete(matrix_dir, log_handle)
                    return 0

                active_total = len(active_run_ids)
                active_heavy = int(
                    launch_rows[
                        launch_rows["run_id"].astype(str).isin(active_run_ids) & (launch_rows["cutoff"] == HEAVY_CUTOFF)
                    ].shape[0]
                )
                current_group = int(incomplete_launch["order_group"].min()) if not incomplete_launch.empty else -1
                eligible = incomplete_launch[
                    (incomplete_launch["order_group"] == current_group) & (incomplete_launch["status"] == "not_started")
                ].sort_values("order_index")

                print(
                    f"[{utc_now()}] heartbeat pass={int(counts.get('pass', 0))} pending={int(counts.get('pending', 0))} "
                    f"not_started={int(counts.get('not_started', 0))} active={active_total} current_group={current_group} "
                    f"free_gb={free_gb:.1f}",
                    file=log_handle,
                    flush=True,
                )

                if free_gb >= args.pause_free_gb and active_total < args.ordinary_max_concurrent:
                    launch_budget = args.ordinary_max_concurrent - active_total
                    launched_any = False
                    for _, row in eligible.iterrows():
                        if launch_budget <= 0:
                            break
                        if row["cutoff"] == HEAVY_CUTOFF:
                            if active_heavy >= args.heavy_cutoff_max_concurrent:
                                continue
                            if free_gb < args.heavy_free_gb:
                                continue
                        elif free_gb < args.launch_free_gb:
                            break
                        config_path = Path(str(row["config_path"]))
                        launch_run(config_path, log_handle)
                        launched_any = True
                        launch_budget -= 1
                        if row["cutoff"] == HEAVY_CUTOFF:
                            active_heavy += 1
                    if launched_any:
                        time.sleep(2)
                        continue

                time.sleep(max(5, args.poll_seconds))
        except SystemExit:
            raise
        except Exception as exc:
            print(f"[{utc_now()}] controller error: {exc}", file=log_handle, flush=True)
            traceback.print_exc(file=log_handle)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
