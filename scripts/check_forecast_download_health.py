#!/usr/bin/env python3
"""Validate a bounded `forecast_download.py` smoke run and downstream NWS extraction."""

from __future__ import annotations

import argparse
import csv
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate forecast_download.py smoke outputs.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--results-pkl", type=Path, required=True)
    parser.add_argument("--extract-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--expected-site-code", required=True)
    parser.add_argument("--expected-lat", type=float, required=True)
    parser.add_argument("--expected-lon", type=float, required=True)
    parser.add_argument("--expected-feature-id", type=int, required=True)
    parser.add_argument("--min-results", type=int, default=1)
    parser.add_argument("--expected-cutoff-date", default=None)
    return parser.parse_args()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def count_failed_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(sum(1 for _ in csv.DictReader(handle)), 0)


def find_extract_csvs(extract_root: Path) -> List[Path]:
    return sorted(extract_root.glob("cutoff_date=*/nws_members.csv"))


def main() -> int:
    args = parse_args()
    progress_path = args.run_dir / "status" / "progress.json"
    summary_path = args.run_dir / "status" / "run_summary.json"
    bootstrap_path = args.run_dir / "provenance" / "bootstrap_resolution.json"
    plan_path = args.run_dir / "manifests" / "blob_plan.csv"
    failed_path = args.run_dir / "status" / "failed_blobs.csv"

    missing_paths = [
        str(path)
        for path in [progress_path, summary_path, bootstrap_path, plan_path, args.results_pkl]
        if not path.exists()
    ]
    if missing_paths:
        raise SystemExit(f"Missing required artifacts: {missing_paths}")

    progress = read_json(progress_path)
    summary = read_json(summary_path)
    bootstrap = read_json(bootstrap_path)
    with args.results_pkl.open("rb") as handle:
        results_payload = pickle.load(handle)
    if not isinstance(results_payload, dict):
        raise SystemExit(f"results pickle must contain a dict, found {type(results_payload)}")

    plan = pd.read_csv(plan_path)
    extract_csvs = find_extract_csvs(args.extract_root)
    extract_summaries: List[Dict[str, Any]] = []
    extract_checks_ok = True
    for csv_path in extract_csvs:
        df = pd.read_csv(csv_path)
        cutoff_dir = csv_path.parent.name
        cutoff_date = cutoff_dir.split("=", 1)[1] if "=" in cutoff_dir else cutoff_dir
        has_target_date = "target_date" in df.columns
        member_cols = [col for col in df.columns if col.startswith("member_")]
        row_count = len(df)
        target_min = df["target_date"].min() if has_target_date and row_count else None
        target_max = df["target_date"].max() if has_target_date and row_count else None
        checks = {
            "has_target_date": has_target_date,
            "has_member_cols": len(member_cols) >= 1,
            "rows_nonempty": row_count >= 1,
        }
        issue_ok = all(checks.values())
        extract_checks_ok = extract_checks_ok and issue_ok
        extract_summaries.append(
            {
                "cutoff_date": cutoff_date,
                "csv_path": str(csv_path),
                "row_count": row_count,
                "member_cols": member_cols,
                "target_date_min": target_min,
                "target_date_max": target_max,
                "checks": checks,
                "ok": issue_ok,
            }
        )

    checks = {
        "site_code_matches": str(progress.get("site", {}).get("site_code")) == str(args.expected_site_code),
        "lat_matches": abs(float(progress.get("site", {}).get("lat")) - float(args.expected_lat)) < 1e-9,
        "lon_matches": abs(float(progress.get("site", {}).get("lon")) - float(args.expected_lon)) < 1e-9,
        "feature_id_matches": int(bootstrap.get("feature_id")) == int(args.expected_feature_id),
        "summary_status_valid": str(summary.get("status")) in {"run_complete", "already_complete"},
        "results_count_matches_summary": int(summary.get("results_count_after_run", len(results_payload))) == len(results_payload),
        "results_meet_minimum": len(results_payload) >= int(args.min_results),
        "plan_rows_match_results": len(plan) >= len(results_payload),
        "no_failed_rows": count_failed_rows(failed_path) == 0,
        "has_extract_csv": len(extract_csvs) >= 1,
        "extract_checks_ok": extract_checks_ok,
    }
    if args.expected_cutoff_date is not None:
        checks["expected_cutoff_present"] = any(item["cutoff_date"] == args.expected_cutoff_date for item in extract_summaries)

    overall_ok = all(checks.values())
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(args.run_dir),
        "results_pkl": str(args.results_pkl),
        "extract_root": str(args.extract_root),
        "summary": summary,
        "progress": progress,
        "bootstrap": bootstrap,
        "results_count": len(results_payload),
        "plan_rows": len(plan),
        "failed_rows": count_failed_rows(failed_path),
        "extracts": extract_summaries,
        "checks": checks,
        "ok": overall_ok,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "results_count": len(results_payload), "out_json": str(args.out_json)}, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
