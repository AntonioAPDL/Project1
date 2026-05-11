#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from he2_publication_relaunch_lib import ensure_dir, load_yaml, write_yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / 'config' / 'median_warmup_probes_exdqlm_multivar_keep_20210123_q50_20260510.yaml'

PROGRESS_RE = re.compile(
    r"\[gamsig_progress\].*?iter=(?P<iter>\d+).*?sigma_exp=(?P<sigma>[^ ]+).*?gamma_exp=(?P<gamma>[^ ]+)"
    r".*?state_norm_sq=(?P<state>[^ ]+).*?conv_check=(?P<conv>[^ ]+).*?gamsig_update_iters=(?P<updates>\d+)",
    re.DOTALL,
)


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _parse_num(token: str) -> float | None:
    token = str(token).strip()
    if not token or token.upper() == 'NA':
        return None
    try:
        value = float(token)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return value


def _leaf_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_leaf_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_leaf_count(v) for v in value)
    return 1


@dataclass
class ProbeResult:
    probe_id: str
    phase: str
    run_id: str
    exit_code: int
    log_path: Path
    run_root: Path
    guard_events: int
    hessian_failures: int
    refreezes: int
    last_iter: int
    last_updates: int
    last_sigma_exp: float | None
    max_sigma_exp: float | None
    last_state_norm_sq: float | None
    max_state_norm_sq: float | None
    last_conv_check: float | None
    healthy: bool
    note: str

    def row(self) -> dict[str, Any]:
        return {
            'probe_id': self.probe_id,
            'phase': self.phase,
            'run_id': self.run_id,
            'exit_code': self.exit_code,
            'guard_events': self.guard_events,
            'hessian_failures': self.hessian_failures,
            'refreezes': self.refreezes,
            'last_iter': self.last_iter,
            'last_updates': self.last_updates,
            'last_sigma_exp': self.last_sigma_exp,
            'max_sigma_exp': self.max_sigma_exp,
            'last_state_norm_sq': self.last_state_norm_sq,
            'max_state_norm_sq': self.max_state_norm_sq,
            'last_conv_check': self.last_conv_check,
            'healthy': self.healthy,
            'note': self.note,
            'log_path': str(self.log_path),
            'run_root': str(self.run_root),
        }


def _q_label(q: float) -> str:
    return f"q={int(round(q * 100)):02d}"


def _stage_map(enabled: dict[str, Any]) -> dict[str, bool]:
    base = {
        'forecats': False,
        'data_prep_shared': False,
        'fit': False,
        'post': False,
        'validate': False,
        'report': False,
    }
    for key in list(base):
        if key in enabled:
            base[key] = bool(enabled[key])
    return base


def _prepare_config(
    base_cfg: dict[str, Any],
    *,
    artifact_root: Path,
    run_id: str,
    quantile: float,
    workers: int,
    mc_cores: int,
    stages: dict[str, Any],
    gamma_sigma_patch: dict[str, Any],
    probe_patch: dict[str, Any],
) -> dict[str, Any]:
    cfg = copy.deepcopy(base_cfg)
    cfg['run']['run_id'] = run_id
    cfg['run']['run_root'] = str((artifact_root / 'runs').resolve())
    cfg['run']['overwrite'] = False
    cfg['run']['auto_suffix_on_collision'] = False
    cfg['fit']['quantiles'] = [float(quantile)]
    cfg.setdefault('fit', {}).setdefault('parallel', {})
    cfg['fit']['parallel']['mode'] = 'global_models'
    cfg['fit']['parallel']['workers'] = int(workers)
    cfg.setdefault('run', {}).setdefault('threads', {})
    cfg['run']['threads']['mc_cores'] = int(mc_cores)
    cfg['stages'] = _stage_map(stages)
    cfg['models']['run_exdqlm_multivar'] = True
    cfg['models']['run_exdqlm_univar'] = False
    cfg['models']['run_ndlm_main'] = False
    cfg['models']['run_ndlm_univar'] = False
    cfg['fit']['exdqlm_multivar']['gamma_sigma'] = _deep_merge(
        cfg['fit']['exdqlm_multivar']['gamma_sigma'],
        gamma_sigma_patch,
    )
    cfg = _deep_merge(cfg, probe_patch)
    return cfg


