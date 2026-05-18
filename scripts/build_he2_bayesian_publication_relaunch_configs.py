#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import pandas as pd

from he2_publication_relaunch_lib import (
    AUTHORITATIVE_COMPARE_BY_CUTOFF,
    DEFAULT_BUNDLE_ARTIFACT_ROOT,
    DEFAULT_BUNDLE_RUN_ID,
    DEFAULT_CAMPAIGN_SPEC_ID,
    DEFAULT_QUANTILES,
    DEFAULT_RELAUNCH_ARTIFACT_ROOT,
    EXPECTED_CUTOFFS,
    EXPECTED_FAMILY_ORDER,
    canonical_shared_paths,
    ensure_dir,
    family_rank,
    initialize_matrix_status,
    load_publication_manifest_rows,
    load_structured_file,
    load_yaml,
    model_class,
    normalize_code_list,
    parse_quantile_list,
    render_quantile_label,
    row_kind,
    spec_token,
    submodel_count,
    write_yaml,
)
from multimodel_v8_lib import HEAVY_CUTOFF, artifact_disk_free_gb, control_dir, reports_dir, resolve_artifact_root, runs_dir

MODEL_ID_BY_FAMILY = {
    'ndlm_univar_keep': 'ndlm_univar_synth_keep',
    'ndlm_main_drop': 'ndlm_main_synth_drop',
    'ndlm_main_keep': 'ndlm_main_synth_keep',
    'dqlm_univar_al': 'dqlm_univar_al_synth',
    'dqlm_multivar_al_drop': 'dqlm_multivar_al_synth_drop',
    'dqlm_multivar_al_keep': 'dqlm_multivar_al_synth_keep',
    'exdqlm_univar': 'exdqlm_univar_synth',
    'exdqlm_multivar_drop': 'exdqlm_multivar_synth_drop',
    'exdqlm_multivar_keep': 'exdqlm_multivar_synth_keep',
}

MODEL_KEY_BY_FAMILY = {
    'ndlm_univar_keep': 'ndlm_univar',
    'ndlm_main_drop': 'ndlm_main',
    'ndlm_main_keep': 'ndlm_main',
    'dqlm_univar_al': 'exdqlm_univar',
    'dqlm_multivar_al_drop': 'exdqlm_multivar',
    'dqlm_multivar_al_keep': 'exdqlm_multivar',
    'exdqlm_univar': 'exdqlm_univar',
    'exdqlm_multivar_drop': 'exdqlm_multivar',
    'exdqlm_multivar_keep': 'exdqlm_multivar',
}


