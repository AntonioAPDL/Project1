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
OUT_ROOT = ROOT / 'reports' / 'he2_exdqlm_univar_shared_relaunch_plan_20260516'
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml'
BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml'
RUNBOOK = ROOT / 'repro' / 'run' / 'HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md'
HIST_AUDIT = ROOT / 'reports' / 'he2_publication_manifest' / 'historical_support_audit_20260507' / 'historical_support_audit.csv'
FAMILY = 'exdqlm_univar'
MANUSCRIPT_LABEL = 'exAL-U-T1'
SHARED_DISCOUNT_SET = 'set10_manual_20260516'
SHARED_SELECTION_BASIS = 'manual_projection_from_multivar_sharedspec_20260516'
SHARED_STATE = {
    'df_t': 0.99999999,
    'df_s1': 0.99999,
    'df_s2': 0.99999,
    'df_s67': 0.99999,
    'lambda': 0.97,
    'df_trans': 0.9999999,
    'df_covs': 0.9999999,
}
LEGACY_BRIDGE_Q50_MAPPING = {
    'init_controls': 'not_operative_under_legacy_bridge',
    'freeze_target': 'not_operative_under_legacy_bridge',
    'objective_guard.fail_fast': 'not_operative_under_legacy_bridge',
    'terminal_sampling_guard': 'not_supported_by_univar_runner',
    'median_blend_and_step_caps': 'not_applicable_to_univar_runner',
    'operative_controls': 'shared_state_projection_and_validator_smoke_iter_caps_only',
}
VALIDATION_OUTDIR = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_exact_final_batch_20260516')


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f'No rows to write: {path}')
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


def _historical_audit_map() -> dict[str, dict[str, str]]:
    rows = _read_csv(HIST_AUDIT)
    return {row['cutoff']: row for row in rows if row['family'] == FAMILY}


def _bundle_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cutoff, cutoff_date in EXPECTED_CUTOFF_TO_DATE.items():
        shared = canonical_shared_paths(DEFAULT_BUNDLE_ARTIFACT_ROOT, cutoff, DEFAULT_BUNDLE_RUN_ID)
        rows.append({
            'cutoff': cutoff,
            'retros_window': f'{DEFAULT_DATA_START} -> {cutoff_date}',
            'bundle_root': str(shared['bundle_root']),
            'bundle_meta': str(shared['bundle_meta']),
            'retros_path': str(shared['retros']),
            'parameters_path': str(shared['parameters']),
            'nws_forecast_path': str(shared['nws_forecast']),
            'glofas_forecast_path': str(shared['glofas_forecast']),
            'cov_ppt_path': str(shared['cov_ppt']),
            'cov_soil_path': str(shared['cov_soil']),
            'cov_pca_path': str(shared['cov_pca']),
            'support_manifest': str(shared['support_manifest']),
        })
    return rows


