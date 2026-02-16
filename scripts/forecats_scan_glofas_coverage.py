#!/usr/bin/env python3
"""Parallel metadata-light coverage scan for GloFAS historical/forecast/reforecast.

Purpose:
1. Probe valid date windows per (dataset, system_version, hydrological_model, product_type).
2. Execute lanes in parallel (historical, reforecast, forecast).
3. Preserve complete traceability (attempt-level log + coverage summary + local archive audit).

Scope:
- Lightweight requests only (small area, one day, one lead-time for forecast/reforecast).
- No bulk transfer logic.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464
DEFAULT_BUFFER_DEG = 0.2

DEFAULT_RUN_ROOT = Path("repro") / "glofas_coverage_scan_runs"

PRIORITY_PLAN: Dict[str, Dict[str, str]] = {
    # User-requested priority:
    # 1) version 3.1 family first
    # 2) then version 4.0 and operational
    # 3) then version 2.1 / 2.2 associated products
    "P1": {
        "historical": "version_3_1",
        "reforecast": "version_3_1",
        "forecast": "version_3_1",
    },
    "P2": {
        "historical": "version_4_0",
        "reforecast": "version_4_0",
        "forecast": "operational",
    },
    "P3": {
        "historical": "version_2_1",
        "reforecast": "version_2_2",
        "forecast": "version_2_1",
    },
}

LANE_TO_DATASET = {
    "historical": "cems-glofas-historical",
    "forecast": "cems-glofas-forecast",
    "reforecast": "cems-glofas-reforecast",
}

LANE_PRODUCT_TYPES = {
    "historical": ["consolidated", "intermediate"],
    "forecast": ["control_forecast", "ensemble_perturbed_forecasts"],
    "reforecast": ["control_reforecast", "ensemble_perturbed_reforecast"],
}

HYDRO_MODELS = ["htessel_lisflood", "lisflood"]
VARIABLE = "river_discharge_in_the_last_24_hours"


@dataclass(frozen=True)
class Combo:
    priority: str
    lane: str
    dataset: str
    system_version: str
    hydrological_model: str
    product_type: str
    domain_start: date
    domain_end: date
    leadtime_hour: Optional[str]

    @property
    def combo_id(self) -> str:
        return (
            f"{self.priority}__{self.lane}__{self.system_version}"
            f"__{self.hydrological_model}__{self.product_type}"
        )


@dataclass
class AttemptRecord:
    timestamp_utc: str
    run_id: str
    lane: str
    priority: str
    combo_id: str
    dataset: str
    system_version: str
    hydrological_model: str
    product_type: str
    probe_date: str
    status: str
    bytes: Optional[int]
    error_class: str
    error_message: str
    output_path: str
    request_json: str


@dataclass
class CoverageRecord:
    run_id: str
    lane: str
    priority: str
    combo_id: str
    dataset: str
    system_version: str
    hydrological_model: str
    product_type: str
    anchor_status: str
    anchor_date: str
    earliest_success_date: str
    latest_success_date: str
    confidence: str
    attempts_total: int
    attempts_success: int
    attempts_error: int
    notes: str


def parse_date(raw: str) -> date:
    return datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()


def parse_csv_list(raw: str) -> List[str]:
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def area_bbox(lat: float, lon: float, buffer_deg: float) -> List[float]:
    return [lat + buffer_deg, lon - buffer_deg, lat - buffer_deg, lon + buffer_deg]


def classify_error(message: str) -> str:
    msg = message.lower()
    if "400 client error" in msg or "invalid request" in msg:
        return "invalid_request"
    if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
        return "auth"
    if "timeout" in msg:
        return "timeout"
    if "connection" in msg:
        return "connection"
    return "unknown"


def build_domain_map(args: argparse.Namespace) -> Dict[str, Tuple[date, date]]:
    return {
        "historical": (parse_date(args.historical_start), parse_date(args.historical_end)),
        "forecast": (parse_date(args.forecast_start), parse_date(args.forecast_end)),
        "reforecast": (parse_date(args.reforecast_start), parse_date(args.reforecast_end)),
    }


def build_combos(args: argparse.Namespace) -> List[Combo]:
    wanted_priorities = set(parse_csv_list(args.priorities))
    wanted_lanes = set(parse_csv_list(args.lanes))
    domain_map = build_domain_map(args)

    combos: List[Combo] = []
    for priority in ["P1", "P2", "P3"]:
        if priority not in wanted_priorities:
            continue
        lane_versions = PRIORITY_PLAN[priority]
        for lane in ["historical", "reforecast", "forecast"]:
            if lane not in wanted_lanes:
                continue
            if lane == "forecast" and args.skip_forecast_lane:
                continue

            version = lane_versions[lane]
            dataset = LANE_TO_DATASET[lane]
            domain_start, domain_end = domain_map[lane]
            product_types = (
                [LANE_PRODUCT_TYPES[lane][0]] if args.control_only else list(LANE_PRODUCT_TYPES[lane])
            )
            leadtime = None
            if lane == "forecast":
                leadtime = str(args.forecast_leadtime_hour)
            if lane == "reforecast":
                leadtime = str(args.reforecast_leadtime_hour)

            for hydrological_model in HYDRO_MODELS:
                for product_type in product_types:
                    combos.append(
                        Combo(
                            priority=priority,
                            lane=lane,
                            dataset=dataset,
                            system_version=version,
                            hydrological_model=hydrological_model,
                            product_type=product_type,
                            domain_start=domain_start,
                            domain_end=domain_end,
                            leadtime_hour=leadtime,
                        )
                    )
    return combos


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
        req["leadtime_hour"] = [str(combo.leadtime_hour)]
    elif combo.lane == "reforecast":
        req["hyear"] = [f"{probe_day.year:04d}"]
        req["hmonth"] = [f"{probe_day.month:02d}"]
        req["hday"] = [f"{probe_day.day:02d}"]
        req["leadtime_hour"] = [str(combo.leadtime_hour)]
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
    # Binary search nearest by insertion.
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


def anchor_seeds(combo: Combo, valid_days: List[date]) -> List[date]:
    seeds: List[date] = []
    by_key = {
        ("historical", "version_3_1"): ["2021-06-15", "2021-05-26"],
        ("historical", "version_4_0"): ["2023-03-27", "2021-01-04"],
        ("historical", "version_2_1"): ["2020-01-16", "2019-11-05"],
        ("forecast", "version_3_1"): ["2021-06-15", "2021-05-26"],
        ("forecast", "operational"): ["2022-12-25", "2023-03-27"],
        ("forecast", "version_2_1"): ["2020-01-16", "2020-12-01"],
        ("reforecast", "version_3_1"): ["2021-06-14", "2021-06-17"],
        ("reforecast", "version_4_0"): ["2021-01-04", "2020-12-31"],
        ("reforecast", "version_2_2"): ["2020-12-14", "2021-01-04"],
    }
    for raw in by_key.get((combo.lane, combo.system_version), []):
        seeds.append(parse_date(raw))

    midpoint = combo.domain_start + (combo.domain_end - combo.domain_start) / 2
    seeds.extend([combo.domain_start, combo.domain_end, midpoint])

    out: List[date] = []
    seen: Set[date] = set()
    for d in seeds:
        snapped = closest_valid_date(d, valid_days)
        if snapped is None:
            continue
        if snapped not in seen:
            out.append(snapped)
            seen.add(snapped)
    return out


def build_logger(log_file: Path, verbose: bool) -> logging.Logger:
    logger = logging.getLogger(f"glofas_coverage_scan_{log_file.parent.name}")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO if verbose else logging.WARNING)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def summarize_local_forecast_archive(archive_root: Path) -> Dict[str, object]:
    result: Dict[str, object] = {
        "archive_root": str(archive_root),
        "request_file_count": 0,
        "issue_date_min": "",
        "issue_date_max": "",
        "system_version_counts": {},
        "hydrological_model_counts": {},
        "product_type_counts": {},
        "model_transition_points": [],
        "notes": "",
    }
    if not archive_root.exists():
        result["notes"] = "archive root not found"
        return result

    request_files = sorted(archive_root.glob("issue_date=*/*.request.json"))
    result["request_file_count"] = len(request_files)
    if not request_files:
        result["notes"] = "no request.json files found"
        return result

    system_counts: Dict[str, int] = {}
    model_counts: Dict[str, int] = {}
    ptype_counts: Dict[str, int] = {}

    rows: List[Tuple[str, str]] = []
    for p in request_files:
        issue = p.parent.name.replace("issue_date=", "")
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        sv = payload.get("system_version")
        hm = payload.get("hydrological_model")
        pt = payload.get("product_type")
        sv_key = sv[0] if isinstance(sv, list) and sv else str(sv)
        hm_key = hm[0] if isinstance(hm, list) and hm else str(hm)
        pt_key = ",".join(pt) if isinstance(pt, list) else str(pt)

        system_counts[sv_key] = system_counts.get(sv_key, 0) + 1
        model_counts[hm_key] = model_counts.get(hm_key, 0) + 1
        ptype_counts[pt_key] = ptype_counts.get(pt_key, 0) + 1
        rows.append((issue, hm_key))

    rows.sort()
    result["issue_date_min"] = rows[0][0]
    result["issue_date_max"] = rows[-1][0]
    result["system_version_counts"] = system_counts
    result["hydrological_model_counts"] = model_counts
    result["product_type_counts"] = ptype_counts

    transitions: List[Dict[str, str]] = []
    prev: Optional[str] = None
    for issue, hm in rows:
        if prev is None:
            prev = hm
            continue
        if hm != prev:
            transitions.append(
                {
                    "issue_date": issue,
                    "from_model": prev,
                    "to_model": hm,
                }
            )
            prev = hm
    result["model_transition_points"] = transitions
    result["notes"] = "summary from local request JSON manifests"
    return result


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
        args=(
            dataset,
            request_payload,
            str(output_file),
            q,
            retry_max,
            sleep_max,
        ),
    )
    p.start()
    p.join(timeout_seconds)

    if p.is_alive():
        p.terminate()
        p.join()
        return False, f"timeout after {timeout_seconds}s"

    if q.empty():
        return False, "request subprocess exited without response payload"

    payload = q.get()
    if payload.get("ok"):
        return True, ""
    return False, str(payload.get("error", "unknown subprocess error"))


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_combo_scan(
    combo: Combo,
    args: argparse.Namespace,
    run_id: str,
    run_dir: Path,
    logger: logging.Logger,
) -> Tuple[List[AttemptRecord], CoverageRecord]:
    attempts: List[AttemptRecord] = []
    success_cache: Dict[date, bool] = {}

    valid_days = iter_valid_days(combo, reforecast_weekdays=set(args.reforecast_weekdays))
    if not valid_days:
        rec = CoverageRecord(
            run_id=run_id,
            lane=combo.lane,
            priority=combo.priority,
            combo_id=combo.combo_id,
            dataset=combo.dataset,
            system_version=combo.system_version,
            hydrological_model=combo.hydrological_model,
            product_type=combo.product_type,
            anchor_status="no_valid_days",
            anchor_date="",
            earliest_success_date="",
            latest_success_date="",
            confidence="none",
            attempts_total=0,
            attempts_success=0,
            attempts_error=0,
            notes="no valid days for this lane/domain",
        )
        return attempts, rec

    logger.info(
        "[%s] start combo=%s days=%d",
        combo.lane.upper(),
        combo.combo_id,
        len(valid_days),
    )

    area = area_bbox(args.lat, args.lon, args.buffer_deg)
    combo_download_dir = run_dir / "downloads" / combo.lane / combo.combo_id
    combo_download_dir.mkdir(parents=True, exist_ok=True)

    attempt_budget = int(args.max_attempts_per_combo)
    budget_hit = False

    def probe(day: date) -> bool:
        nonlocal attempt_budget, budget_hit
        if day in success_cache:
            return success_cache[day]

        if attempt_budget <= 0:
            success_cache[day] = False
            budget_hit = True
            return False

        attempt_budget -= 1
        request_payload = build_request(combo, day, area)
        output_file = combo_download_dir / f"{day.isoformat()}.zip"

        if not args.overwrite and output_file.exists() and output_file.stat().st_size > 0:
            success_cache[day] = True
            attempts.append(
                AttemptRecord(
                    timestamp_utc=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    run_id=run_id,
                    lane=combo.lane,
                    priority=combo.priority,
                    combo_id=combo.combo_id,
                    dataset=combo.dataset,
                    system_version=combo.system_version,
                    hydrological_model=combo.hydrological_model,
                    product_type=combo.product_type,
                    probe_date=day.isoformat(),
                    status="ok_cached",
                    bytes=int(output_file.stat().st_size),
                    error_class="",
                    error_message="",
                    output_path=str(output_file),
                    request_json=json.dumps(request_payload, sort_keys=True),
                )
            )
            return True

        if not args.run:
            success_cache[day] = False
            attempts.append(
                AttemptRecord(
                    timestamp_utc=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    run_id=run_id,
                    lane=combo.lane,
                    priority=combo.priority,
                    combo_id=combo.combo_id,
                    dataset=combo.dataset,
                    system_version=combo.system_version,
                    hydrological_model=combo.hydrological_model,
                    product_type=combo.product_type,
                    probe_date=day.isoformat(),
                    status="dry_run",
                    bytes=None,
                    error_class="dry_run",
                    error_message="probe not executed in dry-run mode",
                    output_path=str(output_file),
                    request_json=json.dumps(request_payload, sort_keys=True),
                )
            )
            return False

        try:
            ok, err = retrieve_with_timeout(
                dataset=combo.dataset,
                request_payload=request_payload,
                output_file=output_file,
                timeout_seconds=int(args.request_timeout_seconds),
                retry_max=int(args.cdsapi_retry_max),
                sleep_max=int(args.cdsapi_sleep_max),
            )
            if not ok:
                raise RuntimeError(err)
            nbytes = int(output_file.stat().st_size) if output_file.exists() else None
            success_cache[day] = True
            attempts.append(
                AttemptRecord(
                    timestamp_utc=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    run_id=run_id,
                    lane=combo.lane,
                    priority=combo.priority,
                    combo_id=combo.combo_id,
                    dataset=combo.dataset,
                    system_version=combo.system_version,
                    hydrological_model=combo.hydrological_model,
                    product_type=combo.product_type,
                    probe_date=day.isoformat(),
                    status="ok",
                    bytes=nbytes,
                    error_class="",
                    error_message="",
                    output_path=str(output_file),
                    request_json=json.dumps(request_payload, sort_keys=True),
                )
            )
            return True
        except Exception as exc:
            message = str(exc)
            success_cache[day] = False
            attempts.append(
                AttemptRecord(
                    timestamp_utc=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    run_id=run_id,
                    lane=combo.lane,
                    priority=combo.priority,
                    combo_id=combo.combo_id,
                    dataset=combo.dataset,
                    system_version=combo.system_version,
                    hydrological_model=combo.hydrological_model,
                    product_type=combo.product_type,
                    probe_date=day.isoformat(),
                    status="error",
                    bytes=None,
                    error_class=classify_error(message),
                    error_message=message,
                    output_path=str(output_file),
                    request_json=json.dumps(request_payload, sort_keys=True),
                )
            )
            return False

    day_to_index = {d: i for i, d in enumerate(valid_days)}

    # 1) Find anchor.
    anchor: Optional[date] = None
    for seed in anchor_seeds(combo, valid_days):
        if probe(seed):
            anchor = seed
            break
        if attempt_budget <= 0:
            break

    # 2) Fallback anchor scan over coarse grid if needed.
    if anchor is None:
        stride = max(1, int(args.anchor_stride_days))
        sample_days = valid_days[::stride]
        if valid_days and sample_days[-1] != valid_days[-1]:
            sample_days.append(valid_days[-1])
        for d in sample_days:
            if probe(d):
                anchor = d
                break
            if attempt_budget <= 0:
                break

    if anchor is None:
        notes = "no successful anchor in tested days"
        rec = CoverageRecord(
            run_id=run_id,
            lane=combo.lane,
            priority=combo.priority,
            combo_id=combo.combo_id,
            dataset=combo.dataset,
            system_version=combo.system_version,
            hydrological_model=combo.hydrological_model,
            product_type=combo.product_type,
            anchor_status="not_found",
            anchor_date="",
            earliest_success_date="",
            latest_success_date="",
            confidence="none",
            attempts_total=len(attempts),
            attempts_success=sum(1 for a in attempts if a.status.startswith("ok")),
            attempts_error=sum(1 for a in attempts if a.status == "error"),
            notes=notes,
        )
        logger.info("[%s] no anchor combo=%s", combo.lane.upper(), combo.combo_id)
        return attempts, rec

    anchor_idx = day_to_index[anchor]

    # 3) Earliest boundary search (index-based, valid-day calendar aware).
    earliest_idx = anchor_idx
    left_fail_idx: Optional[int] = None
    step = 1
    while earliest_idx > 0:
        cand_idx = max(0, earliest_idx - step)
        cand_day = valid_days[cand_idx]
        if probe(cand_day):
            earliest_idx = cand_idx
            step *= 2
            if earliest_idx == 0:
                break
        else:
            left_fail_idx = cand_idx
            break

    if left_fail_idx is not None:
        lo = left_fail_idx + 1
        hi = earliest_idx
        while lo < hi:
            mid = (lo + hi) // 2
            if probe(valid_days[mid]):
                hi = mid
            else:
                lo = mid + 1
        earliest_idx = lo

    # 4) Latest boundary search.
    latest_idx = anchor_idx
    right_fail_idx: Optional[int] = None
    step = 1
    n_days = len(valid_days)
    while latest_idx < n_days - 1:
        cand_idx = min(n_days - 1, latest_idx + step)
        cand_day = valid_days[cand_idx]
        if probe(cand_day):
            latest_idx = cand_idx
            step *= 2
            if latest_idx == n_days - 1:
                break
        else:
            right_fail_idx = cand_idx
            break

    if right_fail_idx is not None:
        lo = latest_idx
        hi = right_fail_idx - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if probe(valid_days[mid]):
                lo = mid
            else:
                hi = mid - 1
        latest_idx = lo

    earliest_day = valid_days[earliest_idx]
    latest_day = valid_days[latest_idx]

    left_bracketed = left_fail_idx is not None
    right_bracketed = right_fail_idx is not None
    if left_bracketed and right_bracketed:
        confidence = "high"
    elif left_bracketed or right_bracketed:
        confidence = "medium"
    else:
        confidence = "low"

    notes_bits = []
    if not left_bracketed:
        notes_bits.append("left boundary hit domain start or budget before explicit failure")
    if not right_bracketed:
        notes_bits.append("right boundary hit domain end or budget before explicit failure")
    if budget_hit:
        notes_bits.append("attempt budget exhausted")
    notes = "; ".join(notes_bits)

    rec = CoverageRecord(
        run_id=run_id,
        lane=combo.lane,
        priority=combo.priority,
        combo_id=combo.combo_id,
        dataset=combo.dataset,
        system_version=combo.system_version,
        hydrological_model=combo.hydrological_model,
        product_type=combo.product_type,
        anchor_status="found",
        anchor_date=anchor.isoformat(),
        earliest_success_date=earliest_day.isoformat(),
        latest_success_date=latest_day.isoformat(),
        confidence=confidence,
        attempts_total=len(attempts),
        attempts_success=sum(1 for a in attempts if a.status.startswith("ok")),
        attempts_error=sum(1 for a in attempts if a.status == "error"),
        notes=notes,
    )
    logger.info(
        "[%s] done combo=%s earliest=%s latest=%s confidence=%s attempts=%d",
        combo.lane.upper(),
        combo.combo_id,
        rec.earliest_success_date,
        rec.latest_success_date,
        rec.confidence,
        rec.attempts_total,
    )
    return attempts, rec


def run_lane(
    lane: str,
    combos: List[Combo],
    args: argparse.Namespace,
    run_id: str,
    run_dir: Path,
    logger: logging.Logger,
) -> Tuple[List[AttemptRecord], List[CoverageRecord]]:
    lane_attempts: List[AttemptRecord] = []
    lane_coverage: List[CoverageRecord] = []
    lane_combos = [c for c in combos if c.lane == lane]
    lane_combos.sort(key=lambda c: (c.priority, c.system_version, c.hydrological_model, c.product_type))

    logger.info("[%s] combos=%d", lane.upper(), len(lane_combos))
    for combo in lane_combos:
        attempts, coverage = run_combo_scan(combo, args, run_id, run_dir, logger)
        lane_attempts.extend(attempts)
        lane_coverage.append(coverage)
    return lane_attempts, lane_coverage


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    today = datetime.utcnow().date()
    parser = argparse.ArgumentParser(
        description=(
            "Parallel GloFAS coverage scanner for historical/reforecast/forecast with "
            "priority phases and reproducible attempt logging."
        )
    )
    parser.add_argument("--out-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--run", action="store_true", help="Execute EWDS requests. Default is dry-run.")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--overwrite", action="store_true")

    parser.add_argument("--lat", type=float, default=DEFAULT_LAT)
    parser.add_argument("--lon", type=float, default=DEFAULT_LON)
    parser.add_argument("--buffer-deg", type=float, default=DEFAULT_BUFFER_DEG)

    parser.add_argument("--priorities", default="P1,P2,P3")
    parser.add_argument("--lanes", default="historical,reforecast,forecast")
    parser.add_argument("--skip-forecast-lane", action="store_true")
    parser.add_argument("--control-only", action="store_true")

    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--max-attempts-per-combo", type=int, default=60)
    parser.add_argument(
        "--request-timeout-seconds",
        type=int,
        default=240,
        help="Hard timeout per EWDS request attempt. Timed-out attempts are marked as errors and scan continues.",
    )
    parser.add_argument(
        "--cdsapi-retry-max",
        type=int,
        default=3,
        help="Retry count per request attempt inside cdsapi client.",
    )
    parser.add_argument(
        "--cdsapi-sleep-max",
        type=int,
        default=15,
        help="Max retry sleep seconds per request attempt inside cdsapi client.",
    )
    parser.add_argument("--anchor-stride-days", type=int, default=90)
    parser.add_argument("--reforecast-weekdays", type=int, nargs="+", default=[0, 3])

    parser.add_argument("--forecast-leadtime-hour", type=int, default=24)
    parser.add_argument("--reforecast-leadtime-hour", type=int, default=24)

    parser.add_argument("--historical-start", default="1979-01-01")
    parser.add_argument("--historical-end", default=(today - timedelta(days=1)).isoformat())
    parser.add_argument("--forecast-start", default="2019-11-05")
    parser.add_argument("--forecast-end", default=today.isoformat())
    parser.add_argument("--reforecast-start", default="1999-01-03")
    parser.add_argument("--reforecast-end", default="2023-11-25")

    parser.add_argument(
        "--local-forecast-archive-root",
        type=Path,
        default=Path("data") / "glofas_operational_medium_range" / "grib",
        help="Path to legacy local GloFAS forecast archive request manifests (*.request.json).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    run_id = datetime.utcnow().strftime("scan_%Y%m%dT%H%M%SZ")
    run_dir = args.out_root / run_id
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "manifests").mkdir(parents=True, exist_ok=True)
    (run_dir / "reports").mkdir(parents=True, exist_ok=True)

    logger = build_logger(run_dir / "logs" / "scan.log", verbose=args.verbose)
    logger.info("run_id=%s", run_id)
    logger.info("mode=%s", "run" if args.run else "dry-run")

    combos = build_combos(args)
    if not combos:
        logger.error("No combos selected after filtering.")
        return 2

    logger.info("total_combos=%d", len(combos))

    # Persist planned combos.
    planned_path = run_dir / "manifests" / "planned_combos.json"
    planned_path.write_text(
        json.dumps([asdict(c) for c in combos], indent=2, default=str, sort_keys=True),
        encoding="utf-8",
    )

    # Lane-parallel execution.
    wanted_lanes = [lane for lane in ["historical", "reforecast", "forecast"] if lane in parse_csv_list(args.lanes)]
    if args.skip_forecast_lane and "forecast" in wanted_lanes:
        wanted_lanes.remove("forecast")

    all_attempts: List[AttemptRecord] = []
    all_coverage: List[CoverageRecord] = []
    max_workers = max(1, min(int(args.max_workers), len(wanted_lanes)))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_lane, lane, combos, args, run_id, run_dir, logger): lane
            for lane in wanted_lanes
        }
        for fut in as_completed(futures):
            lane = futures[fut]
            try:
                lane_attempts, lane_coverage = fut.result()
            except Exception as exc:
                logger.exception("lane=%s failed: %s", lane, exc)
                continue
            all_attempts.extend(lane_attempts)
            all_coverage.extend(lane_coverage)

    # Write manifests.
    attempts_rows = [asdict(a) for a in all_attempts]
    coverage_rows = [asdict(c) for c in all_coverage]
    write_csv(run_dir / "manifests" / "attempts.csv", attempts_rows)
    write_csv(run_dir / "manifests" / "coverage_summary.csv", coverage_rows)

    # Write grouped summary by priority and lane.
    grouped: Dict[str, Dict[str, int]] = {}
    for row in coverage_rows:
        key = f"{row['priority']}::{row['lane']}"
        if key not in grouped:
            grouped[key] = {"combos": 0, "anchors_found": 0}
        grouped[key]["combos"] += 1
        if row["anchor_status"] == "found":
            grouped[key]["anchors_found"] += 1

    (run_dir / "reports" / "priority_lane_summary.json").write_text(
        json.dumps(grouped, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # Audit old local forecast archive usage to confirm versioning in prior data pulls.
    archive_summary = summarize_local_forecast_archive(args.local_forecast_archive_root)
    (run_dir / "reports" / "local_forecast_archive_summary.json").write_text(
        json.dumps(archive_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # Convenience one-line stats.
    n_ok = sum(1 for r in coverage_rows if r["anchor_status"] == "found")
    logger.info(
        "completed combos=%d anchors_found=%d attempts=%d out=%s",
        len(coverage_rows),
        n_ok,
        len(attempts_rows),
        run_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
