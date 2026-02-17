#!/usr/bin/env python3
"""Targeted GloFAS boundary checks for historical/reforecast combos.

This script runs a fixed list of small EWDS requests (point-area, one day,
one lead time for reforecast) with hard per-request timeout and logs outcomes.
It is intentionally narrow and designed for coverage validation, not bulk data.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


DEFAULT_OUT_ROOT = Path("repro") / "glofas_probe_runs"
DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464
DEFAULT_BUFFER_DEG = 0.2
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_WORKERS = 4

VARIABLE = "river_discharge_in_the_last_24_hours"


@dataclass(frozen=True)
class BoundaryCase:
    case_id: str
    lane: str
    dataset: str
    system_version: str
    hydrological_model: str
    product_type: str
    probe_date: str
    leadtime_hour: Optional[str] = None

    @property
    def combo_id(self) -> str:
        return (
            f"{self.lane}__{self.system_version}__{self.hydrological_model}"
            f"__{self.product_type}"
        )


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


def build_request(case: BoundaryCase, area: List[float]) -> Dict[str, object]:
    y, m, d = case.probe_date.split("-")
    req: Dict[str, object] = {
        "system_version": [case.system_version],
        "hydrological_model": [case.hydrological_model],
        "product_type": [case.product_type],
        "variable": [VARIABLE],
        "data_format": "grib2",
        "download_format": "zip",
        "area": area,
    }
    if case.lane == "historical":
        req["hyear"] = [y]
        req["hmonth"] = [m]
        req["hday"] = [d]
    elif case.lane == "reforecast":
        req["hyear"] = [y]
        req["hmonth"] = [m]
        req["hday"] = [d]
        req["leadtime_hour"] = [str(case.leadtime_hour or "24")]
    else:
        raise ValueError(f"Unsupported lane: {case.lane}")
    return req


def build_default_cases() -> List[BoundaryCase]:
    return [
        # Historical v2.1 (htessel_lisflood) -- explicit user-validated lane.
        BoundaryCase("hist_v21_htessel_cons_pre", "historical", "cems-glofas-historical", "version_2_1", "htessel_lisflood", "consolidated", "1978-12-31"),
        BoundaryCase("hist_v21_htessel_cons_lb", "historical", "cems-glofas-historical", "version_2_1", "htessel_lisflood", "consolidated", "1979-01-01"),
        BoundaryCase("hist_v21_htessel_cons_anchor", "historical", "cems-glofas-historical", "version_2_1", "htessel_lisflood", "consolidated", "1991-07-13"),
        BoundaryCase("hist_v21_htessel_cons_ub", "historical", "cems-glofas-historical", "version_2_1", "htessel_lisflood", "consolidated", "2022-07-31"),
        BoundaryCase("hist_v21_htessel_cons_post", "historical", "cems-glofas-historical", "version_2_1", "htessel_lisflood", "consolidated", "2022-08-01"),
        BoundaryCase("hist_v21_htessel_int_pre", "historical", "cems-glofas-historical", "version_2_1", "htessel_lisflood", "intermediate", "2019-09-30"),
        BoundaryCase("hist_v21_htessel_int_lb", "historical", "cems-glofas-historical", "version_2_1", "htessel_lisflood", "intermediate", "2019-10-01"),
        BoundaryCase("hist_v21_htessel_int_ub", "historical", "cems-glofas-historical", "version_2_1", "htessel_lisflood", "intermediate", "2022-09-01"),
        BoundaryCase("hist_v21_htessel_int_post", "historical", "cems-glofas-historical", "version_2_1", "htessel_lisflood", "intermediate", "2022-09-13"),
        # Historical v3.1 (lisflood)
        BoundaryCase("hist_v31_cons_pre", "historical", "cems-glofas-historical", "version_3_1", "lisflood", "consolidated", "1978-12-31"),
        BoundaryCase("hist_v31_cons_lb", "historical", "cems-glofas-historical", "version_3_1", "lisflood", "consolidated", "1979-01-01"),
        BoundaryCase("hist_v31_cons_interior", "historical", "cems-glofas-historical", "version_3_1", "lisflood", "consolidated", "2021-06-15"),
        BoundaryCase("hist_v31_cons_ub", "historical", "cems-glofas-historical", "version_3_1", "lisflood", "consolidated", "2024-06-30"),
        BoundaryCase("hist_v31_cons_post", "historical", "cems-glofas-historical", "version_3_1", "lisflood", "consolidated", "2024-07-01"),
        BoundaryCase("hist_v31_int_pre", "historical", "cems-glofas-historical", "version_3_1", "lisflood", "intermediate", "2020-12-31"),
        BoundaryCase("hist_v31_int_lb", "historical", "cems-glofas-historical", "version_3_1", "lisflood", "intermediate", "2021-01-01"),
        BoundaryCase("hist_v31_int_ub", "historical", "cems-glofas-historical", "version_3_1", "lisflood", "intermediate", "2024-09-23"),
        BoundaryCase("hist_v31_int_post", "historical", "cems-glofas-historical", "version_3_1", "lisflood", "intermediate", "2024-09-24"),
        # Historical v4.0 (lisflood)
        BoundaryCase("hist_v40_cons_pre", "historical", "cems-glofas-historical", "version_4_0", "lisflood", "consolidated", "1978-12-31"),
        BoundaryCase("hist_v40_cons_lb", "historical", "cems-glofas-historical", "version_4_0", "lisflood", "consolidated", "1979-01-01"),
        BoundaryCase("hist_v40_cons_interior", "historical", "cems-glofas-historical", "version_4_0", "lisflood", "consolidated", "2023-03-27"),
        BoundaryCase("hist_v40_cons_ub", "historical", "cems-glofas-historical", "version_4_0", "lisflood", "consolidated", "2025-11-30"),
        BoundaryCase("hist_v40_cons_post", "historical", "cems-glofas-historical", "version_4_0", "lisflood", "consolidated", "2025-12-01"),
        BoundaryCase("hist_v40_int_probe1", "historical", "cems-glofas-historical", "version_4_0", "lisflood", "intermediate", "2023-03-27"),
        BoundaryCase("hist_v40_int_probe2", "historical", "cems-glofas-historical", "version_4_0", "lisflood", "intermediate", "2025-01-01"),
        # Historical htessel checks (expected unsupported in prior scans)
        BoundaryCase("hist_v31_htessel_probe", "historical", "cems-glofas-historical", "version_3_1", "htessel_lisflood", "consolidated", "2021-06-15"),
        BoundaryCase("hist_v40_htessel_probe", "historical", "cems-glofas-historical", "version_4_0", "htessel_lisflood", "consolidated", "2023-03-27"),
        # Reforecast v3.1 (lisflood)
        BoundaryCase("rf_v31_ctrl_pre", "reforecast", "cems-glofas-reforecast", "version_3_1", "lisflood", "control_reforecast", "2002-01-01", "24"),
        BoundaryCase("rf_v31_ctrl_lb", "reforecast", "cems-glofas-reforecast", "version_3_1", "lisflood", "control_reforecast", "2002-01-03", "24"),
        BoundaryCase("rf_v31_ctrl_ub", "reforecast", "cems-glofas-reforecast", "version_3_1", "lisflood", "control_reforecast", "2002-07-11", "24"),
        BoundaryCase("rf_v31_ctrl_post", "reforecast", "cems-glofas-reforecast", "version_3_1", "lisflood", "control_reforecast", "2002-07-15", "24"),
        BoundaryCase("rf_v31_ens_lb", "reforecast", "cems-glofas-reforecast", "version_3_1", "lisflood", "ensemble_perturbed_reforecast", "2002-06-06", "24"),
        BoundaryCase("rf_v31_ens_ub", "reforecast", "cems-glofas-reforecast", "version_3_1", "lisflood", "ensemble_perturbed_reforecast", "2002-06-17", "24"),
        BoundaryCase("rf_v31_late_probe", "reforecast", "cems-glofas-reforecast", "version_3_1", "lisflood", "control_reforecast", "2021-01-04", "24"),
        # Reforecast v4.0 (lisflood)
        BoundaryCase("rf_v40_ctrl_pre", "reforecast", "cems-glofas-reforecast", "version_4_0", "lisflood", "control_reforecast", "2021-01-03", "24"),
        BoundaryCase("rf_v40_ctrl_anchor", "reforecast", "cems-glofas-reforecast", "version_4_0", "lisflood", "control_reforecast", "2021-01-04", "24"),
        BoundaryCase("rf_v40_ctrl_post", "reforecast", "cems-glofas-reforecast", "version_4_0", "lisflood", "control_reforecast", "2021-01-07", "24"),
        BoundaryCase("rf_v40_ctrl_late", "reforecast", "cems-glofas-reforecast", "version_4_0", "lisflood", "control_reforecast", "2022-01-03", "24"),
        BoundaryCase("rf_v40_ens_anchor", "reforecast", "cems-glofas-reforecast", "version_4_0", "lisflood", "ensemble_perturbed_reforecast", "2021-01-04", "24"),
        # Reforecast htessel checks
        BoundaryCase("rf_v31_htessel_probe", "reforecast", "cems-glofas-reforecast", "version_3_1", "htessel_lisflood", "control_reforecast", "2021-06-14", "24"),
        BoundaryCase("rf_v40_htessel_probe", "reforecast", "cems-glofas-reforecast", "version_4_0", "htessel_lisflood", "control_reforecast", "2021-01-04", "24"),
    ]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run targeted GloFAS boundary checks")
    ap.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    ap.add_argument("--lat", type=float, default=DEFAULT_LAT)
    ap.add_argument("--lon", type=float, default=DEFAULT_LON)
    ap.add_argument("--buffer-deg", type=float, default=DEFAULT_BUFFER_DEG)
    ap.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    ap.add_argument("--retry-max", type=int, default=1)
    ap.add_argument("--sleep-max", type=int, default=5)
    ap.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    ap.add_argument(
        "--case-regex",
        default="",
        help="Optional regex filter on case_id (e.g. '^hist_v21_').",
    )
    ap.add_argument("--run", action="store_true", help="Execute EWDS requests")
    return ap.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    run_id = datetime.utcnow().strftime("boundary_check_%Y%m%dT%H%M%SZ")
    run_dir = args.out_root / run_id
    downloads_dir = run_dir / "downloads"
    manifests_dir = run_dir / "manifests"
    reports_dir = run_dir / "reports"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    cases = build_default_cases()
    if args.case_regex:
        pattern = re.compile(args.case_regex)
        cases = [c for c in cases if pattern.search(c.case_id)]
    area = area_bbox(args.lat, args.lon, args.buffer_deg)

    (run_dir / "cases_resolved.json").write_text(
        json.dumps(
            [
                {
                    "case_id": c.case_id,
                    "combo_id": c.combo_id,
                    "lane": c.lane,
                    "dataset": c.dataset,
                    "system_version": c.system_version,
                    "hydrological_model": c.hydrological_model,
                    "product_type": c.product_type,
                    "probe_date": c.probe_date,
                    "leadtime_hour": c.leadtime_hour or "",
                    "request": build_request(c, area),
                }
                for c in cases
            ],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    if not args.run:
        print(f"Planned {len(cases)} cases at {run_dir}")
        return 0

    def run_case(c: BoundaryCase) -> Dict[str, object]:
        req = build_request(c, area)
        out_file = downloads_dir / f"{c.case_id}.zip"
        ok, err = retrieve_with_timeout(
            dataset=c.dataset,
            request_payload=req,
            output_file=out_file,
            timeout_seconds=args.timeout_seconds,
            retry_max=args.retry_max,
            sleep_max=args.sleep_max,
        )
        if ok and out_file.exists():
            size = int(out_file.stat().st_size)
            status = "ok"
            err_cls = ""
            err_msg = ""
        else:
            size = 0
            status = "error"
            err_cls = classify_error(err)
            err_msg = err
            if out_file.exists():
                try:
                    out_file.unlink()
                except OSError:
                    pass

        return {
            "case_id": c.case_id,
            "combo_id": c.combo_id,
            "lane": c.lane,
            "dataset": c.dataset,
            "system_version": c.system_version,
            "hydrological_model": c.hydrological_model,
            "product_type": c.product_type,
            "probe_date": c.probe_date,
            "leadtime_hour": c.leadtime_hour or "",
            "status": status,
            "bytes": size,
            "error_class": err_cls,
            "error_message": err_msg,
            "request_json": json.dumps(req, sort_keys=True),
        }

    rows: List[Dict[str, object]] = []
    max_workers = max(1, min(args.max_workers, len(cases)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_case, c): c for c in cases}
        for fut in as_completed(futures):
            row = fut.result()
            rows.append(row)
            print(
                f"[{row['status'].upper():>5}] {row['case_id']} "
                f"{row['probe_date']} {row['combo_id']} "
                f"{row['error_class']}"
            )

    rows.sort(key=lambda r: (str(r["combo_id"]), str(r["probe_date"]), str(r["case_id"])))

    manifest_path = manifests_dir / "boundary_checks.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    by_combo: Dict[str, Dict[str, object]] = {}
    for row in rows:
        combo = str(row["combo_id"])
        rec = by_combo.setdefault(
            combo,
            {
                "combo_id": combo,
                "lane": row["lane"],
                "dataset": row["dataset"],
                "system_version": row["system_version"],
                "hydrological_model": row["hydrological_model"],
                "product_type": row["product_type"],
                "tested_dates": [],
                "ok_dates": [],
                "error_dates": [],
                "error_classes": {},
            },
        )
        date_str = str(row["probe_date"])
        rec["tested_dates"].append(date_str)
        if row["status"] == "ok":
            rec["ok_dates"].append(date_str)
        else:
            rec["error_dates"].append(date_str)
            err_cls = str(row["error_class"])
            rec["error_classes"][err_cls] = int(rec["error_classes"].get(err_cls, 0)) + 1

    summary_rows: List[Dict[str, object]] = []
    for combo, rec in sorted(by_combo.items()):
        ok_dates = sorted(rec["ok_dates"])
        tested_dates = sorted(rec["tested_dates"])
        summary_rows.append(
            {
                "combo_id": combo,
                "lane": rec["lane"],
                "dataset": rec["dataset"],
                "system_version": rec["system_version"],
                "hydrological_model": rec["hydrological_model"],
                "product_type": rec["product_type"],
                "tested_count": len(tested_dates),
                "ok_count": len(ok_dates),
                "first_ok_date": ok_dates[0] if ok_dates else "",
                "last_ok_date": ok_dates[-1] if ok_dates else "",
                "ok_dates_csv": ",".join(ok_dates),
                "error_classes_json": json.dumps(rec["error_classes"], sort_keys=True),
            }
        )

    summary_csv = reports_dir / "combo_summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()) if summary_rows else [])
        if summary_rows:
            writer.writeheader()
            writer.writerows(summary_rows)

    (reports_dir / "combo_summary.json").write_text(
        json.dumps(summary_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"Wrote: {manifest_path}")
    print(f"Wrote: {summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
