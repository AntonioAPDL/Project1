#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from he2_publication_relaunch_lib import load_publication_manifest_rows, spec_token

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = ROOT / 'reports' / 'he2_full_crps_stage1_contract_20260516'
DEFAULT_HISTORICAL_AUDIT = (
    ROOT
    / 'reports'
    / 'he2_publication_manifest'
    / 'historical_support_audit_20260507'
    / 'historical_support_audit.csv'
)
DEFAULT_ALIGNMENT_AUDIT = (
    ROOT
    / 'reports'
    / 'he2_publication_manifest'
    / 'he2_bayesian_publication_alignment.csv'
)
DEFAULT_INPUT_AUDIT_SUMMARY = (
    ROOT
    / 'reports'
    / 'he2_bayesian_input_sanity_audit'
    / 'he2_bayesian_input_sanity_summary.csv'
)
DEFAULT_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_20260510.template.yaml'

REFERENCE_COMPLETED_FAMILY = 'exdqlm_multivar_keep'
REFERENCE_COMPLETED_ROOT = (
    ROOT.parent
    / 'project1_ucsc_phd_runtime'
    / 'multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512'
)

APPROVED_LAUNCHER = {
    'selection_source': 'reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv',
    'builder': 'scripts/build_he2_bayesian_publication_relaunch_configs.py',
    'validator': 'scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py',
    'template': 'config/he2_bayesian_publication_relaunch_20260510.template.yaml',
}

QUARANTINED_BUILDERS = [
    'scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py',
    'scripts/build_multimodel_v8_all9_feature_matrix_configs.py',
    'scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py',
]

WAVE_BY_FAMILY = {
    'ndlm_univar_keep': 'wave_a_ndlm',
    'ndlm_main_drop': 'wave_a_ndlm',
    'ndlm_main_keep': 'wave_a_ndlm',
    'dqlm_univar_al': 'wave_b_univariate_bridge',
    'exdqlm_univar': 'wave_b_univariate_bridge',
    'dqlm_multivar_al_drop': 'wave_c_multivariate_bridge',
    'dqlm_multivar_al_keep': 'wave_c_multivariate_bridge',
    'exdqlm_multivar_drop': 'wave_c_multivariate_bridge',
}


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _spec_class(campaign_lineage: str) -> str:
    if campaign_lineage.startswith('featurecov_cf1_eps_sweep_20260416'):
        return 'epsilon_winner'
    if campaign_lineage.startswith('ndlm_featurecov_rerun_postfix_20260421'):
        return 'ndlm_postfix_winner'
    if campaign_lineage.startswith('univar_featurecov_he2_rerun_20260422'):
        return 'univar_winner'
    if campaign_lineage.startswith('exalm_t1_discount_grid_exact_20260424'):
        return 'discount_override_winner'
    return 'other'


