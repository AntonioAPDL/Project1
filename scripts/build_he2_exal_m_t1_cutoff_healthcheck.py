from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CUTOFF = "2022-12-25"
DEFAULT_OUT_DIR = ROOT / "reports" / "he2_exal_m_t1_cutoff_healthcheck_20221225_20260517"
DEFAULT_RUNTIME_ROOT = (
    Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")
    / "multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516"
)
DEFAULT_RUN_ID = "multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep"
DEFAULT_QUANTILES = ["05", "20", "35", "50", "65", "80", "95"]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def symlink_force(target: Path, link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        return
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    link_path.symlink_to(target)


def parse_policy(log_text: str) -> dict[str, str]:
    line = next((ln for ln in log_text.splitlines() if ln.startswith("[gamsig_policy] ")), "")
    out: dict[str, str] = {}
    for key in [
        "p0",
        "freeze_target",
        "warmup_freeze_iters",
        "min_update_iters",
        "min_total_iters",
        "max_iter",
        "state_guard",
        "guard_mode",
    ]:
        match = re.search(rf"{re.escape(key)}=([^ ]+)", line)
        out[key] = match.group(1) if match else ""
    return out


def parse_sampling(log_text: str) -> dict[str, str]:
    finalize = re.search(
        r"\[sampling_phase\] p0=.*? phase=sampling_finalize elapsed=([0-9.]+)s detail=n_samp=([0-9]+)",
        log_text,
    )
    preflight = re.search(
        r"\[sampling_preflight\] p0=.*? detail=mode=([^ ]+) median=([^ ]+) guard_count=([^ ]+) .*? frozen=([^ ]+) .*? update_iters=([^ ]+) min_update_iters=([^ ]+) reason=([^\n]+)",
        log_text,
    )
    out = {
        "sampling_elapsed_sec": finalize.group(1) if finalize else "",
        "n_samp": finalize.group(2) if finalize else "",
        "guard_mode_runtime": "",
        "median_runtime": "",
        "guard_count": "",
        "frozen_at_preflight": "",
        "update_iters_at_preflight": "",
        "min_update_iters_at_preflight": "",
        "preflight_reason": "",
    }
    if preflight:
        out.update(
            {
                "guard_mode_runtime": preflight.group(1),
                "median_runtime": preflight.group(2),
                "guard_count": preflight.group(3),
                "frozen_at_preflight": preflight.group(4),
                "update_iters_at_preflight": preflight.group(5),
                "min_update_iters_at_preflight": preflight.group(6),
                "preflight_reason": preflight.group(7).strip(),
            }
        )
    return out


def parse_health(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def build_quantile_rows(run_root: Path, quantiles: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for q in quantiles:
        fit_log_path = run_root / f"fit/exdqlm_multivar/keep/q={q}/logs/fit.log"
        sampling_log_path = run_root / f"fit/exdqlm_multivar/keep/q={q}/logs/sampling_diagnostics.log"
        health_path = run_root / f"fit/exdqlm_multivar/keep/q={q}/outputs/multivar_forecast_health.txt"
        fit_log = fit_log_path.read_text(errors="ignore") if fit_log_path.exists() else ""
        sampling_log = sampling_log_path.read_text(errors="ignore") if sampling_log_path.exists() else ""
        health = parse_health(health_path) if health_path.exists() else {}
        policy = parse_policy(fit_log)
        sampling = parse_sampling(sampling_log)
        rdata_path = run_root / f"fit/exdqlm_multivar/keep/q={q}/outputs/DISC_variables_{int(q)}_exAL_synth_DISC.RData"
        rows.append(
            {
                "quantile": q,
                "p0": policy["p0"],
                "freeze_target": policy["freeze_target"],
                "warmup_freeze_iters": policy["warmup_freeze_iters"],
                "min_update_iters": policy["min_update_iters"],
                "min_total_iters": policy["min_total_iters"],
                "max_iter": policy["max_iter"],
                "state_guard": policy["state_guard"],
                "guard_mode": policy["guard_mode"],
                "sampling_elapsed_sec": sampling["sampling_elapsed_sec"],
                "n_samp": sampling["n_samp"],
                "update_iters_at_preflight": sampling["update_iters_at_preflight"],
                "guard_count": sampling["guard_count"],
                "frozen_at_preflight": sampling["frozen_at_preflight"],
                "max_abs_sm_ens": health.get("max_abs_sm_ens", ""),
                "max_abs_forecast_exps": health.get("max_abs_forecast_exps", ""),
                "nonfinite_forecast_exps": health.get("nonfinite_forecast_exps", ""),
                "max_E_sigma": health.get("max_E_sigma", ""),
                "health_status_note": (
                    "nonfinite_forecast_exps_present"
                    if health.get("nonfinite_forecast_exps", "0") not in {"0", ""}
                    else "no_nonfinite_forecast_exps"
                ),
                "fit_log_path": str(fit_log_path),
                "sampling_log_path": str(sampling_log_path),
                "forecast_health_path": str(health_path),
                "rdata_path": str(rdata_path),
                "rdata_present": rdata_path.exists(),
            }
        )
    return rows


def build_artifact_inventory(run_root: Path, post_root: Path, quantiles: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def add_row(category: str, label: str, path: Path) -> None:
        rows.append({"category": category, "label": label, "path": str(path), "exists": path.exists()})

    for rel in [
        "run_manifest.yaml",
        "resolved_config.yaml",
        "report/summary.md",
        "report/summary.json",
        "validate/compare_report.json",
        "validate/env_drift_report.json",
        "post/logs/post_runner.log",
        "fit/logs/fit_stage.log",
        "inputs/shared/source_map.txt",
        "inputs/shared/data_start_filter_summary.txt",
        "inputs/shared/deterministic_climate/deterministic_climate_summary.txt",
        "env/R_sessionInfo.txt",
        "env/threads_snapshot.txt",
    ]:
        add_row("run_meta", rel, run_root / rel)

    for q in quantiles:
        add_row("fit_log", f"q={q} fit.log", run_root / f"fit/exdqlm_multivar/keep/q={q}/logs/fit.log")
        add_row("sampling_log", f"q={q} sampling_diagnostics.log", run_root / f"fit/exdqlm_multivar/keep/q={q}/logs/sampling_diagnostics.log")
        add_row("forecast_health", f"q={q} multivar_forecast_health.txt", run_root / f"fit/exdqlm_multivar/keep/q={q}/outputs/multivar_forecast_health.txt")
        add_row("fit_state", f"q={q} DISC_variables", run_root / f"fit/exdqlm_multivar/keep/q={q}/outputs/DISC_variables_{int(q)}_exAL_synth_DISC.RData")

    for rel in [
        "All_ELBOS_DISC.png",
        "SMOKE_OBSERVED_SERIES_DISC.png",
        "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png",
        "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.pdf",
        "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png",
        "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.pdf",
        "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv",
        "exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv",
        "figure_manifest.csv",
        "publication_figure_manifest.csv",
        "post_artifacts_summary.json",
        "tables/crps_forecast_summary.csv",
        "tables/crps_forecast_per_time.csv",
        "tables/crps_input_health.csv",
        "tables/crps_input_health_per_time.csv",
        "tables/gamma_summary.csv",
        "tables/sigma_summary.csv",
        "tables/covariate_effects_summary.csv",
        "tables/posterior_table_exports_manifest.csv",
        "tables/posterior_table_exports_README.md",
    ]:
        add_row("post_artifact", rel, post_root / rel)
    return rows


def link_healthcheck_bundle(out_dir: Path, run_root: Path, post_root: Path, quantiles: list[str]) -> None:
    link_root = out_dir / "links"
    for rel in [
        "run_manifest.yaml",
        "resolved_config.yaml",
        "report/summary.md",
        "report/summary.json",
        "validate/compare_report.json",
        "validate/env_drift_report.json",
        "post/logs/post_runner.log",
        "fit/logs/fit_stage.log",
        "inputs/shared/source_map.txt",
        "inputs/shared/data_start_filter_summary.txt",
        "inputs/shared/deterministic_climate/deterministic_climate_summary.txt",
        "env/R_sessionInfo.txt",
        "env/threads_snapshot.txt",
    ]:
        symlink_force(run_root / rel, link_root / rel)
    for q in quantiles:
        for rel in [
            f"fit/exdqlm_multivar/keep/q={q}/logs/fit.log",
            f"fit/exdqlm_multivar/keep/q={q}/logs/sampling_diagnostics.log",
            f"fit/exdqlm_multivar/keep/q={q}/outputs/multivar_forecast_health.txt",
            f"fit/exdqlm_multivar/keep/q={q}/outputs/DISC_variables_{int(q)}_exAL_synth_DISC.RData",
        ]:
            symlink_force(run_root / rel, link_root / rel)
    for rel in [
        "All_ELBOS_DISC.png",
        "SMOKE_OBSERVED_SERIES_DISC.png",
        "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png",
        "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.pdf",
        "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png",
        "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.pdf",
        "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv",
        "exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv",
        "figure_manifest.csv",
        "publication_figure_manifest.csv",
        "post_artifacts_summary.json",
        "tables/crps_forecast_summary.csv",
        "tables/crps_forecast_per_time.csv",
        "tables/crps_input_health.csv",
        "tables/crps_input_health_per_time.csv",
        "tables/gamma_summary.csv",
        "tables/sigma_summary.csv",
        "tables/covariate_effects_summary.csv",
        "tables/posterior_table_exports_manifest.csv",
        "tables/posterior_table_exports_README.md",
    ]:
        symlink_force(post_root / rel, link_root / "post" / rel)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a single-cutoff exAL-M-T1 healthcheck bundle.")
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--label", default="exAL-M-T1")
    parser.add_argument("--family", default="exdqlm_multivar_keep")
    parser.add_argument("--quantiles", nargs="*", default=DEFAULT_QUANTILES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime_root = Path(args.runtime_root)
    run_root = runtime_root / "runs" / args.run_id
    post_root = run_root / "post" / "outputs" / args.run_id
    out_dir = Path(args.out_dir)
    quantiles = [str(q).zfill(2) for q in args.quantiles]
    out_dir.mkdir(parents=True, exist_ok=True)

    report_summary = read_json(run_root / "report/summary.json")
    post_summary = read_json(post_root / "post_artifacts_summary.json")
    compare_report = read_json(run_root / "validate/compare_report.json")
    crps_rows = read_csv_rows(post_root / "tables/crps_forecast_summary.csv")
    input_health_rows = read_csv_rows(post_root / "tables/crps_input_health.csv")
    quantile_rows = build_quantile_rows(run_root, quantiles)
    artifact_rows = build_artifact_inventory(run_root, post_root, quantiles)
    link_healthcheck_bundle(out_dir, run_root, post_root, quantiles)

    figure_rows = [row for row in artifact_rows if row["category"] == "post_artifact" and str(row["path"]).endswith((".png", ".pdf"))]
    table_rows = [row for row in artifact_rows if row["category"] == "post_artifact" and str(row["path"]).endswith(".csv")]
    synth_crps_row = next(row for row in crps_rows if row["model_id"] == "exdqlm_multivar_synth_keep")
    synth_health_row = next(row for row in input_health_rows if row["model_id"] == "exdqlm_multivar_synth_keep")

    summary = {
        "label": args.label,
        "family": args.family,
        "cutoff_date": args.cutoff,
        "run_id": args.run_id,
        "run_root": str(run_root),
        "healthcheck_bundle": str(out_dir),
        "run_validation_status": compare_report["status"],
        "report_validation_status": report_summary["validation_status"],
        "post_contract_status": post_summary["contract"]["status"],
        "representative_mean_crps": synth_crps_row["mean_crps"],
        "representative_input_health_status": synth_health_row["status"],
        "figure_file_count": len(figure_rows),
        "tabular_file_count": len(table_rows),
        "per_quantile_count": len(quantile_rows),
        "trace_note": "No dedicated per-quantile trace PNGs are emitted; use All_ELBOS_DISC plus per-quantile fit/sampling logs.",
        "fit_state_rdata_present_any": any(bool(row["rdata_present"]) for row in quantile_rows),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    quantile_fields = [
        "quantile", "p0", "freeze_target", "warmup_freeze_iters", "min_update_iters", "min_total_iters", "max_iter",
        "state_guard", "guard_mode", "sampling_elapsed_sec", "n_samp", "update_iters_at_preflight", "guard_count",
        "frozen_at_preflight", "max_abs_sm_ens", "max_abs_forecast_exps", "nonfinite_forecast_exps", "max_E_sigma",
        "health_status_note", "fit_log_path", "sampling_log_path", "forecast_health_path", "rdata_path", "rdata_present",
    ]
    write_csv(out_dir / "quantile_health_matrix.csv", quantile_rows, quantile_fields)
    artifact_fields = ["category", "label", "path", "exists"]
    write_csv(out_dir / "artifact_inventory.csv", artifact_rows, artifact_fields)

    md: list[str] = []
    md.append("# exAL-M-T1 Single-Cutoff Health Check\n\n")
    md.append(f"Cutoff: `{args.cutoff}`  \n")
    md.append(f"Run id: `{args.run_id}`  \n")
    md.append(f"Run root: `{run_root}`  \n")
    md.append(f"Health-check bundle: `{out_dir}`\n\n")
    md.append("## Executive Read\n\n")
    md.append(f"- family: `{args.label}`\n")
    md.append(f"- stages: `{', '.join(report_summary['stages_enabled'])}`\n")
    md.append(f"- validation status: `{report_summary['validation_status']}`\n")
    md.append(f"- post contract status: `{post_summary['contract']['status']}`\n")
    md.append(f"- synthesis mean CRPS: `{synth_crps_row['mean_crps']}`\n")
    md.append(f"- synthesis input-health status: `{synth_health_row['status']}`\n")
    md.append(f"- note: `{summary['trace_note']}`\n\n")
    if not summary["fit_state_rdata_present_any"]:
        md.append("Heavy per-quantile fit-state `.RData` files are no longer present in the run root. That is consistent with post-cleanup and means this health check relies on logs, forecast-health summaries, post tables, and figures rather than retained fit-state blobs.\n\n")
    md.append("## What To Inspect First\n\n")
    md.append("- ELBO/trend figure: [`links/post/All_ELBOS_DISC.png`](./links/post/All_ELBOS_DISC.png)\n")
    md.append("- observed smoke figure: [`links/post/SMOKE_OBSERVED_SERIES_DISC.png`](./links/post/SMOKE_OBSERVED_SERIES_DISC.png)\n")
    md.append("- main synthesis figure: [`links/post/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png`](./links/post/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png)\n")
    md.append("- synthesis figure with raw ensembles: [`links/post/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png`](./links/post/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png)\n")
    md.append("- synthesis quantiles CSV: [`links/post/exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv`](./links/post/exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv)\n")
    md.append("- CRPS summary: [`links/post/tables/crps_forecast_summary.csv`](./links/post/tables/crps_forecast_summary.csv)\n")
    md.append("- gamma summary: [`links/post/tables/gamma_summary.csv`](./links/post/tables/gamma_summary.csv)\n")
    md.append("- sigma summary: [`links/post/tables/sigma_summary.csv`](./links/post/tables/sigma_summary.csv)\n")
    md.append("- covariate effects summary: [`links/post/tables/covariate_effects_summary.csv`](./links/post/tables/covariate_effects_summary.csv)\n")
    md.append("- compare report: [`links/validate/compare_report.json`](./links/validate/compare_report.json)\n")
    md.append("- report summary: [`links/report/summary.md`](./links/report/summary.md)\n\n")
    md.append("## Quantile Matrix\n\n")
    md.append("| q | freeze_target | warmup | state_guard | sampling_sec | n_samp | max_abs_sm_ens | max_abs_forecast_exps | nonfinite_forecast_exps | max_E_sigma |\n")
    md.append("|---|---|---:|---|---:|---:|---:|---:|---:|---:|\n")
    for row in quantile_rows:
        md.append(f"| `{row['quantile']}` | `{row['freeze_target']}` | `{row['warmup_freeze_iters']}` | `{row['state_guard']}` | `{row['sampling_elapsed_sec']}` | `{row['n_samp']}` | `{row['max_abs_sm_ens']}` | `{row['max_abs_forecast_exps']}` | `{row['nonfinite_forecast_exps']}` | `{row['max_E_sigma']}` |\n")
    md.append("\n")
    md.append("## Key Diagnostics\n\n")
    md.append("- run manifest: [`links/run_manifest.yaml`](./links/run_manifest.yaml)\n")
    md.append("- resolved config: [`links/resolved_config.yaml`](./links/resolved_config.yaml)\n")
    md.append("- source map: [`links/inputs/shared/source_map.txt`](./links/inputs/shared/source_map.txt)\n")
    md.append("- deterministic climate summary: [`links/inputs/shared/deterministic_climate/deterministic_climate_summary.txt`](./links/inputs/shared/deterministic_climate/deterministic_climate_summary.txt)\n")
    md.append("- fit stage log: [`links/fit/logs/fit_stage.log`](./links/fit/logs/fit_stage.log)\n")
    md.append("- post runner log: [`links/post/logs/post_runner.log`](./links/post/logs/post_runner.log)\n")
    for q in quantiles:
        md.append(f"- q={q}: [`fit.log`](./links/fit/exdqlm_multivar/keep/q={q}/logs/fit.log), [`sampling_diagnostics.log`](./links/fit/exdqlm_multivar/keep/q={q}/logs/sampling_diagnostics.log), [`multivar_forecast_health.txt`](./links/fit/exdqlm_multivar/keep/q={q}/outputs/multivar_forecast_health.txt)\n")
    md.append("\n## Notes\n\n")
    md.append("- This bundle is a focused reference check for a single cutoff only.\n")
    md.append("- It is meant to help us inspect fit behavior, posterior summaries, and synthesis behavior without mixing in cross-cutoff state.\n")
    md.append("- The workflow emits one aggregate ELBO figure plus per-quantile logs; it does not emit separate per-quantile trace PNGs in this run family.\n")
    md.append("- The representative synthesis figure is current, so any bad-looking forecast-window behavior here should be treated as a real output-quality concern, not an article-sync concern.\n")
    (out_dir / f"HE2_EXAL_M_T1_HEALTHCHECK_{args.cutoff.replace('-', '')}.md").write_text("".join(md))
    print(f"Wrote exAL-M-T1 cutoff health check to {out_dir}")


if __name__ == "__main__":
    main()
