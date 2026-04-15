#!/usr/bin/env python3
"""Summarize multi-split GLOFAS operational download health for recovery campaigns."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

if __package__ is None or __package__ == "":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recovery_priority_lib import (
    GLOFAS_OPERATIONAL_DONE_STATUSES,
    latest_csv_rows_by_key,
    operational_latest_problem_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check health of a parallel GLOFAS operational download campaign.")
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    return parser.parse_args()


def load_split_summary(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def count_nonempty_gribs(download_root: Path, issue_dates_file: Path) -> int:
    issue_dates = [line.strip() for line in issue_dates_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    count = 0
    for issue_date in issue_dates:
        issue_dir = download_root / "grib" / f"issue_date={issue_date}"
        files = [path for path in issue_dir.glob("*.grib") if path.exists() and path.stat().st_size > 0]
        if files:
            count += 1
    return count


def main() -> int:
    args = parse_args()
    campaign_root = args.campaign_root.resolve()
    plan_root = campaign_root / "plans"
    split_summary_path = plan_root / "split_summary.csv"
    split_dir = plan_root / "splits"
    manifest_dir = campaign_root / "manifests"
    download_root = campaign_root / "outputs" / "download_root"

    if not split_summary_path.exists():
        raise SystemExit(f"Missing split summary: {split_summary_path}")

    split_rows = load_split_summary(split_summary_path)
    per_split: List[Dict[str, object]] = []
    overall_counter: Counter[str] = Counter()
    expected_total = 0
    actual_grib_total = 0

    for row in split_rows:
        split_id = row["split_id"]
        expected_count = int(row["issue_count"])
        expected_total += expected_count
        issue_dates_file = split_dir / f"{split_id}_issue_dates.txt"
        manifest_path = manifest_dir / f"{split_id}_download_manifest.csv"
        raw_statuses: Counter[str] = Counter()
        latest_statuses: Counter[str] = Counter()
        manifest_rows = 0
        latest_timestamp = None
        if manifest_path.exists():
            with manifest_path.open(newline="", encoding="utf-8") as handle:
                for manifest_row in csv.DictReader(handle):
                    manifest_rows += 1
                    raw_statuses[manifest_row.get("status", "")] += 1
                    latest_timestamp = manifest_row.get("timestamp_utc") or latest_timestamp
        latest_rows = latest_csv_rows_by_key(manifest_path, "issue_date")
        for manifest_row in latest_rows.values():
            latest_statuses[manifest_row.get("status", "")] += 1
        actual_gribs = count_nonempty_gribs(download_root, issue_dates_file)
        actual_grib_total += actual_gribs
        overall_counter.update(latest_statuses)
        done_like_manifest_count = sum(latest_statuses.get(status, 0) for status in GLOFAS_OPERATIONAL_DONE_STATUSES)
        per_split.append(
            {
                "split_id": split_id,
                "expected_issue_dates": expected_count,
                "manifest_rows": manifest_rows,
                "raw_status_counts": dict(raw_statuses),
                "latest_status_counts": dict(latest_statuses),
                "done_like_manifest_count": done_like_manifest_count,
                "grib_issue_dir_count": actual_gribs,
                "percent_complete": round((actual_gribs / expected_count) * 100.0, 1) if expected_count else 0.0,
                "latest_timestamp_utc": latest_timestamp,
                "ok": actual_gribs <= expected_count,
            }
        )

    latest_problem_rows = operational_latest_problem_rows(campaign_root)
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "campaign_root": str(campaign_root),
        "expected_issue_dates_total": expected_total,
        "grib_issue_dir_count_total": actual_grib_total,
        "latest_status_counts_total": dict(overall_counter),
        "done_like_manifest_total": sum(overall_counter.get(status, 0) for status in GLOFAS_OPERATIONAL_DONE_STATUSES),
        "percent_complete_total": round((actual_grib_total / expected_total) * 100.0, 1) if expected_total else 0.0,
        "latest_problem_count": len(latest_problem_rows),
        "latest_problem_rows": latest_problem_rows,
        "splits": per_split,
        "ok": all(split["ok"] for split in per_split),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": summary["ok"], "out_json": str(args.out_json)}, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
