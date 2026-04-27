#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import pandas as pd

from build_multimodel_v8_all9_feature_matrix_configs import (
    _deep_update,
    _dependency_rows,
    _flatten_rows,
    _resolve_repo_path,
    _set_nested,
    _sorted_enabled,
)
from build_multimodel_v8_featurecov_cf1_eps_matrix_configs import _resolve_source_usgs_daily_path
from multimodel_v8_lib import (
    CUTOFFS,
    HEAVY_CUTOFF,
    artifact_disk_free_gb,
    deep_copy_dict,
    ensure_dir,
    load_yaml,
    reports_dir,
    resolve_artifact_root,
    runs_dir,
    write_yaml,
)

MODEL_ORDER = [
    "exdqlm_multivar_keep",
    "exdqlm_multivar_drop",
    "dqlm_multivar_al_keep",
    "dqlm_multivar_al_drop",
    "exdqlm_univar",
    "dqlm_univar_al",
]

MULTIVAR_FAMILIES = {
    "exdqlm_multivar_keep",
    "exdqlm_multivar_drop",
    "dqlm_multivar_al_keep",
    "dqlm_multivar_al_drop",
}

UNIVAR_FAMILIES = {"exdqlm_univar", "dqlm_univar_al"}


def _cutoff_index() -> dict[str, int]:
    return {cutoff: idx for idx, (cutoff, _date) in enumerate(CUTOFFS, start=1)}


def _source_config_run_root(source_config: str) -> Path:
    path = Path(source_config)
    if path.name != "resolved_config.yaml":
        raise FileNotFoundError(f"Expected source_config to point at resolved_config.yaml, got: {source_config}")
    run_root = path.parent
    if not run_root.exists():
        raise FileNotFoundError(f"Could not resolve source run root from {source_config}")
    return run_root


