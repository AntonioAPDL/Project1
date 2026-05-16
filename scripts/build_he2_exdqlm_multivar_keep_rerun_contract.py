#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from he2_publication_relaunch_lib import (
    DEFAULT_BUNDLE_ARTIFACT_ROOT,
    DEFAULT_BUNDLE_RUN_ID,
    DEFAULT_CAMPAIGN_SPEC_ID,
    DEFAULT_DATA_START,
    EXPECTED_CUTOFF_TO_DATE,
    canonical_shared_paths,
    load_publication_manifest_rows,
    load_yaml,
    spec_token,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = ROOT / 'reports' / 'he2_exdqlm_multivar_keep_rerun_contract_20260516'
DEFAULT_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_rerun_20260516.template.yaml'
DEFAULT_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_all_cutoffs_rerun_20260516.yaml'
DEFAULT_RUNBOOK = ROOT / 'repro' / 'run' / 'HE2_EXDQLM_MULTIVAR_KEEP_ALL_CUTOFFS_RERUN_RUNBOOK_20260516.md'
FAMILY = 'exdqlm_multivar_keep'

APPROVED_LAUNCHER = {
    'selection_source': 'reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv',
    'builder': 'scripts/build_he2_bayesian_publication_relaunch_configs.py',
    'validator': 'scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py',
    'template': str(DEFAULT_TEMPLATE.relative_to(ROOT)),
    'batch': str(DEFAULT_BATCH.relative_to(ROOT)),
}

