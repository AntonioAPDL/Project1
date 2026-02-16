#!/usr/bin/env python3
"""Refine and validate GloFAS coverage windows from an existing scan run.

Goal:
1) Reuse baseline evidence from a completed scan run.
2) Resolve previously-unresolved combos with targeted probes.
3) Re-check lower/upper boundary dates for anchored combos.

Scope:
- Metadata-light requests only (small bbox, one day, one lead-time).
- No bulk downloads.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464
DEFAULT_BUFFER_DEG = 0.2

VARIABLE = "river_discharge_in_the_last_24_hours"

# Transition-aware seed dates to prioritize useful probes.
SEED_DATES_BY_KEY: Dict[Tuple[str, str], List[str]] = {
    ("forecast", "operational"): [
        "2019-11-05",
        "2021-05-26",
        "2023-03-27",
        "2024-02-28",
    ],
    ("forecast", "version_3_1"): [
        "2021-05-26",
        "2021-06-15",
        "2021-10-26",
    ],
    ("forecast", "version_2_1"): [
        "2019-11-05",
        "2020-01-16",
        "2020-12-08",
    ],
    ("historical", "version_4_0"): [
        "1979-09-28",
        "2021-01-04",
        "2022-07-31",
        "2023-03-27",
    ],
    ("historical", "version_3_1"): [
        "2021-02-08",
        "2021-06-15",
    ],
    ("historical", "version_2_1"): [
        "2019-10-30",
        "2019-11-05",
        "2020-01-16",
    ],
    ("reforecast", "version_4_0"): [
        "2021-01-04",
        "2023-03-27",
    ],
    ("reforecast", "version_3_1"): [
        "2021-06-14",
        "2021-06-17",
    ],
    ("reforecast", "version_2_2"): [
        "2020-12-14",
        "2021-01-04",
    ],
}


def parse_date(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def parse_csv_list(raw: str) -> List[str]:
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def area_bbox(lat: float, lon: float, buffer_deg: float) -> List[float]:
    return [lat + buffer_deg, lon - buffer_deg, lat - buffer_deg, lon + buffer_deg]


def classify_error(message: str) -> str:
    msg = message.lower()
    if "400 client error" in msg or "invalid request" in msg:
        return "invalid_request"
    if "429" in msg or "too many requests" in msg:
        return "rate_limit"
    if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
        return "auth"
    if "timeout" in msg:
        return "timeout"
    if "connection" in msg:
        return "connection"
    return "unknown"


@dataclass(frozen=True)
class Combo:
    combo_id: str
    lane: str
    priority: str
    dataset: str
    system_version: str
    hydrological_model: str
    product_type: str
    domain_start: date
    domain_end: date
    leadtime_hour: Optional[str]


@dataclass
class BaselineCoverage:
    combo_id: str
    anchor_status: str
    anchor_date: Optional[date]
    earliest_success_date: Optional[date]
    latest_success_date: Optional[date]
    confidence: str


@dataclass
class ProbeResult:
    ok: bool
    status: str
    error_class: str
    error_message: str
    bytes_written: Optional[int]
    source: str


@dataclass
class RefinedRecord:
    combo_id: str
    lane: str
    priority: str
    dataset: str
    system_version: str
    hydrological_model: str
    product_type: str
    baseline_anchor_status: str
    baseline_earliest: str
    baseline_latest: str
    refined_anchor_status: str
    refined_anchor_date: str
    refined_earliest: str
    refined_latest: str
    lower_bound_check: str
    upper_bound_check: str
    boundary_confidence: str
    attempts_total: int
    attempts_ok: int
    attempts_error: int
    invalid_request_count: int
    timeout_count: int
    notes: str


def build_logger(log_path: Path, verbose: bool) -> logging.Logger:
    logger = logging.getLogger(f"glofas_refine_{log_path.parent.name}")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO if verbose else logging.WARNING)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def retrieve_with_timeout(
    dataset: str,
    request_payload: Dict[str, object],
    output_file: Path,
    timeout_seconds: int,
    retry_max: int,
    sleep_max: int,
) -> Tuple[bool, str]:
    def _worker(
        ds: str,
        req: Dict[str, object],
        out_path: str,
        out_queue: Queue,
        retry_max_inner: int,
        sleep_max_inner: int,
    ) -> None:
        try:
            import cdsapi  # type: ignore

            client = cdsapi.Client(
                retry_max=retry_max_inner,
                sleep_max=sleep_max_inner,
                quiet=True,
            )
            client.retrieve(ds, req).download(out_path)
            out_queue.put({"ok": True, "error": ""})
        except Exception as exc:
            out_queue.put({"ok": False, "error": str(exc)})

    q: Queue = Queue()
    p = Process(
        target=_worker,
        args=(dataset, request_payload, str(output_file), q, retry_max, sleep_max),
    )
    p.start()
    p.join(timeout_seconds)

    if p.is_alive():
        p.terminate()
        p.join(5)
        if p.is_alive():
            p.kill()
            p.join(5)
        return False, f"timeout after {timeout_seconds}s"

    if q.empty():
        return False, "request subprocess exited without response payload"

    payload = q.get()
    if payload.get("ok"):
        return True, ""
    return False, str(payload.get("error", "unknown subprocess error"))


def build_request(combo: Combo, probe_day: date, area: List[float]) -> Dict[str, object]:
    req: Dict[str, object] = {
        "system_version": [combo.system_version],
        "hydrological_model": [combo.hydrological_model],
        "product_type": [combo.product_type],
        "variable": [VARIABLE],
        "data_format": "grib2",
        "download_format": "zip",
        "area": area,
    }
    if combo.lane == "historical":
        req["hyear"] = [f"{probe_day.year:04d}"]
        req["hmonth"] = [f"{probe_day.month:02d}"]
        req["hday"] = [f"{probe_day.day:02d}"]
    elif combo.lane == "forecast":
        req["year"] = [f"{probe_day.year:04d}"]
        req["month"] = [f"{probe_day.month:02d}"]
        req["day"] = [f"{probe_day.day:02d}"]
        req["leadtime_hour"] = [str(combo.leadtime_hour or "24")]
    elif combo.lane == "reforecast":
        req["hyear"] = [f"{probe_day.year:04d}"]
        req["hmonth"] = [f"{probe_day.month:02d}"]
        req["hday"] = [f"{probe_day.day:02d}"]
        req["leadtime_hour"] = [str(combo.leadtime_hour or "24")]
    else:
        raise ValueError(f"Unknown lane: {combo.lane}")
    return req


def iter_valid_days(combo: Combo, reforecast_weekdays: Set[int]) -> List[date]:
    days: List[date] = []
    d = combo.domain_start
    while d <= combo.domain_end:
        if combo.lane == "reforecast" and d.weekday() not in reforecast_weekdays:
            d += timedelta(days=1)
            continue
        days.append(d)
        d += timedelta(days=1)
    return days


def closest_valid_date(candidate: date, valid_days: List[date]) -> Optional[date]:
    if not valid_days:
        return None
    if candidate <= valid_days[0]:
        return valid_days[0]
    if candidate >= valid_days[-1]:
        return valid_days[-1]
    lo = 0
    hi = len(valid_days) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if valid_days[mid] < candidate:
            lo = mid + 1
        else:
            hi = mid
    right = valid_days[lo]
    left = valid_days[lo - 1]
    return right if abs((right - candidate).days) < abs((candidate - left).days) else left


def parse_optional_date(raw: str) -> Optional[date]:
    s = (raw or "").strip()
    if not s:
        return None
    return parse_date(s)


def load_baseline(base_run_dir: Path) -> Tuple[Dict[str, Combo], Dict[str, BaselineCoverage], Dict[Tuple[str, str], ProbeResult], Dict[str, Dict[str, int]]]:
    planned = json.loads((base_run_dir / "manifests" / "planned_combos.json").read_text(encoding="utf-8"))
    combos: Dict[str, Combo] = {}
    for row in planned:
        combo = Combo(
            combo_id=row["priority"] + "__" + row["lane"] + "__" + row["system_version"] + "__" + row["hydrological_model"] + "__" + row["product_type"],
            lane=row["lane"],
            priority=row["priority"],
            dataset=row["dataset"],
            system_version=row["system_version"],
            hydrological_model=row["hydrological_model"],
            product_type=row["product_type"],
            domain_start=parse_date(row["domain_start"]),
            domain_end=parse_date(row["domain_end"]),
            leadtime_hour=str(row["leadtime_hour"]) if row.get("leadtime_hour") is not None else None,
        )
        combos[combo.combo_id] = combo

    coverage: Dict[str, BaselineCoverage] = {}
    with (base_run_dir / "manifests" / "coverage_summary.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            coverage[row["combo_id"]] = BaselineCoverage(
                combo_id=row["combo_id"],
                anchor_status=row["anchor_status"],
                anchor_date=parse_optional_date(row["anchor_date"]),
                earliest_success_date=parse_optional_date(row["earliest_success_date"]),
                latest_success_date=parse_optional_date(row["latest_success_date"]),
                confidence=row["confidence"],
            )

    # Cache prior attempt outcomes by (combo_id, probe_date); prefer ok over error.
    cache: Dict[Tuple[str, str], ProbeResult] = {}
    combo_err_counts: Dict[str, Dict[str, int]] = {}
    with (base_run_dir / "manifests" / "attempts.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["combo_id"], row["probe_date"])
            status = row["status"]
            ok = status.startswith("ok")
            prev = cache.get(key)
            if prev is None or (ok and not prev.ok):
                cache[key] = ProbeResult(
                    ok=ok,
                    status=status,
                    error_class=row["error_class"],
                    error_message=row["error_message"],
                    bytes_written=int(row["bytes"]) if row.get("bytes") else None,
                    source="baseline",
                )
            c = combo_err_counts.setdefault(row["combo_id"], {})
            if status == "error":
                ec = row["error_class"] or "unknown"
                c[ec] = c.get(ec, 0) + 1

    return combos, coverage, cache, combo_err_counts


def to_str(d: Optional[date]) -> str:
    return d.isoformat() if d else ""


def seed_dates(combo: Combo, baseline: BaselineCoverage, valid_days: List[date]) -> List[date]:
    seeds: List[date] = []
    for raw in SEED_DATES_BY_KEY.get((combo.lane, combo.system_version), []):
        seeds.append(parse_date(raw))
    midpoint = combo.domain_start + (combo.domain_end - combo.domain_start) / 2
    seeds.extend([combo.domain_start, combo.domain_end, midpoint])
    if baseline.anchor_date:
        seeds.extend([baseline.anchor_date])
    if baseline.earliest_success_date:
        seeds.extend(
            [
                baseline.earliest_success_date,
                baseline.earliest_success_date - timedelta(days=1),
                baseline.earliest_success_date + timedelta(days=1),
            ]
        )
    if baseline.latest_success_date:
        seeds.extend(
            [
                baseline.latest_success_date,
                baseline.latest_success_date - timedelta(days=1),
                baseline.latest_success_date + timedelta(days=1),
            ]
        )
    out: List[date] = []
    seen: Set[date] = set()
    for s in seeds:
        snapped = closest_valid_date(s, valid_days)
        if snapped is None:
            continue
        if snapped not in seen:
            out.append(snapped)
            seen.add(snapped)
    return out


def verify_combo(
    combo: Combo,
    baseline: BaselineCoverage,
    baseline_cache: Dict[Tuple[str, str], ProbeResult],
    baseline_error_counts: Dict[str, int],
    args: argparse.Namespace,
    run_dir: Path,
    logger: logging.Logger,
) -> Tuple[List[Dict[str, object]], RefinedRecord]:
    attempts: List[Dict[str, object]] = []
    local_cache: Dict[date, ProbeResult] = {}
    area = area_bbox(args.lat, args.lon, args.buffer_deg)
    valid_days = iter_valid_days(combo, reforecast_weekdays=set(args.reforecast_weekdays))
    if not valid_days:
        rec = RefinedRecord(
            combo_id=combo.combo_id,
            lane=combo.lane,
            priority=combo.priority,
            dataset=combo.dataset,
            system_version=combo.system_version,
            hydrological_model=combo.hydrological_model,
            product_type=combo.product_type,
            baseline_anchor_status=baseline.anchor_status,
            baseline_earliest=to_str(baseline.earliest_success_date),
            baseline_latest=to_str(baseline.latest_success_date),
            refined_anchor_status="no_valid_days",
            refined_anchor_date="",
            refined_earliest="",
            refined_latest="",
            lower_bound_check="n/a",
            upper_bound_check="n/a",
            boundary_confidence="none",
            attempts_total=0,
            attempts_ok=0,
            attempts_error=0,
            invalid_request_count=0,
            timeout_count=0,
            notes="no valid days in combo domain",
        )
        return attempts, rec

    budget = int(args.max_attempts_per_combo)
    combo_out_dir = run_dir / "downloads" / combo.lane / combo.combo_id
    combo_out_dir.mkdir(parents=True, exist_ok=True)

    def record_attempt(d: date, res: ProbeResult, payload: Dict[str, object], output_file: Path) -> None:
        attempts.append(
            {
                "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "combo_id": combo.combo_id,
                "lane": combo.lane,
                "priority": combo.priority,
                "dataset": combo.dataset,
                "system_version": combo.system_version,
                "hydrological_model": combo.hydrological_model,
                "product_type": combo.product_type,
                "probe_date": d.isoformat(),
                "status": res.status,
                "ok": int(res.ok),
                "error_class": res.error_class,
                "error_message": res.error_message,
                "bytes": res.bytes_written if res.bytes_written is not None else "",
                "source": res.source,
                "output_path": str(output_file),
                "request_json": json.dumps(payload, sort_keys=True),
            }
        )

    def probe(d: date, force_live: bool = False) -> ProbeResult:
        nonlocal budget
        if d in local_cache:
            return local_cache[d]

        payload = build_request(combo, d, area)
        output_file = combo_out_dir / f"{d.isoformat()}.zip"

        key = (combo.combo_id, d.isoformat())
        if not force_live and key in baseline_cache:
            base = baseline_cache[key]
            res = ProbeResult(
                ok=base.ok,
                status="baseline_ok" if base.ok else "baseline_error",
                error_class=base.error_class,
                error_message=base.error_message,
                bytes_written=base.bytes_written,
                source="baseline",
            )
            local_cache[d] = res
            record_attempt(d, res, payload, output_file)
            return res

        if budget <= 0:
            res = ProbeResult(
                ok=False,
                status="budget_exhausted",
                error_class="budget",
                error_message="attempt budget exhausted",
                bytes_written=None,
                source="local",
            )
            local_cache[d] = res
            record_attempt(d, res, payload, output_file)
            return res

        budget -= 1
        if not args.run:
            res = ProbeResult(
                ok=False,
                status="dry_run",
                error_class="dry_run",
                error_message="probe skipped (dry-run)",
                bytes_written=None,
                source="local",
            )
            local_cache[d] = res
            record_attempt(d, res, payload, output_file)
            return res

        ok, err = retrieve_with_timeout(
            dataset=combo.dataset,
            request_payload=payload,
            output_file=output_file,
            timeout_seconds=int(args.request_timeout_seconds),
            retry_max=int(args.cdsapi_retry_max),
            sleep_max=int(args.cdsapi_sleep_max),
        )
        if ok:
            nbytes = int(output_file.stat().st_size) if output_file.exists() else None
            res = ProbeResult(
                ok=True,
                status="ok",
                error_class="",
                error_message="",
                bytes_written=nbytes,
                source="local",
            )
        else:
            res = ProbeResult(
                ok=False,
                status="error",
                error_class=classify_error(err),
                error_message=err,
                bytes_written=None,
                source="local",
            )
        local_cache[d] = res
        record_attempt(d, res, payload, output_file)
        return res

    logger.info("start combo=%s baseline=%s", combo.combo_id, baseline.anchor_status)
    day_to_index = {d: i for i, d in enumerate(valid_days)}
    seeds = seed_dates(combo, baseline, valid_days)

    anchor: Optional[date] = baseline.anchor_date
    # Force-live confirmation for already-anchored combos.
    if anchor is not None:
        if args.run:
            anchor_res = probe(anchor, force_live=True)
            if not anchor_res.ok:
                anchor = None

    if anchor is None:
        invalid_only_baseline = (
            baseline.anchor_status != "found"
            and baseline_error_counts
            and set(baseline_error_counts.keys()) == {"invalid_request"}
            and baseline_error_counts.get("invalid_request", 0) >= int(args.min_invalid_confirm_count)
        )
        # If baseline strongly suggests unsupported combo, do a small live confirmation set.
        seed_iter = seeds
        if invalid_only_baseline:
            seed_iter = seeds[: int(args.invalid_confirm_probes)]

        for d in seed_iter:
            res = probe(d, force_live=True)
            if res.ok:
                anchor = d
                break

    if anchor is None:
        # Final chance: coarse stride for timeout-heavy combos.
        if not baseline_error_counts or baseline_error_counts.get("timeout", 0) > 0:
            stride = max(1, int(args.unresolved_stride_days))
            sample = valid_days[::stride]
            if valid_days and sample[-1] != valid_days[-1]:
                sample.append(valid_days[-1])
            for d in sample[: int(args.max_unresolved_stride_probes)]:
                res = probe(d, force_live=True)
                if res.ok:
                    anchor = d
                    break

    if anchor is None:
        err_classes = [a["error_class"] for a in attempts if a["status"] in {"error", "baseline_error"}]
        invalid_n = sum(1 for e in err_classes if e == "invalid_request")
        timeout_n = sum(1 for e in err_classes if e == "timeout")
        if err_classes and invalid_n == len(err_classes):
            notes = "no anchor; tested points consistently invalid_request (likely unsupported combo)"
        elif timeout_n > 0:
            notes = "no anchor; timeout present (availability unresolved)"
        else:
            notes = "no anchor in tested points"
        rec = RefinedRecord(
            combo_id=combo.combo_id,
            lane=combo.lane,
            priority=combo.priority,
            dataset=combo.dataset,
            system_version=combo.system_version,
            hydrological_model=combo.hydrological_model,
            product_type=combo.product_type,
            baseline_anchor_status=baseline.anchor_status,
            baseline_earliest=to_str(baseline.earliest_success_date),
            baseline_latest=to_str(baseline.latest_success_date),
            refined_anchor_status="not_found",
            refined_anchor_date="",
            refined_earliest="",
            refined_latest="",
            lower_bound_check="not_tested",
            upper_bound_check="not_tested",
            boundary_confidence="none",
            attempts_total=len(attempts),
            attempts_ok=sum(1 for a in attempts if a["ok"] == 1),
            attempts_error=sum(1 for a in attempts if a["status"] in {"error", "baseline_error"}),
            invalid_request_count=invalid_n,
            timeout_count=timeout_n,
            notes=notes,
        )
        logger.info("done combo=%s status=not_found", combo.combo_id)
        return attempts, rec

    n_days = len(valid_days)
    anchor_idx = day_to_index[anchor]

    def as_valid_idx(d: Optional[date]) -> Optional[int]:
        if d is None:
            return None
        snapped = closest_valid_date(d, valid_days)
        if snapped is None:
            return None
        return day_to_index[snapped]

    # Start from baseline boundaries when available; this is a focused re-check pass.
    earliest_idx = as_valid_idx(baseline.earliest_success_date) or anchor_idx
    latest_idx = as_valid_idx(baseline.latest_success_date) or anchor_idx

    # Fast path for baseline-anchored combos: targeted boundary re-check only.
    fast_found_path = (
        baseline.anchor_status == "found"
        and baseline.earliest_success_date is not None
        and baseline.latest_success_date is not None
    )

    if fast_found_path and not args.aggressive_boundary_expansion:
        if args.run:
            if not probe(valid_days[earliest_idx], force_live=True).ok:
                earliest_idx = anchor_idx
            if not probe(valid_days[latest_idx], force_live=True).ok:
                latest_idx = anchor_idx

        # One-step extension tests around boundaries.
        if earliest_idx > 0 and probe(valid_days[earliest_idx - 1], force_live=True).ok:
            earliest_idx -= 1
        if latest_idx < (n_days - 1) and probe(valid_days[latest_idx + 1], force_live=True).ok:
            latest_idx += 1

        earliest = valid_days[earliest_idx]
        latest = valid_days[latest_idx]

        lower_check = "not_checked"
        if earliest_idx == 0:
            lower_check = "at_domain_start"
        else:
            prev_res = probe(valid_days[earliest_idx - 1], force_live=True)
            cur_res = probe(earliest, force_live=True)
            if (not prev_res.ok) and cur_res.ok:
                lower_check = "bracketed"
            elif prev_res.ok:
                lower_check = "not_bracketed_prev_success"
            else:
                lower_check = "uncertain"

        upper_check = "not_checked"
        if latest_idx == n_days - 1:
            upper_check = "at_domain_end"
        else:
            next_res = probe(valid_days[latest_idx + 1], force_live=True)
            cur_res = probe(latest, force_live=True)
            if cur_res.ok and (not next_res.ok):
                upper_check = "bracketed"
            elif next_res.ok:
                upper_check = "not_bracketed_next_success"
            else:
                upper_check = "uncertain"

        if lower_check == "bracketed" and upper_check == "bracketed":
            boundary_conf = "high"
        elif "not_bracketed" in lower_check or "not_bracketed" in upper_check:
            boundary_conf = "medium"
        elif lower_check.startswith("at_domain") or upper_check.startswith("at_domain"):
            boundary_conf = "medium"
        else:
            boundary_conf = "low"
    else:
        # For newly found anchors from unresolved combos, do focused local expansion.
        if args.run:
            if probe(valid_days[earliest_idx], force_live=True).ok is False:
                earliest_idx = anchor_idx
            if probe(valid_days[latest_idx], force_live=True).ok is False:
                latest_idx = anchor_idx

        # Full-range doubling expansion. This avoids truncating multi-year windows.
        offset_steps: List[int] = []
        step = 1
        while step < n_days:
            offset_steps.append(step)
            step *= 2

        def expand_boundary(start_idx: int, direction: int) -> Tuple[int, Optional[int]]:
            best_idx = start_idx
            fail_idx: Optional[int] = None
            current = start_idx
            for step in offset_steps:
                cand_idx = current + (direction * step)
                cand_idx = max(0, min(n_days - 1, cand_idx))
                if cand_idx == current:
                    break
                r = probe(valid_days[cand_idx], force_live=True)
                if r.ok:
                    best_idx = cand_idx
                    current = cand_idx
                else:
                    fail_idx = cand_idx
                    break
                if budget <= 0:
                    break
            return best_idx, fail_idx

        earliest_idx, left_fail_idx = expand_boundary(earliest_idx, direction=-1)
        latest_idx, right_fail_idx = expand_boundary(latest_idx, direction=1)

        if left_fail_idx is not None and budget > 0:
            lo = min(left_fail_idx, earliest_idx) + 1
            hi = max(left_fail_idx, earliest_idx)
            while lo < hi and budget > 0:
                mid = (lo + hi) // 2
                r = probe(valid_days[mid], force_live=True)
                if r.ok:
                    hi = mid
                else:
                    lo = mid + 1
            earliest_idx = lo

        if right_fail_idx is not None and budget > 0:
            lo = min(right_fail_idx, latest_idx)
            hi = max(right_fail_idx, latest_idx) - 1
            while lo < hi and budget > 0:
                mid = (lo + hi + 1) // 2
                r = probe(valid_days[mid], force_live=True)
                if r.ok:
                    lo = mid
                else:
                    hi = mid - 1
            latest_idx = lo

        earliest = valid_days[earliest_idx]
        latest = valid_days[latest_idx]

        lower_check = "not_checked"
        if earliest_idx == 0:
            lower_check = "at_domain_start"
        else:
            prev_idx = earliest_idx - 1
            prev_res = probe(valid_days[prev_idx], force_live=True)
            cur_res = probe(earliest, force_live=True)
            if (not prev_res.ok) and cur_res.ok:
                lower_check = "bracketed"
            elif prev_res.ok:
                lower_check = "not_bracketed_prev_success"
            else:
                lower_check = "uncertain"

        upper_check = "not_checked"
        if latest_idx == n_days - 1:
            upper_check = "at_domain_end"
        else:
            next_idx = latest_idx + 1
            next_res = probe(valid_days[next_idx], force_live=True)
            cur_res = probe(latest, force_live=True)
            if cur_res.ok and (not next_res.ok):
                upper_check = "bracketed"
            elif next_res.ok:
                upper_check = "not_bracketed_next_success"
            else:
                upper_check = "uncertain"

        if lower_check == "bracketed" and upper_check == "bracketed":
            boundary_conf = "high"
        elif "not_bracketed" in lower_check or "not_bracketed" in upper_check:
            boundary_conf = "medium"
        elif lower_check.startswith("at_domain") or upper_check.startswith("at_domain"):
            boundary_conf = "medium"
        else:
            boundary_conf = "low"

    invalid_count = sum(
        1 for a in attempts if a["status"] in {"error", "baseline_error"} and a["error_class"] == "invalid_request"
    )
    timeout_count = sum(
        1 for a in attempts if a["status"] in {"error", "baseline_error"} and a["error_class"] == "timeout"
    )
    notes_bits: List[str] = []
    if budget <= 0:
        notes_bits.append("attempt budget exhausted")
    if earliest == latest:
        notes_bits.append("point anchor")
    notes = "; ".join(notes_bits)
    rec = RefinedRecord(
        combo_id=combo.combo_id,
        lane=combo.lane,
        priority=combo.priority,
        dataset=combo.dataset,
        system_version=combo.system_version,
        hydrological_model=combo.hydrological_model,
        product_type=combo.product_type,
        baseline_anchor_status=baseline.anchor_status,
        baseline_earliest=to_str(baseline.earliest_success_date),
        baseline_latest=to_str(baseline.latest_success_date),
        refined_anchor_status="found",
        refined_anchor_date=anchor.isoformat(),
        refined_earliest=earliest.isoformat(),
        refined_latest=latest.isoformat(),
        lower_bound_check=lower_check,
        upper_bound_check=upper_check,
        boundary_confidence=boundary_conf,
        attempts_total=len(attempts),
        attempts_ok=sum(1 for a in attempts if a["ok"] == 1),
        attempts_error=sum(1 for a in attempts if a["status"] in {"error", "baseline_error"}),
        invalid_request_count=invalid_count,
        timeout_count=timeout_count,
        notes=notes,
    )
    logger.info(
        "done combo=%s found earliest=%s latest=%s conf=%s",
        combo.combo_id,
        rec.refined_earliest,
        rec.refined_latest,
        rec.boundary_confidence,
    )
    return attempts, rec


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refine GloFAS coverage windows from baseline scan evidence.")
    parser.add_argument(
        "--base-run-dir",
        type=Path,
        default=Path("repro") / "glofas_coverage_scan_runs" / "scan_20260216T015036Z",
        help="Baseline run directory containing planned_combos, attempts, and coverage_summary.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("repro") / "glofas_coverage_scan_runs",
    )
    parser.add_argument("--run", action="store_true", help="Execute live probes. Default is dry-run.")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--max-attempts-per-combo", type=int, default=20)
    parser.add_argument("--min-invalid-confirm-count", type=int, default=5)
    parser.add_argument("--invalid-confirm-probes", type=int, default=3)
    parser.add_argument("--unresolved-stride-days", type=int, default=180)
    parser.add_argument("--max-unresolved-stride-probes", type=int, default=8)
    parser.add_argument("--request-timeout-seconds", type=int, default=120)
    parser.add_argument("--cdsapi-retry-max", type=int, default=2)
    parser.add_argument("--cdsapi-sleep-max", type=int, default=10)
    parser.add_argument("--reforecast-weekdays", type=int, nargs="+", default=[0, 3])
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT)
    parser.add_argument("--lon", type=float, default=DEFAULT_LON)
    parser.add_argument("--buffer-deg", type=float, default=DEFAULT_BUFFER_DEG)
    parser.add_argument("--priorities", default="", help="Optional CSV filter (e.g., P1,P2).")
    parser.add_argument("--lanes", default="", help="Optional CSV filter (e.g., historical,reforecast).")
    parser.add_argument(
        "--system-versions",
        default="",
        help="Optional CSV filter (e.g., version_3_1,version_4_0).",
    )
    parser.add_argument(
        "--hydrological-models",
        default="",
        help="Optional CSV filter (e.g., lisflood,htessel_lisflood).",
    )
    parser.add_argument(
        "--product-types",
        default="",
        help="Optional CSV filter for product_type values.",
    )
    parser.add_argument(
        "--aggressive-boundary-expansion",
        action="store_true",
        help="Use full-range doubling boundary expansion even for baseline-found combos.",
    )
    parser.add_argument(
        "--combo-contains",
        default="",
        help="Optional substring filter for combo_id (for targeted reruns).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    if not args.base_run_dir.exists():
        print(f"Missing base run dir: {args.base_run_dir}", file=sys.stderr)
        return 2

    run_id = datetime.utcnow().strftime("refine_%Y%m%dT%H%M%SZ")
    run_dir = args.out_root / run_id
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "manifests").mkdir(parents=True, exist_ok=True)
    logger = build_logger(run_dir / "logs" / "refine.log", verbose=args.verbose)
    logger.info("base_run_dir=%s", args.base_run_dir)
    logger.info("mode=%s", "run" if args.run else "dry-run")

    combos, coverage, baseline_cache, combo_err_counts = load_baseline(args.base_run_dir)
    combo_ids = sorted(combos.keys())

    priorities = set(parse_csv_list(args.priorities))
    lanes = set(parse_csv_list(args.lanes))
    system_versions = set(parse_csv_list(args.system_versions))
    hydrological_models = set(parse_csv_list(args.hydrological_models))
    product_types = set(parse_csv_list(args.product_types))

    def _matches_filters(combo: Combo) -> bool:
        if priorities and combo.priority not in priorities:
            return False
        if lanes and combo.lane not in lanes:
            return False
        if system_versions and combo.system_version not in system_versions:
            return False
        if hydrological_models and combo.hydrological_model not in hydrological_models:
            return False
        if product_types and combo.product_type not in product_types:
            return False
        return True

    combo_ids = [c for c in combo_ids if _matches_filters(combos[c])]
    if args.combo_contains:
        combo_ids = [c for c in combo_ids if args.combo_contains in c]
    if not combo_ids:
        logger.error("No combos selected.")
        return 2

    logger.info("selected_combos=%d", len(combo_ids))

    all_attempts: List[Dict[str, object]] = []
    refined_rows: List[RefinedRecord] = []

    def _task(combo_id: str) -> Tuple[List[Dict[str, object]], RefinedRecord]:
        combo = combos[combo_id]
        base = coverage.get(
            combo_id,
            BaselineCoverage(
                combo_id=combo_id,
                anchor_status="not_found",
                anchor_date=None,
                earliest_success_date=None,
                latest_success_date=None,
                confidence="none",
            ),
        )
        err_counts = combo_err_counts.get(combo_id, {})
        return verify_combo(combo, base, baseline_cache, err_counts, args, run_dir, logger)

    max_workers = max(1, min(int(args.max_workers), len(combo_ids)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_task, c): c for c in combo_ids}
        for fut in as_completed(futures):
            combo_id = futures[fut]
            try:
                attempts, rec = fut.result()
            except Exception as exc:
                logger.exception("combo=%s failed: %s", combo_id, exc)
                continue
            all_attempts.extend(attempts)
            refined_rows.append(rec)

    attempts_path = run_dir / "manifests" / "refined_attempts.csv"
    write_csv(attempts_path, all_attempts)

    refined_dicts = [r.__dict__ for r in sorted(refined_rows, key=lambda x: x.combo_id)]
    refined_path = run_dir / "manifests" / "refined_ranges.csv"
    write_csv(refined_path, refined_dicts)

    summary = {
        "base_run_dir": str(args.base_run_dir),
        "run_dir": str(run_dir),
        "combos_total": len(refined_rows),
        "refined_found": sum(1 for r in refined_rows if r.refined_anchor_status == "found"),
        "refined_not_found": sum(1 for r in refined_rows if r.refined_anchor_status != "found"),
        "attempts_total": len(all_attempts),
        "attempts_ok": sum(1 for a in all_attempts if a["ok"] == 1),
        "attempts_error_or_baseline_error": sum(
            1 for a in all_attempts if a["status"] in {"error", "baseline_error"}
        ),
    }
    (run_dir / "manifests" / "refine_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    logger.info(
        "completed combos=%d found=%d attempts=%d out=%s",
        summary["combos_total"],
        summary["refined_found"],
        summary["attempts_total"],
        run_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
