#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

import yaml

from build_publication_replay_representative_bundle import (
    LINEAGE_SPECS,
    OUT_CONFIG_DIR,
    REPO_ROOT,
    build_template,
    load_matrix_rows,
    slug_for_row,
)


def read_launch_settings(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        settings[key.strip()] = value.strip()
    return settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build, validate, and optionally detached-launch the publication representative replay rows."
    )
    parser.add_argument("--slugs", nargs="*", help="Subset of representative replay slugs to process.")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run_cmd(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def patch_generated_run_configs(config_output_dir: Path) -> None:
    for path in sorted(config_output_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle) or {}
        run_cfg = cfg.setdefault("run", {})
        run_cfg["overwrite"] = True
        run_cfg["auto_suffix_on_collision"] = False
        run_cfg["git_require_clean"] = False
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(cfg, handle, sort_keys=False)


def queue_cmd_from_config(template_path: Path) -> tuple[Path, Path, list[str]]:
    with template_path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    campaign = cfg.get("campaign", {}) if isinstance(cfg.get("campaign"), dict) else {}
    matrix_dir = Path(str(campaign["matrix_dir"])).resolve()
    artifact_root = Path(str(campaign["artifact_root"])).resolve()
    launch_settings = read_launch_settings(matrix_dir / "launch_settings.env")
    cmd = [
        "python3",
        "scripts/run_multimodel_v8_queue.py",
        "--matrix-dir",
        str(matrix_dir),
        "--artifact-root",
        str(artifact_root),
        "--ordinary-max-concurrent",
        launch_settings["ORDINARY_MAX_CONCURRENT"],
        "--pause-free-gb",
        launch_settings["PAUSE_FREE_GB"],
        "--launch-free-gb",
        launch_settings["LAUNCH_FREE_GB"],
        "--heavy-free-gb",
        launch_settings["HEAVY_FREE_GB"],
        "--poll-seconds",
        launch_settings["POLL_SECONDS"],
    ]
    if "HEAVY_CUTOFF_MAX_CONCURRENT" in launch_settings:
        cmd.extend(["--heavy-cutoff-max-concurrent", launch_settings["HEAVY_CUTOFF_MAX_CONCURRENT"]])
    if launch_settings.get("HEAVY_CUTOFF_BLOCKS_ORDINARY", "1") in {"0", "false", "False", "no"}:
        cmd.append("--no-heavy-cutoff-blocks-ordinary")
    return matrix_dir, artifact_root, cmd


def generated_config_from_template(template_path: Path) -> Path:
    with template_path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    config_output_dir = Path(str(cfg["campaign"]["config_output_dir"])).resolve()
    generated = sorted(config_output_dir.glob("*.yaml"))
    if len(generated) != 1:
        raise SystemExit(f"Expected exactly one generated config under {config_output_dir}, found {len(generated)}")
    return generated[0]


def is_controller_active(matrix_dir: Path) -> bool:
    pid_path = matrix_dir / "controller_state" / "controller.pid"
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def is_pid_active(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def terminate_pids(pids: set[int], grace_seconds: float = 2.0) -> list[int]:
    stopped: list[int] = []
    for pid in sorted(pids):
        if pid == os.getpid():
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            stopped.append(pid)
        except OSError:
            continue
    if not stopped:
        return stopped
    time.sleep(grace_seconds)
    for pid in stopped:
        if not is_pid_active(pid):
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            continue
    time.sleep(1)
    return stopped


def runtime_profile_for_template(template_path: Path) -> str:
    with template_path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    debug_cfg = cfg.get("debug_publication_replay") or {}
    return str(debug_cfg.get("source_runtime_profile", "system_r"))


def direct_cmd_for_config(config_path: Path, runtime_profile: str) -> list[str]:
    if runtime_profile == "authoritative_r440":
        return ["bash", "scripts/run_authoritative_r440_replay.sh", str(config_path)]
    return ["Rscript", "--vanilla", "scripts/unified_run.R", "--config", str(config_path)]


def direct_state_dir(matrix_dir: Path) -> Path:
    state_dir = matrix_dir / "controller_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def direct_log_path(matrix_dir: Path) -> Path:
    return matrix_dir / "direct_launch.log"


def cleanup_stale_controller_state(matrix_dir: Path) -> None:
    state_dir = matrix_dir / "controller_state"
    pid_path = state_dir / "controller.pid"
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = None
        if pid is not None and not is_pid_active(pid):
            pid_path.unlink(missing_ok=True)
            (state_dir / "last_launch.json").unlink(missing_ok=True)


def stop_active_queue_controller(matrix_dir: Path) -> int | None:
    state_dir = matrix_dir / "controller_state"
    pid_path = state_dir / "controller.pid"
    if not pid_path.exists():
        return None
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        pid_path.unlink(missing_ok=True)
        return None
    if not is_pid_active(pid):
        pid_path.unlink(missing_ok=True)
        (state_dir / "last_launch.json").unlink(missing_ok=True)
        return None
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pid_path.unlink(missing_ok=True)
        return None
    time.sleep(2)
    if not is_pid_active(pid):
        pid_path.unlink(missing_ok=True)
        (state_dir / "last_launch.json").unlink(missing_ok=True)
    return pid


def stop_existing_replay_processes(config_path: Path) -> list[int]:
    run_root = None
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle) or {}
        run_cfg = cfg.get("run") or {}
        root_parent = Path(str(run_cfg.get("run_root", ""))).resolve()
        run_id = str(run_cfg.get("run_id", ""))
        if run_id:
            run_root = str((root_parent / run_id).resolve())
    except Exception:
        run_root = None

    patterns = [str(config_path)]
    if run_root:
        patterns.append(run_root)

    seen: set[int] = set()
    for pattern in patterns:
        proc = subprocess.run(
            ["pgrep", "-f", pattern],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        for raw in proc.stdout.split():
            try:
                pid = int(raw)
            except ValueError:
                continue
            if pid == os.getpid() or pid in seen:
                continue
            seen.add(pid)
    return terminate_pids(seen)


def launch_detached(matrix_dir: Path, artifact_root: Path, queue_cmd: list[str]) -> int:
    if is_controller_active(matrix_dir):
        raise SystemExit(f"Controller already active for matrix_dir={matrix_dir}")
    log_path = matrix_dir / "queue.log"
    log_handle = log_path.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        queue_cmd,
        cwd=REPO_ROOT,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    time.sleep(2)
    state_dir = matrix_dir / "controller_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "controller.pid").write_text(f"{proc.pid}\n", encoding="utf-8")
    (state_dir / "last_launch.json").write_text(
        json.dumps(
            {
                "pid": proc.pid,
                "queue_cmd": queue_cmd,
                "matrix_dir": str(matrix_dir),
                "artifact_root": str(artifact_root),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return proc.pid


def launch_direct_detached(matrix_dir: Path, config_path: Path, runtime_profile: str) -> tuple[int, list[int]]:
    stopped_controller = stop_active_queue_controller(matrix_dir)
    cleanup_stale_controller_state(matrix_dir)
    state_dir = direct_state_dir(matrix_dir)
    pid_path = state_dir / "runner.pid"
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = None
        if pid is not None and is_pid_active(pid):
            raise SystemExit(f"Direct runner already active for config={config_path}")
        pid_path.unlink(missing_ok=True)
        (state_dir / "last_direct_launch.json").unlink(missing_ok=True)

    stopped_pids = stop_existing_replay_processes(config_path)
    cmd = direct_cmd_for_config(config_path, runtime_profile)
    log_path = direct_log_path(matrix_dir)
    log_handle = log_path.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    time.sleep(2)
    pid_path.write_text(f"{proc.pid}\n", encoding="utf-8")
    (state_dir / "last_direct_launch.json").write_text(
        json.dumps(
            {
                "pid": proc.pid,
                "stopped_pids": stopped_pids,
                "stopped_controller_pid": stopped_controller,
                "runtime_profile": runtime_profile,
                "config_path": str(config_path),
                "cmd": cmd,
                "log_path": str(log_path),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return proc.pid, stopped_pids


def main() -> int:
    args = parse_args()
    OUT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_matrix_rows()
    representative_rows = [row for row in rows if row["representative_lineage_row"] == "True"]
    if args.slugs:
        requested = set(args.slugs)
        representative_rows = [row for row in representative_rows if slug_for_row(row) in requested]
    if not representative_rows:
        raise SystemExit("No representative rows selected.")

    for row in representative_rows:
        slug = slug_for_row(row)
        lineage = row["campaign_lineage"]
        spec = LINEAGE_SPECS[lineage]
        template_path = OUT_CONFIG_DIR / f"{slug}.template.yaml"
        if not args.skip_build:
            cfg = build_template(row)
            with template_path.open("w", encoding="utf-8") as handle:
                yaml.safe_dump(cfg, handle, sort_keys=False)
            if spec["builder_kind"] == "ndlm_featurecov":
                run_cmd(["python3", "scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py", "--config", str(template_path)])
            elif spec["builder_kind"] == "all9_feature":
                run_cmd(["python3", "scripts/build_multimodel_v8_all9_feature_matrix_configs.py", "--config", str(template_path)])
            elif spec["builder_kind"] == "featurecov_cf1":
                run_cmd(["python3", "scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py", "--config", str(template_path)])
            elif spec["builder_kind"] == "exalm_t1_exact_grid":
                run_cmd(["python3", "scripts/build_multimodel_v8_exalm_t1_discount_grid_configs.py", "--config", str(template_path)])
            else:
                raise SystemExit(f"Unhandled builder_kind={spec['builder_kind']}")
            patch_generated_run_configs(Path(str(cfg["campaign"]["config_output_dir"])))
        if not args.skip_validate:
            run_cmd(["python3", "scripts/validate_publication_replay_representatives.py", "--slugs", slug])

        matrix_dir, artifact_root, queue_cmd = queue_cmd_from_config(template_path)
        config_path = generated_config_from_template(template_path)
        runtime_profile = runtime_profile_for_template(template_path)
        if args.dry_run:
            print(f"[dry-run] {slug}")
            print("config:", config_path)
            print("runtime_profile:", runtime_profile)
            print("queue_cmd:", " ".join(queue_cmd))
            print("direct_cmd:", " ".join(direct_cmd_for_config(config_path, runtime_profile)))
            continue
        if args.launch:
            pid, stopped_pids = launch_direct_detached(matrix_dir, config_path, runtime_profile)
            stopped_note = f" stopped_old_pids={stopped_pids}" if stopped_pids else ""
            print(f"{slug}: launched direct runner pid={pid} runtime={runtime_profile}{stopped_note}")
        else:
            print(f"{slug}: built+validated; launch skipped (runtime={runtime_profile}, config={config_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
