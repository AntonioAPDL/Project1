#!/usr/bin/env python3
"""Validate GLOFAS operational forecast smoke/full outputs for site 11160500."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate GLOFAS operational forecast download + extraction outputs.")
    parser.add_argument("--download-root", type=Path, required=True)
    parser.add_argument("--extract-root", type=Path, required=True)
    parser.add_argument("--dates-file", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--post-days", type=int, default=28)
    parser.add_argument("--expected-system-version", default="operational")
    parser.add_argument("--extract-rerun-log", type=Path, default=None)
    return parser.parse_args()


def read_dates(path: Path) -> List[date]:
    dates: List[date] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        dates.append(datetime.strptime(value, "%Y-%m-%d").date())
    return sorted(dates)


def choose_hydrological_model(issue_date: date) -> str:
    return "htessel_lisflood" if issue_date < date(2021, 5, 26) else "lisflood"


def expected_member_columns() -> List[str]:
    return [f"member_{idx:02d}" for idx in range(0, 51)]


def extract_skip_count(log_path: Path | None) -> int | None:
    if log_path is None or (not log_path.exists()):
        return None
    text = log_path.read_text(encoding="utf-8")
    match = re.search(r"\[DONE\]\s+ok=(\d+)\s+skipped=(\d+)", text)
    if match is None:
        return None
    return int(match.group(2))


def main() -> int:
    args = parse_args()
    dates = read_dates(args.dates_file)
    manifest_path = args.download_root / "manifests" / "download_manifest.csv"
    if not manifest_path.exists():
        raise SystemExit(f"Missing manifest: {manifest_path}")

    manifest = pd.read_csv(manifest_path)
    cell_path = args.extract_root / "cell.json"
    cell_payload = json.loads(cell_path.read_text(encoding="utf-8")) if cell_path.exists() else None
    extract_rerun_skip_count = extract_skip_count(args.extract_rerun_log)

    per_issue: List[Dict[str, object]] = []
    overall_ok = True
    member_cols_expected = expected_member_columns()

    for issue_date in dates:
        issue_str = issue_date.isoformat()
        issue_rows = manifest.loc[manifest["issue_date"] == issue_str].copy()
        statuses = issue_rows["status"].tolist() if not issue_rows.empty else []
        latest_status = statuses[-1] if statuses else None
        history_counts = issue_rows["status"].value_counts().to_dict() if not issue_rows.empty else {}

        issue_dir = args.download_root / "grib" / f"issue_date={issue_str}"
        grib_files = sorted(issue_dir.glob("*.grib"))
        request_files = sorted(issue_dir.glob("*.request.json"))
        request_payload = json.loads(request_files[0].read_text(encoding="utf-8")) if request_files else None

        extract_csv = args.extract_root / f"issue_date={issue_str}" / "glofas_members.csv"
        extract_ok = extract_csv.exists()
        row_count = 0
        target_date_min = None
        target_date_max = None
        member_col_count = 0
        missing_member_cols: List[str] = []
        if extract_ok:
            df = pd.read_csv(extract_csv)
            row_count = len(df)
            target_date_min = df["target_date"].min() if "target_date" in df.columns else None
            target_date_max = df["target_date"].max() if "target_date" in df.columns else None
            member_cols = [col for col in df.columns if col.startswith("member_")]
            member_col_count = len(member_cols)
            missing_member_cols = [col for col in member_cols_expected if col not in member_cols]
        expected_start = (issue_date + timedelta(days=1)).isoformat()
        expected_end = (issue_date + timedelta(days=int(args.post_days))).isoformat()
        expected_model = choose_hydrological_model(issue_date)

        checks = {
            "has_manifest_rows": not issue_rows.empty,
            "has_downloaded_once": int(history_counts.get("downloaded", 0)) >= 1,
            "has_skipped_exists_rerun": int(history_counts.get("skipped_exists", 0)) >= 1,
            "grib_file_count_is_one": len(grib_files) == 1,
            "request_file_count_is_one": len(request_files) == 1,
            "request_system_version_matches": request_payload is not None and request_payload.get("system_version") == args.expected_system_version,
            "request_model_matches": request_payload is not None and request_payload.get("hydrological_model") == expected_model,
            "extract_csv_exists": extract_ok,
            "extract_row_count_matches": row_count == int(args.post_days),
            "extract_target_date_start_matches": target_date_min == expected_start,
            "extract_target_date_end_matches": target_date_max == expected_end,
            "extract_member_cols_complete": member_col_count == len(member_cols_expected) and not missing_member_cols,
        }
        issue_ok = all(checks.values())
        overall_ok = overall_ok and issue_ok
        per_issue.append(
            {
                "issue_date": issue_str,
                "latest_status": latest_status,
                "status_history_counts": history_counts,
                "grib_file_count": len(grib_files),
                "request_file_count": len(request_files),
                "extract_csv": str(extract_csv),
                "extract_row_count": row_count,
                "extract_target_date_min": target_date_min,
                "extract_target_date_max": target_date_max,
                "extract_member_col_count": member_col_count,
                "missing_member_cols": missing_member_cols,
                "expected_model": expected_model,
                "checks": checks,
                "ok": issue_ok,
            }
        )

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "download_root": str(args.download_root),
        "extract_root": str(args.extract_root),
        "dates_file": str(args.dates_file),
        "expected_system_version": args.expected_system_version,
        "cell_json": cell_payload,
        "extract_rerun_log": str(args.extract_rerun_log) if args.extract_rerun_log is not None else None,
        "extract_rerun_skip_count": extract_rerun_skip_count,
        "extract_rerun_skipped_all_issue_dates": extract_rerun_skip_count == len(per_issue) if extract_rerun_skip_count is not None else None,
        "issue_count": len(per_issue),
        "ok": overall_ok,
        "issues": per_issue,
    }
    if summary["extract_rerun_skipped_all_issue_dates"] is False:
        overall_ok = False
        summary["ok"] = False
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "issue_count": len(per_issue), "out_json": str(args.out_json)}, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