def _scope_rows(out_root: Path) -> list[dict[str, Any]]:
    hist = _historical_audit_map()
    freeze_root = out_root / 'source_config_freeze'
    rows: list[dict[str, Any]] = []
    for manifest_row in load_publication_manifest_rows():
        if manifest_row['family'] != FAMILY:
            continue
        cutoff = manifest_row['cutoff']
        run_root = Path(manifest_row['run_root'])
        resolved_config_path = Path(manifest_row['resolved_config_path'])
        cfg = _load_yaml(resolved_config_path)
        source_map = _parse_key_value_text(run_root / 'inputs' / 'shared' / 'source_map.txt')
        data_start = _parse_key_value_text(run_root / 'inputs' / 'shared' / 'data_start_filter_summary.txt')
        climate = _parse_key_value_text(run_root / 'inputs' / 'shared' / 'deterministic_climate' / 'deterministic_climate_summary.txt')
        frozen_name = f"{cutoff}_{MANUSCRIPT_LABEL.replace('-', '_')}_{FAMILY}.resolved_config.yaml"
        _freeze_config(resolved_config_path, freeze_root / frozen_name)
        state = cfg['models']['exdqlm_univar']['state_evolution']
        gamsig = cfg['fit']['exdqlm_univar']['gamma_sigma']
        rows.append({
            'cutoff': cutoff,
            'family': manifest_row['family'],
            'manuscript_label': manifest_row['manuscript_label'],
            'model_class': 'quantile_univariate',
            'current_run_id': manifest_row['run_id'],
            'current_run_root': manifest_row['run_root'],
            'current_campaign_lineage': manifest_row['campaign_lineage'],
            'current_resolved_config_path': manifest_row['resolved_config_path'],
            'frozen_resolved_config_path': str(freeze_root / frozen_name),
            'current_bundle_root': source_map.get('bundle_root', ''),
            'current_data_start': data_start.get('data_start', ''),
            'current_common_date_min': data_start.get('common_date_min', ''),
            'current_common_date_max': data_start.get('common_date_max', ''),
            'current_full_history_from_1987': hist[cutoff]['full_history_from_1987'],
            'current_ppt_source': climate.get('precip_source', ''),
            'current_soil_source': climate.get('soil_source', ''),
            'current_pca_alias': 'PCA(alias=GDPC1)' if climate.get('pca_path') else 'unknown',
            'current_df_t': state['df_t'],
            'current_df_s1': state['df_s1'],
            'current_df_s2': state['df_s2'],
            'current_df_s67': state['df_s67'],
            'current_lambda': state['lambda'],
            'current_df_trans': state['df_trans'],
            'current_df_covs': state['df_covs'],
            'current_df_discrep_present': 'df_discrep' in state,
            'current_gamma_sigma_freeze_target': gamsig.get('freeze_target', ''),
            'current_gamma_sigma_objective_guard_fail_fast': gamsig.get('objective_guard', {}).get('fail_fast', False),
            'current_forecast_cov_present': bool(cfg['models']['exdqlm_univar'].get('prior', {}).get('forecast_cov')),
            'proposed_bundle_root': str(canonical_shared_paths(DEFAULT_BUNDLE_ARTIFACT_ROOT, cutoff, DEFAULT_BUNDLE_RUN_ID)['bundle_root']),
            'risk_note': 'shared discount projection changes df_s1/df_s2/df_s67/df_covs; forecast_cov remains absent by design',
        })
    rows.sort(key=lambda row: row['cutoff'])
    return rows


