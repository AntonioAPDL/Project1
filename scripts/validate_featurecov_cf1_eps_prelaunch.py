#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FAMILIES = [
    'exdqlm_multivar_keep',
    'exdqlm_multivar_drop',
    'dqlm_multivar_al_keep',
    'dqlm_multivar_al_drop',
    'ndlm_main_keep',
    'ndlm_main_drop',
]
EXPECTED_CUTOFFS = ['20210123', '20211112', '20211221', '20220511', '20221225']
EXPECTED_EPSILONS = ['eps1cf1', 'eps30cf1', 'eps60cf1', 'eps90cf1', 'eps180cf1', 'eps360cf1']
EXPECTED_FEATURE_COLUMNS = [
    'PPT', 'SOIL', 'PCA', 'PPT_sq', 'SOIL_sq', 'PPT_x_SOIL',
    'PPT_lag1', 'PPT_lag2', 'PPT_lag3', 'SOIL_lag1', 'SOIL_lag2', 'SOIL_lag3',
]
EXPECTED_FIT_WORKERS_BY_FAMILY = {
    'exdqlm_multivar_keep': 7,
    'exdqlm_multivar_drop': 7,
    'dqlm_multivar_al_keep': 7,
    'dqlm_multivar_al_drop': 7,
    'ndlm_main_keep': 1,
    'ndlm_main_drop': 1,
}


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, env=env)


