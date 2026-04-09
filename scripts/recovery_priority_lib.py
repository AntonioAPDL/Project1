#!/usr/bin/env python3
"""Shared helpers for recovery checkpointing, stopping, and prioritized relaunch."""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


PROJECT_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
DEFAULT_RECOVERY_RUN_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "data_recovery/site=11160500/"
    "recovery_run=site11160500_recovery_20260406T185022Z"
)
SITE_LAT = 37.0443931
SITE_LON = -122.072464
GLOFAS_PROJECT_FOCUS_START = date(1987, 5, 29)
GLOFAS_PROJECT_FOCUS_END = date(2023, 5, 1)
GLOFAS_V31_HISTFIX_END = date(2022, 5, 11)
NWM_V12_EXPECTED_YEARS = list(range(1993, 2018))
GLOFAS_OPERATIONAL_EXPECTED_ISSUE_DATES = 1176


def run_text(command: str) -> str:
    return subprocess.check_output(command, shell=True, text=True).strip()


def list_nonempty_files(paths: Iterable[Path]) -> List[Path]:
    return [path for path in paths if path.exists() and path.is_file() and path.stat().st_size > 0]


def month_starts_between(start: date, end: date) -> Iterable[date]:
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        yield cursor
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def expected_month_shards(start: date, end: date) -> int:
    return sum(1 for _ in month_starts_between(start, end))


def count_nonempty_month_shards(product_root: Path, start: date, end: date) -> int:
    count = 0
    for month_start in month_starts_between(start, end):
        month_dir = product_root / f"year={month_start.year:04d}" / f"month={month_start.month:02d}"
        if list_nonempty_files(month_dir.glob("*.zip")):
            count += 1
    return count


def count_nonempty_issue_dates(grib_root: Path) -> Dict[str, int]:
    completed = 0
    touched = 0
    if not grib_root.exists():
        return {"completed": 0, "touched": 0}
    for issue_dir in sorted(grib_root.glob("issue_date=*")):
        touched += 1
        if list_nonempty_files(issue_dir.glob("*.grib")):
            completed += 1
    return {"completed": completed, "touched": touched}


