#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from canonical_climate_indices_lib import (
    ROOT,
    canonical_paths,
    gdpc_stationarity_review_path,
    load_config,
    standardized_daily_matrix_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full canonical GDPC master-covariate pipeline.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "canonical_gdpc_master_covariate.yaml",
        help="Canonical GDPC config.",
    )
    parser.add_argument("--force-download", action="store_true", help="Redownload monthly raw climate-index files.")
    parser.add_argument("--run-screening", action="store_true", help="Run the small fixed-lag GDPC screening before the canonical build.")
    parser.add_argument("--force-screening", action="store_true", help="Recompute lag-screening runs even if screening metadata already exists.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config.resolve())
    paths = canonical_paths(cfg)
    std_matrix = standardized_daily_matrix_path(cfg, paths)
    stationarity_report = gdpc_stationarity_review_path(cfg, paths)

    steps = [
        [sys.executable, str(ROOT / "scripts" / "download_canonical_climate_indices.py"), "--config", str(args.config.resolve())],
        [sys.executable, str(ROOT / "scripts" / "build_canonical_climate_daily_matrices.py"), "--config", str(args.config.resolve())],
        [sys.executable, str(ROOT / "scripts" / "render_canonical_climate_index_diagnostics.py"), "--config", str(args.config.resolve())],
        [
            "Rscript",
            str(ROOT / "scripts" / "build_canonical_climate_stationarity_audit.R"),
            "--input-csv",
            str(std_matrix),
            "--output-dir",
            str(stationarity_report.parent),
            "--window-label",
            f"{cfg['canonical_window']['start_date']} -> {cfg['canonical_window']['end_date']}",
        ],
        [sys.executable, str(ROOT / "scripts" / "build_canonical_gdpc_master_covariate.py"), "--config", str(args.config.resolve())],
    ]

    if args.force_download:
        steps[0].append("--force")
    if args.run_screening:
        screening_cmd = [sys.executable, str(ROOT / "scripts" / "screen_canonical_gdpc_lags.py"), "--config", str(args.config.resolve())]
        if args.force_screening:
            screening_cmd.append("--force")
        steps.insert(4, screening_cmd)

    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
