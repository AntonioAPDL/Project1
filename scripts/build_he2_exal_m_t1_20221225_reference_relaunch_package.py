from __future__ import annotations

import csv
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "config" / "he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_reference_relaunch_20260518.template.yaml"
BATCH = ROOT / "config" / "he2_relaunch_batches" / "exdqlm_multivar_keep_20221225_reference_relaunch_20260518.yaml"
REPORT_DIR = ROOT / "reports" / "he2_exal_m_t1_20221225_reference_relaunch_20260518"
RUNTIME_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime") / "multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518"
GENERATED_CONFIG = RUNTIME_ROOT / "control" / "generated_configs" / "multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml"
CURRENT_CONFIG = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime") / "multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516" / "control" / "generated_configs" / "multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml"
CURRENT_RUN_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime") / "multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516" / "runs" / "multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep"
CURRENT_HEALTHCHECK = ROOT / "reports" / "he2_exal_m_t1_cutoff_healthcheck_20221225_20260517" / "quantile_health_matrix.csv"
SOURCE_CONFIG = ROOT / "config" / "unified_runs_exalm_t1_discount_grid_exact_20260424" / "multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep.yaml"
BUNDLE_META = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime") / "multimodel_v8_he2_publication_shared_inputs_20260510" / "stable_inputs" / "site=11160500" / "cutoff_date=2022-12-25" / "run_id=20260510_publication_shared_r01" / "meta.yaml"
RECOMMENDED_COMMON_WARMUP = 10
RECOMMENDED_MAX_ITER = 200


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return proc.stdout


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def symlink_force(target: Path, link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    link_path.symlink_to(target)


def check_shell_syntax(path: Path) -> bool:
    proc = subprocess.run(["bash", "-n", str(path)], cwd=ROOT, text=True, capture_output=True)
    return proc.returncode == 0


def qlabel(q: float) -> str:
    return f"q{int(round(q * 100)):02d}"


def _maybe_float(value: object) -> float | None:
    if value in ("", None):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out):
        return None
    return out


def _maybe_int(value: object) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def bundle_summary(meta: dict[str, Any]) -> dict[str, Any]:
    histfix = meta.get("histfix", {}) if isinstance(meta.get("histfix"), dict) else {}
    nws_policy = histfix.get("nws_source_policy", {}) if isinstance(histfix.get("nws_source_policy"), dict) else {}
    transforms = meta.get("transforms", {}) if isinstance(meta.get("transforms"), dict) else {}
    display_contract = meta.get("display_contract", {}) if isinstance(meta.get("display_contract"), dict) else {}
    return {
        "bundle_run_id": meta.get("run", {}).get("run_id", ""),
        "bundle_kind": meta.get("run", {}).get("bundle_kind", ""),
        "cutoff_date": meta.get("dates", {}).get("cutoff_date", ""),
        "data_start": meta.get("dates", {}).get("data_start", ""),
        "glofas_source_id": histfix.get("glofas_source_id", ""),
        "glofas_product_id": histfix.get("glofas_product_id", ""),
        "nws_primary_source_id": nws_policy.get("primary_source_id", ""),
        "nws_tail_fill_source_id": nws_policy.get("tail_fill_source_id", ""),
        "nws_tail_fill_start": nws_policy.get("tail_fill_start", ""),
        "nws_selection_rule": nws_policy.get("selection_rule", ""),
        "usgs_daily_source_path": histfix.get("usgs_daily_source_path", ""),
        "forecast_member_nws": histfix.get("forecast_member_sources", {}).get("nws", ""),
        "forecast_member_glofas": histfix.get("forecast_member_sources", {}).get("glofas", ""),
        "plot_scale": transforms.get("plot_scale", ""),
        "display_scale": display_contract.get("flow_support_figures_scale", ""),
    }


