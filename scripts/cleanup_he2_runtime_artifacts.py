#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CleanupTarget:
    path: Path
    reason: str


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def disk_free_bytes(path: Path) -> int:
    usage = shutil.disk_usage(path)
    return int(usage.free)


def parse_spec(config_path: Path) -> dict[str, Any]:
    payload = load_yaml(config_path)
    cleanup = payload.get('cleanup', {}) if isinstance(payload.get('cleanup'), dict) else {}
    if not cleanup:
        raise KeyError('missing cleanup block in config')
    cleanup_id = str(cleanup['cleanup_id'])
    runtime_root = Path(cleanup['runtime_root']).resolve()
    report_root = (ROOT / cleanup.get('report_root', 'repro/reports/cleanup_runs')).resolve()
    quarantine_root = (ROOT / cleanup.get('quarantine_root', 'repro/quarantine/cleanup_runs')).resolve()
    min_size_bytes = int(float(cleanup.get('min_size_mb', 250)) * 1024 * 1024)
    suffixes = {str(s).lower() for s in (cleanup.get('prune_extensions') or ['.RData', '.rda', '.rds', '.RDS'])}
    evidence_patterns = [str(p) for p in (cleanup.get('evidence_patterns') or [])]
    protected_roots = {Path(p).resolve() for p in (cleanup.get('protected_roots') or [])}
    targets = [
        CleanupTarget(path=Path(item['path']).resolve(), reason=str(item.get('reason', 'unspecified')))
        for item in (cleanup.get('candidate_roots') or [])
        if isinstance(item, dict) and item.get('path')
    ]
    return {
        'cleanup_id': cleanup_id,
        'runtime_root': runtime_root,
        'report_root': report_root,
        'quarantine_root': quarantine_root,
        'min_size_bytes': min_size_bytes,
        'suffixes': suffixes,
        'evidence_patterns': evidence_patterns,
        'protected_roots': protected_roots,
        'targets': targets,
    }


def collect_prune_files(target: CleanupTarget, *, suffixes: set[str], min_size_bytes: int, protected_roots: set[Path]) -> list[Path]:
    if target.path in protected_roots:
        return []
    if not target.path.exists():
        return []
    files: list[Path] = []
    for path in target.path.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix.lower() not in suffixes:
            continue
        if path.stat().st_size < min_size_bytes:
            continue
        files.append(path)
    return sorted(files)


def collect_evidence_files(target: CleanupTarget, *, patterns: list[str]) -> list[Path]:
    if not target.path.exists():
        return []
    found: set[Path] = set()
    for pattern in patterns:
        for path in target.path.glob(pattern):
            if path.is_file():
                found.add(path.resolve())
    return sorted(found)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def copy_evidence(target: CleanupTarget, evidence_files: list[Path], *, quarantine_root: Path) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    target_root = ensure_dir(quarantine_root / target.path.name)
    for src in evidence_files:
        rel = src.relative_to(target.path)
        dst = target_root / rel
        ensure_dir(dst.parent)
        shutil.copy2(src, dst)
        copied.append({
            'target': target.path.name,
            'source': str(src),
            'destination': str(dst),
            'bytes': src.stat().st_size,
        })
    return copied


def build_plan(spec: dict[str, Any]) -> dict[str, Any]:
    targets_report: list[dict[str, Any]] = []
    total_files = 0
    total_bytes = 0
    for target in spec['targets']:
        prune_files = collect_prune_files(
            target,
            suffixes=spec['suffixes'],
            min_size_bytes=spec['min_size_bytes'],
            protected_roots=spec['protected_roots'],
        )
        evidence_files = collect_evidence_files(target, patterns=spec['evidence_patterns'])
        prune_bytes = sum(path.stat().st_size for path in prune_files if path.exists())
        total_files += len(prune_files)
        total_bytes += prune_bytes
        targets_report.append({
            'target_root': str(target.path),
            'target_name': target.path.name,
            'reason': target.reason,
            'exists': target.path.exists(),
            'evidence_files': [str(path) for path in evidence_files],
            'prune_files': [str(path) for path in prune_files],
            'prune_file_count': len(prune_files),
            'prune_bytes': prune_bytes,
        })
    return {
        'cleanup_id': spec['cleanup_id'],
        'runtime_root': str(spec['runtime_root']),
        'min_size_bytes': spec['min_size_bytes'],
        'suffixes': sorted(spec['suffixes']),
        'targets': targets_report,
        'totals': {
            'prune_file_count': total_files,
            'prune_bytes': total_bytes,
        },
    }