def _analyze_log(log_path: Path, rules: dict[str, Any], probe_id: str, phase: str, run_id: str, exit_code: int, run_root: Path) -> ProbeResult:
    text = log_path.read_text(encoding='utf-8', errors='ignore') if log_path.exists() else ''
    guard_events = len(re.findall(r'non-finite dq_transf', text))
    hessian_failures = len(re.findall(r'non-invertible Hessian', text))
    refreezes = len(re.findall(r'\[gamsig_refreeze\]', text))
    progresses = list(PROGRESS_RE.finditer(text))

    last_iter = -1
    last_updates = -1
    last_sigma = None
    max_sigma = None
    last_state = None
    max_state = None
    last_conv = None
    if progresses:
        for m in progresses:
            last_iter = int(m.group('iter'))
            last_updates = int(m.group('updates'))
            sigma = _parse_num(m.group('sigma'))
            state = _parse_num(m.group('state'))
            conv = _parse_num(m.group('conv'))
            last_sigma = sigma
            last_state = state
            last_conv = conv
            if sigma is not None:
                max_sigma = sigma if max_sigma is None else max(max_sigma, sigma)
            if state is not None:
                max_state = state if max_state is None else max(max_state, state)

    note_parts: list[str] = []
    healthy = True
    if exit_code != 0:
        healthy = False
        note_parts.append(f'exit_code={exit_code}')
    if guard_events > int(rules.get('max_guard_events', 0)):
        healthy = False
        note_parts.append(f'guard_events={guard_events}')
    if hessian_failures > int(rules.get('max_hessian_failures', 0)):
        healthy = False
        note_parts.append(f'hessian_failures={hessian_failures}')
    if (max_sigma is None) or (max_sigma > float(rules.get('max_sigma_exp', 100.0))):
        healthy = False
        note_parts.append(f'max_sigma_exp={max_sigma}')
    if (max_state is None) or (max_state > float(rules.get('max_state_norm_sq', 1e8))):
        healthy = False
        note_parts.append(f'max_state_norm_sq={max_state}')
    if last_updates < int(rules.get('min_gamsig_update_iters', 1)):
        healthy = False
        note_parts.append(f'last_updates={last_updates}')
    if bool(rules.get('require_finite_conv_check', True)) and last_conv is None:
        healthy = False
        note_parts.append('last_conv_check=NA')
    if last_iter < 0:
        healthy = False
        note_parts.append('no_progress_lines')

    return ProbeResult(
        probe_id=probe_id,
        phase=phase,
        run_id=run_id,
        exit_code=exit_code,
        log_path=log_path,
        run_root=run_root,
        guard_events=guard_events,
        hessian_failures=hessian_failures,
        refreezes=refreezes,
        last_iter=last_iter,
        last_updates=last_updates,
        last_sigma_exp=last_sigma,
        max_sigma_exp=max_sigma,
        last_state_norm_sq=last_state,
        max_state_norm_sq=max_state,
        last_conv_check=last_conv,
        healthy=healthy,
        note='; '.join(note_parts) if note_parts else 'healthy',
    )


def _score(result: ProbeResult, complexity: int, order: int) -> tuple[Any, ...]:
    inf = float('inf')
    return (
        0 if result.healthy else 1,
        result.guard_events,
        result.hessian_failures,
        result.max_sigma_exp if result.max_sigma_exp is not None else inf,
        result.last_conv_check if result.last_conv_check is not None else inf,
        complexity,
        order,
    )


def _should_abort_early(log_path: Path, rules: dict[str, Any]) -> tuple[bool, str]:
    if not log_path.exists():
        return False, ''
    text = log_path.read_text(encoding='utf-8', errors='ignore')
    guard_events = len(re.findall(r'non-finite dq_transf', text))
    hessian_failures = len(re.findall(r'non-invertible Hessian', text))
    if guard_events > int(rules.get('max_guard_events', 0)):
        return True, f'guard_events={guard_events}'
    if hessian_failures > int(rules.get('max_hessian_failures', 0)):
        return True, f'hessian_failures={hessian_failures}'
    progresses = list(PROGRESS_RE.finditer(text))
    if progresses:
        max_sigma = None
        max_state = None
        for m in progresses:
            sigma = _parse_num(m.group('sigma'))
            state = _parse_num(m.group('state'))
            if sigma is not None:
                max_sigma = sigma if max_sigma is None else max(max_sigma, sigma)
            if state is not None:
                max_state = state if max_state is None else max(max_state, state)
        if max_sigma is not None and max_sigma > float(rules.get('max_sigma_exp', 100.0)):
            return True, f'max_sigma_exp={max_sigma}'
        if max_state is not None and max_state > float(rules.get('max_state_norm_sq', 1e8)):
            return True, f'max_state_norm_sq={max_state}'
    return False, ''


