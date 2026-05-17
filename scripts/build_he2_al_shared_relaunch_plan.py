#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from he2_publication_relaunch_lib import (
    DEFAULT_BUNDLE_ARTIFACT_ROOT,
    DEFAULT_BUNDLE_RUN_ID,
    DEFAULT_DATA_START,
    EXPECTED_CUTOFF_TO_DATE,
    canonical_shared_paths,
    load_publication_manifest_rows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / 'reports' / 'he2_al_shared_relaunch_plan_20260517'
RUNBOOK = ROOT / 'repro' / 'run' / 'HE2_AL_SHARED_RELAUNCH_PLAN_20260517.md'
PUBLICATION_MANIFEST = ROOT / 'reports' / 'he2_publication_manifest' / 'he2_bayesian_publication_manifest.csv'

FAMILIES: dict[str, dict[str, Any]] = {
    'dqlm_multivar_al_keep': {
        'manuscript_label': 'AL-M-T1',
        'model_class': 'quantile_multivariate',
        'model_key': 'exdqlm_multivar',
        'reference_exal_family': 'exdqlm_multivar_keep',
        'template': ROOT / 'config' / 'he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.template.yaml',
        'batch': ROOT / 'config' / 'he2_relaunch_batches' / 'dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.yaml',
        'validator_outdir': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517/control/prelaunch_validation_exact_final_batch_20260517'),
        'artifact_root': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517'),
        'shared_state': {
            'df_t': 0.99999999,
            'df_s1': 0.99999,
            'df_s2': 0.99999,
            'df_s67': 0.99999,
            'df_discrep': 0.99999,
            'lambda': 0.97,
            'df_trans': 0.9999999,
            'df_covs': 0.9999999,
        },
        'forecast_cov': {'epsilon': 30.0, 'c_factor': 1.0},
        'q50_contract': 'shared q50 block is copied from exAL twin; AL fit path ignores non-operative median state-guard controls by design',
    },
    'dqlm_multivar_al_drop': {
        'manuscript_label': 'AL-M-T0',
        'model_class': 'quantile_multivariate',
        'model_key': 'exdqlm_multivar',
        'reference_exal_family': 'exdqlm_multivar_drop',
        'template': ROOT / 'config' / 'he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml',
        'batch': ROOT / 'config' / 'he2_relaunch_batches' / 'dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.yaml',
        'validator_outdir': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517/control/prelaunch_validation_exact_final_batch_20260517'),
        'artifact_root': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517'),
        'shared_state': {
            'df_t': 0.99999999,
            'df_s1': 0.99999,
            'df_s2': 0.99999,
            'df_s67': 0.99999,
            'df_discrep': 0.99999,
            'lambda': 0.97,
            'df_trans': 0.9999999,
            'df_covs': 0.9999999,
        },
        'forecast_cov': {'epsilon': 30.0, 'c_factor': 1.0},
        'q50_contract': 'shared q50 block is copied from exAL twin; AL fit path ignores non-operative median state-guard controls by design',
    },
    'dqlm_univar_al': {
        'manuscript_label': 'AL-U-T1',
        'model_class': 'quantile_univariate',
        'model_key': 'exdqlm_univar',
        'reference_exal_family': 'exdqlm_univar',
        'template': ROOT / 'config' / 'he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml',
        'batch': ROOT / 'config' / 'he2_relaunch_batches' / 'dqlm_univar_al_all_cutoffs_sharedspec_20260517.yaml',
        'validator_outdir': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_univar_al_all_cutoffs_sharedspec_20260517/control/prelaunch_validation_exact_final_batch_20260517'),
        'artifact_root': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_univar_al_all_cutoffs_sharedspec_20260517'),
        'shared_state': {
            'df_t': 0.99999999,
            'df_s1': 0.99999,
            'df_s2': 0.99999,
            'df_s67': 0.99999,
            'lambda': 0.97,
            'df_trans': 0.9999999,
            'df_covs': 0.9999999,
        },
        'forecast_cov': None,
        'q50_contract': 'no exAL-style q50 gamma/sigma stabilization is injected; AL legacy_bridge remains sigma-only with gamma fixed at 0',
    },
}

