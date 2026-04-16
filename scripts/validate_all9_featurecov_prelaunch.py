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
    'exdqlm_univar',
    'dqlm_univar_al',
    'ndlm_main_keep',
    'ndlm_main_drop',
    'ndlm_univar_keep',
]
EXPECTED_CUTOFFS = ['20210123', '20211112', '20211221', '20220511', '20221225']


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, env=env)


def parse_builder_stdout(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if '=' in line and line.split('=', 1)[0] in {'artifact_root', 'matrix_dir', 'config_output_dir', 'generated_configs', 'plan_rows', 'selection_rows'}:
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


def main() -> int:
    ap = argparse.ArgumentParser(description='Validate corrected all-9 feature-covariate relaunch without launching.')
    ap.add_argument('--config', required=True)
    ap.add_argument('--review-config', default='config/forecast_overlay_review.site11160500.yaml')
    ap.add_argument('--outdir')
    args = ap.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config).resolve()
    review_config_path = (ROOT / args.review_config).resolve() if not Path(args.review_config).is_absolute() else Path(args.review_config).resolve()
    cfg = load_yaml(config_path)
    review_cfg = load_yaml(review_config_path)

    artifact_root = Path(cfg['campaign']['artifact_root']).resolve()
    default_outdir = artifact_root / 'control' / f"prelaunch_validation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    outdir = Path(args.outdir).resolve() if args.outdir else default_outdir
    outdir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        'config': str(config_path),
        'review_config': str(review_config_path),
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'checks': {},
        'smoke_runs': [],
    }

    # 1. Campaign config sanity.
    detclim = cfg.get('inputs', {}).get('deterministic_climate', {})
    handoff_root = Path(detclim.get('handoff_root', '')).resolve()
    assert_true(detclim.get('enabled') is True, 'deterministic climate must be enabled')
    assert_true(handoff_root.exists(), f'handoff_root missing: {handoff_root}')
    assert_true((handoff_root / 'handoff_meta.json').exists(), 'handoff_meta.json missing')
    assert_true(detclim.get('precip', {}).get('source') == 'gefs_apcp', 'unexpected precip source')
    assert_true(detclim.get('soil', {}).get('source') == 'gefs_soilw_0_0.1m', 'unexpected soil source')
    assert_true(float(detclim.get('precip', {}).get('noisy_blend', {}).get('noise_sd')) == 30.0, 'unexpected precip noise sd')
    assert_true(float(detclim.get('soil', {}).get('noisy_blend', {}).get('noise_sd')) == 0.05, 'unexpected soil noise sd')
    assert_true(detclim.get('soil', {}).get('noisy_blend', {}).get('noise_distribution') == 'abs_normal', 'unexpected soil noise distribution')
    assert_true(float(detclim.get('precip', {}).get('observed_blend', {}).get('observed_zero_stay_prob')) == 0.9, 'unexpected precip zero-stay prob')
    summary['checks']['config_sanity'] = 'passed'

    # 2. Overlay review artifacts sanity.
    review = review_cfg['review']
    review_root = Path(review['manifest_run_dir']) / 'review_prep' / review['review_id']
    plot_index_path = review_root / 'plot_index.csv'
    summary_json_path = review_root / 'forecast_overlay_review_summary.json'
    climate_status_path = review_root / 'climate_series_status.csv'
    assert_true(plot_index_path.exists(), f'missing plot index: {plot_index_path}')
    assert_true(summary_json_path.exists(), f'missing review summary: {summary_json_path}')
    assert_true(climate_status_path.exists(), f'missing climate series status: {climate_status_path}')
    with plot_index_path.open('r', encoding='utf-8') as handle:
        plot_rows = list(csv.DictReader(handle))
    expected_plot_count = len(review['cutoffs']) * len(review_cfg['plots']['styles'])
    assert_true(len(plot_rows) == expected_plot_count, f'expected {expected_plot_count} review plots, found {len(plot_rows)}')
    with summary_json_path.open('r', encoding='utf-8') as handle:
        review_summary = json.load(handle)
    assert_true(review_summary.get('handoff_health_pass') is True, 'review summary reports unhealthy handoff inputs')
    assert_true(len(review_summary.get('plot_runs', [])) == expected_plot_count, 'review summary plot count mismatch')
    summary['checks']['overlay_review'] = {
        'review_root': str(review_root),
        'plots_rendered': expected_plot_count,
    }

    # 3. Rebuild matrix surface.
    build = run(['python3', 'scripts/build_multimodel_v8_all9_feature_matrix_configs.py', '--config', str(config_path)], cwd=ROOT)
    (outdir / 'build_stdout.log').write_text(build.stdout, encoding='utf-8')
    (outdir / 'build_stderr.log').write_text(build.stderr, encoding='utf-8')
    assert_true(build.returncode == 0, f'builder failed: {build.stderr}')
    build_info = parse_builder_stdout(build.stdout)
    matrix_dir = Path(build_info['matrix_dir']).resolve()
    config_output_dir = Path(build_info['config_output_dir']).resolve()
    assert_true(int(build_info['generated_configs']) == 45, 'unexpected generated config count')
    assert_true(int(build_info['plan_rows']) == 45, 'unexpected plan row count')
    summary['checks']['builder'] = build_info

    # 4. Validate matrix + configs.
    plan_rows = list(csv.DictReader((matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8')))
    selection_rows = list(csv.DictReader((matrix_dir / 'selection_summary.csv').open('r', encoding='utf-8')))
    assert_true(len(plan_rows) == 45, 'matrix_plan row count mismatch')
    assert_true(len(selection_rows) == 45, 'selection_summary row count mismatch')
    family_counts = Counter(r['lane'] for r in plan_rows)
    cutoff_counts = Counter(r['cutoff'] for r in plan_rows)
    for family in EXPECTED_FAMILIES:
        assert_true(family_counts[family] == 5, f'unexpected family count for {family}: {family_counts[family]}')
    for cutoff in EXPECTED_CUTOFFS:
        assert_true(cutoff_counts[cutoff] == 9, f'unexpected cutoff count for {cutoff}: {cutoff_counts[cutoff]}')

    configs = sorted(config_output_dir.glob('*.yaml'))
    assert_true(len(configs) == 45, 'config output dir does not contain 45 yaml files')
    config_checks = []
    for path in configs:
        payload = load_yaml(path)
        covs = payload['inputs']['fit']['covariates']
        names = [row['name'] for row in covs]
        assert_true(names == ['PPT', 'SOIL', 'PCA'], f'{path.name}: unexpected covariates {names}')
        for row in covs:
            cov_path = Path(row['path'])
            assert_true(cov_path.exists(), f'{path.name}: missing covariate path {cov_path}')
        assert_true(payload['inputs']['deterministic_climate']['handoff_root'] == str(handoff_root), f'{path.name}: handoff_root mismatch')
        config_checks.append({'config': path.name, 'covariate_paths_ok': True})
    summary['checks']['generated_configs'] = {
        'count': len(configs),
        'family_counts': dict(family_counts),
        'cutoff_counts': dict(cutoff_counts),
    }

    # 5. Targeted Python + R tests.
    test_cmds = [
        ['python3', '-m', 'unittest', 'tests.python.test_prepare_forecast_overlay_review', 'tests.python.test_deterministic_climate_handoff_workflow', 'tests.python.test_forecast_download_workflow'],
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

    # 6. One data_prep_shared smoke per family.
    smoke_root = outdir / 'smoke_runs'
    smoke_root.mkdir(parents=True, exist_ok=True)
    first_by_family: dict[str, dict[str, str]] = {}
    for row in plan_rows:
        first_by_family.setdefault(row['lane'], row)
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
        assert_true((shared_root / 'covariates' / 'covariate_features.csv').exists(), f'{family}: missing engineered covariate features')
        assert_true((shared_root / 'deterministic_climate' / 'deterministic_climate_summary.txt').exists(), f'{family}: missing detclim summary')
        summary['smoke_runs'].append({'family': family, 'config': str(src_cfg), 'shared_root': str(shared_root)})
    summary['checks']['smoke_runs'] = {'count': len(summary['smoke_runs'])}

    # 7. Write reports.
    summary_path = outdir / 'prelaunch_validation_summary.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    md_lines = [
        '# All-9 Feature-Covariate Prelaunch Validation',
        '',
        f'- config: `{config_path}`',
        f'- review_config: `{review_config_path}`',
        f'- timestamp_utc: `{summary["timestamp_utc"]}`',
        '',
        '## Result',
        '',
        '- status: `passed`',
        '- launch_state: `not launched by this validation`',
        '',
        '## Checks',
        '',
        f'- deterministic-climate config sanity: `{summary["checks"]["config_sanity"]}`',
        f'- overlay review plots verified: `{summary["checks"]["overlay_review"]["plots_rendered"]}`',
        f'- generated configs: `{summary["checks"]["generated_configs"]["count"]}`',
        f'- smoke runs: `{summary["checks"]["smoke_runs"]["count"]}`',
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
