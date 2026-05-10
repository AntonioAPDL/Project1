#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from canonical_climate_indices_lib import (
    ROOT,
    canonical_paths,
    gdpc_screening_alpha_output_path,
    gdpc_screening_beta_output_path,
    gdpc_screening_factor_output_path,
    gdpc_screening_initial_factor_output_path,
    gdpc_screening_metadata_output_path,
    gdpc_screening_review_path,
    gdpc_screening_summary_csv_path,
    gdpc_screening_summary_json_path,
    gdpc_stationarity_review_path,
    load_config,
    standardized_daily_matrix_path,
    utc_now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a simple fixed-lag GDPC screening over a small candidate set.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "canonical_gdpc_master_covariate.yaml",
        help="Canonical GDPC config.",
    )
    parser.add_argument("--force", action="store_true", help="Recompute all screening runs even if metadata already exists.")
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing {label}: {path}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def screening_candidates(cfg: dict[str, Any]) -> list[int]:
    screening = cfg.get("screening", {})
    values = screening.get("candidate_k_values", [])
    if not values:
        raise SystemExit("No screening candidate_k_values configured.")
    unique = sorted({int(v) for v in values})
    if any(v < 1 for v in unique):
        raise SystemExit(f"Invalid screening k values: {unique}")
    return unique


def run_one_k(*, cfg: dict[str, Any], config_path: Path, k: int, force: bool) -> dict[str, Any]:
    paths = canonical_paths(cfg)
    std_matrix = standardized_daily_matrix_path(cfg, paths)
    metadata_json = gdpc_screening_metadata_output_path(cfg, k, paths)
    if metadata_json.exists() and not force:
        meta = read_json(metadata_json)
        meta["screening_reused"] = True
        return meta

    gdpc_cfg = cfg["gdpc"]
    screening_cfg = cfg["screening"]
    cmd = [
        "Rscript",
        str(ROOT / "scripts" / "build_canonical_gdpc_factor.R"),
        "--input-csv",
        str(std_matrix),
        "--output-csv",
        str(gdpc_screening_factor_output_path(cfg, k, paths)),
        "--output-alpha-csv",
        str(gdpc_screening_alpha_output_path(cfg, k, paths)),
        "--output-beta-csv",
        str(gdpc_screening_beta_output_path(cfg, k, paths)),
        "--output-initial-f-csv",
        str(gdpc_screening_initial_factor_output_path(cfg, k, paths)),
        "--output-metadata-json",
        str(metadata_json),
        "--component-name",
        str(gdpc_cfg["component_name"]),
        "--k",
        str(int(k)),
        "--tol",
        str(float(screening_cfg["tol"])),
        "--niter-max",
        str(int(screening_cfg["niter_max"])),
        "--crit",
        str(screening_cfg["criterion"]),
        "--anchor-index",
        str(gdpc_cfg["sign_rule"]["anchor_index_id"]),
        "--require-convergence",
        "true" if screening_cfg.get("require_convergence", False) else "false",
    ]
    env = os.environ.copy()
    blas_threads = int(gdpc_cfg.get("blas_threads", 1))
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
        env[key] = str(blas_threads)
    started = time.monotonic()
    timeout_seconds = screening_cfg.get("max_runtime_seconds_per_k")
    timed_out = False
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            check=False,
            timeout=None if timeout_seconds is None else float(timeout_seconds),
        )
        exit_code = int(proc.returncode)
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = 124

    if timed_out:
        elapsed = float(time.monotonic() - started)
        meta = {
            "generated_at_utc": utc_now_iso(),
            "input_csv": str(std_matrix),
            "output_csv": str(gdpc_screening_factor_output_path(cfg, k, paths)),
            "component_name": str(gdpc_cfg["component_name"]),
            "rows": None,
            "series_count": None,
            "time_start": cfg["canonical_window"]["start_date"],
            "time_end": cfg["canonical_window"]["end_date"],
            "gdpc": {
                "package_version": None,
                "k": int(k),
                "tol": float(screening_cfg["tol"]),
                "niter_max": int(screening_cfg["niter_max"]),
                "crit_name": str(screening_cfg["criterion"]),
                "conv": False,
                "niter": None,
                "mse": None,
                "expart": None,
                "criterion_value": None,
            },
            "sign_rule": {
                "method": str(gdpc_cfg["sign_rule"]["method"]),
                "anchor_index": str(gdpc_cfg["sign_rule"]["anchor_index_id"]),
                "anchor_correlation_before": None,
                "anchor_correlation_after": None,
                "sign_flipped": None,
            },
            "factor_summary": {
                "mean": None,
                "sd": None,
                "min": None,
                "max": None,
            },
            "runtime": {"elapsed_seconds": elapsed},
            "screening_status": {
                "timed_out": True,
                "exit_code": exit_code,
                "timeout_seconds": float(timeout_seconds),
            },
        }
        write_json(metadata_json, meta)
        return meta

    if exit_code != 0:
        raise SystemExit(f"Screening fit failed for k={k} with exit code {exit_code}")
    meta = read_json(metadata_json)
    meta["screening_reused"] = False
    return meta