CODE_EVIDENCE = [
    {
        'area': 'family_ids',
        'path': 'config/multimodel_v8_all9_featurecov.template.yaml',
        'summary': 'Historical AL families already exist as first-class family ids with likelihood_mode=al and model_key mapped onto exdqlm implementations.',
    },
    {
        'area': 'fit_mode_plumbing',
        'path': 'R/unified/stages/stage_fit.R',
        'summary': 'Modern unified fit stage exports DISC_W_LIKELIHOOD_MODE and UNIV_LIKELIHOOD_MODE so AL vs exAL is selected at runtime without a separate launcher path.',
    },
    {
        'area': 'multivar_al_operative_contract',
        'path': 'DISC_Optimal_Synth_Ranges_W_transfer_forecast.r',
        'summary': 'AL mode fixes gamma to 0, forces E.sts and E.sts2 to 0, and reduces the gamma/scale delta approximation to sigma-only optimization.',
    },
    {
        'area': 'univar_al_operative_contract',
        'path': 'R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R',
        'summary': 'AL mode initializes gamma at 0, keeps Es at 0, ignores gamma inside the objective, and solves only for sigma in the legacy_bridge univariate fit loop.',
    },
    {
        'area': 'post_model_identity',
        'path': 'R/environmetrics/02_helpers_core.R',
        'summary': 'Post/report helper code already maps AL likelihood_mode rows to dqlm_* synth model ids, so AL output identities are already supported in the modern post pipeline.',
    },
    {
        'area': 'publication_lineage',
        'path': 'reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv',
        'summary': 'Historical HE2 publication rows already include AL-U-T1, AL-M-T0, and AL-M-T1 across all five cutoffs with the same covariate/lag/interaction contract as their exAL counterparts.',
    },
]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f'No rows for {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _parse_key_value_text(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        out[key.strip()] = value.strip()
    return out