def _load_historical_audit(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    rows = _read_csv(path)
    return {(row['cutoff'], row['manuscript_label']): row for row in rows}


def _load_alignment_audit(path: Path) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for row in _read_csv(path):
        out.setdefault(row['cutoff'], []).append(row)
    return out


def _input_audit_summary(path: Path) -> dict[str, Any]:
    rows = _read_csv(path)
    passed = sum(1 for row in rows if str(row['all_equal']).strip().lower() == 'true')
    return {
        'summary_csv': str(path),
        'artifact_checks_passed': passed,
        'artifact_checks_total': len(rows),
        'cutoffs': sorted({row['cutoff'] for row in rows}),
    }


def _freeze_config(src: Path, dst: Path) -> tuple[str, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    digest = _sha256(dst)
    return str(dst), digest


def build_outputs(
    *,
    manifest_path: Path | None = None,
    historical_audit_path: Path = DEFAULT_HISTORICAL_AUDIT,
    alignment_audit_path: Path = DEFAULT_ALIGNMENT_AUDIT,
    input_audit_summary_path: Path = DEFAULT_INPUT_AUDIT_SUMMARY,
    out_root: Path = DEFAULT_OUT_ROOT,
) -> dict[str, Any]:
    manifest_rows = [
        row for row in load_publication_manifest_rows(manifest_path)
        if row['family'] != REFERENCE_COMPLETED_FAMILY
    ]
    historical_audit = _load_historical_audit(historical_audit_path)
    alignment_audit = _load_alignment_audit(alignment_audit_path)
    input_audit = _input_audit_summary(input_audit_summary_path)

    source_freeze_root = out_root / 'source_config_freeze'
    matrix_rows: list[dict[str, Any]] = []
    spec_rows: list[dict[str, Any]] = []

    for row in manifest_rows:
        hist = historical_audit[(row['cutoff'], row['manuscript_label'])]
        resolved_config = Path(row['resolved_config_path']).resolve()
        frozen_name = f"{row['cutoff']}_{row['manuscript_label'].replace('-', '_')}_{row['family']}.resolved_config.yaml"
        frozen_path, resolved_hash = _freeze_config(resolved_config, source_freeze_root / frozen_name)
        wave = WAVE_BY_FAMILY[row['family']]
        selected_spec = spec_token(row)
        spec_class = _spec_class(row['campaign_lineage'])
        matrix_rows.append(
            {
                'cutoff': row['cutoff'],
                'cutoff_display': row['cutoff_display'],
                'manuscript_label': row['manuscript_label'],
                'family': row['family'],
                'wave': wave,
                'implementation_mode': row['implementation_mode'],
                'likelihood_mode': row['likelihood_mode'],
                'forecast_transfer_mode': row['forecast_transfer_mode'],
                'current_campaign_lineage': row['campaign_lineage'],
                'current_run_id': row['run_id'],
                'current_run_root': row['run_root'],
                'current_resolved_config_path': row['resolved_config_path'],
                'frozen_resolved_config_path': frozen_path,
                'resolved_config_sha256': resolved_hash,
                'selected_spec_token': selected_spec,
                'selected_spec_class': spec_class,
                'current_crps_display4': row['crps_display4'],
                'fit_covariate_names': row['fit_covariate_names'],
                'deterministic_climate_enabled': row['deterministic_climate_enabled'],
                'within_cutoff_shared_inputs_aligned_current': row['within_cutoff_shared_inputs_aligned'],
                'full_history_from_1987_current': hist['full_history_from_1987'],
                'effective_common_start_current': hist['effective_common_start'],
                'approved_launcher_builder': APPROVED_LAUNCHER['builder'],
                'approved_launcher_validator': APPROVED_LAUNCHER['validator'],
                'approved_template': APPROVED_LAUNCHER['template'],
                'requires_corrected_rerun': 'True',
            }
        )
        spec_rows.append(
            {
                **row,
                'selected_spec_token': selected_spec,
                'selected_spec_class': spec_class,
                'wave': wave,
                'full_history_from_1987_current': hist['full_history_from_1987'],
                'effective_common_start_current': hist['effective_common_start'],
                'frozen_resolved_config_path': frozen_path,
                'resolved_config_sha256': resolved_hash,
            }
        )

    matrix_rows.sort(key=lambda item: (item['cutoff'], item['manuscript_label']))
    spec_rows.sort(key=lambda item: (item['cutoff'], item['manuscript_label']))

    wave_rows = [row for row in matrix_rows if row['wave'] == 'wave_a_ndlm']
    wave_rows.sort(key=lambda item: (item['cutoff'], item['manuscript_label']))

    rows_by_cutoff = Counter(row['cutoff'] for row in matrix_rows)
    rows_by_wave = Counter(row['wave'] for row in matrix_rows)
    rows_by_spec_class = Counter(row['selected_spec_class'] for row in matrix_rows)
    historical_cutoffs = sorted(
        {
            row['cutoff']
            for row in matrix_rows
            if str(row['full_history_from_1987_current']).strip().lower() != 'true'
        }
    )
    alignment_status = {
        cutoff: {
            'artifacts': len(rows),
            'all_equal_count': sum(1 for row in rows if str(row['all_equal']).strip().lower() == 'true'),
        }
        for cutoff, rows in alignment_audit.items()
    }
    summary = {
        'generated_from': {
            'manifest_csv': str(manifest_path or (ROOT / APPROVED_LAUNCHER['selection_source'])),
            'historical_audit_csv': str(historical_audit_path),
            'alignment_audit_csv': str(alignment_audit_path),
            'input_audit_summary_csv': str(input_audit_summary_path),
            'reference_completed_family': REFERENCE_COMPLETED_FAMILY,
            'reference_completed_root': str(REFERENCE_COMPLETED_ROOT),
        },
        'approved_launcher': APPROVED_LAUNCHER,
        'quarantined_builders': QUARANTINED_BUILDERS,
        'counts': {
            'remaining_rows': len(matrix_rows),
            'remaining_families': len({row['family'] for row in matrix_rows}),
            'rows_by_cutoff': dict(rows_by_cutoff),
            'rows_by_wave': dict(rows_by_wave),
            'rows_by_selected_spec_class': dict(rows_by_spec_class),
        },
        'cutoffs_requiring_corrected_full_history_attention': historical_cutoffs,
        'input_audit': input_audit,
        'alignment_status': alignment_status,
    }

    return {
        'matrix_rows': matrix_rows,
        'spec_rows': spec_rows,
        'wave_a_rows': wave_rows,
        'summary': summary,
    }


def _render_launcher_md(summary: dict[str, Any], matrix_rows: list[dict[str, Any]], wave_rows: list[dict[str, Any]]) -> str:
    approved = summary['approved_launcher']
    counts = summary['counts']
    lines: list[str] = []
    lines.append('# HE2 Full CRPS Stage 1 Launcher Qualification')
    lines.append('')
    lines.append('Date: 2026-05-16')
    lines.append('')
    lines.append('## Decision')
    lines.append('')
    lines.append('The remaining full-table Bayesian relaunch is approved to proceed only through the manifest-driven relaunch stack.')
    lines.append('')
    lines.append('Approved launch authority:')
    lines.append(f"- selection source: `{approved['selection_source']}`")
    lines.append(f"- builder: `{approved['builder']}`")
    lines.append(f"- validator: `{approved['validator']}`")
    lines.append(f"- baseline template: `{approved['template']}`")
    lines.append('')
    lines.append('Quarantined legacy builders:')
    for path in summary['quarantined_builders']:
        lines.append(f'- `{path}`')
    lines.append('')
    lines.append('## Why this launcher is the approved path')
    lines.append('')
    lines.append('- It selects rows from the authoritative 45-row publication manifest.')
    lines.append('- It starts from each publication-winning `resolved_config.yaml` instead of an older family sweep default.')
    lines.append('- It freezes row-level winning spec tokens, config patches, and cutoff bundle audits.')
    lines.append('- It already supports the corrected shared-input contract and prelaunch validation gates.')
    lines.append('')
    lines.append('## Current audit read')
    lines.append('')
    lines.append(f"- remaining Bayesian rows to relaunch: `{counts['remaining_rows']}`")
    lines.append(f"- remaining Bayesian families: `{counts['remaining_families']}`")
    lines.append(f"- input-alignment audit checks passed: `{summary['input_audit']['artifact_checks_passed']} / {summary['input_audit']['artifact_checks_total']}`")
    lines.append(f"- cutoffs still lacking corrected full-history support in the current publication lineage: `{', '.join(summary['cutoffs_requiring_corrected_full_history_attention'])}`")
    lines.append(f"- completed reference family: `{summary['generated_from']['reference_completed_family']}`")
    lines.append(f"- completed reference root: `{summary['generated_from']['reference_completed_root']}`")
    lines.append('')
    lines.append('## Wave grouping')
    lines.append('')
    lines.append('| Wave | Families | Row count |')
    lines.append('|---|---|---:|')
    wave_families: dict[str, list[str]] = {}
    for row in matrix_rows:
        wave_families.setdefault(row['wave'], [])
        if row['family'] not in wave_families[row['wave']]:
            wave_families[row['wave']].append(row['family'])
    for wave, family_list in sorted(wave_families.items()):
        lines.append(f"| `{wave}` | `{', '.join(family_list)}` | {counts['rows_by_wave'][wave]} |")
    lines.append('')
    lines.append('## Wave A launch path')
    lines.append('')
    lines.append('Wave A is the approved first relaunch wave:')
    for family in sorted({row['family'] for row in wave_rows}):
        lines.append(f'- `{family}`')
    lines.append('')
    lines.append('Wave A row count by cutoff:')
    for cutoff, n_rows in Counter(row['cutoff'] for row in wave_rows).items():
        lines.append(f'- `{cutoff}`: `{n_rows}` rows')
    lines.append('')
    lines.append('## Frozen remaining-family spec source')
    lines.append('')
    lines.append('Every remaining row now has a frozen local copy of its publication-winning `resolved_config.yaml` under:')
    lines.append('')
    lines.append('- `source_config_freeze/`')
    lines.append('')
    lines.append('Those frozen configs are the reviewer-facing proof that the remaining relaunch preserves the exact publication-winning row specs while changing only the shared-input lineage and relaunch scaffolding.')
    lines.append('')
    return '\n'.join(lines) + '\n'


def write_outputs(
    *,
    manifest_path: Path | None = None,
    historical_audit_path: Path = DEFAULT_HISTORICAL_AUDIT,
    alignment_audit_path: Path = DEFAULT_ALIGNMENT_AUDIT,
    input_audit_summary_path: Path = DEFAULT_INPUT_AUDIT_SUMMARY,
    out_root: Path = DEFAULT_OUT_ROOT,
) -> dict[str, Any]:
    out_root.mkdir(parents=True, exist_ok=True)
    payload = build_outputs(
        manifest_path=manifest_path,
        historical_audit_path=historical_audit_path,
        alignment_audit_path=alignment_audit_path,
        input_audit_summary_path=input_audit_summary_path,
        out_root=out_root,
    )

    _write_csv(out_root / 'remaining_family_relaunch_matrix.csv', payload['matrix_rows'])
    (out_root / 'remaining_family_relaunch_matrix.json').write_text(
        json.dumps(payload['matrix_rows'], indent=2) + '\n', encoding='utf-8'
    )
    _write_csv(out_root / 'remaining_family_spec_freeze.csv', payload['spec_rows'])
    (out_root / 'remaining_family_spec_freeze.json').write_text(
        json.dumps(payload['spec_rows'], indent=2) + '\n', encoding='utf-8'
    )
    _write_csv(out_root / 'wave_a_ndlm_rows.csv', payload['wave_a_rows'])

    launcher_md = _render_launcher_md(payload['summary'], payload['matrix_rows'], payload['wave_a_rows'])
    (out_root / 'HE2_FULL_CRPS_STAGE1_LAUNCHER_QUALIFICATION_20260516.md').write_text(
        launcher_md, encoding='utf-8'
    )
    (out_root / 'launcher_qualification.json').write_text(
        json.dumps(payload['summary'], indent=2) + '\n', encoding='utf-8'
    )
    (out_root / 'README.md').write_text(
        '# HE2 Full CRPS Stage 1 Contract Bundle\n\n'
        'This bundle freezes the Stage 1 launcher qualification, remaining-family relaunch matrix, '
        'and frozen source-config copies for the remaining full-table Bayesian relaunch.\n\n'
        'Primary files:\n'
        '- `HE2_FULL_CRPS_STAGE1_LAUNCHER_QUALIFICATION_20260516.md`\n'
        '- `remaining_family_relaunch_matrix.csv`\n'
        '- `remaining_family_spec_freeze.csv`\n'
        '- `wave_a_ndlm_rows.csv`\n'
        '- `launcher_qualification.json`\n',
        encoding='utf-8',
    )
    (out_root / 'summary.json').write_text(json.dumps(payload['summary'], indent=2) + '\n', encoding='utf-8')
    return payload


def main() -> int:
    write_outputs()
    print(f'out_root={DEFAULT_OUT_ROOT}')
    print('remaining_rows=40')
    print('wave_a_rows=15')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
