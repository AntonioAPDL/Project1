#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'reports' / 'he2_al_shared_relaunch_plan_20260517'
OUT_JSON = REPORT_ROOT / 'validation_status_20260517.json'
OUT_MD = REPORT_ROOT / 'HE2_AL_SHARED_RELAUNCH_VALIDATION_STATUS_20260517.md'

PACKAGES: dict[str, dict[str, str]] = {
    'dqlm_multivar_al_keep': {
        'label': 'AL-M-T1',
        'template': 'config/he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.template.yaml',
        'summary_json': '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517/control/prelaunch_validation_exact_final_batch_20260517/prelaunch_validation_summary.json',
    },
    'dqlm_multivar_al_drop': {
        'label': 'AL-M-T0',
        'template': 'config/he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml',
        'summary_json': '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517/control/prelaunch_validation_exact_final_batch_20260517/prelaunch_validation_summary.json',
    },
    'dqlm_univar_al': {
        'label': 'AL-U-T1',
        'template': 'config/he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml',
        'summary_json': '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_univar_al_all_cutoffs_sharedspec_20260517/control/prelaunch_validation_exact_final_batch_20260517/prelaunch_validation_summary.json',
    },
}


def _validator_running(template_rel: str) -> bool:
    proc = subprocess.run(
        ['pgrep', '-af', f'validate_he2_bayesian_publication_relaunch_prelaunch.py --config {template_rel}'],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(proc.stdout.strip())


def build_payload() -> dict[str, Any]:
    families: dict[str, Any] = {}
    all_validated = True
    for family, info in PACKAGES.items():
        summary_path = Path(info['summary_json'])
        row: dict[str, Any] = {
            'manuscript_label': info['label'],
            'template': info['template'],
            'summary_json': str(summary_path),
            'status': 'missing',
            'ready_for_launch_after_validation': False,
        }
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding='utf-8'))
            smoke = (summary.get('checks') or {}).get('smoke_runs', {})
            row.update({
                'status': 'validated',
                'selected_rows': len(summary.get('selected_rows', [])),
                'smoke_runs_count': smoke.get('count', 0),
                'smoke_runs_passed': smoke.get('passed', 0),
                'smoke_runs_skipped': smoke.get('skipped', 0),
                'ready_for_launch_after_validation': True,
            })
        else:
            running = _validator_running(info['template'])
            all_validated = False
            row['status'] = 'validation_in_progress' if running else 'not_validated'
            row['validator_running'] = running
        families[family] = row
        all_validated &= row['status'] == 'validated'
    return {
        'status': 'validated' if all_validated else 'validation_incomplete',
        'families': families,
    }


def render_md(payload: dict[str, Any]) -> str:
    lines = [
        '# HE2 AL Shared Relaunch Validation Status',
        '',
        'Date: 2026-05-17',
        '',
        f"- status: `{payload['status']}`",
        '',
        '| Family | Label | Status | Selected rows | Smoke passed | Smoke skipped | Ready for launch |',
        '|---|---|---|---:|---:|---:|---|',
    ]
    for family, row in payload['families'].items():
        lines.append(
            f"| `{family}` | `{row['manuscript_label']}` | `{row['status']}` | `{row.get('selected_rows', 0)}` | `{row.get('smoke_runs_passed', 0)}` | `{row.get('smoke_runs_skipped', 0)}` | `{str(row['ready_for_launch_after_validation']).lower()}` |"
        )
    return '\n'.join(lines) + '\n'


def main() -> None:
    payload = build_payload()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    OUT_MD.write_text(render_md(payload), encoding='utf-8')


if __name__ == '__main__':
    main()