def _freeze_config(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _scope_rows(out_root: Path) -> list[dict[str, Any]]:
    freeze_root = out_root / 'source_config_freeze'
    rows: list[dict[str, Any]] = []
    for manifest_row in load_publication_manifest_rows(PUBLICATION_MANIFEST):
        family = manifest_row['family']
        if family not in FAMILIES:
            continue
        info = FAMILIES[family]
        cutoff = manifest_row['cutoff']
        run_root = Path(manifest_row['run_root'])
        cfg_path = Path(manifest_row['resolved_config_path'])
        cfg = _load_yaml(cfg_path)
        source_map = _parse_key_value_text(run_root / 'inputs' / 'shared' / 'source_map.txt')
        data_start = _parse_key_value_text(run_root / 'inputs' / 'shared' / 'data_start_filter_summary.txt')
        climate = _parse_key_value_text(run_root / 'inputs' / 'shared' / 'deterministic_climate' / 'deterministic_climate_summary.txt')
        frozen_name = f"{cutoff}_{info['manuscript_label'].replace('-', '_')}_{family}.resolved_config.yaml"
        _freeze_config(cfg_path, freeze_root / frozen_name)
        model_cfg = cfg['models'][info['model_key']]
        state = model_cfg['state_evolution']
        fit_cov = cfg['inputs']['covariate_features']
        fit_covariates = '|'.join(cfg['fit']['covariate_names']) if cfg.get('fit', {}).get('covariate_names') else ''
        legacy_fcov = cfg.get('fit', {}).get('exdqlm_multivar', {}).get('legacy', {}).get('forecast_cov', {}) if family.startswith('dqlm_multivar') else {}
        rows.append({
            'cutoff': cutoff,
            'family': family,
            'manuscript_label': manifest_row['manuscript_label'],
            'reference_exal_family': info['reference_exal_family'],
            'model_key': info['model_key'],
            'model_class': info['model_class'],
            'current_run_id': manifest_row['run_id'],
            'current_run_root': manifest_row['run_root'],
            'current_campaign_lineage': manifest_row['campaign_lineage'],
            'current_resolved_config_path': manifest_row['resolved_config_path'],
            'frozen_resolved_config_path': str(freeze_root / frozen_name),
            'historical_likelihood_mode': str(model_cfg.get('likelihood_mode', '')).lower(),
            'historical_implementation_mode': str(model_cfg.get('implementation_mode', '')),
            'historical_df_t': state['df_t'],
            'historical_df_s1': state['df_s1'],
            'historical_df_s2': state['df_s2'],
            'historical_df_s67': state['df_s67'],
            'historical_df_discrep': state.get('df_discrep', ''),
            'historical_lambda': state['lambda'],
            'historical_df_trans': state['df_trans'],
            'historical_df_covs': state['df_covs'],
            'historical_epsilon': legacy_fcov.get('epsilon', ''),
            'historical_c_factor': legacy_fcov.get('c_factor', ''),
            'historical_fit_covariates': fit_covariates,
            'historical_lag_orders': '|'.join(str(x) for x in fit_cov.get('lag_orders', [])),
            'historical_include_squares': fit_cov.get('include_squares', ''),
            'historical_include_interaction': fit_cov.get('include_interaction', ''),
            'historical_bundle_root': source_map.get('bundle_root', ''),
            'historical_data_start': data_start.get('data_start', ''),
            'historical_common_date_min': data_start.get('common_date_min', ''),
            'historical_common_date_max': data_start.get('common_date_max', ''),
            'historical_precip_source': climate.get('precip_source', ''),
            'historical_soil_source': climate.get('soil_source', ''),
            'historical_pca_path_present': bool(climate.get('pca_path', '')),
            'proposed_template': str(info['template']),
            'proposed_batch': str(info['batch']),
            'proposed_validator_outdir': str(info['validator_outdir']),
        })
    rows.sort(key=lambda row: (row['family'], row['cutoff']))
    return rows


def _bundle_rows(scope_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in scope_rows:
        cutoff = row['cutoff']
        shared = canonical_shared_paths(DEFAULT_BUNDLE_ARTIFACT_ROOT, cutoff, DEFAULT_BUNDLE_RUN_ID)
        rows.append({
            'family': row['family'],
            'cutoff': cutoff,
            'historical_bundle_root': row['historical_bundle_root'],
            'canonical_bundle_root': str(shared['bundle_root']),
            'historical_data_start': row['historical_data_start'],
            'canonical_data_start': DEFAULT_DATA_START,
            'historical_common_date_min': row['historical_common_date_min'],
            'canonical_common_date_min': DEFAULT_DATA_START,
            'historical_full_history_from_1987': str(row['historical_common_date_min'] == DEFAULT_DATA_START).lower(),
            'target_full_history_from_1987': 'true',
            'historical_precip_source': row['historical_precip_source'],
            'historical_soil_source': row['historical_soil_source'],
            'target_precip_source': 'gefs_apcp blended with observed PPT',
            'target_soil_source': 'gefs_soilw_0_0.1m blended with observed SOIL',
            'historical_pca_path_present': row['historical_pca_path_present'],
            'target_pca_alias': 'PCA(alias=GDPC1)',
            'needs_bundle_swap': str(row['historical_bundle_root'] != str(shared['bundle_root'])).lower(),
        })
    return rows


def _spec_rows(scope_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in scope_rows:
        info = FAMILIES[row['family']]
        shared_state = info['shared_state']
        fcov = info['forecast_cov'] or {}
        rows.append({
            'family': row['family'],
            'cutoff': row['cutoff'],
            'historical_likelihood_mode': row['historical_likelihood_mode'],
            'target_likelihood_mode': 'al',
            'historical_implementation_mode': row['historical_implementation_mode'],
            'target_implementation_mode': 'legacy_bridge',
            'historical_df_t': row['historical_df_t'],
            'target_df_t': shared_state['df_t'],
            'historical_df_s1': row['historical_df_s1'],
            'target_df_s1': shared_state['df_s1'],
            'historical_df_s2': row['historical_df_s2'],
            'target_df_s2': shared_state['df_s2'],
            'historical_df_s67': row['historical_df_s67'],
            'target_df_s67': shared_state['df_s67'],
            'historical_df_discrep': row['historical_df_discrep'],
            'target_df_discrep': shared_state.get('df_discrep', ''),
            'historical_lambda': row['historical_lambda'],
            'target_lambda': shared_state['lambda'],
            'historical_df_trans': row['historical_df_trans'],
            'target_df_trans': shared_state['df_trans'],
            'historical_df_covs': row['historical_df_covs'],
            'target_df_covs': shared_state['df_covs'],
            'historical_epsilon': row['historical_epsilon'],
            'target_epsilon': fcov.get('epsilon', ''),
            'historical_c_factor': row['historical_c_factor'],
            'target_c_factor': fcov.get('c_factor', ''),
            'gamma_zero_operational': 'true',
            'st_zero_operational': 'true',
            'sigma_only_delta_optimization': 'true',
            'shared_discount_bundle_reuses_exal_sharedspec': 'true',
            'note': info['q50_contract'],
        })
    return rows


def _reuse_rows() -> list[dict[str, Any]]:
    return [
        {
            'component': 'manifest-driven builder',
            'status': 'directly_reusable',
            'path': 'scripts/build_he2_bayesian_publication_relaunch_configs.py',
            'note': 'AL families are already present in MODEL_ID_BY_FAMILY and MODEL_KEY_BY_FAMILY.',
        },
        {
            'component': 'prelaunch validator',
            'status': 'directly_reusable',
            'path': 'scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py',
            'note': 'No family-specific launcher fork is needed; AL rows validate through the same smoke pipeline.',
        },
        {
            'component': 'queue/controller',
            'status': 'directly_reusable',
            'path': 'scripts/run_multimodel_v8_queue.py',
            'note': 'AL packages use the same serial-by-cutoff queue contract and artifact-root-scoped controller behavior.',
        },
        {
            'component': 'shared input bundles',
            'status': 'directly_reusable',
            'path': str(DEFAULT_BUNDLE_ARTIFACT_ROOT),
            'note': 'AL packages point to the same corrected 20260510 shared bundle lineage as the live exAL packages.',
        },
        {
            'component': 'historical AL family ids',
            'status': 'directly_reusable',
            'path': 'config/multimodel_v8_all9_featurecov.template.yaml',
            'note': 'The clean implementation uses existing dqlm_* AL families instead of inventing new family ids or ad-hoc patches.',
        },
        {
            'component': 'shared-spec package templates and batches',
            'status': 'requires_adaptation',
            'path': 'config/he2_bayesian_publication_relaunch_*_sharedspec_20260517.template.yaml',
            'note': 'Three new AL shared-spec templates and batches are required so the current exAL launch contract can be mirrored cleanly.',
        },
        {
            'component': 'likelihood-mode enforcement',
            'status': 'requires_adaptation',
            'path': 'config/he2_relaunch_batches/dqlm_*_all_cutoffs_sharedspec_20260517.yaml',
            'note': 'Batch patches explicitly pin likelihood_mode=al; univariate AL also pins implementation_mode=legacy_bridge.',
        },
        {
            'component': 'gamma=0 / sigma-only fit behavior',
            'status': 'not_reimplemented',
            'path': 'DISC_Optimal_Synth_Ranges_W_transfer_forecast.r; R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R',
            'note': 'Operative AL fit behavior already exists in code and is validated rather than rewritten.',
        },
    ]


def _package_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family, info in FAMILIES.items():
        template = _load_yaml(info['template'])
        batch = _load_yaml(info['batch'])
        rows.append({
            'family': family,
            'manuscript_label': info['manuscript_label'],
            'template': str(info['template']),
            'batch': str(info['batch']),
            'validator_outdir': str(info['validator_outdir']),
            'artifact_root': str(info['artifact_root']),
            'selection_families': '|'.join(template['campaign']['families']),
            'batch_selection_families': '|'.join(batch['selection']['families']),
            'resource_fit_parallel_workers': batch['resources']['fit_parallel_workers'],
            'resource_mc_cores': batch['resources']['mc_cores'],
            'bundle_artifact_root': template['bundles']['artifact_root'],
            'bundle_run_id': template['bundles']['bundle_run_id'],
            'data_start': template['bundles']['data_start'],
        })
    return rows


def _readiness_summary(package_rows: list[dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, Any] = {}
    all_validated = True
    for row in package_rows:
        summary_json = Path(row['validator_outdir']) / 'prelaunch_validation_summary.json'
        validated = summary_json.exists()
        all_validated &= validated
        families[row['family']] = {
            'manuscript_label': row['manuscript_label'],
            'template_exists': Path(row['template']).exists(),
            'batch_exists': Path(row['batch']).exists(),
            'validator_summary_exists': validated,
            'validator_summary_json': str(summary_json),
            'ready_for_launch_after_validation': validated,
        }
    return {
        'status': 'validated' if all_validated else 'packaged_not_validated',
        'families': families,
        'shared_bundle_artifact_root': str(DEFAULT_BUNDLE_ARTIFACT_ROOT),
        'shared_bundle_run_id': DEFAULT_BUNDLE_RUN_ID,
        'shared_data_start': DEFAULT_DATA_START,
        'runbook': str(RUNBOOK),
    }


def build_payload(out_root: Path = OUT_ROOT) -> dict[str, Any]:
    scope_rows = _scope_rows(out_root)
    bundle_rows = _bundle_rows(scope_rows)
    spec_rows = _spec_rows(scope_rows)
    reuse_rows = _reuse_rows()
    package_rows = _package_rows()
    readiness = _readiness_summary(package_rows)
    return {
        'scope_rows': scope_rows,
        'bundle_rows': bundle_rows,
        'spec_rows': spec_rows,
        'reuse_rows': reuse_rows,
        'package_rows': package_rows,
        'readiness_summary': readiness,
    }


def render_md(payload: dict[str, Any]) -> str:
    lines = [
        '# HE2 AL Shared Relaunch Packages',
        '',
        'Date: 2026-05-17',
        '',
        '## Findings',
        '',
        '- historical AL is a first-class likelihood mode, not a post-hoc naming convention',
        '- the user recollection is substantially correct at the operative fit layer:',
        '  - `gamma = 0` under AL',
        '  - latent `s_t` contributions are forced to `0` under AL',
        '  - the gamma/scale delta approximation reduces to sigma-only optimization under AL',
        '- the clean modern implementation is **not** a new ad-hoc gamma clamp; it is the existing `dqlm_*` AL family set routed through the approved manifest-driven relaunch workflow',
        '- the new packages intentionally reuse the corrected shared bundle lineage and the current exAL shared-spec discount bundle for relaunch parity',
        '- that last point is a deliberate relaunch choice and is **not** identical to the historical per-cutoff AL publication-winning epsilon/discount selections',
        '',
        '## Historical Contract Evidence',
        '',
    ]
    for row in CODE_EVIDENCE:
        lines.append(f"- `{row['area']}`: `{row['path']}`")
        lines.append(f"  - {row['summary']}")
    lines.extend([
        '',
        '## Package Scope',
        '',
        '| Family | Label | Model class | Reference exAL family | Template | Batch |',
        '|---|---|---|---|---|---|',
    ])
    for row in payload['package_rows']:
        lines.append(
            f"| `{row['family']}` | `{row['manuscript_label']}` | `{FAMILIES[row['family']]['model_class']}` | `{FAMILIES[row['family']]['reference_exal_family']}` | `{row['template']}` | `{row['batch']}` |"
        )
    lines.extend([
        '',
        '## Reuse vs Adaptation',
        '',
    ])
    for row in payload['reuse_rows']:
        lines.append(f"- `{row['component']}`: `{row['status']}`")
        lines.append(f"  - path: `{row['path']}`")
        lines.append(f"  - note: {row['note']}")
    lines.extend([
        '',
        '## Readiness',
        '',
        f"- status: `{payload['readiness_summary']['status']}`",
        f"- shared bundle artifact root: `{payload['readiness_summary']['shared_bundle_artifact_root']}`",
        f"- shared bundle run id: `{payload['readiness_summary']['shared_bundle_run_id']}`",
        f"- shared data start: `{payload['readiness_summary']['shared_data_start']}`",
        f"- runbook: `{payload['readiness_summary']['runbook']}`",
        '',
        'Launch boundary for this report:',
        '- package creation and no-launch validation only',
        '- do not disturb the currently running exAL keep/drop/univar relaunches',
        '- do not launch the AL packages until the final validator summaries are present and green',
    ])
    return '\n'.join(lines) + '\n'


def main() -> None:
    payload = build_payload()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    _write_csv(OUT_ROOT / 'al_scope_matrix.csv', payload['scope_rows'])
    _write_csv(OUT_ROOT / 'bundle_parity_table.csv', payload['bundle_rows'])
    _write_csv(OUT_ROOT / 'spec_parity_table.csv', payload['spec_rows'])
    _write_csv(OUT_ROOT / 'reuse_adaptation_mapping_table.csv', payload['reuse_rows'])
    _write_csv(OUT_ROOT / 'package_inventory.csv', payload['package_rows'])
    _write_csv(OUT_ROOT / 'al_contract_evidence.csv', CODE_EVIDENCE)
    _write_json(OUT_ROOT / 'readiness_summary.json', payload['readiness_summary'])
    (OUT_ROOT / 'HE2_AL_SHARED_RELAUNCH_PACKAGES_20260517.md').write_text(render_md(payload), encoding='utf-8')


if __name__ == '__main__':
    main()
