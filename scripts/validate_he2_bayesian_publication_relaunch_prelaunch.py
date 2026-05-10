#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from he2_publication_relaunch_lib import EXPECTED_CUTOFFS, EXPECTED_FAMILY_ORDER, canonical_shared_paths

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def parse_builder_stdout(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            if k.strip() in {'artifact_root', 'matrix_dir', 'config_output_dir', 'generated_configs', 'plan_rows', 'selection_rows'}:
                out[k.strip()] = v.strip()
    return out


def write_temp_smoke_config(src_config: Path, *, run_id: str, run_root: Path, stage_mode: str = 'data_prep_shared') -> Path:
    payload = load_yaml(src_config)
    payload['run']['run_id'] = run_id
    payload['run']['run_root'] = str(run_root)
    payload['run']['overwrite'] = True
    payload['run']['auto_suffix_on_collision'] = True
    for stage in ['forecats', 'fit', 'post', 'validate', 'report']:
        payload['stages'][stage] = False
    payload['stages']['data_prep_shared'] = True
    if stage_mode == 'fit':
        payload['stages']['fit'] = True
    elif stage_mode != 'data_prep_shared':
        raise ValueError(f'Unknown stage_mode: {stage_mode}')
    tmp = run_root / f'{run_id}.yaml'
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(yaml.safe_dump(payload, sort_keys=False), encoding='utf-8')
    return tmp


def _bundle_build(config_path: Path) -> subprocess.CompletedProcess[str]:
    cfg = load_yaml(config_path)
    bundles = cfg['bundles']
    cmd = [
        'python3', 'scripts/build_multimodel_v8_histfix_bundles.py',
        '--artifact-root', str(bundles['artifact_root']),
        '--bundle-run-id', str(bundles['bundle_run_id']),
        '--data-start', str(bundles['data_start']),
        '--cutoffs', *[str(x) for x in bundles['cutoffs']],
    ]
    return run(cmd, cwd=ROOT)


def _validate_data_start_filter(path: Path, cutoff: str) -> None:
    assert_true(path.exists(), f'missing data_start_filter_summary: {path}')
    text = path.read_text(encoding='utf-8')
    assert_true('data_start=1987-05-29' in text, f'{cutoff}: data_start not pinned in {path}')
    assert_true('common_date_min=1987-05-29' in text, f'{cutoff}: common_date_min not restored in {path}')


def _validate_legacy_log_ready_retros(path: Path, cutoff: str) -> None:
    assert_true(path.exists(), f'{cutoff}: missing retros bundle {path}')
    rows = list(csv.DictReader(path.open('r', encoding='utf-8')))
    assert_true(bool(rows), f'{cutoff}: empty retros bundle {path}')
    for col in ['USGS', 'GloFAS', 'NWS3.0']:
        bad = []
        for row in rows:
            try:
                value = float(row[col])
            except Exception:
                bad.append((row.get('Date', ''), row.get(col, '')))
                continue
            if not (value > 0.0):
                bad.append((row.get('Date', ''), value))
            if len(bad) >= 5:
                break
        assert_true(
            not bad,
            f'{cutoff}: retros column {col} is not legacy-log-ready (>0 required). First problematic rows: {bad}',
        )


def main() -> int:
    ap = argparse.ArgumentParser(description='Validate the unified HE2 Bayesian publication relaunch before queue launch.')
    ap.add_argument('--config', required=True)
    ap.add_argument('--outdir')
    args = ap.parse_args()

    config_path = Path(args.config).resolve() if Path(args.config).is_absolute() else (ROOT / args.config).resolve()
    cfg = load_yaml(config_path)
    campaign = cfg['campaign']
    bundles = cfg['bundles']
    validation_cfg = cfg.get('validation', {})

    artifact_root = Path(campaign['artifact_root']).resolve()
    default_outdir = artifact_root / 'control' / f"prelaunch_validation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    outdir = Path(args.outdir).resolve() if args.outdir else default_outdir
    outdir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        'config': str(config_path),
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'checks': {},
        'smoke_runs': [],
    }

    bundle_build = _bundle_build(config_path)
    (outdir / 'bundle_build.stdout.log').write_text(bundle_build.stdout, encoding='utf-8')
    (outdir / 'bundle_build.stderr.log').write_text(bundle_build.stderr, encoding='utf-8')
    assert_true(bundle_build.returncode == 0, f'bundle build failed: {bundle_build.stderr}')
    summary['checks']['bundle_build'] = 'passed'

    for cutoff in bundles['cutoffs']:
        shared = canonical_shared_paths(bundles['artifact_root'], cutoff, bundles['bundle_run_id'])
        for key, path in shared.items():
            if key == 'bundle_root':
                continue
            assert_true(path.exists(), f'{cutoff}: missing canonical shared path {key}: {path}')
        retros = list(csv.DictReader(shared['retros'].open('r', encoding='utf-8')))
        assert_true(retros[0]['Date'] == '1987-05-29', f'{cutoff}: retros start mismatch')
        assert_true(retros[-1]['Date'] == cutoff[:4] + '-' + cutoff[4:6] + '-' + cutoff[6:], f'{cutoff}: retros end mismatch')
        _validate_legacy_log_ready_retros(shared['retros'], cutoff)
    summary['checks']['bundles_present'] = {'cutoffs': list(bundles['cutoffs'])}

    build = run(['python3', 'scripts/build_he2_bayesian_publication_relaunch_configs.py', '--config', str(config_path)], cwd=ROOT)
    (outdir / 'build.stdout.log').write_text(build.stdout, encoding='utf-8')
    (outdir / 'build.stderr.log').write_text(build.stderr, encoding='utf-8')
    assert_true(build.returncode == 0, f'builder failed: {build.stderr}')
    build_info = parse_builder_stdout(build.stdout)
    matrix_dir = Path(build_info['matrix_dir']).resolve()
    config_output_dir = Path(build_info['config_output_dir']).resolve()
    assert_true(int(build_info['generated_configs']) == 45, 'unexpected generated config count')
    assert_true(int(build_info['plan_rows']) == 45, 'unexpected plan row count')
    summary['checks']['builder'] = build_info

    plan_rows = list(csv.DictReader((matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8')))
    selection_rows = list(csv.DictReader((matrix_dir / 'selection_summary.csv').open('r', encoding='utf-8')))
    assert_true(len(plan_rows) == 45, 'matrix plan size mismatch')
    assert_true(len(selection_rows) == 45, 'selection summary size mismatch')
    family_counts = Counter(row['family_id'] for row in plan_rows)
    cutoff_counts = Counter(row['cutoff'] for row in plan_rows)
    for family in EXPECTED_FAMILY_ORDER:
        assert_true(family_counts[family] == 5, f'unexpected family count for {family}: {family_counts[family]}')
    for cutoff in EXPECTED_CUTOFFS:
        assert_true(cutoff_counts[cutoff] == 9, f'unexpected cutoff count for {cutoff}: {cutoff_counts[cutoff]}')

    configs = sorted(config_output_dir.glob('*.yaml'))

    expected_config_paths = [Path(row['config_path']).resolve() for row in plan_rows]
    for path in expected_config_paths:
        assert_true(path.exists(), f'missing generated config referenced by matrix plan: {path}')

    by_cutoff: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in expected_config_paths:
        payload = load_yaml(path)
        cutoff = str(payload['dates']['cutoff_date']).replace('-', '')
        by_cutoff[cutoff].append({'path': path, 'payload': payload})
        names = [row['name'] for row in payload['inputs']['fit']['covariates']]
        assert_true(names == ['PPT', 'SOIL', 'PCA'], f'{path.name}: covariates mismatch {names}')

    for cutoff in EXPECTED_CUTOFFS:
        rows = by_cutoff[cutoff]
        assert_true(len(rows) == 9, f'{cutoff}: expected 9 configs, found {len(rows)}')
        same_fields = [
            ('parameters', lambda p: p['inputs']['fit']['parameters_path']),
            ('retros', lambda p: p['inputs']['fit']['retros_path']),
            ('nws_forecast', lambda p: p['inputs']['fit']['nws_forecast_path']),
            ('glofas_forecast', lambda p: p['inputs']['fit']['glofas_forecast_path']),
            ('bundle_meta', lambda p: p['inputs']['forecats']['existing_bundle_path']),
            ('handoff_root', lambda p: p['inputs']['deterministic_climate']['handoff_root']),
            ('lag_orders', lambda p: json.dumps(p['inputs']['covariate_features']['lag_orders'])),
            ('include_squares', lambda p: str(p['inputs']['covariate_features']['include_squares'])),
            ('include_interaction', lambda p: str(p['inputs']['covariate_features']['include_interaction'])),
        ]
        for field_name, getter in same_fields:
            values = {getter(row['payload']) for row in rows}
            assert_true(len(values) == 1, f'{cutoff}: field {field_name} is not identical across rows: {sorted(values)}')
        cov_paths = defaultdict(set)
        for row in rows:
            for cov in row['payload']['inputs']['fit']['covariates']:
                cov_paths[cov['name']].add(cov['path'])
        for cov_name, values in cov_paths.items():
            assert_true(len(values) == 1, f'{cutoff}: covariate {cov_name} not identical across rows: {sorted(values)}')
    summary['checks']['within_cutoff_bundle_alignment'] = 'passed'

    test_cmds = [
        ['python3', '-m', 'py_compile', 'scripts/he2_publication_relaunch_lib.py', 'scripts/build_he2_bayesian_publication_relaunch_configs.py', 'scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py', 'scripts/launch_he2_bayesian_publication_relaunch.py', 'scripts/build_he2_bayesian_full_relaunch_tracker.py'],
        ['python3', '-m', 'unittest',
         'tests.python.test_canonical_gdpc_master_builder',
         'tests.python.test_multimodel_v8_histfix_bundles_gdpc_alias',
         'tests.python.test_he2_publication_relaunch_lib',
         'tests.python.test_he2_publication_relaunch_template'],
    ]
    test_results = []
    for idx, cmd in enumerate(test_cmds, start=1):
        proc = run(cmd, cwd=ROOT)
        (outdir / f'test_{idx}.stdout.log').write_text(proc.stdout, encoding='utf-8')
        (outdir / f'test_{idx}.stderr.log').write_text(proc.stderr, encoding='utf-8')
        assert_true(proc.returncode == 0, f'test command failed: {cmd}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        test_results.append({'cmd': cmd, 'returncode': proc.returncode})
    summary['checks']['tests'] = test_results

    smoke_root = outdir / 'smoke_runs'
    smoke_root.mkdir(parents=True, exist_ok=True)
    first_by_family: dict[str, dict[str, str]] = {}
    for row in plan_rows:
        if row['cutoff'] == str(validation_cfg.get('family_smoke_cutoff', '20210123')) and row['family_id'] not in first_by_family:
            first_by_family[row['family_id']] = row
    for family in EXPECTED_FAMILY_ORDER:
        row = first_by_family[family]
        src_cfg = Path(row['config_path'])
        run_id = f'smoke_family_{family}'
        run_root = smoke_root / family
        shutil.rmtree(run_root, ignore_errors=True)
        smoke_cfg = write_temp_smoke_config(src_cfg, run_id=run_id, run_root=run_root)
        proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(smoke_cfg)], cwd=ROOT)
        (outdir / f'{family}.stdout.log').write_text(proc.stdout, encoding='utf-8')
        (outdir / f'{family}.stderr.log').write_text(proc.stderr, encoding='utf-8')
        assert_true(proc.returncode == 0, f'family smoke failed for {family}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        shared_root = run_root / run_id / 'inputs' / 'shared'
        assert_true((shared_root / 'covariates' / 'covariate_features.csv').exists(), f'{family}: missing covariate_features.csv')
        _validate_data_start_filter(shared_root / 'data_start_filter_summary.txt', row['cutoff'])
        summary['smoke_runs'].append({'scope': 'family', 'family': family, 'cutoff': row['cutoff'], 'shared_root': str(shared_root)})

    cutoff_family = str(validation_cfg.get('cutoff_smoke_family', 'exdqlm_multivar_keep'))
    by_cutoff_family = {}
    for row in plan_rows:
        if row['family_id'] == cutoff_family:
            by_cutoff_family[row['cutoff']] = row
    for cutoff in EXPECTED_CUTOFFS:
        row = by_cutoff_family[cutoff]
        src_cfg = Path(row['config_path'])
        run_id = f'smoke_cutoff_{cutoff}'
        run_root = smoke_root / cutoff
        shutil.rmtree(run_root, ignore_errors=True)
        smoke_cfg = write_temp_smoke_config(src_cfg, run_id=run_id, run_root=run_root)
        proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(smoke_cfg)], cwd=ROOT)
        (outdir / f'{cutoff}.stdout.log').write_text(proc.stdout, encoding='utf-8')
        (outdir / f'{cutoff}.stderr.log').write_text(proc.stderr, encoding='utf-8')
        assert_true(proc.returncode == 0, f'cutoff smoke failed for {cutoff}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        shared_root = run_root / run_id / 'inputs' / 'shared'
        assert_true((shared_root / 'covariates' / 'covariate_features.csv').exists(), f'{cutoff}: missing covariate_features.csv')
        _validate_data_start_filter(shared_root / 'data_start_filter_summary.txt', cutoff)
        summary['smoke_runs'].append({'scope': 'cutoff', 'family': cutoff_family, 'cutoff': cutoff, 'shared_root': str(shared_root)})

    fit_smoke_family = str(validation_cfg.get('fit_smoke_family', 'ndlm_univar_keep'))
    fit_smoke_cutoff = str(validation_cfg.get('fit_smoke_cutoff', '20210123'))
    fit_row = next(
        row for row in plan_rows
        if row['family_id'] == fit_smoke_family and row['cutoff'] == fit_smoke_cutoff
    )
    fit_cfg_src = Path(fit_row['config_path'])
    fit_run_id = f'fit_smoke_{fit_smoke_family}_{fit_smoke_cutoff}'
    fit_run_root = smoke_root / 'fit' / fit_smoke_family / fit_smoke_cutoff
    shutil.rmtree(fit_run_root, ignore_errors=True)
    fit_smoke_cfg = write_temp_smoke_config(
        fit_cfg_src,
        run_id=fit_run_id,
        run_root=fit_run_root,
        stage_mode='fit',
    )
    fit_proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(fit_smoke_cfg)], cwd=ROOT)
    (outdir / f'fit_smoke_{fit_smoke_family}_{fit_smoke_cutoff}.stdout.log').write_text(fit_proc.stdout, encoding='utf-8')
    (outdir / f'fit_smoke_{fit_smoke_family}_{fit_smoke_cutoff}.stderr.log').write_text(fit_proc.stderr, encoding='utf-8')
    assert_true(
        fit_proc.returncode == 0,
        f'fit smoke failed for family={fit_smoke_family} cutoff={fit_smoke_cutoff}\nSTDOUT:\n{fit_proc.stdout}\nSTDERR:\n{fit_proc.stderr}',
    )
    summary['smoke_runs'].append({
        'scope': 'fit',
        'family': fit_smoke_family,
        'cutoff': fit_smoke_cutoff,
        'run_root': str(fit_run_root / fit_run_id),
    })
    summary['checks']['smoke_runs'] = {'count': len(summary['smoke_runs'])}

    summary_path = outdir / 'prelaunch_validation_summary.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    md_lines = [
        '# HE2 Bayesian Publication Relaunch Prelaunch Validation',
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
        '- canonical shared bundles: `passed`',
        f'- generated configs: `{build_info["generated_configs"]}`',
        '- within-cutoff shared bundle alignment: `passed`',
        f'- smoke runs: `{summary["checks"]["smoke_runs"]["count"]}`',
        '',
        '## Smoke coverage',
        '',
    ]
    for row in summary['smoke_runs']:
        md_lines.append(f"- `{row['scope']}` smoke: family=`{row['family']}` cutoff=`{row['cutoff']}`")
    md_lines.append('')
    md_lines.append(f'- summary_json: `{summary_path}`')
    (outdir / 'prelaunch_validation_summary.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')

    print(f'validation_outdir={outdir}')
    print(f'summary_json={summary_path}')
    print('status=passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
