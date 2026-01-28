#!/usr/bin/env python3
"""Compare current outputs to gold DISC figures by filename and SHA256.

Usage:
  python repro/compare_to_gold_DISC.py \
    --current-dir Environmetrics_reproduce \
    --report repro/compare_report_reproduce.txt \
    --current-sha repro/current_Environmetrics_reproduce.sha256 \
    --generate-diffs --max-diffs 20
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from typing import Dict, Tuple, List


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_hash_file(path: Path) -> Dict[str, Tuple[str, str]]:
    out: Dict[str, Tuple[str, str]] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        h = parts[0]
        rel = parts[1]
        name = Path(rel).name
        out[name] = (h, rel)
    return out


def png_dimensions(path: Path) -> Tuple[int, int] | None:
    try:
        with path.open('rb') as f:
            sig = f.read(8)
            if sig != b'\x89PNG\r\n\x1a\n':
                return None
            f.read(4)  # length
            chunk_type = f.read(4)
            if chunk_type != b'IHDR':
                return None
            data = f.read(8)
            w = int.from_bytes(data[0:4], 'big')
            h = int.from_bytes(data[4:8], 'big')
            return w, h
    except Exception:
        return None


def file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except Exception:
        return None


def compute_current_hashes(current_dir: Path, current_sha: Path) -> None:
    entries: List[Tuple[str, str]] = []
    if current_dir.exists():
        for p in sorted(current_dir.glob('*.png')):
            h = sha256_file(p)
            rel = f"{current_dir.name}/{p.name}"
            entries.append((h, rel))
    current_sha.parent.mkdir(parents=True, exist_ok=True)
    current_sha.write_text("\n".join([f"{h}  {rel}" for h, rel in entries]) + "\n", encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare gold DISC figures with current outputs.")
    parser.add_argument('--current-dir', default='Environmetrics', help='Current output directory')
    parser.add_argument('--gold-sha', default='repro/gold_DISC_figures.sha256', help='Gold hash file')
    parser.add_argument('--report', default='repro/compare_report.txt', help='Report output path')
    parser.add_argument('--current-sha', default='repro/current_outputs.sha256', help='Current hash output path')
    parser.add_argument('--diff-dir', default='repro/diff', help='Diff image output directory')
    parser.add_argument('--generate-diffs', action='store_true', help='Generate diff images for mismatches')
    parser.add_argument('--max-diffs', type=int, default=20, help='Max diff images to generate')
    args = parser.parse_args()

    root = Path('/data/muscat_data/jaguir26/project1_ucsc_phd')
    paper_repo = Path('/data/muscat_data/jaguir26/Environmetrics_paper_repo')

    current_dir = (root / args.current_dir).resolve() if not Path(args.current_dir).is_absolute() else Path(args.current_dir)
    gold_sha = (root / args.gold_sha).resolve() if not Path(args.gold_sha).is_absolute() else Path(args.gold_sha)
    report_path = (root / args.report).resolve() if not Path(args.report).is_absolute() else Path(args.report)
    current_sha = (root / args.current_sha).resolve() if not Path(args.current_sha).is_absolute() else Path(args.current_sha)
    diff_dir = (root / args.diff_dir).resolve() if not Path(args.diff_dir).is_absolute() else Path(args.diff_dir)

    compute_current_hashes(current_dir, current_sha)

    gold = parse_hash_file(gold_sha)
    current = parse_hash_file(current_sha)

    gold_names = set(gold.keys())
    current_names = set(current.keys())

    missing = sorted(gold_names - current_names)
    extra = sorted(current_names - gold_names)
    common = sorted(gold_names & current_names)

    mismatched = []
    for name in common:
        gh, _ = gold[name]
        ch, _ = current[name]
        if gh != ch:
            mismatched.append(name)

    matched = len(common) - len(mismatched)

    lines = []
    lines.append('# Gold vs Current Figure Comparison')
    lines.append('')
    lines.append(f'Gold hash file: {gold_sha}')
    lines.append(f'Current hash file: {current_sha}')
    lines.append(f'Current dir: {current_dir}')
    lines.append('')
    lines.append(f'Matched: {matched}')
    lines.append(f'Missing in current: {len(missing)}')
    lines.append(f'Extra in current: {len(extra)}')
    lines.append(f'Hash mismatches: {len(mismatched)}')
    lines.append('')

    if missing:
        lines.append('## Missing (present in gold, absent in current)')
        for name in missing:
            lines.append(f'- {name}')
        lines.append('')

    if extra:
        lines.append('## Extra (present in current, absent in gold)')
        for name in extra:
            lines.append(f'- {name}')
        lines.append('')

    if mismatched:
        lines.append('## Hash mismatches')
        for name in mismatched:
            gh, grel = gold[name]
            ch, crel = current[name]
            gold_path = paper_repo / grel
            current_path = root / crel
            gold_dim = png_dimensions(gold_path)
            cur_dim = png_dimensions(current_path)
            gold_size = file_size(gold_path)
            cur_size = file_size(current_path)
            lines.append(f'- {name}')
            lines.append(f'  gold hash:    {gh}')
            lines.append(f'  current hash: {ch}')
            lines.append(f'  gold dim:     {gold_dim}  size: {gold_size}')
            lines.append(f'  current dim:  {cur_dim}  size: {cur_size}')
        lines.append('')

    if args.generate_diffs and mismatched:
        try:
            from PIL import Image, ImageChops
            diff_dir.mkdir(parents=True, exist_ok=True)
            for name in mismatched[: args.max_diffs]:
                gold_path = paper_repo / gold[name][1]
                current_path = root / current[name][1]
                if gold_path.exists() and current_path.exists():
                    try:
                        im1 = Image.open(gold_path).convert('RGB')
                        im2 = Image.open(current_path).convert('RGB')
                        if im1.size == im2.size:
                            diff = ImageChops.difference(im1, im2)
                            diff.save(diff_dir / f'{name}_diff.png')
                    except Exception:
                        pass
        except Exception:
            lines.append('Pillow not available; diff images not generated.')
    elif args.generate_diffs:
        lines.append('Diffs requested but no mismatches found.')

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