QUARANTINED_BUILDERS = [
    'scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py',
    'scripts/build_multimodel_v8_all9_feature_matrix_configs.py',
    'scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py',
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freeze_config(src: Path, dst: Path) -> tuple[str, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst), _sha256(dst)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f'No rows to write: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _build_bundle_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cutoff, cutoff_date in EXPECTED_CUTOFF_TO_DATE.items():
        shared = canonical_shared_paths(DEFAULT_BUNDLE_ARTIFACT_ROOT, cutoff, DEFAULT_BUNDLE_RUN_ID)
        meta = load_yaml(shared['bundle_meta'])
        histfix = meta.get('histfix', {}) if isinstance(meta.get('histfix'), dict) else {}
        rows.append(
            {
                'cutoff': cutoff,
                'bundle_root': str(shared['bundle_root']),
                'bundle_meta': str(shared['bundle_meta']),
                'retros_path': str(shared['retros']),
                'retros_start': DEFAULT_DATA_START,
                'retros_end': cutoff_date,
                'parameters_path': str(shared['parameters']),
                'nws_forecast_path': str(shared['nws_forecast']),
                'glofas_forecast_path': str(shared['glofas_forecast']),
                'cov_ppt_path': str(shared['cov_ppt']),
                'cov_soil_path': str(shared['cov_soil']),
                'gdpc_alias_path': str(shared['cov_pca']),
                'gdpc_alias_start': DEFAULT_DATA_START,
                'gdpc_alias_end': '2023-01-22',
                'support_manifest': str(shared['support_manifest']),
                'usgs_daily_source_path': str(histfix.get('usgs_daily_source_path', '')),
                'forecast_nws_member_source': str(((histfix.get('forecast_member_sources') or {}).get('nws')) or ''),
                'forecast_glofas_member_source': str(((histfix.get('forecast_member_sources') or {}).get('glofas')) or ''),
                'selected_window_splice_retros_path': str(((histfix.get('selected_window_splice') or {}).get('retros_path')) or ''),
                'selected_window_splice_overlap': f"{((histfix.get('selected_window_splice') or {}).get('overlap_start')) or ''} -> {((histfix.get('selected_window_splice') or {}).get('overlap_end')) or ''}",
            }
        )
    return rows


def build_outputs(*, manifest_path: Path | None = None, out_root: Path = DEFAULT_OUT_ROOT) -> dict[str, Any]:
    manifest_rows = [row for row in load_publication_manifest_rows(manifest_path) if row['family'] == FAMILY]
    source_freeze_root = out_root / 'source_config_freeze'
    spec_rows: list[dict[str, Any]] = []

    for row in manifest_rows:
        resolved_config = Path(row['resolved_config_path']).resolve()
        cfg = load_yaml(resolved_config)
        fit_cfg = ((cfg.get('fit') or {}).get('exdqlm_multivar') or {})
        legacy = fit_cfg.get('legacy', {}) if isinstance(fit_cfg, dict) else {}
        forecast_cov = (legacy.get('forecast_cov') or {}) if isinstance(legacy, dict) else {}
        model_cfg = ((cfg.get('models') or {}).get('exdqlm_multivar') or {})
        state = model_cfg.get('state_evolution', {}) if isinstance(model_cfg, dict) else {}
        debug_matrix = cfg.get('debug_v8_matrix', {}) if isinstance(cfg.get('debug_v8_matrix'), dict) else {}
        debug_discount = cfg.get('debug_exalm_t1_discount_grid', {}) if isinstance(cfg.get('debug_exalm_t1_discount_grid'), dict) else {}

        frozen_name = f"{row['cutoff']}_{row['manuscript_label'].replace('-', '_')}_{FAMILY}.resolved_config.yaml"
        frozen_path, resolved_hash = _freeze_config(resolved_config, source_freeze_root / frozen_name)
        effective_epsilon = forecast_cov.get('epsilon')
        source_matrix_epsilon_value = debug_matrix.get('epsilon_value')
        epsilon_mismatch = ''
        if effective_epsilon not in (None, '') and source_matrix_epsilon_value not in (None, '') and float(effective_epsilon) != float(source_matrix_epsilon_value):
            epsilon_mismatch = 'debug_v8_matrix epsilon label/value differ from effective exdqlm fit epsilon; trust fit.exdqlm_multivar.legacy.forecast_cov.epsilon'
        spec_rows.append(
            {
                'cutoff': row['cutoff'],
                'cutoff_display': row['cutoff_display'],
                'manuscript_label': row['manuscript_label'],
                'family': row['family'],
                'run_id': row['run_id'],
                'campaign_lineage': row['campaign_lineage'],
                'publication_crps_display4': row['crps_display4'],
                'selected_spec_token': spec_token(row),
                'resolved_config_path': row['resolved_config_path'],
                'frozen_resolved_config_path': frozen_path,
                'resolved_config_sha256': resolved_hash,
                'fit_parallel_workers_source': debug_matrix.get('fit_parallel_workers', ''),
                'source_matrix_epsilon_label': debug_matrix.get('epsilon_label', ''),
                'source_matrix_epsilon_value': debug_matrix.get('epsilon_value', ''),
                'effective_c_factor_fit': forecast_cov.get('c_factor'),
                'effective_epsilon_fit': effective_epsilon,
                'lam1_fit': legacy.get('lam1'),
                'lam2_fit': legacy.get('lam2'),
                'discount_set': debug_discount.get('discount_set', ''),
                'discount_set_index': debug_discount.get('discount_set_index', ''),
                'discount_source_epsilon_label': debug_discount.get('source_epsilon_label', ''),
                'discount_exact_source_snapshot_root': debug_discount.get('exact_source_snapshot_root', ''),
                'df_t': state.get('df_t'),
                'df_s1': state.get('df_s1'),
                'df_s2': state.get('df_s2'),
                'df_s67': state.get('df_s67'),
                'df_discrep': state.get('df_discrep'),
                'lambda': state.get('lambda'),
                'df_trans': state.get('df_trans'),
                'df_covs': state.get('df_covs'),
                'epsilon_alignment_note': epsilon_mismatch,
            }
        )

    spec_rows.sort(key=lambda item: list(EXPECTED_CUTOFF_TO_DATE).index(item['cutoff']))
    bundle_rows = _build_bundle_rows()
    summary = {
        'family': FAMILY,
        'campaign_spec_id': DEFAULT_CAMPAIGN_SPEC_ID,
        'approved_launcher': APPROVED_LAUNCHER,
        'quarantined_builders': QUARANTINED_BUILDERS,
        'counts': {
            'rows': len(spec_rows),
            'cutoffs': [row['cutoff'] for row in spec_rows],
        },
        'bundle_contract': {
            'bundle_artifact_root': str(DEFAULT_BUNDLE_ARTIFACT_ROOT),
            'bundle_run_id': DEFAULT_BUNDLE_RUN_ID,
            'data_start': DEFAULT_DATA_START,
        },
        'paths': {
            'template': str(DEFAULT_TEMPLATE),
            'batch': str(DEFAULT_BATCH),
            'runbook': str(DEFAULT_RUNBOOK),
        },
    }
    return {
        'spec_rows': spec_rows,
        'bundle_rows': bundle_rows,
        'summary': summary,
    }


def _render_md(payload: dict[str, Any]) -> str:
    spec_rows = payload['spec_rows']
    bundle_rows = payload['bundle_rows']
    summary = payload['summary']
    lines: list[str] = []
    lines.append('# HE2 exdqlm_multivar_keep All-Cutoff Rerun Contract')
    lines.append('')
    lines.append('Date: 2026-05-16')
    lines.append('')
    lines.append('## Decision')
    lines.append('')
    lines.append('- status: `VALIDATE_ONLY`')
    lines.append('- family: `exdqlm_multivar_keep`')
    lines.append('- scope: all 5 HE2 cutoffs')
    lines.append('- launcher: manifest-driven relaunch builder + prelaunch validator only')
    lines.append('- launch posture: do not start the queue until this rerun package is explicitly reapproved')
    lines.append('')
    lines.append('## Approved launcher')
    lines.append('')
    for key, value in summary['approved_launcher'].items():
        lines.append(f'- `{key}`: `{value}`')
    lines.append('')
    lines.append('Quarantined builders:')
    lines.append('')
    for path in summary['quarantined_builders']:
        lines.append(f'- `{path}`')
    lines.append('')
    lines.append('## Publication-winning rerun spec freeze')
    lines.append('')
    lines.append('| Cutoff | Winning Run | Campaign | CRPS | epsilon | c_factor | Discount Set | df_s1 | df_s2 | df_s67 | df_discrep | df_covs | lambda | Note |')
    lines.append('|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|')
    for row in spec_rows:
        note = row['epsilon_alignment_note'] or '-'
        lines.append(
            f"| `{row['cutoff']}` | `{row['run_id']}` | `{row['campaign_lineage']}` | `{row['publication_crps_display4']}` | "
            f"`{row['effective_epsilon_fit']}` | `{row['effective_c_factor_fit']}` | `{row['discount_set'] or '-'}` | "
            f"`{row['df_s1']}` | `{row['df_s2']}` | `{row['df_s67']}` | `{row['df_discrep']}` | `{row['df_covs']}` | `{row['lambda']}` | {note} |"
        )
    lines.append('')
    lines.append('## 20221225 nuance')
    lines.append('')
    lines.append('- the winning publication row is the exact-input discount-grid override run')
    lines.append('- effective exdqlm fit epsilon remains `360.0`')
    lines.append('- `debug_v8_matrix.epsilon_label=eps90cf1` is descriptive/debug provenance only and must not override the effective fit spec')
    lines.append('- the rerun contract therefore freezes `epsilon=360.0`, `c_factor=1.0`, and discount-set `set09` state evolution values explicitly')
    lines.append('')
    lines.append('## Canonical input-bundle contract')
    lines.append('')
    lines.append('| Cutoff | Retros Window | Bundle Root | USGS | NWS Forecast | GloFAS Forecast | PPT | SOIL | PCA(alias=GDPC1) |')
    lines.append('|---|---|---|---|---|---|---|---|---|')
    for row in bundle_rows:
        lines.append(
            f"| `{row['cutoff']}` | `{row['retros_start']} -> {row['retros_end']}` | `{row['bundle_root']}` | `{row['usgs_daily_source_path']}` | "
            f"`{row['nws_forecast_path']}` | `{row['glofas_forecast_path']}` | `{row['cov_ppt_path']}` | `{row['cov_soil_path']}` | `{row['gdpc_alias_path']}` |"
        )
    lines.append('')
    lines.append('This rerun contract is intentionally tied to the corrected shared bundle lineage:')
    lines.append(f"- bundle artifact root: `{summary['bundle_contract']['bundle_artifact_root']}`")
    lines.append(f"- bundle run id: `{summary['bundle_contract']['bundle_run_id']}`")
    lines.append(f"- data start: `{summary['bundle_contract']['data_start']}`")
    lines.append('')
    lines.append('## Outputs')
    lines.append('')
    lines.append(f"- template: `{summary['paths']['template']}`")
    lines.append(f"- batch: `{summary['paths']['batch']}`")
    lines.append(f"- runbook: `{summary['paths']['runbook']}`")
    lines.append('- spec freeze CSV/JSON and frozen source configs are written beside this note')
    lines.append('')
    return '\n'.join(lines) + '\n'


def write_outputs(*, manifest_path: Path | None = None, out_root: Path = DEFAULT_OUT_ROOT) -> dict[str, Any]:
    payload = build_outputs(manifest_path=manifest_path, out_root=out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    _write_csv(out_root / 'exdqlm_multivar_keep_rerun_spec_freeze.csv', payload['spec_rows'])
    (out_root / 'exdqlm_multivar_keep_rerun_spec_freeze.json').write_text(json.dumps(payload['spec_rows'], indent=2) + '\n', encoding='utf-8')
    _write_csv(out_root / 'canonical_input_bundle_contract.csv', payload['bundle_rows'])
    (out_root / 'canonical_input_bundle_contract.json').write_text(json.dumps(payload['bundle_rows'], indent=2) + '\n', encoding='utf-8')
    (out_root / 'summary.json').write_text(json.dumps(payload['summary'], indent=2) + '\n', encoding='utf-8')
    md = _render_md(payload)
    (out_root / 'HE2_EXDQLM_MULTIVAR_KEEP_RERUN_CONTRACT_20260516.md').write_text(md, encoding='utf-8')
    (out_root / 'README.md').write_text(md, encoding='utf-8')
    return payload


def main() -> int:
    payload = write_outputs()
    print(json.dumps(payload['summary'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
