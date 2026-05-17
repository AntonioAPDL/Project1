#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from he2_publication_relaunch_lib import (
    DEFAULT_BUNDLE_ARTIFACT_ROOT,
    DEFAULT_BUNDLE_RUN_ID,
    DEFAULT_CAMPAIGN_SPEC_ID,
    DEFAULT_DATA_START,
    canonical_shared_paths,
    load_publication_manifest_rows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / 'reports' / 'he2_exdqlm_univar_shared_relaunch_investigation_20260516'
RUNBOOK_PATH = ROOT / 'repro' / 'run' / 'HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md'
HIST_AUDIT = ROOT / 'reports' / 'he2_publication_manifest' / 'historical_support_audit_20260507' / 'historical_support_audit.csv'
KEEP_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516.template.yaml'
KEEP_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516.yaml'
DROP_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.template.yaml'
DROP_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.yaml'
BASE_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_20260510.template.yaml'
LEGACY_TEMPLATE = ROOT / 'config' / 'multimodel_v8_univar_featurecov_he2_rerun_20260422.template.yaml'
LEGACY_RUNBOOK = ROOT / 'repro' / 'run' / 'UNIVAR_FEATURECOV_HE2_RERUN_RUNBOOK.md'
LEGACY_LAUNCHER = ROOT / 'scripts' / 'launch_multimodel_v8_univar_featurecov_he2_rerun.py'
APPROVED_BUILDER = 'scripts/build_he2_bayesian_publication_relaunch_configs.py'
APPROVED_VALIDATOR = 'scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py'
APPROVED_LAUNCHER = 'scripts/launch_he2_bayesian_publication_relaunch.py'
APPROVED_QUEUE = 'scripts/run_multimodel_v8_queue.py'
TARGET_FAMILY = 'exdqlm_univar'
TARGET_MANUSCRIPT_LABEL = 'exAL-U-T1'
MANUAL_SHARED_SPEC_ID = 'set10_manual_20260516'
REFERENCE_KEEP_ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516')
REFERENCE_DROP_ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516')

