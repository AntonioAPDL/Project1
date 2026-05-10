#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import csv
import json
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from he2_publication_relaunch_lib import canonical_shared_paths, model_class, parse_quantile_list

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def deep_merge_dict(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def parse_builder_stdout(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            if k.strip() in {'artifact_root', 'matrix_dir', 'config_output_dir', 'generated_configs', 'plan_rows', 'selection_rows'}:
                out[k.strip()] = v.strip()
    return out


def extend_builder_args(cmd: list[str], args: argparse.Namespace) -> list[str]:
    for flag, values in [
        ('--cutoffs', args.cutoffs),
        ('--families', args.families),
        ('--manuscript-labels', args.manuscript_labels),
        ('--run-ids', args.run_ids),
        ('--model-classes', args.model_classes),
        ('--quantiles', args.quantiles),
    ]:
        if values:
            cmd.extend([flag, *values])
    if args.batch_file:
        cmd.extend(['--batch-file', args.batch_file])
    if args.profile:
        cmd.extend(['--profile', args.profile])
    if args.fit_parallel_workers is not None:
        cmd.extend(['--fit-parallel-workers', str(args.fit_parallel_workers)])
    if args.mc_cores is not None:
        cmd.extend(['--mc-cores', str(args.mc_cores)])
    return cmd


def write_temp_smoke_config(
    src_config: Path,
    *,
    run_id: str,
    run_root: Path,
    stage_mode: str = 'data_prep_shared',
    quantile_subset: list[float] | None = None,
    fit_parallel_workers: int | None = None,
    mc_cores: int | None = None,
    fit_overrides: dict[str, Any] | None = None,
) -> Path:
    payload = load_yaml(src_config)
    payload['run']['run_id'] = run_id
    payload['run']['run_root'] = str(run_root)
    payload['run']['overwrite'] = True
    payload['run']['auto_suffix_on_collision'] = True
    if mc_cores is not None:
        payload['run'].setdefault('threads', {})
        payload['run']['threads']['mc_cores'] = int(mc_cores)
    for stage in ['forecats', 'fit', 'post', 'validate', 'report']:
        payload['stages'][stage] = False
    payload['stages']['data_prep_shared'] = True
    if stage_mode == 'fit':
        payload['stages']['fit'] = True
    elif stage_mode == 'full_pipeline':
        for stage in ['fit', 'post', 'validate', 'report']:
            payload['stages'][stage] = True
    elif stage_mode != 'data_prep_shared':
        raise ValueError(f'Unknown stage_mode: {stage_mode}')
    if fit_overrides:
        payload.setdefault('fit', {})
        payload['fit'] = deep_merge_dict(payload['fit'], fit_overrides)
    if quantile_subset:
        payload.setdefault('fit', {})
        payload['fit']['quantiles'] = [float(q) for q in quantile_subset]
        payload['fit'].setdefault('parallel', {})
        payload['fit']['parallel']['workers'] = int(fit_parallel_workers or 1)
    elif fit_parallel_workers is not None:
        payload.setdefault('fit', {})
        payload['fit'].setdefault('parallel', {})
        payload['fit']['parallel']['workers'] = int(fit_parallel_workers)
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
        assert_true(not bad, f'{cutoff}: retros column {col} is not legacy-log-ready (>0 required). First problematic rows: {bad}')


def _validate_full_pipeline_run(run_dir: Path, label: str) -> None:
    manifest = load_yaml(run_dir / 'run_manifest.yaml')
    stages = manifest.get('stages', {}) if isinstance(manifest, dict) else {}
    assert_true((stages.get('report') or {}).get('status') == 'pass', f'{label}: report stage did not pass')
    assert_true((run_dir / 'report' / 'summary.json').exists(), f'{label}: missing report summary.json')
    assert_true((run_dir / 'report' / 'summary.md').exists(), f'{label}: missing report summary.md')
    assert_true((run_dir / 'validate' / 'compare_report.json').exists(), f'{label}: missing validate compare_report.json')
    assert_true((run_dir / 'post' / 'outputs').exists(), f'{label}: missing post outputs directory')


def _pick_row(plan_rows: list[dict[str, str]], *, family: str | None = None, cutoff: str | None = None, class_name: str | None = None) -> dict[str, str]:
    candidates = []
    for row in plan_rows:
        if family and row['family_id'] != family:
            continue
        if cutoff and row['cutoff'] != cutoff:
            continue
        if class_name and row['model_class'] != class_name:
            continue
        candidates.append(row)
    if not candidates:
        raise LookupError(f'No row available for family={family} cutoff={cutoff} model_class={class_name}')
    return candidates[0]


def main() -> int:
    ap = argparse.ArgumentParser(description='Validate the unified HE2 Bayesian publication relaunch before queue launch.')
    ap.add_argument('--config', required=True)
    ap.add_argument('--outdir')
    ap.add_argument('--cutoffs', nargs='*')
    ap.add_argument('--families', nargs='*')
    ap.add_argument('--manuscript-labels', nargs='*')
    ap.add_argument('--run-ids', nargs='*')
    ap.add_argument('--model-classes', nargs='*')
    ap.add_argument('--quantiles', nargs='*')
    ap.add_argument('--batch-file')
    ap.add_argument('--profile')
    ap.add_argument('--fit-parallel-workers', type=int)
    ap.add_argument('--mc-cores', type=int)
    args = ap.parse_args()

    config_path = Path(args.config).resolve() if Path(args.config).is_absolute() else (ROOT / args.config).resolve()
    cfg = load_yaml(config_path)
    campaign = cfg['campaign']
    bundles = cfg['bundles']
    validation_cfg = cfg.get('validation', {})
    smoke_fit_overrides = validation_cfg.get('smoke_fit_overrides') or {}

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

    build_cmd = ['python3', 'scripts/build_he2_bayesian_publication_relaunch_configs.py', '--config', str(config_path)]
    build = run(extend_builder_args(build_cmd, args), cwd=ROOT)
    (outdir / 'build.stdout.log').write_text(build.stdout, encoding='utf-8')
    (outdir / 'build.stderr.log').write_text(build.stderr, encoding='utf-8')
    assert_true(build.returncode == 0, f'builder failed: {build.stderr}')
    build_info = parse_builder_stdout(build.stdout)
    matrix_dir = Path(build_info['matrix_dir']).resolve()
    config_output_dir = Path(build_info['config_output_dir']).resolve()
    summary['checks']['builder'] = build_info

    plan_rows = list(csv.DictReader((matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8')))
    selection_rows = list(csv.DictReader((matrix_dir / 'selection_summary.csv').open('r', encoding='utf-8')))
    assert_true(len(plan_rows) == int(build_info['plan_rows']), 'matrix plan size mismatch')
    assert_true(len(selection_rows) == int(build_info['selection_rows']), 'selection summary size mismatch')
    assert_true(len(plan_rows) > 0, 'no selected rows after builder')

    selected_families = sorted({row['family_id'] for row in plan_rows})
    selected_cutoffs = sorted({row['cutoff'] for row in plan_rows})
    family_counts = Counter(row['family_id'] for row in plan_rows)
    cutoff_counts = Counter(row['cutoff'] for row in plan_rows)
    summary['checks']['selected_scope'] = {
        'rows': len(plan_rows),
        'families': selected_families,
        'cutoffs': selected_cutoffs,
        'family_counts': dict(family_counts),
        'cutoff_counts': dict(cutoff_counts),
    }

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

    for cutoff in selected_cutoffs:
        rows = by_cutoff[cutoff]
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
            assert_true(len(values) == 1, f'{cutoff}: field {field_name} is not identical across selected rows: {sorted(values)}')
        cov_paths = defaultdict(set)
        for row in rows:
            for cov in row['payload']['inputs']['fit']['covariates']:
                cov_paths[cov['name']].add(cov['path'])
        for cov_name, values in cov_paths.items():
            assert_true(len(values) == 1, f'{cutoff}: covariate {cov_name} not identical across selected rows: {sorted(values)}')
    summary['checks']['within_cutoff_bundle_alignment'] = 'passed'

    for required in ['frozen_spec_manifest.csv', 'cutoff_bundle_audit.csv', 'batch_request_snapshot.yaml']:
        assert_true((matrix_dir / required).exists(), f'missing builder audit output: {required}')
    summary['checks']['builder_audits'] = 'passed'

    test_cmds = [
        ['python3', '-m', 'py_compile',
         'scripts/he2_publication_relaunch_lib.py',
         'scripts/build_he2_bayesian_publication_relaunch_configs.py',
         'scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py',
         'scripts/launch_he2_bayesian_publication_relaunch.py',
         'scripts/reset_he2_bayesian_publication_relaunch_state.py',
         'scripts/build_he2_bayesian_full_relaunch_tracker.py'],
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

    family_smoke_cutoff = str(validation_cfg.get('family_smoke_cutoff', selected_cutoffs[0]))
    first_by_family: dict[str, dict[str, str]] = {}
    for row in plan_rows:
        if row['cutoff'] == family_smoke_cutoff and row['family_id'] not in first_by_family:
            first_by_family[row['family_id']] = row
    for family in selected_families:
        row = first_by_family.get(family) or _pick_row(plan_rows, family=family)
        src_cfg = Path(row['config_path'])
        run_id = f'smoke_family_{family}'
        run_root = smoke_root / 'family' / family
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

    cutoff_family_pref = str(validation_cfg.get('cutoff_smoke_family', 'exdqlm_multivar_keep'))
    for cutoff in selected_cutoffs:
        try:
            row = _pick_row(plan_rows, family=cutoff_family_pref, cutoff=cutoff)
        except LookupError:
            row = _pick_row(plan_rows, cutoff=cutoff)
        src_cfg = Path(row['config_path'])
        run_id = f'smoke_cutoff_{cutoff}'
        run_root = smoke_root / 'cutoff' / cutoff
        shutil.rmtree(run_root, ignore_errors=True)
        smoke_cfg = write_temp_smoke_config(src_cfg, run_id=run_id, run_root=run_root)
        proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(smoke_cfg)], cwd=ROOT)
        (outdir / f'{cutoff}.stdout.log').write_text(proc.stdout, encoding='utf-8')
        (outdir / f'{cutoff}.stderr.log').write_text(proc.stderr, encoding='utf-8')
        assert_true(proc.returncode == 0, f'cutoff smoke failed for {cutoff}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        shared_root = run_root / run_id / 'inputs' / 'shared'
        assert_true((shared_root / 'covariates' / 'covariate_features.csv').exists(), f'{cutoff}: missing covariate_features.csv')
        _validate_data_start_filter(shared_root / 'data_start_filter_summary.txt', cutoff)
        summary['smoke_runs'].append({'scope': 'cutoff', 'family': row['family_id'], 'cutoff': cutoff, 'shared_root': str(shared_root)})

    fit_smoke_row = _pick_row(
        plan_rows,
        family=str(validation_cfg.get('fit_smoke_family', 'ndlm_univar_keep')) if any(r['family_id'] == str(validation_cfg.get('fit_smoke_family', 'ndlm_univar_keep')) for r in plan_rows) else None,
        cutoff=str(validation_cfg.get('fit_smoke_cutoff', selected_cutoffs[0])) if any(r['cutoff'] == str(validation_cfg.get('fit_smoke_cutoff', selected_cutoffs[0])) and r['family_id'] == str(validation_cfg.get('fit_smoke_family', 'ndlm_univar_keep')) for r in plan_rows) else None,
        class_name='ndlm',
    )
    fit_cfg_src = Path(fit_smoke_row['config_path'])
    fit_run_id = f'fit_smoke_{fit_smoke_row["family_id"]}_{fit_smoke_row["cutoff"]}'
    fit_run_root = smoke_root / 'fit' / fit_smoke_row['family_id'] / fit_smoke_row['cutoff']
    shutil.rmtree(fit_run_root, ignore_errors=True)
    fit_smoke_cfg = write_temp_smoke_config(
        fit_cfg_src,
        run_id=fit_run_id,
        run_root=fit_run_root,
        stage_mode='fit',
        fit_parallel_workers=1,
        mc_cores=1,
        fit_overrides=smoke_fit_overrides,
    )
    fit_proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(fit_smoke_cfg)], cwd=ROOT)
    (outdir / f'{fit_run_id}.stdout.log').write_text(fit_proc.stdout, encoding='utf-8')
    (outdir / f'{fit_run_id}.stderr.log').write_text(fit_proc.stderr, encoding='utf-8')
    assert_true(fit_proc.returncode == 0, f'fit smoke failed for family={fit_smoke_row["family_id"]} cutoff={fit_smoke_row["cutoff"]}\nSTDOUT:\n{fit_proc.stdout}\nSTDERR:\n{fit_proc.stderr}')
    summary['smoke_runs'].append({'scope': 'fit_ndlm', 'family': fit_smoke_row['family_id'], 'cutoff': fit_smoke_row['cutoff'], 'run_root': str(fit_run_root / fit_run_id)})

    quantile_pref = str(validation_cfg.get('quantile_fit_smoke_family', 'exdqlm_multivar_keep'))
    quantile_cutoff_pref = str(validation_cfg.get('quantile_fit_smoke_cutoff', selected_cutoffs[0]))
    quantile_fit_row = _pick_row(plan_rows, family=quantile_pref if any(r['family_id'] == quantile_pref for r in plan_rows) else None, cutoff=quantile_cutoff_pref if any(r['cutoff'] == quantile_cutoff_pref and r['family_id'] == quantile_pref for r in plan_rows) else None, class_name='quantile_multivariate')
    quantile_fit_subset = parse_quantile_list(validation_cfg.get('quantile_fit_smoke_quantiles') or [0.05])
    qfit_cfg_src = Path(quantile_fit_row['config_path'])
    qfit_run_id = f'fit_smoke_{quantile_fit_row["family_id"]}_{quantile_fit_row["cutoff"]}_qsubset'
    qfit_run_root = smoke_root / 'fit_quantile' / quantile_fit_row['family_id'] / quantile_fit_row['cutoff']
    shutil.rmtree(qfit_run_root, ignore_errors=True)
    qfit_smoke_cfg = write_temp_smoke_config(
        qfit_cfg_src,
        run_id=qfit_run_id,
        run_root=qfit_run_root,
        stage_mode='fit',
        quantile_subset=quantile_fit_subset,
        fit_parallel_workers=1,
        mc_cores=1,
        fit_overrides=smoke_fit_overrides,
    )
    qfit_proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(qfit_smoke_cfg)], cwd=ROOT)
    (outdir / f'{qfit_run_id}.stdout.log').write_text(qfit_proc.stdout, encoding='utf-8')
    (outdir / f'{qfit_run_id}.stderr.log').write_text(qfit_proc.stderr, encoding='utf-8')
    assert_true(qfit_proc.returncode == 0, f'quantile fit smoke failed for family={quantile_fit_row["family_id"]} cutoff={quantile_fit_row["cutoff"]}\nSTDOUT:\n{qfit_proc.stdout}\nSTDERR:\n{qfit_proc.stderr}')
    summary['smoke_runs'].append({'scope': 'fit_quantile', 'family': quantile_fit_row['family_id'], 'cutoff': quantile_fit_row['cutoff'], 'quantiles': quantile_fit_subset, 'run_root': str(qfit_run_root / qfit_run_id)})

    univar_quantile_pref = str(validation_cfg.get('univar_quantile_fit_smoke_family', 'exdqlm_univar'))
    univar_quantile_cutoff_pref = str(validation_cfg.get('univar_quantile_fit_smoke_cutoff', selected_cutoffs[0]))
    univar_quantile_fit_row = _pick_row(
        plan_rows,
        family=univar_quantile_pref if any(r['family_id'] == univar_quantile_pref for r in plan_rows) else None,
        cutoff=univar_quantile_cutoff_pref if any(r['cutoff'] == univar_quantile_cutoff_pref and r['family_id'] == univar_quantile_pref for r in plan_rows) else None,
        class_name='quantile_univariate',
    )
    univar_quantile_fit_subset = parse_quantile_list(validation_cfg.get('univar_quantile_fit_smoke_quantiles') or [0.05])
    uqfit_cfg_src = Path(univar_quantile_fit_row['config_path'])
    uqfit_run_id = f'fit_smoke_{univar_quantile_fit_row["family_id"]}_{univar_quantile_fit_row["cutoff"]}_qsubset'
    uqfit_run_root = smoke_root / 'fit_quantile_univar' / univar_quantile_fit_row['family_id'] / univar_quantile_fit_row['cutoff']
    shutil.rmtree(uqfit_run_root, ignore_errors=True)
    uqfit_smoke_cfg = write_temp_smoke_config(
        uqfit_cfg_src,
        run_id=uqfit_run_id,
        run_root=uqfit_run_root,
        stage_mode='fit',
        quantile_subset=univar_quantile_fit_subset,
        fit_parallel_workers=1,
        mc_cores=1,
        fit_overrides=smoke_fit_overrides,
    )
    uqfit_proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(uqfit_smoke_cfg)], cwd=ROOT)
    (outdir / f'{uqfit_run_id}.stdout.log').write_text(uqfit_proc.stdout, encoding='utf-8')
    (outdir / f'{uqfit_run_id}.stderr.log').write_text(uqfit_proc.stderr, encoding='utf-8')
    assert_true(
        uqfit_proc.returncode == 0,
        f'univariate quantile fit smoke failed for family={univar_quantile_fit_row["family_id"]} cutoff={univar_quantile_fit_row["cutoff"]}\nSTDOUT:\n{uqfit_proc.stdout}\nSTDERR:\n{uqfit_proc.stderr}',
    )
    summary['smoke_runs'].append({
        'scope': 'fit_quantile_univar',
        'family': univar_quantile_fit_row['family_id'],
        'cutoff': univar_quantile_fit_row['cutoff'],
        'quantiles': univar_quantile_fit_subset,
        'run_root': str(uqfit_run_root / uqfit_run_id),
    })

    full_ndlm_family = str(validation_cfg.get('full_pipeline_ndlm_family', fit_smoke_row['family_id']))
    full_ndlm_cutoff = str(validation_cfg.get('full_pipeline_ndlm_cutoff', fit_smoke_row['cutoff']))
    ndlm_full_row = _pick_row(plan_rows, family=full_ndlm_family if any(r['family_id'] == full_ndlm_family for r in plan_rows) else None, cutoff=full_ndlm_cutoff if any(r['cutoff'] == full_ndlm_cutoff and r['family_id'] == full_ndlm_family for r in plan_rows) else None, class_name='ndlm')
    ndlm_full_cfg_src = Path(ndlm_full_row['config_path'])
    ndlm_full_run_id = f'full_pipeline_{ndlm_full_row["family_id"]}_{ndlm_full_row["cutoff"]}'
    ndlm_full_run_root = smoke_root / 'full_pipeline' / 'ndlm' / ndlm_full_row['family_id'] / ndlm_full_row['cutoff']
    shutil.rmtree(ndlm_full_run_root, ignore_errors=True)
    ndlm_full_cfg = write_temp_smoke_config(
        ndlm_full_cfg_src,
        run_id=ndlm_full_run_id,
        run_root=ndlm_full_run_root,
        stage_mode='full_pipeline',
        fit_parallel_workers=1,
        mc_cores=1,
        fit_overrides=smoke_fit_overrides,
    )
    ndlm_full_proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(ndlm_full_cfg)], cwd=ROOT)
    (outdir / f'{ndlm_full_run_id}.stdout.log').write_text(ndlm_full_proc.stdout, encoding='utf-8')
    (outdir / f'{ndlm_full_run_id}.stderr.log').write_text(ndlm_full_proc.stderr, encoding='utf-8')
    assert_true(ndlm_full_proc.returncode == 0, f'NDLM full pipeline smoke failed\nSTDOUT:\n{ndlm_full_proc.stdout}\nSTDERR:\n{ndlm_full_proc.stderr}')
    _validate_full_pipeline_run(ndlm_full_run_root / ndlm_full_run_id, ndlm_full_run_id)
    summary['smoke_runs'].append({'scope': 'full_pipeline_ndlm', 'family': ndlm_full_row['family_id'], 'cutoff': ndlm_full_row['cutoff'], 'run_root': str(ndlm_full_run_root / ndlm_full_run_id)})

    full_quantile_family = str(validation_cfg.get('full_pipeline_quantile_family', quantile_fit_row['family_id']))
    full_quantile_cutoff = str(validation_cfg.get('full_pipeline_quantile_cutoff', quantile_fit_row['cutoff']))
    full_quantile_class = model_class(full_quantile_family)
    if full_quantile_class not in {'quantile_multivariate', 'quantile_univariate'}:
        full_quantile_class = 'quantile_multivariate'
    full_quantile_row = _pick_row(
        plan_rows,
        family=full_quantile_family if any(r['family_id'] == full_quantile_family for r in plan_rows) else None,
        cutoff=full_quantile_cutoff if any(r['cutoff'] == full_quantile_cutoff and r['family_id'] == full_quantile_family for r in plan_rows) else None,
        class_name=full_quantile_class,
    )
    full_quantile_subset = parse_quantile_list(validation_cfg.get('full_pipeline_quantiles') or quantile_fit_subset or [0.05])
    full_quantile_cfg_src = Path(full_quantile_row['config_path'])
    full_quantile_run_id = f'full_pipeline_{full_quantile_row["family_id"]}_{full_quantile_row["cutoff"]}_qsubset'
    full_quantile_run_root = smoke_root / 'full_pipeline' / 'quantile' / full_quantile_row['family_id'] / full_quantile_row['cutoff']
    shutil.rmtree(full_quantile_run_root, ignore_errors=True)
    full_quantile_cfg = write_temp_smoke_config(
        full_quantile_cfg_src,
        run_id=full_quantile_run_id,
        run_root=full_quantile_run_root,
        stage_mode='full_pipeline',
        quantile_subset=full_quantile_subset,
        fit_parallel_workers=1,
        mc_cores=1,
        fit_overrides=smoke_fit_overrides,
    )
    full_quantile_proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(full_quantile_cfg)], cwd=ROOT)
    (outdir / f'{full_quantile_run_id}.stdout.log').write_text(full_quantile_proc.stdout, encoding='utf-8')
    (outdir / f'{full_quantile_run_id}.stderr.log').write_text(full_quantile_proc.stderr, encoding='utf-8')
    assert_true(full_quantile_proc.returncode == 0, f'quantile full pipeline smoke failed\nSTDOUT:\n{full_quantile_proc.stdout}\nSTDERR:\n{full_quantile_proc.stderr}')
    _validate_full_pipeline_run(full_quantile_run_root / full_quantile_run_id, full_quantile_run_id)
    summary['smoke_runs'].append({'scope': 'full_pipeline_quantile', 'family': full_quantile_row['family_id'], 'cutoff': full_quantile_row['cutoff'], 'quantiles': full_quantile_subset, 'run_root': str(full_quantile_run_root / full_quantile_run_id)})

    full_univar_quantile_family = str(validation_cfg.get('full_pipeline_univar_quantile_family', 'dqlm_univar_al'))
    full_univar_quantile_cutoff = str(validation_cfg.get('full_pipeline_univar_quantile_cutoff', univar_quantile_fit_row['cutoff']))
    full_univar_quantile_row = _pick_row(
        plan_rows,
        family=full_univar_quantile_family if any(r['family_id'] == full_univar_quantile_family for r in plan_rows) else None,
        cutoff=full_univar_quantile_cutoff if any(r['cutoff'] == full_univar_quantile_cutoff and r['family_id'] == full_univar_quantile_family for r in plan_rows) else None,
        class_name='quantile_univariate',
    )
    full_univar_quantile_subset = parse_quantile_list(validation_cfg.get('full_pipeline_univar_quantiles') or [0.05])
    full_univar_quantile_cfg_src = Path(full_univar_quantile_row['config_path'])
    full_univar_quantile_run_id = f'full_pipeline_{full_univar_quantile_row["family_id"]}_{full_univar_quantile_row["cutoff"]}_qsubset'
    full_univar_quantile_run_root = smoke_root / 'full_pipeline' / 'quantile_univar' / full_univar_quantile_row['family_id'] / full_univar_quantile_row['cutoff']
    shutil.rmtree(full_univar_quantile_run_root, ignore_errors=True)
    full_univar_quantile_cfg = write_temp_smoke_config(
        full_univar_quantile_cfg_src,
        run_id=full_univar_quantile_run_id,
        run_root=full_univar_quantile_run_root,
        stage_mode='full_pipeline',
        quantile_subset=full_univar_quantile_subset,
        fit_parallel_workers=1,
        mc_cores=1,
        fit_overrides=smoke_fit_overrides,
    )
    full_univar_quantile_proc = run(['Rscript', 'scripts/unified_run.R', '--config', str(full_univar_quantile_cfg)], cwd=ROOT)
    (outdir / f'{full_univar_quantile_run_id}.stdout.log').write_text(full_univar_quantile_proc.stdout, encoding='utf-8')
    (outdir / f'{full_univar_quantile_run_id}.stderr.log').write_text(full_univar_quantile_proc.stderr, encoding='utf-8')
    assert_true(
        full_univar_quantile_proc.returncode == 0,
        f'univariate quantile full pipeline smoke failed\nSTDOUT:\n{full_univar_quantile_proc.stdout}\nSTDERR:\n{full_univar_quantile_proc.stderr}',
    )
    _validate_full_pipeline_run(full_univar_quantile_run_root / full_univar_quantile_run_id, full_univar_quantile_run_id)
    summary['smoke_runs'].append({
        'scope': 'full_pipeline_quantile_univar',
        'family': full_univar_quantile_row['family_id'],
        'cutoff': full_univar_quantile_row['cutoff'],
        'quantiles': full_univar_quantile_subset,
        'run_root': str(full_univar_quantile_run_root / full_univar_quantile_run_id),
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
        '- builder audits: `passed`',
        f'- smoke runs: `{summary["checks"]["smoke_runs"]["count"]}`',
        '',
        '## Smoke coverage',
        '',
    ]
    for row in summary['smoke_runs']:
        extra = ''
        if 'quantiles' in row:
            extra = f" quantiles=`{','.join(str(q) for q in row['quantiles'])}`"
        md_lines.append(f"- `{row['scope']}` smoke: family=`{row['family']}` cutoff=`{row['cutoff']}`{extra}")
    md_lines.append('')
    md_lines.append(f'- summary_json: `{summary_path}`')
    (outdir / 'prelaunch_validation_summary.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')

    print(f'validation_outdir={outdir}')
    print(f'summary_json={summary_path}')
    print('status=passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