def _run_single(config_path: Path, launch_log_path: Path, q_log_path: Path, rules: dict[str, Any]) -> int:
    ensure_dir(launch_log_path.parent)
    with launch_log_path.open('w', encoding='utf-8') as log_handle:
        proc = subprocess.Popen(
            ['Rscript', '--vanilla', 'scripts/unified_run.R', '--config', str(config_path)],
            cwd=str(ROOT),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
            preexec_fn=os.setsid,
        )
        while True:
            ret = proc.poll()
            abort, reason = _should_abort_early(q_log_path, rules)
            if abort and ret is None:
                log_handle.write(f'\n[probe_runner] early abort due to screening failure: {reason}\n')
                log_handle.flush()
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait(timeout=10)
                ret = proc.returncode
            if ret is not None:
                return int(ret)
            time.sleep(5)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description='Run standalone exdqlm median warmup probes.')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--skip-existing', action='store_true')
    args = parser.parse_args()

    probe_cfg = load_yaml(args.config)
    base_config_path = Path(str(probe_cfg['base_generated_config'])).resolve()
    artifact_root = Path(str(probe_cfg['artifact_root'])).resolve()
    control_root = ensure_dir(artifact_root / 'control')
    generated_root = ensure_dir(control_root / 'generated_configs')
    launch_logs_root = ensure_dir(control_root / 'launch_logs')
    reports_root = ensure_dir(artifact_root / 'reports')

    base_cfg = load_yaml(base_config_path)
    base_snapshot = control_root / 'base_generated_config_snapshot.yaml'
    write_yaml(base_snapshot, base_cfg)

    quantile = float(probe_cfg['screening']['quantile'])
    screening_rules = probe_cfg['screening']['health_rules']
    screening_patch = {'fit': {'exdqlm_multivar': {'gamma_sigma': probe_cfg['screening']['gamma_sigma']}}}

    results: list[ProbeResult] = []
    scored: list[tuple[tuple[Any, ...], ProbeResult, dict[str, Any], int]] = []
    run_id_base = base_cfg['run']['run_id']

    for order, probe in enumerate(probe_cfg['probes']):
        probe_id = str(probe['id'])
        run_id = f"{run_id_base}__medianprobe__{probe_id}"
        cfg = _prepare_config(
            base_cfg,
            artifact_root=artifact_root,
            run_id=run_id,
            quantile=quantile,
            workers=int(probe_cfg['screening']['fit_parallel_workers']),
            mc_cores=int(probe_cfg['screening']['mc_cores']),
            stages=probe_cfg['screening']['stages'],
            gamma_sigma_patch=probe_cfg['screening']['gamma_sigma'],
            probe_patch=probe.get('config_patch', {}),
        )
        config_path = generated_root / f'{run_id}.yaml'
        write_yaml(config_path, cfg)
        launch_log = launch_logs_root / f'{run_id}.log'
        run_root = Path(cfg['run']['run_root']) / run_id
        q_log = run_root / 'fit' / 'exdqlm_multivar' / 'keep' / _q_label(quantile) / 'logs' / 'fit.log'
        if args.skip_existing and q_log.exists():
            exit_code = 0
        else:
            exit_code = _run_single(config_path, launch_log, q_log, screening_rules)
        result = _analyze_log(q_log, screening_rules, probe_id, 'screening', run_id, exit_code, run_root)
        results.append(result)
        scored.append((_score(result, _leaf_count(probe.get('config_patch', {})), order), result, probe, order))

    scored.sort(key=lambda item: item[0])
    winner_result = scored[0][1]
    winner_probe = scored[0][2]
    healthy_scored = [item for item in scored if item[1].healthy]
    has_healthy_winner = len(healthy_scored) > 0
    selected_result = healthy_scored[0][1] if has_healthy_winner else winner_result
    selected_probe = healthy_scored[0][2] if has_healthy_winner else winner_probe

    confirmation_result: ProbeResult | None = None
    if bool(probe_cfg.get('confirmation', {}).get('enabled', False)) and selected_result.healthy:
        confirm = probe_cfg['confirmation']
        run_id = f"{run_id_base}__medianconfirm__{selected_result.probe_id}"
        confirm_cfg = _prepare_config(
            base_cfg,
            artifact_root=artifact_root,
            run_id=run_id,
            quantile=quantile,
            workers=int(confirm['fit_parallel_workers']),
            mc_cores=int(confirm['mc_cores']),
            stages=confirm['stages'],
            gamma_sigma_patch=confirm['gamma_sigma'],
            probe_patch=selected_probe.get('config_patch', {}),
        )
        config_path = generated_root / f'{run_id}.yaml'
        write_yaml(config_path, confirm_cfg)
        launch_log = launch_logs_root / f'{run_id}.log'
        run_root = Path(confirm_cfg['run']['run_root']) / run_id
        q_log = run_root / 'fit' / 'exdqlm_multivar' / 'keep' / _q_label(quantile) / 'logs' / 'fit.log'
        exit_code = _run_single(config_path, launch_log, q_log, confirm['health_rules'])
        confirmation_result = _analyze_log(q_log, confirm['health_rules'], selected_result.probe_id, 'confirmation', run_id, exit_code, run_root)
        results.append(confirmation_result)

    rows = [res.row() for res in results]
    _write_csv(reports_root / 'probe_results.csv', rows)
    (reports_root / 'probe_results.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')

    summary = {
        'probe_id': probe_cfg['probe']['id'],
        'base_generated_config': str(base_config_path),
        'base_snapshot': str(base_snapshot),
        'has_healthy_winner': has_healthy_winner,
        'selected_probe_id': selected_result.probe_id,
        'selected_phase': selected_result.phase,
        'selected_healthy': selected_result.healthy,
        'selected_note': selected_result.note,
        'selected_patch': selected_probe.get('config_patch', {}),
        'best_probe_id': winner_result.probe_id,
        'best_phase': winner_result.phase,
        'best_healthy': winner_result.healthy,
        'best_note': winner_result.note,
        'best_patch': winner_probe.get('config_patch', {}),
        'confirmation': confirmation_result.row() if confirmation_result else None,
    }
    (reports_root / 'winner_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    md_lines = [
        f"# {probe_cfg['probe']['id']}",
        '',
        probe_cfg['probe'].get('description', ''),
        '',
        f"- Base generated config: `{base_config_path}`",
        f"- Base config snapshot: `{base_snapshot}`",
        f"- Screening quantile: `{quantile}`",
        '',
        '## Results',
        '',
        '| Probe | Phase | Healthy | Guards | Hessian | Last updates | Max sigma | Max state | Last conv | Note |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    for res in results:
        md_lines.append(
            f"| `{res.probe_id}` | `{res.phase}` | `{str(res.healthy)}` | `{res.guard_events}` | `{res.hessian_failures}` | `{res.last_updates}` | `{res.max_sigma_exp}` | `{res.max_state_norm_sq}` | `{res.last_conv_check}` | {res.note} |"
        )
    md_lines += [
        '',
        '## Selection',
        '',
        f"- Healthy winner available: `{has_healthy_winner}`",
        f"- Selected probe: `{selected_result.probe_id}`",
        f"- Selected probe healthy in screening: `{selected_result.healthy}`",
        f"- Selected patch: `{json.dumps(selected_probe.get('config_patch', {}), sort_keys=True)}`",
        f"- Best-scoring probe overall: `{winner_result.probe_id}`",
        f"- Best-scoring probe healthy: `{winner_result.healthy}`",
    ]
    if confirmation_result is not None:
        md_lines.append(f"- Confirmation healthy: `{confirmation_result.healthy}`")
        md_lines.append(f"- Confirmation note: `{confirmation_result.note}`")
    (reports_root / 'MEDIAN_WARMUP_PROBE_REPORT.md').write_text('\n'.join(md_lines) + '\n', encoding='utf-8')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
