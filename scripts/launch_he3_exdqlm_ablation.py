#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from he3_exdqlm_ablation_lib import HE3_TEMPLATE_DEFAULT, load_template


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build, validate, and launch the HE3 exdqlm ablation controller.")
    ap.add_argument("--template", default=str(HE3_TEMPLATE_DEFAULT))
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def read_launch_settings(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        settings[key.strip()] = value.strip()
    return settings


def main() -> int:
    args = parse_args()
    template_path = Path(args.template).resolve()
    template = load_template(template_path)
    campaign = template.get("campaign", {})
    matrix_dir = Path(campaign["matrix_dir"]).resolve()
    artifact_root = Path(campaign["artifact_root"]).resolve()

    if not args.skip_build:
        subprocess.run(
            ["python3", "scripts/build_he3_exdqlm_ablation_matrix.py", "--template", str(template_path)],
            check=True,
        )

    if not args.skip_validate:
        subprocess.run(
            ["python3", "scripts/validate_he3_exdqlm_ablation.py", "--matrix-dir", str(matrix_dir), "--template", str(template_path)],
            check=True,
        )

    launch_settings = read_launch_settings(matrix_dir / "launch_settings.env")
    queue_cmd = [
        "python3",
        "scripts/run_he3_exdqlm_ablation_queue.py",
        "--matrix-dir",
        str(matrix_dir),
        "--artifact-root",
        str(artifact_root),
        "--ordinary-max-concurrent",
        launch_settings["ORDINARY_MAX_CONCURRENT"],
        "--heavy-cutoff-max-concurrent",
        launch_settings["HEAVY_CUTOFF_MAX_CONCURRENT"],
        "--pause-free-gb",
        launch_settings["PAUSE_FREE_GB"],
        "--launch-free-gb",
        launch_settings["LAUNCH_FREE_GB"],
        "--heavy-free-gb",
        launch_settings["HEAVY_FREE_GB"],
        "--poll-seconds",
        launch_settings["POLL_SECONDS"],
    ]

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
