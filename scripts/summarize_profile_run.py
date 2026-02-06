#!/usr/bin/env python3
"""
Summarize a profiling run produced by scripts/run_environmetrics_figures.R.

Inputs (generated when PROFILE=TRUE):
  repro/logs/profile/<RUN_ID>/timings.csv
  repro/logs/profile/<RUN_ID>/io_timings.csv

Optional (for wall time):
  repro/logs/script_runs/<RUN_ID>/run_log.txt

This tool is intentionally dependency-free (stdlib only).
It does NOT validate scientific equivalence; it only summarizes timings.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class Agg:
    count: int = 0
    total: float = 0.0
    min: float = float("inf")
    max: float = float("-inf")

    def add(self, value: float) -> None:
        self.count += 1
        self.total += value
        if value < self.min:
            self.min = value
        if value > self.max:
            self.max = value

    def mean(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total / self.count


def _parse_r_time(value: str) -> Optional[datetime]:
    value = value.strip()
    if not value:
        return None
    # R prints Sys.time() like "YYYY-MM-DD HH:MM:SS" (sometimes with fractional seconds).
    core = value[:19]
    try:
        return datetime.strptime(core, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _read_csv_rows(path: Path) -> Iterable[List[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            yield row


def _format_sec(sec: float) -> str:
    if sec < 60:
        return f"{sec:.2f}s"
    minutes = sec / 60.0
    if minutes < 60:
        return f"{minutes:.2f}m"
    hours = minutes / 60.0
    return f"{hours:.2f}h"


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    out: List[str] = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def _section_group(section: str) -> str:
    if section.endswith(".R"):
        return "module"
    # For internal timers like "figures.*" or "univariate.*"
    if "." in section:
        return section.split(".", 1)[0]
    return "other"


def _parse_wall_time(run_log_path: Path) -> Tuple[Optional[datetime], Optional[datetime]]:
    if not run_log_path.exists():
        return (None, None)
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    with run_log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("START:"):
                start = _parse_r_time(line.replace("START:", "", 1))
            elif line.startswith("END:"):
                end = _parse_r_time(line.replace("END:", "", 1))
    return (start, end)


def summarize_run(project_root: Path, run_id: str, out_path: Path) -> None:
    profile_dir = project_root / "repro" / "logs" / "profile" / run_id
    timings_path = profile_dir / "timings.csv"
    io_path = profile_dir / "io_timings.csv"

    run_log_path = project_root / "repro" / "logs" / "script_runs" / run_id / "run_log.txt"

    if not timings_path.exists():
        raise FileNotFoundError(f"Missing timings file: {timings_path}")
    if not io_path.exists():
        raise FileNotFoundError(f"Missing io timings file: {io_path}")

    section_agg: Dict[str, Agg] = {}
    group_agg: Dict[str, Agg] = {}
    timings_rows = 0

    for i, row in enumerate(_read_csv_rows(timings_path)):
        if i == 0:
            # header
            continue
        if len(row) < 4:
            continue
        section, _start, _end, elapsed_str = row[0], row[1], row[2], row[3]
        try:
            elapsed = float(elapsed_str)
        except ValueError:
            continue
        timings_rows += 1
        section_agg.setdefault(section, Agg()).add(elapsed)
        group = _section_group(section)
        group_agg.setdefault(group, Agg()).add(elapsed)

    io_kind_agg: Dict[str, Agg] = {}
    io_rows = 0
    slow_io: List[Tuple[float, str, str]] = []  # (elapsed, kind, basename(file))

    for i, row in enumerate(_read_csv_rows(io_path)):
        if i == 0:
            continue
        if len(row) < 6:
            continue
        kind, file_path, _start, _end, elapsed_str, _bytes = row[0], row[1], row[2], row[3], row[4], row[5]
        try:
            elapsed = float(elapsed_str)
        except ValueError:
            continue
        io_rows += 1
        io_kind_agg.setdefault(kind, Agg()).add(elapsed)
        base = os.path.basename(file_path) if file_path else ""
        slow_io.append((elapsed, kind, base))

    slow_io.sort(key=lambda x: x[0], reverse=True)

    # Ranking helpers
    def top_items(d: Dict[str, Agg], n: int) -> List[Tuple[str, Agg]]:
        return sorted(d.items(), key=lambda kv: kv[1].total, reverse=True)[:n]

    top_modules = [(k, v) for k, v in top_items(section_agg, 200) if k.endswith(".R")]
    top_sections = [(k, v) for k, v in top_items(section_agg, 50) if not k.endswith(".R")]
    top_groups = top_items(group_agg, 20)
    top_io_kinds = top_items(io_kind_agg, 20)

    start_dt, end_dt = _parse_wall_time(run_log_path)
    wall_sec: Optional[float] = None
    if start_dt and end_dt:
        wall_sec = (end_dt - start_dt).total_seconds()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = []
    lines.append(f"# Profile summary: `{run_id}`")
    lines.append("")
    lines.append(f"- Generated: {now}")
    lines.append(f"- Project root: `{project_root}`")
    lines.append(f"- Profile dir: `{profile_dir}`")
    lines.append(f"- Timings rows: {timings_rows}")
    lines.append(f"- IO rows: {io_rows}")
    if wall_sec is not None:
        lines.append(f"- Wall time (from run_log): {_format_sec(wall_sec)}")
    else:
        lines.append(f"- Wall time (from run_log): unavailable (missing END marker or run_log)")
    lines.append("")
    lines.append("## Group totals (inclusive timers)")
    lines.append(_md_table(
        ["group", "count", "sum", "mean", "max"],
        [
            [g, str(a.count), _format_sec(a.total), _format_sec(a.mean()), _format_sec(a.max)]
            for g, a in top_groups
        ],
    ))
    lines.append("")
    lines.append("Notes:")
    lines.append("- These timers are **inclusive** (nested sections overlap); treat them as ranking signals.")
    lines.append("")
    lines.append("## Top modules")
    lines.append(_md_table(
        ["module", "count", "sum", "mean", "max"],
        [
            [m, str(a.count), _format_sec(a.total), _format_sec(a.mean()), _format_sec(a.max)]
            for m, a in top_modules[:15]
        ],
    ))
    lines.append("")
    lines.append("## Top internal sections")
    lines.append(_md_table(
        ["section", "count", "sum", "mean", "max"],
        [
            [s, str(a.count), _format_sec(a.total), _format_sec(a.mean()), _format_sec(a.max)]
            for s, a in top_sections[:20]
        ],
    ))
    lines.append("")
    lines.append("## I/O kinds (inclusive)")
    lines.append(_md_table(
        ["kind", "count", "sum", "mean", "max"],
        [
            [k, str(a.count), _format_sec(a.total), _format_sec(a.mean()), _format_sec(a.max)]
            for k, a in top_io_kinds[:15]
        ],
    ))
    lines.append("")
    lines.append("Notes:")
    lines.append("- `ggsave` time can overlap with device flush (`png.dev.off`, etc.). Use this as a diagnostic ranking.")
    lines.append("")
    lines.append("## Slowest I/O events (top 20)")
    lines.append(_md_table(
        ["elapsed", "kind", "file"],
        [
            [_format_sec(el), kind, fname]
            for el, kind, fname in slow_io[:20]
        ],
    ))
    lines.append("")
    lines.append("## Step 4 candidates (auto-suggest)")
    if not top_sections:
        lines.append("- No internal section timers found; re-run with `PROFILE=TRUE`.")
    else:
        # Heuristic: list a few largest internal sections.
        for s, a in top_sections[:8]:
            lines.append(f"- `{s}` (~{_format_sec(a.total)} total across {a.count} call(s))")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize PROFILE=TRUE timing logs for a given RUN_ID.")
    parser.add_argument("--project-root", default="/data/muscat_data/jaguir26/project1_ucsc_phd")
    parser.add_argument("--run-id", required=True, help="RUN_ID used when running scripts/run_environmetrics_figures.R")
    parser.add_argument(
        "--out",
        default="",
        help="Output markdown path. Default: repro/logs/profile/<RUN_ID>/profile_summary.md",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    run_id = args.run_id
    out_path = Path(args.out)
    if str(out_path) == "":
        out_path = project_root / "repro" / "logs" / "profile" / run_id / "profile_summary.md"

    summarize_run(project_root=project_root, run_id=run_id, out_path=out_path)
    print(str(out_path))


if __name__ == "__main__":
    main()