def summarize_one(meta: dict[str, Any], k: int) -> dict[str, Any]:
    gdpc_meta = meta["gdpc"]
    sign_meta = meta["sign_rule"]
    runtime = meta.get("runtime", {})
    screening_status = meta.get("screening_status", {})
    return {
        "k": int(k),
        "converged": bool(gdpc_meta["conv"]),
        "criterion_label": str(gdpc_meta["crit_name"]),
        "criterion_value": None if gdpc_meta.get("criterion_value") is None else float(gdpc_meta["criterion_value"]),
        "explained_variance": None if gdpc_meta.get("expart") is None else float(gdpc_meta["expart"]),
        "reconstruction_mse": None if gdpc_meta.get("mse") is None else float(gdpc_meta["mse"]),
        "iterations_used": None if gdpc_meta.get("niter") is None else int(gdpc_meta["niter"]),
        "runtime_seconds": float(runtime.get("elapsed_seconds", 0.0)),
        "anchor_correlation_after": None if sign_meta.get("anchor_correlation_after") is None else float(sign_meta["anchor_correlation_after"]),
        "sign_flipped": None if sign_meta.get("sign_flipped") is None else bool(sign_meta["sign_flipped"]),
        "timed_out": bool(screening_status.get("timed_out", False)),
        "factor_csv": str(meta["output_csv"]),
        "metadata_json": str(meta.get("output_metadata_json", "")),
    }


