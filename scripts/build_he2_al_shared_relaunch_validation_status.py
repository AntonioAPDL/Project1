#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import re
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

PRODCLONE_DIAGNOSTICS: dict[str, dict[str, str]] = {
    'dqlm_multivar_al_keep': {
        'label': 'AL-M-T1 q65 prodclone',
        'template': 'config/he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517.template.yaml',
        'root': '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517',
        'fit_log': '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517/smoke_runs/fit_quantile/dqlm_multivar_al_keep/20221225/fit_smoke_dqlm_multivar_al_keep_20221225_qsubset/fit/exdqlm_multivar/keep/q=65/logs/fit.log',
    },
    'dqlm_multivar_al_drop': {
        'label': 'AL-M-T0 q65 prodclone',
        'template': 'config/he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517.template.yaml',
        'root': '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517',
        'fit_log': '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517/smoke_runs/fit_quantile/dqlm_multivar_al_drop/20221225/fit_smoke_dqlm_multivar_al_drop_20221225_qsubset/fit/q=65/logs/fit.log',
    },
}

ITER_RE = re.compile(r'^\[1\]\s+([0-9]+(?:\.0+)?)\b')


def _validator_running(template_rel: str) -> bool:
    proc = subprocess.run(
        ['pgrep', '-af', f'validate_he2_bayesian_publication_relaunch_prelaunch.py --config {template_rel}'],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(proc.stdout.strip())


def _summary_smoke_ok(summary: dict[str, Any]) -> bool:
    smoke_rows = summary.get('smoke_runs') or []
    if smoke_rows:
        return all((row.get('status') in {'passed', 'skipped'}) for row in smoke_rows)
    smoke = (summary.get('checks') or {}).get('smoke_runs', {})
    count = int(smoke.get('count', 0) or 0)
    passed = int(smoke.get('passed', 0) or 0)
    skipped = int(smoke.get('skipped', 0) or 0)
    return count > 0 and (passed + skipped == count)


def _selected_rows(summary: dict[str, Any]) -> int:
    scope = (summary.get('checks') or {}).get('selected_scope') or {}
    if scope.get('rows') is not None:
        return int(scope['rows'])
    return len(summary.get('selected_rows', []))


def _smoke_counts(summary: dict[str, Any]) -> tuple[int, int, int]:
    smoke = (summary.get('checks') or {}).get('smoke_runs', {})
    count = int(smoke.get('count', 0) or 0)
    passed = int(smoke.get('passed', 0) or 0)
    skipped = int(smoke.get('skipped', 0) or 0)
    if count == 0:
        rows = summary.get('smoke_runs') or []
        count = len(rows)
        passed = sum(1 for row in rows if row.get('status') == 'passed')
        skipped = sum(1 for row in rows if row.get('status') == 'skipped')
    return count, passed, skipped


def _latest_iter(fit_log: Path) -> int | None:
    if not fit_log.exists():
        return None
    latest: int | None = None
    for line in fit_log.read_text(encoding='utf-8', errors='ignore').splitlines():
        match = ITER_RE.match(line.strip())
        if match:
            latest = int(float(match.group(1)))
    return latest


def _prodclone_status(family: str) -> dict[str, Any] | None:
    info = PRODCLONE_DIAGNOSTICS.get(family)
    if not info:
        return None
    root = Path(info['root'])
    row: dict[str, Any] = {
        'label': info['label'],
        'root': str(root),
        'template': info['template'],
    }
    if not root.exists():
        return row
    summary_path = root / 'prelaunch_validation_summary.json'
    fit_log = Path(info['fit_log'])
    row['latest_fit_iter'] = _latest_iter(fit_log)
    row['fit_artifact_present'] = any(
        root.glob('smoke_runs/fit_quantile/**/outputs/DISC_variables_*_exAL_synth_DISC.RData')
    )
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        count, passed, skipped = _smoke_counts(summary)
        row.update({
            'status': 'passed' if _summary_smoke_ok(summary) else 'failed',
            'smoke_runs_count': count,
            'smoke_runs_passed': passed,
            'smoke_runs_skipped': skipped,
            'summary_json': str(summary_path),
        })
    else:
        running = _validator_running(info['template'])
        row['status'] = 'running' if running else 'pending'
        row['validator_running'] = running
    return row


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
            smoke_count, smoke_passed, smoke_skipped = _smoke_counts(summary)
            smoke_ok = _summary_smoke_ok(summary)
            row.update({
                'status': 'validated' if smoke_ok else 'validation_failed',
                'selected_rows': _selected_rows(summary),
                'smoke_runs_count': smoke_count,
                'smoke_runs_passed': smoke_passed,
                'smoke_runs_skipped': smoke_skipped,
                'ready_for_launch_after_validation': smoke_ok,
            })
        else:
            running = _validator_running(info['template'])
            prodclone = _prodclone_status(family)
            row['status'] = 'validation_in_progress' if running else 'not_validated'
            row['validator_running'] = running
            if prodclone and prodclone.get('status') in {'running', 'passed', 'failed'}:
                row['status'] = f"prodclone_{prodclone['status']}"
                row['prodclone'] = prodclone
        all_validated &= row['ready_for_launch_after_validation']
        families[family] = row
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
    prodclone_rows = [
        (family, row['prodclone'])
        for family, row in payload['families'].items()
        if row.get('prodclone')
    ]
    if prodclone_rows:
        lines.extend([
            '',
            '## Prodclone Diagnostics',
            '',
            '| Family | Diagnostic | Status | Latest fit iter | Fit artifact present |',
            '|---|---|---|---:|---|',
        ])
        for family, row in prodclone_rows:
            lines.append(
                f"| `{family}` | `{row['label']}` | `{row['status']}` | `{row.get('latest_fit_iter', 0) or 0}` | `{str(bool(row.get('fit_artifact_present'))).lower()}` |"
            )
    return '\n'.join(lines) + '\n'


def main() -> None:
    payload = build_payload()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    OUT_MD.write_text(render_md(payload), encoding='utf-8')


if __name__ == '__main__':
    main()
