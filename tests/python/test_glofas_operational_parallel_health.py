#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class GlofasOperationalParallelHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = Path(tempfile.mkdtemp(prefix="glofas_parallel_health_test_"))
        self.campaign_root = self.td / "campaign"
        (self.campaign_root / "plans" / "splits").mkdir(parents=True, exist_ok=True)
        (self.campaign_root / "manifests").mkdir(parents=True, exist_ok=True)
        (self.campaign_root / "outputs" / "download_root" / "grib" / "issue_date=2020-01-16").mkdir(parents=True, exist_ok=True)

        with (self.campaign_root / "plans" / "split_summary.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["split_id", "issue_count"])
            writer.writeheader()
            writer.writerow({"split_id": "split_01", "issue_count": 1})
        (self.campaign_root / "plans" / "splits" / "split_01_issue_dates.txt").write_text("2020-01-16\n", encoding="utf-8")
        with (self.campaign_root / "manifests" / "split_01_download_manifest.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["issue_date", "status", "path", "req_id", "hydrological_model", "notes", "timestamp_utc"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "issue_date": "2020-01-16",
                    "status": "downloaded",
                    "path": "/tmp/example_1.grib",
                    "req_id": "req_a",
                    "hydrological_model": "htessel_lisflood",
                    "notes": "ok",
                    "timestamp_utc": "2026-04-08T00:00:00",
                }
            )
            writer.writerow(
                {
                    "issue_date": "2020-01-16",
                    "status": "skipped_exists",
                    "path": "/tmp/example_1.grib",
                    "req_id": "req_a",
                    "hydrological_model": "htessel_lisflood",
                    "notes": "rerun",
                    "timestamp_utc": "2026-04-08T00:05:00",
                }
            )
        (self.campaign_root / "outputs" / "download_root" / "grib" / "issue_date=2020-01-16" / "sample.grib").write_bytes(
            b"grib"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_health_dedupes_rerun_manifest_rows(self) -> None:
        out_json = self.td / "health.json"
        subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "check_glofas_operational_parallel_health.py"),
                "--campaign-root",
                str(self.campaign_root),
                "--out-json",
                str(out_json),
            ],
            cwd=ROOT,
            check=True,
        )
        payload = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["percent_complete_total"], 100.0)
        self.assertEqual(payload["grib_issue_dir_count_total"], 1)
        self.assertEqual(payload["done_like_manifest_total"], 1)
        self.assertEqual(payload["latest_status_counts_total"], {"skipped_exists": 1})
        self.assertEqual(payload["splits"][0]["manifest_rows"], 2)
        self.assertEqual(payload["splits"][0]["raw_status_counts"], {"downloaded": 1, "skipped_exists": 1})


if __name__ == "__main__":
    unittest.main()