def select_best(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    screening_cfg = cfg["screening"]
    selection = screening_cfg["selection_rule"]
    require_converged = bool(selection.get("require_converged_fit", True))
    objective = str(selection.get("objective", "minimize")).lower()
    primary_metric = str(selection.get("primary_metric", "criterion_value"))

    candidates = [row for row in rows if row["converged"]] if require_converged else list(rows)
    if not candidates:
        raise SystemExit("No eligible screening candidates remained after applying the convergence filter.")

    if objective != "minimize":
        raise SystemExit(f"Unsupported screening objective: {objective}")

    def sort_key(row: dict[str, Any]) -> tuple[float, float, int]:
        return (
            float(row[primary_metric]),
            float(row["runtime_seconds"]),
            int(row["k"]),
        )

    best = sorted(candidates, key=sort_key)[0]
    return {
        "selected_k": int(best["k"]),
        "selection_rule": {
            "primary_metric": primary_metric,
            "objective": objective,
            "require_converged_fit": require_converged,
            "tie_breakers": ["lower_runtime_seconds", "smaller_k"],
        },
        "selected_row": best,
    }


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "k",
                "converged",
                "criterion_label",
                "criterion_value",
                "explained_variance",
                "reconstruction_mse",
                "iterations_used",
                "runtime_seconds",
                "anchor_correlation_after",
                "sign_flipped",
                "timed_out",
                "factor_csv",
                "metadata_json",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_review(path: Path, *, cfg: dict[str, Any], rows: list[dict[str, Any]], selection: dict[str, Any], config_path: Path) -> None:
    lines = [
        "# Canonical GDPC Lag Screening Review",
        "",
        f"- generated_at_utc: `{utc_now_iso()}`",
        f"- config: `{config_path}`",
        f"- canonical_window: `{cfg['canonical_window']['start_date']}` -> `{cfg['canonical_window']['end_date']}`",
        f"- screening_candidates: `{', '.join(str(row['k']) for row in rows)}`",
        f"- current_config_k: `{cfg['gdpc']['k']}`",
        f"- selected_k: `{selection['selected_k']}`",
        f"- criterion_label: `{rows[0]['criterion_label'] if rows else cfg['screening']['criterion']}`",
        f"- timeout_seconds_per_k: `{cfg['screening'].get('max_runtime_seconds_per_k')}`",
        "",
        "## Selection Rule",
        "",
        "- keep only converged fits,",
        f"- minimize `{selection['selection_rule']['primary_metric']}`,",
        "- break ties by lower runtime, then smaller `k`.",
        "",
        "## Screening Summary",
        "",
        "| k | converged | timed_out | BIC | explained_variance | mse | iterations | runtime_seconds | anchor_corr_after |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        bic = "NA" if row["criterion_value"] is None else f"{row['criterion_value']:.4f}"
        expv = "NA" if row["explained_variance"] is None else f"{row['explained_variance']:.4f}"
        mse = "NA" if row["reconstruction_mse"] is None else f"{row['reconstruction_mse']:.4f}"
        niter = "NA" if row["iterations_used"] is None else str(row["iterations_used"])
        corr = "NA" if row["anchor_correlation_after"] is None else f"{row['anchor_correlation_after']:.4f}"
        lines.append(
            f"| {row['k']} | {row['converged']} | {row['timed_out']} | {bic} | {expv} | {mse} | {niter} | {row['runtime_seconds']:.4f} | {corr} |"
        )
    selected = selection["selected_row"]
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- selected `k = {selected['k']}` because it achieved the best converged `{selected['criterion_label']}` value among the screened candidates.",
            f"- selected-row BIC: `{selected['criterion_value']:.4f}`",
            f"- selected-row explained variance: `{selected['explained_variance']:.4f}`",
            f"- selected-row runtime (seconds): `{selected['runtime_seconds']:.4f}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config.resolve())
    paths = canonical_paths(cfg)
    std_matrix = standardized_daily_matrix_path(cfg, paths)
    stationarity_report = gdpc_stationarity_review_path(cfg, paths)
    require_file(std_matrix, "standardized daily matrix")
    require_file(stationarity_report, "stationarity audit report")
    if not cfg.get("screening", {}).get("enabled", False):
        raise SystemExit("Screening is disabled in the canonical GDPC config.")

    rows: list[dict[str, Any]] = []
    for k in screening_candidates(cfg):
        meta = run_one_k(cfg=cfg, config_path=args.config.resolve(), k=k, force=args.force)
        summary = summarize_one(meta, k)
        summary["metadata_json"] = str(gdpc_screening_metadata_output_path(cfg, k, paths))
        rows.append(summary)

    rows = sorted(rows, key=lambda row: int(row["k"]))
    selection = select_best(rows, cfg)

    summary_csv = gdpc_screening_summary_csv_path(cfg, paths)
    summary_json = gdpc_screening_summary_json_path(cfg, paths)
    review_md = gdpc_screening_review_path(cfg, paths)
    write_summary_csv(summary_csv, rows)
    write_json(
        summary_json,
        {
            "generated_at_utc": utc_now_iso(),
            "config_path": str(args.config.resolve()),
            "canonical_window": cfg["canonical_window"],
            "screening": cfg["screening"],
            "current_config_k": int(cfg["gdpc"]["k"]),
            "selection": selection,
            "rows": rows,
            "stationarity_audit_report": str(stationarity_report),
        },
    )
    write_review(review_md, cfg=cfg, rows=rows, selection=selection, config_path=args.config.resolve())

    print(f"[OK] wrote screening summary csv: {summary_csv}")
    print(f"[OK] wrote screening summary json: {summary_json}")
    print(f"[OK] wrote screening review: {review_md}")
    print(f"[OK] selected_k={selection['selected_k']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
