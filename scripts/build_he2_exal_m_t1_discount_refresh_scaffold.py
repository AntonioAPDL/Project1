#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
SOURCE_CONFIG = (
    Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")
    / "multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518"
    / "control"
    / "generated_configs"
    / "multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep_bridgefix_20260518.yaml"
)
TARGET_RUNTIME_ROOT = (
    Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")
    / "multimodel_v8_he2_exdqlm_multivar_keep_20221225_discount_refresh_20260518"
)
DEFAULT_SPEC_LABEL = "pending_discount_spec"
STATE_KEYS = [
    "df_t",
    "df_s1",
    "df_s2",
    "df_s67",
    "df_discrep",
    "lambda",
    "df_trans",
    "df_covs",
]


def _normalize_string_list(raw: Any, label: str) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        vals = [part.strip() for part in raw.split(",")]
    else:
        vals = [str(v).strip() for v in raw]
    vals = [v for v in vals if v]
    if any(not v for v in vals):
        raise ValueError(f"{label} entries must be non-empty strings")
    # preserve order, de-duplicate
    return list(dict.fromkeys(vals))


def load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return payload


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Prepare a new exAL-M-T1 discount-refresh launch scaffold from the bridge-fixed representative config."
    )
    ap.add_argument("--source-config", type=Path, default=SOURCE_CONFIG)
    ap.add_argument("--target-runtime-root", type=Path, default=TARGET_RUNTIME_ROOT)
    ap.add_argument("--spec-label", default=DEFAULT_SPEC_LABEL)
    ap.add_argument("--discount-spec", type=Path, help="Optional YAML/JSON file with state_evolution overrides.")
    ap.add_argument(
        "--cleanup-mode",
        choices=("with_cleanup", "without_cleanup"),
        default="with_cleanup",
        help="Choose whether the launch wrapper should delete retained fit-state .RData after post.",
    )
    ap.add_argument("--cleanup-report-dir", type=Path, default=ROOT / "reports" / "he2_exal_m_t1_discount_refresh_scaffold_20260518")
    return ap.parse_args()


def normalize_state_evolution(raw: dict[str, Any]) -> dict[str, float]:
    missing = [key for key in STATE_KEYS if key not in raw]
    if missing:
        raise ValueError(f"Discount spec missing keys: {', '.join(missing)}")
    out: dict[str, float] = {}
    for key in STATE_KEYS:
        out[key] = float(raw[key])
    return out


def _as_float(raw: Any, label: str) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric; got {raw!r}") from exc


def _normalize_forecast_cov(raw: dict[str, Any]) -> dict[str, float]:
    return {
        "c_factor": _as_float(raw["c_factor"], "forecast_cov.c_factor"),
        "epsilon": _as_float(raw["epsilon"], "forecast_cov.epsilon"),
    }


def _normalize_gamsig_init(raw: dict[str, Any]) -> dict[str, float | str]:
    return {
        "mode": str(raw.get("mode", "robust")),
        "gamma": _as_float(raw["gamma"], "gamma_sigma.init.gamma"),
        "sigma_floor": _as_float(raw["sigma_floor"], "gamma_sigma.init.sigma_floor"),
        "sigma_scale": _as_float(raw["sigma_scale"], "gamma_sigma.init.sigma_scale"),
    }


def _normalize_gamsig_priors(raw: dict[str, Any]) -> dict[str, dict[str, float]]:
    sigma = raw.get("sigma", {})
    gamma = raw.get("gamma", {})
    if not isinstance(sigma, dict) or not isinstance(gamma, dict):
        raise ValueError("gamma_sigma.priors must contain sigma and gamma mappings")
    return {
        "sigma": {
            "mean": _as_float(sigma["mean"], "gamma_sigma.priors.sigma.mean"),
            "variance": _as_float(sigma["variance"], "gamma_sigma.priors.sigma.variance"),
        },
        "gamma": {
            "location": _as_float(gamma["location"], "gamma_sigma.priors.gamma.location"),
            "scale": _as_float(gamma["scale"], "gamma_sigma.priors.gamma.scale"),
            "df": _as_float(gamma["df"], "gamma_sigma.priors.gamma.df"),
        },
    }