DIRECT = 'direct_reuse'
ADAPT = 'requires_adaptation'
PARTIAL = 'partial_equivalent'
NA_MAP = 'not_applicable'
CODE_DECISION = 'requires_code_or_policy_decision'


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f'No rows to write: {path}')
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freeze_config(src: Path, dst: Path) -> tuple[str, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    digest = _sha256(dst)
    return str(dst), digest


def _parse_key_value_text(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        out[key.strip()] = value.strip()
    return out


def _nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _stringify(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _load_historical_audit(path: Path = HIST_AUDIT) -> dict[str, dict[str, str]]:
    rows = _read_csv(path)
    return {row['cutoff']: row for row in rows if row['family'] == TARGET_FAMILY}


def _extract_reference_contract() -> dict[str, Any]:
    keep_template = _load_yaml(KEEP_TEMPLATE)
    keep_batch = _load_yaml(KEEP_BATCH)
    drop_template = _load_yaml(DROP_TEMPLATE)
    drop_batch = _load_yaml(DROP_BATCH)
    base_template = _load_yaml(BASE_TEMPLATE)
    legacy_template = _load_yaml(LEGACY_TEMPLATE)

    keep_patch = keep_batch['overrides']['row_config_patches'][0]['config_patch']
    drop_patch = drop_batch['overrides']['row_config_patches'][0]['config_patch']
    keep_fit = keep_patch['fit']['exdqlm_multivar']
    keep_state = keep_patch['models']['exdqlm_multivar']['state_evolution']
    q50 = keep_fit['gamma_sigma']['quantile_overrides']['q50']

    return {
        'approved_paths': {
            'builder': APPROVED_BUILDER,
            'validator': APPROVED_VALIDATOR,
            'launcher': APPROVED_LAUNCHER,
            'queue': APPROVED_QUEUE,
            'base_template': str(BASE_TEMPLATE),
            'manifest_csv': 'reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv',
        },
        'live_reference_roots': {
            'keep': str(REFERENCE_KEEP_ROOT),
            'drop': str(REFERENCE_DROP_ROOT),
        },
        'bundle_contract': {
            'artifact_root': str(keep_template['bundles']['artifact_root']),
            'bundle_run_id': str(keep_template['bundles']['bundle_run_id']),
            'data_start': str(keep_template['bundles']['data_start']),
            'covariates': ['PPT', 'SOIL', 'PCA'],
            'climate_factor_alias': 'PCA(alias=GDPC1)',
            'deterministic_climate_enabled': True,
        },
        'runtime_contract': {
            'queue_ordinary_max_concurrent': int(keep_template['queue']['ordinary_max_concurrent']),
            'queue_pause_free_gb': float(keep_template['queue']['pause_free_gb']),
            'queue_launch_free_gb': float(keep_template['queue']['launch_free_gb']),
            'queue_heavy_free_gb': float(keep_template['queue']['heavy_free_gb']),
            'queue_heavy_cutoff_max_concurrent': int(keep_template['queue']['heavy_cutoff_max_concurrent']),
            'queue_heavy_cutoff_blocks_ordinary': bool(keep_template['queue']['heavy_cutoff_blocks_ordinary']),
            'queue_poll_seconds': int(keep_template['queue']['poll_seconds']),
            'fit_parallel_workers': int(keep_batch['resources']['fit_parallel_workers']),
            'mc_cores': int(keep_batch['resources']['mc_cores']),
            'thread_caps': {
                'omp': int(keep_patch['run']['threads']['omp']),
                'openblas': int(keep_patch['run']['threads']['openblas']),
                'mkl': int(keep_patch['run']['threads']['mkl']),
                'veclib': int(keep_patch['run']['threads']['veclib']),
                'numexpr': int(keep_patch['run']['threads']['numexpr']),
            },
            'legacy_univar_queue_ordinary_max_concurrent': int(legacy_template['queue']['ordinary_max_concurrent']),
        },
        'shared_spec': {
            'id': MANUAL_SHARED_SPEC_ID,
            'epsilon': float(keep_fit['legacy']['forecast_cov']['epsilon']),
            'c_factor': float(keep_fit['legacy']['forecast_cov']['c_factor']),
            'state_evolution': {key: keep_state[key] for key in ['df_t', 'df_s1', 'df_s2', 'df_s67', 'df_discrep', 'lambda', 'df_trans', 'df_covs']},
            'q50_stabilization': {
                'freeze_target': q50['freeze_target'],
                'terminal_sampling_guard_mode': q50['terminal_sampling_guard']['mode'],
                'median_state_hold_after_guard_iters': q50['stabilization']['median_state_hold_after_guard_iters'],
                'median_state_blend_alpha': q50['stabilization']['median_state_blend_alpha'],
                'median_cov_blend_alpha': q50['stabilization']['median_cov_blend_alpha'],
                'median_max_abs_gamma_step': q50['stabilization']['median_max_abs_gamma_step'],
                'median_max_abs_log_sigma_step': q50['stabilization']['median_max_abs_log_sigma_step'],
            },
        },
        'legacy_univar_path': {
            'template': str(LEGACY_TEMPLATE),
            'launcher': str(LEGACY_LAUNCHER),
            'runbook': str(LEGACY_RUNBOOK),
            'queue_ordinary_max_concurrent': int(legacy_template['queue']['ordinary_max_concurrent']),
        },
        'template_contracts': {
            'keep_template': str(KEEP_TEMPLATE),
            'keep_batch': str(KEEP_BATCH),
            'drop_template': str(DROP_TEMPLATE),
            'drop_batch': str(DROP_BATCH),
            'drop_matches_keep_state_spec': keep_patch['models']['exdqlm_multivar']['state_evolution'] == drop_patch['models']['exdqlm_multivar']['state_evolution'],
        },
    }


def _scope_rows(reference_contract: dict[str, Any], out_root: Path) -> list[dict[str, Any]]:
    hist = _load_historical_audit()
    source_freeze_root = out_root / 'source_config_freeze'
    rows: list[dict[str, Any]] = []
    for manifest_row in load_publication_manifest_rows():
        if manifest_row['family'] != TARGET_FAMILY:
            continue
        cutoff = manifest_row['cutoff']
        run_root = Path(manifest_row['run_root'])
        resolved_config_path = Path(manifest_row['resolved_config_path'])
        cfg = _load_yaml(resolved_config_path)
        source_map = _parse_key_value_text(run_root / 'inputs' / 'shared' / 'source_map.txt')
        data_start_summary = _parse_key_value_text(run_root / 'inputs' / 'shared' / 'data_start_filter_summary.txt')
        climate_summary = _parse_key_value_text(run_root / 'inputs' / 'shared' / 'deterministic_climate' / 'deterministic_climate_summary.txt')
        frozen_name = f"{cutoff}_{manifest_row['manuscript_label'].replace('-', '_')}_{TARGET_FAMILY}.resolved_config.yaml"
        frozen_path, resolved_hash = _freeze_config(resolved_config_path, source_freeze_root / frozen_name)

        univar_model = _nested(cfg, 'models', 'exdqlm_univar', default={})
        univar_state = _nested(univar_model, 'state_evolution', default={})
        univar_prior_fc = _nested(univar_model, 'prior', 'forecast_cov', default={})
        univar_fit = _nested(cfg, 'fit', 'exdqlm_univar', default={})
        univar_gs = _nested(univar_fit, 'gamma_sigma', default={})
        legacy = _nested(univar_fit, 'legacy', default={})
        target_shared = canonical_shared_paths(DEFAULT_BUNDLE_ARTIFACT_ROOT, cutoff, DEFAULT_BUNDLE_RUN_ID)
        hist_row = hist[cutoff]

        risks: list[str] = []
        if str(hist_row['full_history_from_1987']).strip().lower() != 'true':
            risks.append(f"historical support starts at {hist_row['effective_common_start']}")
        if manifest_row['campaign_lineage'] != 'univar_featurecov_he2_rerun_20260422':
            risks.append('unexpected campaign lineage drift')
        if not univar_prior_fc:
            risks.append('forecast_cov prior block absent in current univariate source config')
        if 'df_discrep' in univar_state:
            risks.append('unexpected df_discrep present in univar state block')
        risks.append('legacy univar launcher still points at all9 feature builder unless quarantined')

        rows.append({
            'cutoff': cutoff,
            'manuscript_label': manifest_row['manuscript_label'],
            'family': manifest_row['family'],
            'model_class': 'quantile_univariate',
            'current_run_id': manifest_row['run_id'],
            'current_run_root': manifest_row['run_root'],
            'current_campaign_lineage': manifest_row['campaign_lineage'],
            'current_resolved_config_path': manifest_row['resolved_config_path'],
            'frozen_resolved_config_path': frozen_path,
            'resolved_config_sha256': resolved_hash,
            'implementation_mode': manifest_row['implementation_mode'],
            'likelihood_mode': manifest_row['likelihood_mode'],
            'fit_covariate_names': manifest_row['fit_covariate_names'],
            'within_cutoff_shared_inputs_aligned_current': manifest_row['within_cutoff_shared_inputs_aligned'],
            'current_full_history_from_1987': hist_row['full_history_from_1987'],
            'current_effective_common_start': hist_row['effective_common_start'],
            'current_effective_common_end': hist_row['effective_common_end'],
            'current_common_dates_count': hist_row['common_dates_count'],
            'current_source_parameters': source_map.get('source.parameters', ''),
            'current_source_retros': source_map.get('source.retros', ''),
            'current_source_nws': source_map.get('source.nws', ''),
            'current_source_glofas': source_map.get('source.glofas', ''),
            'current_source_usgs': source_map.get('source.usgs', ''),
            'current_usgs_origin': source_map.get('source.usgs_origin', ''),
            'current_handoff_root': climate_summary.get('handoff_root', ''),
            'current_ppt_output': climate_summary.get('precip_output', ''),
            'current_soil_output': climate_summary.get('soil_output', ''),
            'current_pca_passthrough': climate_summary.get('pca_passthrough', ''),
            'current_data_start': data_start_summary.get('data_start', ''),
            'current_source_bundle_root_guess': str(Path(source_map.get('source.retros', '')).parent) if source_map.get('source.retros') else '',
            'proposed_bundle_artifact_root': str(reference_contract['bundle_contract']['artifact_root']),
            'proposed_bundle_run_id': reference_contract['bundle_contract']['bundle_run_id'],
            'proposed_campaign_spec_id': DEFAULT_CAMPAIGN_SPEC_ID,
            'proposed_template_family': TARGET_FAMILY,
            'proposed_manuscript_label': TARGET_MANUSCRIPT_LABEL,
            'current_state_df_t': _stringify(univar_state.get('df_t')),
            'current_state_df_s1': _stringify(univar_state.get('df_s1')),
            'current_state_df_s2': _stringify(univar_state.get('df_s2')),
            'current_state_df_s67': _stringify(univar_state.get('df_s67')),
            'current_state_lambda': _stringify(univar_state.get('lambda')),
            'current_state_df_trans': _stringify(univar_state.get('df_trans')),
            'current_state_df_covs': _stringify(univar_state.get('df_covs')),
            'current_state_df_discrep_present': 'true' if 'df_discrep' in univar_state else 'false',
            'current_prior_forecast_cov_c_factor': _stringify(univar_prior_fc.get('c_factor')),
            'current_prior_forecast_cov_epsilon': _stringify(univar_prior_fc.get('epsilon')),
            'current_gamma_sigma_freeze_target': _stringify(univar_gs.get('freeze_target')),
            'current_gamma_sigma_fail_fast': _stringify(_nested(univar_gs, 'objective_guard', 'fail_fast')),
            'current_gamma_sigma_mode': _stringify(_nested(univar_gs, 'objective_guard', 'mode')),
            'current_gamma_sigma_min_update_iters': _stringify(univar_gs.get('min_update_iters')),
            'current_gamma_sigma_max_iter': _stringify(univar_gs.get('max_iter')),
            'current_legacy_lam1': _stringify(legacy.get('lam1')),
            'current_legacy_lam2': _stringify(legacy.get('lam2')),
            'current_legacy_n_samp': _stringify(legacy.get('n_samp')),
            'risk_summary': '; '.join(risks),
        })
    rows.sort(key=lambda row: row['cutoff'])
    return rows


def _bundle_parity_rows(scope_rows: list[dict[str, Any]], reference_contract: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in scope_rows:
        cutoff = row['cutoff']
        target = canonical_shared_paths(DEFAULT_BUNDLE_ARTIFACT_ROOT, cutoff, DEFAULT_BUNDLE_RUN_ID)
        current_retros = row['current_source_retros']
        current_nws = row['current_source_nws']
        current_glofas = row['current_source_glofas']
        current_parameters = row['current_source_parameters']
        current_ppt = row['current_ppt_output']
        current_soil = row['current_soil_output']
        current_pca = row['current_pca_passthrough']

        rows.append({
            'cutoff': cutoff,
            'current_full_history_from_1987': row['current_full_history_from_1987'],
            'current_effective_common_start': row['current_effective_common_start'],
            'target_data_start': reference_contract['bundle_contract']['data_start'],
            'current_parameters_path': current_parameters,
            'target_parameters_path': str(target['parameters']),
            'parameters_path_matches_target': str(current_parameters == str(target['parameters'])),
            'current_retros_path': current_retros,
            'target_retros_path': str(target['retros']),
            'retros_path_matches_target': str(current_retros == str(target['retros'])),
            'current_nws_path': current_nws,
            'target_nws_path': str(target['nws_forecast']),
            'nws_path_matches_target': str(current_nws == str(target['nws_forecast'])),
            'current_glofas_path': current_glofas,
            'target_glofas_path': str(target['glofas_forecast']),
            'glofas_path_matches_target': str(current_glofas == str(target['glofas_forecast'])),
            'current_cov_ppt_path': current_ppt,
            'target_cov_ppt_path': str(target['cov_ppt']),
            'cov_ppt_matches_target': str(current_ppt == str(target['cov_ppt'])),
            'current_cov_soil_path': current_soil,
            'target_cov_soil_path': str(target['cov_soil']),
            'cov_soil_matches_target': str(current_soil == str(target['cov_soil'])),
            'current_cov_pca_path': current_pca,
            'target_cov_pca_path': str(target['cov_pca']),
            'cov_pca_matches_target': str(current_pca == str(target['cov_pca'])),
            'current_usgs_path': row['current_source_usgs'],
            'current_handoff_root': row['current_handoff_root'],
            'bundle_artifact_root_target': reference_contract['bundle_contract']['artifact_root'],
            'bundle_run_id_target': reference_contract['bundle_contract']['bundle_run_id'],
            'parity_status': ADAPT if any([
                current_parameters != str(target['parameters']),
                current_retros != str(target['retros']),
                current_nws != str(target['nws_forecast']),
                current_glofas != str(target['glofas_forecast']),
                current_ppt != str(target['cov_ppt']),
                current_soil != str(target['cov_soil']),
                current_pca != str(target['cov_pca']),
                str(row['current_full_history_from_1987']).strip().lower() != 'true',
            ]) else DIRECT,
            'notes': 'full bundle swap to canonical 20260510 shared inputs is required for three early/late cutoffs and path normalization is required for all five',
        })
    return rows


def _spec_parity_rows(scope_rows: list[dict[str, Any]], reference_contract: dict[str, Any]) -> list[dict[str, Any]]:
    target_state = reference_contract['shared_spec']['state_evolution']
    representative = scope_rows[0]
    cfg = _load_yaml(Path(representative['current_resolved_config_path']))
    univar_model = _nested(cfg, 'models', 'exdqlm_univar', default={})
    univar_state = _nested(univar_model, 'state_evolution', default={})
    univar_prior_fc = _nested(univar_model, 'prior', 'forecast_cov', default={})
    univar_gs = _nested(cfg, 'fit', 'exdqlm_univar', 'gamma_sigma', default={})
    rows = [
        {
            'category': 'state_evolution',
            'item': 'df_t',
            'config_path': 'models.exdqlm_univar.state_evolution.df_t',
            'current_value': _stringify(univar_state.get('df_t')),
            'target_multivar_shared_value': _stringify(target_state['df_t']),
            'mapping_status': DIRECT if float(univar_state.get('df_t')) == float(target_state['df_t']) else ADAPT,
            'notes': 'same numeric value already present in published univariate rows',
        },
        {
            'category': 'state_evolution',
            'item': 'df_s1',
            'config_path': 'models.exdqlm_univar.state_evolution.df_s1',
            'current_value': _stringify(univar_state.get('df_s1')),
            'target_multivar_shared_value': _stringify(target_state['df_s1']),
            'mapping_status': ADAPT,
            'notes': 'published univariate winner uses 0.9999; shared multivariate contract uses 0.99999',
        },
        {
            'category': 'state_evolution',
            'item': 'df_s2',
            'config_path': 'models.exdqlm_univar.state_evolution.df_s2',
            'current_value': _stringify(univar_state.get('df_s2')),
            'target_multivar_shared_value': _stringify(target_state['df_s2']),
            'mapping_status': ADAPT,
            'notes': 'published univariate winner uses 0.9999; shared multivariate contract uses 0.99999',
        },
        {
            'category': 'state_evolution',
            'item': 'df_s67',
            'config_path': 'models.exdqlm_univar.state_evolution.df_s67',
            'current_value': _stringify(univar_state.get('df_s67')),
            'target_multivar_shared_value': _stringify(target_state['df_s67']),
            'mapping_status': ADAPT,
            'notes': 'published univariate winner uses 0.9999; shared multivariate contract uses 0.99999',
        },
        {
            'category': 'state_evolution',
            'item': 'df_discrep',
            'config_path': 'models.exdqlm_univar.state_evolution.df_discrep',
            'current_value': '<absent>',
            'target_multivar_shared_value': _stringify(target_state['df_discrep']),
            'mapping_status': NA_MAP,
            'notes': 'repo validation explicitly asserts univariate EXDQLM should not gain df_discrep and stage_fit does not read it',
        },
        {
            'category': 'state_evolution',
            'item': 'lambda',
            'config_path': 'models.exdqlm_univar.state_evolution.lambda',
            'current_value': _stringify(univar_state.get('lambda')),
            'target_multivar_shared_value': _stringify(target_state['lambda']),
            'mapping_status': DIRECT if float(univar_state.get('lambda')) == float(target_state['lambda']) else ADAPT,
            'notes': 'same numeric value already present in published univariate rows',
        },
        {
            'category': 'state_evolution',
            'item': 'df_trans',
            'config_path': 'models.exdqlm_univar.state_evolution.df_trans',
            'current_value': _stringify(univar_state.get('df_trans')),
            'target_multivar_shared_value': _stringify(target_state['df_trans']),
            'mapping_status': DIRECT if float(univar_state.get('df_trans')) == float(target_state['df_trans']) else ADAPT,
            'notes': 'same numeric value already present in published univariate rows',
        },
        {
            'category': 'state_evolution',
            'item': 'df_covs',
            'config_path': 'models.exdqlm_univar.state_evolution.df_covs',
            'current_value': _stringify(univar_state.get('df_covs')),
            'target_multivar_shared_value': _stringify(target_state['df_covs']),
            'mapping_status': ADAPT,
            'notes': 'published univariate winner uses 0.99999; shared multivariate contract uses 0.9999999',
        },
        {
            'category': 'forecast_cov_prior',
            'item': 'c_factor',
            'config_path': 'models.exdqlm_univar.prior.forecast_cov.c_factor',
            'current_value': _stringify(univar_prior_fc.get('c_factor')),
            'target_multivar_shared_value': _stringify(reference_contract['shared_spec']['c_factor']),
            'mapping_status': CODE_DECISION,
            'notes': 'current univariate source config has no forecast_cov prior block and the fit-stage path does not consume c_factor for exdqlm_univar',
        },
        {
            'category': 'forecast_cov_prior',
            'item': 'epsilon',
            'config_path': 'models.exdqlm_univar.prior.forecast_cov.epsilon',
            'current_value': _stringify(univar_prior_fc.get('epsilon')),
            'target_multivar_shared_value': _stringify(reference_contract['shared_spec']['epsilon']),
            'mapping_status': CODE_DECISION,
            'notes': 'current univariate source config has no forecast_cov prior block and the fit-stage path does not consume epsilon for exdqlm_univar',
        },
        {
            'category': 'gamma_sigma_policy',
            'item': 'freeze_target',
            'config_path': 'fit.exdqlm_univar.gamma_sigma.freeze_target',
            'current_value': _stringify(univar_gs.get('freeze_target')),
            'target_multivar_shared_value': reference_contract['shared_spec']['q50_stabilization']['freeze_target'],
            'mapping_status': PARTIAL,
            'notes': 'univariate runner supports freeze_target and can map states/gamma_sigma directly',
        },
        {
            'category': 'gamma_sigma_policy',
            'item': 'objective_guard.fail_fast',
            'config_path': 'fit.exdqlm_univar.gamma_sigma.objective_guard.fail_fast',
            'current_value': _stringify(_nested(univar_gs, 'objective_guard', 'fail_fast')),
            'target_multivar_shared_value': 'true',
            'mapping_status': PARTIAL,
            'notes': 'univariate runner supports objective_guard.fail_fast but does not expose multivariate terminal_sampling_guard',
        },
        {
            'category': 'gamma_sigma_policy',
            'item': 'median_state_blend_alpha',
            'config_path': 'fit.exdqlm_univar.gamma_sigma.stabilization.median_state_blend_alpha',
            'current_value': '<unsupported>',
            'target_multivar_shared_value': _stringify(reference_contract['shared_spec']['q50_stabilization']['median_state_blend_alpha']),
            'mapping_status': NA_MAP,
            'notes': 'no equivalent knob exists in run_exdqlm_univar.R or exdqlm_univar gamma-sigma resolver',
        },
        {
            'category': 'gamma_sigma_policy',
            'item': 'median_cov_blend_alpha',
            'config_path': 'fit.exdqlm_univar.gamma_sigma.stabilization.median_cov_blend_alpha',
            'current_value': '<unsupported>',
            'target_multivar_shared_value': _stringify(reference_contract['shared_spec']['q50_stabilization']['median_cov_blend_alpha']),
            'mapping_status': NA_MAP,
            'notes': 'no equivalent knob exists in run_exdqlm_univar.R or exdqlm_univar gamma-sigma resolver',
        },
        {
            'category': 'gamma_sigma_policy',
            'item': 'median_max_abs_gamma_step',
            'config_path': 'fit.exdqlm_univar.gamma_sigma.stabilization.median_max_abs_gamma_step',
            'current_value': '<unsupported>',
            'target_multivar_shared_value': _stringify(reference_contract['shared_spec']['q50_stabilization']['median_max_abs_gamma_step']),
            'mapping_status': NA_MAP,
            'notes': 'no equivalent step-cap knob exists for univariate EXDQLM today',
        },
        {
            'category': 'gamma_sigma_policy',
            'item': 'median_max_abs_log_sigma_step',
            'config_path': 'fit.exdqlm_univar.gamma_sigma.stabilization.median_max_abs_log_sigma_step',
            'current_value': '<unsupported>',
            'target_multivar_shared_value': _stringify(reference_contract['shared_spec']['q50_stabilization']['median_max_abs_log_sigma_step']),
            'mapping_status': NA_MAP,
            'notes': 'no equivalent step-cap knob exists for univariate EXDQLM today',
        },
    ]
    return rows


def _mapping_rows(reference_contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            'component': 'approved_builder',
            'reference_value': APPROVED_BUILDER,
            'mapping_status': DIRECT,
            'reuse_strategy': 'reuse exactly',
            'notes': 'builder already supports family selection and quantile_univariate model class',
        },
        {
            'component': 'approved_validator',
            'reference_value': APPROVED_VALIDATOR,
            'mapping_status': DIRECT,
            'reuse_strategy': 'reuse exactly',
            'notes': 'validator already supports univar fit/full-pipeline smokes through quantile_univariate selection',
        },
        {
            'component': 'queue_controller',
            'reference_value': APPROVED_QUEUE,
            'mapping_status': DIRECT,
            'reuse_strategy': 'reuse exactly',
            'notes': 'root-scoped active-process fix already allows parallel family controllers under separate artifact roots',
        },
        {
            'component': 'bundle_contract',
            'reference_value': reference_contract['bundle_contract']['artifact_root'],
            'mapping_status': DIRECT,
            'reuse_strategy': 'reuse exactly',
            'notes': 'same canonical 20260510 shared-input bundle root should be used per cutoff',
        },
        {
            'component': 'data_start',
            'reference_value': reference_contract['bundle_contract']['data_start'],
            'mapping_status': DIRECT,
            'reuse_strategy': 'reuse exactly',
            'notes': 'full retrospective history start is already enforced in the approved builder path',
        },
        {
            'component': 'deterministic_climate_contract',
            'reference_value': 'PPT/SOIL blended deterministic climate with GDPC-backed PCA slot',
            'mapping_status': DIRECT,
            'reuse_strategy': 'reuse exactly',
            'notes': 'univariate publication rows already use the same covariate names and deterministic climate support assets',
        },
        {
            'component': 'runtime_posture',
            'reference_value': '7 quantile workers, 7 mc_cores, thread caps = 1',
            'mapping_status': DIRECT,
            'reuse_strategy': 'reuse exactly',
            'notes': 'published univariate rerun already used one core per quantile and should keep that posture for parity',
        },
        {
            'component': 'artifact_root_naming',
            'reference_value': 'multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516',
            'mapping_status': ADAPT,
            'reuse_strategy': 'new univar-specific artifact root with sharedspec naming',
            'notes': 'needs a dedicated exdqlm_univar sharedspec root so it can queue in parallel without colliding with keep/drop',
        },
        {
            'component': 'template_and_batch',
            'reference_value': 'multivar keep/drop sharedspec template + batch pair',
            'mapping_status': ADAPT,
            'reuse_strategy': 'create univar twin template and batch using approved publication relaunch style',
            'notes': 'selection/family/model_class must target exdqlm_univar / quantile_univariate',
        },
        {
            'component': 'shared_discount_bundle',
            'reference_value': MANUAL_SHARED_SPEC_ID,
            'mapping_status': PARTIAL,
            'reuse_strategy': 'project applicable state-evolution fields into univar state block',
            'notes': 'df_discrep has no univar state slot and must remain excluded to preserve current univar family contract',
        },
        {
            'component': 'shared_epsilon_c_factor',
            'reference_value': 'epsilon=30.0, c_factor=1.0',
            'mapping_status': CODE_DECISION,
            'reuse_strategy': 'decide whether to keep as metadata only or extend fit-stage to consume them',
            'notes': 'current exdqlm_univar fit path does not read forecast_cov prior knobs and the published univariate source config does not currently define that block',
        },
        {
            'component': 'q50_stabilization',
            'reference_value': 'states freeze + fail_fast + median blend/step caps',
            'mapping_status': PARTIAL,
            'reuse_strategy': 'reuse freeze_target/init/objective_guard subset; validate separately',
            'notes': 'multivariate median-specific stabilization knobs do not exist for univariate EXDQLM today',
        },
        {
            'component': 'legacy_univar_launcher',
            'reference_value': str(LEGACY_LAUNCHER),
            'mapping_status': ADAPT,
            'reuse_strategy': 'quarantine and do not reuse',
            'notes': 'points to legacy all9-feature builder/validator path rather than the approved publication relaunch workflow',
        },
    ]


def _readiness_summary(scope_rows: list[dict[str, Any]], bundle_rows: list[dict[str, Any]], spec_rows: list[dict[str, Any]], mapping_rows: list[dict[str, Any]]) -> dict[str, Any]:
    full_history_failures = [row['cutoff'] for row in scope_rows if str(row['current_full_history_from_1987']).strip().lower() != 'true']
    bundle_mismatches = [row['cutoff'] for row in bundle_rows if row['parity_status'] != DIRECT]
    spec_requires_adaptation = [row['item'] for row in spec_rows if row['mapping_status'] in {ADAPT, PARTIAL, CODE_DECISION, NA_MAP}]
    open_questions = [row['component'] for row in mapping_rows if row['mapping_status'] in {ADAPT, PARTIAL, CODE_DECISION}]
    return {
        'family': TARGET_FAMILY,
        'manuscript_label': TARGET_MANUSCRIPT_LABEL,
        'status': 'INVESTIGATED_ONLY',
        'ready_for_no_launch_packaging': False,
        'ready_for_launch_after_validation': False,
        'why_not_ready': [
            'no univariate sharedspec template/batch exists yet under the approved publication relaunch path',
            'shared discount-spec bundle must be projected because df_discrep is not applicable to exdqlm_univar',
            'epsilon/c_factor are not currently consumed by the exdqlm_univar fit-stage path and the published univariate source config does not define a forecast_cov prior block',
            'multivariate q50 stabilization has only a partial equivalent in the univariate runner and needs targeted smoke validation',
        ],
        'scope_rows': len(scope_rows),
        'cutoffs': [row['cutoff'] for row in scope_rows],
        'cutoffs_missing_full_history_today': full_history_failures,
        'cutoffs_needing_bundle_swap': bundle_mismatches,
        'spec_items_requiring_action': spec_requires_adaptation,
        'open_questions': open_questions,
        'next_gate': 'codify_univariate sharedspec projection and no-launch package before any validator or queue action',
    }


def build_outputs(out_root: Path = OUT_ROOT) -> dict[str, Any]:
    reference_contract = _extract_reference_contract()
    scope_rows = _scope_rows(reference_contract, out_root)
    bundle_rows = _bundle_parity_rows(scope_rows, reference_contract)
    spec_rows = _spec_parity_rows(scope_rows, reference_contract)
    mapping_rows = _mapping_rows(reference_contract)
    readiness = _readiness_summary(scope_rows, bundle_rows, spec_rows, mapping_rows)
    return {
        'reference_contract': reference_contract,
        'scope_rows': scope_rows,
        'bundle_rows': bundle_rows,
        'spec_rows': spec_rows,
        'mapping_rows': mapping_rows,
        'readiness': readiness,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    ref = payload['reference_contract']
    scope_rows = payload['scope_rows']
    bundle_rows = payload['bundle_rows']
    spec_rows = payload['spec_rows']
    mapping_rows = payload['mapping_rows']
    readiness = payload['readiness']

    lines: list[str] = []
    lines.append('# HE2 exdqlm_univar Shared Relaunch Investigation')
    lines.append('')
    lines.append('Date: 2026-05-16')
    lines.append('')
    lines.append('## Decision boundary')
    lines.append('')
    lines.append('- posture: `INVESTIGATION_ONLY`')
    lines.append('- launch status: `DO NOT LAUNCH`')
    lines.append('- target family: `exdqlm_univar` (`exAL-U-T1`)')
    lines.append('- reference multivariate contracts: live `exdqlm_multivar_keep` and live `exdqlm_multivar_drop` shared-spec relaunches')
    lines.append('')
    lines.append('## Phase A: current multivariate reference contract')
    lines.append('')
    lines.append('| Contract Area | Approved Value | Evidence |')
    lines.append('|---|---|---|')
    lines.append(f"| builder | `{ref['approved_paths']['builder']}` | current approved publication relaunch path |")
    lines.append(f"| validator | `{ref['approved_paths']['validator']}` | current approved publication relaunch path |")
    lines.append(f"| launcher | `{ref['approved_paths']['launcher']}` | current approved publication relaunch path |")
    lines.append(f"| queue/controller | `{ref['approved_paths']['queue']}` | current root-scoped queue path |")
    lines.append(f"| shared bundle root | `{ref['bundle_contract']['artifact_root']}` | current keep/drop sharedspec templates and live runs |")
    lines.append(f"| shared bundle run id | `{ref['bundle_contract']['bundle_run_id']}` | current keep/drop sharedspec templates and live runs |")
    lines.append(f"| data_start | `{ref['bundle_contract']['data_start']}` | current approved builder contract |")
    lines.append(f"| covariates | `{', '.join(ref['bundle_contract']['covariates'])}` | manifest + canonical shared bundle paths |")
    lines.append(f"| climate factor alias | `{ref['bundle_contract']['climate_factor_alias']}` | deterministic climate / PCA passthrough contract |")
    lines.append(f"| fit_parallel_workers | `{ref['runtime_contract']['fit_parallel_workers']}` | sharedspec batch resource block |")
    lines.append(f"| mc_cores | `{ref['runtime_contract']['mc_cores']}` | sharedspec batch resource block |")
    lines.append(f"| queue ordinary_max_concurrent | `{ref['runtime_contract']['queue_ordinary_max_concurrent']}` | sharedspec templates |")
    lines.append('')
    lines.append('### Shared multivariate science spec')
    lines.append('')
    lines.append('| Item | Value |')
    lines.append('|---|---|')
    lines.append(f"| `epsilon` | `{ref['shared_spec']['epsilon']}` |")
    lines.append(f"| `c_factor` | `{ref['shared_spec']['c_factor']}` |")
    for key, value in ref['shared_spec']['state_evolution'].items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.append(f"| `q50.freeze_target` | `{ref['shared_spec']['q50_stabilization']['freeze_target']}` |")
    lines.append(f"| `q50.terminal_sampling_guard.mode` | `{ref['shared_spec']['q50_stabilization']['terminal_sampling_guard_mode']}` |")
    lines.append(f"| `q50.median_state_blend_alpha` | `{ref['shared_spec']['q50_stabilization']['median_state_blend_alpha']}` |")
    lines.append(f"| `q50.median_cov_blend_alpha` | `{ref['shared_spec']['q50_stabilization']['median_cov_blend_alpha']}` |")
    lines.append('')
    lines.append('## Phase B: exact univariate target scope')
    lines.append('')
    lines.append('| Cutoff | Label | Family | Current Run ID | Current Campaign | Implementation | Likelihood | Full History Today | Risk Summary |')
    lines.append('|---|---|---|---|---|---|---|---|---|')
    for row in scope_rows:
        lines.append(
            f"| `{row['cutoff']}` | `{row['manuscript_label']}` | `{row['family']}` | `{row['current_run_id']}` | `{row['current_campaign_lineage']}` | `{row['implementation_mode']}` | `{row['likelihood_mode']}` | `{row['current_full_history_from_1987']}` | {row['risk_summary']} |"
        )
    lines.append('')
    lines.append('Scope conclusion: the correct target is exactly `exdqlm_univar`, one row per HE2 cutoff, manuscript label `exAL-U-T1`.')
    lines.append('')
    lines.append('## Phase C: bundle parity audit')
    lines.append('')
    lines.append('| Cutoff | Full History Today | Current Effective Start | Retros Matches Target | NWS Matches Target | GloFAS Matches Target | PPT Matches Target | SOIL Matches Target | PCA Matches Target | Parity Status |')
    lines.append('|---|---|---|---|---|---|---|---|---|---|')
    for row in bundle_rows:
        lines.append(
            f"| `{row['cutoff']}` | `{row['current_full_history_from_1987']}` | `{row['current_effective_common_start']}` | `{row['retros_path_matches_target']}` | `{row['nws_path_matches_target']}` | `{row['glofas_path_matches_target']}` | `{row['cov_ppt_matches_target']}` | `{row['cov_soil_matches_target']}` | `{row['cov_pca_matches_target']}` | `{row['parity_status']}` |"
        )
    lines.append('')
    lines.append('Bundle conclusion: the univariate family can and should use the exact same corrected 20260510 shared bundle lineage as multivariate keep/drop, but every current publication-source row still needs an explicit bundle path swap under the approved builder path.')
    lines.append('')
    lines.append('## Phase C: spec parity audit')
    lines.append('')
    lines.append('| Item | Current | Target Sharedspec | Status | Notes |')
    lines.append('|---|---|---|---|---|')
    for row in spec_rows:
        lines.append(
            f"| `{row['config_path']}` | `{row['current_value']}` | `{row['target_multivar_shared_value']}` | `{row['mapping_status']}` | {row['notes']} |"
        )
    lines.append('')
    lines.append('Spec conclusion:')
    lines.append('')
    lines.append('- `df_t`, `lambda`, and `df_trans` already match the multivariate sharedspec numerically.')
    lines.append('- `df_s1`, `df_s2`, `df_s67`, and `df_covs` require explicit univariate value overrides if we want numeric parity with the multivariate sharedspec.')
    lines.append('- `df_discrep` is not applicable to `exdqlm_univar` in the current code path and should not be forced into the univariate state block.')
    lines.append('- `epsilon` and `c_factor` do not currently have an operative univariate home: the published univariate source config does not define `models.exdqlm_univar.prior.forecast_cov`, and the fit-stage path does not consume those knobs for `exdqlm_univar`.')
    lines.append('')
    lines.append('## Phase C: directly reusable vs adaptation mapping')
    lines.append('')
    lines.append('| Component | Status | Reuse Strategy | Notes |')
    lines.append('|---|---|---|---|')
    for row in mapping_rows:
        lines.append(f"| `{row['component']}` | `{row['mapping_status']}` | {row['reuse_strategy']} | {row['notes']} |")
    lines.append('')
    lines.append('## Phase D: launcher / builder / template adaptation plan')
    lines.append('')
    lines.append('Recommended new files:')
    lines.append('')
    lines.append('- `config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml`')
    lines.append('- `config/he2_relaunch_batches/exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml`')
    lines.append('- `repro/run/HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md`')
    lines.append('- `reports/he2_exdqlm_univar_shared_relaunch_plan_20260516/` (future no-launch package outputs)')
    lines.append('- `tests/python/test_he2_exdqlm_univar_sharedspec_package.py`')
    lines.append('')
    lines.append('Recommended edits:')
    lines.append('')
    lines.append(f"- `{APPROVED_BUILDER}`: likely no family-support changes needed; only use it through a new univariate sharedspec template/batch.")
    lines.append(f"- `{APPROVED_VALIDATOR}`: likely no code changes needed, but the new univariate template should set `cutoff_smoke_family`, `univar_quantile_fit_smoke_family`, and `full_pipeline_univar_quantile_family` explicitly to `exdqlm_univar`.")
    lines.append(f"- `{APPROVED_QUEUE}`: no code change expected; reuse current root-scoped behavior under a separate univariate artifact root.")
    lines.append('')
    lines.append('## Phase E: no-launch validation plan')
    lines.append('')
    lines.append('1. Build the univariate sharedspec configs with the approved builder.')
    lines.append('2. Inspect generated configs for:')
    lines.append('   - canonical 20260510 bundle paths')
    lines.append('   - `data_start = 1987-05-29`')
    lines.append('   - `fit_parallel_workers = 7`, `mc_cores = 7`, thread caps = 1')
    lines.append('   - `models.run_exdqlm_univar = true` and no stray family flags')
    lines.append('3. Run the approved prelaunch validator on the final exact batch.')
    lines.append('4. Add targeted univariate quantile smokes, at minimum:')
    lines.append('   - `20210123 q50`')
    lines.append('   - `20211221 q50`')
    lines.append('   - `20221225 q50`')
    lines.append('   - one full-pipeline univariate smoke row')
    lines.append('5. Add a queue/controller dry check proving a third family artifact root can coexist with live keep/drop without cross-root blocking.')
    lines.append('')
    lines.append('## Phase F: staged implementation plan')
    lines.append('')
    lines.append('| Stage | Objective | Files / Scripts | Success Criteria | Launch Boundary |')
    lines.append('|---|---|---|---|---|')
    lines.append(f"| `Stage 0` | Freeze the univariate investigation contract. | `{Path(__file__).name}`, scope/parity CSVs, this report | scope and parity artifacts rebuild deterministically | `do not launch` |")
    lines.append(f"| `Stage 1` | Create the univariate sharedspec template and batch on the approved publication relaunch path. | new template/batch + `{RUNBOOK_PATH}` | builder selects exactly 5 `exdqlm_univar` rows | `do not launch` |")
    lines.append(f"| `Stage 2` | Encode the univariate sharedspec projection. | batch row patch + tests | state-evolution overrides are explicit, `df_discrep` remains absent, epsilon/c_factor decision is documented | `do not launch` |")
    lines.append(f"| `Stage 3` | Run no-launch validation. | `{APPROVED_VALIDATOR}` + focused tests | builder dry-run, bundle audit, univariate q50/full-pipeline smokes all pass | `do not launch` |")
    lines.append(f"| `Stage 4` | Parallel-launch readiness review. | queue compatibility note + validation status report | explicit conclusion that a third family can run beside live keep/drop | `ready for launch after validation` |")
    lines.append('')
    lines.append('## Risks / blockers / open questions')
    lines.append('')
    lines.append('1. `df_discrep` is a multivariate-only part of the shared discount bundle today. Forcing it into univariate would contradict existing repo validation expectations.')
    lines.append('2. `epsilon` and `c_factor` are present in the univariate source config but are not read by the current univariate fit-stage path. We need an explicit choice between preserving model identity and extending the code.')
    lines.append('3. The multivariate q50 stabilization layer has only a partial univariate equivalent. Univariate needs its own smoke-confirmed q50 policy rather than a blind copy.')
    lines.append('4. The legacy univariate launcher is intentionally out of contract for this corrected relaunch and must stay quarantined.')
    lines.append('')
    lines.append('## Readiness conclusion')
    lines.append('')
    lines.append(f"- readiness status: `{readiness['status']}`")
    lines.append(f"- ready_for_no_launch_packaging: `{readiness['ready_for_no_launch_packaging']}`")
    lines.append(f"- ready_for_launch_after_validation: `{readiness['ready_for_launch_after_validation']}`")
    lines.append('')
    lines.append('Current conclusion: we are ready to implement the univariate sharedspec package cleanly, but we are **not** ready to claim launch readiness until we codify the univariate-specific spec projection and validate a partial q50 stabilization strategy under the approved no-launch path.')
    lines.append('')
    return '\n'.join(lines) + '\n'


def write_outputs(out_root: Path = OUT_ROOT) -> dict[str, Any]:
    payload = build_outputs(out_root=out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    _write_csv(out_root / 'exdqlm_univar_scope_matrix.csv', payload['scope_rows'])
    _write_csv(out_root / 'bundle_parity_table.csv', payload['bundle_rows'])
    _write_csv(out_root / 'spec_parity_table.csv', payload['spec_rows'])
    _write_csv(out_root / 'reuse_adaptation_mapping_table.csv', payload['mapping_rows'])
    _write_json(out_root / 'reference_contract.json', payload['reference_contract'])
    _write_json(out_root / 'readiness_summary.json', payload['readiness'])
    (out_root / 'HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_INVESTIGATION_20260516.md').write_text(
        _render_markdown(payload),
        encoding='utf-8',
    )
    return payload


def main() -> int:
    write_outputs()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