def parse_builder_stdout(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if '=' in line and line.split('=', 1)[0] in {'artifact_root', 'matrix_dir', 'config_output_dir', 'generated_configs', 'plan_rows', 'selection_rows', 'reused_rows'}:
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_temp_smoke_config(src_config: Path, *, run_id: str, run_root: Path) -> Path:
    payload = load_yaml(src_config)
    payload['run']['run_id'] = run_id
    payload['run']['run_root'] = str(run_root)
    payload['run']['overwrite'] = True
    for stage in ['forecats', 'fit', 'post', 'validate', 'report']:
        payload['stages'][stage] = False
    payload['stages']['data_prep_shared'] = True
    tmp = run_root / f'{run_id}.yaml'
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(yaml.safe_dump(payload, sort_keys=False), encoding='utf-8')
    return tmp


def _target_knobs(payload: dict[str, Any], family: str) -> tuple[Any, Any]:
    if family.startswith('ndlm_main'):
        fc = (((payload.get('models') or {}).get('ndlm_main') or {}).get('prior') or {}).get('forecast_cov') or {}
        return fc.get('c_factor'), fc.get('epsilon')
    fc = (((payload.get('fit') or {}).get('exdqlm_multivar') or {}).get('legacy') or {}).get('forecast_cov') or {}
    return fc.get('c_factor'), fc.get('epsilon')


def main() -> int:
    ap = argparse.ArgumentParser(description='Validate featurecov cf1 epsilon sweep scaffolding without launching.')
    ap.add_argument('--config', required=True)
    ap.add_argument('--outdir')
    args = ap.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config).resolve()
    cfg = load_yaml(config_path)

    artifact_root = Path(cfg['campaign']['artifact_root']).resolve()
    default_outdir = artifact_root / 'control' / f"prelaunch_validation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    outdir = Path(args.outdir).resolve() if args.outdir else default_outdir
    outdir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        'config': str(config_path),
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'checks': {},
        'smoke_runs': [],
    }

    detclim = cfg.get('inputs', {}).get('deterministic_climate', {})
    handoff_root = Path(detclim.get('handoff_root', '')).resolve()
    assert_true(detclim.get('enabled') is True, 'deterministic climate must be enabled')
    assert_true(handoff_root.exists(), f'handoff_root missing: {handoff_root}')
    assert_true((handoff_root / 'handoff_meta.json').exists(), 'handoff_meta.json missing')
    covfeat = cfg.get('inputs', {}).get('covariate_features', {})
    tf_covs = cfg.get('inputs', {}).get('transfer_function_covariates', {})
    assert_true(covfeat.get('enabled') is True, 'covariate_features must be enabled')
    assert_true(covfeat.get('lag_orders') == [1, 2, 3], 'lag_orders must be [1,2,3]')
    assert_true(covfeat.get('include_squares') is True, 'include_squares must be true')
    assert_true(covfeat.get('include_interaction') is True, 'include_interaction must be true')
    assert_true(tf_covs.get('base_covariates') == ['PPT', 'SOIL', 'PCA'], 'unexpected base transfer covariates')
    assert_true(tf_covs.get('engineered_terms') == EXPECTED_FEATURE_COLUMNS[3:], 'unexpected engineered transfer covariates')
    summary['checks']['config_sanity'] = 'passed'

    build = run(['python3', 'scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py', '--config', str(config_path)], cwd=ROOT)
    (outdir / 'build_stdout.log').write_text(build.stdout, encoding='utf-8')
    (outdir / 'build_stderr.log').write_text(build.stderr, encoding='utf-8')
    assert_true(build.returncode == 0, f'builder failed: {build.stderr}')
    build_info = parse_builder_stdout(build.stdout)
    matrix_dir = Path(build_info['matrix_dir']).resolve()
    config_output_dir = Path(build_info['config_output_dir']).resolve()
    assert_true(int(build_info['generated_configs']) == 180, 'unexpected generated config count')
    assert_true(int(build_info['plan_rows']) == 180, 'unexpected plan row count')
    summary['checks']['builder'] = build_info

    plan_rows = list(csv.DictReader((matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8')))
    selection_rows = list(csv.DictReader((matrix_dir / 'selection_summary.csv').open('r', encoding='utf-8')))
    assert_true(len(plan_rows) == 180, 'matrix_plan row count mismatch')
    assert_true(len(selection_rows) == 180, 'selection_summary row count mismatch')
    family_counts = Counter(r['lane'] for r in plan_rows)
    cutoff_counts = Counter(r['cutoff'] for r in plan_rows)
    epsilon_counts = Counter(r['epsilon'] for r in plan_rows)
    for family in EXPECTED_FAMILIES:
        assert_true(family_counts[family] == 30, f'unexpected family count for {family}: {family_counts[family]}')
    for cutoff in EXPECTED_CUTOFFS:
        assert_true(cutoff_counts[cutoff] == 36, f'unexpected cutoff count for {cutoff}: {cutoff_counts[cutoff]}')
    for epsilon in EXPECTED_EPSILONS:
        assert_true(epsilon_counts[epsilon] == 30, f'unexpected epsilon count for {epsilon}: {epsilon_counts[epsilon]}')

    configs = sorted(config_output_dir.glob('*.yaml'))
    assert_true(len(configs) == 180, 'config output dir does not contain 180 yaml files')
    plan_by_run_id = {row['run_id']: row for row in plan_rows}
    for path in configs:
        payload = load_yaml(path)
        run_id = payload['run']['run_id']
        row = plan_by_run_id[run_id]
        family = row['family_id']
        covs = payload['inputs']['fit']['covariates']
        names = [item['name'] for item in covs]
        assert_true(names == ['PPT', 'SOIL', 'PCA'], f'{path.name}: unexpected covariates {names}')
        assert_true(payload['inputs']['covariate_features']['lag_orders'] == [1, 2, 3], f'{path.name}: lag orders mismatch')
        assert_true(payload['inputs']['covariate_features']['include_squares'] is True, f'{path.name}: squares disabled')
        assert_true(payload['inputs']['covariate_features']['include_interaction'] is True, f'{path.name}: interaction disabled')
        assert_true(payload['inputs']['deterministic_climate']['handoff_root'] == str(handoff_root), f'{path.name}: handoff_root mismatch')
        assert_true(payload['fit']['parallel']['mode'] == 'global_models', f'{path.name}: fit.parallel.mode must be global_models')
        expected_workers = EXPECTED_FIT_WORKERS_BY_FAMILY[family]
        assert_true(int(payload['run']['threads']['mc_cores']) == expected_workers, f'{path.name}: mc_cores must be {expected_workers}')
        assert_true(int(payload['fit']['parallel']['workers']) == expected_workers, f'{path.name}: fit.parallel.workers must be {expected_workers}')
        active = {
            'run_exdqlm_multivar': bool(payload['models']['run_exdqlm_multivar']),
            'run_exdqlm_univar': bool(payload['models']['run_exdqlm_univar']),
            'run_ndlm_main': bool(payload['models']['run_ndlm_main']),
            'run_ndlm_univar': bool(payload['models']['run_ndlm_univar']),
        }
        assert_true(sum(1 for v in active.values() if v) == 1, f'{path.name}: expected exactly one active family, saw {active}')
        c_factor, epsilon_value = _target_knobs(payload, family)
        assert_true(float(c_factor) == 1.0, f'{path.name}: target c_factor must be 1.0, got {c_factor}')
        assert_true(float(epsilon_value) == float(row['target_epsilon']), f"{path.name}: target epsilon mismatch {epsilon_value} != {row['target_epsilon']}")
        dbg = payload.get('debug_featurecov_cf1_eps_campaign', {})
        assert_true(dbg.get('transfer_function_covariates', {}).get('base_covariates') == ['PPT', 'SOIL', 'PCA'], f'{path.name}: debug transfer covariates missing')
        assert_true(dbg.get('transfer_function_covariates', {}).get('engineered_terms') == EXPECTED_FEATURE_COLUMNS[3:], f'{path.name}: debug engineered terms mismatch')

    reuse_manifest_path = matrix_dir / 'reuse_manifest.csv'
    if reuse_manifest_path.exists() and reuse_manifest_path.stat().st_size > 0:
        reuse_rows = list(csv.DictReader(reuse_manifest_path.open('r', encoding='utf-8')))
        for row in reuse_rows:
            manifest_path = artifact_root / 'runs' / row['run_id'] / 'run_manifest.yaml'
            assert_true(manifest_path.exists(), f"reused row missing synthetic manifest: {row['run_id']}")
            manifest = load_yaml(manifest_path)
            report_status = (((manifest.get('stages') or {}).get('report') or {}).get('status'))
            assert_true(str(report_status).lower() == 'pass', f"reused row manifest is not pass: {row['run_id']}")
        summary['checks']['reuse_rows'] = {'count': len(reuse_rows)}
    else:
        summary['checks']['reuse_rows'] = {'count': 0}

    test_cmds = [
        ['python3', '-m', 'unittest', 'tests.python.test_multimodel_v8_featurecov_cf1_eps_tooling', 'tests.python.test_deterministic_climate_handoff_workflow'],
        ['Rscript', '-e', 'testthat::test_file("tests/testthat/test_detclim_blend_contract.R"); testthat::test_file("tests/testthat/test_covariate_feature_engineering.R")'],
    ]
    test_results = []
    for idx, cmd in enumerate(test_cmds, start=1):
        proc = run(cmd, cwd=ROOT)
        (outdir / f'test_{idx}.stdout.log').write_text(proc.stdout, encoding='utf-8')
        (outdir / f'test_{idx}.stderr.log').write_text(proc.stderr, encoding='utf-8')
        assert_true(proc.returncode == 0, f'test command failed: {cmd}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        test_results.append({'cmd': cmd, 'returncode': proc.returncode})
    summary['checks']['unit_tests'] = test_results

    smoke_root = outdir / 'smoke_runs'
    smoke_root.mkdir(parents=True, exist_ok=True)
    first_by_family: dict[str, dict[str, str]] = {}
    for row in plan_rows:
        if row['lane'] not in first_by_family:
            first_by_family[row['lane']] = row
    for family in EXPECTED_FAMILIES:
        row = first_by_family[family]
        src_cfg = Path(row['config_path'])
        run_id = f'smoke_{family}'
        run_root = smoke_root / family
        shutil.rmtree(run_root, ignore_errors=True)
        smoke_cfg = write_temp_smoke_config(src_cfg, run_id=run_id, run_root=run_root)
        proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(smoke_cfg)], cwd=ROOT)
        (outdir / f'{family}.stdout.log').write_text(proc.stdout, encoding='utf-8')
        (outdir / f'{family}.stderr.log').write_text(proc.stderr, encoding='utf-8')
        assert_true(proc.returncode == 0, f'smoke failed for {family}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        shared_root = run_root / run_id / 'inputs' / 'shared'
        feature_path = shared_root / 'covariates' / 'covariate_features.csv'
        assert_true(feature_path.exists(), f'{family}: missing engineered covariate features')
        feature_rows = list(csv.DictReader(feature_path.open('r', encoding='utf-8')))
        assert_true(len(feature_rows) > 0, f'{family}: covariate_features.csv is empty')
        observed_cols = list(feature_rows[0].keys())
        assert_true(observed_cols == ['date'] + EXPECTED_FEATURE_COLUMNS, f'{family}: unexpected engineered feature columns {observed_cols}')
        assert_true((shared_root / 'deterministic_climate' / 'deterministic_climate_summary.txt').exists(), f'{family}: missing detclim summary')
        summary['smoke_runs'].append({'family': family, 'config': str(src_cfg), 'shared_root': str(shared_root)})
    summary['checks']['smoke_runs'] = {'count': len(summary['smoke_runs'])}

    summary_path = outdir / 'prelaunch_validation_summary.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    md_lines = [
        '# Featurecov CF1 Epsilon Sweep Prelaunch Validation',
        '',
        f'- config: `{config_path}`',
        f'- timestamp_utc: `{summary["timestamp_utc"]}`',
        '',
        '## Result',
        '',
        '- status: `passed`',
        '- launch_state: `not launched by this validation`',
        '',
        '## Checks',
        '',
        f'- generated configs: `{build_info["generated_configs"]}`',
        f'- matrix rows: `{build_info["plan_rows"]}`',
        f'- reused rows: `{summary["checks"]["reuse_rows"]["count"]}`',
        f'- smoke runs: `{summary["checks"]["smoke_runs"]["count"]}`',
        '',
        '## Transfer-function covariates',
        '',
        '- base: `PPT`, `SOIL`, `PCA`',
        '- engineered: `PPT_sq`, `SOIL_sq`, `PPT_x_SOIL`, `PPT_lag1..3`, `SOIL_lag1..3`',
        '',
        '## Families smoke-tested',
        '',
    ]
    for row in summary['smoke_runs']:
        md_lines.append(f"- `{row['family']}` via `{Path(row['config']).name}`")
    md_lines.append('')
    md_lines.append(f'- summary_json: `{summary_path}`')
    (outdir / 'prelaunch_validation_summary.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')

    print(f'validation_outdir={outdir}')
    print(f'summary_json={summary_path}')
    print('status=passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
