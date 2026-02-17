#!/usr/bin/env python3
"""
Downloader/planner for GloFAS historical consolidated point-area campaigns.

Scope is fixed to three historical tuples:
1) version_2_1 + htessel_lisflood + consolidated
2) version_3_1 + lisflood + consolidated
3) version_4_0 + lisflood + consolidated

Default focus window is clipped to project analysis bounds:
1987-05-29 .. 2023-05-01 (inclusive).

The script supports:
- planning monthly shards (CSV + JSON)
- dry-run manifest generation
- actual EWDS retrieval execution
"""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import cdsapi  # type: ignore
except Exception:
    cdsapi = None  # type: ignore


DATASET = "cems-glofas-historical"
VARIABLE = "river_discharge_in_the_last_24_hours"
DEFAULT_LAT = 37.0443931
DEFAULT_LON = -122.072464
DEFAULT_BUFFER_DEG = 0.33
DEFAULT_FOCUS_START = date(1987, 5, 29)
DEFAULT_FOCUS_END = date(2023, 5, 1)


@dataclass(frozen=True)
class ProductSpec:
    product_id: str
    system_version: str
    hydrological_model: str
    product_type: str
    coverage_start: date
    coverage_end: date


@dataclass(frozen=True)
class MonthShard:
    product_id: str
    shard_id: str
    start: date
    end: date