def write_reports(plan: dict[str, Any], *, report_dir: Path, mode: str, free_before: int, free_after: int | None = None, copied: list[dict[str, Any]] | None = None, deleted: list[dict[str, Any]] | None = None) -> None:
    ensure_dir(report_dir)
    write_json(report_dir / 'cleanup_plan.json', plan)
    before_after = [
        f'mode\t{mode}',
        f'free_before_bytes\t{free_before}',
        f'planned_prune_file_count\t{plan["totals"]["prune_file_count"]}',
        f'planned_prune_bytes\t{plan["totals"]["prune_bytes"]}',
    ]
    if free_after is not None:
        before_after.append(f'free_after_bytes\t{free_after}')
        before_after.append(f'freed_bytes\t{free_after - free_before}')
    (report_dir / 'before_after.tsv').write_text('\n'.join(before_after) + '\n', encoding='utf-8')

    inventory_lines = ['target_name\treason\tprune_file_count\tprune_bytes']
    for row in plan['targets']:
        inventory_lines.append(f"{row['target_name']}\t{row['reason']}\t{row['prune_file_count']}\t{row['prune_bytes']}")
    (report_dir / 'target_inventory.tsv').write_text('\n'.join(inventory_lines) + '\n', encoding='utf-8')

    if copied is not None:
        copied_lines = ['target\tsource\tdestination\tbytes']
        for row in copied:
            copied_lines.append(f"{row['target']}\t{row['source']}\t{row['destination']}\t{row['bytes']}")
        (report_dir / 'copied_evidence.tsv').write_text('\n'.join(copied_lines) + '\n', encoding='utf-8')

    if deleted is not None:
        deleted_lines = ['target\tpath\tbytes']
        for row in deleted:
            deleted_lines.append(f"{row['target']}\t{row['path']}\t{row['bytes']}")
        (report_dir / 'deleted_paths.tsv').write_text('\n'.join(deleted_lines) + '\n', encoding='utf-8')

    summary_lines = [
        f'# HE2 Runtime Artifact Cleanup: {plan["cleanup_id"]}',
        '',
        f'- mode: `{mode}`',
        f'- planned prune files: `{plan["totals"]["prune_file_count"]}`',
        f'- planned prune bytes: `{plan["totals"]["prune_bytes"]}`',
        f'- free before bytes: `{free_before}`',
    ]
    if free_after is not None:
        summary_lines.extend([
            f'- free after bytes: `{free_after}`',
            f'- freed bytes: `{free_after - free_before}`',
        ])
    summary_lines.extend(['', '## Targets', '', '| Target | Reason | Files | Bytes |', '|---|---|---:|---:|'])
    for row in plan['targets']:
        summary_lines.append(f"| `{row['target_name']}` | `{row['reason']}` | `{row['prune_file_count']}` | `{row['prune_bytes']}` |")
    (report_dir / 'summary.md').write_text('\n'.join(summary_lines) + '\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description='Prune large superseded HE2 runtime R artifacts after preserving compact evidence.')
    parser.add_argument('--config', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    config_path = Path(args.config).resolve() if Path(args.config).is_absolute() else (ROOT / args.config).resolve()
    spec = parse_spec(config_path)
    plan = build_plan(spec)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    mode = 'apply' if args.apply else 'dryrun'
    report_dir = ensure_dir(spec['report_root'] / f'{stamp}_{spec["cleanup_id"]}_{mode}')
    quarantine_root = spec['quarantine_root'] / stamp
    free_before = disk_free_bytes(spec['runtime_root'])

    copied: list[dict[str, Any]] | None = None
    deleted: list[dict[str, Any]] | None = None
    free_after: int | None = None

    if args.apply:
        copied = []
        deleted = []
        quarantine_manifest_root = ensure_dir(quarantine_root)
        for target_spec in plan['targets']:
            target = CleanupTarget(path=Path(target_spec['target_root']), reason=target_spec['reason'])
            evidence_paths = [Path(path) for path in target_spec['evidence_files']]
            copied.extend(copy_evidence(target, evidence_paths, quarantine_root=quarantine_manifest_root))
            for raw_path in target_spec['prune_files']:
                path = Path(raw_path)
                if not path.exists():
                    continue
                size = path.stat().st_size
                path.unlink()
                deleted.append({'target': target.path.name, 'path': str(path), 'bytes': size})
        free_after = disk_free_bytes(spec['runtime_root'])
        write_json(quarantine_manifest_root / 'cleanup_summary.json', {
            'cleanup_id': spec['cleanup_id'],
            'config': str(config_path),
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'copied_evidence_count': len(copied),
            'deleted_file_count': len(deleted),
            'deleted_bytes': sum(item['bytes'] for item in deleted),
        })
    write_reports(plan, report_dir=report_dir, mode=mode, free_before=free_before, free_after=free_after, copied=copied, deleted=deleted)

    print(f'cleanup_id={spec["cleanup_id"]}')
    print(f'mode={mode}')
    print(f'report_dir={report_dir}')
    if args.apply:
        print(f'quarantine_root={quarantine_root}')
        print(f'deleted_file_count={len(deleted or [])}')
        print(f'deleted_bytes={sum(item["bytes"] for item in (deleted or []))}')
    else:
        print(f'planned_file_count={plan["totals"]["prune_file_count"]}')
        print(f'planned_bytes={plan["totals"]["prune_bytes"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
