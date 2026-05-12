#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from he2_publication_relaunch_lib import ensure_dir, load_yaml, write_yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / 'config' / 'median_overnight_campaign_exdqlm_multivar_keep_20210123_q50_20260511.yaml'
PROBE_RUNNER = ROOT / 'scripts' / 'run_exdqlm_median_warmup_probes.py'


@dataclass(frozen=True)
class ProbeTask:
    wave_id: str
    wave_order: int
    batch: str
    probe_id: str
    description: str
    config_patch: dict[str, Any]
    screening_patch: dict[str, Any]
    tags: list[str]


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _leaf_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_leaf_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_leaf_count(v) for v in value)
    return 1


def _flatten_tasks(
    campaign_cfg: dict[str, Any],
    *,
    selected_waves: set[str] | None = None,
    selected_probe_ids: set[str] | None = None,
    max_probes: int | None = None,
) -> list[ProbeTask]:
    tasks: list[ProbeTask] = []
    for wave_order, wave in enumerate(campaign_cfg.get('waves', []), start=1):
        wave_id = str(wave['id'])
        if selected_waves and wave_id not in selected_waves:
            continue
        for probe in wave.get('probes', []):
            probe_id = str(probe['id'])
            if selected_probe_ids and probe_id not in selected_probe_ids:
                continue
            tasks.append(
                ProbeTask(
                    wave_id=wave_id,
                    wave_order=wave_order,
                    batch=str(probe.get('batch', wave.get('batch', 'unclassified'))),
                    probe_id=probe_id,
                    description=str(probe.get('description', '')).strip(),
                    config_patch=copy.deepcopy(probe.get('config_patch', {})),
                    screening_patch=copy.deepcopy(probe.get('screening_patch', {})),
                    tags=[str(x) for x in probe.get('tags', [])],
                )
            )
            if max_probes is not None and len(tasks) >= max_probes:
                return tasks
    return tasks


def _build_single_probe_config(campaign_cfg: dict[str, Any], task: ProbeTask) -> dict[str, Any]:
    campaign_id = str(campaign_cfg['campaign']['id'])
    artifact_root = Path(str(campaign_cfg['artifact_root'])).resolve() / 'probes' / task.wave_id / task.probe_id
    screening_cfg = _deep_merge(copy.deepcopy(campaign_cfg['screening']), task.screening_patch)
    return {
        'probe': {
            'id': f'{campaign_id}__{task.wave_id}__{task.probe_id}',
            'description': task.description,
        },
        'base_generated_config': str(Path(str(campaign_cfg['base_generated_config'])).resolve()),
        'artifact_root': str(artifact_root),
        'screening': screening_cfg,
        'probes': [
            {
                'id': task.probe_id,
                'description': task.description,
                'config_patch': task.config_patch,
            }
        ],
        'confirmation': {'enabled': False},
    }


def _score_row(row: dict[str, Any]) -> tuple[Any, ...]:
    inf = float('inf')
    return (
        0 if bool(row.get('selected_healthy', False)) else 1,
        int(row.get('guard_events') or 0),
        int(row.get('hessian_failures') or 0),
        float(row.get('max_sigma_exp') if row.get('max_sigma_exp') is not None else inf),
        float(row.get('last_conv_check') if row.get('last_conv_check') is not None else inf),
        int(row.get('patch_leaf_count') or 0),
        int(row.get('wave_order') or 0),
        str(row.get('probe_id') or ''),
    )


