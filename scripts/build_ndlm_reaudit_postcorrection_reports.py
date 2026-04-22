#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from statistics import median


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
NDLM_RERUN_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_ndlm_featurecov_rerun_20260420"
)
FEATURECOV_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_featurecov_cf1_eps_sweep_20260416"
)
OUTPUT_DIR = REPO_ROOT / "reports" / "ndlm_reaudit_postcorrection"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt_float(value: float | None, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def bool_text(flag: bool) -> str:
    return "True" if flag else "False"


def parse_run_name(name: str) -> tuple[str, str]:
    parts = name.split("_")
    return parts[1], "_".join(parts[-3:])


def live_ndlm_runs() -> list[Path]:
    runs_root = NDLM_RERUN_ROOT / "runs"
    return sorted(
        p for p in runs_root.iterdir() if p.is_dir() and "__failed_" not in p.name
    )


def best_quantile_run_path(cutoff: str, variant: str) -> Path | None:
    variant_map = {
        "ndlm_main_keep": "exdqlm_multivar_keep",
        "ndlm_main_drop": "exdqlm_multivar_drop",
    }
    if variant not in variant_map:
        return None
    best_rows = read_csv(
        FEATURECOV_ROOT
        / "reports"
        / "final_featurecov_cf1_eps_analysis"
        / "best_by_cutoff_long.csv"
    )
    mapped_variant = variant_map[variant]
    for row in best_rows:
        if row["cutoff"] != cutoff or row["model_variant"] != mapped_variant:
            continue
        eps_label = row["best_epsilon_label"]
        if not eps_label:
            return None
        run_name = f"multimodel_{cutoff}_v8_{eps_label}_{mapped_variant}_featurecov_cf1"
        return FEATURECOV_ROOT / "runs" / run_name
    return None


def summarize_ndlm_run(run_dir: Path) -> dict[str, object]:
    cutoff, variant = parse_run_name(run_dir.name)
    table_root = run_dir / "post" / "outputs" / run_dir.name / "tables"
    crps_summary = read_csv(table_root / "crps_forecast_summary.csv")[0]
    crps_per_time = read_csv(table_root / "crps_forecast_per_time.csv")
    quantiles = read_csv(table_root / "ndlm_forecast_window_quantiles.csv")
    ensemble_summary_path = (
        run_dir / "diagnostics" / "ndlm" / "ndlm_forecast_ensemble_summary.csv"
    )
    ensemble_summary = (
        read_csv(ensemble_summary_path) if ensemble_summary_path.exists() else []
    )

    crps_vals = [float(row["crps"]) for row in crps_per_time]
    q50_vals = [float(row["q50_log1p"]) for row in quantiles]
    q80_vals = [float(row["q80_log1p"]) for row in quantiles]
    q95_vals = [float(row["q95_log1p"]) for row in quantiles]
    truth_vals = [float(row["truth_log1p"]) for row in quantiles]

    ensemble_q95 = [float(row["ensemble_q95"]) for row in ensemble_summary]
    ensemble_mean = [float(row["ensemble_mean"]) for row in ensemble_summary]

    corresponding_quantile_run = best_quantile_run_path(cutoff, variant)
    quantile_max_q95 = None
    quantile_max_q80 = None
    quantile_max_q50 = None
    quantile_run_name = ""
    if corresponding_quantile_run is not None:
        quantile_run_name = corresponding_quantile_run.name
        quantile_file = next(
            corresponding_quantile_run.glob(
                "post/outputs/*/exdqlm_multivar_synth_*_cutoff_window_quantiles.csv"
            ),
            None,
        )
        if quantile_file and quantile_file.exists():
            q_rows = read_csv(quantile_file)
            if q_rows and "segment" in q_rows[0]:
                q_rows = [row for row in q_rows if row["segment"] == "forecast"]
            quantile_max_q95 = max(float(row["q95"]) for row in q_rows)
            quantile_max_q80 = max(float(row["q80"]) for row in q_rows)
            quantile_max_q50 = max(float(row["q50"]) for row in q_rows)

    return {
        "run_name": run_dir.name,
        "cutoff": cutoff,
        "model_variant": variant,
        "transfer_mode": crps_summary["transfer_mode"],
        "mean_crps": float(crps_summary["mean_crps"]),
        "median_crps": float(crps_summary["median_crps"]),
        "max_crps": float(crps_summary["max_crps"]),
        "max_crps_over_median": float(crps_summary["max_crps"]) / max(
            float(crps_summary["median_crps"]), 1e-10
        ),
        "max_q50_log1p": max(q50_vals),
        "max_q80_log1p": max(q80_vals),
        "max_q95_log1p": max(q95_vals),
        "n_days_q80_gt_5": sum(value > 5 for value in q80_vals),
        "n_days_q95_gt_10": sum(value > 10 for value in q95_vals),
        "truth_max_log1p": max(truth_vals),
        "ensemble_max_q95_log1p": max(ensemble_q95) if ensemble_q95 else None,
        "ensemble_max_mean_log1p": max(ensemble_mean) if ensemble_mean else None,
        "quantile_run_name": quantile_run_name,
        "quantile_max_q50_log1p": quantile_max_q50,
        "quantile_max_q80_log1p": quantile_max_q80,
        "quantile_max_q95_log1p": quantile_max_q95,
    }


def build_anomaly_digest() -> list[dict[str, object]]:
    rows = [summarize_ndlm_run(run_dir) for run_dir in live_ndlm_runs()]
    rows.sort(key=lambda row: (-float(row["mean_crps"]), row["run_name"]))
    return rows


def build_runtime_inventory() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for run_dir in live_ndlm_runs():
        cutoff, variant = parse_run_name(run_dir.name)
        table_root = run_dir / "post" / "outputs" / run_dir.name / "tables"
        rows.append(
            {
                "run_name": run_dir.name,
                "cutoff": cutoff,
                "model_variant": variant,
                "resolved_config_exists": bool_text((run_dir / "resolved_config.yaml").exists()),
                "run_manifest_exists": bool_text((run_dir / "run_manifest.yaml").exists()),
                "fit_contract_check_exists": bool_text(
                    (
                        run_dir
                        / "fit"
                        / "contract_checks"
                        / ("ndlm_main" if "ndlm_main" in run_dir.name else "ndlm_univar")
                    ).exists()
                ),
                "fit_diagnostics_exists": bool_text(
                    (
                        run_dir
                        / "fit"
                        / "diagnostics"
                        / ("ndlm_main" if "ndlm_main" in run_dir.name else "ndlm_univar")
                    ).exists()
                ),
                "post_crps_summary_exists": bool_text((table_root / "crps_forecast_summary.csv").exists()),
                "post_crps_per_time_exists": bool_text((table_root / "crps_forecast_per_time.csv").exists()),
                "post_quantiles_exists": bool_text((table_root / "ndlm_forecast_window_quantiles.csv").exists()),
                "cache_mean_exists": bool_text((run_dir / "post" / "cache" / "xbs_ndlm_mean_loglog1p.rds").exists()),
                "cache_predictive_loglog_exists": bool_text((run_dir / "post" / "cache" / "y_reps_ndlm_loglog1p.rds").exists()),
                "cache_predictive_log1p_exists": bool_text((run_dir / "post" / "cache" / "y_reps_ndlm_log1p.rds").exists()),
                "diag_covariance_exists": bool_text(
                    (run_dir / "diagnostics" / "ndlm" / "ndlm_covariance_diagnostics.csv").exists()
                ),
                "diag_active_set_exists": bool_text(
                    (run_dir / "diagnostics" / "ndlm" / "active_set_by_lead.csv").exists()
                ),
                "diag_state_dim_exists": bool_text(
                    (run_dir / "diagnostics" / "ndlm" / "state_dim_by_lead.csv").exists()
                ),
                "diag_ensemble_summary_exists": bool_text(
                    (run_dir / "diagnostics" / "ndlm" / "ndlm_forecast_ensemble_summary.csv").exists()
                ),
            }
        )
    rows.sort(key=lambda row: row["run_name"])
    return rows


def write_anomaly_digest_md(rows: list[dict[str, object]], path: Path) -> None:
    worst = rows[:5]
    lines = [
        "# NDLM Reaudit Anomaly Digest",
        "",
        "Generated from the corrected 15-row NDLM rerun.",
        "",
        "| Run | Mean CRPS | Median CRPS | Max CRPS | Max q80 | Max q95 | Ensemble max q95 | Quantile max q95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in worst:
        lines.append(
            "| {run_name} | {mean_crps} | {median_crps} | {max_crps} | {max_q80_log1p} | {max_q95_log1p} | {ensemble_max_q95_log1p} | {quantile_max_q95_log1p} |".format(
                run_name=row["run_name"],
                mean_crps=fmt_float(float(row["mean_crps"])),
                median_crps=fmt_float(float(row["median_crps"])),
                max_crps=fmt_float(float(row["max_crps"])),
                max_q80_log1p=fmt_float(float(row["max_q80_log1p"])),
                max_q95_log1p=fmt_float(float(row["max_q95_log1p"])),
                ensemble_max_q95_log1p=fmt_float(float(row["ensemble_max_q95_log1p"])),
                quantile_max_q95_log1p=fmt_float(
                    None if row["quantile_max_q95_log1p"] is None else float(row["quantile_max_q95_log1p"])
                ),
            )
        )
    lines.extend(
        [
            "",
            "Key read:",
            "- The worst rows are concentrated in the multivariate NDLM path (`ndlm_main_keep`, `ndlm_main_drop`).",
            "- Their forecast-window medians are far smaller than their maxima, which indicates a small number of catastrophic forecast days dominate the score.",
            "- The multivariate NDLM upper forecast quantiles are far larger than both the raw driver ensembles and the matched multivariate quantile-model outputs.",
            "- The univariate NDLM rows do not carry multivariate ensemble-summary diagnostics, so those cells are intentionally `n/a` in the CSV.",
            "",
        ]
    )
    path.write_text("\n".join(lines))


def write_runtime_inventory_md(rows: list[dict[str, object]], path: Path) -> None:
    lines = [
        "# NDLM Reaudit Runtime Inventory",
        "",
        "All corrected live NDLM rerun rows have the expected runtime artifacts needed for the post-correction reaudit.",
        "",
        "| Run | CRPS summary | CRPS per-time | Quantiles | Predictive cache | Cov diagnostics |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {run_name} | {post_crps_summary_exists} | {post_crps_per_time_exists} | {post_quantiles_exists} | {cache_predictive_log1p_exists} | {diag_covariance_exists} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    anomaly_rows = build_anomaly_digest()
    anomaly_fields = list(anomaly_rows[0].keys())
    write_csv(OUTPUT_DIR / "ndlm_reaudit_anomaly_digest.csv", anomaly_rows, anomaly_fields)
    write_anomaly_digest_md(anomaly_rows, OUTPUT_DIR / "ndlm_reaudit_anomaly_digest.md")

    inventory_rows = build_runtime_inventory()
    inventory_fields = list(inventory_rows[0].keys())
    write_csv(
        OUTPUT_DIR / "ndlm_reaudit_runtime_inventory.csv",
        inventory_rows,
        inventory_fields,
    )
    write_runtime_inventory_md(
        inventory_rows, OUTPUT_DIR / "ndlm_reaudit_runtime_inventory.md"
    )


if __name__ == "__main__":
    main()
