#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / 'repro' / 'reports' / 'he2_relaunch_incidents' / '20260515_q50_blend_fix_and_overnight_ladder_r01'
EVENTS_PATH = REPORT_ROOT / 'q50_overnight_ladder_events.jsonl'
SUMMARY_PATH = REPORT_ROOT / 'q50_overnight_ladder_summary.json'


@dataclass(frozen=True)
class Candidate:
    name: str
    template: str
    batch: str
    description: str
    gamma_cap: float
    sigma_cap: float


CANDIDATES = [
    Candidate(
        name='baseline_rerun',
        template='config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_rerun_20260515.template.yaml',
        batch='config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_rerun_20260515.yaml',
        description='Same q50 state-freeze candidate after fixing materialized/raw blend mismatch.',
        gamma_cap=0.15,
        sigma_cap=0.25,
    ),
    Candidate(
        name='stepcap10',
        template='config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap10_20260515.template.yaml',
        batch='config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap10_20260515.yaml',
        description='Narrow q50-only damping tighten: gamma cap 0.10, log-sigma cap 0.20.',
        gamma_cap=0.10,
        sigma_cap=0.20,
    ),
    Candidate(
        name='stepcap075',
        template='config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap075_20260515.template.yaml',
        batch='config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap075_20260515.yaml',
        description='Second narrow q50-only damping tighten: gamma cap 0.075, log-sigma cap 0.15.',
        gamma_cap=0.075,
        sigma_cap=0.15,
    ),
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='Run the q50 state-freeze overnight ladder until one candidate passes or all fail.')
    ap.add_argument('--poll-seconds', type=int, default=60)
    ap.add_argument('--profile', default='overnight_q50_ladder')
    ap.add_argument('--start-at', choices=[c.name for c in CANDIDATES], default=CANDIDATES[0].name)
    ap.add_argument('--resume', action='store_true', help='Resume from the most recent launch event instead of launching a new baseline rung.')
    return ap.parse_args()


def ensure_report_root() -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def read_matrix_row(matrix_path: Path) -> dict[str, str] | None:
    if not matrix_path.exists():
        return None
    with matrix_path.open('r', encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return None
    return rows[0]


def read_controller_exit_code(queue_log: Path) -> int | None:
    if not queue_log.exists():
        return None
    exit_code = None
    for line in queue_log.read_text(encoding='utf-8').splitlines():
        if 'controller stop exit_code=' in line:
            try:
                exit_code = int(line.rsplit('=', 1)[-1])
            except ValueError:
                pass
    return exit_code


def pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def emit_event(kind: str, payload: dict[str, Any]) -> None:
    ensure_report_root()
    record = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'kind': kind, **payload}
    with EVENTS_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, sort_keys=True) + '\n')


