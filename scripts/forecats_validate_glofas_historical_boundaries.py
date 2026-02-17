#!/usr/bin/env python3
"""Strict boundary validation for selected GloFAS historical consolidated products.

Scope is intentionally fixed to three EWDS historical tuples:
1) version_2_1 + htessel_lisflood + consolidated
2) version_3_1 + lisflood + consolidated
3) version_4_0 + lisflood + consolidated

For each tuple, this script probes seven dates:
LB-1, LB, LB+1, midpoint, UB-1, UB, UB+1

Goal:
- Confirm boundary precision with metadata-light requests (small area, one day).
- Distinguish hard exclusions (invalid_request) from unresolved outcomes (timeout/other).
"""

from __future__ import annotations

import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


DEFAULT_OUT_ROOT = Path("repro") / "glofas_probe_runs"
DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464
DEFAULT_BUFFER_DEG = 0.2
DEFAULT_TIMEOUT_SECONDS = 360
DEFAULT_MAX_WORKERS = 1
VARIABLE = "river_discharge_in_the_last_24_hours"
DATASET = "cems-glofas-historical"


@dataclass(frozen=True)
class ProductSpec:
    product_id: str
    system_version: str
    hydrological_model: str
    product_type: str
    expected_lb: date
    expected_ub: date


@dataclass(frozen=True)
class ProbeCase:
    case_id: str
    product_id: str
    system_version: str
    hydrological_model: str
    product_type: str
    probe_date: date
    boundary_slot: str


def area_bbox(lat: float, lon: float, buffer_deg: float) -> List[float]:
    return [lat + buffer_deg, lon - buffer_deg, lat - buffer_deg, lon + buffer_deg]


def classify_error(message: str) -> str:
    msg = (message or "").lower()
    if "400 client error" in msg or "invalid request" in msg:
        return "invalid_request"
    if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
        return "auth"
    if "timeout" in msg:
        return "timeout"
    if "connection" in msg:
        return "connection"
    return "unknown"


