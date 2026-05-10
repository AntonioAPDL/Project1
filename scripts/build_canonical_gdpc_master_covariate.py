#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from canonical_climate_indices_lib import (
    ROOT,
    canonical_paths,
    gdpc_alpha_output_path,
    gdpc_beta_output_path,
    gdpc_compat_alias_paths,
    gdpc_factor_output_path,
    gdpc_initial_factor_output_path,
    gdpc_metadata_output_path,
    gdpc_review_output_path,
    gdpc_stationarity_review_path,
    load_config,
    package_versions,
    sha256_path,
    snapshot_config,
    standardized_daily_matrix_path,
    utc_now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the canonical GDPC1 master factor and workflow compatibility aliases.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "canonical_gdpc_master_covariate.yaml",
        help="Canonical GDPC master-covariate config.",
    )
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing {label}: {path}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_alias_files(
    *,
    factor_csv: Path,
    alias_paths: dict[str, Path],
    alias_specs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    df = pd.read_csv(factor_csv)
    if list(df.columns) != ["time", "GDPC1"]:
        raise SystemExit(f"Unexpected canonical factor columns in {factor_csv}: {df.columns.tolist()}")

    manifest_rows: list[dict[str, Any]] = []
    for spec in alias_specs:
        alias_filename = str(spec["alias_filename"])
        value_column = str(spec["value_column"])
        alias_path = alias_paths[alias_filename]
        alias_df = df.rename(columns={"GDPC1": value_column})
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        alias_df.to_csv(alias_path, index=False)
        manifest_rows.append(
            {
                "alias_filename": alias_filename,
                "alias_path": str(alias_path),
                "value_column": value_column,
                "source_factor_path": str(factor_csv),
                "rows": int(len(alias_df)),
                "time_start": str(alias_df["time"].iloc[0]),
                "time_end": str(alias_df["time"].iloc[-1]),
                "sha256": sha256_path(alias_path),
            }
        )
    return manifest_rows


def write_alias_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "alias_filename",
                "alias_path",
                "value_column",
                "source_factor_path",
                "rows",
                "time_start",
                "time_end",
                "sha256",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def render_review(
    *,
    cfg: dict[str, Any],
    review_path: Path,
    factor_csv: Path,
    alpha_csv: Path,
    beta_csv: Path,
    initial_f_csv: Path,
    metadata: dict[str, Any],
    alias_manifest_rows: list[dict[str, Any]],
    stationarity_report: Path,
) -> None:
    gdpc_meta = metadata["gdpc"]
    sign_meta = metadata["sign_rule"]
    factor_summary = metadata["factor_summary"]
    lines = [
        "# Canonical GDPC Build Review",
        "",
        f"- generated_at_utc: `{metadata['generated_at_utc']}`",
        f"- lineage_version: `{cfg['version']}`",
        f"- factor_file: `{factor_csv}`",
        f"- alpha_file: `{alpha_csv}`",
        f"- beta_file: `{beta_csv}`",
        f"- initial_f_file: `{initial_f_csv}`",
        "",
        "## Fit Contract",
        "",
        f"- component_name: `{metadata['component_name']}`",
        f"- canonical_window: `{metadata['time_start']}` -> `{metadata['time_end']}`",
        f"- series_count: `{metadata['series_count']}`",
        f"- fixed_lag_k: `{gdpc_meta['k']}`",
        f"- tolerance: `{gdpc_meta['tol']}`",
        f"- max_iterations: `{gdpc_meta['niter_max']}`",
        f"- criterion_label: `{gdpc_meta['crit_name']}`",
        f"- criterion_value: `{gdpc_meta['criterion_value']}`",
        f"- converged: `{gdpc_meta['conv']}`",
        f"- iterations_used: `{gdpc_meta['niter']}`",
        f"- explained_variance: `{gdpc_meta['expart']}`",
        f"- reconstruction_mse: `{gdpc_meta['mse']}`",
        "",
        "## Sign Orientation",
        "",
        f"- anchor_index: `{sign_meta['anchor_index']}`",
        f"- correlation_before: `{sign_meta['anchor_correlation_before']}`",
        f"- correlation_after: `{sign_meta['anchor_correlation_after']}`",
        f"- sign_flipped: `{sign_meta['sign_flipped']}`",
        "",
        "## Factor Summary",
        "",
        f"- mean: `{factor_summary['mean']}`",
        f"- sd: `{factor_summary['sd']}`",
        f"- min: `{factor_summary['min']}`",
        f"- max: `{factor_summary['max']}`",
        "",
        "## Compatibility Aliases",
        "",
        "| alias_filename | value_column | rows | time_start | time_end |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in alias_manifest_rows:
        lines.append(
            f"| `{row['alias_filename']}` | `{row['value_column']}` | {row['rows']} | {row['time_start']} | {row['time_end']} |"
        )
    lines.extend(
        [
            "",
            "## Reference Inputs",
            "",
            f"- standardized_matrix: `{metadata['input_csv']}`",
            f"- stationarity_audit: `{stationarity_report}`",
            "",
            "## Package Environment",
            "",
            f"- python: `{package_versions()['python']}`",
            f"- gdpc: `{gdpc_meta['package_version']}`",
        ]
    )
    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config.resolve())
    paths = canonical_paths(cfg)

    std_matrix = standardized_daily_matrix_path(cfg, paths)
    stationarity_report = gdpc_stationarity_review_path(cfg, paths)
    require_file(std_matrix, "standardized daily matrix")
    require_file(stationarity_report, "stationarity audit report")

    factor_csv = gdpc_factor_output_path(cfg, paths)
    alpha_csv = gdpc_alpha_output_path(cfg, paths)
    beta_csv = gdpc_beta_output_path(cfg, paths)
    initial_f_csv = gdpc_initial_factor_output_path(cfg, paths)
    metadata_json = gdpc_metadata_output_path(cfg, paths)
    review_md = gdpc_review_output_path(cfg, paths)

    gdpc_cfg = cfg["gdpc"]
    cmd = [
        "Rscript",
        str(ROOT / "scripts" / "build_canonical_gdpc_factor.R"),
        "--input-csv",
        str(std_matrix),
        "--output-csv",
        str(factor_csv),
        "--output-alpha-csv",
        str(alpha_csv),
        "--output-beta-csv",
        str(beta_csv),
        "--output-initial-f-csv",
        str(initial_f_csv),
        "--output-metadata-json",
        str(metadata_json),
        "--component-name",
        str(gdpc_cfg["component_name"]),
        "--k",
        str(int(gdpc_cfg["k"])),
        "--tol",
        str(float(gdpc_cfg["tol"])),
        "--niter-max",
        str(int(gdpc_cfg["niter_max"])),
        "--crit",
        str(gdpc_cfg["crit"]),
        "--anchor-index",
        str(gdpc_cfg["sign_rule"]["anchor_index_id"]),
        "--require-convergence",
        "true" if gdpc_cfg.get("require_convergence", True) else "false",
    ]
    env = os.environ.copy()
    blas_threads = int(gdpc_cfg.get("blas_threads", 1))
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
        env[key] = str(blas_threads)
    proc = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
    if proc.returncode != 0:
        return proc.returncode

    alias_paths = gdpc_compat_alias_paths(cfg, paths)
    alias_manifest_rows = write_alias_files(
        factor_csv=factor_csv,
        alias_paths=alias_paths,
        alias_specs=cfg.get("compatibility_aliases", []),
    )
    alias_manifest_path = paths.metadata_root / "compatibility_alias_manifest.csv"
    write_alias_manifest(alias_manifest_path, alias_manifest_rows)

    metadata = read_json(metadata_json)
    metadata["alias_outputs"] = alias_manifest_rows
    metadata["stationarity_audit_report"] = str(stationarity_report)
    metadata["config_snapshot_path"] = str(paths.metadata_root / "canonical_gdpc_build_config.yaml")
    write_json(metadata_json, metadata)
    snapshot_config(args.config.resolve(), paths.metadata_root / "canonical_gdpc_build_config.yaml")

    render_review(
        cfg=cfg,
        review_path=review_md,
        factor_csv=factor_csv,
        alpha_csv=alpha_csv,
        beta_csv=beta_csv,
        initial_f_csv=initial_f_csv,
        metadata=metadata,
        alias_manifest_rows=alias_manifest_rows,
        stationarity_report=stationarity_report,
    )

    print(f"[OK] wrote canonical GDPC factor: {factor_csv}")
    print(f"[OK] wrote compatibility manifest: {alias_manifest_path}")
    print(f"[OK] wrote review: {review_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
