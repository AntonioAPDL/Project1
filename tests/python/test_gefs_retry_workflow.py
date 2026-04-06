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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


class GefsRetryWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = Path(tempfile.mkdtemp(prefix="gefs_retry_test_"))
        self.base_run_dir = self.td / "base_manifest_run"
        self.retry_run_dir = self.base_run_dir / "retry_passes" / "retry_001"
        (self.base_run_dir / "manifests").mkdir(parents=True, exist_ok=True)
        (self.base_run_dir / "smoke" / "gefs").mkdir(parents=True, exist_ok=True)
        (self.base_run_dir / "smoke" / "nwm").mkdir(parents=True, exist_ok=True)
        (self.base_run_dir / "extract_gefs_full" / "gefs").mkdir(parents=True, exist_ok=True)

        write_json(self.base_run_dir / "smoke" / "smoke_summary.json", {"gefs": {"rows_out": 1}})
        write_json(self.base_run_dir / "smoke" / "gefs" / "gefs_point_smoke_meta.json", {"selected_cell_dist_km": 1.23})
        write_json(
            self.base_run_dir / "smoke" / "nwm" / "nwm_point_smoke_meta.json",
            {"grid_reference": {"reference_distance_m": 45.0}},
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def run_python_script(self, rel_path: str, *args: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [os.sys.executable, str(ROOT / rel_path), *args]
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        if expect_ok and proc.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        return proc

    def test_build_retry_bundle_filters_to_targeted_failed_urls(self) -> None:
        write_csv(
            self.base_run_dir / "manifests" / "gefs_manifest.csv",
            [
                {"object_url": "s3://bucket/a.grib2", "init_date": "2022-12-25", "cycle_hour": 0, "member_number": 0, "product_family": "pgrb2ap5", "lead_hours": 6, "short_name": "APCP"},
                {"object_url": "s3://bucket/b.grib2", "init_date": "2022-12-25", "cycle_hour": 0, "member_number": 0, "product_family": "pgrb2ap5", "lead_hours": 12, "short_name": "APCP"},
                {"object_url": "s3://bucket/c.grib2", "init_date": "2022-12-25", "cycle_hour": 0, "member_number": 0, "product_family": "pgrb2bp5", "lead_hours": 18, "short_name": "SOILW"},
            ],
        )
        write_csv(
            self.base_run_dir / "extract_gefs_full" / "gefs" / "gefs_file_status.csv",
            [
                {"object_url": "s3://bucket/a.grib2", "status": "ok", "error": "", "init_date": "2022-12-25", "cycle_hour": 0, "member_code": "gec00", "product_family": "pgrb2ap5"},
                {"object_url": "s3://bucket/b.grib2", "status": "failed", "error": "HTTPError 503: Slow Down", "init_date": "2022-12-25", "cycle_hour": 0, "member_code": "gec00", "product_family": "pgrb2ap5"},
                {"object_url": "s3://bucket/c.grib2", "status": "failed", "error": "HTTPError 404: Missing", "init_date": "2022-12-25", "cycle_hour": 0, "member_code": "gec00", "product_family": "pgrb2bp5"},
            ],
        )
        write_csv(
            self.base_run_dir / "extract_gefs_full" / "gefs" / "gefs_row_failures.csv",
            [
                {"object_url": "s3://bucket/b.grib2", "error": "HTTPError 503: Slow Down"},
                {"object_url": "s3://bucket/c.grib2", "error": "HTTPError 404: Missing"},
            ],
        )

        self.run_python_script(
            "scripts/build_gefs_failed_retry_bundle.py",
            "--base-manifest-run-dir",
            str(self.base_run_dir),
            "--retry-run-dir",
            str(self.retry_run_dir),
        )

        retry_manifest = pd.read_csv(self.retry_run_dir / "manifests" / "gefs_manifest.csv")
        retry_status = pd.read_csv(self.retry_run_dir / "provenance" / "failed_gefs_status_rows.csv")
        retry_summary = json.loads((self.retry_run_dir / "provenance" / "retry_bundle_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(retry_manifest["object_url"].tolist(), ["s3://bucket/b.grib2"])
        self.assertEqual(retry_status["object_url"].tolist(), ["s3://bucket/b.grib2"])
        self.assertEqual(retry_summary["failed_object_urls_selected"], 1)
        self.assertTrue((self.retry_run_dir / "smoke" / "gefs" / "gefs_point_smoke_meta.json").exists())
        self.assertTrue((self.retry_run_dir / "smoke" / "nwm" / "nwm_point_smoke_meta.json").exists())

    def test_reconcile_refuses_unresolved_retry_by_default(self) -> None:
        write_csv(
            self.base_run_dir / "extract_gefs_full" / "gefs" / "gefs_point_series.csv",
            [
                {"object_url": "s3://bucket/a.grib2", "init_date": "2022-12-25", "cycle_hour": 0, "member_number": 0, "lead_hours": 6, "product_family": "pgrb2ap5", "short_name": "APCP", "level_descriptor": "surface", "value": 1.0},
            ],
        )
        write_csv(
            self.base_run_dir / "extract_gefs_full" / "gefs" / "gefs_file_status.csv",
            [
                {"object_url": "s3://bucket/a.grib2", "status": "ok", "init_date": "2022-12-25", "cycle_hour": 0, "member_code": "gec00", "product_family": "pgrb2ap5", "lead_hours_min": 6},
                {"object_url": "s3://bucket/b.grib2", "status": "failed", "init_date": "2022-12-25", "cycle_hour": 0, "member_code": "gec00", "product_family": "pgrb2ap5", "lead_hours_min": 12},
            ],
        )
        write_csv(self.base_run_dir / "extract_gefs_full" / "gefs" / "gefs_row_failures.csv", [{"object_url": "s3://bucket/b.grib2", "error": "HTTPError 503: Slow Down"}])

        retry_root = self.retry_run_dir / "extract_gefs_retry" / "gefs"
        write_csv(
            retry_root / "gefs_point_series.csv",
            [
                {"object_url": "s3://bucket/b.grib2", "init_date": "2022-12-25", "cycle_hour": 0, "member_number": 0, "lead_hours": 12, "product_family": "pgrb2ap5", "short_name": "APCP", "level_descriptor": "surface", "value": 2.0},
            ],
        )
        write_csv(
            retry_root / "gefs_file_status.csv",
            [
                {"object_url": "s3://bucket/b.grib2", "status": "failed", "init_date": "2022-12-25", "cycle_hour": 0, "member_code": "gec00", "product_family": "pgrb2ap5", "lead_hours_min": 12},
            ],
        )

        proc = self.run_python_script(
            "scripts/reconcile_gefs_retry_outputs.py",
            "--base-manifest-run-dir",
            str(self.base_run_dir),
            "--retry-run-dir",
            str(self.retry_run_dir),
            expect_ok=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("still contains non-ok rows", proc.stderr + proc.stdout)

    def test_reconcile_merges_recovered_rows_and_clears_failures(self) -> None:
        write_csv(
            self.base_run_dir / "extract_gefs_full" / "gefs" / "gefs_point_series.csv",
            [
                {"object_url": "s3://bucket/a.grib2", "init_date": "2022-12-25", "cycle_hour": 0, "member_number": 0, "lead_hours": 6, "product_family": "pgrb2ap5", "short_name": "APCP", "level_descriptor": "surface", "value": 1.0},
            ],
        )
        write_csv(
            self.base_run_dir / "extract_gefs_full" / "gefs" / "gefs_file_status.csv",
            [
                {"object_url": "s3://bucket/a.grib2", "status": "ok", "init_date": "2022-12-25", "cycle_hour": 0, "member_code": "gec00", "product_family": "pgrb2ap5", "lead_hours_min": 6},
                {"object_url": "s3://bucket/b.grib2", "status": "failed", "init_date": "2022-12-25", "cycle_hour": 0, "member_code": "gec00", "product_family": "pgrb2ap5", "lead_hours_min": 12},
            ],
        )
        write_csv(self.base_run_dir / "extract_gefs_full" / "gefs" / "gefs_row_failures.csv", [{"object_url": "s3://bucket/b.grib2", "error": "HTTPError 503: Slow Down"}])

        retry_root = self.retry_run_dir / "extract_gefs_retry" / "gefs"
        write_csv(
            retry_root / "gefs_point_series.csv",
            [
                {"object_url": "s3://bucket/b.grib2", "init_date": "2022-12-25", "cycle_hour": 0, "member_number": 0, "lead_hours": 12, "product_family": "pgrb2ap5", "short_name": "APCP", "level_descriptor": "surface", "value": 2.0},
            ],
        )
        write_csv(
            retry_root / "gefs_file_status.csv",
            [
                {"object_url": "s3://bucket/b.grib2", "status": "ok", "init_date": "2022-12-25", "cycle_hour": 0, "member_code": "gec00", "product_family": "pgrb2ap5", "lead_hours_min": 12},
            ],
        )

        self.run_python_script(
            "scripts/reconcile_gefs_retry_outputs.py",
            "--base-manifest-run-dir",
            str(self.base_run_dir),
            "--retry-run-dir",
            str(self.retry_run_dir),
            "--reconciled-out-subdir",
            "extract_gefs_full_reconciled_retry_001",
        )

        reconciled_root = self.base_run_dir / "extract_gefs_full_reconciled_retry_001" / "gefs"
        merged_series = pd.read_csv(reconciled_root / "gefs_point_series.csv")
        merged_status = pd.read_csv(reconciled_root / "gefs_file_status.csv")
        summary = json.loads((self.base_run_dir / "extract_gefs_full_reconciled_retry_001" / "gefs_reconciliation_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(sorted(merged_series["object_url"].tolist()), ["s3://bucket/a.grib2", "s3://bucket/b.grib2"])
        self.assertEqual(sorted(merged_status["status"].unique().tolist()), ["ok"])
        self.assertFalse((reconciled_root / "gefs_row_failures.csv").exists())
        self.assertEqual(summary["retry_urls_recovered_ok"], 1)
        self.assertEqual(summary["reconciled_failed_status_rows"], 0)

    def test_retry_wrapper_dry_run_writes_command_plan(self) -> None:
        write_csv(
            self.base_run_dir / "manifests" / "gefs_manifest.csv",
            [{"object_url": "s3://bucket/a.grib2"}],
        )
        write_csv(
            self.base_run_dir / "extract_gefs_full" / "gefs" / "gefs_file_status.csv",
            [{"object_url": "s3://bucket/a.grib2", "status": "failed", "error": "HTTPError 503: Slow Down"}],
        )

        env = os.environ.copy()
        env["DRY_RUN"] = "1"
        proc = subprocess.run(
            ["bash", "scripts/run_gefs_failed_retry_pass.sh", str(self.base_run_dir), "retry_002"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"Dry-run wrapper failed.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        plan_file = self.base_run_dir / "retry_passes" / "retry_002" / "commands" / "retry_pass_plan.sh"
        self.assertTrue(plan_file.exists())
        plan_text = plan_file.read_text(encoding="utf-8")
        self.assertIn("build_gefs_failed_retry_bundle.py", plan_text)
        self.assertIn("reconcile_gefs_retry_outputs.py", plan_text)


if __name__ == "__main__":
    unittest.main()
