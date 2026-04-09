#!/usr/bin/env python3
"""Validate full parallel GLOFAS operational download + extraction outputs."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a parallel GLOFAS operational campaign after extraction.")
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--post-days", type=int, default=28)
    return parser.parse_args()


def read_dates(path: Path) -> List[date]:
    return [
        datetime.strptime(line.strip(), "%Y-%m-%d").date()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def expected_member_columns() -> List[str]:
    return [f"member_{idx:02d}" for idx in range(0, 51)]


def main() -> int:
    args = parse_args()
    campaign_root = args.campaign_root.resolve()
    dates_file = campaign_root / "plans" / "all_issue_dates.txt"
    download_root = campaign_root / "outputs" / "download_root"
    extract_root = campaign_root / "outputs" / "forecast_cache" / "glofas"
    issue_dates = read_dates(dates_file)
    expected_members = expected_member_columns()

    per_issue: List[Dict[str, object]] = []
    overall_ok = True
    for issue_date in issue_dates:
        issue_str = issue_date.isoformat()
        grib_dir = download_root / "grib" / f"issue_date={issue_str}"
        grib_count = len([path for path in grib_dir.glob("*.grib") if path.exists() and path.stat().st_size > 0])
        extract_csv = extract_root / f"issue_date={issue_str}" / "glofas_members.csv"
        row_count = 0
        target_min = None
        target_max = None
        missing_member_cols: List[str] = []
        if extract_csv.exists():
            df = pd.read_csv(extract_csv)
            row_count = len(df)
            target_min = df["target_date"].min() if "target_date" in df.columns else None
            target_max = df["target_date"].max() if "target_date" in df.columns else None
            missing_member_cols = [name for name in expected_members if name not in df.columns]

        checks = {
            "grib_present": grib_count == 1,
            "extract_present": extract_csv.exists(),
            "extract_row_count_matches": row_count == int(args.post_days),
            "member_columns_complete": not missing_member_cols,
            "target_start_matches": target_min == (issue_date + timedelta(days=1)).isoformat(),
            "target_end_matches": target_max == (issue_date + timedelta(days=int(args.post_days))).isoformat(),
        }
        issue_ok = all(checks.values())
        overall_ok = overall_ok and issue_ok
        per_issue.append(
            {
                "issue_date": issue_str,
                "grib_count": grib_count,
                "extract_csv": str(extract_csv),
                "extract_exists": extract_csv.exists(),
                "row_count": row_count,
                "target_date_min": target_min,
                "target_date_max": target_max,
                "missing_member_cols": missing_member_cols,
                "checks": checks,
                "ok": issue_ok,
            }
        )

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "campaign_root": str(campaign_root),
        "issue_count": len(issue_dates),
        "ok": overall_ok,
        "issues": per_issue,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "issue_count": len(issue_dates), "out_json": str(args.out_json)}, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
