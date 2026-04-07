#!/usr/bin/env python3
"""Build balanced GLOFAS operational issue-date split plans for parallel download sessions."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from glofas_operational_mediumrange_download_point import DEFAULT_INTERVALS, Interval, parse_ymd


@dataclass(frozen=True)
class SplitPlan:
    split_id: str
    issue_dates: List[date]

    @property
    def intervals(self) -> List[Interval]:
        if not self.issue_dates:
            return []
        out: List[Interval] = []
        start = self.issue_dates[0]
        end = start
        for current in self.issue_dates[1:]:
            if current == end + timedelta(days=1):
                end = current
                continue
            out.append(Interval(start, end))
            start = current
            end = current
        out.append(Interval(start, end))
        return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build balanced split plans for GLOFAS operational forecast downloads.")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--num-splits", type=int, default=6)
    parser.add_argument("--intervals-file", type=Path, default=None)
    parser.add_argument("--start-date", default="2019-11-05")
    parser.add_argument("--end-date", default="2023-01-31")
    parser.add_argument(
        "--smoke-days-per-split",
        type=int,
        default=0,
        help="If >0, truncate each split to its first N issue dates for smoke testing.",
    )
    return parser.parse_args()


def load_intervals(path: Path | None) -> List[Interval]:
    if path is None:
        return [Interval(parse_ymd(start), parse_ymd(end)) for start, end in DEFAULT_INTERVALS]

    text = path.read_text(encoding="utf-8").splitlines()
    cleaned = [line.strip() for line in text if line.strip() and not line.strip().startswith("#")]
    if not cleaned:
        return []
    if "," in cleaned[0]:
        rows = list(csv.DictReader(cleaned))
        return [Interval(parse_ymd(row["start"]), parse_ymd(row["end"])) for row in rows]
    return [Interval(parse_ymd(line.split()[0]), parse_ymd(line.split()[1])) for line in cleaned]


def clip_intervals(intervals: Sequence[Interval], start_date: date, end_date: date) -> List[Interval]:
    clipped: List[Interval] = []
    for interval in intervals:
        start = max(interval.start, start_date)
        end = min(interval.end, end_date)
        if start <= end:
            clipped.append(Interval(start, end))
    return clipped


def enumerate_issue_dates(intervals: Sequence[Interval]) -> List[date]:
    out: List[date] = []
    for interval in intervals:
        out.extend(list(interval.iter_days()))
    return out


def balanced_chunk_sizes(total: int, parts: int) -> List[int]:
    base = total // parts
    remainder = total % parts
    return [base + (1 if idx < remainder else 0) for idx in range(parts)]


def build_splits(issue_dates: Sequence[date], num_splits: int, smoke_days_per_split: int) -> List[SplitPlan]:
    sizes = balanced_chunk_sizes(len(issue_dates), num_splits)
    splits: List[SplitPlan] = []
    cursor = 0
    for idx, size in enumerate(sizes, start=1):
        chunk = list(issue_dates[cursor : cursor + size])
        cursor += size
        if smoke_days_per_split > 0:
            chunk = chunk[:smoke_days_per_split]
        splits.append(SplitPlan(split_id=f"split_{idx:02d}", issue_dates=chunk))
    return splits


def write_issue_dates(path: Path, issue_dates: Iterable[date]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(f"{value.isoformat()}\n" for value in issue_dates)
    path.write_text(text, encoding="utf-8")


def write_intervals_csv(path: Path, intervals: Sequence[Interval]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["start", "end"])
        writer.writeheader()
        for interval in intervals:
            writer.writerow({"start": interval.start.isoformat(), "end": interval.end.isoformat()})


def write_summary_csv(path: Path, splits: Sequence[SplitPlan]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "split_id",
                "issue_count",
                "first_issue_date",
                "last_issue_date",
                "interval_count",
                "intervals_compact",
            ],
        )
        writer.writeheader()
        for split in splits:
            intervals = split.intervals
            writer.writerow(
                {
                    "split_id": split.split_id,
                    "issue_count": len(split.issue_dates),
                    "first_issue_date": split.issue_dates[0].isoformat() if split.issue_dates else "",
                    "last_issue_date": split.issue_dates[-1].isoformat() if split.issue_dates else "",
                    "interval_count": len(intervals),
                    "intervals_compact": ";".join(f"{i.start.isoformat()}..{i.end.isoformat()}" for i in intervals),
                }
            )


def main() -> int:
    args = parse_args()
    if args.num_splits < 1:
        raise SystemExit("--num-splits must be >= 1")
    if args.smoke_days_per_split < 0:
        raise SystemExit("--smoke-days-per-split must be >= 0")

    start_date = parse_ymd(args.start_date)
    end_date = parse_ymd(args.end_date)
    if start_date > end_date:
        raise SystemExit("--start-date must be <= --end-date")

    intervals = clip_intervals(load_intervals(args.intervals_file), start_date, end_date)
    issue_dates = enumerate_issue_dates(intervals)
    if not issue_dates:
        raise SystemExit("No issue dates found after clipping the supplied intervals")
    if len(issue_dates) < args.num_splits:
        raise SystemExit("Issue-date count is smaller than the requested number of splits")

    splits = build_splits(issue_dates, args.num_splits, args.smoke_days_per_split)
    if any(not split.issue_dates for split in splits):
        raise SystemExit("At least one split is empty; reduce --num-splits or expand the interval window")

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    split_dir = out_dir / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)

    write_issue_dates(out_dir / "all_issue_dates.txt", issue_dates)
    write_summary_csv(out_dir / "split_summary.csv", splits)

    for split in splits:
        write_issue_dates(split_dir / f"{split.split_id}_issue_dates.txt", split.issue_dates)
        write_intervals_csv(split_dir / f"{split.split_id}_intervals.csv", split.intervals)

    metadata = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out_dir),
        "num_splits": args.num_splits,
        "smoke_days_per_split": args.smoke_days_per_split,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_issue_dates": len(issue_dates),
        "intervals": [{"start": i.start.isoformat(), "end": i.end.isoformat()} for i in intervals],
        "splits": [
            {
                "split_id": split.split_id,
                "issue_count": len(split.issue_dates),
                "first_issue_date": split.issue_dates[0].isoformat(),
                "last_issue_date": split.issue_dates[-1].isoformat(),
                "intervals": [{"start": i.start.isoformat(), "end": i.end.isoformat()} for i in split.intervals],
            }
            for split in splits
        ],
    }
    (out_dir / "plan_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