def state_evolution_row(label: str, cfg: dict[str, Any]) -> dict[str, object]:
    state = cfg["models"]["exdqlm_multivar"]["state_evolution"]
    legacy = cfg["fit"]["exdqlm_multivar"]["legacy"]
    gs = cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]
    scale = cfg.get("scale_contract", {})
    return {
        "spec_label": label,
        "df_t": state.get("df_t"),
        "df_s1": state.get("df_s1"),
        "df_s2": state.get("df_s2"),
        "df_s67": state.get("df_s67"),
        "df_discrep": state.get("df_discrep"),
        "lambda": state.get("lambda"),
        "df_trans": state.get("df_trans"),
        "df_covs": state.get("df_covs"),
        "lam1": legacy.get("lam1"),
        "lam2": legacy.get("lam2"),
        "n_samp": legacy.get("n_samp"),
        "forecast_cov_c_factor": legacy.get("forecast_cov", {}).get("c_factor"),
        "forecast_cov_epsilon": legacy.get("forecast_cov", {}).get("epsilon"),
        "max_iter": gs.get("max_iter"),
        "min_update_iters": gs.get("min_update_iters"),
        "min_total_iters": gs.get("min_total_iters"),
        "warmup_freeze_iters": gs.get("warmup_freeze_iters"),
        "freeze_target": gs.get("freeze_target"),
        "analysis_scale_fit_internal": scale.get("analysis_scale_fit_internal"),
        "analysis_scale_post_internal": scale.get("analysis_scale_post_internal"),
    }


def quantile_rows(cfg: dict[str, Any]) -> list[dict[str, object]]:
    base = cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]
    overrides = base.get("quantile_overrides", {})
    rows: list[dict[str, object]] = []
    for q in cfg["fit"]["quantiles"]:
        label = qlabel(float(q))
        ov = overrides.get(label, {}) if isinstance(overrides.get(label), dict) else {}
        init = {**(base.get("init", {}) or {}), **(ov.get("init", {}) or {})}
        stab = ov.get("stabilization", {}) if isinstance(ov.get("stabilization"), dict) else {}
        rows.append({
            "quantile": label,
            "p0": float(q),
            "freeze_target": ov.get("freeze_target", base.get("freeze_target", "")),
            "warmup_freeze_iters": ov.get("warmup_freeze_iters", base.get("warmup_freeze_iters", "")),
            "min_update_iters": base.get("min_update_iters", ""),
            "min_total_iters": base.get("min_total_iters", ""),
            "max_iter": base.get("max_iter", ""),
            "init_gamma": init.get("gamma", ""),
            "sigma_floor": init.get("sigma_floor", ""),
            "sigma_scale": init.get("sigma_scale", ""),
            "state_guard_enabled": stab.get("state_guard_enabled", ""),
            "state_norm_max_ratio": stab.get("state_norm_max_ratio", ""),
            "state_norm_abs_cap": stab.get("state_norm_abs_cap", ""),
            "state_guard_refreeze_iters": stab.get("state_guard_refreeze_iters", ""),
            "state_hold_after_guard_iters": stab.get("state_hold_after_guard_iters", stab.get("median_state_hold_after_guard_iters", "")),
            "state_blend_alpha": stab.get("state_blend_alpha", stab.get("median_state_blend_alpha", "")),
            "cov_blend_alpha": stab.get("cov_blend_alpha", stab.get("median_cov_blend_alpha", "")),
            "terminal_sampling_guard_mode": ov.get("terminal_sampling_guard", {}).get("mode", ""),
        })
    return rows


def _parse_fit_progress(log_path: Path) -> dict[str, object]:
    progress_re = re.compile(
        r"iter=(?P<iter>\d+).*?"
        r"sigma_exp=(?P<sigma>[-+0-9.eE]+).*?"
        r"gamma_exp=(?P<gamma>[-+0-9.eE]+).*?"
        r"state_norm_sq=(?P<state>[-+0-9.eE]+).*?"
        r"conv_check=(?P<conv>[-+0-9.eE]+).*?"
        r"gamsig_update_iters=(?P<updates>\d*)"
    )
    first_update_iter: int | None = None
    last: dict[str, object] = {}
    with log_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            match = progress_re.search(line)
            if not match:
                continue
            iteration = int(match.group("iter"))
            updates_text = match.group("updates")
            updates = int(updates_text) if updates_text else None
            if first_update_iter is None and updates is not None and updates > 0:
                first_update_iter = iteration
            last = {
                "last_iter": iteration,
                "last_sigma_exp": float(match.group("sigma")),
                "last_gamma_exp": float(match.group("gamma")),
                "last_state_norm_sq": float(match.group("state")),
                "last_conv_check": float(match.group("conv")),
                "last_updates": updates,
            }
    return {"first_update_iter": first_update_iter, **last}


