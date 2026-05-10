#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import pandas as pd

from he2_publication_relaunch_lib import (
    AUTHORITATIVE_COMPARE_BY_CUTOFF,
    DEFAULT_BUNDLE_ARTIFACT_ROOT,
    DEFAULT_BUNDLE_RUN_ID,
    DEFAULT_CAMPAIGN_SPEC_ID,
    DEFAULT_RELAUNCH_ARTIFACT_ROOT,
    EXPECTED_CUTOFFS,
    EXPECTED_FAMILY_ORDER,
    canonical_shared_paths,
    ensure_dir,
    family_rank,
    load_publication_manifest_rows,
    load_yaml,
    row_kind,
    spec_token,
    submodel_count,
    write_yaml,
)
from multimodel_v8_lib import HEAVY_CUTOFF, artifact_disk_free_gb, control_dir, reports_dir, resolve_artifact_root, runs_dir

MODEL_ID_BY_FAMILY = {
    'ndlm_univar_keep': 'ndlm_univar_synth_keep',
    'ndlm_main_drop': 'ndlm_main_synth_drop',
    'ndlm_main_keep': 'ndlm_main_synth_keep',
    'dqlm_univar_al': 'dqlm_univar_al_synth',
    'dqlm_multivar_al_drop': 'dqlm_multivar_al_synth_drop',
    'dqlm_multivar_al_keep': 'dqlm_multivar_al_synth_keep',
    'exdqlm_univar': 'exdqlm_univar_synth',
    'exdqlm_multivar_drop': 'exdqlm_multivar_synth_drop',
    'exdqlm_multivar_keep': 'exdqlm_multivar_synth_keep',
}

MODEL_KEY_BY_FAMILY = {
    'ndlm_univar_keep': 'ndlm_univar',
    'ndlm_main_drop': 'ndlm_main',
    'ndlm_main_keep': 'ndlm_main',
    'dqlm_univar_al': 'exdqlm_univar',
    'dqlm_multivar_al_drop': 'exdqlm_multivar',
    'dqlm_multivar_al_keep': 'exdqlm_multivar',
    'exdqlm_univar': 'exdqlm_univar',
    'exdqlm_multivar_drop': 'exdqlm_multivar',
    'exdqlm_multivar_keep': 'exdqlm_multivar',
}


