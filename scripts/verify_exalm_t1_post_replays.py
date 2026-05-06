#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

import yaml


REQUIRED_OUTPUT_FILES = [
    "figure_manifest.csv",
    "publication_figure_manifest.csv",
    "publication_style_used.yaml",
    "post_artifacts_manifest.csv",
    "post_artifacts_summary.json",
    "timestamps.csv",
    "timestamps_keep.csv",
    "data_cbind_tY_X.csv",
    "data_cbind_tY_X.rds",
    "data_cbind_tY_X_keep.csv",
    "data_cbind_tY_X_keep.rds",
    "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png",
    "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.pdf",
    "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png",
    "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.pdf",
    "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv",
    "exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv",
    "exdqlm_multivar_synth_drop_cutoff_window_posterior_samples.png",
    "exdqlm_multivar_synth_drop_cutoff_window_posterior_samples.pdf",
    "exdqlm_multivar_synth_drop_cutoff_window_posterior_samples_with_raw_ensembles.png",
    "exdqlm_multivar_synth_drop_cutoff_window_posterior_samples_with_raw_ensembles.pdf",
    "exdqlm_multivar_synth_drop_cutoff_window_quantiles.csv",
    "exdqlm_multivar_synth_drop_cutoff_window_sample_subset.csv",
]

REQUIRED_TABLE_FILES = [
    "crps_forecast_summary.csv",
    "crps_forecast_per_time.csv",
    "crps_input_health.csv",
    "crps_input_health_per_time.csv",
    "crps_forecast_summary_keep.csv",
    "crps_forecast_per_time_keep.csv",
    "crps_input_health_keep.csv",
    "crps_input_health_per_time_keep.csv",
    "covariate_effects_summary.csv",
    "covariate_effects_summary.rds",
    "covariate_effects_summary.tex",
    "gamma_summary.csv",
    "gamma_summary.rds",
    "gamma_summary.tex",
    "sigma_summary.csv",
    "sigma_summary.rds",
    "sigma_summary.tex",
    "posterior_table_exports_manifest.csv",
    "posterior_table_exports_README.md",
]

REQUIRED_POST_INPUTS = [
    "retros_post_adapter.csv",
    "nws_post_adapter.csv",
    "glofas_post_adapter.csv",
]

REQUIRED_CACHE_FILES = [
    "exdqlm_multivar_synth_drop__mode-drop__synth_multivar_forecast_log1p.rds",
    "exdqlm_multivar_synth_drop__mode-drop__synth_multivar_forecast_quantiles_log1p.rds",
    "exdqlm_multivar_synth_drop__mode-drop__synth_multivar_hist_log1p.rds",
    "exdqlm_multivar_synth_drop__mode-drop__synth_multivar_hist_quantiles_log1p.rds",
    "exdqlm_multivar_synth_drop__mode-drop__y_reps_f_new_smoke.rds",
    "exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_log1p.rds",
    "exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_quantiles_log1p.rds",
    "exdqlm_multivar_synth_keep__mode-keep__synth_multivar_hist_log1p.rds",
    "exdqlm_multivar_synth_keep__mode-keep__synth_multivar_hist_quantiles_log1p.rds",
    "exdqlm_multivar_synth_keep__mode-keep__y_reps_f_new_smoke.rds",
]

Q_SPECS = [
    ("05", 5),
    ("20", 20),
    ("35", 35),
    ("50", 50),
    ("65", 65),
    ("80", 80),
    ("95", 95),
]

