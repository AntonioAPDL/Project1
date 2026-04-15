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


class GlofasOperationalTailRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = Path(tempfile.mkdtemp(prefix="glofas_op_tail_repair_test_"))
        self.campaign_root = self.td / "campaign"
        (self.campaign_root / "plans" / "splits").mkdir(parents=True, exist_ok=True)
        (self.campaign_root / "manifests").mkdir(parents=True, exist_ok=True)
        (self.campaign_root / "outputs" / "download_root" / "grib" / "issue_date=2020-01-01").mkdir(
            parents=True, exist_ok=True
        )
        (self.campaign_root / "outputs" / "download_root" / "grib" / "issue_date=2020-01-02").mkdir(
            parents=True, exist_ok=True
        )

        with (self.campaign_root / "plans" / "split_summary.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["split_id", "issue_count"])
            writer.writeheader()
            writer.writerow({"split_id": "split_01", "issue_count": 2})
        (self.campaign_root / "plans" / "splits" / "split_01_issue_dates.txt").write_text(
            "2020-01-01\n2020-01-02\n",
            encoding="utf-8",
        )
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
                    "issue_date": "2020-01-01",
                    "status": "downloaded",
                    "path": str(
                        self.campaign_root / "outputs" / "download_root" / "grib" / "issue_date=2020-01-01" / "a.grib"
                    ),
                    "req_id": "req_ok",
                    "hydrological_model": "htessel_lisflood",
                    "notes": "ok",
                    "timestamp_utc": "2026-04-14T00:00:00",
                }
            )
            writer.writerow(
                {
                    "issue_date": "2020-01-02",
                    "status": "error_exception",
                    "path": str(
                        self.campaign_root / "outputs" / "download_root" / "grib" / "issue_date=2020-01-02" / "b.grib"
                    ),
                    "req_id": "req_bad",
                    "hydrological_model": "htessel_lisflood",
                    "notes": "HTTPError('400 job failed')",
                    "timestamp_utc": "2026-04-14T00:05:00",
                }
            )
        (
            self.campaign_root / "outputs" / "download_root" / "grib" / "issue_date=2020-01-01" / "a.grib"
        ).write_bytes(b"grib")
        (
            self.campaign_root / "outputs" / "download_root" / "grib" / "issue_date=2020-01-02" / "b.request.json"
        ).write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_dry_run_stages_targeted_retry_bundle(self) -> None:
        out_dir = self.td / "repair_bundle"
        subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "repair_glofas_operational_tail.py"),
                "--campaign-root",
                str(self.campaign_root),
                "--out-dir",
                str(out_dir),
            ],
            cwd=ROOT,
            check=True,
        )

        payload = json.loads((out_dir / "repair_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["latest_problem_count"], 1)
        self.assertEqual(payload["retry_split_count"], 1)
        self.assertEqual(payload["retry_splits"], {"split_01": ["2020-01-02"]})

        intervals_csv = (out_dir / "plans" / "split_01_retry_intervals.csv").read_text(encoding="utf-8")
        self.assertIn("start,end", intervals_csv)
        self.assertIn("2020-01-02,2020-01-02", intervals_csv)

        retry_script = (out_dir / "commands" / "10_retry_split_01.sh").read_text(encoding="utf-8")
        self.assertIn("glofas_operational_mediumrange_download_point.py", retry_script)
        self.assertIn("split_01_download_manifest.csv", retry_script)
        self.assertIn("2020-01-02", (out_dir / "plans" / "split_01_retry_issue_dates.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