def _set_nested(cfg: dict[str, Any], path: list[str], value: Any) -> None:
    cur = cfg
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def _dependency_rows(config_path: Path, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dep_specs = [
        ('forecats_existing_bundle', cfg.get('inputs', {}).get('forecats', {}).get('existing_bundle_path', '')),
        ('fit_parameters', cfg.get('inputs', {}).get('fit', {}).get('parameters_path', '')),
        ('fit_retros', cfg.get('inputs', {}).get('fit', {}).get('retros_path', '')),
        ('fit_nws_forecast', cfg.get('inputs', {}).get('fit', {}).get('nws_forecast_path', '')),
        ('fit_glofas_forecast', cfg.get('inputs', {}).get('fit', {}).get('glofas_forecast_path', '')),
    ]
    for cov in cfg.get('inputs', {}).get('fit', {}).get('covariates', []) or []:
        if isinstance(cov, dict):
            dep_specs.append((f"covariate:{cov.get('name', '')}", cov.get('path', '')))
    for dep_type, dep_path in dep_specs:
        rows.append({'consumer_config': str(config_path), 'dependency_type': dep_type, 'dependency_path': str(dep_path or '')})
    return rows


def _run_id(cutoff: str, campaign_spec_id: str, family: str) -> str:
    return f'multimodel_{cutoff}_v8_{campaign_spec_id}_{family}'


def _build_run_config(
    template_cfg: dict[str, Any],
    *,
    run_id: str,
    artifact_root: Path,
    cutoff: str,
    bundle_artifact_root: Path,
    bundle_run_id: str,
    source_row: dict[str, str],
) -> dict[str, Any]:
    cfg = template_cfg
    shared = canonical_shared_paths(bundle_artifact_root, cutoff, bundle_run_id)

    _set_nested(cfg, ['run', 'run_id'], run_id)
    _set_nested(cfg, ['run', 'run_root'], str(runs_dir(artifact_root)))
    _set_nested(cfg, ['run', 'overwrite'], False)
    _set_nested(cfg, ['run', 'dry_run'], False)
    _set_nested(cfg, ['run', 'git_require_clean'], False)
    _set_nested(cfg, ['run', 'auto_suffix_on_collision'], False)

    _set_nested(cfg, ['stages', 'forecats'], False)
    for stage in ['data_prep_shared', 'fit', 'post', 'validate', 'report']:
        _set_nested(cfg, ['stages', stage], True)
    _set_nested(cfg, ['post', 'figures'], True)
    _set_nested(cfg, ['post', 'export_tables'], True)

    _set_nested(cfg, ['dates', 'data_start'], '1987-05-29')
    _set_nested(cfg, ['inputs', 'shared', 'prefer_forecats_snapshot'], False)
    _set_nested(cfg, ['inputs', 'shared', 'exact_source_snapshot_root'], '')
    _set_nested(cfg, ['inputs', 'forecats', 'existing_bundle_path'], str(shared['bundle_meta']))

    _set_nested(cfg, ['inputs', 'fit', 'parameters_path'], str(shared['parameters']))
    _set_nested(cfg, ['inputs', 'fit', 'retros_path'], str(shared['retros']))
    _set_nested(cfg, ['inputs', 'fit', 'retros_storage_scale'], 'log1p_cms')
    _set_nested(cfg, ['inputs', 'fit', 'nws_forecast_path'], str(shared['nws_forecast']))
    _set_nested(cfg, ['inputs', 'fit', 'nws_storage_scale'], 'raw_cms')
    _set_nested(cfg, ['inputs', 'fit', 'glofas_forecast_path'], str(shared['glofas_forecast']))
    _set_nested(cfg, ['inputs', 'fit', 'glofas_storage_scale'], 'raw_cms')
    _set_nested(
        cfg,
        ['inputs', 'fit', 'covariates'],
        [
            {'name': 'PPT', 'path': str(shared['cov_ppt'])},
            {'name': 'SOIL', 'path': str(shared['cov_soil'])},
            {'name': 'PCA', 'path': str(shared['cov_pca'])},
        ],
    )

    workers = (((cfg.get('fit') or {}).get('parallel') or {}).get('workers'))
    if workers is not None:
        _set_nested(cfg, ['run', 'threads', 'mc_cores'], int(workers))

    cfg['debug_he2_publication_relaunch'] = {
        'campaign_spec_id': DEFAULT_CAMPAIGN_SPEC_ID,
        'source_publication_run_id': source_row['run_id'],
        'source_publication_run_root': source_row['run_root'],
        'source_publication_resolved_config': source_row['resolved_config_path'],
        'campaign_lineage': source_row['campaign_lineage'],
        'manuscript_label': source_row['manuscript_label'],
        'family': source_row['family'],
        'implementation_mode': source_row.get('implementation_mode', ''),
        'likelihood_mode': source_row.get('likelihood_mode', ''),
        'forecast_transfer_mode': source_row.get('forecast_transfer_mode', ''),
        'publication_crps_display4': source_row['crps_display4'],
        'selected_spec_token': spec_token(source_row),
        'canonical_bundle_meta': str(shared['bundle_meta']),
        'canonical_bundle_root': str(shared['bundle_root']),
        'support_manifest': str(shared['support_manifest']),
        'canonical_fit_covariate_contract': 'PPT|SOIL|PCA(alias=GDPC1)',
    }
    return cfg


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='Build the unified 45-row HE2 Bayesian publication relaunch configs.')
    ap.add_argument('--config', required=True)
    ap.add_argument('--artifact-root')
    ap.add_argument('--matrix-dir')
    ap.add_argument('--config-output-dir')
    ap.add_argument('--cutoffs', nargs='*')
    ap.add_argument('--families', nargs='*')
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    campaign_path = Path(args.config).resolve() if Path(args.config).is_absolute() else (Path(__file__).resolve().parents[1] / args.config).resolve()
    campaign = load_yaml(campaign_path)

    campaign_cfg = campaign.get('campaign', {}) if isinstance(campaign.get('campaign'), dict) else {}
    source_cfg = campaign.get('source', {}) if isinstance(campaign.get('source'), dict) else {}
    bundles_cfg = campaign.get('bundles', {}) if isinstance(campaign.get('bundles'), dict) else {}
    queue_cfg = campaign.get('queue', {}) if isinstance(campaign.get('queue'), dict) else {}

    artifact_root = Path(resolve_artifact_root(args.artifact_root or campaign_cfg.get('artifact_root') or DEFAULT_RELAUNCH_ARTIFACT_ROOT))
    matrix_dir = ensure_dir(Path(args.matrix_dir).resolve() if args.matrix_dir else (artifact_root / 'control' / 'publication_relaunch_matrix'))
    config_output_dir = ensure_dir(Path(args.config_output_dir).resolve() if args.config_output_dir else (artifact_root / 'control' / 'generated_configs'))
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))
    ensure_dir(control_dir(artifact_root))

    bundle_artifact_root = Path(str(bundles_cfg.get('artifact_root') or DEFAULT_BUNDLE_ARTIFACT_ROOT)).resolve()
    bundle_run_id = str(bundles_cfg.get('bundle_run_id') or DEFAULT_BUNDLE_RUN_ID)
    manifest_path = Path(str(source_cfg.get('publication_manifest') or Path('reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv')))
    if not manifest_path.is_absolute():
        manifest_path = campaign_path.parents[1] / manifest_path
    manifest_path = manifest_path.resolve()
    campaign_spec_id = str(campaign_cfg.get('campaign_spec_id') or DEFAULT_CAMPAIGN_SPEC_ID)

    selected_cutoffs = set(str(c) for c in args.cutoffs) if args.cutoffs else set(str(c) for c in (campaign_cfg.get('cutoffs') or EXPECTED_CUTOFFS))
    selected_families = set(str(f) for f in args.families) if args.families else set(str(f) for f in (campaign_cfg.get('families') or EXPECTED_FAMILY_ORDER))

    rows = [row for row in load_publication_manifest_rows(manifest_path) if row['cutoff'] in selected_cutoffs and row['family'] in selected_families]
    if not rows:
        raise SystemExit('No manifest rows selected for relaunch build.')

    dependency_rows: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    generated_configs: list[Path] = []
    selection_rows: list[dict[str, Any]] = []

    order_index = 0
    for row in rows:
        cutoff = row['cutoff']
        family = row['family']
        source_cfg_path = Path(row['resolved_config_path'])
        if not source_cfg_path.exists():
            raise FileNotFoundError(f'Missing source resolved_config: {source_cfg_path}')
        shared = canonical_shared_paths(bundle_artifact_root, cutoff, bundle_run_id)
        missing = [str(path) for path in shared.values() if isinstance(path, Path) and not path.exists()]
        if missing:
            raise FileNotFoundError(f'Canonical shared bundle is incomplete for cutoff {cutoff}: {missing[:5]}')

        run_id = _run_id(cutoff, campaign_spec_id, family)
        config_path = config_output_dir / f'{run_id}.yaml'
        cfg = load_yaml(source_cfg_path)
        cfg = _build_run_config(
            cfg,
            run_id=run_id,
            artifact_root=artifact_root,
            cutoff=cutoff,
            bundle_artifact_root=bundle_artifact_root,
            bundle_run_id=bundle_run_id,
            source_row=row,
        )
        write_yaml(config_path, cfg)
        generated_configs.append(config_path)
        dependency_rows.extend(_dependency_rows(config_path, cfg))

        order_index += 1
        row_kind_value = row_kind(family)
        is_heavy = cutoff == HEAVY_CUTOFF
        plan_row = {
            'order_index': order_index,
            'cutoff': cutoff,
            'epsilon': campaign_spec_id,
            'epsilon_value': campaign_spec_id,
            'lane': family,
            'run_scope': 'he2_publication_relaunch',
            'run_id': run_id,
            'config_path': str(config_path),
            'compare_outdir': str(reports_dir(artifact_root) / f'multimodel_{cutoff}_v8_{campaign_spec_id}_compare'),
            'priority_group': 2 if is_heavy else 1,
            'max_concurrent_class': 'heavy' if is_heavy else 'ordinary',
            'family_id': family,
            'model_id': MODEL_ID_BY_FAMILY[family],
            'model_key': MODEL_KEY_BY_FAMILY[family],
            'likelihood_mode': row.get('likelihood_mode', ''),
            'transfer_mode': row.get('forecast_transfer_mode', ''),
            'authoritative_compare_dir': str(AUTHORITATIVE_COMPARE_BY_CUTOFF[cutoff]),
            'selected_compare_dir': str(AUTHORITATIVE_COMPARE_BY_CUTOFF[cutoff]),
            'selected_source_run': row['run_id'],
            'selected_source_type': row['campaign_lineage'],
            'selected_source_config': row['resolved_config_path'],
            'selected_mean_crps': row['crps_exact'],
            'selected_c_factor': '',
            'selected_epsilon': spec_token(row),
            'cutoff_rank': EXPECTED_CUTOFFS.index(cutoff) + 1,
            'manuscript_label': row['manuscript_label'],
            'row_kind': row_kind_value,
            'quantile_submodels': submodel_count(family),
            'publication_crps_display4': row['crps_display4'],
        }
        plan_rows.append(plan_row)
        selection_rows.append(dict(plan_row))

    plan_df = pd.DataFrame(plan_rows).sort_values(['cutoff_rank', 'order_index']).drop(columns=['cutoff_rank'])
    plan_df.to_csv(matrix_dir / 'matrix_plan.csv', index=False)

    dep_df = pd.DataFrame(dependency_rows).sort_values(['consumer_config', 'dependency_type']).reset_index(drop=True)
    dep_df.to_csv(matrix_dir / 'dependency_preservation.csv', index=False)

    selection_df = pd.DataFrame(selection_rows).sort_values(['cutoff', 'manuscript_label']).reset_index(drop=True)
    selection_df.to_csv(matrix_dir / 'selection_summary.csv', index=False)

    status_path = matrix_dir / 'matrix_status.csv'
    if not status_path.exists():
        with status_path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle)
            writer.writerow([
                'cutoff', 'epsilon', 'lane', 'run_id', 'phase', 'status', 'started_at', 'finished_at',
                'manifest_path', 'latest_log_mtime', 'disk_free_gb', 'note',
            ])

    metadata = {
        'campaign_id': str(campaign_cfg.get('campaign_id', 'he2_bayesian_publication_relaunch')),
        'campaign_spec_id': campaign_spec_id,
        'campaign_config': str(campaign_path),
        'artifact_root': str(artifact_root),
        'matrix_dir': str(matrix_dir),
        'config_output_dir': str(config_output_dir),
        'publication_manifest': str(manifest_path),
        'bundle_artifact_root': str(bundle_artifact_root),
        'bundle_run_id': bundle_run_id,
        'compare_builder': 'scripts/build_multimodel_v8_all9_feature_compare_bundle.py',
        'queue': {
            'ordinary_max_concurrent': int(queue_cfg.get('ordinary_max_concurrent', 2)),
            'pause_free_gb': float(queue_cfg.get('pause_free_gb', 180)),
            'launch_free_gb': float(queue_cfg.get('launch_free_gb', 220)),
            'heavy_free_gb': float(queue_cfg.get('heavy_free_gb', 240)),
            'heavy_cutoff_max_concurrent': int(queue_cfg.get('heavy_cutoff_max_concurrent', 1)),
            'heavy_cutoff_blocks_ordinary': bool(queue_cfg.get('heavy_cutoff_blocks_ordinary', True)),
            'poll_seconds': int(queue_cfg.get('poll_seconds', 60)),
        },
    }
    write_yaml(matrix_dir / 'matrix_metadata.yaml', metadata)
    write_yaml(matrix_dir / 'campaign_snapshot.yaml', {'campaign': campaign, 'campaign_path': str(campaign_path)})

    launch_env = '\n'.join([
        f'ARTIFACT_ROOT={artifact_root}',
        f'MATRIX_DIR={matrix_dir}',
        f'ORDINARY_MAX_CONCURRENT={metadata["queue"]["ordinary_max_concurrent"]}',
        f'PAUSE_FREE_GB={metadata["queue"]["pause_free_gb"]}',
        f'LAUNCH_FREE_GB={metadata["queue"]["launch_free_gb"]}',
        f'HEAVY_FREE_GB={metadata["queue"]["heavy_free_gb"]}',
        f'HEAVY_CUTOFF_MAX_CONCURRENT={metadata["queue"]["heavy_cutoff_max_concurrent"]}',
        f'HEAVY_CUTOFF_BLOCKS_ORDINARY={1 if metadata["queue"]["heavy_cutoff_blocks_ordinary"] else 0}',
        f'POLL_SECONDS={metadata["queue"]["poll_seconds"]}',
        '',
    ])
    (matrix_dir / 'launch_settings.env').write_text(launch_env, encoding='utf-8')
    (matrix_dir / 'queue.log').touch()

    lines = [
        '# HE2 Bayesian Publication Relaunch Scope',
        '',
        f'- campaign_config: `{campaign_path}`',
        f'- artifact_root: `{artifact_root}`',
        f'- matrix_dir: `{matrix_dir}`',
        f'- config_output_dir: `{config_output_dir}`',
        f'- publication_manifest: `{manifest_path}`',
        f'- bundle_artifact_root: `{bundle_artifact_root}`',
        f'- bundle_run_id: `{bundle_run_id}`',
        f'- generated_configs: `{len(generated_configs)}`',
        '',
        '## Workload',
        f'- row launches: `{len(plan_df)}`',
        f'- total fitted submodels: `{int(selection_df["quantile_submodels"].astype(int).sum())}`',
        '',
        '## Queue defaults',
        f'- ordinary_max_concurrent: `{metadata["queue"]["ordinary_max_concurrent"]}`',
        f'- pause_free_gb: `{metadata["queue"]["pause_free_gb"]}`',
        f'- launch_free_gb: `{metadata["queue"]["launch_free_gb"]}`',
        f'- heavy_free_gb: `{metadata["queue"]["heavy_free_gb"]}`',
        f'- heavy_cutoff_max_concurrent: `{metadata["queue"]["heavy_cutoff_max_concurrent"]}`',
        f'- heavy_cutoff_blocks_ordinary: `{metadata["queue"]["heavy_cutoff_blocks_ordinary"]}`',
        f'- poll_seconds: `{metadata["queue"]["poll_seconds"]}`',
        '',
        '## Current disk headroom',
        f'- artifact disk free GB: `{artifact_disk_free_gb(artifact_root)}`',
    ]
    (matrix_dir / 'he2_publication_relaunch_scope.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(f'artifact_root={artifact_root}')
    print(f'matrix_dir={matrix_dir}')
    print(f'config_output_dir={config_output_dir}')
    print(f'generated_configs={len(generated_configs)}')
    print(f'plan_rows={len(plan_df)}')
    print(f'selection_rows={len(selection_df)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