def _normalize_state_refresh_schedule(raw: dict[str, Any]) -> dict[str, int | bool]:
    if not isinstance(raw, dict):
        raise ValueError("gamma_sigma.state_refresh_schedule must be a mapping")
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("gamma_sigma.state_refresh_schedule.enabled must be boolean")
    out = {
        "enabled": enabled,
        "start_iter": int(raw.get("start_iter", 11)),
        "end_iter": int(raw.get("end_iter", 200)),
        "hold_iters": int(raw.get("hold_iters", 10)),
        "refresh_iters": int(raw.get("refresh_iters", 1)),
    }
    if enabled:
        if out["start_iter"] < 1:
            raise ValueError("gamma_sigma.state_refresh_schedule.start_iter must be >= 1")
        if out["end_iter"] < out["start_iter"]:
            raise ValueError("gamma_sigma.state_refresh_schedule.end_iter must be >= start_iter")
        if out["hold_iters"] < 1:
            raise ValueError("gamma_sigma.state_refresh_schedule.hold_iters must be >= 1")
        if out["refresh_iters"] < 1:
            raise ValueError("gamma_sigma.state_refresh_schedule.refresh_iters must be >= 1")
    return out


def _normalize_gamsig_controls(raw: dict[str, Any]) -> dict[str, Any]:
    max_iter_raw = raw.get("max_iter")
    if max_iter_raw is None:
        raise ValueError("fit.exdqlm_multivar.gamma_sigma.max_iter must be provided when gamma_sigma controls are supplied")
    try:
        max_iter = int(max_iter_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"fit.exdqlm_multivar.gamma_sigma.max_iter must be an integer; got {max_iter_raw!r}") from exc
    if max_iter < 1:
        raise ValueError("fit.exdqlm_multivar.gamma_sigma.max_iter must be >= 1")
    out: dict[str, Any] = {
        "max_iter": max_iter,
    }
    freeze_target = raw.get("freeze_target")
    if freeze_target is not None:
        freeze_target = str(freeze_target).strip() or "gamma_sigma"
        if freeze_target not in {"gamma_sigma", "states"}:
            raise ValueError("fit.exdqlm_multivar.gamma_sigma.freeze_target must be 'gamma_sigma' or 'states'")
        out["freeze_target"] = freeze_target
    if "state_refresh_schedule" in raw:
        out["state_refresh_schedule"] = _normalize_state_refresh_schedule(raw["state_refresh_schedule"])
    return out


def _normalize_structure(raw: dict[str, Any]) -> dict[str, Any]:
    include_trend = raw.get("include_trend", True)
    if not isinstance(include_trend, bool):
        raise ValueError("models.exdqlm_multivar.structure.include_trend must be boolean")
    enabled = _normalize_string_list(raw.get("enabled_harmonic_indices", [1, 2, 3]), "enabled_harmonic_indices")
    if enabled:
        try:
            enabled_i = [int(v) for v in enabled]
        except ValueError as exc:
            raise ValueError("models.exdqlm_multivar.structure.enabled_harmonic_indices must be integers") from exc
        if any(v < 1 or v > 3 for v in enabled_i):
            raise ValueError("models.exdqlm_multivar.structure.enabled_harmonic_indices must be within 1:3")
    else:
        enabled_i = []
    if (not include_trend) and (not enabled_i):
        raise ValueError("structure cannot disable both trend and all harmonics")
    return {
        "include_trend": include_trend,
        "enabled_harmonic_indices": enabled_i,
    }


def _normalize_transfer_covariates(raw: dict[str, Any]) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        raise ValueError("inputs.transfer_function_covariates must be a mapping")
    base = _normalize_string_list(raw.get("base_covariates", []), "base_covariates")
    engineered = _normalize_string_list(raw.get("engineered_terms", []), "engineered_terms")
    if len(base) + len(engineered) < 1:
        raise ValueError("inputs.transfer_function_covariates must select at least one feature")
    return {
        "base_covariates": base,
        "engineered_terms": engineered,
    }


