#!/usr/bin/env python3
"""
Lightweight parity probe: compare GloFAS forecast payloads from
`system_version=operational` versus explicit system versions for selected dates.

Design goals:
- small requests (point-area bbox, short leadtime list)
- reproducible artifacts (request json + downloaded grib + summary report)
- direct numeric parity diagnostics at nearest grid cell
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import xarray as xr

try:
    import cdsapi  # type: ignore
except Exception:
    cdsapi = None  # type: ignore


DATASET = "cems-glofas-forecast"
VARIABLE = "river_discharge_in_the_last_24_hours"
PRODUCT_TYPE = ["control_forecast", "ensemble_perturbed_forecasts"]


@dataclass(frozen=True)
class ParityCase:
    label: str
    issue_date: date
    explicit_version: str
    hydrological_model: str


def parse_ymd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def to_0_360(lon: float) -> float:
    lon = lon % 360.0
    return 0.0 if abs(lon - 360.0) < 1e-12 else lon


def area_bbox(lat: float, lon: float, buffer_deg: float) -> List[float]:
    # Match downloader geometry: +/-2*buffer in lat, +/-buffer in lon.
    return [lat + 2.0 * buffer_deg, lon - buffer_deg, lat - 2.0 * buffer_deg, lon + buffer_deg]


def short_hash(payload: Dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:10]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def haversine_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    r = 6371.0
    lat1r = np.deg2rad(lat1)
    lon1r = np.deg2rad(lon1)
    lat2r = np.deg2rad(lat2)
    lon2r = np.deg2rad(lon2)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2.0) ** 2
    return 2.0 * r * np.arcsin(np.sqrt(a))


def pick_var(ds: xr.Dataset) -> str:
    if "dis24" in ds.data_vars:
        return "dis24"
    return list(ds.data_vars)[0]


def open_by_dtype(path: Path, dtype: str) -> xr.Dataset:
    return xr.open_dataset(
        path,
        engine="cfgrib",
        backend_kwargs={"indexpath": "", "filter_by_keys": {"dataType": dtype}},
    )


def nearest_cell_index(ds: xr.Dataset, lat: float, lon: float, var: str) -> Tuple[int, int, float]:
    da = ds[var]
    lats = da["latitude"].values
    lons = da["longitude"].values
    lat2d = np.repeat(lats[:, None], lons.size, axis=1)
    lon2d = np.repeat(lons[None, :], lats.size, axis=0)
    dist = haversine_km(lat, to_0_360(lon), lat2d, lon2d)

    # Prefer finite-value cells.
    finite_any = np.isfinite(da.values).any(axis=0)
    if finite_any.any():
        dist = np.where(finite_any, dist, np.inf)

    lat_i, lon_i = np.unravel_index(int(np.argmin(dist)), dist.shape)
    return int(lat_i), int(lon_i), float(dist[lat_i, lon_i])


def compare_arrays(a: np.ndarray, b: np.ndarray) -> Dict[str, float]:
    if a.shape != b.shape:
        return {
            "shape_equal": 0.0,
            "n_total": float(max(a.size, b.size)),
            "n_exact": 0.0,
            "max_abs_diff": math.inf,
            "mean_abs_diff": math.inf,
        }

    diff = np.abs(a.astype("float64") - b.astype("float64"))
    n_total = diff.size
    n_exact = int(np.sum(diff == 0.0))
    max_abs = float(np.nanmax(diff)) if n_total > 0 else 0.0
    mean_abs = float(np.nanmean(diff)) if n_total > 0 else 0.0
    return {
        "shape_equal": 1.0,
        "n_total": float(n_total),
        "n_exact": float(n_exact),
        "max_abs_diff": max_abs,
        "mean_abs_diff": mean_abs,
    }


def build_request(
    issue_date: date,
    system_version: str,
    hydrological_model: str,
    lat: float,
    lon: float,
    buffer_deg: float,
    leadtimes: Sequence[str],
) -> Dict:
    return {
        "system_version": system_version,
        "hydrological_model": hydrological_model,
        "product_type": PRODUCT_TYPE,
        "variable": VARIABLE,
        "year": f"{issue_date.year:04d}",
        "month": f"{issue_date.month:02d}",
        "day": f"{issue_date.day:02d}",
        "leadtime_hour": list(leadtimes),
        "format": "grib",
        "area": area_bbox(lat, lon, buffer_deg),
    }


def parse_case(text: str) -> ParityCase:
    # label:YYYY-MM-DD:explicit_version:hydrological_model
    parts = text.split(":")
    if len(parts) != 4:
        raise ValueError(
            f"Bad --case format {text!r}. Expected label:YYYY-MM-DD:version_x_y:hydrological_model"
        )
    return ParityCase(
        label=parts[0],
        issue_date=parse_ymd(parts[1]),
        explicit_version=parts[2],
        hydrological_model=parts[3],
    )


def default_cases() -> List[ParityCase]:
    return [
        ParityCase(
            label="v2_1_era",
            issue_date=parse_ymd("2020-01-15"),
            explicit_version="version_2_1",
            hydrological_model="htessel_lisflood",
        ),
        ParityCase(
            label="v3_1_era",
            issue_date=parse_ymd("2021-06-15"),
            explicit_version="version_3_1",
            hydrological_model="lisflood",
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=37.0443931)
    ap.add_argument("--lon", type=float, default=-122.072464)
    ap.add_argument("--buffer-deg", type=float, default=0.33)
    ap.add_argument("--leadtimes", nargs="+", default=["24", "48", "72"])
    ap.add_argument("--out-root", type=Path, default=Path("repro/glofas_probe_runs"))
    ap.add_argument(
        "--case",
        action="append",
        default=[],
        help="label:YYYY-MM-DD:explicit_version:hydrological_model (repeatable)",
    )
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if cdsapi is None and not args.dry_run:
        raise RuntimeError("cdsapi import failed. Install cdsapi in the active environment.")

    cases = [parse_case(c) for c in args.case] if args.case else default_cases()
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.out_root / f"operational_explicit_parity_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: List[Dict[str, object]] = []

    client = cdsapi.Client() if (not args.dry_run) else None

    for case in cases:
        case_dir = run_dir / case.label
        case_dir.mkdir(parents=True, exist_ok=True)

        req_oper = build_request(
            issue_date=case.issue_date,
            system_version="operational",
            hydrological_model=case.hydrological_model,
            lat=args.lat,
            lon=args.lon,
            buffer_deg=args.buffer_deg,
            leadtimes=args.leadtimes,
        )
        req_exp = build_request(
            issue_date=case.issue_date,
            system_version=case.explicit_version,
            hydrological_model=case.hydrological_model,
            lat=args.lat,
            lon=args.lon,
            buffer_deg=args.buffer_deg,
            leadtimes=args.leadtimes,
        )

        req_oper_id = f"operational_{case.issue_date.isoformat()}_{short_hash(req_oper)}"
        req_exp_id = f"{case.explicit_version}_{case.issue_date.isoformat()}_{short_hash(req_exp)}"

        oper_json = case_dir / f"{req_oper_id}.request.json"
        exp_json = case_dir / f"{req_exp_id}.request.json"
        oper_grib = case_dir / f"{req_oper_id}.grib"
        exp_grib = case_dir / f"{req_exp_id}.grib"

        oper_json.write_text(json.dumps(req_oper, indent=2, sort_keys=True))
        exp_json.write_text(json.dumps(req_exp, indent=2, sort_keys=True))

        status = "planned"
        note = ""

        try:
            if args.dry_run:
                status = "dry_run"
                note = "no requests executed"
            else:
                if args.overwrite or (not oper_grib.exists()) or oper_grib.stat().st_size == 0:
                    client.retrieve(DATASET, req_oper, str(oper_grib))
                if args.overwrite or (not exp_grib.exists()) or exp_grib.stat().st_size == 0:
                    client.retrieve(DATASET, req_exp, str(exp_grib))

                ds_oper_cf = open_by_dtype(oper_grib, "cf")
                ds_exp_cf = open_by_dtype(exp_grib, "cf")
                ds_oper_pf = open_by_dtype(oper_grib, "pf")
                ds_exp_pf = open_by_dtype(exp_grib, "pf")

                var_cf_oper = pick_var(ds_oper_cf)
                var_cf_exp = pick_var(ds_exp_cf)
                var_pf_oper = pick_var(ds_oper_pf)
                var_pf_exp = pick_var(ds_exp_pf)

                lat_i, lon_i, dist_km = nearest_cell_index(ds_oper_cf, args.lat, args.lon, var_cf_oper)

                cf_oper = ds_oper_cf[var_cf_oper].isel(latitude=lat_i, longitude=lon_i).values
                cf_exp = ds_exp_cf[var_cf_exp].isel(latitude=lat_i, longitude=lon_i).values

                pf_oper = ds_oper_pf[var_pf_oper].isel(latitude=lat_i, longitude=lon_i).values
                pf_exp = ds_exp_pf[var_pf_exp].isel(latitude=lat_i, longitude=lon_i).values

                cf_metrics = compare_arrays(np.asarray(cf_oper), np.asarray(cf_exp))
                pf_metrics = compare_arrays(np.asarray(pf_oper), np.asarray(pf_exp))

                same_bytes = file_sha256(oper_grib) == file_sha256(exp_grib)
                exact_all = (
                    cf_metrics["shape_equal"] == 1.0
                    and pf_metrics["shape_equal"] == 1.0
                    and cf_metrics["max_abs_diff"] == 0.0
                    and pf_metrics["max_abs_diff"] == 0.0
                )

                summary = {
                    "label": case.label,
                    "issue_date": case.issue_date.isoformat(),
                    "explicit_version": case.explicit_version,
                    "hydrological_model": case.hydrological_model,
                    "lat": args.lat,
                    "lon": args.lon,
                    "buffer_deg": args.buffer_deg,
                    "leadtimes": list(args.leadtimes),
                    "cell": {
                        "lat_index": lat_i,
                        "lon_index": lon_i,
                        "dist_km": dist_km,
                        "cell_lat": float(ds_oper_cf["latitude"].values[lat_i]),
                        "cell_lon_0_360": float(ds_oper_cf["longitude"].values[lon_i]),
                    },
                    "operational_file": str(oper_grib),
                    "explicit_file": str(exp_grib),
                    "sha256_operational": file_sha256(oper_grib),
                    "sha256_explicit": file_sha256(exp_grib),
                    "same_file_sha256": same_bytes,
                    "cf_metrics": cf_metrics,
                    "pf_metrics": pf_metrics,
                    "exact_all": exact_all,
                }
                (case_dir / "parity_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))

                status = "exact_match" if exact_all else "mismatch"
                note = (
                    f"same_bytes={same_bytes}; "
                    f"cf_max_abs={cf_metrics['max_abs_diff']}; "
                    f"pf_max_abs={pf_metrics['max_abs_diff']}"
                )

        except Exception as e:  # noqa: BLE001
            status = "error_exception"
            note = repr(e)[:2000]

        manifest_rows.append(
            {
                "label": case.label,
                "issue_date": case.issue_date.isoformat(),
                "explicit_version": case.explicit_version,
                "hydrological_model": case.hydrological_model,
                "status": status,
                "notes": note,
                "run_dir": str(case_dir),
                "timestamp_utc": datetime.utcnow().isoformat(timespec="seconds"),
            }
        )

    manifest_path = run_dir / "parity_manifest.csv"
    with manifest_path.open("w", newline="") as f:
        if manifest_rows:
            writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
            writer.writeheader()
            writer.writerows(manifest_rows)

    print(f"[DONE] parity run_dir={run_dir}")
    for row in manifest_rows:
        print(f"  - {row['label']}: {row['status']} | {row['notes']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
