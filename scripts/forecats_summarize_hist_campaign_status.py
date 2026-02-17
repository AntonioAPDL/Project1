#!/usr/bin/env python3
"""Summarize historical campaign completion against planned shard inventory."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


STATUS_PRIORITY = {
    "downloaded": 4,
    "skipped_exists": 3,
    "error_empty": 2,
    "error_exception": 1,
    "planned": 0,
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Summarize campaign status versus planned shards")
    ap.add_argument("--plan-dir", type=Path, required=True, help="Directory containing shards_all.csv")
    ap.add_argument(
        "--run-glob",
        default="repro/glofas_probe_runs/hist_campaign_20260217T0*",
        help="Glob for run directories with download_manifest.csv",
    )
    ap.add_argument("--out-csv", type=Path, default=None)
    return ap.parse_args()


def shard_key(r: Dict[str, str]) -> Tuple[str, str, str, str]:
    return (r["product_id"], r.get("shard_id", ""), r.get("start", ""), r.get("end", ""))


def main() -> int:
    args = parse_args()
    plan_csv = args.plan_dir / "shards_all.csv"
    if not plan_csv.exists():
        raise SystemExit(f"Missing plan CSV: {plan_csv}")

    planned: Dict[Tuple[str, str, str, str], Dict[str, str]] = {}
    with plan_csv.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            planned[shard_key(r)] = r

    merged: Dict[Tuple[str, str, str, str], Dict[str, str]] = {k: dict(v) for k, v in planned.items()}
    for k in merged:
        merged[k]["status"] = "planned"
        merged[k]["status_source"] = "none"

    run_dirs = sorted(Path(".").glob(args.run_glob))
    manifest_count = 0
    for d in run_dirs:
        m = d / "download_manifest.csv"
        if not m.exists():
            continue
        manifest_count += 1
        with m.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                k = shard_key(r)
                if k not in merged:
                    # Keep unplanned rows too (diagnostic).
                    merged[k] = {
                        "product_id": r.get("product_id", ""),
                        "shard_id": r.get("shard_id", ""),
                        "start": r.get("start", ""),
                        "end": r.get("end", ""),
                        "status": r.get("status", "planned"),
                        "status_source": str(d),
                    }
                    continue
                prev = merged[k].get("status", "planned")
                cur = r.get("status", "planned")
                if STATUS_PRIORITY.get(cur, -1) >= STATUS_PRIORITY.get(prev, -1):
                    merged[k]["status"] = cur
                    merged[k]["status_source"] = str(d)

    total_planned = len(planned)
    final_status = Counter(v.get("status", "planned") for v in merged.values() if shard_key(v) in planned)

    by_product: Dict[str, Counter] = defaultdict(Counter)
    for k, v in merged.items():
        if k not in planned:
            continue
        by_product[v["product_id"]][v.get("status", "planned")] += 1

    print(f"plan_dir={args.plan_dir}")
    print(f"run_dirs={len(run_dirs)} manifest_runs={manifest_count}")
    print(f"planned_shards={total_planned}")
    print(f"status_counts={dict(final_status)}")

    done = final_status.get("downloaded", 0) + final_status.get("skipped_exists", 0)
    print(f"completion={done}/{total_planned} ({(100.0*done/total_planned):.2f}%)")

    for pid in sorted(by_product):
        c = by_product[pid]
        pdone = c.get("downloaded", 0) + c.get("skipped_exists", 0)
        ptotal = sum(c.values())
        print(f"{pid}: total={ptotal} done={pdone} status={dict(c)}")

    if args.out_csv is not None:
        args.out_csv.parent.mkdir(parents=True, exist_ok=True)
        fields = ["product_id", "shard_id", "start", "end", "status", "status_source"]
        with args.out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for _, v in sorted(merged.items()):
                w.writerow({k: v.get(k, "") for k in fields})
        print(f"[OK] wrote {args.out_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
