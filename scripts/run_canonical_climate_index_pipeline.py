#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the canonical climate-index download + postprocess pipeline.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "canonical_gdpc_master_covariate.yaml",
        help="Canonical climate-index config.",
    )
    parser.add_argument("--force-download", action="store_true", help="Redownload monthly raw files before postprocessing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    steps = [
        [sys.executable, str(ROOT / "scripts" / "download_canonical_climate_indices.py"), "--config", str(args.config.resolve())],
        [sys.executable, str(ROOT / "scripts" / "build_canonical_climate_daily_matrices.py"), "--config", str(args.config.resolve())],
    ]
    if args.force_download:
        steps[0].append("--force")
    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
