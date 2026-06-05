#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from he2_publication_relaunch_lib import EXPECTED_CUTOFFS, initialize_matrix_status  # noqa: E402


SOURCE_FAMILY = "exdqlm_multivar_drop"
SOURCE_LABEL = "exAL-M-T0"
SOURCE_MODEL_ID = "exdqlm_multivar_synth_drop"
TARGET_FAMILY = "dqlm_multivar_al_drop"
TARGET_LABEL = "AL-M-T0"
TARGET_MODEL_ID = "dqlm_multivar_al_synth_drop"
TARGET_MODEL_KEY = "exdqlm_multivar"
CAMPAIGN_SPEC_ID = "he2pubgdpc1r1"
RUN_ROWS_AT_ONCE = 2
QUANTILE_WORKERS_PER_RUN = 7
MAX_ACTIVE_QUANTILE_WORKERS = RUN_ROWS_AT_ONCE * QUANTILE_WORKERS_PER_RUN
SOURCE_ARTIFACT_ROOT = (
    ROOT.parent / "project1_ucsc_phd_runtime" / "multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602"
)
DEFAULT_ARTIFACT_ROOT = (
    ROOT.parent / "project1_ucsc_phd_runtime" / "multimodel_v8_he2_dqlm_multivar_al_drop_from_exal_drop_20260603"
)
DEFAULT_P3_POLICY_SPEC = (
    ROOT / "config" / "he2_relaunch_batches" / "al_m_t0_p3_production_overlay_20260605.yaml"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True)
    except Exception:
        return "unknown"
    return out.strip()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, default_flow_style=False)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cutoff_dash(cutoff: str) -> str:
    cutoff = str(cutoff).zfill(8)
    return f"{cutoff[:4]}-{cutoff[4:6]}-{cutoff[6:8]}"


def source_run_id(cutoff: str) -> str:
    return f"multimodel_{cutoff}_v8_{CAMPAIGN_SPEC_ID}_{SOURCE_FAMILY}"


def target_run_id(cutoff: str) -> str:
    return f"multimodel_{cutoff}_v8_{CAMPAIGN_SPEC_ID}_{TARGET_FAMILY}"


def parse_cutoff_list(value: str | None) -> list[str] | None:
    if value is None or not str(value).strip():
        return None
    cutoffs: list[str] = []
    for item in str(value).split(","):
        item = item.strip()
        if not item:
            continue
        compact = item.replace("-", "")
        if len(compact) != 8 or not compact.isdigit():
            raise ValueError(f"invalid cutoff value: {item}")
        cutoffs.append(compact)
    unknown = sorted(set(cutoffs) - set(EXPECTED_CUTOFFS))
    if unknown:
        raise ValueError(f"unknown cutoff(s): {', '.join(unknown)}")
    return cutoffs


