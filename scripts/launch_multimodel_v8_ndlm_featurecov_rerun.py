#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "config" / "multimodel_v8_ndlm_featurecov_rerun.template.yaml"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


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
    ap = argparse.ArgumentParser(
        description="Build, validate, and launch the corrected NDLM-only featurecov rerun controller."
    )
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    template_path = Path(args.template).resolve()
    template = load_yaml(template_path)
    campaign = template.get("campaign", {})
    matrix_dir = Path(campaign["matrix_dir"]).resolve()
    artifact_root = Path(campaign["artifact_root"]).resolve()

    subprocess.run(
        [
            "python3",
            "scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py",
            "--config",
            str(template_path),
        ],
        cwd=ROOT,
        check=True,
    )

    if not args.skip_validate:
        subprocess.run(
            [
                "python3",
                "scripts/validate_ndlm_featurecov_rerun_prelaunch.py",
                "--config",
                str(template_path),
            ],
            cwd=ROOT,
            check=True,
        )

    launch_settings = read_launch_settings(matrix_dir / "launch_settings.env")
    queue_cmd = [
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
        "--heavy-cutoff-max-concurrent",
        launch_settings.get("HEAVY_CUTOFF_MAX_CONCURRENT", "1"),
        "--poll-seconds",
        launch_settings["POLL_SECONDS"],
    ]
    if launch_settings.get("HEAVY_CUTOFF_BLOCKS_ORDINARY", "1") in {"0", "false", "False", "no"}:
        queue_cmd.append("--no-heavy-cutoff-blocks-ordinary")

    if args.dry_run:
        print(" ".join(queue_cmd))
        return 0

    log_path = matrix_dir / "queue.log"
    log_handle = log_path.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        queue_cmd,
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
    print(proc.pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
