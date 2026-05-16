#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from he2_publication_relaunch_lib import (
    DEFAULT_BUNDLE_ARTIFACT_ROOT,
    DEFAULT_BUNDLE_RUN_ID,
    DEFAULT_DATA_START,
    EXPECTED_CUTOFF_TO_DATE,
    canonical_shared_paths,
    load_yaml,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / 'reports' / 'he2_exdqlm_multivar_keep_shared_relaunch_plan_20260516'
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516.template.yaml'
BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516.yaml'
RUNBOOK = ROOT / 'repro' / 'run' / 'HE2_EXDQLM_MULTIVAR_KEEP_SHARED_RELAUNCH_PLAN_20260516.md'
EXACT_DISCOUNT_CSV = ROOT / 'reports' / 'quantile_discount_probe_analysis' / 'exalm_t1_discount_grid_exact_vs_he2.csv'
CF1_BEST_CSV = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/final_featurecov_cf1_eps_analysis/overall_best_epsilon_by_model_type.csv')
CF1_BY_CUTOFF_CSV = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/final_featurecov_cf1_eps_analysis/best_by_cutoff_long.csv')
DISCOUNT_TEMPLATE = ROOT / 'config' / 'multimodel_v8_exalm_t1_discount_grid_exact_20260424.template.yaml'
BLOCKED_VALIDATION_JSON = ROOT / 'reports' / 'he2_exdqlm_multivar_keep_rerun_contract_20260516' / 'validation_status_20260516.json'
FAMILY = 'exdqlm_multivar_keep'
SHARED_DISCOUNT_SET = 'set08'
SHARED_EPSILON_LABEL = 'eps360cf1'
SHARED_EPSILON = 360.0
SHARED_C_FACTOR = 1.0

Q50_STABILIZATION = {
    'freeze_target': 'states',
    'terminal_sampling_guard.mode': 'fail_fast',
    'terminal_sampling_guard.min_guard_count': 1,
    'terminal_sampling_guard.max_guard_lag_iters': 0,
    'terminal_sampling_guard.require_frozen': True,
    'median_state_hold_after_guard_iters': 0,
    'median_state_blend_alpha': 0.5,
    'median_cov_blend_alpha': 0.5,
    'median_max_abs_gamma_step': 0.15,
    'median_max_abs_log_sigma_step': 0.25,
}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f'No rows to write: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _load_discount_profiles() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = yaml.safe_load(DISCOUNT_TEMPLATE.read_text(encoding='utf-8')) or {}
    profiles = payload.get('discount_profiles') or []
    by_name = {item['name']: item for item in profiles}
    ranking_df = pd.read_csv(EXACT_DISCOUNT_CSV)
    agg = (
        ranking_df.groupby('discount_set')
        .agg(
            mean_probe_crps=('probe_crps', 'mean'),
            mean_delta=('delta_vs_baseline', 'mean'),
            median_delta=('delta_vs_baseline', 'median'),
            wins=('is_better_than_baseline', 'sum'),
        )
        .reset_index()
        .sort_values(['mean_delta', 'mean_probe_crps', 'discount_set'])
    )
    ranking_rows: list[dict[str, Any]] = []
    for _, row in agg.iterrows():
        state = (by_name[row['discount_set']]['state_evolution']).copy()
        ranking_rows.append({
            'discount_set': row['discount_set'],
            'mean_probe_crps': float(row['mean_probe_crps']),
            'mean_delta': float(row['mean_delta']),
            'median_delta': float(row['median_delta']),
            'wins': int(row['wins']),
            **state,
        })
    return by_name[SHARED_DISCOUNT_SET], ranking_rows


def _load_cf1_summary() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    overall = pd.read_csv(CF1_BEST_CSV)
    target = overall.loc[overall['model_variant'] == FAMILY].iloc[0].to_dict()
    by_cutoff = pd.read_csv(CF1_BY_CUTOFF_CSV)
    target_rows = by_cutoff.loc[by_cutoff['model_variant'] == FAMILY, ['cutoff', 'best_epsilon_label', 'best_epsilon_value', 'best_c_factor', 'forecast_window_crps']]
    return target, target_rows.to_dict(orient='records')