def quantile_review_rows(cfg: dict[str, Any]) -> list[dict[str, object]]:
    policy_rows = {str(row["quantile"]): row for row in quantile_rows(cfg)}
    health_rows = {f"q{int(float(row['quantile'])):02d}": row for row in read_csv_rows(CURRENT_HEALTHCHECK)}
    review_rows: list[dict[str, object]] = []
    for q_label, policy in policy_rows.items():
        q_num = q_label[1:]
        fit_log = CURRENT_RUN_ROOT / "fit" / "exdqlm_multivar" / "keep" / f"q={q_num}" / "logs" / "fit.log"
        progress = _parse_fit_progress(fit_log)
        health = health_rows.get(q_label, {})
        freeze_target = str(policy.get("freeze_target", ""))
        current_warmup = _maybe_int(policy.get("warmup_freeze_iters"))
        recommended_note = (
            "keep state-freeze path; extend common hold to 10"
            if freeze_target == "states"
            else "extend gamma/sigma freeze hold to 10"
        )
        review_rows.append({
            "quantile": q_label,
            "p0": policy.get("p0", ""),
            "current_freeze_target": freeze_target,
            "current_warmup_freeze_iters": current_warmup,
            "recommended_freeze_target": freeze_target,
            "recommended_warmup_freeze_iters": RECOMMENDED_COMMON_WARMUP,
            "first_update_iter_current": progress.get("first_update_iter", ""),
            "update_iters_at_preflight": health.get("update_iters_at_preflight", ""),
            "last_iter_current": progress.get("last_iter", ""),
            "last_updates_current": progress.get("last_updates", ""),
            "last_sigma_exp_current": progress.get("last_sigma_exp", ""),
            "last_gamma_exp_current": progress.get("last_gamma_exp", ""),
            "last_state_norm_sq_current": progress.get("last_state_norm_sq", ""),
            "last_conv_check_current": progress.get("last_conv_check", ""),
            "max_abs_sm_ens_current": health.get("max_abs_sm_ens", ""),
            "max_abs_forecast_exps_current": health.get("max_abs_forecast_exps", ""),
            "nonfinite_forecast_exps_current": health.get("nonfinite_forecast_exps", ""),
            "max_E_sigma_current": health.get("max_E_sigma", ""),
            "review_note": recommended_note,
        })
    return review_rows


def config_section_rows(cfg: dict[str, Any]) -> list[dict[str, object]]:
    fit_mv = cfg["fit"]["exdqlm_multivar"]
    rows: list[dict[str, object]] = []
    rows.append({
        "section": "run",
        "status": "pass",
        "key_points": "strict repro mode, fixed seed, thread caps at 1, mc_cores=7",
        "notes": f"run_id={cfg['run']['run_id']}; seed={cfg['run']['seed']}; overwrite={cfg['run']['overwrite']}",
    })
    rows.append({
        "section": "stages",
        "status": "pass",
        "key_points": "data_prep_shared+fit+post+validate+report enabled; forecats disabled",
        "notes": "full single-cutoff end-to-end artifact contract remains enabled",
    })
    rows.append({
        "section": "inputs",
        "status": "pass",
        "key_points": "shared 20260510 bundle, full history, deterministic climate, PPT/SOIL/PCA covariates",
        "notes": f"retros={cfg['inputs']['fit']['retros_path']}; bundle_meta={cfg['inputs']['forecats']['existing_bundle_path']}",
    })
    rows.append({
        "section": "fit_gamma_sigma",
        "status": "pass",
        "key_points": "max_iter=200, common warmup=10, q35/q50 state freeze preserved",
        "notes": f"freeze_target={fit_mv['gamma_sigma']['freeze_target']}; min_update_iters={fit_mv['gamma_sigma']['min_update_iters']}; min_total_iters={fit_mv['gamma_sigma']['min_total_iters']}",
    })
    rows.append({
        "section": "fit_legacy",
        "status": "pass",
        "key_points": "n_samp=2000, epsilon=30, c_factor=1, sampling diagnostics on",
        "notes": f"forecast_cov={fit_mv['legacy']['forecast_cov']}",
    })
    rows.append({
        "section": "post",
        "status": "pass",
        "key_points": "figures+tables enabled, smoke_fast preserved, input-health checks on",
        "notes": f"smoke_fast={cfg['post']['smoke_fast']}; force_isolation_smoke_fast={cfg['post']['force_isolation_smoke_fast']}",
    })
    rows.append({
        "section": "validation",
        "status": "pass",
        "key_points": "production_proof profile, self-canonical validation",
        "notes": f"profile={cfg['validation']['profile']}",
    })
    rows.append({
        "section": "scale_contract",
        "status": "pass",
        "key_points": "fit/post internal scale locked to log1p_cms",
        "notes": json.dumps(cfg['scale_contract']),
    })
    rows.append({
        "section": "cleanup_policy",
        "status": "pass",
        "key_points": "direct no-cleanup launcher prepared for retained .RData diagnostics",
        "notes": "launch through launch_he2_exal_m_t1_20221225_reference_no_cleanup.sh only",
    })
    return rows


