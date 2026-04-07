#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


class GlofasOperationalHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = Path(tempfile.mkdtemp(prefix="glofas_operational_health_test_"))
        self.download_root = self.td / "download_root"
        self.extract_root = self.td / "extract_root"
        (self.download_root / "manifests").mkdir(parents=True, exist_ok=True)
        (self.download_root / "grib" / "issue_date=2020-01-16").mkdir(parents=True, exist_ok=True)
        (self.extract_root / "issue_date=2020-01-16").mkdir(parents=True, exist_ok=True)

        manifest_rows = [
            {
                "issue_date": "2020-01-16",
                "status": "downloaded",
                "path": str(self.download_root / "grib" / "issue_date=2020-01-16" / "sample.grib"),
                "req_id": "req_001",
                "hydrological_model": "htessel_lisflood",
                "notes": "ok",
                "timestamp_utc": "2026-04-06T00:00:00",
            },
            {
                "issue_date": "2020-01-16",
                "status": "skipped_exists",
                "path": str(self.download_root / "grib" / "issue_date=2020-01-16" / "sample.grib"),
                "req_id": "req_001",
                "hydrological_model": "htessel_lisflood",
                "notes": "rerun",
                "timestamp_utc": "2026-04-06T00:10:00",
            },
        ]
        pd.DataFrame(manifest_rows).to_csv(self.download_root / "manifests" / "download_manifest.csv", index=False)
        (self.download_root / "grib" / "issue_date=2020-01-16" / "sample.grib").write_bytes(b"grib")
        (self.download_root / "grib" / "issue_date=2020-01-16" / "sample.request.json").write_text(
            json.dumps({"system_version": "operational", "hydrological_model": "htessel_lisflood"}),
            encoding="utf-8",
        )
        (self.extract_root / "cell.json").write_text(json.dumps({"dist_km": 1.23}), encoding="utf-8")
        df = pd.DataFrame({"target_date": pd.date_range("2020-01-17", periods=28, freq="D").strftime("%Y-%m-%d")})
        for idx in range(0, 51):
            df[f"member_{idx:02d}"] = float(idx)
        df.to_csv(self.extract_root / "issue_date=2020-01-16" / "glofas_members.csv", index=False)
        (self.td / "issue_dates.txt").write_text("2020-01-16\n", encoding="utf-8")
        (self.td / "extract_rerun.log").write_text("[DONE] ok=0 skipped=1 out_root=/tmp/example\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_health_script_accepts_valid_smoke_outputs(self) -> None:
        out_json = self.td / "health.json"
        proc = subprocess.run(
            [
                os.sys.executable,
                str(ROOT / "scripts" / "check_glofas_operational_forecast_health.py"),
                "--download-root",
                str(self.download_root),
                "--extract-root",
                str(self.extract_root),
                "--dates-file",
                str(self.td / "issue_dates.txt"),
                "--out-json",
                str(out_json),
                "--extract-rerun-log",
                str(self.td / "extract_rerun.log"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"Health script failed.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        payload = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["issue_count"], 1)
        self.assertEqual(payload["extract_rerun_skip_count"], 1)


if __name__ == "__main__":
    unittest.main()
