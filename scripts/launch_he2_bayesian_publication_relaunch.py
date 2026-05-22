#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_20260510.template.yaml'


def load_yaml(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def read_launch_settings(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        key, _, value = line.partition('=')
        settings[key.strip()] = value.strip()
    return settings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='Build, validate, and detached-launch the HE2 Bayesian publication relaunch controller.')
    ap.add_argument('--template', '--config', dest='template', default=str(DEFAULT_TEMPLATE))
    ap.add_argument('--skip-validate', action='store_true')
    ap.add_argument('--reset-state', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
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
    ap.add_argument('--start-monitor', action='store_true')
    ap.add_argument('--monitor-out-dir')
    ap.add_argument('--monitor-interval', type=float, default=300.0)
    ap.add_argument('--monitor-max-snapshots', type=int, default=288)
    return ap.parse_args(argv)


def extend_with_selection_args(cmd: list[str], args: argparse.Namespace) -> list[str]:
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


def main() -> int:
    args = parse_args()
    template_path = Path(args.template).resolve()
    template = load_yaml(template_path)
    campaign = template.get('campaign', {})
    matrix_dir = Path(campaign['matrix_dir']).resolve()
    artifact_root = Path(campaign['artifact_root']).resolve()

    build_cmd = ['python3', 'scripts/build_he2_bayesian_publication_relaunch_configs.py', '--config', str(template_path)]
    subprocess.run(extend_with_selection_args(build_cmd, args), cwd=ROOT, check=True)

    if not args.skip_validate:
        validate_cmd = ['python3', 'scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py', '--config', str(template_path)]
        subprocess.run(extend_with_selection_args(validate_cmd, args), cwd=ROOT, check=True)

    if args.reset_state and not args.dry_run:
        subprocess.run(
            ['python3', 'scripts/reset_he2_bayesian_publication_relaunch_state.py', '--template', str(template_path)],
            cwd=ROOT,
            check=True,
        )

    launch_settings = read_launch_settings(matrix_dir / 'launch_settings.env')
    queue_cmd = [
        'python3', 'scripts/run_multimodel_v8_queue.py',
        '--matrix-dir', str(matrix_dir),
        '--artifact-root', str(artifact_root),
        '--ordinary-max-concurrent', launch_settings['ORDINARY_MAX_CONCURRENT'],
        '--pause-free-gb', launch_settings['PAUSE_FREE_GB'],
        '--launch-free-gb', launch_settings['LAUNCH_FREE_GB'],
        '--heavy-free-gb', launch_settings['HEAVY_FREE_GB'],
        '--heavy-cutoff-max-concurrent', launch_settings.get('HEAVY_CUTOFF_MAX_CONCURRENT', '1'),
        '--poll-seconds', launch_settings['POLL_SECONDS'],
    ]
    if launch_settings.get('HEAVY_CUTOFF_BLOCKS_ORDINARY', '1') in {'0', 'false', 'False', 'no'}:
        queue_cmd.append('--no-heavy-cutoff-blocks-ordinary')
    monitor_out_dir = Path(args.monitor_out_dir).resolve() if args.monitor_out_dir else (
        ROOT / 'reports' / f"{campaign.get('campaign_id', 'he2_relaunch')}_live"
    )
    monitor_cmd = [
        'python3', 'scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py',
        '--artifact-root', str(artifact_root),
        '--matrix-dir', str(matrix_dir),
        '--out-dir', str(monitor_out_dir),
        '--interval', str(args.monitor_interval),
        '--max-snapshots', str(args.monitor_max_snapshots),
        '--refresh-matrix',
    ]

    if args.dry_run:
        print(' '.join(queue_cmd))
        if args.start_monitor:
            print(' '.join(monitor_cmd))
        return 0

    log_path = matrix_dir / 'queue.log'
    log_handle = log_path.open('a', encoding='utf-8')
    proc = subprocess.Popen(queue_cmd, stdout=log_handle, stderr=subprocess.STDOUT, start_new_session=True)
    time.sleep(2)
    state_dir = matrix_dir / 'controller_state'
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / 'controller.pid').write_text(f'{proc.pid}\n', encoding='utf-8')
    launch_payload = {
        'pid': proc.pid,
        'queue_cmd': queue_cmd,
        'matrix_dir': str(matrix_dir),
        'artifact_root': str(artifact_root),
        'template': str(template_path),
    }
    if args.start_monitor:
        monitor_out_dir.mkdir(parents=True, exist_ok=True)
        monitor_log = monitor_out_dir / 'monitor.log'
        monitor_handle = monitor_log.open('a', encoding='utf-8')
        monitor_proc = subprocess.Popen(
            monitor_cmd,
            cwd=ROOT,
            stdout=monitor_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        (state_dir / 'monitor.pid').write_text(f'{monitor_proc.pid}\n', encoding='utf-8')
        launch_payload.update({
            'monitor_pid': monitor_proc.pid,
            'monitor_cmd': monitor_cmd,
            'monitor_out_dir': str(monitor_out_dir),
            'monitor_log': str(monitor_log),
        })
    (state_dir / 'last_launch.json').write_text(
        json.dumps(launch_payload, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    print(proc.pid)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
