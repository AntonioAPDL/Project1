#!/usr/bin/env python3
"""Refill and extract a GLOFAS historical product until the requested window is complete."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recovery_priority_lib import (
    GLOFAS_PROJECT_FOCUS_END,
    GLOFAS_PROJECT_FOCUS_START,
    PROJECT_ROOT,
    SITE_LAT,
    SITE_LON,
    count_nonempty_month_shards,
    expected_month_shards,
)


PRODUCT_SPECS = {
    "hist_v21_htessel_cons": {
        "focus_start": date(1987, 5, 29),
        "focus_end": date(2022, 7, 31),
        "default_workers": 6,
    },
    "hist_v31_lisflood_cons": {
        "focus_start": GLOFAS_PROJECT_FOCUS_START,
        "focus_end": GLOFAS_PROJECT_FOCUS_END,
        "default_workers": 8,
    },
    "hist_v40_lisflood_cons": {
        "focus_start": GLOFAS_PROJECT_FOCUS_START,
        "focus_end": GLOFAS_PROJECT_FOCUS_END,
        "default_workers": 4,
    },
}


@dataclass(frozen=True)
class MonthShard:
    start: date
    end: date

    @property
    def shard_id(self) -> str:
        return f"{self.start.year:04d}-{self.start.month:02d}"


def utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def month_end(value: date) -> date:
    first_next = date(value.year + (value.month == 12), 1 if value.month == 12 else value.month + 1, 1)
    return first_next - timedelta(days=1)


def iter_month_shards(start: date, end: date) -> Iterable[MonthShard]:
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        yield MonthShard(start=max(start, cursor), end=min(end, month_end(cursor)))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def zip_exists_nonempty(out_root: Path, product_id: str, shard: MonthShard) -> bool:
    month_dir = out_root / product_id / f"year={shard.start.year:04d}" / f"month={shard.start.month:02d}"
    return any(path.stat().st_size > 0 for path in month_dir.glob("*.zip") if path.exists() and path.is_file())


def plan_missing(out_root: Path, product_id: str, focus_start: date, focus_end: date) -> tuple[list[MonthShard], list[MonthShard]]:
    done: list[MonthShard] = []
    missing: list[MonthShard] = []
    for shard in iter_month_shards(focus_start, focus_end):
        (done if zip_exists_nonempty(out_root, product_id, shard) else missing).append(shard)
    return done, missing


def split_round_robin(shards: list[MonthShard], workers: int) -> list[list[MonthShard]]:
    groups: list[list[MonthShard]] = [[] for _ in range(max(1, workers))]
    for idx, shard in enumerate(shards):
        groups[idx % len(groups)].append(shard)
    return [group for group in groups if group]


def write_shards_csv(path: Path, product_id: str, shards: List[MonthShard]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["product_id", "shard_id", "start", "end"])
        writer.writeheader()
        for shard in shards:
            writer.writerow(
                {
                    "product_id": product_id,
                    "shard_id": shard.shard_id,
                    "start": shard.start.isoformat(),
                    "end": shard.end.isoformat(),
                }
            )


def write_status(status_path: Path, payload: dict) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_point_series(recovery_family_root: Path, product_id: str, focus_start: date, focus_end: date) -> tuple[Path, Path]:
    campaign_root = recovery_family_root / "outputs" / "historical_zips" / product_id
    out_csv = recovery_family_root / "outputs" / "point_series" / f"{product_id}_point.csv"
    out_meta = recovery_family_root / "logs" / f"{product_id}_point.meta.json"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "forecats_extract_glofas_historical_point.py"),
            "--campaign-root",
            str(campaign_root),
            "--out-csv",
            str(out_csv),
            "--out-meta",
            str(out_meta),
            "--lat",
            str(SITE_LAT),
            "--lon",
            str(SITE_LON),
            "--cell-policy",
            "nearest_valid",
            "--start-date",
            focus_start.isoformat(),
            "--end-date",
            focus_end.isoformat(),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    return out_csv, out_meta


def extracted_point_ready(meta_path: Path, required_end: date) -> bool:
    if not meta_path.exists():
        return False
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    end_text = str(meta.get("end_date", "")).strip()
    return bool(end_text) and parse_date(end_text) >= required_end


def run_split_workers(
    recovery_family_root: Path,
    product_id: str,
    campaign_root: Path,
    split_groups: list[list[MonthShard]],
    retry_max: int,
    sleep_max: int,
) -> list[int]:
    cmd_root = campaign_root / "commands"
    log_root = campaign_root / "logs"
    split_root = campaign_root / "split_plans"
    out_root = recovery_family_root / "outputs" / "historical_zips"
    plan_root = recovery_family_root / "plans"

    cmd_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)
    split_root.mkdir(parents=True, exist_ok=True)

    procs: list[subprocess.Popen[bytes]] = []
    for idx, group in enumerate(split_groups, start=1):
        split_id = f"split_{idx:02d}"
        shards_csv = split_root / f"{split_id}.csv"
        script_path = cmd_root / f"{split_id}.sh"
        log_path = log_root / f"{split_id}.log"
        write_shards_csv(shards_csv, product_id, group)
        script_path.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    f"cd {PROJECT_ROOT}",
                    "python3 scripts/forecats_download_glofas_historical_consolidated.py \\",
                    f"  --out-root {out_root} \\",
                    f"  --plan-root {plan_root} \\",
                    f"  --product-id {product_id} \\",
                    f"  --shards-csv {shards_csv} \\",
                    f"  --retry-max {retry_max} \\",
                    f"  --sleep-max {sleep_max} \\",
                    "  --run",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        script_path.chmod(0o755)
        log_handle = log_path.open("ab")
        proc = subprocess.Popen(
            ["bash", str(script_path)],
            cwd=PROJECT_ROOT,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        log_handle.close()
        procs.append(proc)

    return [proc.wait() for proc in procs]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ensure a GLOFAS historical product is complete for a target focus window.")
    parser.add_argument("--recovery-family-root", required=True, type=Path)
    parser.add_argument("--product-id", required=True, choices=sorted(PRODUCT_SPECS))
    parser.add_argument("--focus-start", default=None)
    parser.add_argument("--focus-end", default=None)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--passes", type=int, default=6)
    parser.add_argument("--retry-max", type=int, default=2)
    parser.add_argument("--sleep-max", type=int, default=20)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    recovery_family_root = args.recovery_family_root.expanduser().resolve()
    spec = PRODUCT_SPECS[args.product_id]
    focus_start = parse_date(args.focus_start) if args.focus_start else spec["focus_start"]
    focus_end = parse_date(args.focus_end) if args.focus_end else spec["focus_end"]
    workers = args.workers or int(spec["default_workers"])

    if focus_end < focus_start:
        raise SystemExit("focus-end must be >= focus-start")

    out_root = recovery_family_root / "outputs" / "historical_zips"
    meta_path = recovery_family_root / "logs" / f"{args.product_id}_point.meta.json"
    status_path = recovery_family_root / "status" / f"{args.product_id}_ready.json"

    done, missing = plan_missing(out_root, args.product_id, focus_start, focus_end)
    payload = {
        "status": "planned" if args.dry_run else "running",
        "created_at_utc": utc_now_text(),
        "product_id": args.product_id,
        "focus_start": focus_start.isoformat(),
        "focus_end": focus_end.isoformat(),
        "done_shards": len(done),
        "missing_shards": len(missing),
        "expected_shards": expected_month_shards(focus_start, focus_end),
        "percent_complete": round((len(done) / expected_month_shards(focus_start, focus_end)) * 100.0, 1),
    }

    if not missing and extracted_point_ready(meta_path, focus_end):
        payload["status"] = "ready"
        payload["point_meta"] = str(meta_path)
        write_status(status_path, payload)
        print(f"[READY] {args.product_id} already covers {focus_start.isoformat()}..{focus_end.isoformat()}")
        return 0

    campaign_root = recovery_family_root / "status" / f"{args.product_id}_refill_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    payload["campaign_root"] = str(campaign_root)
    write_status(status_path, payload)

    if args.dry_run:
        split_groups = split_round_robin(missing, min(max(1, workers), max(1, len(missing))))
        for idx, group in enumerate(split_groups, start=1):
            write_shards_csv(campaign_root / "split_plans" / f"split_{idx:02d}.csv", args.product_id, group)
        print(f"[DRY-RUN] campaign_root={campaign_root}")
        print(f"[DRY-RUN] done={len(done)} missing={len(missing)} workers={workers}")
        return 0

    last_remaining = math.inf
    for pass_idx in range(1, args.passes + 1):
        done, missing = plan_missing(out_root, args.product_id, focus_start, focus_end)
        payload = {
            "status": "running",
            "created_at_utc": utc_now_text(),
            "product_id": args.product_id,
            "focus_start": focus_start.isoformat(),
            "focus_end": focus_end.isoformat(),
            "pass_index": pass_idx,
            "done_shards": len(done),
            "missing_shards": len(missing),
            "expected_shards": expected_month_shards(focus_start, focus_end),
            "percent_complete": round((len(done) / expected_month_shards(focus_start, focus_end)) * 100.0, 1),
            "campaign_root": str(campaign_root),
        }
        write_status(status_path, payload)
        print(f"[PASS {pass_idx}] product={args.product_id} done={len(done)} missing={len(missing)}")
        if not missing:
            break
        if len(missing) >= last_remaining and pass_idx > 1:
            print(f"[STOP] no improvement after pass {pass_idx - 1}; remaining shards={len(missing)}", file=sys.stderr)
            break
        last_remaining = len(missing)
        split_groups = split_round_robin(missing, min(max(1, workers), len(missing)))
        exit_codes = run_split_workers(
            recovery_family_root,
            args.product_id,
            campaign_root / f"pass_{pass_idx:02d}",
            split_groups,
            args.retry_max,
            args.sleep_max,
        )
        print(f"[PASS {pass_idx}] worker exit codes={exit_codes}")
        time.sleep(max(0, args.poll_seconds))

    done, missing = plan_missing(out_root, args.product_id, focus_start, focus_end)
    if missing:
        write_status(
            status_path,
            {
                "status": "incomplete",
                "created_at_utc": utc_now_text(),
                "product_id": args.product_id,
                "focus_start": focus_start.isoformat(),
                "focus_end": focus_end.isoformat(),
                "done_shards": len(done),
                "missing_shards": len(missing),
                "expected_shards": expected_month_shards(focus_start, focus_end),
                "first_missing": [shard.shard_id for shard in missing[:20]],
                "campaign_root": str(campaign_root),
            },
        )
        print(f"[INCOMPLETE] product={args.product_id} remaining missing shards={len(missing)}", file=sys.stderr)
        return 1

    out_csv, out_meta = extract_point_series(recovery_family_root, args.product_id, focus_start, focus_end)
    if not extracted_point_ready(out_meta, focus_end):
        write_status(
            status_path,
            {
                "status": "extract_incomplete",
                "created_at_utc": utc_now_text(),
                "product_id": args.product_id,
                "focus_start": focus_start.isoformat(),
                "focus_end": focus_end.isoformat(),
                "point_csv": str(out_csv),
                "point_meta": str(out_meta),
                "campaign_root": str(campaign_root),
            },
        )
        print(f"[ERROR] extracted point series does not reach {focus_end.isoformat()}", file=sys.stderr)
        return 1

    write_status(
        status_path,
        {
            "status": "ready",
            "created_at_utc": utc_now_text(),
            "product_id": args.product_id,
            "focus_start": focus_start.isoformat(),
            "focus_end": focus_end.isoformat(),
            "done_shards": len(done),
            "missing_shards": 0,
            "expected_shards": expected_month_shards(focus_start, focus_end),
            "point_csv": str(out_csv),
            "point_meta": str(out_meta),
            "campaign_root": str(campaign_root),
        },
    )
    print(f"[READY] point_csv={out_csv}")
    print(f"[READY] point_meta={out_meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