def load_events() -> list[dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return []
    records: list[dict[str, Any]] = []
    for raw in EVENTS_PATH.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def candidate_by_name(name: str) -> Candidate:
    return next(candidate for candidate in CANDIDATES if candidate.name == name)


def template_matrix_and_queue(candidate: Candidate) -> tuple[Path, Path, Path]:
    template = load_yaml(ROOT / candidate.template)
    matrix_dir = Path(template['campaign']['matrix_dir'])
    return matrix_dir / 'matrix_status.csv', matrix_dir / 'queue.log', Path(template['campaign']['artifact_root'])


def launch_candidate(candidate: Candidate, profile: str) -> tuple[int, Path, Path, Path]:
    template_path = ROOT / candidate.template
    batch_path = ROOT / candidate.batch
    template = load_yaml(template_path)
    matrix_dir = Path(template['campaign']['matrix_dir'])
    queue_log = matrix_dir / 'queue.log'
    matrix_path = matrix_dir / 'matrix_status.csv'
    artifact_root = Path(template['campaign']['artifact_root'])

    cmd = [
        'python3',
        'scripts/launch_he2_bayesian_publication_relaunch.py',
        '--config', str(template_path),
        '--batch-file', str(batch_path),
        '--profile', profile,
        '--skip-validate',
        '--reset-state',
    ]
    proc = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    stdout_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    controller_pid = int(stdout_lines[-1])
    emit_event('launch', {
        'candidate': asdict(candidate),
        'controller_pid': controller_pid,
        'matrix_dir': str(matrix_dir),
        'artifact_root': str(artifact_root),
        'command': cmd,
    })
    return controller_pid, matrix_path, queue_log, artifact_root


def wait_for_candidate(candidate: Candidate, controller_pid: int, matrix_path: Path, queue_log: Path, poll_seconds: int) -> dict[str, Any]:
    while True:
        row = read_matrix_row(matrix_path)
        if row and row.get('status') in {'pass', 'fail'}:
            exit_code = read_controller_exit_code(queue_log)
            result = {
                'candidate': asdict(candidate),
                'status': row.get('status'),
                'phase': row.get('phase'),
                'matrix_row': row,
                'controller_exit_code': exit_code,
                'controller_pid': controller_pid,
            }
            emit_event('result', result)
            return result
        if not pid_running(controller_pid):
            exit_code = read_controller_exit_code(queue_log)
            result = {
                'candidate': asdict(candidate),
                'status': 'unknown',
                'phase': row.get('phase') if row else None,
                'matrix_row': row,
                'controller_exit_code': exit_code,
                'controller_pid': controller_pid,
            }
            emit_event('result', result)
            return result
        time.sleep(poll_seconds)


def resume_active_candidate(poll_seconds: int) -> dict[str, Any] | None:
    events = load_events()
    launches = [event for event in events if event.get('kind') == 'launch']
    results = [event for event in events if event.get('kind') == 'result']
    if not launches:
        return None
    latest_launch = launches[-1]
    latest_name = latest_launch['candidate']['name']
    if any(event.get('candidate', {}).get('name') == latest_name for event in results):
        return None
    candidate = candidate_by_name(latest_name)
    matrix_path, queue_log, artifact_root = template_matrix_and_queue(candidate)
    result = wait_for_candidate(candidate, int(latest_launch['controller_pid']), matrix_path, queue_log, poll_seconds)
    result['artifact_root'] = str(artifact_root)
    return result


def main() -> int:
    args = parse_args()
    ensure_report_root()
    ladder_results: list[dict[str, Any]] = []

    if args.resume:
        resumed = resume_active_candidate(args.poll_seconds)
        if resumed is None:
            emit_event('resume_noop', {'reason': 'no_active_launch'})
            return 0
        ladder_results = [resumed]
        SUMMARY_PATH.write_text(json.dumps({'results': ladder_results}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        if resumed['status'] == 'pass':
            emit_event('ladder_complete', {'outcome': 'pass', 'winning_candidate': resumed['candidate']['name'], 'mode': 'resume'})
            return 0
        if resumed['status'] == 'unknown':
            emit_event('ladder_complete', {'outcome': 'unknown', 'stopped_at': resumed['candidate']['name'], 'mode': 'resume'})
            return 2
        start_index = next(i for i, candidate in enumerate(CANDIDATES) if candidate.name == resumed['candidate']['name']) + 1
    else:
        start_index = next(i for i, candidate in enumerate(CANDIDATES) if candidate.name == args.start_at)

    for candidate in CANDIDATES[start_index:]:
        controller_pid, matrix_path, queue_log, artifact_root = launch_candidate(candidate, args.profile)
        result = wait_for_candidate(candidate, controller_pid, matrix_path, queue_log, args.poll_seconds)
        result['artifact_root'] = str(artifact_root)
        ladder_results.append(result)
        SUMMARY_PATH.write_text(json.dumps({'results': ladder_results}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        if result['status'] == 'pass':
            emit_event('ladder_complete', {'outcome': 'pass', 'winning_candidate': candidate.name})
            return 0
        if result['status'] == 'unknown':
            emit_event('ladder_complete', {'outcome': 'unknown', 'stopped_at': candidate.name})
            return 2

    emit_event('ladder_complete', {'outcome': 'all_failed'})
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