def build_payload(out_root: Path = OUT_ROOT) -> dict[str, Any]:
    template = _load_yaml(TEMPLATE)
    batch = _load_yaml(BATCH)
    scope_rows = _scope_rows(out_root)
    bundle_rows = _bundle_rows()

    shared_spec_rows = []
    state_projection_rows = []
    for row in scope_rows:
        cutoff = row['cutoff']
        shared_spec_rows.append({
            'cutoff': cutoff,
            'shared_discount_set': SHARED_DISCOUNT_SET,
            'shared_selection_basis': SHARED_SELECTION_BASIS,
            'forecast_cov_contract': 'not_applied_by_design',
            'df_discrep_contract': 'absent_by_design',
            **SHARED_STATE,
            'legacy_bridge_q50_init_controls': LEGACY_BRIDGE_Q50_MAPPING['init_controls'],
            'legacy_bridge_q50_freeze_target': LEGACY_BRIDGE_Q50_MAPPING['freeze_target'],
            'legacy_bridge_q50_objective_guard_fail_fast': LEGACY_BRIDGE_Q50_MAPPING['objective_guard.fail_fast'],
            'legacy_bridge_q50_terminal_sampling_guard': LEGACY_BRIDGE_Q50_MAPPING['terminal_sampling_guard'],
            'legacy_bridge_q50_median_blend_and_step_caps': LEGACY_BRIDGE_Q50_MAPPING['median_blend_and_step_caps'],
        })
        state_projection_rows.append({
            'cutoff': cutoff,
            'current_df_t': row['current_df_t'],
            'target_df_t': SHARED_STATE['df_t'],
            'current_df_s1': row['current_df_s1'],
            'target_df_s1': SHARED_STATE['df_s1'],
            'current_df_s2': row['current_df_s2'],
            'target_df_s2': SHARED_STATE['df_s2'],
            'current_df_s67': row['current_df_s67'],
            'target_df_s67': SHARED_STATE['df_s67'],
            'current_lambda': row['current_lambda'],
            'target_lambda': SHARED_STATE['lambda'],
            'current_df_trans': row['current_df_trans'],
            'target_df_trans': SHARED_STATE['df_trans'],
            'current_df_covs': row['current_df_covs'],
            'target_df_covs': SHARED_STATE['df_covs'],
            'current_df_discrep_present': row['current_df_discrep_present'],
            'target_df_discrep_present': False,
        })

    validation_schedule = {
        'builder': {
            'config': str(TEMPLATE),
            'batch_file': str(BATCH),
            'profile': 'disk_guarded_serial',
        },
        'validator': {
            'config': str(TEMPLATE),
            'batch_file': str(BATCH),
            'outdir': str(VALIDATION_OUTDIR),
            'fit_parallel_workers': 7,
            'mc_cores': 7,
        },
        'hard_case_fit_smokes': [
            {'cutoff': '20210123', 'family': FAMILY, 'quantiles': [0.50]},
        ],
        'hard_case_full_pipeline_smokes': [
            {'cutoff': '20210123', 'family': FAMILY, 'quantiles': [0.35, 0.50, 0.65]},
        ],
    }

    stage_schedule = [
        {
            'stage': 'Stage 0',
            'goal': 'Freeze the no-launch univariate shared-spec package under the approved publication relaunch workflow.',
            'deliverables': 'template, batch, runbook, report bundle, source-config freeze',
            'gate': 'package files exist and focused unit tests pass',
        },
        {
            'stage': 'Stage 1',
            'goal': 'Run builder dry-run and inspect the generated univariate configs for exact bundle/spec projection.',
            'deliverables': 'generated configs, matrix plan, config inspection notes',
            'gate': '5 exdqlm_univar rows generated with canonical 20260510 shared bundles and shared state projection',
        },
        {
            'stage': 'Stage 2',
            'goal': 'Run the no-launch validator on the final exact batch with targeted q50 fit and full-pipeline smokes.',
            'deliverables': 'prelaunch_validation_summary.json, smoke logs, validation status report',
            'gate': '20210123 q50 fit smoke passes and representative 20210123 q35/q50/q65 full-pipeline smoke clears post/validate/report without queue launch',
        },
        {
            'stage': 'Stage 3',
            'goal': 'Review launch readiness for later parallel execution alongside the live multivariate keep/drop campaigns.',
            'deliverables': 'explicit ready/not-ready conclusion and future launch schedule',
            'gate': 'all no-launch validation gates are green',
        },
    ]

    workflow_refresh = [
        {
            'artifact_family': 'five_cutoff_crps_validation_sources',
            'role': 'refresh the exdqlm_univar row lineage in the five-cutoff CRPS validation source freeze',
            'refresh_after_stage': 'Stage 3 (after real relaunch completes)',
        },
        {
            'artifact_family': 'he2_publication_compare_bundle_refresh',
            'role': 'refresh compare bundles so the exdqlm_univar rows move from legacy lineage to the corrected shared-spec lineage',
            'refresh_after_stage': 'Stage 3 (after real relaunch completes)',
        },
        {
            'artifact_family': 'article_crps_table_provenance',
            'role': 'document the updated exdqlm_univar provenance if revised-article tables or supplements surface those rows',
            'refresh_after_stage': 'Stage 3 (only if article outputs consume the refreshed univariate rows)',
        },
    ]

    summary = {
        'family': FAMILY,
        'manuscript_label': MANUSCRIPT_LABEL,
        'shared_discount_set': SHARED_DISCOUNT_SET,
        'shared_selection_basis': SHARED_SELECTION_BASIS,
        'shared_state_evolution': SHARED_STATE,
        'forecast_cov_contract': 'not_applied_by_design',
        'df_discrep_contract': 'absent_by_design',
        'q50_stabilization_contract': LEGACY_BRIDGE_Q50_MAPPING,
        'validation_outdir': str(VALIDATION_OUTDIR),
        'paths': {
            'template': str(TEMPLATE),
            'batch': str(BATCH),
            'runbook': str(RUNBOOK),
        },
        'runtime_contract': {
            'fit_parallel_workers': batch['resources']['fit_parallel_workers'],
            'mc_cores': batch['resources']['mc_cores'],
            'thread_caps': batch['overrides']['row_config_patches'][0]['config_patch']['run']['threads'],
            'queue_ordinary_max_concurrent': template['queue']['ordinary_max_concurrent'],
            'queue_heavy_cutoff_max_concurrent': template['queue']['heavy_cutoff_max_concurrent'],
        },
        'readiness': {
            'status': 'READY_FOR_NO_LAUNCH_VALIDATION',
            'ready_for_no_launch_packaging': True,
            'ready_for_launch_after_validation': False,
            'why_not_launch_yet': [
                'exact-final-batch builder and validator have not been run yet',
                'hard-case univariate q50 smokes must pass on the final shared-spec package before any queue action',
            ],
        },
    }

    return {
        'summary': summary,
        'scope_rows': scope_rows,
        'shared_spec_rows': shared_spec_rows,
        'bundle_rows': bundle_rows,
        'state_projection_rows': state_projection_rows,
        'validation_schedule': validation_schedule,
        'stage_schedule': stage_schedule,
        'workflow_refresh': workflow_refresh,
    }


