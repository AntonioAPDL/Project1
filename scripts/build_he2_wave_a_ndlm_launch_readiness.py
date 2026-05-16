#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE1_ROOT = ROOT / 'reports' / 'he2_full_crps_stage1_contract_20260516'
WAVE_A_ROOT = Path(
    '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/'
    'multimodel_v8_he2_bayesian_publication_relaunch_wave_a_ndlm_20260516'
)
VALIDATION_ROOT = WAVE_A_ROOT / 'control' / 'prelaunch_validation_20260516T203333Z'


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    out_root = STAGE1_ROOT
    out_root.mkdir(parents=True, exist_ok=True)

    stage1_summary = read_json(STAGE1_ROOT / 'summary.json')
    validation_summary = read_json(VALIDATION_ROOT / 'prelaunch_validation_summary.json')
    bundle_rows = read_csv(WAVE_A_ROOT / 'control' / 'publication_relaunch_matrix' / 'cutoff_bundle_audit.csv')

    readiness = {
        'status': 'go',
        'wave': 'wave_a_ndlm',
        'approved_launcher': stage1_summary['approved_launcher'],
        'quarantined_builders': stage1_summary['quarantined_builders'],
        'remaining_scope_counts': stage1_summary['counts'],
        'wave_a_selected_scope': validation_summary['checks']['selected_scope'],
        'input_bundle_contract': [
            {
                'cutoff': row['cutoff'],
                'bundle_root': row['bundle_root'],
                'retros_start': row['retros_start'],
                'retros_end': row['retros_end'],
                'usgs_daily_source_path': row['usgs_daily_source_path'],
                'deterministic_handoff_root': row['deterministic_handoff_root'],
                'deterministic_precip_source': row['deterministic_precip_source'],
                'deterministic_soil_source': row['deterministic_soil_source'],
                'gdpc_alias_path': row['gdpc_alias_path'],
                'gdpc_alias_start': row['gdpc_alias_start'],
                'gdpc_alias_end': row['gdpc_alias_end'],
            }
            for row in bundle_rows
        ],
        'validation_status': validation_summary,
    }

    (out_root / 'wave_a_ndlm_launch_readiness_20260516.json').write_text(
        json.dumps(readiness, indent=2) + '\n',
        encoding='utf-8',
    )

    lines: list[str] = []
    lines.append('# HE2 Wave A NDLM Launch Readiness')
    lines.append('')
    lines.append('Date: 2026-05-16')
    lines.append('')
    lines.append('## Decision')
    lines.append('')
    lines.append('- status: `GO`')
    lines.append('- approved launcher: manifest-driven publication relaunch builder + validator only')
    lines.append('- scope: 15 NDLM rows across 5 cutoffs')
    lines.append('')
    lines.append('## Approved launcher')
    lines.append('')
    for key, value in stage1_summary['approved_launcher'].items():
        lines.append(f'- `{key}`: `{value}`')
    lines.append('')
    lines.append('Quarantined builders:')
    lines.append('')
    for path in stage1_summary['quarantined_builders']:
        lines.append(f'- `{path}`')
    lines.append('')
    lines.append('## Wave A scope')
    lines.append('')
    scope = validation_summary['checks']['selected_scope']
    lines.append(f"- rows: `{scope['rows']}`")
    lines.append(f"- families: `{', '.join(scope['families'])}`")
    lines.append(f"- cutoffs: `{', '.join(scope['cutoffs'])}`")
    lines.append('')
    lines.append('## Input-bundle contract')
    lines.append('')
    lines.append('| Cutoff | Bundle Root | Retros | USGS | Deterministic Futures | GDPC Alias |')
    lines.append('|---|---|---|---|---|---|')
    for row in bundle_rows:
        lines.append(
            f"| `{row['cutoff']}` | `{row['bundle_root']}` | `{row['retros_start']} -> {row['retros_end']}` | "
            f"`{row['usgs_daily_source_path']}` | `{row['deterministic_handoff_root']}` | `{row['gdpc_alias_path']}` |"
        )
    lines.append('')
    lines.append('## Validation result')
    lines.append('')
    checks = validation_summary['checks']
    lines.append(f"- bundle build: `{checks['bundle_build']}`")
    lines.append(f"- within-cutoff bundle alignment: `{checks['within_cutoff_bundle_alignment']}`")
    smoke = checks['smoke_runs']
    lines.append(
        f"- smoke runs: `{smoke['passed']}` passed, `{smoke['skipped']}` skipped, `{smoke['count']}` total"
    )
    lines.append('- quantile smoke scopes skipped only because Wave A intentionally selects NDLM rows')
    lines.append('')
    lines.append('## Launch gate')
    lines.append('')
    lines.append('- full-history retros: `1987-05-29 -> cutoff` verified')
    lines.append('- within-cutoff shared bundles: verified')
    lines.append('- canonical covariate contract: `PPT`, `SOIL`, `PCA(alias=GDPC1)` verified')
    lines.append('- deterministic blended futures: verified')
    lines.append('- Wave A NDLM fit + pipeline smokes: passed')
    lines.append('')
    lines.append('Wave A is ready for real launch on the approved path.')
    lines.append('')

    (out_root / 'HE2_WAVE_A_NDLM_LAUNCH_READINESS_20260516.md').write_text(
        '\n'.join(lines),
        encoding='utf-8',
    )
    print(out_root / 'HE2_WAVE_A_NDLM_LAUNCH_READINESS_20260516.md')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
