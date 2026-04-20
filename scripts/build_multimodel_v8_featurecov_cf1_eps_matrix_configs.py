#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from multimodel_v8_lib import (
    CUTOFFS,
    HEAVY_CUTOFF,
    ROOT,
    artifact_disk_free_gb,
    deep_copy_dict,
    ensure_dir,
    load_yaml,
    reports_dir,
    resolve_artifact_root,
    runs_dir,
    write_yaml,
)

SWEEP_MODEL_ORDER = [
    "exdqlm_multivar_keep",
    "exdqlm_multivar_drop",
    "dqlm_multivar_al_keep",
    "dqlm_multivar_al_drop",
    "ndlm_main_keep",
    "ndlm_main_drop",
]

REUSE_REQUIRED_FILES = [
    "tables/crps_forecast_summary.csv",
    "tables/crps_input_health.csv",
    "figure_manifest.csv",
]


def _set_nested(cfg: dict[str, Any], path: list[str], value: Any) -> None:
    cur = cfg
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def _deep_update(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _deep_update(dst[key], value)
        else:
            dst[key] = value
    return dst


def _resolve_repo_path(raw: str | Path | None) -> Path | None:
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _cutoff_index() -> dict[str, int]:
    return {cutoff: idx for idx, (cutoff, _date) in enumerate(CUTOFFS, start=1)}


def _sorted_enabled(mapping: dict[str, Any], preferred_order: list[str] | None = None) -> list[tuple[str, dict[str, Any]]]:
    preferred_order = preferred_order or []
    preferred_rank = {key: idx for idx, key in enumerate(preferred_order, start=1)}
    rows: list[tuple[str, dict[str, Any]]] = []
    for key, value in mapping.items():
        if not isinstance(value, dict):
            continue
        if value.get("enabled", True) is False:
            continue
        rows.append((str(key), value))
    rows.sort(key=lambda item: (preferred_rank.get(item[0], 10_000), item[0]))
    return rows


def _flatten_rows(prefix: str, value: Any, rows: list[dict[str, Any]], extra: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            _flatten_rows(next_prefix, child, rows, extra)
        return
    if isinstance(value, list):
        rendered = ",".join(str(x) for x in value)
    else:
        rendered = value
    row = dict(extra)
    row.update({"parameter": prefix, "value": rendered})
    rows.append(row)


def _dependency_rows(config_path: Path, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dep_specs = [
        ("forecats_existing_bundle", cfg.get("inputs", {}).get("forecats", {}).get("existing_bundle_path", "")),
        ("fit_parameters", cfg.get("inputs", {}).get("fit", {}).get("parameters_path", "")),
        ("fit_retros", cfg.get("inputs", {}).get("fit", {}).get("retros_path", "")),
        ("fit_nws_forecast", cfg.get("inputs", {}).get("fit", {}).get("nws_forecast_path", "")),
        ("fit_glofas_forecast", cfg.get("inputs", {}).get("fit", {}).get("glofas_forecast_path", "")),
        ("fit_usgs_cache", cfg.get("inputs", {}).get("fit", {}).get("usgs_cache_path", "")),
    ]
    for cov in cfg.get("inputs", {}).get("fit", {}).get("covariates", []) or []:
        if isinstance(cov, dict):
            dep_specs.append((f"covariate:{cov.get('name', '')}", cov.get("path", "")))
    for dep_type, dep_path in dep_specs:
        rows.append(
            {
                "consumer_config": str(config_path),
                "dependency_type": dep_type,
                "dependency_path": str(dep_path or ""),
            }
        )
    return rows


def _source_config_run_root(source_config: str) -> Path:
    path = Path(source_config)
    if path.name != "resolved_config.yaml":
        raise FileNotFoundError(f"Expected source_config to point at resolved_config.yaml, got: {source_config}")
    run_root = path.parent
    if not run_root.exists():
        raise FileNotFoundError(f"Could not resolve source run root from {source_config}")
    return run_root


def _first_existing_path(candidates: list[Path | None]) -> str:
    for candidate in candidates:
        if candidate is None:
            continue
        if candidate.exists():
            return str(candidate.resolve())
    return ""


def _resolve_bundle_usgs_daily_path(bundle_meta_path: str | Path | None) -> tuple[str, str]:
    meta_path = _resolve_repo_path(bundle_meta_path)
    if meta_path is None:
        return "", ""
    bundle_root = meta_path.parent
    meta: dict[str, Any] = {}
    if meta_path.exists():
        try:
            loaded = load_yaml(meta_path)
        except Exception:
            loaded = {}
        if isinstance(loaded, dict):
            meta = loaded

    direct_path = _first_existing_path([
        bundle_root / "inputs" / "usgs_daily.csv",
        bundle_root / "usgs_daily.csv",
    ])
    if direct_path:
        origin = "bundle_inputs" if direct_path.endswith("/inputs/usgs_daily.csv") else "bundle_root"
        return direct_path, origin

    paths_cfg = meta.get("paths", {}) if isinstance(meta.get("paths"), dict) else {}
    meta_usgs_rel = str(paths_cfg.get("usgs_daily", "") or "").strip()
    if meta_usgs_rel:
        rel_path = _first_existing_path([bundle_root / meta_usgs_rel])
        if rel_path:
            return rel_path, "bundle_meta_paths"

    histfix_cfg = meta.get("histfix", {}) if isinstance(meta.get("histfix"), dict) else {}
    histfix_usgs = str(histfix_cfg.get("usgs_daily_source_path", "") or "").strip()
    histfix_path = _first_existing_path([_resolve_repo_path(histfix_usgs)])
    if histfix_path:
        return histfix_path, "bundle_histfix_source"

    return "", ""


def _resolve_source_usgs_daily_path(source_config: str) -> tuple[str, str]:
    run_root = _source_config_run_root(source_config)
    run_shared_usgs = _first_existing_path([run_root / "inputs" / "shared" / "usgs" / "usgs_daily.csv"])
    if run_shared_usgs:
        return run_shared_usgs, "source_run_shared"

    source_cfg = load_yaml(Path(source_config))
    fit_cache = _first_existing_path([
        _resolve_repo_path(_get_nested(source_cfg, ["inputs", "fit", "usgs_cache_path"]))
    ])
    if fit_cache:
        return fit_cache, "source_fit_cache"

    for bundle_meta_path in [
        run_root / "inputs" / "shared" / "forecats_bundle" / "meta.yaml",
        _get_nested(source_cfg, ["inputs", "forecats", "existing_bundle_path"]),
    ]:
        path, origin = _resolve_bundle_usgs_daily_path(bundle_meta_path)
        if path:
            return path, f"source_{origin}"

    return "", ""


def _rewrite_inputs_from_source_snapshot(cfg: dict[str, Any], *, source_config: str) -> None:
    run_root = _source_config_run_root(source_config)
    shared_root = run_root / "inputs" / "shared"
    snapshot_map = {
        ("inputs", "fit", "parameters_path"): shared_root / "parameters" / "parameters.txt",
        ("inputs", "fit", "retros_path"): shared_root / "retros" / "retros.csv",
        ("inputs", "fit", "nws_forecast_path"): shared_root / "forecasts" / "nws_forecast.csv",
        ("inputs", "fit", "glofas_forecast_path"): shared_root / "forecasts" / "glofas_forecast.csv",
        ("inputs", "forecats", "existing_bundle_path"): shared_root / "forecats_bundle" / "meta.yaml",
    }
    for path_keys, source_path in snapshot_map.items():
        if source_path.exists():
            _set_nested(cfg, list(path_keys), str(source_path))
    source_usgs_path, _origin = _resolve_source_usgs_daily_path(source_config)
    if source_usgs_path:
        _set_nested(cfg, ["inputs", "fit", "usgs_cache_path"], source_usgs_path)


def _rewrite_fit_covariates_from_source_snapshot(cfg: dict[str, Any], *, source_config: str, keep_names: set[str]) -> None:
    run_root = _source_config_run_root(source_config)
    shared_cov_root = run_root / "inputs" / "shared" / "covariates"
    filename_map = {
        "ELI": "cov_01_ELI.csv",
        "ONI": "cov_02_ONI.csv",
        "PPT": "cov_03_PPT.csv",
        "SOIL": "cov_04_SOIL.csv",
        "PCA": "cov_05_PCA.csv",
    }
    rewritten: list[dict[str, Any]] = []
    for name in sorted(keep_names):
        source_path = shared_cov_root / filename_map[name]
        if not source_path.exists():
            raise FileNotFoundError(
                f"Missing shared covariate snapshot for {name} in source run {run_root}: {source_path}"
            )
        rewritten.append({"name": name, "path": str(source_path)})
    rewritten.sort(key=lambda item: list(filename_map).index(item["name"]))
    _set_nested(cfg, ["inputs", "fit", "covariates"], rewritten)


def _discover_compare_dirs(raw_paths: list[Any], cutoff: str) -> list[Path]:
    discovered: list[Path] = []
    seen: set[str] = set()
    for raw in raw_paths:
        path = _resolve_repo_path(raw)
        if path is None:
            continue
        candidates: list[Path] = []
        if path.name.endswith("_compare"):
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(path.glob(f"multimodel_{cutoff}_*_compare"))
        for cand in candidates:
            key = str(cand.resolve())
            if cutoff not in cand.name or key in seen or not cand.exists():
                continue
            seen.add(key)
            discovered.append(cand.resolve())
    return discovered


def _load_compare_row(compare_dir: Path, model_id: str) -> dict[str, Any] | None:
    crps_path = compare_dir / "crps_forecast_summary_all_models.csv"
    prov_path = compare_dir / "source_provenance.csv"
    if not crps_path.exists() or not prov_path.exists():
        return None
    crps = pd.read_csv(crps_path)
    crps["model_id"] = crps["model_id"].astype(str)
    subset = crps.loc[crps["model_id"] == str(model_id)].copy()
    if subset.empty:
        return None
    subset = subset.sort_values(["mean_crps", "median_crps", "model_id"], kind="stable")
    row = subset.iloc[0].to_dict()

    prov = pd.read_csv(prov_path)
    if "model_id" in prov.columns:
        prov["model_id"] = prov["model_id"].astype(str)
        prov_row = prov.loc[prov["model_id"] == str(model_id)].copy()
        if not prov_row.empty:
            prov_row = prov_row.iloc[0].to_dict()
            row["source_run"] = prov_row.get("source_run", row.get("source_run", ""))
            row["source_type"] = prov_row.get("source_type", row.get("source_type", ""))
            row["source_lane"] = prov_row.get("source_lane", row.get("source_lane", ""))
    row["compare_dir"] = str(compare_dir)
    return row


def _target_knob_path(family_cfg: dict[str, Any]) -> list[str]:
    model_key = str(family_cfg["model_key"])
    if model_key == "exdqlm_multivar":
        return ["fit", "exdqlm_multivar", "legacy", "forecast_cov"]
    if model_key == "ndlm_main":
        return ["models", "ndlm_main", "prior", "forecast_cov"]
    raise ValueError(f"Unsupported sweep model_key: {model_key}")


def _get_nested(mapping: dict[str, Any], path: list[str]) -> Any:
    cur: Any = mapping
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _extract_target_knobs(cfg: dict[str, Any], family_cfg: dict[str, Any]) -> tuple[Any, Any]:
    knob_cfg = _get_nested(cfg, _target_knob_path(family_cfg)) or {}
    if not isinstance(knob_cfg, dict):
        return None, None
    return knob_cfg.get("c_factor"), knob_cfg.get("epsilon")


def _source_run_root(compare_dir: Path, source_run: str) -> Path:
    artifact_root = compare_dir.parent.parent
    run_root = artifact_root / "runs" / source_run
    if not run_root.exists():
        raise FileNotFoundError(f"Missing source run root for {source_run}: {run_root}")
    return run_root


def _select_best_source(cutoff: str, family_id: str, family_cfg: dict[str, Any], compare_dirs: list[Path]) -> dict[str, Any]:
    model_id = str(family_cfg["model_id"])
    best: dict[str, Any] | None = None
    for compare_dir in compare_dirs:
        row = _load_compare_row(compare_dir, model_id)
        if row is None:
            continue
        mean_crps = float(row["mean_crps"])
        if best is None or mean_crps < float(best["mean_crps"]):
            source_run = str(row.get("source_run", "") or "")
            if not source_run:
                raise RuntimeError(f"No source_run found for cutoff={cutoff} model_id={model_id} in {compare_dir}")
            run_root = _source_run_root(compare_dir, source_run)
            resolved_cfg = run_root / "resolved_config.yaml"
            if not resolved_cfg.exists():
                raise FileNotFoundError(f"Missing resolved_config for source run {source_run}: {resolved_cfg}")
            cfg = load_yaml(resolved_cfg)
            c_factor, epsilon_value = _extract_target_knobs(cfg, family_cfg)
            best = {
                "cutoff": cutoff,
                "family_id": family_id,
                "model_id": model_id,
                "mean_crps": mean_crps,
                "median_crps": float(row.get("median_crps", float("nan"))),
                "compare_dir": str(compare_dir),
                "source_run": source_run,
                "source_type": str(row.get("source_type", "")),
                "source_lane": str(row.get("source_lane", "")),
                "source_run_root": str(run_root),
                "source_config": str(resolved_cfg),
                "selected_c_factor": c_factor,
                "selected_epsilon": epsilon_value,
            }
    if best is None:
        raise RuntimeError(f"No compare row found for cutoff={cutoff} family={family_id} model_id={model_id}")
    return best


def _apply_family_scope(cfg: dict[str, Any], family_cfg: dict[str, Any]) -> None:
    _set_nested(cfg, ["models", "run_exdqlm_multivar"], False)
    _set_nested(cfg, ["models", "run_exdqlm_univar"], False)
    _set_nested(cfg, ["models", "run_ndlm_main"], False)
    _set_nested(cfg, ["models", "run_ndlm_univar"], False)

    model_key = str(family_cfg["model_key"])
    likelihood_mode = str(family_cfg.get("likelihood_mode", "")).strip()
    transfer_mode = str(family_cfg.get("transfer_mode", "")).strip()

    if model_key == "exdqlm_multivar":
        _set_nested(cfg, ["models", "run_exdqlm_multivar"], True)
        _set_nested(cfg, ["models", "exdqlm_multivar", "likelihood_mode"], likelihood_mode)
        _set_nested(cfg, ["models", "exdqlm_multivar", "forecast_transfer_mode"], transfer_mode)
        _set_nested(cfg, ["models", "exdqlm_multivar", "forecast_transfer_modes"], None)
    elif model_key == "ndlm_main":
        _set_nested(cfg, ["models", "run_ndlm_main"], True)
        _set_nested(cfg, ["models", "ndlm_main", "forecast_transfer_mode"], transfer_mode)
    else:
        raise ValueError(f"Unsupported sweep model_key: {model_key}")


def _apply_forecast_cov_knobs(cfg: dict[str, Any], family_cfg: dict[str, Any], c_factor: float, epsilon_value: float) -> None:
    knob_path = _target_knob_path(family_cfg)
    _set_nested(cfg, knob_path + ["c_factor"], float(c_factor))
    _set_nested(cfg, knob_path + ["epsilon"], float(epsilon_value))


def _normalize_input_snapshot(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "parameters_path": str(_get_nested(cfg, ["inputs", "fit", "parameters_path"]) or ""),
        "retros_path": str(_get_nested(cfg, ["inputs", "fit", "retros_path"]) or ""),
        "nws_forecast_path": str(_get_nested(cfg, ["inputs", "fit", "nws_forecast_path"]) or ""),
        "glofas_forecast_path": str(_get_nested(cfg, ["inputs", "fit", "glofas_forecast_path"]) or ""),
        "usgs_cache_path": str(_get_nested(cfg, ["inputs", "fit", "usgs_cache_path"]) or ""),
        "forecats_existing_bundle_path": str(_get_nested(cfg, ["inputs", "forecats", "existing_bundle_path"]) or ""),
        "fit_covariates": [
            {"name": str(row.get("name", "")), "path": str(row.get("path", ""))}
            for row in (_get_nested(cfg, ["inputs", "fit", "covariates"]) or [])
            if isinstance(row, dict)
        ],
    }


def _drop_none_values(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, child in value.items():
            normalized = _drop_none_values(child)
            if normalized is None:
                continue
            cleaned[str(key)] = normalized
        return cleaned
    if isinstance(value, list):
        return [_drop_none_values(child) for child in value]
    return value


def _family_signature(cfg: dict[str, Any], family_cfg: dict[str, Any]) -> dict[str, Any]:
    model_key = str(family_cfg["model_key"])
    sig = {
        "run_exdqlm_multivar": bool(_get_nested(cfg, ["models", "run_exdqlm_multivar"])),
        "run_exdqlm_univar": bool(_get_nested(cfg, ["models", "run_exdqlm_univar"])),
        "run_ndlm_main": bool(_get_nested(cfg, ["models", "run_ndlm_main"])),
        "run_ndlm_univar": bool(_get_nested(cfg, ["models", "run_ndlm_univar"])),
    }
    if model_key == "exdqlm_multivar":
        sig["likelihood_mode"] = str(_get_nested(cfg, ["models", "exdqlm_multivar", "likelihood_mode"]) or "")
        sig["transfer_mode"] = str(_get_nested(cfg, ["models", "exdqlm_multivar", "forecast_transfer_mode"]) or "")
    elif model_key == "ndlm_main":
        sig["transfer_mode"] = str(_get_nested(cfg, ["models", "ndlm_main", "forecast_transfer_mode"]) or "")
    return sig


def _configs_match_for_reuse(new_cfg: dict[str, Any], prior_cfg: dict[str, Any], family_cfg: dict[str, Any], c_factor: float, epsilon_value: float) -> bool:
    new_c, new_e = _extract_target_knobs(new_cfg, family_cfg)
    old_c, old_e = _extract_target_knobs(prior_cfg, family_cfg)
    if float(new_c) != float(c_factor) or float(old_c) != float(c_factor):
        return False
    if float(new_e) != float(epsilon_value) or float(old_e) != float(epsilon_value):
        return False
    if _family_signature(new_cfg, family_cfg) != _family_signature(prior_cfg, family_cfg):
        return False
    new_det = _drop_none_values((_get_nested(new_cfg, ["inputs", "deterministic_climate"]) or {}))
    old_det = _drop_none_values((_get_nested(prior_cfg, ["inputs", "deterministic_climate"]) or {}))
    if new_det != old_det:
        return False
    new_covfeat = _drop_none_values((_get_nested(new_cfg, ["inputs", "covariate_features"]) or {}))
    old_covfeat = _drop_none_values((_get_nested(prior_cfg, ["inputs", "covariate_features"]) or {}))
    if new_covfeat != old_covfeat:
        return False
    if _normalize_input_snapshot(new_cfg) != _normalize_input_snapshot(prior_cfg):
        return False
    return True


def _run_manifest_passed(manifest_path: Path) -> bool:
    if not manifest_path.exists():
        return False
    try:
        manifest = load_yaml(manifest_path)
    except Exception:
        return False
    report = ((manifest.get("stages") or {}).get("report") or {}) if isinstance(manifest, dict) else {}
    return str(report.get("status", "")).strip().lower() == "pass"


def _run_outputs_ready(run_root: Path, run_id: str) -> bool:
    output_root = run_root / "post" / "outputs" / run_id
    return all((output_root / rel).exists() for rel in REUSE_REQUIRED_FILES)


def _materialize_reuse_stub(run_root: Path, run_id: str, cfg: dict[str, Any], reuse_info: dict[str, Any]) -> None:
    ensure_dir(run_root)
    write_yaml(run_root / "resolved_config.yaml", cfg)
    write_yaml(run_root / "reuse_pointer.yaml", reuse_info)
    reuse_dir = ensure_dir(run_root / "reuse")
    reuse_log = reuse_dir / "reused_external_pass.log"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    reuse_log.write_text(
        "\n".join(
            [
                f"reused_at_utc={now}",
                f"run_id={run_id}",
                f"reuse_source_run_id={reuse_info['reuse_source_run_id']}",
                f"reuse_source_run_root={reuse_info['reuse_source_run_root']}",
                f"reuse_source_artifact_root={reuse_info['reuse_source_artifact_root']}",
                f"reuse_reason={reuse_info['reuse_reason']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "stages": {
            stage: {
                "status": "pass",
                "started_at_utc": now,
                "finished_at_utc": now,
                "log_path": str(reuse_log),
            }
            for stage in ["data_prep_shared", "fit", "post", "validate", "report"]
        },
        "timestamps": {
            "started_at_utc": now,
            "finished_at_utc": now,
        },
        "debug_reuse": reuse_info,
    }
    write_yaml(run_root / "run_manifest.yaml", manifest)


def _existing_local_reuse_info(local_run_root: Path) -> dict[str, Any] | None:
    pointer_path = local_run_root / "reuse_pointer.yaml"
    manifest_path = local_run_root / "run_manifest.yaml"
    if not pointer_path.exists() or not manifest_path.exists():
        return None
    if not _run_manifest_passed(manifest_path):
        return None
    try:
        payload = load_yaml(pointer_path)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "reused": True,
        "reuse_source_run_id": str(payload.get("reuse_source_run_id", "")),
        "reuse_source_run_root": str(payload.get("reuse_source_run_root", "")),
        "reuse_source_artifact_root": str(payload.get("reuse_source_artifact_root", "")),
        "reuse_reason": str(payload.get("reuse_reason", "")),
        "reuse_source_config": str(payload.get("reuse_source_config", "")),
        "execution_strategy": str(payload.get("execution_strategy", "reused_external_pass")),
    }


def _find_reusable_prior_run(
    *,
    cutoff: str,
    family_cfg: dict[str, Any],
    cfg: dict[str, Any],
    c_factor: float,
    epsilon_value: float,
    reuse_cfg: dict[str, Any],
    local_run_root: Path,
) -> dict[str, Any] | None:
    existing_reuse = _existing_local_reuse_info(local_run_root)
    if existing_reuse is not None:
        return existing_reuse
    if local_run_root.exists() and (local_run_root / "run_manifest.yaml").exists():
        return None
    if not bool(reuse_cfg.get("enabled", False)):
        return None
    run_suffix = str(family_cfg.get("run_suffix", "")).strip() or str(family_cfg.get("model_id", "")).strip()
    for prior in reuse_cfg.get("prior_campaigns", []) or []:
        if not isinstance(prior, dict):
            continue
        prior_artifact_root = resolve_artifact_root(prior.get("artifact_root"))
        spec_id = str(prior.get("spec_id", "featurecov_v1")).strip() or "featurecov_v1"
        run_tmpl = str(prior.get("run_id_template", "multimodel_{cutoff}_v8_{spec_id}_{run_suffix}"))
        prior_run_id = run_tmpl.format(cutoff=cutoff, spec_id=spec_id, run_suffix=run_suffix)
        prior_run_root = runs_dir(prior_artifact_root) / prior_run_id
        manifest_path = prior_run_root / "run_manifest.yaml"
        resolved_cfg = prior_run_root / "resolved_config.yaml"
        if not prior_run_root.exists() or not manifest_path.exists() or not resolved_cfg.exists():
            continue
        if not _run_manifest_passed(manifest_path):
            continue
        if not _run_outputs_ready(prior_run_root, prior_run_id):
            continue
        prior_cfg = load_yaml(resolved_cfg)
        if not _configs_match_for_reuse(cfg, prior_cfg, family_cfg, c_factor, epsilon_value):
            continue
        return {
            "reused": True,
            "reuse_source_run_id": prior_run_id,
            "reuse_source_run_root": str(prior_run_root),
            "reuse_source_artifact_root": str(prior_artifact_root),
            "reuse_reason": "exact_featurecov_match",
            "reuse_source_config": str(resolved_cfg),
            "execution_strategy": "reused_external_pass",
        }
    return None


def _build_run_config(
    template_cfg: dict[str, Any],
    run_id: str,
    artifact_root: Path,
    family_id: str,
    family_cfg: dict[str, Any],
    inputs_overrides: dict[str, Any],
    selection: dict[str, Any],
    epsilon_label: str,
    epsilon_value: float,
    c_factor: float,
    fit_parallel_mode: str,
    fit_parallel_workers: int,
    transfer_covariates: dict[str, Any],
) -> dict[str, Any]:
    cfg = deep_copy_dict(template_cfg)
    _set_nested(cfg, ["run", "run_id"], run_id)
    _set_nested(cfg, ["run", "run_root"], str(runs_dir(artifact_root)))
    _set_nested(cfg, ["run", "overwrite"], False)
    _set_nested(cfg, ["run", "dry_run"], False)
    _set_nested(cfg, ["run", "git_require_clean"], False)
    _set_nested(cfg, ["run", "auto_suffix_on_collision"], False)
    _set_nested(cfg, ["run", "threads", "mc_cores"], int(max(fit_parallel_workers, 1)))

    _set_nested(cfg, ["stages", "forecats"], False)
    for stage in ["data_prep_shared", "fit", "post", "validate", "report"]:
        _set_nested(cfg, ["stages", stage], True)
    _set_nested(cfg, ["post", "figures"], True)
    _set_nested(cfg, ["post", "smoke_fast"], True)
    _set_nested(cfg, ["post", "force_isolation_smoke_fast"], True)
    _set_nested(cfg, ["post", "export_tables"], True)

    _set_nested(cfg, ["fit", "parallel", "mode"], str(fit_parallel_mode))
    _set_nested(cfg, ["fit", "parallel", "workers"], int(max(fit_parallel_workers, 1)))
    _set_nested(cfg, ["inputs", "shared", "prefer_forecats_snapshot"], False)

    _apply_family_scope(cfg, family_cfg)
    _deep_update(cfg.setdefault("inputs", {}), deep_copy_dict(inputs_overrides))
    _rewrite_inputs_from_source_snapshot(cfg, source_config=str(selection["source_config"]))
    _rewrite_fit_covariates_from_source_snapshot(
        cfg,
        source_config=str(selection["source_config"]),
        keep_names={"PPT", "SOIL", "PCA"},
    )
    _apply_forecast_cov_knobs(cfg, family_cfg, c_factor=c_factor, epsilon_value=epsilon_value)
    resolved_usgs_cache_path = str(_get_nested(cfg, ["inputs", "fit", "usgs_cache_path"]) or "")

    cfg["debug_featurecov_cf1_eps_campaign"] = {
        "family_id": family_id,
        "model_id": str(family_cfg["model_id"]),
        "model_key": str(family_cfg["model_key"]),
        "likelihood_mode": str(family_cfg.get("likelihood_mode", "")),
        "transfer_mode": str(family_cfg.get("transfer_mode", "")),
        "epsilon_label": epsilon_label,
        "epsilon_value": epsilon_value,
        "target_c_factor": c_factor,
        "selected_source_run": selection["source_run"],
        "selected_source_type": selection["source_type"],
        "selected_compare_dir": selection["compare_dir"],
        "selected_mean_crps": selection["mean_crps"],
        "selected_source_config": selection["source_config"],
        "resolved_usgs_cache_path": resolved_usgs_cache_path,
        "fit_parallel_mode": fit_parallel_mode,
        "fit_parallel_workers": fit_parallel_workers,
        "transfer_function_covariates": deep_copy_dict(transfer_covariates),
    }
    return cfg


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build featurecov cf1 epsilon sweep matrix configs without launching runs.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--artifact-root")
    ap.add_argument("--matrix-dir")
    ap.add_argument("--config-output-dir")
    ap.add_argument("--cutoffs", nargs="*")
    ap.add_argument("--families", nargs="*")
    ap.add_argument("--epsilons", nargs="*")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    campaign_path = _resolve_repo_path(args.config)
    assert campaign_path is not None
    campaign = load_yaml(campaign_path)

    campaign_cfg = campaign.get("campaign", {}) if isinstance(campaign.get("campaign"), dict) else {}
    queue_cfg = campaign.get("queue", {}) if isinstance(campaign.get("queue"), dict) else {}
    fit_parallel_cfg = campaign.get("fit_parallel", {}) if isinstance(campaign.get("fit_parallel"), dict) else {}
    cutoffs_cfg = campaign.get("cutoffs", {}) if isinstance(campaign.get("cutoffs"), dict) else {}
    families_cfg = campaign.get("families", {}) if isinstance(campaign.get("families"), dict) else {}
    eps_cfg = campaign.get("epsilons", {}) if isinstance(campaign.get("epsilons"), dict) else {}
    compare_cfg = campaign.get("compare", {}) if isinstance(campaign.get("compare"), dict) else {}
    inputs_cfg = campaign.get("inputs", {}) if isinstance(campaign.get("inputs"), dict) else {}
    reuse_cfg = campaign.get("reuse", {}) if isinstance(campaign.get("reuse"), dict) else {}

    artifact_root = resolve_artifact_root(args.artifact_root or campaign_cfg.get("artifact_root"))
    matrix_dir = ensure_dir(_resolve_repo_path(args.matrix_dir or campaign_cfg.get("matrix_dir")) or (artifact_root / "control" / "featurecov_cf1_eps_matrix"))
    config_output_dir = ensure_dir(_resolve_repo_path(args.config_output_dir or campaign_cfg.get("config_output_dir")) or (artifact_root / "control" / "generated_configs"))
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))

    sweep_id = str(campaign_cfg.get("sweep_id", campaign_cfg.get("campaign_id", "featurecov_cf1_eps_v1"))).strip() or "featurecov_cf1_eps_v1"
    supported_cutoffs = {cutoff for cutoff, _ in CUTOFFS}
    selected_cutoffs = set(str(c) for c in args.cutoffs) if args.cutoffs else None
    selected_families = set(str(f) for f in args.families) if args.families else None
    selected_epsilons = set(str(e) for e in args.epsilons) if args.epsilons else None

    enabled_cutoffs = []
    for cutoff, cutoff_cfg in _sorted_enabled(cutoffs_cfg, preferred_order=[c for c, _ in CUTOFFS]):
        if cutoff not in supported_cutoffs:
            raise SystemExit(f"Unsupported cutoff in campaign config: {cutoff}")
        if selected_cutoffs and cutoff not in selected_cutoffs:
            continue
        enabled_cutoffs.append((cutoff, cutoff_cfg))

    enabled_families = []
    for family_id, family_cfg in _sorted_enabled(families_cfg, preferred_order=SWEEP_MODEL_ORDER):
        if selected_families and family_id not in selected_families:
            continue
        enabled_families.append((family_id, family_cfg))

    enabled_eps = []
    for epsilon_label, epsilon_cfg in _sorted_enabled(eps_cfg):
        if selected_epsilons and epsilon_label not in selected_epsilons:
            continue
        enabled_eps.append((epsilon_label, epsilon_cfg))

    if not enabled_cutoffs:
        raise SystemExit("No enabled cutoffs selected for featurecov cf1 epsilon sweep build.")
    if not enabled_families:
        raise SystemExit("No enabled families selected for featurecov cf1 epsilon sweep build.")
    if not enabled_eps:
        raise SystemExit("No enabled epsilons selected for featurecov cf1 epsilon sweep build.")

    selection_rows: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    dependency_rows: list[dict[str, Any]] = []
    generated_configs: list[Path] = []
    scope_rows: list[dict[str, Any]] = []
    reuse_rows: list[dict[str, Any]] = []
    order_index = 0
    cutoff_rank = _cutoff_index()
    epsilon_rank = {label: idx for idx, (label, _cfg) in enumerate(enabled_eps, start=1)}

    transfer_covariates = deep_copy_dict(inputs_cfg.get("transfer_function_covariates", {}))

    for cutoff, cutoff_cfg in enabled_cutoffs:
        authoritative_compare_dir = _resolve_repo_path(cutoff_cfg.get("authoritative_compare_dir"))
        if authoritative_compare_dir is None:
            raise SystemExit(f"Missing authoritative_compare_dir for cutoff {cutoff}")
        candidate_dirs = _discover_compare_dirs(cutoff_cfg.get("candidate_report_roots", []), cutoff)
        if len(candidate_dirs) < 1:
            raise SystemExit(f"No candidate compare dirs found for cutoff {cutoff}")

        selection_by_family: dict[str, dict[str, Any]] = {}
        for family_id, family_cfg in enabled_families:
            selection_by_family[family_id] = _select_best_source(cutoff, family_id, family_cfg, candidate_dirs)

        for epsilon_label, epsilon_cfg in enabled_eps:
            epsilon_value = float(epsilon_cfg.get("epsilon_value"))
            c_factor = float(epsilon_cfg.get("c_factor", 1.0))
            for family_id, family_cfg in enabled_families:
                selection = selection_by_family[family_id]
                template_cfg = load_yaml(Path(selection["source_config"]))
                run_suffix = str(family_cfg.get("run_suffix", family_id)).strip() or family_id
                run_id = f"multimodel_{cutoff}_v8_{epsilon_label}_{run_suffix}_featurecov_cf1"
                config_path = config_output_dir / f"{run_id}.yaml"
                fit_parallel_mode = str(family_cfg.get("fit_parallel_mode") or fit_parallel_cfg.get("mode") or "global_models")
                fit_parallel_workers = int(family_cfg.get("fit_parallel_workers") or fit_parallel_cfg.get("default_workers") or 1)

                cfg = _build_run_config(
                    template_cfg=template_cfg,
                    run_id=run_id,
                    artifact_root=artifact_root,
                    family_id=family_id,
                    family_cfg=family_cfg,
                    inputs_overrides=inputs_cfg,
                    selection=selection,
                    epsilon_label=epsilon_label,
                    epsilon_value=epsilon_value,
                    c_factor=c_factor,
                    fit_parallel_mode=fit_parallel_mode,
                    fit_parallel_workers=fit_parallel_workers,
                    transfer_covariates=transfer_covariates,
                )
                write_yaml(config_path, cfg)
                generated_configs.append(config_path)
                dependency_rows.extend(_dependency_rows(config_path, cfg))

                local_run_root = runs_dir(artifact_root) / run_id
                reuse_info = _find_reusable_prior_run(
                    cutoff=cutoff,
                    family_cfg=family_cfg,
                    cfg=cfg,
                    c_factor=c_factor,
                    epsilon_value=epsilon_value,
                    reuse_cfg=reuse_cfg,
                    local_run_root=local_run_root,
                )
                if reuse_info is not None:
                    _materialize_reuse_stub(local_run_root, run_id, cfg, reuse_info)
                    reuse_rows.append(
                        {
                            "cutoff": cutoff,
                            "epsilon": epsilon_label,
                            "run_id": run_id,
                            "family_id": family_id,
                            **reuse_info,
                        }
                    )

                order_index += 1
                is_heavy = cutoff == HEAVY_CUTOFF
                plan_row = {
                    "order_index": order_index,
                    "cutoff": cutoff,
                    "epsilon": epsilon_label,
                    "epsilon_value": epsilon_value,
                    "lane": family_id,
                    "run_scope": "featurecov_cf1_eps_sweep",
                    "run_id": run_id,
                    "config_path": str(config_path),
                    "compare_outdir": str(reports_dir(artifact_root) / f"multimodel_{cutoff}_v8_{epsilon_label}_compare"),
                    "priority_group": 2 if is_heavy else 1,
                    "max_concurrent_class": "heavy" if is_heavy else "ordinary",
                    "sweep_id": sweep_id,
                    "family_id": family_id,
                    "model_id": str(family_cfg["model_id"]),
                    "model_key": str(family_cfg["model_key"]),
                    "likelihood_mode": str(family_cfg.get("likelihood_mode", "")),
                    "transfer_mode": str(family_cfg.get("transfer_mode", "")),
                    "authoritative_compare_dir": str(authoritative_compare_dir),
                    "selected_compare_dir": selection["compare_dir"],
                    "selected_source_run": selection["source_run"],
                    "selected_source_type": selection["source_type"],
                    "selected_source_config": selection["source_config"],
                    "selected_mean_crps": selection["mean_crps"],
                    "selected_c_factor": selection["selected_c_factor"],
                    "selected_epsilon": selection["selected_epsilon"],
                    "target_c_factor": c_factor,
                    "target_epsilon": epsilon_value,
                    "reused": bool(reuse_info is not None),
                    "reuse_source_run_id": reuse_info.get("reuse_source_run_id", "") if reuse_info else "",
                    "reuse_source_run_root": reuse_info.get("reuse_source_run_root", "") if reuse_info else "",
                    "reuse_source_artifact_root": reuse_info.get("reuse_source_artifact_root", "") if reuse_info else "",
                    "execution_strategy": reuse_info.get("execution_strategy", "launch_required") if reuse_info else "launch_required",
                    "cutoff_rank": cutoff_rank[cutoff],
                    "epsilon_rank": epsilon_rank[epsilon_label],
                }
                plan_rows.append(plan_row)
                selection_rows.append(dict(plan_row))

    plan_df = pd.DataFrame(plan_rows).sort_values(["cutoff_rank", "epsilon_rank", "order_index"]).drop(columns=["cutoff_rank", "epsilon_rank"])
    plan_df.to_csv(matrix_dir / "matrix_plan.csv", index=False)

    dep_df = pd.DataFrame(dependency_rows).sort_values(["consumer_config", "dependency_type"]).reset_index(drop=True)
    dep_df.to_csv(matrix_dir / "dependency_preservation.csv", index=False)

    selection_df = pd.DataFrame(selection_rows).sort_values(["cutoff", "epsilon", "family_id"]).reset_index(drop=True)
    selection_df.to_csv(matrix_dir / "selection_summary.csv", index=False)

    reuse_df = pd.DataFrame(
        reuse_rows,
        columns=[
            "cutoff",
            "epsilon",
            "run_id",
            "family_id",
            "reused",
            "reuse_source_run_id",
            "reuse_source_run_root",
            "reuse_source_artifact_root",
            "reuse_reason",
            "reuse_source_config",
            "execution_strategy",
        ],
    )
    reuse_df.sort_values(["cutoff", "epsilon", "family_id"]).reset_index(drop=True).to_csv(matrix_dir / "reuse_manifest.csv", index=False)

    scope_rows = []
    _flatten_rows("inputs", inputs_cfg, scope_rows, {"sweep_id": sweep_id, "section": "inputs"})
    for epsilon_label, epsilon_cfg in enabled_eps:
        _flatten_rows("epsilons." + epsilon_label, epsilon_cfg, scope_rows, {"sweep_id": sweep_id, "section": "epsilons"})
    for family_id, family_cfg in enabled_families:
        _flatten_rows("families." + family_id, family_cfg, scope_rows, {"sweep_id": sweep_id, "section": "families"})
    pd.DataFrame(scope_rows).sort_values(["section", "parameter"]).reset_index(drop=True).to_csv(matrix_dir / "campaign_parameter_table.csv", index=False)

    status_path = matrix_dir / "matrix_status.csv"
    if not status_path.exists():
        with status_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "cutoff", "epsilon", "lane", "run_id", "phase", "status", "started_at", "finished_at",
                "manifest_path", "latest_log_mtime", "disk_free_gb", "note",
            ])

    metadata = {
        "campaign_id": str(campaign_cfg.get("campaign_id", "multimodel_v8_featurecov_cf1_eps_sweep")),
        "sweep_id": sweep_id,
        "campaign_config": str(campaign_path),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "compare_builder": str(compare_cfg.get("builder", "scripts/build_multimodel_v8_featurecov_cf1_eps_compare_bundle.py")),
        "queue": {
            "ordinary_max_concurrent": int(queue_cfg.get("ordinary_max_concurrent", 12)),
            "pause_free_gb": float(queue_cfg.get("pause_free_gb", 180)),
            "launch_free_gb": float(queue_cfg.get("launch_free_gb", 220)),
            "heavy_free_gb": float(queue_cfg.get("heavy_free_gb", 240)),
            "poll_seconds": int(queue_cfg.get("poll_seconds", 60)),
        },
        "counts": {
            "cutoffs": len(enabled_cutoffs),
            "epsilons": len(enabled_eps),
            "families": len(enabled_families),
            "plan_rows": int(len(plan_df)),
            "reused_rows": int(len(reuse_rows)),
        },
    }
    write_yaml(matrix_dir / "matrix_metadata.yaml", metadata)
    write_yaml(
        matrix_dir / "campaign_snapshot.yaml",
        {
            "config_path": str(campaign_path),
            "artifact_root": str(artifact_root),
            "matrix_dir": str(matrix_dir),
            "config_output_dir": str(config_output_dir),
            "campaign": campaign,
        },
    )

    launch_env = "\n".join([
        f"ARTIFACT_ROOT={artifact_root}",
        f"MATRIX_DIR={matrix_dir}",
        f"ORDINARY_MAX_CONCURRENT={metadata['queue']['ordinary_max_concurrent']}",
        f"PAUSE_FREE_GB={metadata['queue']['pause_free_gb']}",
        f"LAUNCH_FREE_GB={metadata['queue']['launch_free_gb']}",
        f"HEAVY_FREE_GB={metadata['queue']['heavy_free_gb']}",
        f"POLL_SECONDS={metadata['queue']['poll_seconds']}",
        "",
    ])
    (matrix_dir / "launch_settings.env").write_text(launch_env, encoding="utf-8")
    (matrix_dir / "queue.log").touch()

    scope_lines = [
        f"# {metadata['campaign_id']}",
        "",
        f"- campaign_config: `{campaign_path}`",
        f"- sweep_id: `{sweep_id}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- config_output_dir: `{config_output_dir}`",
        f"- generated_configs: `{len(generated_configs)}`",
        f"- enabled_cutoffs: `{', '.join(c for c, _cfg in enabled_cutoffs)}`",
        f"- enabled_epsilons: `{', '.join(label for label, _cfg in enabled_eps)}`",
        f"- enabled_families: `{', '.join(fam for fam, _cfg in enabled_families)}`",
        f"- reused_rows: `{len(reuse_rows)}`",
        "",
        "## Transfer-function covariates",
        f"- base_covariates: `{', '.join(inputs_cfg.get('transfer_function_covariates', {}).get('base_covariates', []))}`",
        f"- engineered_terms: `{', '.join(inputs_cfg.get('transfer_function_covariates', {}).get('engineered_terms', []))}`",
        "",
        "## Current queue defaults",
        f"- ordinary_max_concurrent: `{metadata['queue']['ordinary_max_concurrent']}`",
        f"- pause_free_gb: `{metadata['queue']['pause_free_gb']}`",
        f"- launch_free_gb: `{metadata['queue']['launch_free_gb']}`",
        f"- heavy_free_gb: `{metadata['queue']['heavy_free_gb']}`",
        f"- poll_seconds: `{metadata['queue']['poll_seconds']}`",
        "",
        "## Current disk headroom",
        f"- artifact disk free GB: `{artifact_disk_free_gb(artifact_root)}`",
    ]
    (matrix_dir / "featurecov_cf1_eps_scope.md").write_text("\n".join(scope_lines) + "\n", encoding="utf-8")

    print(f"artifact_root={artifact_root}")
    print(f"matrix_dir={matrix_dir}")
    print(f"config_output_dir={config_output_dir}")
    print(f"generated_configs={len(generated_configs)}")
    print(f"plan_rows={len(plan_df)}")
    print(f"selection_rows={len(selection_df)}")
    print(f"reused_rows={len(reuse_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