def _render_md(payload: dict[str, Any]) -> str:
    s = payload['summary']
    lines: list[str] = []
    lines.append('# HE2 exdqlm_univar Shared Relaunch Plan')
    lines.append('')
    lines.append('Date: 2026-05-16')
    lines.append('')
    lines.append('## Decision')
    lines.append('')
    lines.append('- family: `exdqlm_univar`')
    lines.append('- launch posture: `PREPARE_ONLY`')
    lines.append(f"- shared discount set: `{s['shared_discount_set']}`")
    lines.append(f"- selection basis: `{s['shared_selection_basis']}`")
    lines.append('- forecast-covariance knobs (`epsilon`, `c_factor`) remain absent by design for univariate EXDQLM')
    lines.append('- `df_discrep` remains absent because it is not part of the univariate state block')
    lines.append('- q50 gamma/sigma stabilization knobs from the multivariate relaunch are not operative under the published `legacy_bridge` univariate runner')
    lines.append('')
    lines.append('## Shared science contract')
    lines.append('')
    lines.append('| Parameter | Value | Applicability |')
    lines.append('|---|---|---|')
    for key, value in s['shared_state_evolution'].items():
        lines.append(f"| `{key}` | `{value}` | shared projected state-evolution knob |")
    lines.append('| `epsilon` | `not applied` | univariate forecast-cov block remains absent by design |')
    lines.append('| `c_factor` | `not applied` | univariate forecast-cov block remains absent by design |')
    lines.append('| `df_discrep` | `absent` | not part of `models.exdqlm_univar.state_evolution` |')
    lines.append('')
    lines.append('## q50 gamma/sigma mapping under `legacy_bridge`')
    lines.append('')
    lines.append('| Item | Value | Notes |')
    lines.append('|---|---|---|')
    lines.append(f"| `init.*` | `{LEGACY_BRIDGE_Q50_MAPPING['init_controls']}` | `run_OptimalModelSLexAL.R` does not read the univariate init env knobs |")
    lines.append(f"| `freeze_target` | `{LEGACY_BRIDGE_Q50_MAPPING['freeze_target']}` | not read by the published legacy runner |")
    lines.append(f"| `objective_guard.fail_fast` | `{LEGACY_BRIDGE_Q50_MAPPING['objective_guard.fail_fast']}` | not read by the published legacy runner |")
    lines.append(f"| `terminal_sampling_guard` | `{LEGACY_BRIDGE_Q50_MAPPING['terminal_sampling_guard']}` | no univariate terminal-sampling guard path exists in the legacy runner |")
    lines.append(f"| `median_blend_and_step_caps` | `{LEGACY_BRIDGE_Q50_MAPPING['median_blend_and_step_caps']}` | multivariate-only |")
    lines.append(f"| operative controls | `{LEGACY_BRIDGE_Q50_MAPPING['operative_controls']}` | the real no-launch gates are state projection plus validator smoke evidence |")
    lines.append('')
    lines.append('## Current source scope')
    lines.append('')
    lines.append('| Cutoff | Current run id | Current bundle root | Full history today | Current df_s1 | Target df_s1 | Forecast-cov present today |')
    lines.append('|---|---|---|---|---:|---:|---|')
    for row in payload['scope_rows']:
        lines.append(
            f"| `{row['cutoff']}` | `{row['current_run_id']}` | `{row['current_bundle_root']}` | `{row['current_full_history_from_1987']}` | `{row['current_df_s1']}` | `{SHARED_STATE['df_s1']}` | `{row['current_forecast_cov_present']}` |"
        )
    lines.append('')
    lines.append('## Canonical shared-input contract')
    lines.append('')
    lines.append('| Cutoff | Retros window | Bundle root | PPT | SOIL | PCA(alias=GDPC1) |')
    lines.append('|---|---|---|---|---|---|')
    for row in payload['bundle_rows']:
        lines.append(
            f"| `{row['cutoff']}` | `{row['retros_window']}` | `{row['bundle_root']}` | `{row['cov_ppt_path']}` | `{row['cov_soil_path']}` | `{row['cov_pca_path']}` |"
        )
    lines.append('')
    lines.append('## No-launch validation schedule')
    lines.append('')
    lines.append('| Stage | Goal | Deliverables | Gate |')
    lines.append('|---|---|---|---|')
    for stage in payload['stage_schedule']:
        lines.append(f"| `{stage['stage']}` | {stage['goal']} | {stage['deliverables']} | {stage['gate']} |")
    lines.append('')
    lines.append('## Future workflow refresh points')
    lines.append('')
    lines.append('| Artifact family | Role | Refresh timing |')
    lines.append('|---|---|---|')
    for row in payload['workflow_refresh']:
        lines.append(f"| `{row['artifact_family']}` | {row['role']} | `{row['refresh_after_stage']}` |")
    lines.append('')
    lines.append('## No-launch output paths')
    lines.append('')
    lines.append(f"- template: `{s['paths']['template']}`")
    lines.append(f"- batch: `{s['paths']['batch']}`")
    lines.append(f"- runbook: `{s['paths']['runbook']}`")
    lines.append(f"- validator outdir: `{s['validation_outdir']}`")
    lines.append('')
    return '\n'.join(lines) + '\n'


def write_outputs(out_root: Path = OUT_ROOT) -> dict[str, Any]:
    payload = build_payload(out_root=out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    _write_csv(out_root / 'shared_relaunch_spec.csv', payload['shared_spec_rows'])
    _write_csv(out_root / 'current_source_scope.csv', payload['scope_rows'])
    _write_csv(out_root / 'state_projection_comparison.csv', payload['state_projection_rows'])
    _write_csv(out_root / 'canonical_input_bundle_contract.csv', payload['bundle_rows'])
    _write_json(out_root / 'summary.json', payload['summary'])
    _write_json(out_root / 'validation_schedule.json', payload['validation_schedule'])
    _write_json(out_root / 'stage_schedule.json', payload['stage_schedule'])
    _write_json(out_root / 'workflow_refresh_schedule.json', payload['workflow_refresh'])
    md = _render_md(payload)
    (out_root / 'HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md').write_text(md, encoding='utf-8')
    (out_root / 'README.md').write_text(md, encoding='utf-8')
    return payload


def main() -> int:
    payload = write_outputs()
    print(json.dumps(payload['summary'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