def nested(payload: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def input_paths_for_row(cfg: dict[str, Any]) -> dict[str, str]:
    covariates = nested(cfg, ["inputs", "fit", "covariates"], [])
    return {
        "parameters_path": str(nested(cfg, ["inputs", "fit", "parameters_path"], "")),
        "retros_path": str(nested(cfg, ["inputs", "fit", "retros_path"], "")),
        "nws_forecast_path": str(nested(cfg, ["inputs", "fit", "nws_forecast_path"], "")),
        "glofas_forecast_path": str(nested(cfg, ["inputs", "fit", "glofas_forecast_path"], "")),
        "forecats_existing_bundle_path": str(nested(cfg, ["inputs", "forecats", "existing_bundle_path"], "")),
        "covariates_json": json.dumps(covariates, sort_keys=True),
    }


def source_config_path(source_root: Path, cutoff: str) -> Path:
    return source_root / "control" / "generated_configs" / f"{source_run_id(cutoff)}.yaml"


def update_debug_blocks(
    cfg: dict[str, Any],
    *,
    cutoff: str,
    source_cfg_path: Path,
    target_cfg_path: Path,
    source_root: Path,
    artifact_root: Path,
    code_commit: str,
    policy_spec: dict[str, Any] | None = None,
) -> None:
    policy_spec_id = str(policy_spec.get("spec_id", "")) if isinstance(policy_spec, dict) else ""
    if isinstance(cfg.get("debug_featurecov_cf1_eps_campaign"), dict):
        debug = cfg["debug_featurecov_cf1_eps_campaign"]
        debug["family_id"] = TARGET_FAMILY
        debug["model_id"] = TARGET_MODEL_ID
        debug["model_key"] = TARGET_MODEL_KEY
        debug["likelihood_mode"] = "al"
        debug["transfer_mode"] = "drop"
        debug["selected_source_run"] = source_run_id(cutoff)
        debug["selected_source_type"] = "exdqlm_multivar_drop_current_q50repair_al_clone_20260603"
        debug["selected_source_config"] = str(source_cfg_path)
        if policy_spec_id:
            debug["selected_spec_token"] = policy_spec_id

    if isinstance(cfg.get("debug_he2_publication_relaunch"), dict):
        debug = cfg["debug_he2_publication_relaunch"]
        debug["source_publication_run_id"] = source_run_id(cutoff)
        debug["source_publication_run_root"] = str(source_root / "runs" / source_run_id(cutoff))
        debug["source_publication_resolved_config"] = str(source_cfg_path)
        debug["campaign_lineage"] = "dqlm_multivar_al_drop_from_exdqlm_drop_q50repair_20260603"
        debug["manuscript_label"] = TARGET_LABEL
        debug["family"] = TARGET_FAMILY
        debug["model_class"] = "quantile_multivariate"
        debug["implementation_mode"] = "legacy_bridge"
        debug["likelihood_mode"] = "al"
        debug["forecast_transfer_mode"] = "drop"
        debug["publication_crps_display4"] = ""
        debug["selected_spec_token"] = policy_spec_id or "eps030_cf1_highdiscount_drop_clone"
        debug["model_config_key"] = TARGET_MODEL_KEY
        debug["config_patch_applied"] = True
        debug["config_patch_source"] = str(ROOT / "scripts" / "build_he2_dqlm_multivar_al_drop_from_exal_drop.py")

    cfg["debug_he2_dqlm_al_drop_from_exal_drop"] = {
        "status": "prepared_not_launched",
        "generated_at_utc": utc_now(),
        "builder": str(ROOT / "scripts" / "build_he2_dqlm_multivar_al_drop_from_exal_drop.py"),
        "code_commit": code_commit,
        "source_artifact_root": str(source_root),
        "source_family": SOURCE_FAMILY,
        "source_label": SOURCE_LABEL,
        "source_model_id": SOURCE_MODEL_ID,
        "source_likelihood_mode": "exal",
        "source_run_id": source_run_id(cutoff),
        "source_config_path": str(source_cfg_path),
        "target_artifact_root": str(artifact_root),
        "target_family": TARGET_FAMILY,
        "target_label": TARGET_LABEL,
        "target_model_id": TARGET_MODEL_ID,
        "target_model_key": TARGET_MODEL_KEY,
        "target_likelihood_mode": "al",
        "target_run_id": target_run_id(cutoff),
        "target_config_path": str(target_cfg_path),
        "likelihood_switch": "exal_to_al",
        "forecast_transfer_mode": "drop",
        "input_and_state_contract": (
            "Preserve promoted exAL-M-T0 inputs, dates, trend/full-harmonic structure, transfer covariates, "
            "discount factors, epsilon, c_factor, max_iter, and post/report wiring exactly."
        ),
        "expected_gamma_contract": "DISC_W_LIKELIHOOD_MODE=al forces gamma draws and gamma moments to zero.",
        "expected_st_contract": "DISC_W_AL_MODE makes update_sts return zero E.sts/E.sts2 for the active AL likelihood path.",
        "no_launch": True,
    }
    if policy_spec_id:
        cfg["debug_he2_dqlm_al_drop_from_exal_drop"]["policy_spec_id"] = policy_spec_id
        cfg["debug_he2_dqlm_al_drop_from_exal_drop"]["policy_spec_description"] = str(
            policy_spec.get("description", "")
        )


def apply_policy_spec(cfg: dict[str, Any], policy_spec: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(policy_spec, dict) or not policy_spec:
        return cfg

    model_cfg = cfg.setdefault("models", {}).setdefault(TARGET_MODEL_KEY, {})
    fit_model_cfg = cfg.setdefault("fit", {}).setdefault(TARGET_MODEL_KEY, {})
    legacy_cfg = fit_model_cfg.setdefault("legacy", {})

    if isinstance(policy_spec.get("state_evolution"), dict):
        model_cfg["state_evolution"] = deep_merge(
            model_cfg.get("state_evolution", {}) if isinstance(model_cfg.get("state_evolution"), dict) else {},
            policy_spec["state_evolution"],
        )

    if isinstance(policy_spec.get("forecast_cov"), dict):
        legacy_cfg["forecast_cov"] = deep_merge(
            legacy_cfg.get("forecast_cov", {}) if isinstance(legacy_cfg.get("forecast_cov"), dict) else {},
            policy_spec["forecast_cov"],
        )

    if isinstance(policy_spec.get("legacy"), dict):
        legacy_cfg.update(deepcopy(policy_spec["legacy"]))

    # The legacy AL-drop entrypoint performs the actual fit/save operation inside
    # objective_deltas(...). The production P3 overlay must therefore force this
    # bridge on instead of inheriting a null/false source value.
    legacy_cfg["post_save_objective_enabled"] = True
    legacy_cfg["post_save_jsd_enabled"] = False

    if isinstance(policy_spec.get("gamma_sigma"), dict):
        fit_model_cfg["gamma_sigma"] = deep_merge(
            fit_model_cfg.get("gamma_sigma", {}) if isinstance(fit_model_cfg.get("gamma_sigma"), dict) else {},
            policy_spec["gamma_sigma"],
        )

    if isinstance(policy_spec.get("fit"), dict):
        fit_model_cfg.update(deep_merge(fit_model_cfg, policy_spec["fit"]))

    cfg.setdefault("debug_he2_dqlm_al_drop_policy_overlay", {})
    cfg["debug_he2_dqlm_al_drop_policy_overlay"] = {
        "applied": True,
        "spec_id": str(policy_spec.get("spec_id", "")),
        "description": str(policy_spec.get("description", "")),
        "state_evolution_overridden": isinstance(policy_spec.get("state_evolution"), dict),
        "forecast_cov_overridden": isinstance(policy_spec.get("forecast_cov"), dict),
        "gamma_sigma_overridden": isinstance(policy_spec.get("gamma_sigma"), dict),
        "legacy_post_save_objective_forced": True,
    }
    return cfg


def clone_config(
    source_cfg: dict[str, Any],
    *,
    cutoff: str,
    source_cfg_path: Path,
    target_cfg_path: Path,
    source_root: Path,
    artifact_root: Path,
    code_commit: str,
    policy_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = deepcopy(source_cfg)
    run_id = target_run_id(cutoff)
    run_root = artifact_root / "runs"

    cfg.setdefault("run", {})
    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(run_root)
    cfg["run"]["resolved_run_root"] = str(run_root / run_id)
    cfg["run"]["resolved_config_path"] = str(target_cfg_path)
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = False
    cfg["run"]["dry_run"] = False
    cfg["run"]["git_require_clean"] = False

    cfg.setdefault("models", {})
    cfg["models"]["run_exdqlm_multivar"] = True
    cfg["models"]["run_exdqlm_univar"] = False
    cfg["models"]["run_ndlm_main"] = False
    cfg["models"]["run_ndlm_univar"] = False
    cfg["models"].setdefault(TARGET_MODEL_KEY, {})
    cfg["models"][TARGET_MODEL_KEY]["likelihood_mode"] = "al"
    cfg["models"][TARGET_MODEL_KEY]["forecast_transfer_mode"] = "drop"
    cfg = apply_policy_spec(cfg, policy_spec)

    update_debug_blocks(
        cfg,
        cutoff=cutoff,
        source_cfg_path=source_cfg_path,
        target_cfg_path=target_cfg_path,
        source_root=source_root,
        artifact_root=artifact_root,
        code_commit=code_commit,
        policy_spec=policy_spec,
    )
    return cfg


def build_package(
    artifact_root: Path,
    *,
    source_artifact_root: Path = SOURCE_ARTIFACT_ROOT,
    reset_status: bool = True,
    policy_spec_path: Path | None = None,
    selected_cutoffs: list[str] | None = None,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    source_artifact_root = source_artifact_root.resolve()
    matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
    config_output_dir = artifact_root / "control" / "generated_configs"
    matrix_dir.mkdir(parents=True, exist_ok=True)
    config_output_dir.mkdir(parents=True, exist_ok=True)

    code_commit = git_head()
    policy_spec: dict[str, Any] | None = None
    if policy_spec_path is not None:
        policy_spec_path = policy_spec_path.resolve()
        policy_spec = load_yaml(policy_spec_path)
        if not str(policy_spec.get("spec_id", "")).strip():
            raise ValueError(f"policy spec missing spec_id: {policy_spec_path}")
    selected_cutoffs = selected_cutoffs or list(EXPECTED_CUTOFFS)
    unknown = sorted(set(selected_cutoffs) - set(EXPECTED_CUTOFFS))
    if unknown:
        raise ValueError(f"unknown selected cutoff(s): {', '.join(unknown)}")
    plan_rows: list[dict[str, Any]] = []
    frozen_rows: list[dict[str, Any]] = []
    clone_rows: list[dict[str, Any]] = []
    bundle_rows: list[dict[str, Any]] = []

    for order_index, cutoff in enumerate(selected_cutoffs, 1):
        src_path = source_config_path(source_artifact_root, cutoff)
        if not src_path.exists():
            raise FileNotFoundError(f"missing promoted exAL-M-T0 source config: {src_path}")
        src_cfg = load_yaml(src_path)
        tgt_path = config_output_dir / f"{target_run_id(cutoff)}.yaml"
        target_cfg = clone_config(
            src_cfg,
            cutoff=cutoff,
            source_cfg_path=src_path,
            target_cfg_path=tgt_path,
            source_root=source_artifact_root,
            artifact_root=artifact_root,
            code_commit=code_commit,
            policy_spec=policy_spec,
        )
        write_yaml(tgt_path, target_cfg)

        paths = input_paths_for_row(target_cfg)
        state = nested(target_cfg, ["models", TARGET_MODEL_KEY, "state_evolution"], {}) or {}
        legacy = nested(target_cfg, ["fit", TARGET_MODEL_KEY, "legacy"], {}) or {}
        forecast_cov = legacy.get("forecast_cov", {}) if isinstance(legacy, dict) else {}
        active_quantiles = nested(target_cfg, ["fit", "quantiles"], []) or []
        src_hash = sha256(src_path)
        tgt_hash = sha256(tgt_path)
        row = {
            "order_index": order_index,
            "cutoff": cutoff,
            "epsilon": CAMPAIGN_SPEC_ID,
            "epsilon_value": CAMPAIGN_SPEC_ID,
            "lane": TARGET_FAMILY,
            "run_scope": "he2_dqlm_multivar_al_drop_from_exal_drop_20260603",
            "run_id": target_run_id(cutoff),
            "config_path": str(tgt_path),
            "compare_outdir": "",
            "priority_group": 2 if cutoff == "20221225" else 1,
            "max_concurrent_class": "heavy" if cutoff == "20221225" else "ordinary",
            "family_id": TARGET_FAMILY,
            "model_id": TARGET_MODEL_ID,
            "model_key": TARGET_MODEL_KEY,
            "model_class": "quantile_multivariate",
            "manuscript_label": TARGET_LABEL,
            "likelihood_mode": "al",
            "transfer_mode": "drop",
            "row_kind": "quantile_multivariate",
            "quantile_submodels": len(active_quantiles),
            "active_quantiles": "|".join(f"{int(round(float(q) * 100)):02d}" for q in active_quantiles),
            "profile_name": "al_drop_from_exal_drop_20260603",
            "policy_spec_id": str(policy_spec.get("spec_id", "")) if policy_spec else "",
            "policy_spec_path": str(policy_spec_path) if policy_spec_path is not None else "",
            "policy_overlay_applied": bool(policy_spec),
            "selected_source_run": source_run_id(cutoff),
            "selected_source_type": "exdqlm_multivar_drop_current_q50repair_al_clone_20260603",
            "selected_source_config": str(src_path),
            "source_family_id": SOURCE_FAMILY,
            "source_model_id": SOURCE_MODEL_ID,
            "source_likelihood_mode": "exal",
            "df_t": state.get("df_t"),
            "df_s1": state.get("df_s1"),
            "df_s2": state.get("df_s2"),
            "df_s67": state.get("df_s67"),
            "df_discrep": state.get("df_discrep"),
            "lambda": state.get("lambda"),
            "df_trans": state.get("df_trans"),
            "df_covs": state.get("df_covs"),
            "c_factor": forecast_cov.get("c_factor"),
            "forecast_cov_epsilon": forecast_cov.get("epsilon"),
            "max_iter": nested(target_cfg, ["fit", TARGET_MODEL_KEY, "gamma_sigma", "max_iter"], ""),
            "min_update_iters": nested(target_cfg, ["fit", TARGET_MODEL_KEY, "gamma_sigma", "min_update_iters"], ""),
            "min_total_iters": nested(target_cfg, ["fit", TARGET_MODEL_KEY, "gamma_sigma", "min_total_iters"], ""),
            "post_save_objective_enabled": nested(
                target_cfg, ["fit", TARGET_MODEL_KEY, "legacy", "post_save_objective_enabled"], ""
            ),
            "data_start": str(nested(target_cfg, ["dates", "data_start"], "")),
            "cutoff_date": str(nested(target_cfg, ["dates", "cutoff_date"], cutoff_dash(cutoff))),
            "artifact_root": str(artifact_root),
            "run_root": str(artifact_root / "runs" / target_run_id(cutoff)),
            "matrix_dir": str(matrix_dir),
            "source_config_sha256": src_hash,
            "target_config_sha256": tgt_hash,
            **paths,
        }
        plan_rows.append(row)
        frozen_rows.append(dict(row))
        clone_rows.append(
            {
                "cutoff": cutoff,
                "source_run_id": source_run_id(cutoff),
                "source_config_path": str(src_path),
                "source_config_sha256": src_hash,
                "target_run_id": target_run_id(cutoff),
                "target_config_path": str(tgt_path),
                "target_config_sha256": tgt_hash,
                "only_intended_scientific_change": "likelihood_mode exal -> al",
            }
        )
        bundle_rows.append(
            {
                "cutoff": cutoff,
                "cutoff_date": cutoff_dash(cutoff),
                "run_id": target_run_id(cutoff),
                "bundle_meta": paths["forecats_existing_bundle_path"],
                "parameters_path": paths["parameters_path"],
                "retros_path": paths["retros_path"],
                "nws_forecast_path": paths["nws_forecast_path"],
                "glofas_forecast_path": paths["glofas_forecast_path"],
                "covariates_json": paths["covariates_json"],
            }
        )

    write_csv(matrix_dir / "matrix_plan.csv", plan_rows)
    write_csv(matrix_dir / "frozen_spec_manifest.csv", frozen_rows)
    write_csv(matrix_dir / "source_clone_manifest.csv", clone_rows)
    write_csv(matrix_dir / "cutoff_bundle_audit.csv", bundle_rows)
    write_csv(matrix_dir / "al_drop_run_registry.csv", frozen_rows)

    queue = {
        "ordinary_max_concurrent": RUN_ROWS_AT_ONCE,
        "pause_free_gb": 25.0,
        "launch_free_gb": 35.0,
        "heavy_free_gb": 35.0,
        "pause_mem_gb": 0.0,
        "launch_mem_gb": 0.0,
        "heavy_mem_gb": 0.0,
        "heavy_cutoff_max_concurrent": RUN_ROWS_AT_ONCE,
        "heavy_cutoff_blocks_ordinary": False,
        "poll_seconds": 30,
    }
    resources = {"fit_parallel_workers": QUANTILE_WORKERS_PER_RUN, "mc_cores": QUANTILE_WORKERS_PER_RUN}
    metadata = {
        "generated_at_utc": utc_now(),
        "status": "prepared_not_launched",
        "campaign_id": "he2_dqlm_multivar_al_drop_from_exal_drop_20260603",
        "campaign_spec_id": CAMPAIGN_SPEC_ID,
        "source_artifact_root": str(source_artifact_root),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "source_family": SOURCE_FAMILY,
        "source_label": SOURCE_LABEL,
        "source_model_id": SOURCE_MODEL_ID,
        "target_family": TARGET_FAMILY,
        "target_label": TARGET_LABEL,
        "target_model_id": TARGET_MODEL_ID,
        "target_model_key": TARGET_MODEL_KEY,
        "likelihood_switch": "exal_to_al",
        "forecast_transfer_mode": "drop",
        "active_quantiles": ["05", "20", "35", "50", "65", "80", "95"],
        "policy_spec_id": str(policy_spec.get("spec_id", "")) if policy_spec else "",
        "policy_spec_path": str(policy_spec_path) if policy_spec_path is not None else "",
        "policy_overlay_applied": bool(policy_spec),
        "selected_cutoffs": selected_cutoffs,
        "n_cutoffs": len(selected_cutoffs),
        "n_run_rows": len(plan_rows),
        "n_quantile_fits": len(plan_rows) * QUANTILE_WORKERS_PER_RUN,
        "queue": queue,
        "resources": resources,
        "run_rows_at_once": RUN_ROWS_AT_ONCE,
        "quantile_workers_per_run": QUANTILE_WORKERS_PER_RUN,
        "max_active_quantile_workers": MAX_ACTIVE_QUANTILE_WORKERS,
        "cleanup_rdata_after_post": True,
        "skip_compare_bundles": True,
        "continue_on_fail": True,
        "code_commit": code_commit,
    }
    write_yaml(matrix_dir / "matrix_metadata.yaml", metadata)
    if reset_status:
        initialize_matrix_status(matrix_dir / "matrix_status.csv")
    else:
        (matrix_dir / "matrix_status.csv").touch()
    (matrix_dir / "queue.log").touch()

    launch_cmd = [
        "python3",
        "scripts/run_multimodel_v8_queue.py",
        "--matrix-dir",
        str(matrix_dir),
        "--artifact-root",
        str(artifact_root),
        "--ordinary-max-concurrent",
        str(queue["ordinary_max_concurrent"]),
        "--pause-free-gb",
        str(queue["pause_free_gb"]),
        "--launch-free-gb",
        str(queue["launch_free_gb"]),
        "--heavy-free-gb",
        str(queue["heavy_free_gb"]),
        "--pause-mem-gb",
        str(queue["pause_mem_gb"]),
        "--launch-mem-gb",
        str(queue["launch_mem_gb"]),
        "--heavy-mem-gb",
        str(queue["heavy_mem_gb"]),
        "--heavy-cutoff-max-concurrent",
        str(queue["heavy_cutoff_max_concurrent"]),
        "--poll-seconds",
        str(queue["poll_seconds"]),
        "--continue-on-fail",
        "--skip-compares",
        "--no-heavy-cutoff-blocks-ordinary",
    ]
    launch_env = "\n".join(
        [
            f"ARTIFACT_ROOT={artifact_root}",
            f"MATRIX_DIR={matrix_dir}",
            f"ORDINARY_MAX_CONCURRENT={queue['ordinary_max_concurrent']}",
            f"PAUSE_FREE_GB={queue['pause_free_gb']}",
            f"LAUNCH_FREE_GB={queue['launch_free_gb']}",
            f"HEAVY_FREE_GB={queue['heavy_free_gb']}",
            f"PAUSE_MEM_GB={queue['pause_mem_gb']}",
            f"LAUNCH_MEM_GB={queue['launch_mem_gb']}",
            f"HEAVY_MEM_GB={queue['heavy_mem_gb']}",
            f"HEAVY_CUTOFF_MAX_CONCURRENT={queue['heavy_cutoff_max_concurrent']}",
            f"HEAVY_CUTOFF_BLOCKS_ORDINARY={1 if queue['heavy_cutoff_blocks_ordinary'] else 0}",
            f"POLL_SECONDS={queue['poll_seconds']}",
            "CONTINUE_ON_FAIL=1",
            "SKIP_COMPARES=1",
            "",
        ]
    )
    (matrix_dir / "launch_settings.env").write_text(launch_env, encoding="utf-8")
    (matrix_dir / "launch_al_drop_from_exal_drop.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\ncd " + str(ROOT) + "\n" + " ".join(launch_cmd) + "\n",
        encoding="utf-8",
    )

    scope_lines = [
        "# HE2 AL-M-T0 From exAL-M-T0 Drop Clone Scope",
        "",
        "- status: `prepared_not_launched`",
        f"- source family: `{SOURCE_LABEL}` / `{SOURCE_FAMILY}`",
        f"- target family: `{TARGET_LABEL}` / `{TARGET_FAMILY}`",
        f"- source artifact root: `{source_artifact_root}`",
        f"- target artifact root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- generated configs: `{config_output_dir}`",
        f"- run rows: `{len(plan_rows)}`",
        f"- quantile fits: `{len(plan_rows) * QUANTILE_WORKERS_PER_RUN}`",
        f"- run rows at once: `{RUN_ROWS_AT_ONCE}`",
        f"- quantile workers per run: `{QUANTILE_WORKERS_PER_RUN}`",
        f"- max active quantile workers: `{MAX_ACTIVE_QUANTILE_WORKERS}`",
        "- intended scientific change: `likelihood_mode: exal -> al`",
        "- preserved: source input bundle paths, cutoff dates, data start, harmonics, transfer covariates, discount factors, epsilon, c_factor, and max_iter.",
        "- cleanup after post: `true`",
        "",
        "## Launch Command",
        "",
        "```bash",
        " ".join(launch_cmd),
        "```",
        "",
        "## Key Files",
        "",
        "- `matrix_plan.csv`",
        "- `frozen_spec_manifest.csv`",
        "- `source_clone_manifest.csv`",
        "- `cutoff_bundle_audit.csv`",
        "- `al_drop_run_registry.csv`",
        "- `matrix_metadata.yaml`",
    ]
    (matrix_dir / "AL_DROP_FROM_EXAL_DROP_SCOPE.md").write_text("\n".join(scope_lines) + "\n", encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare AL-M-T0 configs by cloning the promoted current-code exAL-M-T0 drop configs."
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--source-artifact-root", type=Path, default=SOURCE_ARTIFACT_ROOT)
    parser.add_argument("--no-reset-status", action="store_true")
    parser.add_argument(
        "--policy-spec-yaml",
        type=Path,
        help="Optional explicit AL-M-T0 production policy overlay, for example the P3 stabilization spec.",
    )
    parser.add_argument(
        "--cutoffs",
        help="Optional comma-separated cutoff subset, e.g. 20211112,20220511 for smoke packaging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = build_package(
        args.artifact_root.resolve(),
        source_artifact_root=args.source_artifact_root.resolve(),
        reset_status=not args.no_reset_status,
        policy_spec_path=args.policy_spec_yaml,
        selected_cutoffs=parse_cutoff_list(args.cutoffs),
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
