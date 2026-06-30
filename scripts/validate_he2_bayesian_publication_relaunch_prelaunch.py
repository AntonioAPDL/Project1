#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from he2_publication_relaunch_lib import canonical_shared_paths, model_class, parse_quantile_list

ROOT = Path(__file__).resolve().parents[1]
RDATA_SUFFIXES = {'.rdata', '.rda', '.rds'}
FORBIDDEN_LEGACY_UNIVAR_TRANSFORMS = (
    'nws_forecast[,-1] <- log(nws_forecast[,-1])',
    'glofas_forecast[,-1] <- log(glofas_forecast[,-1])',
    'Y <- log(Y)',
)


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def run_unified(config_path: Path, *, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env['CLEANUP_RDATA_AFTER_POST'] = '1'
    return subprocess.run(
        ['Rscript', 'scripts/unified_run.R', '--config', str(config_path)],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


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


def _choose_smoke_row(
    plan_rows: list[dict[str, str]],
    *,
    preferred_family: str | None = None,
    preferred_cutoff: str | None = None,
    class_name: str | None = None,
) -> dict[str, str] | None:
    candidates = list(plan_rows)
    if class_name:
        candidates = [row for row in candidates if row['model_class'] == class_name]
    if not candidates:
        return None
    if preferred_family and any(row['family_id'] == preferred_family for row in candidates):
        candidates = [row for row in candidates if row['family_id'] == preferred_family]
    if preferred_cutoff and any(row['cutoff'] == preferred_cutoff for row in candidates):
        candidates = [row for row in candidates if row['cutoff'] == preferred_cutoff]
    return candidates[0]


def _append_smoke_result(
    summary: dict[str, Any],
    *,
    scope: str,
    status: str,
    family: str | None = None,
    cutoff: str | None = None,
    reason: str | None = None,
    run_root: str | None = None,
    shared_root: str | None = None,
    quantiles: list[float] | None = None,
    cleanup_removed_files: int | None = None,
    cleanup_removed_bytes: int | None = None,
) -> None:
    row: dict[str, Any] = {'scope': scope, 'status': status}
    if family:
        row['family'] = family
    if cutoff:
        row['cutoff'] = cutoff
    if reason:
        row['reason'] = reason
    if run_root:
        row['run_root'] = run_root
    if shared_root:
        row['shared_root'] = shared_root
    if quantiles:
        row['quantiles'] = quantiles
    if cleanup_removed_files is not None:
        row['cleanup_removed_files'] = int(cleanup_removed_files)
    if cleanup_removed_bytes is not None:
        row['cleanup_removed_bytes'] = int(cleanup_removed_bytes)
    summary['smoke_runs'].append(row)


def _prune_r_artifacts(root: Path) -> dict[str, int]:
    removed_files = 0
    removed_bytes = 0
    if not root.exists():
        return {'removed_files': 0, 'removed_bytes': 0}
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix.lower() not in RDATA_SUFFIXES:
            continue
        size = path.stat().st_size
        path.unlink()
        removed_files += 1
        removed_bytes += size
    return {'removed_files': removed_files, 'removed_bytes': removed_bytes}


def _validate_legacy_univar_scale_source_contract() -> dict[str, Any]:
    runner_path = ROOT / 'OptimalModelSLexAL.r'
    helper_path = ROOT / 'R' / 'unified' / 'univar_legacy_scale_contract.R'
    stage_fit_path = ROOT / 'R' / 'unified' / 'stages' / 'stage_fit.R'
    post_figures_path = ROOT / 'R' / 'unified' / 'post_publication_figures.R'

    assert_true(runner_path.exists(), f'missing legacy univariate runner: {runner_path}')
    assert_true(helper_path.exists(), f'missing legacy univariate scale helper: {helper_path}')

    runner_text = runner_path.read_text(encoding='utf-8')
    helper_text = helper_path.read_text(encoding='utf-8')
    stage_fit_text = stage_fit_path.read_text(encoding='utf-8')
    post_figures_text = post_figures_path.read_text(encoding='utf-8')

    for needle in FORBIDDEN_LEGACY_UNIVAR_TRANSFORMS:
        assert_true(needle not in runner_text, f'legacy univariate runner still contains forbidden transform: {needle}')

    for needle in (
        'univar_legacy_resolve_scale_contract',
        'univar_legacy_transform_flow_frame_cols',
        'univar_legacy_transform_flow_values_to_internal_scale',
    ):
        assert_true(needle in runner_text, f'legacy univariate runner does not use scale bridge symbol: {needle}')
        assert_true(needle in helper_text, f'legacy univariate scale helper missing symbol: {needle}')

    assert_true(
        stage_fit_text.count('UNIFIED_LEGACY_FIT_INPUT_SCALE = as.character(cfg$scale_contract$legacy_fit_input_scale)') >= 2,
        'stage_fit.R must export UNIFIED_LEGACY_FIT_INPUT_SCALE to multivariate and univariate subprocesses',
    )
    assert_true(
        stage_fit_text.count('UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL = as.character(cfg$scale_contract$analysis_scale_fit_internal)') >= 2,
        'stage_fit.R must export UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL to multivariate and univariate subprocesses',
    )
    assert_true(
        stage_fit_text.count('UNIFIED_TRANSFORM_POLICY = as.character(unified_get(') >= 2,
        'stage_fit.R must export UNIFIED_TRANSFORM_POLICY to multivariate and univariate subprocesses',
    )
    assert_true(
        'log1p_cms = bquote(River~flow~"["*log(1 + x)*";"' in post_figures_text,
        'publication figure axis label must expose log(1 + x) for log1p_cms',
    )
    assert_true(
        'log_log1p_cms = stop("post publication figures must stay on log1p_cms' in post_figures_text,
        'publication figures must reject log_log1p_cms',
    )
    return {
        'runner': str(runner_path),
        'helper': str(helper_path),
        'stage_fit': str(stage_fit_path),
        'post_publication_figures': str(post_figures_path),
        'status': 'passed',
    }


def _validate_generated_config_scale_contract(payload: dict[str, Any], path: Path) -> None:
    scale = payload.get('scale_contract') if isinstance(payload.get('scale_contract'), dict) else {}
    expected = {
        'legacy_fit_input_scale': 'log1p_cms',
        'legacy_post_input_scale': 'log1p_cms',
        'analysis_scale_fit_internal': 'log1p_cms',
        'analysis_scale_post_internal': 'log1p_cms',
        'transform_policy': 'log1p_only',
    }
    for key, expected_value in expected.items():
        actual = scale.get(key)
        assert_true(
            actual == expected_value,
            f'{path.name}: scale_contract.{key} expected {expected_value}, got {actual}',
        )

    models = payload.get('models') if isinstance(payload.get('models'), dict) else {}
    if bool(models.get('run_exdqlm_univar')):
        univar_model = models.get('exdqlm_univar') if isinstance(models.get('exdqlm_univar'), dict) else {}
        assert_true(
            univar_model.get('implementation_mode') == 'legacy_bridge',
            f'{path.name}: exdqlm_univar publication relaunch must use legacy_bridge until intentionally migrated',
        )
        assert_true(
            str(univar_model.get('likelihood_mode', '')).lower() in {'al', 'exal'},
            f'{path.name}: exdqlm_univar likelihood_mode must be al or exal',
        )


def _normalize_quantile_smoke_cases(
    validation_cfg: dict[str, Any],
    *,
    cases_key: str,
    family_key: str,
    cutoff_key: str,
    quantiles_key: str,
    default_family: str,
    default_cutoff: str,
    default_quantiles: list[float],
) -> list[dict[str, Any]]:
    def _is_disabled_family(value: Any) -> bool:
        token = str(value or '').strip().lower()
        return token in {'', '__disabled__', 'disabled', 'none', 'null', 'false'}

    raw_cases = validation_cfg.get(cases_key)
    if raw_cases:
        normalized: list[dict[str, Any]] = []
        for idx, item in enumerate(raw_cases, start=1):
            if not isinstance(item, dict):
                raise TypeError(f'{cases_key}[{idx - 1}] must be a mapping')
            family = str(item.get('family') or default_family)
            cutoff = str(item.get('cutoff') or default_cutoff)
            quantiles = parse_quantile_list(item.get('quantiles') or default_quantiles)
            label = str(item.get('label') or cutoff)
            fit_overrides = copy.deepcopy(item.get('fit_overrides') or {})
            normalized.append({'family': family, 'cutoff': cutoff, 'quantiles': quantiles, 'label': label, 'fit_overrides': fit_overrides})
        return normalized
    family = str(validation_cfg.get(family_key, default_family))
    if _is_disabled_family(family):
        return []
    return [{
        'family': family,
        'cutoff': str(validation_cfg.get(cutoff_key, default_cutoff)),
        'quantiles': parse_quantile_list(validation_cfg.get(quantiles_key) or default_quantiles),
        'label': str(validation_cfg.get(cutoff_key, default_cutoff)),
        'fit_overrides': {},
    }]


def _normalize_ndlm_smoke_cases(
    validation_cfg: dict[str, Any],
    *,
    cases_key: str,
    family_key: str,
    cutoff_key: str,
    default_family: str,
    default_cutoff: str,
) -> list[dict[str, Any]]:
    def _is_disabled_family(value: Any) -> bool:
        token = str(value or '').strip().lower()
        return token in {'', '__disabled__', 'disabled', 'none', 'null', 'false'}

    raw_cases = validation_cfg.get(cases_key)
    if raw_cases:
        normalized: list[dict[str, Any]] = []
        for idx, item in enumerate(raw_cases, start=1):
            if not isinstance(item, dict):
                raise TypeError(f'{cases_key}[{idx - 1}] must be a mapping')
            family = str(item.get('family') or default_family)
            cutoff = str(item.get('cutoff') or default_cutoff)
            label = str(item.get('label') or f'{family}_{cutoff}')
            fit_overrides = copy.deepcopy(item.get('fit_overrides') or {})
            normalized.append({'family': family, 'cutoff': cutoff, 'label': label, 'fit_overrides': fit_overrides})
        return normalized
    family = str(validation_cfg.get(family_key, default_family))
    if _is_disabled_family(family):
        return []
    cutoff = str(validation_cfg.get(cutoff_key, default_cutoff))
    return [{'family': family, 'cutoff': cutoff, 'label': f'{family}_{cutoff}', 'fit_overrides': {}}]


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
    summary['checks']['legacy_univar_scale_source_contract'] = _validate_legacy_univar_scale_source_contract()

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
        _validate_generated_config_scale_contract(payload, path)
        cutoff = str(payload['dates']['cutoff_date']).replace('-', '')
        by_cutoff[cutoff].append({'path': path, 'payload': payload})
        names = [row['name'] for row in payload['inputs']['fit']['covariates']]
        assert_true(names == ['PPT', 'SOIL', 'PCA'], f'{path.name}: covariates mismatch {names}')
    summary['checks']['generated_config_scale_contract'] = 'passed'

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
        proc = run_unified(smoke_cfg, cwd=ROOT)
        (outdir / f'{family}.stdout.log').write_text(proc.stdout, encoding='utf-8')
        (outdir / f'{family}.stderr.log').write_text(proc.stderr, encoding='utf-8')
        assert_true(proc.returncode == 0, f'family smoke failed for {family}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        shared_root = run_root / run_id / 'inputs' / 'shared'
        assert_true((shared_root / 'covariates' / 'covariate_features.csv').exists(), f'{family}: missing covariate_features.csv')
        _validate_data_start_filter(shared_root / 'data_start_filter_summary.txt', row['cutoff'])
        _append_smoke_result(summary, scope='family', status='passed', family=family, cutoff=row['cutoff'], shared_root=str(shared_root))

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
        proc = run_unified(smoke_cfg, cwd=ROOT)
        (outdir / f'{cutoff}.stdout.log').write_text(proc.stdout, encoding='utf-8')
        (outdir / f'{cutoff}.stderr.log').write_text(proc.stderr, encoding='utf-8')
        assert_true(proc.returncode == 0, f'cutoff smoke failed for {cutoff}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
        shared_root = run_root / run_id / 'inputs' / 'shared'
        assert_true((shared_root / 'covariates' / 'covariate_features.csv').exists(), f'{cutoff}: missing covariate_features.csv')
        _validate_data_start_filter(shared_root / 'data_start_filter_summary.txt', cutoff)
        _append_smoke_result(summary, scope='cutoff', status='passed', family=row['family_id'], cutoff=cutoff, shared_root=str(shared_root))

    fit_smoke_family_pref = str(validation_cfg.get('fit_smoke_family', 'ndlm_univar_keep'))
    fit_smoke_cutoff_pref = str(validation_cfg.get('fit_smoke_cutoff', selected_cutoffs[0]))
    fit_smoke_row = _choose_smoke_row(plan_rows, preferred_family=fit_smoke_family_pref, preferred_cutoff=fit_smoke_cutoff_pref, class_name='ndlm')
    if fit_smoke_row is None:
        _append_smoke_result(summary, scope='fit_ndlm', status='skipped', family=fit_smoke_family_pref, cutoff=fit_smoke_cutoff_pref, reason='no ndlm row available in selected scope')
    else:
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
        fit_proc = run_unified(fit_smoke_cfg, cwd=ROOT)
        (outdir / f'{fit_run_id}.stdout.log').write_text(fit_proc.stdout, encoding='utf-8')
        (outdir / f'{fit_run_id}.stderr.log').write_text(fit_proc.stderr, encoding='utf-8')
        assert_true(fit_proc.returncode == 0, f'fit smoke failed for family={fit_smoke_row["family_id"]} cutoff={fit_smoke_row["cutoff"]}\nSTDOUT:\n{fit_proc.stdout}\nSTDERR:\n{fit_proc.stderr}')
        fit_cleanup = _prune_r_artifacts(fit_run_root / fit_run_id)
        _append_smoke_result(
            summary,
            scope='fit_ndlm',
            status='passed',
            family=fit_smoke_row['family_id'],
            cutoff=fit_smoke_row['cutoff'],
            run_root=str(fit_run_root / fit_run_id),
            cleanup_removed_files=fit_cleanup['removed_files'],
            cleanup_removed_bytes=fit_cleanup['removed_bytes'],
        )

    quantile_fit_cases = _normalize_quantile_smoke_cases(
        validation_cfg,
        cases_key='quantile_fit_smoke_cases',
        family_key='quantile_fit_smoke_family',
        cutoff_key='quantile_fit_smoke_cutoff',
        quantiles_key='quantile_fit_smoke_quantiles',
        default_family='exdqlm_multivar_keep',
        default_cutoff=selected_cutoffs[0],
        default_quantiles=[0.05],
    )
    for case in quantile_fit_cases:
        quantile_fit_row = _choose_smoke_row(plan_rows, preferred_family=case['family'], preferred_cutoff=case['cutoff'], class_name='quantile_multivariate')
        if quantile_fit_row is None:
            _append_smoke_result(summary, scope='fit_quantile', status='skipped', family=case['family'], cutoff=case['cutoff'], quantiles=case['quantiles'], reason='no multivariate quantile row available in selected scope')
            continue
        qfit_cfg_src = Path(quantile_fit_row['config_path'])
        qfit_run_id = f'fit_smoke_{quantile_fit_row["family_id"]}_{quantile_fit_row["cutoff"]}_qsubset'
        qfit_run_root = smoke_root / 'fit_quantile' / quantile_fit_row['family_id'] / quantile_fit_row['cutoff']
        shutil.rmtree(qfit_run_root, ignore_errors=True)
        qfit_smoke_cfg = write_temp_smoke_config(
            qfit_cfg_src,
            run_id=qfit_run_id,
            run_root=qfit_run_root,
            stage_mode='fit',
            quantile_subset=case['quantiles'],
            fit_parallel_workers=1,
            mc_cores=1,
            fit_overrides=deep_merge_dict(smoke_fit_overrides, case.get('fit_overrides') or {}),
        )
        qfit_proc = run_unified(qfit_smoke_cfg, cwd=ROOT)
        (outdir / f'{qfit_run_id}.stdout.log').write_text(qfit_proc.stdout, encoding='utf-8')
        (outdir / f'{qfit_run_id}.stderr.log').write_text(qfit_proc.stderr, encoding='utf-8')
        assert_true(qfit_proc.returncode == 0, f'quantile fit smoke failed for family={quantile_fit_row["family_id"]} cutoff={quantile_fit_row["cutoff"]}\nSTDOUT:\n{qfit_proc.stdout}\nSTDERR:\n{qfit_proc.stderr}')
        qfit_cleanup = _prune_r_artifacts(qfit_run_root / qfit_run_id)
        _append_smoke_result(
            summary,
            scope='fit_quantile',
            status='passed',
            family=quantile_fit_row['family_id'],
            cutoff=quantile_fit_row['cutoff'],
            quantiles=case['quantiles'],
            run_root=str(qfit_run_root / qfit_run_id),
            cleanup_removed_files=qfit_cleanup['removed_files'],
            cleanup_removed_bytes=qfit_cleanup['removed_bytes'],
        )

    univar_quantile_pref = str(validation_cfg.get('univar_quantile_fit_smoke_family', 'exdqlm_univar'))
    univar_quantile_cutoff_pref = str(validation_cfg.get('univar_quantile_fit_smoke_cutoff', selected_cutoffs[0]))
    univar_quantile_fit_subset = parse_quantile_list(validation_cfg.get('univar_quantile_fit_smoke_quantiles') or [0.05])
    univar_quantile_fit_row = _choose_smoke_row(plan_rows, preferred_family=univar_quantile_pref, preferred_cutoff=univar_quantile_cutoff_pref, class_name='quantile_univariate')
    if univar_quantile_fit_row is None:
        _append_smoke_result(summary, scope='fit_quantile_univar', status='skipped', family=univar_quantile_pref, cutoff=univar_quantile_cutoff_pref, quantiles=univar_quantile_fit_subset, reason='no univariate quantile row available in selected scope')
    else:
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
        uqfit_proc = run_unified(uqfit_smoke_cfg, cwd=ROOT)
        (outdir / f'{uqfit_run_id}.stdout.log').write_text(uqfit_proc.stdout, encoding='utf-8')
        (outdir / f'{uqfit_run_id}.stderr.log').write_text(uqfit_proc.stderr, encoding='utf-8')
        assert_true(
            uqfit_proc.returncode == 0,
            f'univariate quantile fit smoke failed for family={univar_quantile_fit_row["family_id"]} cutoff={univar_quantile_fit_row["cutoff"]}\nSTDOUT:\n{uqfit_proc.stdout}\nSTDERR:\n{uqfit_proc.stderr}',
        )
        uqfit_cleanup = _prune_r_artifacts(uqfit_run_root / uqfit_run_id)
        _append_smoke_result(
            summary,
            scope='fit_quantile_univar',
            status='passed',
            family=univar_quantile_fit_row['family_id'],
            cutoff=univar_quantile_fit_row['cutoff'],
            quantiles=univar_quantile_fit_subset,
            run_root=str(uqfit_run_root / uqfit_run_id),
            cleanup_removed_files=uqfit_cleanup['removed_files'],
            cleanup_removed_bytes=uqfit_cleanup['removed_bytes'],
        )

    full_ndlm_cases = _normalize_ndlm_smoke_cases(
        validation_cfg,
        cases_key='full_pipeline_ndlm_cases',
        family_key='full_pipeline_ndlm_family',
        cutoff_key='full_pipeline_ndlm_cutoff',
        default_family=fit_smoke_family_pref,
        default_cutoff=fit_smoke_cutoff_pref,
    )
    for case in full_ndlm_cases:
        ndlm_full_row = _choose_smoke_row(plan_rows, preferred_family=case['family'], preferred_cutoff=case['cutoff'], class_name='ndlm')
        if ndlm_full_row is None:
            _append_smoke_result(summary, scope='full_pipeline_ndlm', status='skipped', family=case['family'], cutoff=case['cutoff'], reason='no NDLM row available in selected scope')
            continue
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
            fit_overrides=deep_merge_dict(smoke_fit_overrides, case.get('fit_overrides') or {}),
        )
        ndlm_full_proc = run_unified(ndlm_full_cfg, cwd=ROOT)
        (outdir / f'{ndlm_full_run_id}.stdout.log').write_text(ndlm_full_proc.stdout, encoding='utf-8')
        (outdir / f'{ndlm_full_run_id}.stderr.log').write_text(ndlm_full_proc.stderr, encoding='utf-8')
        assert_true(ndlm_full_proc.returncode == 0, f'NDLM full pipeline smoke failed\nSTDOUT:\n{ndlm_full_proc.stdout}\nSTDERR:\n{ndlm_full_proc.stderr}')
        _validate_full_pipeline_run(ndlm_full_run_root / ndlm_full_run_id, ndlm_full_run_id)
        ndlm_full_cleanup = _prune_r_artifacts(ndlm_full_run_root / ndlm_full_run_id)
        _append_smoke_result(
            summary,
            scope='full_pipeline_ndlm',
            status='passed',
            family=ndlm_full_row['family_id'],
            cutoff=ndlm_full_row['cutoff'],
            run_root=str(ndlm_full_run_root / ndlm_full_run_id),
            cleanup_removed_files=ndlm_full_cleanup['removed_files'],
            cleanup_removed_bytes=ndlm_full_cleanup['removed_bytes'],
        )

    default_quantile_case = quantile_fit_cases[0] if quantile_fit_cases else {'family': 'exdqlm_multivar_keep', 'cutoff': selected_cutoffs[0], 'quantiles': [0.05]}
    full_quantile_cases = _normalize_quantile_smoke_cases(
        validation_cfg,
        cases_key='full_pipeline_quantile_smoke_cases',
        family_key='full_pipeline_quantile_family',
        cutoff_key='full_pipeline_quantile_cutoff',
        quantiles_key='full_pipeline_quantiles',
        default_family=default_quantile_case['family'],
        default_cutoff=default_quantile_case['cutoff'],
        default_quantiles=default_quantile_case['quantiles'],
    )
    for case in full_quantile_cases:
        full_quantile_class = model_class(case['family'])
        if full_quantile_class not in {'quantile_multivariate', 'quantile_univariate'}:
            full_quantile_class = 'quantile_multivariate'
        full_quantile_row = _choose_smoke_row(plan_rows, preferred_family=case['family'], preferred_cutoff=case['cutoff'], class_name=full_quantile_class)
        if full_quantile_row is None:
            _append_smoke_result(summary, scope='full_pipeline_quantile', status='skipped', family=case['family'], cutoff=case['cutoff'], quantiles=case['quantiles'], reason=f'no {full_quantile_class} row available in selected scope')
            continue
        full_quantile_cfg_src = Path(full_quantile_row['config_path'])
        full_quantile_run_id = f'full_pipeline_{full_quantile_row["family_id"]}_{full_quantile_row["cutoff"]}_qsubset'
        full_quantile_run_root = smoke_root / 'full_pipeline' / 'quantile' / full_quantile_row['family_id'] / full_quantile_row['cutoff']
        shutil.rmtree(full_quantile_run_root, ignore_errors=True)
        full_quantile_cfg = write_temp_smoke_config(
            full_quantile_cfg_src,
            run_id=full_quantile_run_id,
            run_root=full_quantile_run_root,
            stage_mode='full_pipeline',
            quantile_subset=case['quantiles'],
            fit_parallel_workers=1,
            mc_cores=1,
            fit_overrides=smoke_fit_overrides,
        )
        full_quantile_proc = run_unified(full_quantile_cfg, cwd=ROOT)
        (outdir / f'{full_quantile_run_id}.stdout.log').write_text(full_quantile_proc.stdout, encoding='utf-8')
        (outdir / f'{full_quantile_run_id}.stderr.log').write_text(full_quantile_proc.stderr, encoding='utf-8')
        assert_true(full_quantile_proc.returncode == 0, f'quantile full pipeline smoke failed\nSTDOUT:\n{full_quantile_proc.stdout}\nSTDERR:\n{full_quantile_proc.stderr}')
        _validate_full_pipeline_run(full_quantile_run_root / full_quantile_run_id, full_quantile_run_id)
        full_quantile_cleanup = _prune_r_artifacts(full_quantile_run_root / full_quantile_run_id)
        _append_smoke_result(
            summary,
            scope='full_pipeline_quantile',
            status='passed',
            family=full_quantile_row['family_id'],
            cutoff=full_quantile_row['cutoff'],
            quantiles=case['quantiles'],
            run_root=str(full_quantile_run_root / full_quantile_run_id),
            cleanup_removed_files=full_quantile_cleanup['removed_files'],
            cleanup_removed_bytes=full_quantile_cleanup['removed_bytes'],
        )

    full_univar_quantile_family = str(validation_cfg.get('full_pipeline_univar_quantile_family', univar_quantile_pref))
    full_univar_quantile_cutoff = str(validation_cfg.get('full_pipeline_univar_quantile_cutoff', univar_quantile_cutoff_pref))
    full_univar_quantile_subset = parse_quantile_list(validation_cfg.get('full_pipeline_univar_quantiles') or [0.05])
    full_univar_quantile_row = _choose_smoke_row(plan_rows, preferred_family=full_univar_quantile_family, preferred_cutoff=full_univar_quantile_cutoff, class_name='quantile_univariate')
    if full_univar_quantile_row is None:
        _append_smoke_result(summary, scope='full_pipeline_quantile_univar', status='skipped', family=full_univar_quantile_family, cutoff=full_univar_quantile_cutoff, quantiles=full_univar_quantile_subset, reason='no quantile_univariate row available in selected scope')
    else:
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
        full_univar_quantile_proc = run_unified(full_univar_quantile_cfg, cwd=ROOT)
        (outdir / f'{full_univar_quantile_run_id}.stdout.log').write_text(full_univar_quantile_proc.stdout, encoding='utf-8')
        (outdir / f'{full_univar_quantile_run_id}.stderr.log').write_text(full_univar_quantile_proc.stderr, encoding='utf-8')
        assert_true(
            full_univar_quantile_proc.returncode == 0,
            f'univariate quantile full pipeline smoke failed\nSTDOUT:\n{full_univar_quantile_proc.stdout}\nSTDERR:\n{full_univar_quantile_proc.stderr}',
        )
        _validate_full_pipeline_run(full_univar_quantile_run_root / full_univar_quantile_run_id, full_univar_quantile_run_id)
        full_univar_cleanup = _prune_r_artifacts(full_univar_quantile_run_root / full_univar_quantile_run_id)
        _append_smoke_result(
            summary,
            scope='full_pipeline_quantile_univar',
            status='passed',
            family=full_univar_quantile_row['family_id'],
            cutoff=full_univar_quantile_row['cutoff'],
            quantiles=full_univar_quantile_subset,
            run_root=str(full_univar_quantile_run_root / full_univar_quantile_run_id),
            cleanup_removed_files=full_univar_cleanup['removed_files'],
            cleanup_removed_bytes=full_univar_cleanup['removed_bytes'],
        )

    smoke_status_counts = Counter(row.get('status', 'passed') for row in summary['smoke_runs'])
    cleanup_removed_files = sum(int(row.get('cleanup_removed_files', 0)) for row in summary['smoke_runs'])
    cleanup_removed_bytes = sum(int(row.get('cleanup_removed_bytes', 0)) for row in summary['smoke_runs'])
    summary['checks']['smoke_runs'] = {
        'count': len(summary['smoke_runs']),
        'passed': int(smoke_status_counts.get('passed', 0)),
        'skipped': int(smoke_status_counts.get('skipped', 0)),
        'cleanup_removed_files': cleanup_removed_files,
        'cleanup_removed_bytes': cleanup_removed_bytes,
    }

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
        f'- smoke passed: `{summary["checks"]["smoke_runs"]["passed"]}`',
        f'- smoke skipped: `{summary["checks"]["smoke_runs"]["skipped"]}`',
        f'- smoke cleanup removed files: `{summary["checks"]["smoke_runs"]["cleanup_removed_files"]}`',
        f'- smoke cleanup removed bytes: `{summary["checks"]["smoke_runs"]["cleanup_removed_bytes"]}`',
        '',
        '## Smoke coverage',
        '',
    ]
    for row in summary['smoke_runs']:
        extra = ''
        if 'quantiles' in row:
            extra = f" quantiles=`{','.join(str(q) for q in row['quantiles'])}`"
        reason = f" reason=`{row['reason']}`" if row.get('reason') else ''
        md_lines.append(f"- `{row['scope']}` `{row.get('status', 'passed')}`: family=`{row.get('family', '')}` cutoff=`{row.get('cutoff', '')}`{extra}{reason}")
    md_lines.append('')
    md_lines.append(f'- summary_json: `{summary_path}`')
    (outdir / 'prelaunch_validation_summary.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')

    print(f'validation_outdir={outdir}')
    print(f'summary_json={summary_path}')
    print('status=passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
