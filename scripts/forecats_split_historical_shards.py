#!/usr/bin/env python3
"""Split historical shard CSV into lane CSVs for parallel tmux execution."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Sequence


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Split shard CSV rows into N lane CSV files")
    ap.add_argument("--shards-csv", type=Path, required=True)
    ap.add_argument("--lanes", type=int, default=4)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--prefix", default="lane")
    return ap.parse_args(argv)


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    if args.lanes < 1:
        raise ValueError("--lanes must be >= 1")

    with args.shards_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError("shards CSV has no header")
        rows = [{k: str(v) for k, v in r.items()} for r in reader]

    buckets: List[List[Dict[str, str]]] = [[] for _ in range(args.lanes)]
    for i, row in enumerate(rows):
        buckets[i % args.lanes].append(row)

    for lane_idx, bucket in enumerate(buckets):
        out = args.out_dir / f"{args.prefix}_{lane_idx:02d}.csv"
        write_csv(out, bucket, fieldnames)
        print(f"[OK] {out} rows={len(bucket)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(tuple(__import__("sys").argv[1:])))
