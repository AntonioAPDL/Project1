#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'reports' / 'he2_exdqlm_univar_shared_relaunch_plan_20260516'
VALIDATION_OUTDIR = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_exact_final_batch_20260516')
SUMMARY_JSON = VALIDATION_OUTDIR / 'prelaunch_validation_summary.json'
OUT_JSON = REPORT_ROOT / 'validation_status_20260516.json'
OUT_MD = REPORT_ROOT / 'HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_VALIDATION_STATUS_20260516.md'
FIT_SMOKE_ROOT = VALIDATION_OUTDIR / 'smoke_runs' / 'fit_quantile_univar' / 'exdqlm_univar' / '20210123' / 'fit_smoke_exdqlm_univar_20210123_qsubset'
FULL_PIPELINE_ROOT = VALIDATION_OUTDIR / 'smoke_runs' / 'full_pipeline' / 'quantile' / 'exdqlm_univar'
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml'


def _read_text(path: Path) -> str:
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8', errors='replace')


def _validator_is_running() -> bool:
    cmd = [
        'pgrep',
        '-af',
        'validate_he2_bayesian_publication_relaunch_prelaunch.py --config config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return bool(proc.stdout.strip())


def _cutoff_smoke_checks() -> dict[str, Any]:
    cutoffs = ['20210123', '20211112', '20211221', '20220511', '20221225']
    rows: list[dict[str, Any]] = []
    passed = 0
    for cutoff in cutoffs:
        stdout = _read_text(VALIDATION_OUTDIR / f'{cutoff}.stdout.log')
        stderr = _read_text(VALIDATION_OUTDIR / f'{cutoff}.stderr.log')
        row = {
            'cutoff': cutoff,
            'stdout_complete': 'Unified run complete.' in stdout,
            'stderr_shared_input_valid': 'shared input validation passed' in stderr,
        }
        row['passed'] = row['stdout_complete'] and row['stderr_shared_input_valid']
        if row['passed']:
            passed += 1
        rows.append(row)
    return {
        'rows': rows,
        'passed': passed,
        'expected': len(cutoffs),
    }


def _family_smoke_check() -> dict[str, Any]:
    stdout = _read_text(VALIDATION_OUTDIR / 'exdqlm_univar.stdout.log')
    stderr = _read_text(VALIDATION_OUTDIR / 'exdqlm_univar.stderr.log')
    return {
        'stdout_complete': 'Unified run complete.' in stdout,
        'stderr_shared_input_valid': 'shared input validation passed' in stderr,
        'passed': ('Unified run complete.' in stdout) and ('shared input validation passed' in stderr),
    }


def _test_block_check() -> dict[str, Any]:
    stderr = _read_text(VALIDATION_OUTDIR / 'test_2.stderr.log')
    return {
        'suite': 'validator_internal_tests',
        'passed': 'OK' in stderr and 'Ran 30 tests' in stderr,
        'stderr_excerpt': stderr.strip().splitlines()[-4:] if stderr.strip() else [],
    }


def _fit_smoke_check() -> dict[str, Any]:
    legacy_log = FIT_SMOKE_ROOT / 'fit' / 'exdqlm_univar' / 'q=50' / 'logs' / 'univar_legacy.log'
    theory_log = FIT_SMOKE_ROOT / 'fit' / 'exdqlm_univar' / 'q=50' / 'logs' / 'univar_theory_summary.log'
    rdata = FIT_SMOKE_ROOT / 'fit' / 'exdqlm_univar' / 'q=50' / 'outputs' / 'variables_50_exAL_synth_DISC_uni.RData'
    legacy_text = _read_text(legacy_log)
    theory_text = _read_text(theory_log)
    return {
        'legacy_log_exists': legacy_log.exists(),
        'theory_log_exists': theory_log.exists(),
        'rdata_exists': rdata.exists(),
        'rdata_logged': 'variables_50_exAL_synth_DISC_uni.RData' in legacy_text,
        'vb_converged': 'VB converged:' in legacy_text,
        'sampling_finished': 'Sampling finished:' in legacy_text,
        'variables_saved': 'Variables saved to:' in legacy_text,
        'shared_state_projection_seen': '[univ_legacy_env_delta] df_t=0.99999999 df_s1=0.99999000 df_s2=0.99999000 df_s67=0.99999000 lambda=0.97000000' in legacy_text,
        'implementation_mode_legacy_bridge': 'implementation_mode=legacy_bridge' in theory_text,
        'passed': (
            legacy_log.exists()
            and theory_log.exists()
            and 'VB converged:' in legacy_text
            and 'Sampling finished:' in legacy_text
            and 'Variables saved to:' in legacy_text
        ),
    }


def _full_pipeline_case_status(case_root: Path) -> dict[str, Any]:
    fit_log = case_root / 'fit' / 'exdqlm_univar' / 'q=50' / 'logs' / 'univar_legacy.log'
    theory_log = case_root / 'fit' / 'exdqlm_univar' / 'q=50' / 'logs' / 'univar_theory_summary.log'
    post_log = case_root / 'post' / 'logs' / 'post_stage.log'
    validate_log = case_root / 'validate' / 'logs' / 'validate_stage.log'
    report_log = case_root / 'report' / 'logs' / 'report_stage.log'
    fit_text = _read_text(fit_log)
    row = {
        'case_root': str(case_root),
        'fit_started': fit_log.exists(),
        'fit_vb_converged': 'VB converged:' in fit_text,
        'fit_sampling_finished': 'Sampling finished:' in fit_text,
        'fit_output_saved': 'Variables saved to:' in fit_text,
        'theory_log_exists': theory_log.exists(),
        'post_started': post_log.exists(),
        'validate_started': validate_log.exists(),
        'report_started': report_log.exists(),
    }
    row['passed'] = row['report_started']
    if row['passed']:
        row['status'] = 'pipeline_passed'
    elif row['fit_output_saved']:
        row['status'] = 'fit_passed_post_pending'
    elif row['fit_started']:
        row['status'] = 'fit_active'
    else:
        row['status'] = 'pending'
    return row


def _full_pipeline_checks() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    expected = 0
    if TEMPLATE.exists():
        template = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        expected = len(((template.get('validation') or {}).get('full_pipeline_quantile_smoke_cases') or []))
    if FULL_PIPELINE_ROOT.exists():
        for case_root in sorted(FULL_PIPELINE_ROOT.glob('*/full_pipeline_exdqlm_univar_*_qsubset')):
            rows.append(_full_pipeline_case_status(case_root))
    return {
        'rows': rows,
        'passed': sum(1 for row in rows if row['passed']),
        'started': sum(1 for row in rows if row['status'] != 'pending'),
        'expected': expected,
    }


def build_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        'family': 'exdqlm_univar',
        'validation_outdir': str(VALIDATION_OUTDIR),
        'summary_json': str(SUMMARY_JSON),
        'status': 'missing',
        'ready_for_launch_after_validation': False,
        'notes': [],
    }
    if SUMMARY_JSON.exists():
        summary = json.loads(SUMMARY_JSON.read_text(encoding='utf-8'))
        checks = summary.get('checks', {})
        smoke = checks.get('smoke_runs', {})
        payload.update({
            'status': 'validated',
            'builder': summary.get('builder', {}),
            'selected_rows': summary.get('selected_rows', []),
            'checks': checks,
            'smoke_runs': summary.get('smoke_runs', []),
            'ready_for_launch_after_validation': True,
            'notes': [
                'no-launch validation completed on the exact final batch',
                f"smoke_runs_passed={smoke.get('passed', 0)}",
                f"smoke_runs_skipped={smoke.get('skipped', 0)}",
            ],
        })
        return payload

    cutoff_checks = _cutoff_smoke_checks()
    family_check = _family_smoke_check()
    test_block = _test_block_check()
    fit_smoke = _fit_smoke_check()
    full_pipeline = _full_pipeline_checks()
    validator_running = _validator_is_running()

    payload.update({
        'status': 'validation_in_progress' if validator_running else 'validation_partial',
        'validator_running': validator_running,
        'cutoff_smoke_checks': cutoff_checks,
        'family_smoke_check': family_check,
        'test_block_check': test_block,
        'fit_smoke_check': fit_smoke,
        'full_pipeline_checks': full_pipeline,
    })
    payload['notes'].extend([
        'prelaunch validation summary does not exist yet',
        f"cutoff_smokes_passed={cutoff_checks['passed']}/{cutoff_checks['expected']}",
        f"family_smoke_passed={str(family_check['passed']).lower()}",
        f"validator_internal_tests_passed={str(test_block['passed']).lower()}",
        f"fit_q50_smoke_passed={str(fit_smoke['passed']).lower()}",
        f"full_pipeline_cases_started={full_pipeline['started']}/{full_pipeline['expected']}",
        f"full_pipeline_cases_passed={full_pipeline['passed']}/{full_pipeline['expected']}",
    ])
    if fit_smoke['passed']:
        payload['notes'].append(
            'hard-case 20210123 q50 fit smoke reached terminal VB, finished sampling, and wrote variables_50_exAL_synth_DISC_uni.RData'
        )
    if validator_running:
        payload['notes'].append('exact-final-batch validator is still running; treat this as an in-progress no-launch validation state')
    return payload


