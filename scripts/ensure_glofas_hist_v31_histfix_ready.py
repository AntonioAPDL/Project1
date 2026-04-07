#!/usr/bin/env python3
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
from typing import Iterable


ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
PRODUCT_ID = "hist_v31_lisflood_cons"
SITE_LAT = 37.0443931
SITE_LON = -122.072464
DEFAULT_RECOVERY_FAMILY_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "data_recovery/site=11160500/"
    "recovery_run=site11160500_recovery_20260406T185022Z/"
    "family=glofas_historical/full_runs/source_native_tranche1_20260406T194500Z"
)
DEFAULT_FOCUS_START = "1987-05-29"
DEFAULT_FOCUS_END = "2022-05-11"
DEFAULT_WORKERS = 4
DEFAULT_PASSES = 4


@dataclass(frozen=True)
class MonthShard:
    start: date
    end: date

    @property
    def shard_id(self) -> str:
        return f"{self.start.year:04d}-{self.start.month:02d}"


def parse_date(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def month_end(d: date) -> date:
    first_next = date(d.year + (d.month == 12), 1 if d.month == 12 else d.month + 1, 1)
    return first_next - timedelta(days=1)


def iter_month_shards(start: date, end: date) -> Iterable[MonthShard]:
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        shard_start = max(start, cursor)
        shard_end = min(end, month_end(cursor))
        yield MonthShard(start=shard_start, end=shard_end)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def zip_exists(out_root: Path, shard: MonthShard) -> bool:
    month_dir = out_root / PRODUCT_ID / f"year={shard.start.year:04d}" / f"month={shard.start.month:02d}"
    return any(month_dir.glob("*.zip"))


def plan_missing(out_root: Path, focus_start: date, focus_end: date) -> tuple[list[MonthShard], list[MonthShard]]:
    done: list[MonthShard] = []
    missing: list[MonthShard] = []
    for shard in iter_month_shards(focus_start, focus_end):
        (done if zip_exists(out_root, shard) else missing).append(shard)
    return done, missing


def write_shards_csv(path: Path, shards: list[MonthShard]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["product_id", "shard_id", "start", "end"])
        writer.writeheader()
        for shard in shards:
            writer.writerow(
                {
                    "product_id": PRODUCT_ID,
                    "shard_id": shard.shard_id,
                    "start": shard.start.isoformat(),
                    "end": shard.end.isoformat(),
                }
            )


def split_round_robin(shards: list[MonthShard], workers: int) -> list[list[MonthShard]]:
    groups = [[] for _ in range(workers)]
    for idx, shard in enumerate(shards):
        groups[idx % workers].append(shard)
    return [group for group in groups if group]


def run_split_workers(campaign_root: Path, split_groups: list[list[MonthShard]], retry_max: int, sleep_max: int) -> list[int]:
    cmd_root = campaign_root / "commands"
    log_root = campaign_root / "logs"
    split_root = campaign_root / "split_plans"
    cmd_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)
    split_root.mkdir(parents=True, exist_ok=True)

    out_root = campaign_root.parent / "outputs" / "historical_zips"
    plan_root = campaign_root.parent / "plans"
    procs: list[subprocess.Popen[bytes]] = []

    for idx, group in enumerate(split_groups, start=1):
        split_id = f"split_{idx:02d}"
        shards_csv = split_root / f"{split_id}.csv"
        script_path = cmd_root / f"{split_id}.sh"
        log_path = log_root / f"{split_id}.log"
        write_shards_csv(shards_csv, group)
        script_path.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    f"cd {ROOT}",
                    "python3 scripts/forecats_download_glofas_historical_consolidated.py \\",
                    f"  --out-root {out_root} \\",
                    f"  --plan-root {plan_root} \\",
                    f"  --product-id {PRODUCT_ID} \\",
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
            cwd=ROOT,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        log_handle.close()
        procs.append(proc)

    exit_codes: list[int] = []
    for proc in procs:
        exit_codes.append(proc.wait())
    return exit_codes


def extract_point_series(recovery_family_root: Path, focus_start: date, focus_end: date) -> tuple[Path, Path]:
    out_root = recovery_family_root / "outputs" / "historical_zips" / PRODUCT_ID
    out_csv = recovery_family_root / "outputs" / "point_series" / f"{PRODUCT_ID}_point.csv"
    out_meta = recovery_family_root / "logs" / f"{PRODUCT_ID}_point.meta.json"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3",
        "scripts/forecats_extract_glofas_historical_point.py",
        "--campaign-root",
        str(out_root),
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
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    return out_csv, out_meta


