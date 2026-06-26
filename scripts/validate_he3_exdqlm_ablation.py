#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

from he3_exdqlm_ablation_lib import (
    HE3_TEMPLATE_DEFAULT,
    build_status_frame,
    crps_summary_path,
    deep_merge,
    load_variant_specs,
    load_template,
    manifest_path,
    read_model_mean_crps,
    stage_status,
)
from multimodel_v8_lib import load_yaml


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validate HE3 exdqlm multivar ablation configs and references.")
    ap.add_argument("--matrix-dir", required=True)
    ap.add_argument("--template", default=str(HE3_TEMPLATE_DEFAULT))
    ap.add_argument("--crps-tolerance", type=float, default=5e-6)
    return ap.parse_args()


def expected_state_dim(include_trend: bool, enabled_harmonic_indices: list[int]) -> int:
    return (1 if include_trend else 0) + 2 * len(enabled_harmonic_indices)


def nested_get(payload: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def run_structure_smoke(plan: pd.DataFrame) -> list[dict[str, Any]]:
    distinct = (
        plan.loc[:, ["variant", "include_trend", "enabled_harmonic_indices"]]
        .drop_duplicates()
        .sort_values("variant")
        .reset_index(drop=True)
    )
    spec_rows = []
    for _, row in distinct.iterrows():
        enabled = ",".join(str(int(x)) for x in str(row["enabled_harmonic_indices"]).split(",") if x)
        spec_rows.append(f"{row['variant']}|{int(bool(row['include_trend']))}|{enabled}")
    payload = ";".join(spec_rows)
    r_code = r"""
library(exdqlm)
raw_specs <- strsplit(Sys.getenv("HE3_SPECS_PAYLOAD"), ";", fixed = TRUE)[[1]]
source("R/unified/families/exdqlm_multivar_structure.R")
out <- lapply(raw_specs[nzchar(raw_specs)], function(raw_spec) {
  parts <- strsplit(raw_spec, "|", fixed = TRUE)[[1]]
  variant <- parts[[1]]
  include_trend <- as.logical(as.integer(parts[[2]]))
  enabled_harmonic_indices <- integer(0)
  if (length(parts) >= 3 && nzchar(parts[[3]])) {
    enabled_harmonic_indices <- as.integer(strsplit(parts[[3]], ",", fixed = TRUE)[[1]])
  }
  built <- exdqlm_multivar_build_structure(
    m_yy = 1.0,
    kk = 0.5,
    df_t = 0.99,
    df_s1 = 0.98,
    df_s2 = 0.97,
    df_s67 = 0.96,
    lam1 = 0.9,
    lam2 = 0.8,
    include_trend = include_trend,
    enabled_harmonic_indices = enabled_harmonic_indices,
    default_harmonics = exdqlm_multivar_default_harmonics(),
    season_period = 363.5854,
    trend_c0_scale = 1.0,
    season_c0_scale = 0.5
  )
  sprintf(
    "%s|%s|%s|%s",
    variant,
    as.integer(built$p),
    as.integer(length(built$df)),
    paste(as.integer(built$dim.df), collapse = ",")
  )
})
cat(paste(out, collapse = "\n"))
"""
    proc = subprocess.run(
        ["Rscript", "--vanilla", "-e", r_code],
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, "HE3_SPECS_PAYLOAD": payload},
    )
    results: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        variant, p, df_length, dim_df = line.split("|", 3)
        results.append(
            {
                "variant": variant,
                "p": int(p),
                "df_length": int(df_length),
                "dim_df": [int(x) for x in dim_df.split(",") if x],
            }
        )
    return results


