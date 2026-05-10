#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import requests

from canonical_climate_indices_lib import (
    ROOT,
    canonical_paths,
    load_config,
    monthly_wide_to_long,
    package_versions,
    parse_psl_monthly_text,
    render_download_review,
    request_text,
    sha256_path,
    snapshot_config,
    utc_now_iso,
    write_index_catalog,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download the canonical monthly climate-index source files.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "canonical_gdpc_master_covariate.yaml",
        help="Canonical climate-index config.",
    )
    parser.add_argument("--force", action="store_true", help="Redownload and overwrite existing files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config.resolve())
    paths = canonical_paths(cfg)

    manifest_rows: list[dict[str, object]] = []
    session = requests.Session()
    try:
        for item in cfg["indices"]:
            index_id = item["index_id"]
            display_name = item["display_name"]
            raw_path = paths.raw_text_root / f"{index_id}.txt"
            parsed_path = paths.monthly_csv_root / f"{index_id}.csv"

            if args.force or not raw_path.exists():
                text = request_text(
                    item["url"],
                    timeout_seconds=int(cfg["download"]["timeout_seconds"]),
                    retries=int(cfg["download"]["retries"]),
                    user_agent=str(cfg["download"]["user_agent"]),
                    session=session,
                )
                raw_path.write_text(text, encoding="utf-8")

            text = raw_path.read_text(encoding="utf-8")
            parsed = parse_psl_monthly_text(text)
            parsed.to_csv(parsed_path, index=False)
            monthly_long = monthly_wide_to_long(
                parsed,
                start_month=cfg["monthly_source_window"]["start_month"],
                end_month=cfg["monthly_source_window"]["end_month"],
            )
            manifest_rows.append(
                {
                    "index_id": index_id,
                    "display_name": display_name,
                    "url": item["url"],
                    "retrieved_at_utc": utc_now_iso(),
                    "raw_text_path": str(raw_path),
                    "raw_text_sha256": sha256_path(raw_path),
                    "parsed_csv_path": str(parsed_path),
                    "parsed_csv_sha256": sha256_path(parsed_path),
                    "year_min": int(parsed["Year"].min()),
                    "year_max": int(parsed["Year"].max()),
                    "month_start_min": monthly_long["month_start"].min().strftime("%Y-%m-%d"),
                    "month_start_max": monthly_long["month_start"].max().strftime("%Y-%m-%d"),
                    "parsed_rows": int(len(parsed)),
                }
            )
    finally:
        session.close()

    manifest_path = paths.metadata_root / "source_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "index_id",
            "display_name",
            "url",
            "retrieved_at_utc",
            "raw_text_path",
            "raw_text_sha256",
            "parsed_csv_path",
            "parsed_csv_sha256",
            "year_min",
            "year_max",
            "month_start_min",
            "month_start_max",
            "parsed_rows",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in manifest_rows:
            writer.writerow(row)

    write_index_catalog(paths.metadata_root / "index_catalog.csv", cfg["indices"])
    snapshot_config(args.config.resolve(), paths.metadata_root / "canonical_gdpc_build_config.yaml")
    write_json(
        paths.metadata_root / "source_download_summary.json",
        {
            "generated_at_utc": utc_now_iso(),
            "config_path": str(args.config.resolve()),
            "lineage_version": cfg["version"],
            "artifact_root": str(paths.root),
            "indices_count": len(cfg["indices"]),
            "package_versions": package_versions(),
            "source_manifest_path": str(manifest_path),
        },
    )
    render_download_review(cfg, manifest_rows, paths)
    print(f"[OK] wrote source manifest: {manifest_path}")
    print(f"[OK] downloaded and parsed indices: {len(manifest_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