def _normalize_warm_start(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("fit.warm_start must be a mapping")
    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("fit.warm_start.enabled must be boolean")
    mode = str(raw.get("mode", "resume")).strip() or "resume"
    if mode != "resume":
        raise ValueError("fit.warm_start.mode must be 'resume'")
    source_run_id = raw.get("source_run_id")
    if source_run_id is not None:
      source_run_id = str(source_run_id).strip() or None
    source_run_root = raw.get("source_run_root")
    if source_run_root is not None:
      source_run_root = str(source_run_root).strip() or None
    if enabled and not source_run_root:
        raise ValueError("fit.warm_start.enabled requires source_run_root")
    return {
        "enabled": enabled,
        "mode": mode,
        "source_run_id": source_run_id,
        "source_run_root": source_run_root,
    }


def load_discount_override(path: Path) -> tuple[dict[str, Any], str]:
    payload = load_yaml(path)
    if "state_evolution" in payload and isinstance(payload["state_evolution"], dict):
        state = payload["state_evolution"]
    else:
        state = payload
    if not isinstance(state, dict):
        raise ValueError("discount spec must be a mapping or contain state_evolution")
    normalized: dict[str, Any] = {"state_evolution": normalize_state_evolution(state)}
    fit = payload.get("fit", {})
    if fit:
        if not isinstance(fit, dict):
            raise ValueError("fit block must be a mapping")
        exdqlm_mv = fit.get("exdqlm_multivar", {})
        if not isinstance(exdqlm_mv, dict):
            raise ValueError("fit.exdqlm_multivar must be a mapping")
        legacy = exdqlm_mv.get("legacy", {})
        if legacy:
            if not isinstance(legacy, dict):
                raise ValueError("fit.exdqlm_multivar.legacy must be a mapping")
            fcov = legacy.get("forecast_cov", {})
            if not isinstance(fcov, dict):
                raise ValueError("fit.exdqlm_multivar.legacy.forecast_cov must be a mapping")
            normalized["forecast_cov"] = _normalize_forecast_cov(fcov)
        gamsig = exdqlm_mv.get("gamma_sigma", {})
        if gamsig:
            if not isinstance(gamsig, dict):
                raise ValueError("fit.exdqlm_multivar.gamma_sigma must be a mapping")
            if "init" in gamsig:
                if not isinstance(gamsig["init"], dict):
                    raise ValueError("fit.exdqlm_multivar.gamma_sigma.init must be a mapping")
                normalized["gamsig_init"] = _normalize_gamsig_init(gamsig["init"])
            if "max_iter" in gamsig:
                normalized["gamsig_controls"] = _normalize_gamsig_controls(gamsig)
            if "priors" in gamsig:
                if not isinstance(gamsig["priors"], dict):
                    raise ValueError("fit.exdqlm_multivar.gamma_sigma.priors must be a mapping")
                normalized["gamsig_priors"] = _normalize_gamsig_priors(gamsig["priors"])
        warm_start = fit.get("warm_start", {})
        if warm_start:
            normalized["warm_start"] = _normalize_warm_start(warm_start)
    models_block = payload.get("models", {})
    if models_block:
        if not isinstance(models_block, dict):
            raise ValueError("models block must be a mapping")
        exdqlm_mv_model = models_block.get("exdqlm_multivar", {})
        if exdqlm_mv_model:
            if not isinstance(exdqlm_mv_model, dict):
                raise ValueError("models.exdqlm_multivar must be a mapping")
            structure = exdqlm_mv_model.get("structure", {})
            if structure:
                if not isinstance(structure, dict):
                    raise ValueError("models.exdqlm_multivar.structure must be a mapping")
                normalized["structure"] = _normalize_structure(structure)
    inputs_block = payload.get("inputs", {})
    if inputs_block:
        if not isinstance(inputs_block, dict):
            raise ValueError("inputs block must be a mapping")
        tf_cov = inputs_block.get("transfer_function_covariates", {})
        if tf_cov:
            normalized["transfer_function_covariates"] = _normalize_transfer_covariates(tf_cov)
    label = str(payload.get("spec_label") or path.stem).strip() or path.stem
    return normalized, label


def _apply_init_to_quantile_overrides(cfg: dict[str, Any], init_block: dict[str, float | str]) -> None:
    mv_fit = (((cfg.get("fit") or {}).get("exdqlm_multivar")) or {})
    gamsig = (mv_fit.get("gamma_sigma") or {})
    overrides = gamsig.get("quantile_overrides")
    if not isinstance(overrides, dict):
        return
    for override in overrides.values():
        if not isinstance(override, dict):
            continue
        override["init"] = dict(init_block)


def main() -> int:
    args = parse_args()
    source_cfg = load_yaml(args.source_config)
    source_fit = (source_cfg.get("fit") or {})
    source_mv_fit = (source_fit.get("exdqlm_multivar") or {})
    source_state = normalize_state_evolution(source_cfg["models"]["exdqlm_multivar"]["state_evolution"])
    source_forecast_cov = dict((((source_mv_fit.get("legacy") or {}).get("forecast_cov")) or {}))
    source_gamsig = (source_mv_fit.get("gamma_sigma") or {})
    source_init = dict((source_gamsig.get("init") or {}))
    source_controls = {
        "max_iter": int(source_gamsig.get("max_iter", 100)),
        "freeze_target": str(source_gamsig.get("freeze_target", "gamma_sigma")),
        "state_refresh_schedule": json.loads(json.dumps(source_gamsig.get("state_refresh_schedule") or {
            "enabled": False,
            "start_iter": 11,
            "end_iter": 200,
            "hold_iters": 10,
            "refresh_iters": 1,
        })),
    }
    source_priors = {
        "sigma": {"mean": 1.0, "variance": 1e10},
        "gamma": {"location": 0.0, "scale": 1e10, "df": 1.0},
    }
    if isinstance(source_gamsig.get("priors"), dict):
        pri = source_gamsig["priors"]
        if isinstance(pri.get("sigma"), dict):
            source_priors["sigma"].update(pri["sigma"])
        if isinstance(pri.get("gamma"), dict):
            source_priors["gamma"].update(pri["gamma"])
    source_structure = json.loads(json.dumps(((((source_cfg.get("models") or {}).get("exdqlm_multivar")) or {}).get("structure")) or {
        "include_trend": True,
        "enabled_harmonic_indices": [1, 2, 3],
    }))
    source_warm_start = json.loads(json.dumps((source_fit.get("warm_start")) or {
        "enabled": False,
        "source_run_id": None,
        "source_run_root": None,
        "mode": "resume",
    }))
    source_transfer_covariates = json.loads(json.dumps(((source_cfg.get("inputs") or {}).get("transfer_function_covariates")) or {
        "base_covariates": ["PPT", "SOIL", "PCA"],
        "engineered_terms": [
            "PPT_sq", "SOIL_sq", "PPT_x_SOIL",
            "PPT_lag1", "PPT_lag2", "PPT_lag3",
            "SOIL_lag1", "SOIL_lag2", "SOIL_lag3",
        ],
    }))

    if args.discount_spec:
        target_spec, spec_label = load_discount_override(args.discount_spec)
    else:
        target_spec = {
            "state_evolution": dict(source_state),
            "forecast_cov": dict(source_forecast_cov),
            "gamsig_controls": dict(source_controls),
            "gamsig_init": dict(source_init),
            "gamsig_priors": json.loads(json.dumps(source_priors)),
            "warm_start": json.loads(json.dumps(source_warm_start)),
            "structure": json.loads(json.dumps(source_structure)),
            "transfer_function_covariates": json.loads(json.dumps(source_transfer_covariates)),
        }
        spec_label = str(args.spec_label).strip() or DEFAULT_SPEC_LABEL

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_runtime_root = args.target_runtime_root
    target_control_root = target_runtime_root / "control"
    target_generated = target_control_root / "generated_configs"
    target_reports = args.cleanup_report_dir
    target_reports.mkdir(parents=True, exist_ok=True)
    target_generated.mkdir(parents=True, exist_ok=True)
    (target_runtime_root / "runs").mkdir(parents=True, exist_ok=True)

    run_id = f"multimodel_20221225_v8_he2pubgdpc1r1_{spec_label}_exdqlm_multivar_keep"
    config_path = target_generated / f"{run_id}.yaml"
    launch_suffix = "with_cleanup" if args.cleanup_mode == "with_cleanup" else "without_cleanup"
    launch_wrapper = (
        "$REPO_ROOT/scripts/run_unified_with_cleanup.sh"
        if args.cleanup_mode == "with_cleanup"
        else "$REPO_ROOT/scripts/run_unified_without_cleanup.sh"
    )
    launch_path = target_control_root / f"launch_{run_id}_{launch_suffix}.sh"
    spec_path = target_control_root / f"{run_id}_discount_spec.yaml"
    summary_path = target_reports / "summary.json"
    report_path = target_reports / "HE2_EXAL_M_T1_DISCOUNT_REFRESH_SCAFFOLD_20260518.md"

    cfg = json.loads(json.dumps(source_cfg))
    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(target_runtime_root / "runs")
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = True
    cfg["run"]["dry_run"] = False
    cfg["run"].pop("resolved_run_root", None)
    cfg["run"].pop("resolved_config_path", None)
    cfg["models"]["exdqlm_multivar"]["state_evolution"] = dict(target_spec["state_evolution"])
    if "forecast_cov" in target_spec:
        cfg.setdefault("fit", {}).setdefault("exdqlm_multivar", {}).setdefault("legacy", {})["forecast_cov"] = dict(target_spec["forecast_cov"])
    if "gamsig_init" in target_spec:
        cfg.setdefault("fit", {}).setdefault("exdqlm_multivar", {}).setdefault("gamma_sigma", {})["init"] = dict(target_spec["gamsig_init"])
        _apply_init_to_quantile_overrides(cfg, dict(target_spec["gamsig_init"]))
    if "gamsig_controls" in target_spec:
        gamsig_cfg = cfg.setdefault("fit", {}).setdefault("exdqlm_multivar", {}).setdefault("gamma_sigma", {})
        gamsig_cfg["max_iter"] = int(target_spec["gamsig_controls"]["max_iter"])
        if "freeze_target" in target_spec["gamsig_controls"]:
            gamsig_cfg["freeze_target"] = str(target_spec["gamsig_controls"]["freeze_target"])
            overrides = gamsig_cfg.get("quantile_overrides")
            if isinstance(overrides, dict):
                for key, override in list(overrides.items()):
                    if isinstance(override, dict):
                        override.pop("freeze_target", None)
                        if not override:
                            overrides[key] = {}
        if "state_refresh_schedule" in target_spec["gamsig_controls"]:
            gamsig_cfg["state_refresh_schedule"] = json.loads(
                json.dumps(target_spec["gamsig_controls"]["state_refresh_schedule"])
            )
    if "gamsig_priors" in target_spec:
        cfg.setdefault("fit", {}).setdefault("exdqlm_multivar", {}).setdefault("gamma_sigma", {})["priors"] = json.loads(json.dumps(target_spec["gamsig_priors"]))
    if "warm_start" in target_spec:
        cfg.setdefault("fit", {})["warm_start"] = json.loads(json.dumps(target_spec["warm_start"]))
    if "structure" in target_spec:
        cfg.setdefault("models", {}).setdefault("exdqlm_multivar", {})["structure"] = json.loads(json.dumps(target_spec["structure"]))
    if "transfer_function_covariates" in target_spec:
        cfg.setdefault("inputs", {})["transfer_function_covariates"] = json.loads(json.dumps(target_spec["transfer_function_covariates"]))

    debug = cfg.setdefault("debug_discount_refresh", {})
    debug["prepared_at"] = timestamp
    debug["source_config"] = str(args.source_config)
    debug["source_run_id"] = str(source_cfg["run"]["run_id"])
    debug["spec_label"] = spec_label
    debug["state_evolution"] = dict(target_spec["state_evolution"])
    debug["forecast_cov"] = dict(target_spec.get("forecast_cov", source_forecast_cov))
    debug["gamsig_controls"] = dict(target_spec.get("gamsig_controls", source_controls))
    debug["gamsig_init"] = dict(target_spec.get("gamsig_init", source_init))
    debug["gamsig_priors"] = json.loads(json.dumps(target_spec.get("gamsig_priors", source_priors)))
    debug["warm_start"] = json.loads(json.dumps(target_spec.get("warm_start", source_warm_start)))
    debug["structure"] = json.loads(json.dumps(target_spec.get("structure", source_structure)))
    debug["transfer_function_covariates"] = json.loads(json.dumps(target_spec.get("transfer_function_covariates", source_transfer_covariates)))
    debug["uses_cleanup_launcher"] = args.cleanup_mode == "with_cleanup"
    debug["cleanup_mode"] = args.cleanup_mode
    debug["notes"] = "Prepared from bridge-fixed representative source config; update discount spec if needed before launch."

    write_yaml(config_path, cfg)
    write_yaml(
        spec_path,
        {
            "spec_label": spec_label,
            "state_evolution": dict(target_spec["state_evolution"]),
            "fit": {
                "warm_start": json.loads(json.dumps(target_spec.get("warm_start", source_warm_start))),
                "exdqlm_multivar": {
                    "legacy": {
                        "forecast_cov": dict(target_spec.get("forecast_cov", source_forecast_cov)),
                    },
                    "gamma_sigma": {
                        "max_iter": int(target_spec.get("gamsig_controls", source_controls)["max_iter"]),
                        "freeze_target": str(target_spec.get("gamsig_controls", source_controls).get("freeze_target", "gamma_sigma")),
                        "state_refresh_schedule": json.loads(json.dumps(
                            target_spec.get("gamsig_controls", source_controls).get("state_refresh_schedule", source_controls.get("state_refresh_schedule"))
                        )),
                        "init": dict(target_spec.get("gamsig_init", source_init)),
                        "priors": json.loads(json.dumps(target_spec.get("gamsig_priors", source_priors))),
                    },
                }
            },
            "models": {
                "exdqlm_multivar": {
                    "structure": json.loads(json.dumps(target_spec.get("structure", source_structure))),
                }
            },
            "inputs": {
                "transfer_function_covariates": json.loads(json.dumps(target_spec.get("transfer_function_covariates", source_transfer_covariates))),
            },
            "source_config": str(args.source_config),
            "source_run_id": str(source_cfg["run"]["run_id"]),
            "note": "Edit the state_evolution block here, then rerun build_he2_exal_m_t1_discount_refresh_scaffold.py --discount-spec <this file> to refresh the launch-ready config.",
        },
    )

    launch_text = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
            f'CONFIG="{config_path}"',
            'REPO_ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"',
            'if [ ! -f "$CONFIG" ]; then',
            '  echo "Missing generated config: $CONFIG" >&2',
            "  exit 1",
            "fi",
            'cd "$REPO_ROOT"',
            f'exec "{launch_wrapper}" --config "$CONFIG"',
            "",
        ]
    )
    launch_path.write_text(launch_text, encoding="utf-8")
    launch_path.chmod(0o755)

    summary = {
        "prepared_at": timestamp,
        "source_config": str(args.source_config),
        "source_run_id": str(source_cfg["run"]["run_id"]),
        "target_runtime_root": str(target_runtime_root),
        "generated_config": str(config_path),
        "launch_script": str(launch_path),
        "discount_spec_template": str(spec_path),
        "spec_label": spec_label,
        "state_evolution": target_spec["state_evolution"],
        "forecast_cov": target_spec.get("forecast_cov", source_forecast_cov),
        "gamsig_controls": target_spec.get("gamsig_controls", source_controls),
        "gamsig_init": target_spec.get("gamsig_init", source_init),
        "gamsig_priors": target_spec.get("gamsig_priors", source_priors),
        "warm_start": target_spec.get("warm_start", source_warm_start),
        "structure": target_spec.get("structure", source_structure),
        "transfer_function_covariates": target_spec.get("transfer_function_covariates", source_transfer_covariates),
        "cleanup_mode": args.cleanup_mode,
        "launch_ready": bool(args.discount_spec),
        "awaiting_exact_discount_values": not bool(args.discount_spec),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = []
    md.append("# HE2 exAL-M-T1 Discount Refresh Scaffold 2026-05-18\n\n")
    md.append(f"- source_config: `{args.source_config}`\n")
    md.append(f"- source_run_id: `{source_cfg['run']['run_id']}`\n")
    md.append(f"- target_runtime_root: `{target_runtime_root}`\n")
    md.append(f"- generated_config: `{config_path}`\n")
    md.append(f"- launch_script: `{launch_path}`\n")
    md.append(f"- discount_spec_template: `{spec_path}`\n")
    md.append(f"- spec_label: `{spec_label}`\n")
    md.append(f"- cleanup_mode: `{args.cleanup_mode}`\n")
    md.append(f"- launch_ready: `{summary['launch_ready']}`\n")
    md.append(f"- awaiting_exact_discount_values: `{summary['awaiting_exact_discount_values']}`\n\n")
    md.append("## Discount Block\n\n")
    for key in STATE_KEYS:
        md.append(f"- {key}: `{target_spec['state_evolution'][key]}`\n")
    md.append("\n## Forecast Covariance\n\n")
    md.append(f"- c_factor: `{summary['forecast_cov'].get('c_factor')}`\n")
    md.append(f"- epsilon: `{summary['forecast_cov'].get('epsilon')}`\n")
    md.append("\n## Gamma/Sigma Controls\n\n")
    md.append(f"- max_iter: `{summary['gamsig_controls'].get('max_iter')}`\n")
    md.append("\n## Gamma/Sigma Init\n\n")
    md.append(f"- mode: `{summary['gamsig_init'].get('mode')}`\n")
    md.append(f"- gamma: `{summary['gamsig_init'].get('gamma')}`\n")
    md.append(f"- sigma_floor: `{summary['gamsig_init'].get('sigma_floor')}`\n")
    md.append(f"- sigma_scale: `{summary['gamsig_init'].get('sigma_scale')}`\n")
    md.append("\n## Gamma/Sigma Priors\n\n")
    md.append(f"- sigma.mean: `{summary['gamsig_priors']['sigma'].get('mean')}`\n")
    md.append(f"- sigma.variance: `{summary['gamsig_priors']['sigma'].get('variance')}`\n")
    md.append(f"- gamma.location: `{summary['gamsig_priors']['gamma'].get('location')}`\n")
    md.append(f"- gamma.scale: `{summary['gamsig_priors']['gamma'].get('scale')}`\n")
    md.append(f"- gamma.df: `{summary['gamsig_priors']['gamma'].get('df')}`\n")
    md.append("\n## Warm Start\n\n")
    md.append(f"- enabled: `{summary['warm_start'].get('enabled')}`\n")
    md.append(f"- mode: `{summary['warm_start'].get('mode')}`\n")
    md.append(f"- source_run_id: `{summary['warm_start'].get('source_run_id')}`\n")
    md.append(f"- source_run_root: `{summary['warm_start'].get('source_run_root')}`\n")
    md.append("\n## Structure\n\n")
    md.append(f"- include_trend: `{summary['structure'].get('include_trend')}`\n")
    md.append(f"- enabled_harmonic_indices: `{summary['structure'].get('enabled_harmonic_indices')}`\n")
    md.append("\n## Transfer Covariates\n\n")
    md.append(f"- base_covariates: `{summary['transfer_function_covariates'].get('base_covariates')}`\n")
    md.append(f"- engineered_terms: `{summary['transfer_function_covariates'].get('engineered_terms')}`\n")
    md.append("\n## Notes\n\n")
    md.append("- This scaffold is cloned from the bridge-fixed representative config so it preserves the corrected rewiring.\n")
    if args.cleanup_mode == "with_cleanup":
        md.append("- The launcher uses `scripts/run_unified_with_cleanup.sh`, so fit-state `.RData` is removed automatically after post.\n")
    else:
        md.append("- The launcher uses `scripts/run_unified_without_cleanup.sh`, so fit-state `.RData` is retained after post for deeper investigation.\n")
    md.append("- If you want a different discount block, edit the generated spec template and rerun this builder with `--discount-spec`.\n")
    report_path.write_text("".join(md), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