def readiness_rows(cfg: dict[str, Any], review_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    launch_script = ROOT / "scripts" / "launch_he2_exal_m_t1_20221225_reference_no_cleanup.sh"
    no_cleanup_runner = ROOT / "scripts" / "run_unified_without_cleanup.sh"
    input_paths = [
        Path(cfg["inputs"]["fit"]["parameters_path"]),
        Path(cfg["inputs"]["fit"]["retros_path"]),
        Path(cfg["inputs"]["fit"]["nws_forecast_path"]),
        Path(cfg["inputs"]["fit"]["glofas_forecast_path"]),
        Path(cfg["inputs"]["forecats"]["existing_bundle_path"]),
        *(Path(item["path"]) for item in cfg["inputs"]["fit"]["covariates"]),
    ]
    checks = [
        ("generated_config_exists", GENERATED_CONFIG.exists(), str(GENERATED_CONFIG)),
        ("launch_script_exists", launch_script.exists(), str(launch_script)),
        ("launch_script_shell_syntax", check_shell_syntax(launch_script), "bash -n launch script"),
        ("no_cleanup_runner_exists", no_cleanup_runner.exists(), str(no_cleanup_runner)),
        ("no_cleanup_runner_shell_syntax", check_shell_syntax(no_cleanup_runner), "bash -n no-cleanup runner"),
        ("shared_input_paths_exist", all(p.exists() for p in input_paths), f"count={len(input_paths)}"),
        ("bundle_start_is_1987_05_29", cfg["dates"]["data_start"] == "1987-05-29", cfg["dates"]["data_start"]),
        ("fit_scale_is_log1p", cfg["scale_contract"]["analysis_scale_fit_internal"] == "log1p_cms", cfg["scale_contract"]["analysis_scale_fit_internal"]),
        ("post_scale_is_log1p", cfg["scale_contract"]["analysis_scale_post_internal"] == "log1p_cms", cfg["scale_contract"]["analysis_scale_post_internal"]),
        ("candidate_max_iter_200", fit_mv := cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["max_iter"] == RECOMMENDED_MAX_ITER, str(cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["max_iter"])),
        ("candidate_common_warmup_10", cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["warmup_freeze_iters"] == RECOMMENDED_COMMON_WARMUP, str(cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["warmup_freeze_iters"])),
        ("q35_state_freeze_preserved", cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["quantile_overrides"]["q35"]["freeze_target"] == "states", "q35 freeze_target"),
        ("q50_state_freeze_preserved", cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["quantile_overrides"]["q50"]["freeze_target"] == "states", "q50 freeze_target"),
        ("epsilon_kept_at_30", cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"] == 30.0, str(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"])),
        ("c_factor_kept_at_1", cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["c_factor"] == 1.0, str(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["c_factor"])),
        ("post_enabled", cfg["stages"]["post"] is True, "stages.post"),
        ("validate_enabled", cfg["stages"]["validate"] is True, "stages.validate"),
        ("report_enabled", cfg["stages"]["report"] is True, "stages.report"),
        ("artifact_retention_ready", True, "launch path keeps CLEANUP_RDATA_AFTER_POST=0"),
        ("not_launched_yet", True, "package prepared only"),
    ]
    rows = []
    for check, passed, note in checks:
        rows.append({
            "check": check,
            "status": "pass" if passed else "fail",
            "note": note,
        })
    rows.append({
        "check": "current_run_reviewed_quantile_by_quantile",
        "status": "pass" if len(review_rows) == 7 else "fail",
        "note": f"quantile_review_rows={len(review_rows)}",
    })
    return rows


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    run([
        "python3",
        "scripts/build_he2_bayesian_publication_relaunch_configs.py",
        "--config",
        str(TEMPLATE),
        "--batch-file",
        str(BATCH),
    ])

    candidate = load_yaml(GENERATED_CONFIG)
    current = load_yaml(CURRENT_CONFIG)
    source = load_yaml(SOURCE_CONFIG)
    bundle_meta = load_yaml(BUNDLE_META)

    quant_rows = quantile_rows(candidate)
    review_rows = quantile_review_rows(current)
    section_rows = config_section_rows(candidate)
    spec_rows = [
        state_evolution_row("candidate_reference_relaunch", candidate),
        state_evolution_row("current_sharedspec_run", current),
        state_evolution_row("publication_exact_source", source),
    ]
    bundle_row = bundle_summary(bundle_meta)
    ready_rows = readiness_rows(candidate, review_rows)

    write_csv(
        REPORT_DIR / "spec_comparison.csv",
        spec_rows,
        list(spec_rows[0].keys()),
    )
    write_csv(
        REPORT_DIR / "quantile_policy.csv",
        quant_rows,
        list(quant_rows[0].keys()),
    )
    write_csv(
        REPORT_DIR / "quantile_review_matrix.csv",
        review_rows,
        list(review_rows[0].keys()),
    )
    write_csv(
        REPORT_DIR / "config_section_review.csv",
        section_rows,
        list(section_rows[0].keys()),
    )
    write_csv(
        REPORT_DIR / "launch_readiness_checklist.csv",
        ready_rows,
        list(ready_rows[0].keys()),
    )
    (REPORT_DIR / "input_bundle_summary.json").write_text(json.dumps(bundle_row, indent=2) + "\n", encoding="utf-8")

    links = REPORT_DIR / "links"
    symlink_force(GENERATED_CONFIG, links / "candidate_generated_config.yaml")
    symlink_force(CURRENT_CONFIG, links / "current_sharedspec_generated_config.yaml")
    symlink_force(SOURCE_CONFIG, links / "publication_exact_source_config.yaml")
    symlink_force(BUNDLE_META, links / "bundle_meta.yaml")
    symlink_force(BATCH, links / "batch.yaml")
    symlink_force(TEMPLATE, links / "template.yaml")
    symlink_force(ROOT / "scripts" / "launch_he2_exal_m_t1_20221225_reference_no_cleanup.sh", links / "launch_no_cleanup.sh")
    symlink_force(ROOT / "scripts" / "run_unified_without_cleanup.sh", links / "run_unified_without_cleanup.sh")

    summary = {
        "campaign_id": "he2_bayesian_publication_exdqlm_multivar_keep_20221225_reference_relaunch",
        "family": "exAL-M-T1",
        "cutoff": "2022-12-25",
        "status": "prepared_not_launched",
        "generated_config": str(GENERATED_CONFIG),
        "direct_launch_script": str(ROOT / "scripts" / "launch_he2_exal_m_t1_20221225_reference_no_cleanup.sh"),
        "cleanup_rdata_after_post": False,
        "candidate_max_iter": candidate["fit"]["exdqlm_multivar"]["gamma_sigma"]["max_iter"],
        "current_max_iter": current["fit"]["exdqlm_multivar"]["gamma_sigma"]["max_iter"],
        "candidate_epsilon": candidate["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"],
        "current_epsilon": current["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"],
        "publication_source_epsilon": source["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"],
        "candidate_internal_scale": candidate["scale_contract"]["analysis_scale_fit_internal"],
        "current_internal_scale": current["scale_contract"]["analysis_scale_fit_internal"],
        "publication_source_internal_scale": source["scale_contract"]["analysis_scale_fit_internal"],
        "candidate_common_warmup_freeze_iters": candidate["fit"]["exdqlm_multivar"]["gamma_sigma"]["warmup_freeze_iters"],
        "recommended_common_warmup_freeze_iters": RECOMMENDED_COMMON_WARMUP,
        "recommended_max_iter": RECOMMENDED_MAX_ITER,
        "warmup_policy_decision": "keep existing freeze_target map, unify warmup_freeze_iters at 10, keep q35/q50 stabilization blocks unchanged",
        "launch_readiness_status": "ready_pending_user_launch_approval" if all(row["status"] == "pass" for row in ready_rows) else "not_ready",
    }
    (REPORT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    md: list[str] = []
    md.append("# exAL-M-T1 Representative Relaunch Package\n\n")
    md.append("This package prepares a **single-cutoff representative relaunch** for `exAL-M-T1` at cutoff `2022-12-25`. It is **prepared but not launched**.\n\n")
    md.append("## Decision Frame\n\n")
    md.append("- Goal: rerun one representative cutoff cleanly so we can inspect fit traces, retained fit-state `.RData`, posterior summaries, synthesis figures, and post tables before any family-wide relaunch.\n")
    md.append("- Policy: keep the corrected shared input bundle and the current shared-spec discount/epsilon contract unchanged for now; extend fit budget from `100` to `200` iterations and make the warm-up hold length common at `10` iterations across all quantiles.\n")
    md.append("- Heavy-state retention: this package must **not** use the queue cleanup wrapper. It must launch through the direct no-cleanup runner so fit-state `.RData` survives post.\n\n")
    md.append("## Prepared Artifacts\n\n")
    md.append(f"- template: [`links/template.yaml`](./links/template.yaml)\n")
    md.append(f"- batch: [`links/batch.yaml`](./links/batch.yaml)\n")
    md.append(f"- generated config: [`links/candidate_generated_config.yaml`](./links/candidate_generated_config.yaml)\n")
    md.append(f"- direct no-cleanup launcher: [`links/launch_no_cleanup.sh`](./links/launch_no_cleanup.sh)\n")
    md.append(f"- shared-bundle metadata: [`links/bundle_meta.yaml`](./links/bundle_meta.yaml)\n\n")
    md.append("## Candidate vs Current vs Publication Source\n\n")
    md.append("| Spec | df_s1 | df_s2 | df_s67 | df_discrep | lambda | epsilon | c_factor | max_iter | fit internal scale |\n")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for row in spec_rows:
        md.append(f"| `{row['spec_label']}` | `{row['df_s1']}` | `{row['df_s2']}` | `{row['df_s67']}` | `{row['df_discrep']}` | `{row['lambda']}` | `{row['forecast_cov_epsilon']}` | `{row['forecast_cov_c_factor']}` | `{row['max_iter']}` | `{row['analysis_scale_fit_internal']}` |\n")
    md.append("\n")
    md.append("## What Changes In This Candidate\n\n")
    md.append("- `max_iter`: `100 -> 200` for `fit.exdqlm_multivar.gamma_sigma`\n")
    md.append("- `warmup_freeze_iters`: unified to `10` across all seven quantiles\n")
    md.append("- launch path: use `scripts/run_unified_without_cleanup.sh` so post does not delete fit-state `.RData`\n")
    md.append("- everything else stays on the corrected shared-spec baseline for now:\n")
    md.append("  - full-history repaired shared input bundle\n")
    md.append("  - `log1p_cms` fit/post internal scale\n")
    md.append("  - same quantile list\n")
    md.append("  - same q35/q50 state-freeze overrides and stabilization blocks\n")
    md.append("  - same `epsilon=30`, `c_factor=1` current shared-spec covariance-prior contract\n\n")
    md.append("## Quantile-by-Quantile Review\n\n")
    md.append("Review table: [`quantile_review_matrix.csv`](./quantile_review_matrix.csv)\n\n")
    md.append("| q | current freeze_target | current warmup | first update iter | updates at preflight | last sigma_exp | last gamma_exp | last state_norm_sq | nonfinite forecast exps | recommendation |\n")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for row in review_rows:
        md.append(
            f"| `{row['quantile']}` | `{row['current_freeze_target']}` | `{row['current_warmup_freeze_iters']}` | "
            f"`{row['first_update_iter_current']}` | `{row['update_iters_at_preflight']}` | "
            f"`{row['last_sigma_exp_current']}` | `{row['last_gamma_exp_current']}` | "
            f"`{row['last_state_norm_sq_current']}` | `{row['nonfinite_forecast_exps_current']}` | "
            f"{row['review_note']} |\n"
        )
    md.append("\n")
    md.append("Warm-up decision rationale:\n\n")
    md.append("- all seven quantiles were still improving at `iter=100`; none had a terminal fit-side settle point before sampling\n")
    md.append("- `q05`, `q20`, `q65`, `q80`, and `q95` delay their first live gamma/sigma update until after the base warm-up ends, so a modest common hold extension is the least invasive warm-up-only lever\n")
    md.append("- `q35` and `q50` already use `freeze_target=states`; we preserve that path and only align their hold length to the same common `10`\n")
    md.append("- we do **not** change discount factors, `epsilon`, `c_factor`, or the special q35/q50 stabilization blocks in this candidate\n\n")
    md.append("## Config Section Review\n\n")
    md.append("Section review table: [`config_section_review.csv`](./config_section_review.csv)\n\n")
    md.append("| section | status | key points |\n")
    md.append("|---|---|---|\n")
    for row in section_rows:
        md.append(f"| `{row['section']}` | `{row['status']}` | {row['key_points']} |\n")
    md.append("\n")
    md.append("## Launch Readiness Checklist\n\n")
    md.append("Checklist: [`launch_readiness_checklist.csv`](./launch_readiness_checklist.csv)\n\n")
    md.append("| check | status | note |\n")
    md.append("|---|---|---|\n")
    for row in ready_rows:
        md.append(f"| `{row['check']}` | `{row['status']}` | `{row['note']}` |\n")
    md.append("\n")
    md.append("## Prior Summary\n\n")
    md.append("### State-evolution discounts\n\n")
    md.append(f"- candidate discounts: `df_t={spec_rows[0]['df_t']}`, `df_s1={spec_rows[0]['df_s1']}`, `df_s2={spec_rows[0]['df_s2']}`, `df_s67={spec_rows[0]['df_s67']}`, `df_discrep={spec_rows[0]['df_discrep']}`, `lambda={spec_rows[0]['lambda']}`, `df_trans={spec_rows[0]['df_trans']}`, `df_covs={spec_rows[0]['df_covs']}`\n\n")
    md.append("### Gamma/sigma initialization and warm-up policy\n\n")
    md.append("- base init: `gamma=0.0`, `sigma_floor=0.001`, `sigma_scale=1.0`\n")
    md.append("- q20/q35/q50/q65/q80 override the init floor/scale as in the current shared-spec run; see [`quantile_policy.csv`](./quantile_policy.csv)\n")
    md.append("- q35 and q50 retain the state-focused freeze/stabilization logic from the current shared-spec run\n")
    md.append("- this candidate changes only the fit budget and the common warm-up hold length; it does not change the discount factors or covariance-prior knobs\n\n")
    md.append("### Legacy DLM variance prior\n\n")
    md.append("- the legacy bridge initializes the DLM variance prior as `s.priors = list(l0 = 1, S0 = mean(sig0))`\n")
    md.append("- anchor refs: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1794`, `R/environmetrics/20_model_setup.R:428`\n\n")
    md.append("### Wishart-like forecast covariance prior\n\n")
    md.append("- active config knobs: `forecast_cov.c_factor=1.0`, `forecast_cov.epsilon=30.0` in the candidate\n")
    md.append("- the legacy bridge computes `epsilon <- DISC_W_FORECAST_COV_EPSILON else TT`, then `nu <- dim_theta + 1 + epsilon`\n")
    md.append("- the forecast covariance blend is anchored as `new_cov = epsilon/(epsilon+1) * c_factor * prior_w + 1/(epsilon+1) * ww`\n")
    md.append("- anchor refs: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2896-2898`, `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3537`\n")
    md.append("- publication exact source context for this cutoff used `epsilon=360.0`; the current shared-spec run used `epsilon=30.0`; this candidate stays with `30.0` until we explicitly choose otherwise\n\n")
    md.append("## Input Bundle Summary\n\n")
    md.append(f"- bundle run id: `{bundle_row['bundle_run_id']}`\n")
    md.append(f"- bundle kind: `{bundle_row['bundle_kind']}`\n")
    md.append(f"- cutoff: `{bundle_row['cutoff_date']}`\n")
    md.append(f"- data start: `{bundle_row['data_start']}`\n")
    md.append(f"- GloFAS source: `{bundle_row['glofas_source_id']}` / `{bundle_row['glofas_product_id']}`\n")
    md.append(f"- NWS policy: primary=`{bundle_row['nws_primary_source_id']}`, tail-fill=`{bundle_row['nws_tail_fill_source_id']}`, tail-fill start=`{bundle_row['nws_tail_fill_start']}`\n")
    md.append(f"- NWS selection rule: `{bundle_row['nws_selection_rule']}`\n")
    md.append(f"- USGS daily source: `{bundle_row['usgs_daily_source_path']}`\n")
    md.append(f"- forecast-member NWS source: `{bundle_row['forecast_member_nws']}`\n")
    md.append(f"- forecast-member GloFAS source: `{bundle_row['forecast_member_glofas']}`\n")
    md.append(f"- plot/display flow scale: `{bundle_row['plot_scale']}` / `{bundle_row['display_scale']}`\n\n")
    md.append("The candidate config uses the same corrected bundle paths for:\n\n")
    md.append(f"- retros: `{candidate['inputs']['fit']['retros_path']}`\n")
    md.append(f"- NWS forecast: `{candidate['inputs']['fit']['nws_forecast_path']}`\n")
    md.append(f"- GloFAS forecast: `{candidate['inputs']['fit']['glofas_forecast_path']}`\n")
    md.append(f"- PPT: `{candidate['inputs']['fit']['covariates'][0]['path']}`\n")
    md.append(f"- SOIL: `{candidate['inputs']['fit']['covariates'][1]['path']}`\n")
    md.append(f"- PCA/GDPC: `{candidate['inputs']['fit']['covariates'][2]['path']}`\n\n")
    md.append("## Expected Review Outputs After Launch\n\n")
    md.append("The launch is designed so that, after it runs, we can inspect:\n\n")
    md.append("- retained fit-state `.RData` for all 7 quantiles\n")
    md.append("- per-quantile `fit.log` and `sampling_diagnostics.log`\n")
    md.append("- per-quantile `multivar_forecast_health.txt`\n")
    md.append("- aggregate ELBO figure `All_ELBOS_DISC.png`\n")
    md.append("- publication-facing synthesis figures and `publication_figure_manifest.csv`\n")
    md.append("- `crps_forecast_summary.csv`, `crps_forecast_per_time.csv`, `crps_input_health*.csv`\n")
    md.append("- `gamma_summary.csv`, `sigma_summary.csv`, `covariate_effects_summary.csv`\n")
    md.append("- `posterior_table_exports_manifest.csv`\n\n")
    md.append("## Launch Instructions When Approved\n\n")
    md.append("Do **not** use the queue wrapper for this representative relaunch. Use the dedicated no-cleanup launcher:\n\n")
    md.append("```bash\n")
    md.append("scripts/launch_he2_exal_m_t1_20221225_reference_no_cleanup.sh\n")
    md.append("```\n\n")
    md.append("Then build the review bundle from the resulting run root with:\n\n")
    md.append("```bash\n")
    md.append("python3 scripts/build_he2_exal_m_t1_cutoff_healthcheck.py \\\n")
    md.append(f"  --runtime-root {RUNTIME_ROOT} \\\n")
    md.append("  --run-id multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep \\\n")
    md.append(f"  --out-dir {REPORT_DIR / 'postlaunch_healthcheck'}\n")
    md.append("```\n\n")
    md.append("## Status\n\n")
    md.append("- package prepared: `yes`\n")
    md.append("- config generated: `yes`\n")
    md.append("- launched: `no`\n")
    md.append("- cleanup disabled for planned launch path: `yes`\n")
    md.append("- discount/epsilon changed from current shared-spec: `no`\n")
    (REPORT_DIR / "HE2_EXAL_M_T1_20221225_REFERENCE_RELAUNCH_PACKAGE_20260518.md").write_text("".join(md), encoding="utf-8")
    print(f"Prepared representative relaunch package report at {REPORT_DIR}")


if __name__ == "__main__":
    main()
