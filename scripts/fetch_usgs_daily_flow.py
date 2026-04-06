#!/usr/bin/env python3
"""Fetch USGS NWIS daily flow and write a canonical CSV + metadata JSON.

This is a small, restartable materializer for family 5 in the recovery workflow.
It keeps the fetch explicit instead of relying on implicit runtime pulls inside R.
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


CFS_TO_CMS = 0.0283168466
DEFAULT_SITE_ID = "11160500"
DEFAULT_PARAMETER_CD = "00060"
DEFAULT_STAT_CD = "00003"
DEFAULT_START_DATE = "1979-01-01"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch USGS NWIS daily flow.")
    parser.add_argument("--site-id", default=DEFAULT_SITE_ID)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE, help="Inclusive YYYY-MM-DD.")
    parser.add_argument(
        "--end-date",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="Inclusive YYYY-MM-DD.",
    )
    parser.add_argument("--parameter-cd", default=DEFAULT_PARAMETER_CD)
    parser.add_argument("--stat-cd", default=DEFAULT_STAT_CD)
    parser.add_argument("--out-csv", required=True, type=Path)
    parser.add_argument("--out-meta", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def build_url(site_id: str, start_date: str, end_date: str, parameter_cd: str, stat_cd: str) -> str:
    params = {
        "format": "json",
        "sites": site_id,
        "parameterCd": parameter_cd,
        "statCd": stat_cd,
        "startDT": start_date,
        "endDT": end_date,
        "siteStatus": "all",
    }
    return "https://waterservices.usgs.gov/nwis/dv/?" + urllib.parse.urlencode(params)


def fetch_payload(url: str, timeout_seconds: int) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
        return json.load(response)


def parse_rows(payload: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    time_series = ((payload.get("value") or {}).get("timeSeries") or [])
    if not time_series:
        raise RuntimeError("USGS NWIS returned no timeSeries entries.")

    series = time_series[0]
    source_info = series.get("sourceInfo") or {}
    geo = (((source_info.get("geoLocation") or {}).get("geogLocation") or {}))
    site_codes = source_info.get("siteCode") or []
    variable = series.get("variable") or {}

    values = (((series.get("values") or [{}])[0]).get("value") or [])
    rows: List[Dict[str, Any]] = []
    for item in values:
        date_raw = str(item.get("dateTime", ""))
        value_raw = str(item.get("value", ""))
        qualifiers = ",".join(item.get("qualifiers") or [])
        try:
            day = datetime.fromisoformat(date_raw.replace("Z", "+00:00")).date().isoformat()
            discharge_cfs = float(value_raw)
        except Exception:
            continue
        rows.append(
            {
                "date": day,
                "discharge_cfs": discharge_cfs,
                "discharge_cms": discharge_cfs * CFS_TO_CMS,
                "qualifiers": qualifiers,
            }
        )

    if not rows:
        raise RuntimeError("USGS NWIS parsing produced no valid daily rows.")

    df = pd.DataFrame(rows)
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

    meta = {
        "site_name": str(source_info.get("siteName", "")),
        "site_code": str(site_codes[0].get("value", "")) if site_codes else "",
        "latitude": float(geo.get("latitude")) if geo.get("latitude") is not None else None,
        "longitude": float(geo.get("longitude")) if geo.get("longitude") is not None else None,
        "variable_name": str(variable.get("variableName", "")),
        "variable_code": str(((variable.get("variableCode") or [{}])[0]).get("value", "")),
        "unit_code": str(((variable.get("unit") or {}).get("unitCode", ""))),
    }
    return df, meta


def main() -> int:
    args = parse_args()
    out_csv = args.out_csv.resolve()
    out_meta = args.out_meta.resolve()

    if not args.overwrite:
        if out_csv.exists():
            raise SystemExit(f"Output exists: {out_csv}. Use --overwrite to replace it.")
        if out_meta.exists():
            raise SystemExit(f"Output exists: {out_meta}. Use --overwrite to replace it.")

    url = build_url(
        site_id=str(args.site_id),
        start_date=str(args.start_date),
        end_date=str(args.end_date),
        parameter_cd=str(args.parameter_cd),
        stat_cd=str(args.stat_cd),
    )

    if args.dry_run:
        print(f"[DRY-RUN] request_url={url}")
        print(f"[DRY-RUN] out_csv={out_csv}")
        print(f"[DRY-RUN] out_meta={out_meta}")
        return 0

    payload = fetch_payload(url, timeout_seconds=int(args.timeout_seconds))
    df, series_meta = parse_rows(payload)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    meta = {
        "fetched_utc": datetime.now(timezone.utc).isoformat(),
        "request_url": url,
        "request": {
            "site_id": str(args.site_id),
            "start_date": str(args.start_date),
            "end_date": str(args.end_date),
            "parameter_cd": str(args.parameter_cd),
            "stat_cd": str(args.stat_cd),
        },
        "units": {
            "input": "cfs",
            "output": "cms",
            "cms_conversion_factor": CFS_TO_CMS,
        },
        "row_count": int(len(df)),
        "date_min": str(df["date"].iloc[0]),
        "date_max": str(df["date"].iloc[-1]),
        "series": series_meta,
    }
    out_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"[OK] wrote {out_csv} rows={len(df)}")
    print(f"[OK] wrote {out_meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