def main() -> int:
    args = parse_args()
    matrix_dir = Path(args.matrix_dir).resolve()
    template = load_template(Path(args.template).resolve())
    plan = pd.read_csv(matrix_dir / "matrix_plan.csv")
    metadata = load_yaml(matrix_dir / "matrix_metadata.yaml")
    artifact_root = Path(metadata["artifact_root"]).resolve()
    fit_workers = int(metadata["fit_workers"])
    variant_specs = load_variant_specs(template)
    variant_by_key = {spec.key: spec for spec in variant_specs}

    findings: list[str] = []
    expected_cutoffs = int(plan["cutoff"].astype(str).str.zfill(8).nunique())
    expected_total = expected_cutoffs * len(variant_specs)
    expected_reuse = expected_cutoffs * sum(1 for spec in variant_specs if spec.reuse_reference)
    expected_launch = expected_total - expected_reuse
    if len(plan) != expected_total:
        findings.append(f"Expected {expected_total} HE3 rows, found {len(plan)}.")
    counts = plan["launch_mode"].value_counts().to_dict()
    if int(counts.get("reuse_reference", 0)) != expected_reuse:
        findings.append(
            f"Expected {expected_reuse} reused full references, found {counts.get('reuse_reference', 0)}."
        )
    if int(counts.get("launch", 0)) != expected_launch:
        findings.append(f"Expected {expected_launch} launch rows, found {counts.get('launch', 0)}.")

    # Validate reused full references match the finalized HE2 winners exactly.
    reuse_rows = plan[plan["launch_mode"] == "reuse_reference"].copy()
    for _, row in reuse_rows.iterrows():
        source_dir = Path(str(row["source_run_dir"]))
        phase, status = stage_status(manifest_path(source_dir))
        if status != "pass":
            findings.append(f"Reused reference {row['variant']} / {row['cutoff']} is not pass (phase={phase}, status={status}).")
            continue
        mean_crps = read_model_mean_crps(crps_summary_path(source_dir), str(row["target_model_id"]))
        expected = float(row["source_full_crps"])
        if abs(mean_crps - expected) > args.crps_tolerance:
            findings.append(
                f"Reused reference {row['cutoff']} deviates from selected CRPS "
                f"({mean_crps:.8f} vs expected {expected:.8f})."
            )

    launch_rows = plan[plan["launch_mode"] == "launch"].copy()
    for _, row in launch_rows.iterrows():
        cfg_path = Path(str(row["config_path"]))
        if not cfg_path.exists():
            findings.append(f"Missing launch config: {cfg_path}")
            continue
        cfg = load_yaml(cfg_path)
        run_cfg = cfg.get("run", {})
        models_cfg = cfg.get("models", {})
        fit_cfg = cfg.get("fit", {})
        if str(run_cfg.get("run_id", "")) != str(row["run_id"]):
            findings.append(f"run_id mismatch in {cfg_path}")
        if Path(str(run_cfg.get("run_root", ""))).resolve() != (artifact_root / "runs").resolve():
            findings.append(f"run_root mismatch in {cfg_path}")
        if not bool(models_cfg.get("run_exdqlm_multivar", False)):
            findings.append(f"run_exdqlm_multivar disabled in {cfg_path}")
        if any(bool(models_cfg.get(flag, False)) for flag in ("run_exdqlm_univar", "run_ndlm_main", "run_ndlm_univar")):
            findings.append(f"Non-target model family enabled in {cfg_path}")
        multivar_cfg = models_cfg.get("exdqlm_multivar", {})
        structure_cfg = multivar_cfg.get("structure", {})
        enabled_indices = [int(x) for x in structure_cfg.get("enabled_harmonic_indices", [])]
        expected_indices = [int(x) for x in str(row["enabled_harmonic_indices"]).split(",") if x]
        if bool(structure_cfg.get("include_trend", True)) != bool(row["include_trend"]):
            findings.append(f"include_trend mismatch in {cfg_path}")
        if enabled_indices != expected_indices:
            findings.append(f"enabled_harmonic_indices mismatch in {cfg_path}")
        if str(multivar_cfg.get("forecast_transfer_mode", "")).strip().lower() != str(row["forecast_transfer_mode"]).strip().lower():
            findings.append(f"forecast_transfer_mode mismatch in {cfg_path}")
        legacy_cfg = fit_cfg.get("exdqlm_multivar", {}).get("legacy", {})
        if bool(legacy_cfg.get("use_covariates", True)) != bool(row["use_covariates"]):
            findings.append(f"use_covariates mismatch in {cfg_path}")
        if int(fit_cfg.get("parallel", {}).get("workers", 0)) != fit_workers:
            findings.append(f"fit.parallel.workers mismatch in {cfg_path}")
        if int(run_cfg.get("threads", {}).get("mc_cores", 0)) != fit_workers:
            findings.append(f"run.threads.mc_cores mismatch in {cfg_path}")
        variant_spec = variant_by_key.get(str(row["variant"]))
        if variant_spec is None:
            findings.append(f"Unknown variant in plan: {row['variant']}")
            continue
        he3_meta = cfg.get("he3_ablation", {})
        actual_override = he3_meta.get("forecast_health_overrides", {}) if isinstance(he3_meta, dict) else {}
        expected_override = variant_spec.forecast_health_overrides
        if actual_override != expected_override:
            findings.append(f"forecast_health_overrides metadata mismatch in {cfg_path}")
        if not bool(he3_meta.get("cleanup_rdata_after_post", False)):
            findings.append(f"cleanup_rdata_after_post metadata is not true in {cfg_path}")
        actual_gamma_overrides = he3_meta.get("gamma_sigma_overrides", {}) if isinstance(he3_meta, dict) else {}
        expected_gamma_overrides = (
            template.get("fit_policy", {})
            .get("exdqlm_multivar", {})
            .get("gamma_sigma_overrides", {})
        ) or {}
        if actual_gamma_overrides != expected_gamma_overrides:
            findings.append(f"gamma_sigma_overrides metadata mismatch in {cfg_path}")
        source_cfg = load_yaml(Path(str(row["source_config_path"])))
        source_health = source_cfg.get("fit", {}).get("exdqlm_multivar", {}).get("forecast_health", {}) or {}
        expected_health = deep_merge(source_health, expected_override)
        actual_health = fit_cfg.get("exdqlm_multivar", {}).get("forecast_health", {}) or {}
        if actual_health != expected_health:
            findings.append(f"forecast_health resolved config mismatch in {cfg_path}")
        gamma_sigma = fit_cfg.get("exdqlm_multivar", {}).get("gamma_sigma", {}) or {}
        max_iter = nested_get(gamma_sigma, ["max_iter"])
        state_guard_enabled = nested_get(gamma_sigma, ["stabilization", "state_guard_enabled"], True)
        state_guard_start_iter = nested_get(gamma_sigma, ["stabilization", "state_guard_start_iter"])
        try:
            max_iter_int = int(max_iter)
        except (TypeError, ValueError):
            max_iter_int = None
        try:
            state_guard_start_int = int(state_guard_start_iter)
        except (TypeError, ValueError):
            state_guard_start_int = None
        if state_guard_enabled is not False:
            if state_guard_start_int is None:
                findings.append(f"state_guard_start_iter missing in {cfg_path}")
            elif max_iter_int is not None and state_guard_start_int >= max_iter_int:
                findings.append(
                    f"state_guard_start_iter={state_guard_start_int} is outside max_iter={max_iter_int} in {cfg_path}"
                )

    smoke_rows = run_structure_smoke(plan)
    for row in smoke_rows:
        variant = row["variant"]
        match = plan[plan["variant"] == variant].iloc[0]
        expected_indices = [int(x) for x in str(match["enabled_harmonic_indices"]).split(",") if x]
        expected_p = expected_state_dim(bool(match["include_trend"]), expected_indices)
        if int(row["p"]) != expected_p:
            findings.append(f"Structure helper produced p={row['p']} for {variant}, expected {expected_p}.")
        expected_df_len = (1 if bool(match["include_trend"]) else 0) + len(expected_indices)
        if int(row["df_length"]) != expected_df_len:
            findings.append(
                f"Structure helper produced df length={row['df_length']} for {variant}, expected {expected_df_len}."
            )

    status_df = build_status_frame(plan, artifact_root)
    status_df.to_csv(matrix_dir / "matrix_status.csv", index=False)

    summary_lines = [
        "# HE3 exdqlm ablation validation",
        "",
        f"- template: `{args.template}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- total rows: `{len(plan)}`",
        f"- launch rows: `{len(launch_rows)}`",
        f"- reused rows: `{len(reuse_rows)}`",
        f"- findings: `{len(findings)}`",
        "",
    ]
    if findings:
        summary_lines.append("## Findings")
        summary_lines.append("")
        summary_lines.extend(f"- {item}" for item in findings)
    else:
        summary_lines.append("## Findings")
        summary_lines.append("")
        summary_lines.append("- None. Validation passed.")
    summary_path = matrix_dir / "validation_summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    payload = {
        "passed": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "matrix_dir": str(matrix_dir),
        "artifact_root": str(artifact_root),
    }
    (matrix_dir / "validation_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if findings:
        raise SystemExit(1)
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