def extracted_point_ready(meta_path: Path, required_end: date) -> bool:
    if not meta_path.exists():
        return False
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    end_text = str(meta.get("end_date", "")).strip()
    if not end_text:
        return False
    return parse_date(end_text) >= required_end


def write_status(status_path: Path, payload: dict) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Ensure the GloFAS historical v3.1 archive is complete enough for the hist-fix rerun.")
    ap.add_argument("--recovery-family-root", default=str(DEFAULT_RECOVERY_FAMILY_ROOT))
    ap.add_argument("--focus-start", default=DEFAULT_FOCUS_START)
    ap.add_argument("--focus-end", default=DEFAULT_FOCUS_END)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--passes", type=int, default=DEFAULT_PASSES)
    ap.add_argument("--retry-max", type=int, default=2)
    ap.add_argument("--sleep-max", type=int, default=20)
    ap.add_argument("--poll-seconds", type=int, default=30)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    recovery_family_root = Path(args.recovery_family_root).expanduser().resolve()
    focus_start = parse_date(args.focus_start)
    focus_end = parse_date(args.focus_end)
    if focus_end < focus_start:
        raise SystemExit("focus-end must be >= focus-start")

    out_root = recovery_family_root / "outputs" / "historical_zips"
    meta_path = recovery_family_root / "logs" / f"{PRODUCT_ID}_point.meta.json"
    status_path = recovery_family_root / "status" / "hist_v31_histfix_ready.json"

    done, missing = plan_missing(out_root, focus_start, focus_end)
    if not missing and extracted_point_ready(meta_path, focus_end):
        write_status(
            status_path,
            {
                "status": "ready",
                "created_at_utc": utc_now(),
                "focus_start": focus_start.isoformat(),
                "focus_end": focus_end.isoformat(),
                "existing_done_shards": len(done),
                "missing_shards": 0,
                "point_meta": str(meta_path),
            },
        )
        print(f"[READY] {PRODUCT_ID} already covers {focus_start}..{focus_end}")
        return 0

    campaign_root = recovery_family_root / "status" / f"hist_v31_histfix_refill_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    campaign_root.mkdir(parents=True, exist_ok=True)

    last_remaining = math.inf
    for pass_idx in range(1, args.passes + 1):
        done, missing = plan_missing(out_root, focus_start, focus_end)
        write_status(
            status_path,
            {
                "status": "running",
                "created_at_utc": utc_now(),
                "focus_start": focus_start.isoformat(),
                "focus_end": focus_end.isoformat(),
                "pass_index": pass_idx,
                "done_shards": len(done),
                "missing_shards": len(missing),
                "campaign_root": str(campaign_root),
            },
        )
        print(f"[PASS {pass_idx}] done={len(done)} missing={len(missing)}")
        if not missing:
            break
        if len(missing) >= last_remaining and pass_idx > 1:
            print(f"[STOP] no improvement after pass {pass_idx - 1}; remaining shards={len(missing)}", file=sys.stderr)
            break
        last_remaining = len(missing)
        split_groups = split_round_robin(missing, max(1, args.workers))
        exit_codes = run_split_workers(campaign_root / f"pass_{pass_idx:02d}", split_groups, args.retry_max, args.sleep_max)
        print(f"[PASS {pass_idx}] worker exit codes={exit_codes}")
        time.sleep(max(0, args.poll_seconds))

    done, missing = plan_missing(out_root, focus_start, focus_end)
    if missing:
        write_status(
            status_path,
            {
                "status": "incomplete",
                "created_at_utc": utc_now(),
                "focus_start": focus_start.isoformat(),
                "focus_end": focus_end.isoformat(),
                "done_shards": len(done),
                "missing_shards": len(missing),
                "first_missing": [shard.shard_id for shard in missing[:20]],
                "campaign_root": str(campaign_root),
            },
        )
        print(f"[INCOMPLETE] remaining missing shards={len(missing)}", file=sys.stderr)
        return 1

    out_csv, out_meta = extract_point_series(recovery_family_root, focus_start, focus_end)
    if not extracted_point_ready(out_meta, focus_end):
        write_status(
            status_path,
            {
                "status": "extract_incomplete",
                "created_at_utc": utc_now(),
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
            "created_at_utc": utc_now(),
            "focus_start": focus_start.isoformat(),
            "focus_end": focus_end.isoformat(),
            "done_shards": len(done),
            "missing_shards": 0,
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