def parse_ymd(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def format_ymd(d: date) -> str:
    return d.isoformat()


def area_bbox(lat: float, lon: float, buffer_deg: float) -> List[float]:
    # Symmetric bbox for point-focused historical extraction.
    return [lat + buffer_deg, lon - buffer_deg, lat - buffer_deg, lon + buffer_deg]


def short_hash(payload: Dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:10]


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def month_end(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def iter_month_starts(start: date, end: date) -> Iterable[date]:
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield date(y, m, 1)
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1


def build_specs() -> List[ProductSpec]:
    return [
        ProductSpec(
            product_id="hist_v21_htessel_cons",
            system_version="version_2_1",
            hydrological_model="htessel_lisflood",
            product_type="consolidated",
            coverage_start=date(1979, 1, 1),
            coverage_end=date(2022, 7, 31),
        ),
        ProductSpec(
            product_id="hist_v31_lisflood_cons",
            system_version="version_3_1",
            hydrological_model="lisflood",
            product_type="consolidated",
            coverage_start=date(1979, 1, 1),
            coverage_end=date(2024, 6, 30),
        ),
        ProductSpec(
            product_id="hist_v40_lisflood_cons",
            system_version="version_4_0",
            hydrological_model="lisflood",
            product_type="consolidated",
            coverage_start=date(1979, 1, 1),
            coverage_end=date(2025, 11, 30),
        ),
    ]


def clip_window(spec: ProductSpec, focus_start: date, focus_end: date) -> Optional[Tuple[date, date]]:
    s = max(spec.coverage_start, focus_start)
    e = min(spec.coverage_end, focus_end)
    if s > e:
        return None
    return s, e


def make_month_shards(spec: ProductSpec, focus_start: date, focus_end: date) -> List[MonthShard]:
    clipped = clip_window(spec, focus_start, focus_end)
    if clipped is None:
        return []

    s, e = clipped
    shards: List[MonthShard] = []
    for ms in iter_month_starts(s, e):
        me = month_end(ms)
        ss = max(s, ms)
        ee = min(e, me)
        shard_id = f"{ss.year:04d}-{ss.month:02d}"
        shards.append(MonthShard(product_id=spec.product_id, shard_id=shard_id, start=ss, end=ee))
    return shards


def build_request(spec: ProductSpec, shard: MonthShard, area: List[float]) -> Dict[str, object]:
    days = [f"{d:02d}" for d in range(shard.start.day, shard.end.day + 1)]
    return {
        "system_version": [spec.system_version],
        "hydrological_model": [spec.hydrological_model],
        "product_type": [spec.product_type],
        "variable": [VARIABLE],
        "hyear": [f"{shard.start.year:04d}"],
        "hmonth": [f"{shard.start.month:02d}"],
        "hday": days,
        "data_format": "grib2",
        "download_format": "zip",
        "area": area,
    }


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def is_nonempty(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    ensure_dir(path.parent)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def append_manifest(path: Path, row: Dict[str, object]) -> None:
    ensure_dir(path.parent)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            w.writeheader()
        w.writerow(row)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Plan/download GloFAS historical consolidated monthly shards")
    ap.add_argument("--out-root", type=Path, default=Path("data") / "glofas_historical_consolidated_point")
    ap.add_argument("--plan-root", type=Path, default=Path("repro") / "glofas_probe_runs")
    ap.add_argument("--focus-start", default=format_ymd(DEFAULT_FOCUS_START))
    ap.add_argument("--focus-end", default=format_ymd(DEFAULT_FOCUS_END))
    ap.add_argument("--lat", type=float, default=DEFAULT_LAT)
    ap.add_argument("--lon", type=float, default=DEFAULT_LON)
    ap.add_argument("--buffer-deg", type=float, default=DEFAULT_BUFFER_DEG)
    ap.add_argument("--product-id", action="append", default=[])
    ap.add_argument("--shards-csv", type=Path, default=None, help="Optional CSV subset with columns product_id,start,end")
    ap.add_argument("--retry-max", type=int, default=2)
    ap.add_argument("--sleep-max", type=int, default=20)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--max-shards", type=int, default=0, help="Limit shards processed (0 = all)")
    return ap.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    focus_start = parse_ymd(args.focus_start)
    focus_end = parse_ymd(args.focus_end)
    if focus_start > focus_end:
        raise ValueError("focus-start must be <= focus-end")

    run_id = datetime.utcnow().strftime("hist_campaign_%Y%m%dT%H%M%SZ")
    plan_dir = args.plan_root / run_id
    ensure_dir(plan_dir)

    specs = build_specs()
    if args.product_id:
        chosen = set(args.product_id)
        specs = [s for s in specs if s.product_id in chosen]
        missing = chosen.difference({s.product_id for s in specs})
        if missing:
            raise ValueError(f"Unknown --product-id: {sorted(missing)}")

    area = area_bbox(args.lat, args.lon, args.buffer_deg)

    spec_rows: List[Dict[str, object]] = []
    shard_rows: List[Dict[str, object]] = []
    product_to_shards: Dict[str, List[MonthShard]] = {}

    for spec in specs:
        clipped = clip_window(spec, focus_start, focus_end)
        eff_start = clipped[0] if clipped else None
        eff_end = clipped[1] if clipped else None
        spec_rows.append(
            {
                "product_id": spec.product_id,
                "system_version": spec.system_version,
                "hydrological_model": spec.hydrological_model,
                "product_type": spec.product_type,
                "coverage_start": format_ymd(spec.coverage_start),
                "coverage_end": format_ymd(spec.coverage_end),
                "focus_start": format_ymd(focus_start),
                "focus_end": format_ymd(focus_end),
                "effective_start": format_ymd(eff_start) if eff_start else "",
                "effective_end": format_ymd(eff_end) if eff_end else "",
            }
        )

        shards = make_month_shards(spec, focus_start, focus_end)
        product_to_shards[spec.product_id] = shards
        for sh in shards:
            shard_rows.append(
                {
                    "product_id": sh.product_id,
                    "shard_id": sh.shard_id,
                    "start": format_ymd(sh.start),
                    "end": format_ymd(sh.end),
                    "system_version": spec.system_version,
                    "hydrological_model": spec.hydrological_model,
                    "product_type": spec.product_type,
                }
            )

    write_csv(plan_dir / "products.csv", spec_rows)
    write_csv(plan_dir / "shards_all.csv", shard_rows)

    for pid, shards in product_to_shards.items():
        rows = [
            {
                "product_id": s.product_id,
                "shard_id": s.shard_id,
                "start": format_ymd(s.start),
                "end": format_ymd(s.end),
            }
            for s in shards
        ]
        write_csv(plan_dir / f"shards_{pid}.csv", rows)

    (plan_dir / "campaign_metadata.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "dataset": DATASET,
                "variable": VARIABLE,
                "focus_start": format_ymd(focus_start),
                "focus_end": format_ymd(focus_end),
                "lat": args.lat,
                "lon": args.lon,
                "buffer_deg": args.buffer_deg,
                "area": area,
                "retry_max": args.retry_max,
                "sleep_max": args.sleep_max,
                "products": [s.__dict__ for s in specs],
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )

    # If only planning requested, stop here.
    if not args.run:
        print(f"[PLAN] created {plan_dir}")
        print(f"[PLAN] products={len(spec_rows)} shards={len(shard_rows)}")
        return 0

    if cdsapi is None:
        raise RuntimeError("cdsapi import failed; install cdsapi in active environment")

    client = cdsapi.Client(retry_max=args.retry_max, sleep_max=args.sleep_max)

    selected_rows: List[Dict[str, str]] = []
    if args.shards_csv is not None:
        with args.shards_csv.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                selected_rows.append({k: str(v) for k, v in row.items()})
    else:
        for r in shard_rows:
            selected_rows.append({k: str(v) for k, v in r.items()})

    if args.max_shards > 0:
        selected_rows = selected_rows[: args.max_shards]

    spec_by_pid = {s.product_id: s for s in specs}

    manifest_path = plan_dir / "download_manifest.csv"
    for row in selected_rows:
        pid = row["product_id"]
        spec = spec_by_pid[pid]
        shard = MonthShard(
            product_id=pid,
            shard_id=row.get("shard_id") or f"{row['start'][:7]}",
            start=parse_ymd(row["start"]),
            end=parse_ymd(row["end"]),
        )

        req = build_request(spec, shard, area)
        req_id = f"{pid}_{shard.shard_id}_{short_hash(req)}"
        y = f"{shard.start.year:04d}"
        m = f"{shard.start.month:02d}"
        out_dir = args.out_root / pid / f"year={y}" / f"month={m}"
        ensure_dir(out_dir)
        out_zip = out_dir / f"{req_id}.zip"
        out_req = out_dir / f"{req_id}.request.json"

        status = "planned"
        note = ""

        if is_nonempty(out_zip) and not args.overwrite:
            status = "skipped_exists"
            note = "file exists"
        else:
            try:
                out_req.write_text(json.dumps(req, indent=2, sort_keys=True), encoding="utf-8")
                client.retrieve(DATASET, req).download(str(out_zip))
                if is_nonempty(out_zip):
                    status = "downloaded"
                    note = "ok"
                else:
                    status = "error_empty"
                    note = "download produced empty file"
            except Exception as exc:  # noqa: BLE001
                status = "error_exception"
                note = str(exc)[:5000]

        append_manifest(
            manifest_path,
            {
                "product_id": pid,
                "shard_id": shard.shard_id,
                "start": format_ymd(shard.start),
                "end": format_ymd(shard.end),
                "system_version": spec.system_version,
                "hydrological_model": spec.hydrological_model,
                "product_type": spec.product_type,
                "status": status,
                "path": str(out_zip),
                "request_id": req_id,
                "notes": note,
                "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
            },
        )

        print(f"[{status.upper():>13}] {pid} {shard.shard_id} {format_ymd(shard.start)}..{format_ymd(shard.end)}")

    print(f"[DONE] run dir: {plan_dir}")
    print(f"[DONE] manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(tuple(__import__("sys").argv[1:])))