REQUIRED_RUN_FILES = [
    "run_manifest.yaml",
    "resolved_config.yaml",
    "fit/logs/fit_stage.log",
    "fit/logs/shared_input_source_map.log",
    "report/summary.json",
    "report/summary.md",
    "validate/compare_report.json",
    "validate/compare_report.txt",
    "validate/current.sha256",
    "validate/canonical.sha256",
    "env/R_installed_packages.csv",
    "env/R_sessionInfo.txt",
    "env/renviron_snapshot.txt",
    "env/threads_snapshot.txt",
    "env/python_pip_freeze.txt",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify exAL-M-T1 post replay runs.")
    parser.add_argument(
        "--manifest",
        default="repro/manifests/exalm_t1_authoritative_runs_20260505.csv",
        help="CSV manifest listing authoritative source runs.",
    )
    parser.add_argument(
        "--run-root",
        default="repro/runs",
        help="Replay run root.",
    )
    parser.add_argument(
        "--suffix",
        default="20260505",
        help="Replay run suffix used by build_exalm_t1_post_replay_configs.py.",
    )
    parser.add_argument(
        "--run-prefix",
        default="paper_exalm_t1_postreplay",
        help="Replay run prefix.",
    )
    parser.add_argument(
        "--require-fit",
        action="store_true",
        help="Require fit-stage artifacts and fit stage pass status.",
    )
    return parser.parse_args()


def replay_run_id(cutoff_date: str, suffix: str, prefix: str) -> str:
    return f"{prefix}_{cutoff_date.replace('-', '')}_{suffix}"


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def expect_files(root: Path, rels: Iterable[str], failures: list[str], label: str) -> None:
    for rel in rels:
        if not (root / rel).exists():
            failures.append(f"{label} missing: {root / rel}")


def fit_rels() -> list[str]:
    rels: list[str] = []
    for q_label, q_num in Q_SPECS:
        rels.extend(
            [
                f"fit/q={q_label}/outputs/DISC_variables_{q_num}_exAL_synth_DISC.RData",
                f"fit/q={q_label}/outputs/multivar_forecast_health.txt",
                f"fit/q={q_label}/logs/fit.log",
                f"fit/exdqlm_multivar/keep/q={q_label}/outputs/DISC_variables_{q_num}_exAL_synth_DISC.RData",
                f"fit/exdqlm_multivar/keep/q={q_label}/outputs/multivar_forecast_health.txt",
                f"fit/exdqlm_multivar/keep/q={q_label}/logs/fit.log",
            ]
        )
    return rels


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = (repo_root / args.manifest).resolve()
    run_root = (repo_root / args.run_root).resolve()
    rows = load_manifest(manifest_path)

    all_failures: list[str] = []
    summary = []

    for row in rows:
        run_id = replay_run_id(row["cutoff_date"], args.suffix, args.run_prefix)
        replay_root = run_root / run_id
        manifest_file = replay_root / "run_manifest.yaml"
        failures: list[str] = []

        if not manifest_file.exists():
            all_failures.append(f"{run_id}: missing run_manifest.yaml")
            continue

        manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8")) or {}
        stages = manifest.get("stages") or {}
        required_stages = ["post", "validate", "report"]
        if args.require_fit:
            required_stages.insert(0, "fit")
        for stage in required_stages:
            status = (stages.get(stage) or {}).get("status")
            if status != "pass":
                failures.append(f"stage {stage} status={status!r}")

        out_dir = replay_root / "post" / "outputs" / run_id
        tables_dir = out_dir / "tables"
        inputs_dir = replay_root / "post" / "inputs"
        cache_dir = replay_root / "post" / "cache"
        expect_files(replay_root, REQUIRED_RUN_FILES, failures, "run")
        if args.require_fit:
            expect_files(replay_root, fit_rels(), failures, "fit")
        expect_files(out_dir, REQUIRED_OUTPUT_FILES, failures, "output")
        expect_files(tables_dir, REQUIRED_TABLE_FILES, failures, "table")
        expect_files(inputs_dir, REQUIRED_POST_INPUTS, failures, "post input")
        expect_files(cache_dir, REQUIRED_CACHE_FILES, failures, "cache")

        crps_path = tables_dir / "crps_forecast_summary.csv"
        if crps_path.exists():
            rows_csv = load_csv(crps_path)
            selected = [r for r in rows_csv if r.get("model_id") == "exdqlm_multivar_synth_keep"]
            if not selected:
                failures.append("crps_forecast_summary.csv missing exdqlm_multivar_synth_keep row")
            else:
                row0 = selected[0]
                field = "mean_crps" if "mean_crps" in row0 else "crps_mean"
                got = float(row0[field])
                expected = float(row["expected_mean_crps"])
                if got != expected:
                    failures.append(
                        f"mean_crps mismatch for exdqlm_multivar_synth_keep: got={got:.16f} expected={expected:.16f}"
                    )

        summary_json = out_dir / "post_artifacts_summary.json"
        if summary_json.exists():
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            if str(payload.get("status", "")).lower() not in {"pass", "ok", "true"}:
                failures.append(f"post_artifacts_summary.json status={payload.get('status')!r}")

        summary.append({"run_id": run_id, "failures": failures})
        all_failures.extend([f"{run_id}: {item}" for item in failures])

    if all_failures:
        print("VERIFY_FAIL")
        for line in all_failures:
            print(line)
        raise SystemExit(1)

    print("VERIFY_PASS")
    for item in summary:
        print(item["run_id"])


if __name__ == "__main__":
    main()