def _normalize_label(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    rendered = str(value).strip()
    if not rendered or rendered.lower() == "nan":
        return fallback
    return rendered


def _normalize_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        rendered = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(rendered):
        return None
    return rendered


def _find_shared_covariate_path(shared_cov_root: Path, cov_name: str) -> Path:
    token = cov_name.strip().upper()
    candidates = sorted(shared_cov_root.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No shared covariate CSVs found under {shared_cov_root}")

    for cand in candidates:
        stem = cand.stem.upper().replace("-", "_")
        if token == stem or f"_{token}" in stem or stem.endswith(token):
            return cand

    raise FileNotFoundError(
        f"Could not match covariate {cov_name!r} to a shared snapshot under {shared_cov_root}"
    )


def _rewrite_inputs_from_source_snapshot_preserving_shape(cfg: dict[str, Any], *, source_config: str) -> dict[str, Any]:
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

    cov_root = shared_root / "covariates"
    covariates = cfg.get("inputs", {}).get("fit", {}).get("covariates", []) or []
    rewritten_covariates: list[dict[str, Any]] = []
    if cov_root.exists() and covariates:
        for entry in covariates:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            updated = dict(entry)
            updated["path"] = str(_find_shared_covariate_path(cov_root, name))
            rewritten_covariates.append(updated)
        if rewritten_covariates:
            _set_nested(cfg, ["inputs", "fit", "covariates"], rewritten_covariates)

    source_usgs_path, source_usgs_origin = _resolve_source_usgs_daily_path(source_config)
    if source_usgs_path:
        _set_nested(cfg, ["inputs", "fit", "usgs_cache_path"], source_usgs_path)

    return {
        "shared_root": str(shared_root),
        "resolved_usgs_cache_path": str(cfg.get("inputs", {}).get("fit", {}).get("usgs_cache_path", "") or ""),
        "resolved_usgs_origin": source_usgs_origin,
        "resolved_covariate_names": [str(row.get("name", "")) for row in rewritten_covariates],
        "resolved_covariate_paths": [str(row.get("path", "")) for row in rewritten_covariates],
    }


def _build_run_config(
    template_cfg: dict[str, Any],
    *,
    run_id: str,
    artifact_root: Path,
    family_id: str,
    family_cfg: dict[str, Any],
    campaign_spec_id: str,
    fit_parallel_mode: str,
    fit_parallel_workers: int,
    inputs_overrides: dict[str, Any],
    model_overrides: dict[str, Any],
    selection: dict[str, Any],
) -> dict[str, Any]:
    cfg = deep_copy_dict(template_cfg)
    _set_nested(cfg, ["run", "run_id"], run_id)
    _set_nested(cfg, ["run", "run_root"], str(runs_dir(artifact_root)))
    _set_nested(cfg, ["run", "overwrite"], False)
    _set_nested(cfg, ["run", "dry_run"], False)
    _set_nested(cfg, ["run", "git_require_clean"], False)
    _set_nested(cfg, ["run", "auto_suffix_on_collision"], False)
    _set_nested(cfg, ["run", "repro_mode"], "strict")
    _set_nested(cfg, ["run", "threads", "mc_cores"], int(max(fit_parallel_workers, 1)))

    _set_nested(cfg, ["stages", "forecats"], False)
    for stage in ["data_prep_shared", "fit", "post", "validate", "report"]:
        _set_nested(cfg, ["stages", stage], True)
    _set_nested(cfg, ["post", "figures"], True)
    _set_nested(cfg, ["post", "export_tables"], True)

    _set_nested(cfg, ["fit", "parallel", "mode"], str(fit_parallel_mode))
    _set_nested(cfg, ["fit", "parallel", "workers"], int(max(fit_parallel_workers, 1)))

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
    elif model_key == "exdqlm_univar":
        _set_nested(cfg, ["models", "run_exdqlm_univar"], True)
        _set_nested(cfg, ["models", "exdqlm_univar", "likelihood_mode"], likelihood_mode)
    else:
        raise ValueError(f"Unsupported model_key for quantile probe: {model_key}")

    _deep_update(cfg.setdefault("inputs", {}), deep_copy_dict(inputs_overrides))
    if model_overrides:
        _deep_update(cfg.setdefault("models", {}), deep_copy_dict(model_overrides))
    source_debug = _rewrite_inputs_from_source_snapshot_preserving_shape(
        cfg,
        source_config=str(selection["source_config"]),
    )

    cfg["debug_quantile_ndlm_discount_probe"] = {
        "campaign_spec_id": campaign_spec_id,
        "family_id": family_id,
        "model_id": str(family_cfg["model_id"]),
        "model_key": model_key,
        "likelihood_mode": likelihood_mode,
        "transfer_mode": transfer_mode,
        "selected_source_run": selection["source_run"],
        "selected_source_type": selection["source_type"],
        "selected_compare_dir": selection["compare_dir"],
        "selected_mean_crps": selection["mean_crps"],
        "selected_epsilon_label": selection["selected_epsilon_label"],
        "selected_epsilon": selection["selected_epsilon"],
        "selected_source_config": selection["source_config"],
        "fit_parallel_mode": fit_parallel_mode,
        "fit_parallel_workers": fit_parallel_workers,
        "model_overrides": deep_copy_dict(model_overrides),
        **source_debug,
    }
    return cfg


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _match_row(rows: list[dict[str, str]], *, key: str, value: str, path: Path) -> dict[str, str]:
    matched = [row for row in rows if str(row.get(key, "")) == value]
    if not matched:
        raise RuntimeError(f"Could not find {key}={value!r} in {path}")
    if len(matched) != 1:
        raise RuntimeError(f"Expected one {key}={value!r} row in {path}, found {len(matched)}")
    return matched[0]


def _resolve_runtime_config(
    *,
    source_run: str,
    source_type: str,
    selection_cfg: dict[str, Any],
) -> Path:
    source_type = str(source_type).strip()
    if source_type == "featurecov_cf1_eps_sweep":
        artifact_root = Path(str(selection_cfg["multivar_artifact_root"])).resolve()
    elif source_type == "featurecov_relaunch":
        artifact_root = Path(str(selection_cfg["univar_artifact_root"])).resolve()
    else:
        raise RuntimeError(f"Unsupported source_type for corrected quantile probe: {source_type}")

    config_path = artifact_root / "runs" / source_run / "resolved_config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Resolved source config missing: {config_path}")
    return config_path


def _univar_compare_dir(selection_cfg: dict[str, Any], cutoff: str) -> Path:
    compare_root = Path(str(selection_cfg["univar_compare_root"])).resolve()
    spec_id = str(selection_cfg.get("univar_compare_spec_id", "univar_featurecov_he2_v1")).strip()
    compare_dir = compare_root / f"multimodel_{cutoff}_v8_{spec_id}_compare"
    if not compare_dir.exists():
        raise FileNotFoundError(f"Missing univariate compare dir for cutoff {cutoff}: {compare_dir}")
    return compare_dir


def _selection_from_multivar(
    *,
    parity_row: dict[str, Any],
    family_id: str,
    family_cfg: dict[str, Any],
    selection_cfg: dict[str, Any],
) -> dict[str, Any]:
    compare_dir = Path(str(parity_row["compare_dir"])).resolve()
    provenance_path = compare_dir / "source_provenance.csv"
    crps_path = compare_dir / "crps_forecast_summary_all_models.csv"
    provenance_rows = _read_csv_rows(provenance_path)
    crps_rows = _read_csv_rows(crps_path)
    model_id = str(family_cfg["model_id"])
    prov_row = _match_row(provenance_rows, key="model_id", value=model_id, path=provenance_path)
    crps_row = _match_row(crps_rows, key="model_id", value=model_id, path=crps_path)

    source_run = str(prov_row["source_run"]).strip()
    source_type = str(prov_row["source_type"]).strip()
    source_config = _resolve_runtime_config(
        source_run=source_run,
        source_type=source_type,
        selection_cfg=selection_cfg,
    )

    return {
        "cutoff": str(parity_row["cutoff"]).zfill(8),
        "family_id": family_id,
        "model_id": model_id,
        "manuscript_label": str(parity_row.get("manuscript_label", "") or ""),
        "compare_dir": str(compare_dir),
        "source_run": source_run,
        "source_type": source_type,
        "source_lineage": str(prov_row.get("selected_source_run", "") or ""),
        "source_run_root": str(source_config.parent),
        "source_config": str(source_config),
        "mean_crps": float(crps_row["mean_crps"]),
        "selected_epsilon_label": _normalize_label(parity_row.get("best_epsilon_label"), "featurecov_shared"),
        "selected_epsilon": _normalize_float(parity_row.get("best_epsilon_value")),
        "state_df_t": _normalize_float(parity_row.get("state_df_t")),
        "state_df_s1": _normalize_float(parity_row.get("state_df_s1")),
        "state_df_s2": _normalize_float(parity_row.get("state_df_s2")),
        "state_df_s67": _normalize_float(parity_row.get("state_df_s67")),
        "state_df_discrep": _normalize_float(parity_row.get("state_df_discrep")),
        "state_lambda": _normalize_float(parity_row.get("state_lambda")),
        "state_df_trans": _normalize_float(parity_row.get("state_df_trans")),
        "state_df_covs": _normalize_float(parity_row.get("state_df_covs")),
    }


def _selection_from_univar(
    *,
    cutoff: str,
    family_id: str,
    family_cfg: dict[str, Any],
    selection_cfg: dict[str, Any],
) -> dict[str, Any]:
    compare_dir = _univar_compare_dir(selection_cfg, cutoff)
    provenance_path = compare_dir / "source_provenance.csv"
    crps_path = compare_dir / "crps_forecast_summary_all_models.csv"
    provenance_rows = _read_csv_rows(provenance_path)
    crps_rows = _read_csv_rows(crps_path)
    model_id = str(family_cfg["model_id"])
    prov_row = _match_row(provenance_rows, key="model_id", value=model_id, path=provenance_path)
    crps_row = _match_row(crps_rows, key="model_id", value=model_id, path=crps_path)

    source_run = str(prov_row["source_run"]).strip()
    source_type = str(prov_row["source_type"]).strip()
    source_config = _resolve_runtime_config(
        source_run=source_run,
        source_type=source_type,
        selection_cfg=selection_cfg,
    )

    return {
        "cutoff": cutoff,
        "family_id": family_id,
        "model_id": model_id,
        "manuscript_label": "AL-U-T1" if family_id == "dqlm_univar_al" else "exAL-U-T1",
        "compare_dir": str(compare_dir),
        "source_run": source_run,
        "source_type": source_type,
        "source_lineage": str(prov_row.get("selected_source_run", "") or ""),
        "source_run_root": str(source_config.parent),
        "source_config": str(source_config),
        "mean_crps": float(crps_row["mean_crps"]),
        "selected_epsilon_label": _normalize_label(prov_row.get("epsilon"), "univar_featurecov_he2_v1"),
        "selected_epsilon": None,
        "state_df_t": None,
        "state_df_s1": None,
        "state_df_s2": None,
        "state_df_s67": None,
        "state_df_discrep": None,
        "state_lambda": None,
        "state_df_trans": None,
        "state_df_covs": None,
    }


def _load_selection_manifest(
    parity_matrix_path: Path,
    *,
    enabled_cutoffs: list[tuple[str, dict[str, Any]]],
    enabled_families: list[tuple[str, dict[str, Any]]],
    selection_cfg: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    df = pd.read_csv(parity_matrix_path)
    df["cutoff"] = df["cutoff"].astype(str).str.zfill(8)

    parity_rows = {
        (str(row["cutoff"]).zfill(8), str(row["model_variant"])): row
        for row in df.to_dict(orient="records")
    }

    selections: dict[tuple[str, str], dict[str, Any]] = {}
    for cutoff, _cutoff_cfg in enabled_cutoffs:
        for family_id, family_cfg in enabled_families:
            if family_id in MULTIVAR_FAMILIES:
                parity_row = parity_rows.get((cutoff, family_id))
                if parity_row is None:
                    raise RuntimeError(f"No parity selection found for cutoff={cutoff} family={family_id}")
                selection = _selection_from_multivar(
                    parity_row=parity_row,
                    family_id=family_id,
                    family_cfg=family_cfg,
                    selection_cfg=selection_cfg,
                )
            elif family_id in UNIVAR_FAMILIES:
                selection = _selection_from_univar(
                    cutoff=cutoff,
                    family_id=family_id,
                    family_cfg=family_cfg,
                    selection_cfg=selection_cfg,
                )
            else:
                raise RuntimeError(f"Unsupported family for selection manifest: {family_id}")
            selections[(cutoff, family_id)] = selection
    return selections


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Build the quantile-only NDLM-discount probe configs using the corrected proper-featurecov HE2 sources."
    )
    ap.add_argument("--config", required=True)
    ap.add_argument("--artifact-root")
    ap.add_argument("--matrix-dir")
    ap.add_argument("--config-output-dir")
    ap.add_argument("--cutoffs", nargs="*")
    ap.add_argument("--families", nargs="*")
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
    compare_cfg = campaign.get("compare", {}) if isinstance(campaign.get("compare"), dict) else {}
    inputs_cfg = campaign.get("inputs", {}) if isinstance(campaign.get("inputs"), dict) else {}
    selection_cfg = campaign.get("selection", {}) if isinstance(campaign.get("selection"), dict) else {}
    model_overrides_cfg = campaign.get("model_overrides", {}) if isinstance(campaign.get("model_overrides"), dict) else {}

    artifact_root = resolve_artifact_root(args.artifact_root or campaign_cfg.get("artifact_root"))
    matrix_dir = ensure_dir(
        _resolve_repo_path(args.matrix_dir or campaign_cfg.get("matrix_dir"))
        or (artifact_root / "control" / "quantile_ndlm_discount_probe")
    )
    config_output_dir = ensure_dir(
        _resolve_repo_path(args.config_output_dir or campaign_cfg.get("config_output_dir"))
        or (artifact_root / "control" / "generated_configs")
    )
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))

    campaign_spec_id = str(campaign_cfg.get("spec_id", campaign_cfg.get("campaign_id", "quantile_ndlm_discount_probe_v1"))).strip() or "quantile_ndlm_discount_probe_v1"
    supported_cutoffs = {cutoff for cutoff, _ in CUTOFFS}
    selected_cutoffs = set(str(c) for c in args.cutoffs) if args.cutoffs else None
    selected_families = set(str(f) for f in args.families) if args.families else None

    enabled_cutoffs = []
    for cutoff, cutoff_cfg in _sorted_enabled(cutoffs_cfg, preferred_order=[c for c, _cfg in CUTOFFS]):
        if cutoff not in supported_cutoffs:
            raise SystemExit(f"Unsupported cutoff in campaign config: {cutoff}")
        if selected_cutoffs and cutoff not in selected_cutoffs:
            continue
        enabled_cutoffs.append((cutoff, cutoff_cfg))

    enabled_families = []
    for family_id, family_cfg in _sorted_enabled(families_cfg, preferred_order=MODEL_ORDER):
        if selected_families and family_id not in selected_families:
            continue
        enabled_families.append((family_id, family_cfg))

    if not enabled_cutoffs:
        raise SystemExit("No enabled cutoffs selected for quantile NDLM-discount probe build.")
    if not enabled_families:
        raise SystemExit("No enabled model families selected for quantile NDLM-discount probe build.")

    parity_matrix_path = _resolve_repo_path(selection_cfg.get("parity_matrix_path"))
    if parity_matrix_path is None or not parity_matrix_path.exists():
        raise SystemExit(f"Missing selection.parity_matrix_path: {parity_matrix_path}")

    selections = _load_selection_manifest(
        parity_matrix_path,
        enabled_cutoffs=enabled_cutoffs,
        enabled_families=enabled_families,
        selection_cfg=selection_cfg,
    )

    selection_rows: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    dependency_rows: list[dict[str, Any]] = []
    generated_configs: list[Path] = []
    order_index = 0
    cutoff_rank = _cutoff_index()

    for cutoff, cutoff_cfg in enabled_cutoffs:
        authoritative_compare_dir = _resolve_repo_path(cutoff_cfg.get("authoritative_compare_dir"))
        if authoritative_compare_dir is None:
            raise SystemExit(f"Missing authoritative_compare_dir for cutoff {cutoff}")

        for family_id, family_cfg in enabled_families:
            selection = selections[(cutoff, family_id)]
            template_cfg = load_yaml(Path(selection["source_config"]))
            run_suffix = str(family_cfg.get("run_suffix", family_id)).strip() or family_id
            run_id = f"multimodel_{cutoff}_v8_{campaign_spec_id}_{run_suffix}"
            config_path = config_output_dir / f"{run_id}.yaml"
            fit_parallel_mode = str(family_cfg.get("fit_parallel_mode") or fit_parallel_cfg.get("mode") or "global_models")
            fit_parallel_workers = int(family_cfg.get("fit_parallel_workers") or fit_parallel_cfg.get("default_workers") or 1)

            cfg = _build_run_config(
                template_cfg=template_cfg,
                run_id=run_id,
                artifact_root=artifact_root,
                family_id=family_id,
                family_cfg=family_cfg,
                campaign_spec_id=campaign_spec_id,
                fit_parallel_mode=fit_parallel_mode,
                fit_parallel_workers=fit_parallel_workers,
                inputs_overrides=inputs_cfg,
                model_overrides=model_overrides_cfg,
                selection=selection,
            )
            write_yaml(config_path, cfg)
            generated_configs.append(config_path)
            dependency_rows.extend(_dependency_rows(config_path, cfg))

            order_index += 1
            is_heavy = cutoff == HEAVY_CUTOFF
            plan_row = {
                "order_index": order_index,
                "cutoff": cutoff,
                "epsilon": selection["selected_epsilon_label"],
                "epsilon_value": selection["selected_epsilon"],
                "lane": family_id,
                "run_scope": "quantile_ndlm_discount_probe",
                "run_id": run_id,
                "config_path": str(config_path),
                "compare_outdir": str(reports_dir(artifact_root) / f"multimodel_{cutoff}_v8_{campaign_spec_id}_compare"),
                "priority_group": 2 if is_heavy else 1,
                "max_concurrent_class": "heavy" if is_heavy else "ordinary",
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
                "selected_source_lineage": selection["source_lineage"],
                "selected_discount_df_t": selection["state_df_t"],
                "selected_discount_df_s1": selection["state_df_s1"],
                "selected_discount_df_s2": selection["state_df_s2"],
                "selected_discount_df_s67": selection["state_df_s67"],
                "selected_discount_df_discrep": selection["state_df_discrep"],
                "selected_discount_lambda": selection["state_lambda"],
                "selected_discount_df_trans": selection["state_df_trans"],
                "selected_discount_df_covs": selection["state_df_covs"],
                "cutoff_rank": cutoff_rank[cutoff],
            }
            plan_rows.append(plan_row)
            selection_rows.append(dict(plan_row))

    plan_df = pd.DataFrame(plan_rows).sort_values(["cutoff_rank", "order_index"]).drop(columns=["cutoff_rank"])
    plan_df.to_csv(matrix_dir / "matrix_plan.csv", index=False)

    dep_df = pd.DataFrame(dependency_rows).sort_values(["consumer_config", "dependency_type"]).reset_index(drop=True)
    dep_df.to_csv(matrix_dir / "dependency_preservation.csv", index=False)

    selection_df = pd.DataFrame(selection_rows).sort_values(["cutoff", "family_id"]).reset_index(drop=True)
    selection_df.to_csv(matrix_dir / "selection_summary.csv", index=False)

    spec_rows: list[dict[str, Any]] = []
    _flatten_rows("selection", selection_cfg, spec_rows, {"campaign_spec_id": campaign_spec_id, "section": "selection"})
    _flatten_rows("inputs", inputs_cfg, spec_rows, {"campaign_spec_id": campaign_spec_id, "section": "inputs"})
    _flatten_rows("model_overrides", model_overrides_cfg, spec_rows, {"campaign_spec_id": campaign_spec_id, "section": "model_overrides"})
    for family_id, family_cfg in enabled_families:
        _flatten_rows(
            "families." + family_id,
            family_cfg,
            spec_rows,
            {"campaign_spec_id": campaign_spec_id, "section": "families"},
        )
    pd.DataFrame(spec_rows).sort_values(["section", "parameter"]).reset_index(drop=True).to_csv(
        matrix_dir / "spec_parameter_table.csv", index=False
    )

    status_path = matrix_dir / "matrix_status.csv"
    if not status_path.exists():
        with status_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "cutoff",
                    "epsilon",
                    "lane",
                    "run_id",
                    "phase",
                    "status",
                    "started_at",
                    "finished_at",
                    "manifest_path",
                    "latest_log_mtime",
                    "disk_free_gb",
                    "note",
                ]
            )

    metadata = {
        "campaign_id": str(campaign_cfg.get("campaign_id", "multimodel_v8_quantile_ndlm_discount_probe")),
        "campaign_spec_id": campaign_spec_id,
        "campaign_config": str(campaign_path),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "compare_builder": str(compare_cfg.get("builder", "scripts/build_multimodel_v8_all9_feature_compare_bundle.py")),
        "queue": {
            "ordinary_max_concurrent": int(queue_cfg.get("ordinary_max_concurrent", 4)),
            "pause_free_gb": float(queue_cfg.get("pause_free_gb", 180)),
            "launch_free_gb": float(queue_cfg.get("launch_free_gb", 220)),
            "heavy_free_gb": float(queue_cfg.get("heavy_free_gb", 240)),
            "heavy_cutoff_max_concurrent": int(queue_cfg.get("heavy_cutoff_max_concurrent", 4)),
            "heavy_cutoff_blocks_ordinary": bool(queue_cfg.get("heavy_cutoff_blocks_ordinary", False)),
            "poll_seconds": int(queue_cfg.get("poll_seconds", 15)),
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

    launch_env = "\n".join(
        [
            f"ARTIFACT_ROOT={artifact_root}",
            f"MATRIX_DIR={matrix_dir}",
            f"ORDINARY_MAX_CONCURRENT={metadata['queue']['ordinary_max_concurrent']}",
            f"PAUSE_FREE_GB={metadata['queue']['pause_free_gb']}",
            f"LAUNCH_FREE_GB={metadata['queue']['launch_free_gb']}",
            f"HEAVY_FREE_GB={metadata['queue']['heavy_free_gb']}",
            f"HEAVY_CUTOFF_MAX_CONCURRENT={metadata['queue']['heavy_cutoff_max_concurrent']}",
            f"HEAVY_CUTOFF_BLOCKS_ORDINARY={'1' if metadata['queue']['heavy_cutoff_blocks_ordinary'] else '0'}",
            f"POLL_SECONDS={metadata['queue']['poll_seconds']}",
            "",
        ]
    )
    (matrix_dir / "launch_settings.env").write_text(launch_env, encoding="utf-8")
    (matrix_dir / "queue.log").touch()

    scope_lines = [
        f"# {metadata['campaign_id']}",
        "",
        f"- campaign_config: `{campaign_path}`",
        f"- campaign_spec_id: `{campaign_spec_id}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- config_output_dir: `{config_output_dir}`",
        f"- parity_matrix_path: `{parity_matrix_path}`",
        f"- generated_configs: `{len(generated_configs)}`",
        f"- enabled_cutoffs: `{', '.join(c for c, _cfg in enabled_cutoffs)}`",
        f"- enabled_families: `{', '.join(fam for fam, _cfg in enabled_families)}`",
        "",
        "## Corrected Source Contract",
        "- multivariate AL/exAL rows are resolved from the current HE2 best-epsilon compare bundles, but the source config is taken from the actual executed `featurecov_cf1_eps_sweep` run listed in `source_provenance.csv`.",
        "- univariate AL/exAL rows are resolved from the finished `univar_featurecov_he2_v1` rerun compare bundles, not from the legacy TT baselines.",
        "- all generated configs therefore inherit the proper blended-featurecov input contract: `PPT`, `SOIL`, `PCA`, deterministic climate on, engineered lag/square/interaction covariates on.",
        "",
        "## Queue defaults",
        f"- ordinary_max_concurrent: `{metadata['queue']['ordinary_max_concurrent']}`",
        f"- pause_free_gb: `{metadata['queue']['pause_free_gb']}`",
        f"- launch_free_gb: `{metadata['queue']['launch_free_gb']}`",
        f"- heavy_free_gb: `{metadata['queue']['heavy_free_gb']}`",
        f"- heavy_cutoff_max_concurrent: `{metadata['queue']['heavy_cutoff_max_concurrent']}`",
        f"- heavy_cutoff_blocks_ordinary: `{metadata['queue']['heavy_cutoff_blocks_ordinary']}`",
        f"- poll_seconds: `{metadata['queue']['poll_seconds']}`",
        "",
        "## Discount override contract",
        f"- exdqlm_multivar.state_evolution.df_s1/s2/s67: `{model_overrides_cfg.get('exdqlm_multivar', {}).get('state_evolution', {}).get('df_s1', '')}`",
        f"- exdqlm_multivar.state_evolution.df_discrep: `{model_overrides_cfg.get('exdqlm_multivar', {}).get('state_evolution', {}).get('df_discrep', '')}`",
        f"- exdqlm_multivar.state_evolution.df_covs: `{model_overrides_cfg.get('exdqlm_multivar', {}).get('state_evolution', {}).get('df_covs', '')}`",
        f"- exdqlm_univar.state_evolution.df_s1/s2/s67: `{model_overrides_cfg.get('exdqlm_univar', {}).get('state_evolution', {}).get('df_s1', '')}`",
        f"- exdqlm_univar.state_evolution.df_covs: `{model_overrides_cfg.get('exdqlm_univar', {}).get('state_evolution', {}).get('df_covs', '')}`",
        "",
        "## Current disk headroom",
        f"- artifact disk free GB: `{artifact_disk_free_gb(artifact_root)}`",
    ]
    (matrix_dir / "quantile_ndlm_discount_probe_scope.md").write_text("\n".join(scope_lines) + "\n", encoding="utf-8")

    print(f"artifact_root={artifact_root}")
    print(f"matrix_dir={matrix_dir}")
    print(f"config_output_dir={config_output_dir}")
    print(f"generated_configs={len(generated_configs)}")
    print(f"plan_rows={len(plan_df)}")
    print(f"selection_rows={len(selection_df)}")
    print(f"spec_rows={len(spec_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