def count_csv_rows(path: Path) -> Optional[int]:
    if not path.exists():
        return None
    with path.open("r", newline="", encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def find_single_child(root: Path) -> Path:
    children = sorted([path for path in root.iterdir() if path.is_dir()])
    if len(children) != 1:
        raise RuntimeError(f"Expected exactly one child directory under {root}, found {len(children)}")
    return children[0]


def find_latest_child(root: Path) -> Path:
    children = sorted([path for path in root.iterdir() if path.is_dir()])
    if not children:
        raise RuntimeError(f"Expected at least one child directory under {root}, found 0")
    return children[-1]


def find_hist_family_root(recovery_run_root: Path) -> Path:
    return find_latest_child(recovery_run_root / "family=glofas_historical" / "full_runs")


def find_nwm_full_root(recovery_run_root: Path) -> Path:
    return find_latest_child(recovery_run_root / "family=nwm_retrospective" / "full_runs")


def find_nwm_v12_run_root(recovery_run_root: Path) -> Path:
    full_root = find_nwm_full_root(recovery_run_root)
    matches = sorted(full_root.glob("nwm_v12_campaign_*"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one NWM v1.2 campaign under {full_root}, found {len(matches)}")
    return matches[0]


def find_glofas_operational_campaign_root(recovery_run_root: Path) -> Path:
    full_root = recovery_run_root / "family=glofas_operational_forecasts" / "full_runs"
    candidates = sorted(
        [
            path
            for path in full_root.iterdir()
            if path.is_dir() and path.name.startswith("glofas_operational_parallel_") and "stagecheck" not in path.name
        ]
    )
    if len(candidates) != 1:
        raise RuntimeError(f"Expected exactly one operational campaign under {full_root}, found {len(candidates)}")
    return candidates[0]


def list_target_tmux_sessions() -> List[str]:
    try:
        raw = run_text("tmux ls 2>/dev/null")
    except subprocess.CalledProcessError:
        return []
    sessions: List[str] = []
    for line in raw.splitlines():
        name = line.split(":", 1)[0].strip()
        if (
            name.startswith("nwm_v12_w")
            or name.startswith("split_")
            or name.startswith("glofas_hist_v40_parallel_")
            or name.startswith("multimodel_v8_histfix_")
        ):
            sessions.append(name)
    return sessions


def list_v31_histfix_refill_pids() -> List[int]:
    command = (
        "ps -eo pid=,cmd= | "
        "grep 'forecats_download_glofas_historical_consolidated.py' | "
        "grep 'hist_v31_lisflood_cons' | "
        "grep 'hist_v31_histfix_refill_' | "
        "grep -v grep || true"
    )
    raw = run_text(command)
    pids: List[int] = []
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        pid_text = text.split(None, 1)[0]
        try:
            pids.append(int(pid_text))
        except ValueError:
            continue
    return pids


def parse_split_summary(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def current_resource_snapshot() -> Dict[str, str]:
    return {
        "host": run_text("hostname -f"),
        "timestamp": run_text("date"),
        "uptime": run_text("uptime"),
        "memory": run_text("free -h | sed -n '2p'"),
        "data_disk": run_text("df -h /data | tail -n 1"),
        "user_processes": run_text(
            "ps -u jaguir26 -o %cpu=,%mem=,rss= | "
            "awk '{cpu+=$1; mem+=$2; rss+=$3} "
            "END {printf \"cpu_sum=%.1f mem_sum=%.1f rss_gib=%.2f\\n\", cpu, mem, rss/1024/1024}'"
        ),
    }


def operational_phase_status(campaign_root: Path) -> Dict[str, object]:
    grib_root = campaign_root / "outputs" / "download_root" / "grib"
    counts = count_nonempty_issue_dates(grib_root)
    expected = GLOFAS_OPERATIONAL_EXPECTED_ISSUE_DATES
    split_summary = campaign_root / "plans" / "split_summary.csv"
    if split_summary.exists():
        expected = sum(int(row["issue_count"]) for row in parse_split_summary(split_summary))
    return {
        "expected": expected,
        "completed": counts["completed"],
        "touched": counts["touched"],
        "percent_complete": round((counts["completed"] / expected) * 100.0, 1) if expected else 0.0,
        "campaign_root": str(campaign_root),
    }


def nwm_v12_phase_status(v12_run_root: Path) -> Dict[str, object]:
    yearly_dir = v12_run_root / "point_series" / "v12_yearly"
    done = len(list_nonempty_files(yearly_dir.glob("v12_*_daily.csv")))
    expected = len(NWM_V12_EXPECTED_YEARS)
    open_years_raw = run_text(
        "ps -eo cmd | grep 'nwm_retrospective_extract_point_v12_comp.py' | "
        "grep -v grep | sed -E 's/.*--start-date ([0-9]{4})-01-01.*/\\1/' | tr '\\n' ' ' || true"
    )
    open_years = [token for token in open_years_raw.split() if token]
    return {
        "expected": expected,
        "completed": done,
        "open_years": open_years,
        "percent_complete": round((done / expected) * 100.0, 1) if expected else 0.0,
        "run_root": str(v12_run_root),
    }


def glofas_historical_phase_status(recovery_family_root: Path, product_id: str, focus_start: date, focus_end: date) -> Dict[str, object]:
    product_root = recovery_family_root / "outputs" / "historical_zips" / product_id
    done = count_nonempty_month_shards(product_root, focus_start, focus_end)
    expected = expected_month_shards(focus_start, focus_end)
    return {
        "expected": expected,
        "completed": done,
        "percent_complete": round((done / expected) * 100.0, 1) if expected else 0.0,
        "product_root": str(product_root),
        "product_id": product_id,
        "focus_start": focus_start.isoformat(),
        "focus_end": focus_end.isoformat(),
    }


def snapshot_priority_status(recovery_run_root: Path) -> Dict[str, object]:
    hist_family_root = find_hist_family_root(recovery_run_root)
    v12_run_root = find_nwm_v12_run_root(recovery_run_root)
    op_campaign_root = find_glofas_operational_campaign_root(recovery_run_root)
    return {
        "resource": current_resource_snapshot(),
        "lanes": {
            "glofas_historical_v31": glofas_historical_phase_status(
                hist_family_root,
                product_id="hist_v31_lisflood_cons",
                focus_start=GLOFAS_PROJECT_FOCUS_START,
                focus_end=GLOFAS_PROJECT_FOCUS_END,
            ),
            "glofas_operational": operational_phase_status(op_campaign_root),
            "nwm_retrospective_v12": nwm_v12_phase_status(v12_run_root),
            "glofas_historical_v40": glofas_historical_phase_status(
                hist_family_root,
                product_id="hist_v40_lisflood_cons",
                focus_start=GLOFAS_PROJECT_FOCUS_START,
                focus_end=GLOFAS_PROJECT_FOCUS_END,
            ),
        },
        "complete_lanes": {
            "usgs_rows": count_csv_rows(
                recovery_run_root
                / "family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv"
            ),
            "nwm_v20_rows": count_csv_rows(
                recovery_run_root
                / "family=nwm_retrospective/full_runs/source_native_tranche1_20260406T194500Z/"
                / "nwm_v20_campaign_source_native_tranche1_20260406T194500Z/point_series/v20_full_daily.csv"
            ),
            "glofas_v21_point_rows": count_csv_rows(
                hist_family_root / "outputs/point_series/hist_v21_htessel_cons_point.csv"
            ),
        },
        "target_tmux_sessions": list_target_tmux_sessions(),
        "target_v31_refill_pids": list_v31_histfix_refill_pids(),
    }
