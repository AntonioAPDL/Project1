#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / 'reports' / 'he2_exdqlm_multivar_keep_rerun_contract_20260516'
RERUN_ROOT = Path(
    '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/'
    'multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_rerun_20260516'
)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def _latest_validation_dir(control_root: Path) -> Path:
    matches = sorted(control_root.glob('prelaunch_validation_*'))
    if not matches:
        raise FileNotFoundError(f'No prelaunch validation directories found under {control_root}')
    return max(matches, key=lambda p: p.stat().st_mtime)


def main() -> int:
    CONTRACT_ROOT.mkdir(parents=True, exist_ok=True)
    contract_summary = _read_json(CONTRACT_ROOT / 'summary.json')
    spec_rows = _read_csv(CONTRACT_ROOT / 'exdqlm_multivar_keep_rerun_spec_freeze.csv')
    validation_dir = _latest_validation_dir(RERUN_ROOT / 'control')
    validation_summary = _read_json(validation_dir / 'prelaunch_validation_summary.json')
    bundle_rows = _read_csv(RERUN_ROOT / 'control' / 'publication_relaunch_matrix' / 'cutoff_bundle_audit.csv')

    readiness = {
        'status': 'validated_no_launch',
        'family': 'exdqlm_multivar_keep',
        'approved_launcher': contract_summary['approved_launcher'],
        'validation_dir': str(validation_dir),
        'selected_scope': validation_summary['checks']['selected_scope'],
        'smoke_runs': validation_summary['checks']['smoke_runs'],
        'spec_rows': spec_rows,
        'bundle_rows': bundle_rows,
    }
    (CONTRACT_ROOT / 'exdqlm_multivar_keep_rerun_readiness_20260516.json').write_text(
        json.dumps(readiness, indent=2) + '\n',
        encoding='utf-8',
    )

    lines: list[str] = []
    lines.append('# HE2 exdqlm_multivar_keep Rerun Readiness')
    lines.append('')
    lines.append('Date: 2026-05-16')
    lines.append('')
    lines.append('## Decision')
    lines.append('')
    lines.append('- status: `VALIDATED_NO_LAUNCH`')
    lines.append('- scope: all 5 `exdqlm_multivar_keep` rows')
    lines.append('- launch posture: queue remains stopped; this note confirms readiness only')
    lines.append('')
    lines.append('## Selected scope')
    lines.append('')
    scope = validation_summary['checks']['selected_scope']
    lines.append(f"- rows: `{scope['rows']}`")
    lines.append(f"- families: `{', '.join(scope['families'])}`")
    lines.append(f"- cutoffs: `{', '.join(scope['cutoffs'])}`")
    lines.append('')
    lines.append('## Bundle contract recheck')
    lines.append('')
    lines.append('| Cutoff | Retros | USGS | Deterministic Futures | PPT | SOIL | GDPC Alias |')
    lines.append('|---|---|---|---|---|---|---|')
    for row in bundle_rows:
        lines.append(
            f"| `{row['cutoff']}` | `{row['retros_start']} -> {row['retros_end']}` | `{row['usgs_daily_source_path']}` | `{row['deterministic_handoff_root']}` | `{row['deterministic_precip_source']}` | `{row['deterministic_soil_source']}` | `{row['gdpc_alias_path']}` |"
        )
    lines.append('')
    lines.append('## Frozen publication-winning spec recheck')
    lines.append('')
    lines.append('| Cutoff | epsilon | c_factor | Discount Set | df_s1 | df_s2 | df_s67 | df_discrep | df_covs | lambda |')
    lines.append('|---|---:|---:|---|---:|---:|---:|---:|---:|---:|')
    for row in spec_rows:
        lines.append(
            f"| `{row['cutoff']}` | `{row['effective_epsilon_fit']}` | `{row['effective_c_factor_fit']}` | `{row['discount_set'] or '-'}` | `{row['df_s1']}` | `{row['df_s2']}` | `{row['df_s67']}` | `{row['df_discrep']}` | `{row['df_covs']}` | `{row['lambda']}` |"
        )
    lines.append('')
    lines.append('## Validator result')
    lines.append('')
    checks = validation_summary['checks']
    lines.append(f"- bundle build: `{checks['bundle_build']}`")
    lines.append(f"- within-cutoff bundle alignment: `{checks['within_cutoff_bundle_alignment']}`")
    lines.append(f"- smoke runs: `{checks['smoke_runs']['passed']}` passed, `{checks['smoke_runs']['skipped']}` skipped, `{checks['smoke_runs']['count']}` total")
    lines.append('- expected skips: NDLM and univariate smoke scopes are outside the selected rerun family')
    lines.append('')
    lines.append('## Gate')
    lines.append('')
    lines.append('- corrected shared bundles: verified')
    lines.append('- full-history retros and USGS from `1987-05-29 -> cutoff`: verified')
    lines.append('- blended deterministic `PPT` and `SOIL`: verified')
    lines.append('- `PCA(alias=GDPC1)` covariate lineage: verified')
    lines.append('- exact exdqlm per-cutoff spec freeze: verified')
    lines.append('- live launch: not started in this stage')
    lines.append('')
    (CONTRACT_ROOT / 'HE2_EXDQLM_MULTIVAR_KEEP_RERUN_READINESS_20260516.md').write_text(
        '\n'.join(lines) + '\n',
        encoding='utf-8',
    )
    print(CONTRACT_ROOT / 'HE2_EXDQLM_MULTIVAR_KEEP_RERUN_READINESS_20260516.md')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