def render_md(payload: dict[str, Any]) -> str:
    lines = [
        '# HE2 exdqlm_univar Shared Relaunch Validation Status',
        '',
        'Date: 2026-05-16',
        '',
        f"- family: `{payload['family']}`",
        f"- validation_outdir: `{payload['validation_outdir']}`",
        f"- summary_json: `{payload['summary_json']}`",
        f"- status: `{payload['status']}`",
        f"- ready_for_launch_after_validation: `{str(payload['ready_for_launch_after_validation']).lower()}`",
        '',
    ]
    if payload['status'] != 'validated':
        lines.append('## Notes')
        lines.append('')
        for note in payload['notes']:
            lines.append(f'- {note}')
        lines.append('')
        if payload['status'] in {'validation_in_progress', 'validation_partial'}:
            cutoff_checks = payload.get('cutoff_smoke_checks', {})
            family_check = payload.get('family_smoke_check', {})
            test_block = payload.get('test_block_check', {})
            fit_smoke = payload.get('fit_smoke_check', {})
            full_pipeline = payload.get('full_pipeline_checks', {})
            lines.extend([
                '## Partial Evidence',
                '',
                '| Check | Result |',
                '|---|---|',
                f"| cutoff_smokes | `{cutoff_checks.get('passed', 0)}/{cutoff_checks.get('expected', 0)}` |",
                f"| family_smoke | `{str(family_check.get('passed', False)).lower()}` |",
                f"| validator_internal_tests | `{str(test_block.get('passed', False)).lower()}` |",
                f"| fit_q50_smoke | `{str(fit_smoke.get('passed', False)).lower()}` |",
                f"| full_pipeline_cases_started | `{full_pipeline.get('started', 0)}/{full_pipeline.get('expected', 0)}` |",
                f"| full_pipeline_cases_passed | `{full_pipeline.get('passed', 0)}/{full_pipeline.get('expected', 0)}` |",
                '',
            ])
        return '\n'.join(lines) + '\n'

    checks = payload['checks']
    smoke = checks.get('smoke_runs', {})
    lines.extend([
        '## Checks',
        '',
        '| Check | Result |',
        '|---|---|',
        f"| bundle_rows | `{checks.get('bundle_rows', {})}` |",
        f"| generated_configs | `{checks.get('generated_configs', {})}` |",
        f"| plan_rows | `{checks.get('plan_rows', {})}` |",
        f"| smoke_runs | `passed={smoke.get('passed', 0)} skipped={smoke.get('skipped', 0)}` |",
        '',
        '## Notes',
        '',
    ])
    for note in payload['notes']:
        lines.append(f'- {note}')
    lines.append('')
    return '\n'.join(lines) + '\n'


def main() -> int:
    payload = build_payload()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    OUT_MD.write_text(render_md(payload), encoding='utf-8')
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