def _bundle_rows() -> list[dict[str, Any]]:
    rows = []
    for cutoff, cutoff_date in EXPECTED_CUTOFF_TO_DATE.items():
        shared = canonical_shared_paths(DEFAULT_BUNDLE_ARTIFACT_ROOT, cutoff, DEFAULT_BUNDLE_RUN_ID)
        rows.append({
            'cutoff': cutoff,
            'retros_window': f"{DEFAULT_DATA_START} -> {cutoff_date}",
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


def build_payload() -> dict[str, Any]:
    shared_discount_profile, discount_ranking_rows = _load_discount_profiles()
    shared_state = (shared_discount_profile['state_evolution']).copy()
    cf1_overall, cf1_cutoff_rows = _load_cf1_summary()
    blocked_validation = json.loads(BLOCKED_VALIDATION_JSON.read_text(encoding='utf-8'))
    bundle_rows = _bundle_rows()

    shared_spec_rows = []
    for cutoff in EXPECTED_CUTOFF_TO_DATE:
        shared_spec_rows.append({
            'cutoff': cutoff,
            'shared_discount_set': SHARED_DISCOUNT_SET,
            'shared_epsilon_label': SHARED_EPSILON_LABEL,
            'shared_epsilon': SHARED_EPSILON,
            'shared_c_factor': SHARED_C_FACTOR,
            **shared_state,
            'q50_freeze_target': Q50_STABILIZATION['freeze_target'],
            'q50_guard_mode': Q50_STABILIZATION['terminal_sampling_guard.mode'],
            'q50_hold_after_guard': Q50_STABILIZATION['median_state_hold_after_guard_iters'],
            'q50_state_blend_alpha': Q50_STABILIZATION['median_state_blend_alpha'],
            'q50_cov_blend_alpha': Q50_STABILIZATION['median_cov_blend_alpha'],
            'q50_gamma_step_cap': Q50_STABILIZATION['median_max_abs_gamma_step'],
            'q50_log_sigma_step_cap': Q50_STABILIZATION['median_max_abs_log_sigma_step'],
        })

    stage_schedule = [
        {
            'stage': 'Stage 0',
            'goal': 'Freeze the shared relaunch contract before any queue launch.',
            'deliverables': 'shared spec report, no-launch template/batch, validator runbook',
            'gate': 'builder and focused unit tests pass; bundle contract unchanged',
        },
        {
            'stage': 'Stage 1',
            'goal': 'Run no-launch prelaunch validation on representative q50/q65 smokes under the shared spec.',
            'deliverables': 'prelaunch_validation_summary.json and smoke-run evidence logs',
            'gate': '20210123 q50, 20211221 q50, and 20221225 q50/q65 all clear the validator contract',
        },
        {
            'stage': 'Stage 2',
            'goal': 'Run a staged relaunch: first canary rows, then all five cutoffs.',
            'deliverables': 'five row manifests, fit/post/validate/report status, CRPS compare bundle refresh',
            'gate': 'all five rows pass report and compare status under the shared spec',
        },
        {
            'stage': 'Stage 3',
            'goal': 'Refresh the revised article figures/tables from the new relaunch outputs.',
            'deliverables': 'five-cutoff validation bundle, representative selected-model bundle, cutoff setup/support, forecast-context and synthesis families',
            'gate': 'article review manifests refreshed and committed in the revised-doc repo',
        },
    ]

    article_assets = [
        {'family': 'five_cutoff_crps_validation_sources', 'role': 'Table 1 CRPS source freeze', 'refresh_after_stage': 'Stage 2'},
        {'family': 'representative_selected_model_2022_12_25', 'role': 'Section 5 representative outputs and posterior tables', 'refresh_after_stage': 'Stage 2'},
        {'family': 'five_cutoff_setup_support', 'role': 'input/setup/support bundle by cutoff', 'refresh_after_stage': 'Stage 3'},
        {'family': 'forecast_context_by_cutoff', 'role': 'forecast window context figures for all cutoffs', 'refresh_after_stage': 'Stage 3'},
        {'family': 'multivariate_synthesis_by_cutoff', 'role': 'main-model synthesis family for all cutoffs', 'refresh_after_stage': 'Stage 3'},
        {'family': 'reference_synthesis_by_cutoff', 'role': 'reference synthesis family for all cutoffs', 'refresh_after_stage': 'Stage 3'},
        {'family': 'historical_support_from_current_models', 'role': 'historical support figures; refresh only if corrected retained-artifact contract is satisfied', 'refresh_after_stage': 'Stage 3 (gated)'},
    ]

    summary = {
        'family': FAMILY,
        'shared_discount_set': SHARED_DISCOUNT_SET,
        'shared_epsilon_label': SHARED_EPSILON_LABEL,
        'shared_epsilon': SHARED_EPSILON,
        'shared_c_factor': SHARED_C_FACTOR,
        'shared_state_evolution': shared_state,
        'q50_stabilization': Q50_STABILIZATION,
        'paths': {
            'template': str(TEMPLATE),
            'batch': str(BATCH),
            'runbook': str(RUNBOOK),
        },
        'blocked_publication_spec_validation': blocked_validation,
        'cf1_overall_family_best': cf1_overall,
    }
    return {
        'summary': summary,
        'shared_spec_rows': shared_spec_rows,
        'discount_ranking_rows': discount_ranking_rows,
        'cf1_cutoff_rows': cf1_cutoff_rows,
        'bundle_rows': bundle_rows,
        'stage_schedule': stage_schedule,
        'article_assets': article_assets,
    }


def _render_md(payload: dict[str, Any]) -> str:
    s = payload['summary']
    lines: list[str] = []
    lines.append('# HE2 exdqlm_multivar_keep Shared Relaunch Plan')
    lines.append('')
    lines.append('Date: 2026-05-16')
    lines.append('')
    lines.append('## Decision')
    lines.append('')
    lines.append('- family: `exdqlm_multivar_keep`')
    lines.append('- launch posture: `PREPARE_ONLY`')
    lines.append(f"- shared forecast-covariance spec: `epsilon={s['shared_epsilon']}`, `c_factor={s['shared_c_factor']}`")
    lines.append(f"- shared discount set: `{s['shared_discount_set']}`")
    lines.append('- shared q50 stabilization layer: enabled from the successful 2026-05-15 recovery path')
    lines.append('')
    lines.append('## Why this shared spec')
    lines.append('')
    lines.append(f"- family-wide cf1 epsilon sweep winner for `exdqlm_multivar_keep`: `{s['cf1_overall_family_best']['epsilon_label']}` with mean CRPS `{s['cf1_overall_family_best']['mean_crps_across_cutoffs']:.6f}` across 5 cutoffs")
    lines.append(f"- family-wide exact-input discount-grid winner by mean delta: `{s['shared_discount_set']}`")
    lines.append(f"- the earlier publication-spec-only rerun contract is blocked by q50 validation at `20210123`, so the shared rerun must carry an explicit median stabilization layer")
    lines.append('')
    lines.append('## Shared science spec')
    lines.append('')
    lines.append('| Parameter | Value | Evidence |')
    lines.append('|---|---|---|')
    lines.append(f"| `epsilon` | `{s['shared_epsilon']}` | cf1 family-wide best epsilon summary |")
    lines.append(f"| `c_factor` | `{s['shared_c_factor']}` | cf1 sweep held at `1.0` for the tuned current multivariate families |")
    for key, value in s['shared_state_evolution'].items():
        lines.append(f"| `{key}` | `{value}` | exact-input discount-grid `{s['shared_discount_set']}` |")
    lines.append('')
    lines.append('## Shared execution stabilization layer')
    lines.append('')
    for key, value in s['q50_stabilization'].items():
        lines.append(f'- `{key}`: `{value}`')
    lines.append('')
    lines.append('## Discount-set ranking across all 5 cutoffs')
    lines.append('')
    lines.append('| Set | Mean Probe CRPS | Mean Delta vs HE | Median Delta | Wins | df_s1 | df_discrep | lambda | df_covs |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    for row in payload['discount_ranking_rows']:
        lines.append(
            f"| `{row['discount_set']}` | `{row['mean_probe_crps']:.6f}` | `{row['mean_delta']:.6f}` | `{row['median_delta']:.6f}` | `{row['wins']}` | `{row['df_s1']}` | `{row['df_discrep']}` | `{row['lambda']}` | `{row['df_covs']}` |"
        )
    lines.append('')
    lines.append('## Shared-input bundle contract')
    lines.append('')
    lines.append('| Cutoff | Retros Window | Bundle Root | PPT | SOIL | PCA(alias=GDPC1) |')
    lines.append('|---|---|---|---|---|---|')
    for row in payload['bundle_rows']:
        lines.append(f"| `{row['cutoff']}` | `{row['retros_window']}` | `{row['bundle_root']}` | `{row['cov_ppt_path']}` | `{row['cov_soil_path']}` | `{row['cov_pca_path']}` |")
    lines.append('')
    lines.append('## Staged relaunch schedule')
    lines.append('')
    lines.append('| Stage | Goal | Deliverables | Gate |')
    lines.append('|---|---|---|---|')
    for stage in payload['stage_schedule']:
        lines.append(f"| `{stage['stage']}` | {stage['goal']} | {stage['deliverables']} | {stage['gate']} |")
    lines.append('')
    lines.append('## Article refresh schedule')
    lines.append('')
    lines.append('| Asset family | Role | Refresh timing |')
    lines.append('|---|---|---|')
    for row in payload['article_assets']:
        lines.append(f"| `{row['family']}` | {row['role']} | `{row['refresh_after_stage']}` |")
    lines.append('')
    lines.append('## No-launch output paths')
    lines.append('')
    lines.append(f"- template: `{s['paths']['template']}`")
    lines.append(f"- batch: `{s['paths']['batch']}`")
    lines.append(f"- runbook: `{s['paths']['runbook']}`")
    lines.append('')
    return '\n'.join(lines) + '\n'


def write_outputs(out_root: Path = OUT_ROOT) -> dict[str, Any]:
    payload = build_payload()
    out_root.mkdir(parents=True, exist_ok=True)
    _write_csv(out_root / 'shared_relaunch_spec.csv', payload['shared_spec_rows'])
    _write_csv(out_root / 'discount_set_ranking.csv', payload['discount_ranking_rows'])
    _write_csv(out_root / 'cf1_cutoff_winners_reference.csv', payload['cf1_cutoff_rows'])
    _write_csv(out_root / 'canonical_input_bundle_contract.csv', payload['bundle_rows'])
    (out_root / 'summary.json').write_text(json.dumps(payload['summary'], indent=2) + '\n', encoding='utf-8')
    (out_root / 'stage_schedule.json').write_text(json.dumps(payload['stage_schedule'], indent=2) + '\n', encoding='utf-8')
    (out_root / 'article_refresh_schedule.json').write_text(json.dumps(payload['article_assets'], indent=2) + '\n', encoding='utf-8')
    md = _render_md(payload)
    (out_root / 'HE2_EXDQLM_MULTIVAR_KEEP_SHARED_RELAUNCH_PLAN_20260516.md').write_text(md, encoding='utf-8')
    (out_root / 'README.md').write_text(md, encoding='utf-8')
    return payload


def main() -> int:
    payload = write_outputs()
    print(json.dumps(payload['summary'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