def _set_nested(cfg: dict[str, Any], path: list[str], value: Any) -> None:
    cur = cfg
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def _get_nested(cfg: dict[str, Any] | None, path: list[str], default: Any = None) -> Any:
    cur: Any = cfg
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _dependency_rows(config_path: Path, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dep_specs = [
        ('forecats_existing_bundle', cfg.get('inputs', {}).get('forecats', {}).get('existing_bundle_path', '')),
        ('fit_parameters', cfg.get('inputs', {}).get('fit', {}).get('parameters_path', '')),
        ('fit_retros', cfg.get('inputs', {}).get('fit', {}).get('retros_path', '')),
        ('fit_nws_forecast', cfg.get('inputs', {}).get('fit', {}).get('nws_forecast_path', '')),
        ('fit_glofas_forecast', cfg.get('inputs', {}).get('fit', {}).get('glofas_forecast_path', '')),
    ]
    for cov in cfg.get('inputs', {}).get('fit', {}).get('covariates', []) or []:
        if isinstance(cov, dict):
            dep_specs.append((f"covariate:{cov.get('name', '')}", cov.get('path', '')))
    for dep_type, dep_path in dep_specs:
        rows.append({'consumer_config': str(config_path), 'dependency_type': dep_type, 'dependency_path': str(dep_path or '')})
    return rows


def _run_id(cutoff: str, campaign_spec_id: str, family: str) -> str:
    return f'multimodel_{cutoff}_v8_{campaign_spec_id}_{family}'


def _resolve_optional_path(base: Path, raw: str) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (base / path).resolve()
    else:
        path = path.resolve()
    return path


def _pick_list(default: list[str], *overrides: Any) -> list[str]:
    result = list(default)
    for override in overrides:
        values = normalize_code_list(override)
        if values:
            result = values
    return result


def _pick_quantiles(*overrides: Any) -> list[float]:
    result: list[float] = []
    for override in overrides:
        values = parse_quantile_list(override)
        if values:
            result = values
    return result


def _pick_scalar(default: Any, *overrides: Any) -> Any:
    result = default
    for override in overrides:
        if override not in (None, ''):
            result = override
    return result


def _merge_queue(default_queue: dict[str, Any], *overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(default_queue)
    for override in overrides:
        if not isinstance(override, dict):
            continue
        for key, value in override.items():
            if value not in (None, ''):
                merged[key] = value
    return merged


def _deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _resolve_row_config_patch(batch_payload: dict[str, Any], source_row: dict[str, str]) -> dict[str, Any]:
    overrides = batch_payload.get('overrides', {}) if isinstance(batch_payload.get('overrides'), dict) else {}
    resolved: dict[str, Any] = {}
    common_patch = overrides.get('common_config_patch', {})
    if isinstance(common_patch, dict) and common_patch:
        resolved = _deep_merge_dict(resolved, common_patch)

    for item in overrides.get('row_config_patches', []) or []:
        if not isinstance(item, dict):
            continue
        cutoff = str(item.get('cutoff', '')).strip()
        family = str(item.get('family', '')).strip()
        manuscript_label = str(item.get('manuscript_label', '')).strip()
        source_run_id = str(item.get('source_run_id', '')).strip()
        if cutoff and cutoff != source_row['cutoff']:
            continue
        if family and family != source_row['family']:
            continue
        if manuscript_label and manuscript_label != source_row['manuscript_label']:
            continue
        if source_run_id and source_run_id != source_row['run_id']:
            continue
        patch = item.get('config_patch', {})
        if isinstance(patch, dict) and patch:
            resolved = _deep_merge_dict(resolved, patch)
    return resolved


def _selection_spec(args: argparse.Namespace, campaign: dict[str, Any], campaign_path: Path) -> dict[str, Any]:
    selection_cfg = campaign.get('selection', {}) if isinstance(campaign.get('selection'), dict) else {}
    resources_cfg = campaign.get('resources', {}) if isinstance(campaign.get('resources'), dict) else {}
    profiles_cfg = campaign.get('profiles', {}) if isinstance(campaign.get('profiles'), dict) else {}
    active_profile = str(args.profile or profiles_cfg.get('active') or 'default')
    profile_defs = profiles_cfg.get('definitions', {}) if isinstance(profiles_cfg.get('definitions'), dict) else {}
    profile_cfg = profile_defs.get(active_profile, {}) if isinstance(profile_defs.get(active_profile), dict) else {}
    if active_profile != 'default' and active_profile not in profile_defs:
        raise KeyError(f'Unknown relaunch profile: {active_profile}')

    batch_file_raw = _pick_scalar('', selection_cfg.get('batch_file', ''), profile_cfg.get('batch_file', ''), args.batch_file)
    batch_cfg: dict[str, Any] = {}
    if batch_file_raw:
        batch_path = _resolve_optional_path(campaign_path.parents[1], str(batch_file_raw))
        if batch_path is None or not batch_path.exists():
            raise FileNotFoundError(f'batch file not found: {batch_file_raw}')
        batch_cfg = load_structured_file(batch_path)
    else:
        batch_path = None

    batch_selection = batch_cfg.get('selection', {}) if isinstance(batch_cfg.get('selection'), dict) else {}
    batch_resources = batch_cfg.get('resources', {}) if isinstance(batch_cfg.get('resources'), dict) else {}
    batch_queue = batch_cfg.get('queue', {}) if isinstance(batch_cfg.get('queue'), dict) else {}

    campaign_cfg = campaign.get('campaign', {}) if isinstance(campaign.get('campaign'), dict) else {}
    default_cutoffs = normalize_code_list(campaign_cfg.get('cutoffs') or EXPECTED_CUTOFFS)
    default_families = normalize_code_list(campaign_cfg.get('families') or EXPECTED_FAMILY_ORDER)

    selection = {
        'cutoffs': _pick_list(default_cutoffs, selection_cfg.get('cutoffs'), profile_cfg.get('selection', {}).get('cutoffs'), batch_selection.get('cutoffs'), args.cutoffs),
        'families': _pick_list(default_families, selection_cfg.get('families'), profile_cfg.get('selection', {}).get('families'), batch_selection.get('families'), args.families),
        'manuscript_labels': _pick_list([], selection_cfg.get('manuscript_labels'), profile_cfg.get('selection', {}).get('manuscript_labels'), batch_selection.get('manuscript_labels'), args.manuscript_labels),
        'run_ids': _pick_list([], selection_cfg.get('run_ids'), profile_cfg.get('selection', {}).get('run_ids'), batch_selection.get('run_ids'), args.run_ids),
        'model_classes': _pick_list([], selection_cfg.get('model_classes'), profile_cfg.get('selection', {}).get('model_classes'), batch_selection.get('model_classes'), args.model_classes),
        'quantiles': _pick_quantiles(selection_cfg.get('quantiles'), profile_cfg.get('selection', {}).get('quantiles'), batch_selection.get('quantiles'), args.quantiles),
        'batch_file': str(batch_path) if batch_path else '',
    }
    resources = {
        'fit_parallel_workers': int(_pick_scalar(None, resources_cfg.get('fit_parallel_workers'), profile_cfg.get('resources', {}).get('fit_parallel_workers'), batch_resources.get('fit_parallel_workers'), args.fit_parallel_workers)) if _pick_scalar(None, resources_cfg.get('fit_parallel_workers'), profile_cfg.get('resources', {}).get('fit_parallel_workers'), batch_resources.get('fit_parallel_workers'), args.fit_parallel_workers) not in (None, '') else None,
        'mc_cores': int(_pick_scalar(None, resources_cfg.get('mc_cores'), profile_cfg.get('resources', {}).get('mc_cores'), batch_resources.get('mc_cores'), args.mc_cores)) if _pick_scalar(None, resources_cfg.get('mc_cores'), profile_cfg.get('resources', {}).get('mc_cores'), batch_resources.get('mc_cores'), args.mc_cores) not in (None, '') else None,
    }
    queue = _merge_queue(
        campaign.get('queue', {}) if isinstance(campaign.get('queue'), dict) else {},
        profile_cfg.get('queue', {}) if isinstance(profile_cfg.get('queue'), dict) else {},
        batch_queue,
    )
    return {
        'profile': active_profile,
        'selection': selection,
        'resources': resources,
        'queue': queue,
        'profile_payload': profile_cfg,
        'batch_payload': batch_cfg,
    }


def _passes_selection(row: dict[str, str], *, campaign_spec_id: str, selection: dict[str, Any]) -> bool:
    cutoff = row['cutoff']
    family = row['family']
    target_run_id = _run_id(cutoff, campaign_spec_id, family)
    if cutoff not in set(selection['cutoffs']):
        return False
    if family not in set(selection['families']):
        return False
    if selection['manuscript_labels'] and row['manuscript_label'] not in set(selection['manuscript_labels']):
        return False
    if selection['run_ids'] and target_run_id not in set(selection['run_ids']):
        return False
    if selection['model_classes'] and model_class(family) not in set(selection['model_classes']):
        return False
    return True


def _build_run_config(
    template_cfg: dict[str, Any],
    *,
    run_id: str,
    artifact_root: Path,
    cutoff: str,
    bundle_artifact_root: Path,
    bundle_run_id: str,
    source_row: dict[str, str],
    resources: dict[str, Any],
    selected_quantiles: list[float],
    profile_name: str,
    row_config_patch: dict[str, Any] | None = None,
    row_config_patch_source: str = '',
) -> dict[str, Any]:
    cfg = copy.deepcopy(template_cfg)
    shared = canonical_shared_paths(bundle_artifact_root, cutoff, bundle_run_id)
    family = source_row['family']
    family_model_key = MODEL_KEY_BY_FAMILY[family]
    class_name = model_class(family)

    _set_nested(cfg, ['run', 'run_id'], run_id)
    _set_nested(cfg, ['run', 'run_root'], str(runs_dir(artifact_root)))
    _set_nested(cfg, ['run', 'overwrite'], False)
    _set_nested(cfg, ['run', 'dry_run'], False)
    _set_nested(cfg, ['run', 'git_require_clean'], False)
    _set_nested(cfg, ['run', 'auto_suffix_on_collision'], False)

    _set_nested(cfg, ['stages', 'forecats'], False)
    for stage in ['data_prep_shared', 'fit', 'post', 'validate', 'report']:
        _set_nested(cfg, ['stages', stage], True)
    _set_nested(cfg, ['post', 'figures'], True)
    _set_nested(cfg, ['post', 'export_tables'], True)

    _set_nested(cfg, ['dates', 'data_start'], '1987-05-29')
    _set_nested(cfg, ['inputs', 'shared', 'prefer_forecats_snapshot'], False)
    _set_nested(cfg, ['inputs', 'shared', 'exact_source_snapshot_root'], '')
    _set_nested(cfg, ['inputs', 'forecats', 'existing_bundle_path'], str(shared['bundle_meta']))

    _set_nested(cfg, ['inputs', 'fit', 'parameters_path'], str(shared['parameters']))
    _set_nested(cfg, ['inputs', 'fit', 'retros_path'], str(shared['retros']))
    _set_nested(cfg, ['inputs', 'fit', 'retros_storage_scale'], 'log1p_cms')
    _set_nested(cfg, ['inputs', 'fit', 'nws_forecast_path'], str(shared['nws_forecast']))
    _set_nested(cfg, ['inputs', 'fit', 'nws_storage_scale'], 'raw_cms')
    _set_nested(cfg, ['inputs', 'fit', 'glofas_forecast_path'], str(shared['glofas_forecast']))
    _set_nested(cfg, ['inputs', 'fit', 'glofas_storage_scale'], 'raw_cms')
    _set_nested(cfg, ['scale_contract', 'legacy_fit_input_scale'], 'log1p_cms')
    _set_nested(cfg, ['scale_contract', 'legacy_post_input_scale'], 'log1p_cms')
    _set_nested(cfg, ['scale_contract', 'analysis_scale_fit_internal'], 'log1p_cms')
    _set_nested(cfg, ['scale_contract', 'analysis_scale_post_internal'], 'log1p_cms')
    _set_nested(
        cfg,
        ['inputs', 'fit', 'covariates'],
        [
            {'name': 'PPT', 'path': str(shared['cov_ppt'])},
            {'name': 'SOIL', 'path': str(shared['cov_soil'])},
            {'name': 'PCA', 'path': str(shared['cov_pca'])},
        ],
    )

    full_quantiles = [float(q) for q in (((cfg.get('fit') or {}).get('quantiles')) or DEFAULT_QUANTILES)]
    active_quantiles = full_quantiles
    if selected_quantiles and class_name.startswith('quantile'):
        active_quantiles = [float(q) for q in selected_quantiles]
        _set_nested(cfg, ['fit', 'quantiles'], active_quantiles)

    source_workers = (((cfg.get('fit') or {}).get('parallel') or {}).get('workers'))
    workers = source_workers
    if resources.get('fit_parallel_workers') is not None:
        workers = int(resources['fit_parallel_workers'])
    elif active_quantiles and class_name.startswith('quantile'):
        # Default quantile relaunch behavior is one worker per active quantile.
        # This intentionally overrides lower source-run worker counts unless an
        # explicit relaunch resource override/profile asks for something else.
        workers = len(active_quantiles)
    if workers is not None:
        _set_nested(cfg, ['fit', 'parallel', 'workers'], int(workers))

    mc_cores = resources.get('mc_cores') if resources.get('mc_cores') is not None else workers
    if mc_cores is not None:
        _set_nested(cfg, ['run', 'threads', 'mc_cores'], int(mc_cores))

    if row_config_patch:
        cfg = _deep_merge_dict(cfg, row_config_patch)

    row_patch_workers = _get_nested(row_config_patch, ['fit', 'parallel', 'workers'])
    row_patch_mc_cores = _get_nested(row_config_patch, ['run', 'threads', 'mc_cores'])
    active_quantiles = [float(q) for q in (((cfg.get('fit') or {}).get('quantiles')) or full_quantiles)]
    if class_name.startswith('quantile'):
        if resources.get('fit_parallel_workers') is None and row_patch_workers in (None, ''):
            workers = len(active_quantiles)
            _set_nested(cfg, ['fit', 'parallel', 'workers'], int(workers))
        else:
            workers = (((cfg.get('fit') or {}).get('parallel')) or {}).get('workers')
        if resources.get('mc_cores') is None and row_patch_mc_cores in (None, ''):
            mc_cores = int(workers) if workers is not None else None
            if mc_cores is not None:
                _set_nested(cfg, ['run', 'threads', 'mc_cores'], int(mc_cores))
        else:
            mc_cores = (((cfg.get('run') or {}).get('threads')) or {}).get('mc_cores')
    else:
        workers = (((cfg.get('fit') or {}).get('parallel')) or {}).get('workers')
        mc_cores = (((cfg.get('run') or {}).get('threads')) or {}).get('mc_cores')

    # Enforce the current transform policy after any source-config or batch patch
    # merges so old log-log settings cannot leak back into active relaunch runs.
    _set_nested(cfg, ['scale_contract', 'legacy_fit_input_scale'], 'log1p_cms')
    _set_nested(cfg, ['scale_contract', 'legacy_post_input_scale'], 'log1p_cms')
    _set_nested(cfg, ['scale_contract', 'analysis_scale_fit_internal'], 'log1p_cms')
    _set_nested(cfg, ['scale_contract', 'analysis_scale_post_internal'], 'log1p_cms')

    cfg['debug_he2_publication_relaunch'] = {
        'campaign_spec_id': DEFAULT_CAMPAIGN_SPEC_ID,
        'source_publication_run_id': source_row['run_id'],
        'source_publication_run_root': source_row['run_root'],
        'source_publication_resolved_config': source_row['resolved_config_path'],
        'campaign_lineage': source_row['campaign_lineage'],
        'manuscript_label': source_row['manuscript_label'],
        'family': source_row['family'],
        'model_class': class_name,
        'implementation_mode': source_row.get('implementation_mode', ''),
        'likelihood_mode': source_row.get('likelihood_mode', ''),
        'forecast_transfer_mode': source_row.get('forecast_transfer_mode', ''),
        'publication_crps_display4': source_row['crps_display4'],
        'selected_spec_token': spec_token(source_row),
        'canonical_bundle_meta': str(shared['bundle_meta']),
        'canonical_bundle_root': str(shared['bundle_root']),
        'support_manifest': str(shared['support_manifest']),
        'canonical_fit_covariate_contract': 'PPT|SOIL|PCA(alias=GDPC1)',
        'profile_name': profile_name,
        'transform_policy': 'log1p_only',
        'full_quantiles': full_quantiles,
        'active_quantiles': active_quantiles,
        'fit_parallel_workers_effective': int(workers or 0),
        'mc_cores_effective': int(mc_cores or 0),
        'model_config_key': family_model_key,
        'config_patch_applied': bool(row_config_patch),
        'config_patch_source': row_config_patch_source,
        'config_patch_json': row_config_patch or {},
    }
    return cfg


def _extract_spec_row(plan_row: dict[str, Any], source_row: dict[str, str], cfg: dict[str, Any]) -> dict[str, Any]:
    family = source_row['family']
    model_key = MODEL_KEY_BY_FAMILY[family]
    model_cfg = ((cfg.get('models') or {}).get(model_key) or {})
    fit_cfg = ((cfg.get('fit') or {}).get(model_key) or {})
    state = model_cfg.get('state_evolution', {}) if isinstance(model_cfg, dict) else {}
    legacy = fit_cfg.get('legacy', {}) if isinstance(fit_cfg, dict) else {}
    model_prior_fc = ((model_cfg.get('prior') or {}).get('forecast_cov') or {}) if isinstance(model_cfg, dict) else {}
    legacy_forecast_cov = (legacy.get('forecast_cov') or {}) if isinstance(legacy, dict) else {}
    active_quantiles = [float(q) for q in (((cfg.get('fit') or {}).get('quantiles')) or [])]
    debug = cfg.get('debug_he2_publication_relaunch', {}) if isinstance(cfg.get('debug_he2_publication_relaunch'), dict) else {}
    fit_parallel = (((cfg.get('fit') or {}).get('parallel')) or {})
    run_threads = (((cfg.get('run') or {}).get('threads')) or {})
    scale_contract = ((cfg.get('scale_contract') or {}) if isinstance(cfg.get('scale_contract'), dict) else {})
    row = {
        'run_id': plan_row['run_id'],
        'cutoff': plan_row['cutoff'],
        'family': family,
        'model_key': model_key,
        'model_class': model_class(family),
        'manuscript_label': source_row['manuscript_label'],
        'row_kind': row_kind(family),
        'source_publication_run_id': source_row['run_id'],
        'source_publication_resolved_config': source_row['resolved_config_path'],
        'campaign_lineage': source_row['campaign_lineage'],
        'selected_spec_token': spec_token(source_row),
        'likelihood_mode': source_row.get('likelihood_mode', ''),
        'forecast_transfer_mode': source_row.get('forecast_transfer_mode', ''),
        'implementation_mode': model_cfg.get('implementation_mode', ''),
        'kalman_backend': model_cfg.get('kalman_backend', ''),
        'df_t': state.get('df_t'),
        'df_s1': state.get('df_s1'),
        'df_s2': state.get('df_s2'),
        'df_s67': state.get('df_s67'),
        'df_discrep': state.get('df_discrep'),
        'lambda': state.get('lambda'),
        'df_trans': state.get('df_trans'),
        'df_covs': state.get('df_covs'),
        'lam1': legacy.get('lam1'),
        'lam2': legacy.get('lam2'),
        'n_samp': legacy.get('n_samp'),
        'sims_enabled': legacy.get('sims_enabled'),
        'use_covariates': legacy.get('use_covariates'),
        'fit_parallel_workers': fit_parallel.get('workers'),
        'run_mc_cores': run_threads.get('mc_cores'),
        'legacy_fit_input_scale': scale_contract.get('legacy_fit_input_scale', ''),
        'legacy_post_input_scale': scale_contract.get('legacy_post_input_scale', ''),
        'analysis_scale_fit_internal': scale_contract.get('analysis_scale_fit_internal', ''),
        'analysis_scale_post_internal': scale_contract.get('analysis_scale_post_internal', ''),
        'active_quantiles': '|'.join(render_quantile_label(q) for q in active_quantiles),
        'active_quantile_count': len(active_quantiles),
        'full_quantiles': '|'.join(render_quantile_label(q) for q in debug.get('full_quantiles', active_quantiles)),
        'full_quantile_count': len(debug.get('full_quantiles', active_quantiles)),
        'quantile_subset_applied': bool(model_class(family).startswith('quantile') and len(active_quantiles) < len(debug.get('full_quantiles', active_quantiles))),
        'forecast_cov_c_factor_fit': legacy_forecast_cov.get('c_factor'),
        'forecast_cov_epsilon_fit': legacy_forecast_cov.get('epsilon'),
        'forecast_cov_c_factor_model_prior': model_prior_fc.get('c_factor'),
        'forecast_cov_epsilon_model_prior': model_prior_fc.get('epsilon'),
        'config_patch_applied': bool(debug.get('config_patch_applied', False)),
        'config_patch_source': debug.get('config_patch_source', ''),
        'config_patch_json': json.dumps(debug.get('config_patch_json', {}), sort_keys=True),
        'publication_crps_display4': source_row.get('crps_display4', ''),
        'selected_mean_crps': source_row.get('crps_exact', ''),
        'canonical_bundle_meta': debug.get('canonical_bundle_meta', ''),
        'support_manifest': debug.get('support_manifest', ''),
        'config_path': plan_row['config_path'],
        'compare_outdir': plan_row['compare_outdir'],
        'profile_name': debug.get('profile_name', ''),
    }
    return row


def _build_cutoff_bundle_audit_rows(selected_rows: list[dict[str, Any]], bundle_artifact_root: Path, bundle_run_id: str) -> list[dict[str, Any]]:
    audit_rows: list[dict[str, Any]] = []
    for cutoff in sorted({row['cutoff'] for row in selected_rows}, key=lambda x: EXPECTED_CUTOFFS.index(x) if x in EXPECTED_CUTOFFS else x):
        shared = canonical_shared_paths(bundle_artifact_root, cutoff, bundle_run_id)
        meta = load_yaml(shared['bundle_meta'])
        histfix = meta.get('histfix', {}) if isinstance(meta.get('histfix'), dict) else {}
        retros = pd.read_csv(shared['retros'])
        dates = pd.to_datetime(retros['Date'])
        unique_dates = pd.Index(dates.unique()).sort_values()
        expected = pd.date_range(unique_dates.min(), unique_dates.max(), freq='D') if len(unique_dates) else pd.DatetimeIndex([])
        duplicate_count = int(len(dates) - len(unique_dates))
        missing_days = int(len(expected.difference(unique_dates))) if len(unique_dates) else 0
        cfg = load_yaml(Path(next(row['config_path'] for row in selected_rows if row['cutoff'] == cutoff)))
        det = ((cfg.get('inputs') or {}).get('deterministic_climate') or {})
        pca_df = pd.read_csv(shared['cov_pca'])
        pca_date_col = 'Date' if 'Date' in pca_df.columns else ('time' if 'time' in pca_df.columns else None)
        if pca_date_col is None:
            raise KeyError(f"GDPC alias file missing date column (expected 'Date' or 'time'): {shared['cov_pca']}")
        pca_dates = pd.to_datetime(pca_df[pca_date_col])
        audit_rows.append({
            'cutoff': cutoff,
            'bundle_meta': str(shared['bundle_meta']),
            'bundle_root': str(shared['bundle_root']),
            'retros_path': str(shared['retros']),
            'retros_start': str(unique_dates.min().date()) if len(unique_dates) else '',
            'retros_end': str(unique_dates.max().date()) if len(unique_dates) else '',
            'retros_rows': int(len(retros)),
            'retros_duplicate_dates': duplicate_count,
            'retros_missing_days': missing_days,
            'glofas_source_id': histfix.get('glofas_source_id', ''),
            'glofas_product_id': histfix.get('glofas_product_id', ''),
            'nws_primary_source_id': ((histfix.get('nws_source_policy') or {}).get('primary_source_id', '')),
            'nws_tail_fill_source_id': ((histfix.get('nws_source_policy') or {}).get('tail_fill_source_id', '')),
            'nws_selection_rule': ((histfix.get('nws_source_policy') or {}).get('selection_rule', '')),
            'usgs_daily_source_path': histfix.get('usgs_daily_source_path', ''),
            'support_manifest': histfix.get('support_manifest', ''),
            'forecast_nws_source': ((histfix.get('forecast_member_sources') or {}).get('nws', '')),
            'forecast_glofas_source': ((histfix.get('forecast_member_sources') or {}).get('glofas', '')),
            'deterministic_handoff_root': det.get('handoff_root', ''),
            'deterministic_precip_source': ((det.get('precip') or {}).get('source', '')),
            'deterministic_precip_reduction': ((det.get('precip') or {}).get('reduction', '')),
            'deterministic_soil_source': ((det.get('soil') or {}).get('source', '')),
            'deterministic_soil_reduction': ((det.get('soil') or {}).get('reduction', '')),
            'gdpc_alias_path': str(shared['cov_pca']),
            'gdpc_alias_start': str(pca_dates.min().date()),
            'gdpc_alias_end': str(pca_dates.max().date()),
            'legacy_log_repair_glofas': next((item.get('replaced_nonpositive_count', 0) for item in histfix.get('legacy_log_ready_repairs', []) if item.get('column') == 'glofas_cms'), 0),
            'legacy_log_repair_nws': next((item.get('replaced_nonpositive_count', 0) for item in histfix.get('legacy_log_ready_repairs', []) if item.get('column') == 'nws_cms'), 0),
            'legacy_log_repair_usgs': next((item.get('replaced_nonpositive_count', 0) for item in histfix.get('legacy_log_ready_repairs', []) if item.get('column') == 'usgs_cms'), 0),
        })
    return audit_rows


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='Build the unified HE2 Bayesian publication relaunch configs.')
    ap.add_argument('--config', required=True)
    ap.add_argument('--artifact-root')
    ap.add_argument('--matrix-dir')
    ap.add_argument('--config-output-dir')
    ap.add_argument('--cutoffs', nargs='*')
    ap.add_argument('--families', nargs='*')
    ap.add_argument('--manuscript-labels', nargs='*')
    ap.add_argument('--run-ids', nargs='*')
    ap.add_argument('--model-classes', nargs='*')
    ap.add_argument('--quantiles', nargs='*')
    ap.add_argument('--batch-file')
    ap.add_argument('--profile')
    ap.add_argument('--fit-parallel-workers', type=int)
    ap.add_argument('--mc-cores', type=int)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    campaign_path = Path(args.config).resolve() if Path(args.config).is_absolute() else (Path(__file__).resolve().parents[1] / args.config).resolve()
    campaign = load_yaml(campaign_path)

    campaign_cfg = campaign.get('campaign', {}) if isinstance(campaign.get('campaign'), dict) else {}
    source_cfg = campaign.get('source', {}) if isinstance(campaign.get('source'), dict) else {}
    bundles_cfg = campaign.get('bundles', {}) if isinstance(campaign.get('bundles'), dict) else {}

    request = _selection_spec(args, campaign, campaign_path)
    queue_cfg = request['queue']

    artifact_root = Path(resolve_artifact_root(args.artifact_root or campaign_cfg.get('artifact_root') or DEFAULT_RELAUNCH_ARTIFACT_ROOT))
    matrix_dir = ensure_dir(Path(args.matrix_dir).resolve() if args.matrix_dir else (artifact_root / 'control' / 'publication_relaunch_matrix'))
    config_output_dir = ensure_dir(Path(args.config_output_dir).resolve() if args.config_output_dir else (artifact_root / 'control' / 'generated_configs'))
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))
    ensure_dir(control_dir(artifact_root))

    bundle_artifact_root = Path(str(bundles_cfg.get('artifact_root') or DEFAULT_BUNDLE_ARTIFACT_ROOT)).resolve()
    bundle_run_id = str(bundles_cfg.get('bundle_run_id') or DEFAULT_BUNDLE_RUN_ID)
    manifest_path = Path(str(source_cfg.get('publication_manifest') or Path('reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv')))
    if not manifest_path.is_absolute():
        manifest_path = campaign_path.parents[1] / manifest_path
    manifest_path = manifest_path.resolve()
    campaign_spec_id = str(campaign_cfg.get('campaign_spec_id') or DEFAULT_CAMPAIGN_SPEC_ID)

    rows = [
        row for row in load_publication_manifest_rows(manifest_path)
        if _passes_selection(row, campaign_spec_id=campaign_spec_id, selection=request['selection'])
    ]
    if not rows:
        raise SystemExit('No manifest rows selected for relaunch build.')

    dependency_rows: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    generated_configs: list[Path] = []
    selection_rows: list[dict[str, Any]] = []
    frozen_spec_rows: list[dict[str, Any]] = []

    order_index = 0
    for row in rows:
        cutoff = row['cutoff']
        family = row['family']
        source_cfg_path = Path(row['resolved_config_path'])
        if not source_cfg_path.exists():
            raise FileNotFoundError(f'Missing source resolved_config: {source_cfg_path}')
        shared = canonical_shared_paths(bundle_artifact_root, cutoff, bundle_run_id)
        missing = [str(path) for path in shared.values() if isinstance(path, Path) and not path.exists()]
        if missing:
            raise FileNotFoundError(f'Canonical shared bundle is incomplete for cutoff {cutoff}: {missing[:5]}')

        row_config_patch = _resolve_row_config_patch(request.get('batch_payload', {}), row)

        run_id = _run_id(cutoff, campaign_spec_id, family)
        config_path = config_output_dir / f'{run_id}.yaml'
        cfg = load_yaml(source_cfg_path)
        cfg = _build_run_config(
            cfg,
            run_id=run_id,
            artifact_root=artifact_root,
            cutoff=cutoff,
            bundle_artifact_root=bundle_artifact_root,
            bundle_run_id=bundle_run_id,
            source_row=row,
            resources=request['resources'],
            selected_quantiles=request['selection']['quantiles'],
            profile_name=request['profile'],
            row_config_patch=row_config_patch,
            row_config_patch_source=request['selection'].get('batch_file', ''),
        )
        write_yaml(config_path, cfg)
        generated_configs.append(config_path)
        dependency_rows.extend(_dependency_rows(config_path, cfg))

        order_index += 1
        row_kind_value = row_kind(family)
        is_heavy = cutoff == HEAVY_CUTOFF
        active_quantiles = ((cfg.get('fit') or {}).get('quantiles') or [])
        plan_row = {
            'order_index': order_index,
            'cutoff': cutoff,
            'epsilon': campaign_spec_id,
            'epsilon_value': campaign_spec_id,
            'lane': family,
            'run_scope': 'he2_publication_relaunch',
            'run_id': run_id,
            'config_path': str(config_path),
            'compare_outdir': str(reports_dir(artifact_root) / f'multimodel_{cutoff}_v8_{campaign_spec_id}_compare'),
            'priority_group': 2 if is_heavy else 1,
            'max_concurrent_class': 'heavy' if is_heavy else 'ordinary',
            'family_id': family,
            'model_id': MODEL_ID_BY_FAMILY[family],
            'model_key': MODEL_KEY_BY_FAMILY[family],
            'model_class': model_class(family),
            'likelihood_mode': row.get('likelihood_mode', ''),
            'transfer_mode': row.get('forecast_transfer_mode', ''),
            'authoritative_compare_dir': str(AUTHORITATIVE_COMPARE_BY_CUTOFF[cutoff]),
            'selected_compare_dir': str(AUTHORITATIVE_COMPARE_BY_CUTOFF[cutoff]),
            'selected_source_run': row['run_id'],
            'selected_source_type': row['campaign_lineage'],
            'selected_source_config': row['resolved_config_path'],
            'selected_mean_crps': row['crps_exact'],
            'selected_c_factor': '',
            'selected_epsilon': spec_token(row),
            'cutoff_rank': EXPECTED_CUTOFFS.index(cutoff) + 1,
            'manuscript_label': row['manuscript_label'],
            'row_kind': row_kind_value,
            'quantile_submodels': len(active_quantiles) if model_class(family).startswith('quantile') else 1,
            'publication_crps_display4': row['crps_display4'],
            'active_quantiles': '|'.join(render_quantile_label(float(q)) for q in active_quantiles),
            'profile_name': request['profile'],
        }
        plan_rows.append(plan_row)
        selection_rows.append(dict(plan_row))
        frozen_spec_rows.append(_extract_spec_row(plan_row, row, cfg))

    plan_df = pd.DataFrame(plan_rows).sort_values(['cutoff_rank', 'order_index']).drop(columns=['cutoff_rank'])
    plan_df.to_csv(matrix_dir / 'matrix_plan.csv', index=False)

    dep_df = pd.DataFrame(dependency_rows).sort_values(['consumer_config', 'dependency_type']).reset_index(drop=True)
    dep_df.to_csv(matrix_dir / 'dependency_preservation.csv', index=False)

    selection_df = pd.DataFrame(selection_rows).sort_values(['cutoff', 'manuscript_label']).reset_index(drop=True)
    selection_df.to_csv(matrix_dir / 'selection_summary.csv', index=False)

    frozen_df = pd.DataFrame(frozen_spec_rows).sort_values(['cutoff', 'manuscript_label']).reset_index(drop=True)
    frozen_df.to_csv(matrix_dir / 'frozen_spec_manifest.csv', index=False)
    (matrix_dir / 'frozen_spec_manifest.json').write_text(frozen_df.to_json(orient='records', indent=2) + '\n', encoding='utf-8')

    cutoff_audit_df = pd.DataFrame(_build_cutoff_bundle_audit_rows(plan_rows, bundle_artifact_root, bundle_run_id)).sort_values(['cutoff']).reset_index(drop=True)
    cutoff_audit_df.to_csv(matrix_dir / 'cutoff_bundle_audit.csv', index=False)
    (matrix_dir / 'cutoff_bundle_audit.json').write_text(cutoff_audit_df.to_json(orient='records', indent=2) + '\n', encoding='utf-8')

    status_path = matrix_dir / 'matrix_status.csv'
    if not status_path.exists():
        initialize_matrix_status(status_path)

    metadata = {
        'campaign_id': str(campaign_cfg.get('campaign_id', 'he2_bayesian_publication_relaunch')),
        'campaign_spec_id': campaign_spec_id,
        'campaign_config': str(campaign_path),
        'artifact_root': str(artifact_root),
        'matrix_dir': str(matrix_dir),
        'config_output_dir': str(config_output_dir),
        'publication_manifest': str(manifest_path),
        'bundle_artifact_root': str(bundle_artifact_root),
        'bundle_run_id': bundle_run_id,
        'compare_builder': 'scripts/build_multimodel_v8_all9_feature_compare_bundle.py',
        'request': request,
        'queue': {
            'ordinary_max_concurrent': int(queue_cfg.get('ordinary_max_concurrent', 2)),
            'pause_free_gb': float(queue_cfg.get('pause_free_gb', 180)),
            'launch_free_gb': float(queue_cfg.get('launch_free_gb', 220)),
            'heavy_free_gb': float(queue_cfg.get('heavy_free_gb', 240)),
            'heavy_cutoff_max_concurrent': int(queue_cfg.get('heavy_cutoff_max_concurrent', 1)),
            'heavy_cutoff_blocks_ordinary': bool(queue_cfg.get('heavy_cutoff_blocks_ordinary', True)),
            'poll_seconds': int(queue_cfg.get('poll_seconds', 60)),
        },
    }
    write_yaml(matrix_dir / 'matrix_metadata.yaml', metadata)
    write_yaml(matrix_dir / 'campaign_snapshot.yaml', {'campaign': campaign, 'campaign_path': str(campaign_path), 'resolved_request': request})
    write_yaml(matrix_dir / 'batch_request_snapshot.yaml', request)

    launch_env = '\n'.join([
        f'ARTIFACT_ROOT={artifact_root}',
        f'MATRIX_DIR={matrix_dir}',
        f'ORDINARY_MAX_CONCURRENT={metadata["queue"]["ordinary_max_concurrent"]}',
        f'PAUSE_FREE_GB={metadata["queue"]["pause_free_gb"]}',
        f'LAUNCH_FREE_GB={metadata["queue"]["launch_free_gb"]}',
        f'HEAVY_FREE_GB={metadata["queue"]["heavy_free_gb"]}',
        f'HEAVY_CUTOFF_MAX_CONCURRENT={metadata["queue"]["heavy_cutoff_max_concurrent"]}',
        f'HEAVY_CUTOFF_BLOCKS_ORDINARY={1 if metadata["queue"]["heavy_cutoff_blocks_ordinary"] else 0}',
        f'POLL_SECONDS={metadata["queue"]["poll_seconds"]}',
        '',
    ])
    (matrix_dir / 'launch_settings.env').write_text(launch_env, encoding='utf-8')
    (matrix_dir / 'queue.log').touch()

    lines = [
        '# HE2 Bayesian Publication Relaunch Scope',
        '',
        f'- campaign_config: `{campaign_path}`',
        f'- artifact_root: `{artifact_root}`',
        f'- matrix_dir: `{matrix_dir}`',
        f'- config_output_dir: `{config_output_dir}`',
        f'- publication_manifest: `{manifest_path}`',
        f'- bundle_artifact_root: `{bundle_artifact_root}`',
        f'- bundle_run_id: `{bundle_run_id}`',
        f'- generated_configs: `{len(generated_configs)}`',
        f'- active_profile: `{request["profile"]}`',
        f'- selected_cutoffs: `{", ".join(request["selection"]["cutoffs"])}`',
        f'- selected_families: `{", ".join(request["selection"]["families"])}`',
        f'- selected_manuscript_labels: `{", ".join(request["selection"]["manuscript_labels"]) or "ALL"}`',
        f'- selected_run_ids: `{", ".join(request["selection"]["run_ids"]) or "ALL"}`',
        f'- selected_model_classes: `{", ".join(request["selection"]["model_classes"]) or "ALL"}`',
        f'- selected_quantiles: `{", ".join(render_quantile_label(q) for q in request["selection"]["quantiles"]) or "ALL"}`',
        '',
        '## Workload',
        f'- row launches: `{len(plan_df)}`',
        f'- total fitted submodels: `{int(selection_df["quantile_submodels"].astype(int).sum())}`',
        '',
        '## Queue defaults',
        f'- ordinary_max_concurrent: `{metadata["queue"]["ordinary_max_concurrent"]}`',
        f'- pause_free_gb: `{metadata["queue"]["pause_free_gb"]}`',
        f'- launch_free_gb: `{metadata["queue"]["launch_free_gb"]}`',
        f'- heavy_free_gb: `{metadata["queue"]["heavy_free_gb"]}`',
        f'- heavy_cutoff_max_concurrent: `{metadata["queue"]["heavy_cutoff_max_concurrent"]}`',
        f'- heavy_cutoff_blocks_ordinary: `{metadata["queue"]["heavy_cutoff_blocks_ordinary"]}`',
        f'- poll_seconds: `{metadata["queue"]["poll_seconds"]}`',
        '',
        '## Resource overrides',
        f'- fit_parallel_workers: `{request["resources"].get("fit_parallel_workers")}`',
        f'- mc_cores: `{request["resources"].get("mc_cores")}`',
        '',
        '## Audits',
        '- `frozen_spec_manifest.csv`',
        '- `cutoff_bundle_audit.csv`',
        '- `batch_request_snapshot.yaml`',
        '',
        '## Current disk headroom',
        f'- artifact disk free GB: `{artifact_disk_free_gb(artifact_root)}`',
    ]
    (matrix_dir / 'he2_publication_relaunch_scope.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(f'artifact_root={artifact_root}')
    print(f'matrix_dir={matrix_dir}')
    print(f'config_output_dir={config_output_dir}')
    print(f'generated_configs={len(generated_configs)}')
    print(f'plan_rows={len(plan_df)}')
    print(f'selection_rows={len(selection_df)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