def _read_single_probe_outputs(artifact_root: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    reports_root = artifact_root / 'reports'
    summary_path = reports_root / 'winner_summary.json'
    results_path = reports_root / 'probe_results.csv'
    if not summary_path.exists() or not results_path.exists():
        return None, None
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    with results_path.open('r', encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    screening_row = None
    for row in rows:
        if row.get('phase') == 'screening':
            screening_row = row
            break
    return summary, screening_row


def _parse_optional_float(value: Any) -> float | None:
    if value in (None, '', 'NA'):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def _parse_optional_int(value: Any) -> int | None:
    if value in (None, '', 'NA'):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _build_result_row(
    task: ProbeTask,
    *,
    config_path: Path,
    artifact_root: Path,
    worker_log_path: Path,
    process_exit_code: int,
    elapsed_seconds: float,
) -> dict[str, Any]:
    summary, screening_row = _read_single_probe_outputs(artifact_root)
    if summary is None or screening_row is None:
        return {
            'wave_id': task.wave_id,
            'wave_order': task.wave_order,
            'batch': task.batch,
            'probe_id': task.probe_id,
            'description': task.description,
            'selected_healthy': False,
            'best_healthy': False,
            'selected_note': 'missing_probe_summary',
            'best_note': 'missing_probe_summary',
            'guard_events': None,
            'hessian_failures': None,
            'refreezes': None,
            'last_iter': None,
            'last_updates': None,
            'max_sigma_exp': None,
            'max_state_norm_sq': None,
            'last_conv_check': None,
            'process_exit_code': process_exit_code,
            'elapsed_seconds': round(elapsed_seconds, 3),
            'artifact_root': str(artifact_root),
            'config_path': str(config_path),
            'worker_log_path': str(worker_log_path),
            'patch_leaf_count': _leaf_count(task.config_patch),
            'config_patch_json': json.dumps(task.config_patch, sort_keys=True),
            'tags': ','.join(task.tags),
        }
    return {
        'wave_id': task.wave_id,
        'wave_order': task.wave_order,
        'batch': task.batch,
        'probe_id': task.probe_id,
        'description': task.description,
        'selected_healthy': bool(summary.get('selected_healthy', False)),
        'best_healthy': bool(summary.get('best_healthy', False)),
        'selected_note': str(summary.get('selected_note', '')),
        'best_note': str(summary.get('best_note', '')),
        'guard_events': _parse_optional_int(screening_row.get('guard_events')),
        'hessian_failures': _parse_optional_int(screening_row.get('hessian_failures')),
        'refreezes': _parse_optional_int(screening_row.get('refreezes')),
        'last_iter': _parse_optional_int(screening_row.get('last_iter')),
        'last_updates': _parse_optional_int(screening_row.get('last_updates')),
        'max_sigma_exp': _parse_optional_float(screening_row.get('max_sigma_exp')),
        'max_state_norm_sq': _parse_optional_float(screening_row.get('max_state_norm_sq')),
        'last_conv_check': _parse_optional_float(screening_row.get('last_conv_check')),
        'process_exit_code': process_exit_code,
        'elapsed_seconds': round(elapsed_seconds, 3),
        'artifact_root': str(artifact_root),
        'config_path': str(config_path),
        'worker_log_path': str(worker_log_path),
        'patch_leaf_count': _leaf_count(task.config_patch),
        'config_patch_json': json.dumps(task.config_patch, sort_keys=True),
        'tags': ','.join(task.tags),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_reports(campaign_cfg: dict[str, Any], tasks: list[ProbeTask], results: list[dict[str, Any]], reports_root: Path, progress_state: dict[str, Any]) -> None:
    ensure_dir(reports_root)
    ordered_results = sorted(results, key=_score_row)
    _write_csv(reports_root / 'campaign_results.csv', ordered_results)
    (reports_root / 'campaign_results.json').write_text(json.dumps(ordered_results, indent=2), encoding='utf-8')
    (reports_root / 'campaign_progress.json').write_text(json.dumps(progress_state, indent=2), encoding='utf-8')

    wave_counts: dict[str, int] = {}
    wave_healthy: dict[str, int] = {}
    for row in ordered_results:
        wave_counts[row['wave_id']] = wave_counts.get(row['wave_id'], 0) + 1
        if row['selected_healthy']:
            wave_healthy[row['wave_id']] = wave_healthy.get(row['wave_id'], 0) + 1

    md_lines = [
        f"# {campaign_cfg['campaign']['id']}",
        '',
        str(campaign_cfg['campaign'].get('description', '')).strip(),
        '',
        f"- Total probes planned: `{len(tasks)}`",
        f"- Completed probes: `{progress_state.get('completed', 0)}`",
        f"- Healthy probes: `{sum(1 for row in ordered_results if row['selected_healthy'])}`",
        f"- Concurrency: `{progress_state.get('concurrency')}`",
        '',
        '## Wave Summary',
        '',
        '| Wave | Completed | Healthy |',
        '|---|---:|---:|',
    ]
    for wave in campaign_cfg.get('waves', []):
        wave_id = str(wave['id'])
        md_lines.append(f"| `{wave_id}` | `{wave_counts.get(wave_id, 0)}` | `{wave_healthy.get(wave_id, 0)}` |")

    md_lines += [
        '',
        '## Ranked Results',
        '',
        '| Wave | Batch | Probe | Healthy | Guards | Hessian | Updates | Max sigma | Max state | Last conv | Note |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    for row in ordered_results:
        md_lines.append(
            f"| `{row['wave_id']}` | `{row['batch']}` | `{row['probe_id']}` | `{row['selected_healthy']}` | `{row['guard_events']}` | `{row['hessian_failures']}` | `{row['last_updates']}` | `{row['max_sigma_exp']}` | `{row['max_state_norm_sq']}` | `{row['last_conv_check']}` | {row['selected_note']} |"
        )
    (reports_root / 'MORNING_SUMMARY.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')


def _run_probe_task(task: ProbeTask, config_path: Path, artifact_root: Path, worker_log_path: Path, skip_existing: bool) -> dict[str, Any]:
    ensure_dir(worker_log_path.parent)
    cmd = ['python3', str(PROBE_RUNNER), '--config', str(config_path)]
    if skip_existing:
        cmd.append('--skip-existing')
    started = time.time()
    with worker_log_path.open('w', encoding='utf-8') as log_handle:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
    elapsed = time.time() - started
    return _build_result_row(
        task,
        config_path=config_path,
        artifact_root=artifact_root,
        worker_log_path=worker_log_path,
        process_exit_code=proc.returncode,
        elapsed_seconds=elapsed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description='Run sidecar exdqlm quantile stabilization campaign.')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-existing', action='store_true')
    parser.add_argument('--concurrency', type=int, default=None)
    parser.add_argument('--wave', action='append', default=[])
    parser.add_argument('--probe-id', action='append', default=[])
    parser.add_argument('--max-probes', type=int, default=None)
    args = parser.parse_args()

    campaign_cfg = load_yaml(args.config)
    selected_waves = {str(x) for x in args.wave} if args.wave else None
    selected_probe_ids = {str(x) for x in args.probe_id} if args.probe_id else None
    tasks = _flatten_tasks(
        campaign_cfg,
        selected_waves=selected_waves,
        selected_probe_ids=selected_probe_ids,
        max_probes=args.max_probes,
    )
    if not tasks:
        raise SystemExit('No probes selected for overnight campaign.')

    artifact_root = Path(str(campaign_cfg['artifact_root'])).resolve()
    control_root = ensure_dir(artifact_root / 'control')
    generated_root = ensure_dir(control_root / 'generated_single_probe_configs')
    worker_logs_root = ensure_dir(control_root / 'worker_logs')
    reports_root = ensure_dir(artifact_root / 'reports')

    execution_cfg = campaign_cfg.get('execution', {})
    concurrency = int(args.concurrency or execution_cfg.get('concurrency', 24))
    if concurrency < 1:
        raise SystemExit('Concurrency must be >= 1')

    generated_entries: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    task_bundle: list[tuple[ProbeTask, Path, Path, Path]] = []
    for task in tasks:
        single_cfg = _build_single_probe_config(campaign_cfg, task)
        config_path = generated_root / f'{task.wave_id}__{task.probe_id}.yaml'
        write_yaml(config_path, single_cfg)
        artifact_probe_root = Path(str(single_cfg['artifact_root']))
        worker_log_path = worker_logs_root / f'{task.wave_id}__{task.probe_id}.log'
        task_bundle.append((task, config_path, artifact_probe_root, worker_log_path))
        generated_entries.append({'probe_id': task.probe_id, 'config_path': str(config_path), 'artifact_root': str(artifact_probe_root)})
        plan_rows.append({
            'wave_id': task.wave_id,
            'wave_order': task.wave_order,
            'batch': task.batch,
            'probe_id': task.probe_id,
            'description': task.description,
            'patch_leaf_count': _leaf_count(task.config_patch),
            'config_patch_json': json.dumps(task.config_patch, sort_keys=True),
            'tags': ','.join(task.tags),
            'config_path': str(config_path),
            'artifact_root': str(artifact_probe_root),
            'worker_log_path': str(worker_log_path),
        })
    _write_csv(reports_root / 'campaign_plan.csv', plan_rows)
    (reports_root / 'campaign_plan.json').write_text(json.dumps(plan_rows, indent=2), encoding='utf-8')
    (control_root / 'generated_single_probe_configs.json').write_text(json.dumps(generated_entries, indent=2), encoding='utf-8')

    progress_state = {
        'campaign_id': str(campaign_cfg['campaign']['id']),
        'completed': 0,
        'total': len(task_bundle),
        'healthy': 0,
        'concurrency': concurrency,
        'dry_run': bool(args.dry_run),
        'started_at_epoch': time.time(),
    }
    _write_reports(campaign_cfg, tasks, [], reports_root, progress_state)

    if args.dry_run:
        return 0

    results: list[dict[str, Any]] = []
    for wave in campaign_cfg.get('waves', []):
        wave_id = str(wave['id'])
        wave_tasks = [bundle for bundle in task_bundle if bundle[0].wave_id == wave_id]
        if not wave_tasks:
            continue
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_map = {
                executor.submit(_run_probe_task, task, config_path, artifact_probe_root, worker_log_path, args.skip_existing): (task, config_path)
                for task, config_path, artifact_probe_root, worker_log_path in wave_tasks
            }
            for future in concurrent.futures.as_completed(future_map):
                row = future.result()
                results.append(row)
                progress_state['completed'] = len(results)
                progress_state['healthy'] = sum(1 for item in results if item.get('selected_healthy'))
                _write_reports(campaign_cfg, tasks, results, reports_root, progress_state)

    progress_state['finished_at_epoch'] = time.time()
    progress_state['healthy'] = sum(1 for item in results if item.get('selected_healthy'))
    _write_reports(campaign_cfg, tasks, results, reports_root, progress_state)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
