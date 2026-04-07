#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import pickle
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import forecast_download as fd


ROOT = Path(__file__).resolve().parents[2]


class ForecastDownloadUnitTests(unittest.TestCase):
    def test_construct_blob_names_excludes_20190310(self) -> None:
        blob_names = fd.construct_blob_names(fd.date(2019, 3, 9), fd.date(2019, 3, 11))
        joined = "\n".join(blob_names)
        self.assertIn("nwm.20190309/medium_range/", joined)
        self.assertNotIn("20190310", joined)
        self.assertIn("nwm.20190311/medium_range/", joined)

    def test_construct_blob_names_single_member_count_before_ensemble_transition(self) -> None:
        blob_names = fd.construct_blob_names(fd.date(2019, 6, 18), fd.date(2019, 6, 18))
        self.assertEqual(len(blob_names), 80)
        self.assertTrue(all("/medium_range/" in name for name in blob_names))
        self.assertTrue(all(".t00z." in name for name in blob_names))

    def test_construct_blob_names_multi_member_count_at_ensemble_transition(self) -> None:
        blob_names = fd.construct_blob_names(fd.date(2019, 6, 19), fd.date(2019, 6, 19))
        self.assertEqual(len(blob_names), 488)
        self.assertTrue(any("medium_range_mem7" in name for name in blob_names))
        self.assertTrue(all(".t12z." in name for name in blob_names))

    def test_construct_blob_names_hourly_count_after_20210421(self) -> None:
        blob_names = fd.construct_blob_names(fd.date(2021, 4, 21), fd.date(2021, 4, 21))
        self.assertEqual(len(blob_names), 1464)
        self.assertIn("f001", "\n".join(blob_names))
        self.assertIn("f240", "\n".join(blob_names))

    def test_load_saved_data_resolution(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="forecast_saved_data_test_"))
        try:
            saved = td / "saved_data.pkl"
            with saved.open("wb") as handle:
                pickle.dump(
                    {
                        "closest_feature": 17684066,
                        "closest_lon": -122.0344,
                        "closest_lat": 36.9953,
                        "closest_x": -2266749.4,
                        "closest_y": 1862673.0,
                    },
                    handle,
                )
            resolution = fd.load_saved_data_resolution(saved)
            self.assertEqual(resolution.feature_id, 17684066)
            self.assertEqual(resolution.feature_source, "saved_data_pkl")
            self.assertEqual(resolution.saved_data_pkl, str(saved))
        finally:
            shutil.rmtree(td, ignore_errors=True)


class ForecastDownloadHealthScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = Path(tempfile.mkdtemp(prefix="forecast_health_test_"))
        self.run_dir = self.td / "run"
        (self.run_dir / "status").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "provenance").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "manifests").mkdir(parents=True, exist_ok=True)
        self.results_pkl = self.td / "results.pkl"
        self.extract_root = self.td / "extract_root"
        (self.extract_root / "cutoff_date=2019-06-18").mkdir(parents=True, exist_ok=True)

        (self.run_dir / "status" / "progress.json").write_text(
            json.dumps({"site": {"site_code": "11160500", "lat": 37.0443931, "lon": -122.072464}}),
            encoding="utf-8",
        )
        (self.run_dir / "status" / "run_summary.json").write_text(
            json.dumps({"status": "already_complete", "results_count_after_run": 80}),
            encoding="utf-8",
        )
        (self.run_dir / "provenance" / "bootstrap_resolution.json").write_text(
            json.dumps({"feature_id": 17684066, "feature_source": "saved_data_pkl"}),
            encoding="utf-8",
        )
        pd.DataFrame([{"blob_name": f"blob_{idx}", "already_in_results": False} for idx in range(80)]).to_csv(
            self.run_dir / "manifests" / "blob_plan.csv", index=False
        )
        with self.results_pkl.open("wb") as handle:
            pickle.dump({f"blob_{idx}": float(idx) for idx in range(80)}, handle)
        pd.DataFrame(
            {
                "target_date": ["2019-06-19", "2019-06-20"],
                "member_01": [1.0, 2.0],
            }
        ).to_csv(self.extract_root / "cutoff_date=2019-06-18" / "nws_members.csv", index=False)

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_health_script_accepts_valid_smoke_artifacts(self) -> None:
        out_json = self.td / "health.json"
        proc = subprocess.run(
            [
                os.sys.executable,
                str(ROOT / "scripts" / "check_forecast_download_health.py"),
                "--run-dir",
                str(self.run_dir),
                "--results-pkl",
                str(self.results_pkl),
                "--extract-root",
                str(self.extract_root),
                "--expected-site-code",
                "11160500",
                "--expected-lat",
                "37.0443931",
                "--expected-lon",
                "-122.072464",
                "--expected-feature-id",
                "17684066",
                "--min-results",
                "80",
                "--expected-cutoff-date",
                "2019-06-18",
                "--out-json",
                str(out_json),
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
        self.assertEqual(payload["results_count"], 80)


if __name__ == "__main__":
    unittest.main()