def retrieve_with_timeout(
    request_payload: Dict[str, object],
    output_file: Path,
    timeout_seconds: int,
    retry_max: int,
    sleep_max: int,
) -> Tuple[bool, str]:
    def _worker(
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
            client.retrieve(DATASET, req).download(out_path)
            out_queue.put({"ok": True, "error": ""})
        except Exception as exc:
            out_queue.put({"ok": False, "error": str(exc)})

    q: Queue = Queue()
    p = Process(
        target=_worker,
        args=(request_payload, str(output_file), q, retry_max, sleep_max),
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


def build_request(case: ProbeCase, area: List[float]) -> Dict[str, object]:
    d = case.probe_date
    return {
        "system_version": [case.system_version],
        "hydrological_model": [case.hydrological_model],
        "product_type": [case.product_type],
        "variable": [VARIABLE],
        "hyear": [f"{d.year:04d}"],
        "hmonth": [f"{d.month:02d}"],
        "hday": [f"{d.day:02d}"],
        "data_format": "grib2",
        "download_format": "zip",
        "area": area,
    }


def build_specs() -> List[ProductSpec]:
    return [
        ProductSpec(
            product_id="hist_v21_htessel_cons",
            system_version="version_2_1",
            hydrological_model="htessel_lisflood",
            product_type="consolidated",
            expected_lb=date(1979, 1, 1),
            expected_ub=date(2022, 7, 31),
        ),
        ProductSpec(
            product_id="hist_v31_lisflood_cons",
            system_version="version_3_1",
            hydrological_model="lisflood",
            product_type="consolidated",
            expected_lb=date(1979, 1, 1),
            expected_ub=date(2024, 6, 30),
        ),
        ProductSpec(
            product_id="hist_v40_lisflood_cons",
            system_version="version_4_0",
            hydrological_model="lisflood",
            product_type="consolidated",
            expected_lb=date(1979, 1, 1),
            expected_ub=date(2025, 11, 30),
        ),
    ]


def midpoint_day(lb: date, ub: date) -> date:
    return lb + (ub - lb) // 2


def build_cases(specs: List[ProductSpec]) -> List[ProbeCase]:
    out: List[ProbeCase] = []
    for s in specs:
        checks = [
            ("lb_minus_1", s.expected_lb - timedelta(days=1)),
            ("lb", s.expected_lb),
            ("lb_plus_1", s.expected_lb + timedelta(days=1)),
            ("midpoint", midpoint_day(s.expected_lb, s.expected_ub)),
            ("ub_minus_1", s.expected_ub - timedelta(days=1)),
            ("ub", s.expected_ub),
            ("ub_plus_1", s.expected_ub + timedelta(days=1)),
        ]
        for slot, d in checks:
            out.append(
                ProbeCase(
                    case_id=f"{s.product_id}__{slot}",
                    product_id=s.product_id,
                    system_version=s.system_version,
                    hydrological_model=s.hydrological_model,
                    product_type=s.product_type,
                    probe_date=d,
                    boundary_slot=slot,
                )
            )
    return out


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate strict historical consolidated boundaries for selected GloFAS versions."
    )
    ap.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    ap.add_argument("--lat", type=float, default=DEFAULT_LAT)
    ap.add_argument("--lon", type=float, default=DEFAULT_LON)
    ap.add_argument("--buffer-deg", type=float, default=DEFAULT_BUFFER_DEG)
    ap.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    ap.add_argument("--retry-max", type=int, default=2)
    ap.add_argument("--sleep-max", type=int, default=20)
    ap.add_argument("--attempts-per-case", type=int, default=2)
    ap.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    ap.add_argument("--run", action="store_true", help="Execute EWDS retrievals.")
    return ap.parse_args(argv)


def case_row(
    case: ProbeCase,
    request_payload: Dict[str, object],
    status: str,
    error_class: str,
    error_message: str,
    bytes_out: int,
    output_path: Path,
    attempt_index: int,
) -> Dict[str, object]:
    return {
        "case_id": case.case_id,
        "product_id": case.product_id,
        "boundary_slot": case.boundary_slot,
        "dataset": DATASET,
        "system_version": case.system_version,
        "hydrological_model": case.hydrological_model,
        "product_type": case.product_type,
        "probe_date": case.probe_date.isoformat(),
        "attempt_index": attempt_index,
        "status": status,
        "error_class": error_class,
        "error_message": error_message,
        "bytes": bytes_out,
        "output_path": str(output_path),
        "request_json": json.dumps(request_payload, sort_keys=True),
    }


def run_case(
    case: ProbeCase,
    area: List[float],
    downloads_dir: Path,
    args: argparse.Namespace,
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    request_payload = build_request(case, area)
    attempt_rows: List[Dict[str, object]] = []

    if not args.run:
        row = case_row(
            case=case,
            request_payload=request_payload,
            status="dry_run",
            error_class="dry_run",
            error_message="not executed",
            bytes_out=0,
            output_path=downloads_dir / f"{case.case_id}__attempt1.zip",
            attempt_index=1,
        )
        attempt_rows.append(row)
        return row, attempt_rows

    best_final: Optional[Dict[str, object]] = None
    for attempt_idx in range(1, int(args.attempts_per_case) + 1):
        out_path = downloads_dir / f"{case.case_id}__attempt{attempt_idx}.zip"
        ok, err = retrieve_with_timeout(
            request_payload=request_payload,
            output_file=out_path,
            timeout_seconds=int(args.timeout_seconds),
            retry_max=int(args.retry_max),
            sleep_max=int(args.sleep_max),
        )
        if ok:
            row = case_row(
                case=case,
                request_payload=request_payload,
                status="ok",
                error_class="",
                error_message="",
                bytes_out=int(out_path.stat().st_size) if out_path.exists() else 0,
                output_path=out_path,
                attempt_index=attempt_idx,
            )
            attempt_rows.append(row)
            best_final = row
            break

        row = case_row(
            case=case,
            request_payload=request_payload,
            status="error",
            error_class=classify_error(err),
            error_message=err,
            bytes_out=0,
            output_path=out_path,
            attempt_index=attempt_idx,
        )
        attempt_rows.append(row)
        best_final = row

    assert best_final is not None
    return best_final, attempt_rows


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize(specs: List[ProductSpec], final_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    by_product: Dict[str, Dict[str, Dict[str, object]]] = {}
    for r in final_rows:
        by_product.setdefault(str(r["product_id"]), {})[str(r["boundary_slot"])] = r

    summaries: List[Dict[str, object]] = []
    for s in specs:
        slots = by_product.get(s.product_id, {})
        def st(slot: str) -> str:
            return str(slots.get(slot, {}).get("status", "missing"))
        def ec(slot: str) -> str:
            return str(slots.get(slot, {}).get("error_class", ""))

        lb_ok = st("lb") == "ok"
        ub_ok = st("ub") == "ok"
        lbm1_invalid = st("lb_minus_1") == "error" and ec("lb_minus_1") == "invalid_request"
        ubp1_invalid = st("ub_plus_1") == "error" and ec("ub_plus_1") == "invalid_request"
        lbp1_ok = st("lb_plus_1") == "ok"
        ubm1_ok = st("ub_minus_1") == "ok"
        mid_ok = st("midpoint") == "ok"

        if lb_ok and ub_ok and lbm1_invalid and ubp1_invalid and lbp1_ok and ubm1_ok and mid_ok:
            confidence = "high"
        elif lb_ok and ub_ok and lbm1_invalid and ubp1_invalid:
            confidence = "medium"
        else:
            confidence = "low_or_unresolved"

        summaries.append(
            {
                "product_id": s.product_id,
                "dataset": DATASET,
                "system_version": s.system_version,
                "hydrological_model": s.hydrological_model,
                "product_type": s.product_type,
                "expected_lb": s.expected_lb.isoformat(),
                "expected_ub": s.expected_ub.isoformat(),
                "lb_minus_1_status": st("lb_minus_1"),
                "lb_minus_1_error_class": ec("lb_minus_1"),
                "lb_status": st("lb"),
                "lb_plus_1_status": st("lb_plus_1"),
                "midpoint_status": st("midpoint"),
                "ub_minus_1_status": st("ub_minus_1"),
                "ub_status": st("ub"),
                "ub_plus_1_status": st("ub_plus_1"),
                "ub_plus_1_error_class": ec("ub_plus_1"),
                "boundary_confidence": confidence,
            }
        )

    return summaries


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)

    run_id = datetime.utcnow().strftime("hist_boundary_strict_%Y%m%dT%H%M%SZ")
    run_dir = args.out_root / run_id
    downloads_dir = run_dir / "downloads"
    manifests_dir = run_dir / "manifests"
    reports_dir = run_dir / "reports"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    specs = build_specs()
    cases = build_cases(specs)
    area = area_bbox(args.lat, args.lon, args.buffer_deg)

    (run_dir / "cases_resolved.json").write_text(
        json.dumps(
            [
                {
                    "case_id": c.case_id,
                    "product_id": c.product_id,
                    "boundary_slot": c.boundary_slot,
                    "probe_date": c.probe_date.isoformat(),
                    "request": build_request(c, area),
                }
                for c in cases
            ],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    final_rows: List[Dict[str, object]] = []
    attempt_rows: List[Dict[str, object]] = []

    with ThreadPoolExecutor(max_workers=int(args.max_workers)) as ex:
        futures = [
            ex.submit(run_case, c, area, downloads_dir, args)
            for c in cases
        ]
        for fut in as_completed(futures):
            final_row, rows = fut.result()
            final_rows.append(final_row)
            attempt_rows.extend(rows)
            print(
                f"[{final_row['status'].upper():>7}] {final_row['case_id']} "
                f"{final_row['probe_date']} {final_row['error_class']}"
            )

    final_rows.sort(key=lambda r: (str(r["product_id"]), str(r["boundary_slot"])))
    attempt_rows.sort(key=lambda r: (str(r["case_id"]), int(r["attempt_index"])))
    summary_rows = summarize(specs=specs, final_rows=final_rows)

    write_csv(manifests_dir / "boundary_checks_final.csv", final_rows)
    write_csv(manifests_dir / "boundary_checks_attempts.csv", attempt_rows)
    write_csv(reports_dir / "boundary_summary.csv", summary_rows)

    print(f"Wrote: {manifests_dir / 'boundary_checks_final.csv'}")
    print(f"Wrote: {manifests_dir / 'boundary_checks_attempts.csv'}")
    print(f"Wrote: {reports_dir / 'boundary_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(tuple(__import__("sys").argv[1:])))

