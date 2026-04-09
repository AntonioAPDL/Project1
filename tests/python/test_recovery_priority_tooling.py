#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

import scripts.recovery_priority_lib as priority_lib


ROOT = Path(__file__).resolve().parents[2]


class RecoveryPriorityToolingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = Path(tempfile.mkdtemp(prefix="recovery_priority_tooling_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_count_nonempty_month_shards_ignores_empty_files(self) -> None:
        product_root = self.td / "hist_v31_lisflood_cons"
        good_dir = product_root / "year=1987" / "month=05"
        bad_dir = product_root / "year=1987" / "month=06"
        good_dir.mkdir(parents=True, exist_ok=True)
        bad_dir.mkdir(parents=True, exist_ok=True)
        (good_dir / "good.zip").write_bytes(b"zip")
        (bad_dir / "empty.zip").write_bytes(b"")
        count = priority_lib.count_nonempty_month_shards(product_root, date(1987, 5, 29), date(1987, 6, 30))
        self.assertEqual(count, 1)

    def test_ensure_glofas_historical_product_ready_dry_run_writes_status(self) -> None:
        recovery_family_root = self.td / "family=glofas_historical" / "full_runs" / "source_native_tranche1"
        done_dir = recovery_family_root / "outputs" / "historical_zips" / "hist_v31_lisflood_cons" / "year=1987" / "month=05"
        done_dir.mkdir(parents=True, exist_ok=True)
        (done_dir / "done.zip").write_bytes(b"zip")

        subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "ensure_glofas_historical_product_ready.py"),
                "--recovery-family-root",
                str(recovery_family_root),
                "--product-id",
                "hist_v31_lisflood_cons",
                "--focus-start",
                "1987-05-29",
                "--focus-end",
                "1987-07-31",
                "--workers",
                "2",
                "--dry-run",
            ],
            cwd=ROOT,
            check=True,
        )

        status_path = recovery_family_root / "status" / "hist_v31_lisflood_cons_ready.json"
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["done_shards"], 1)
        self.assertEqual(payload["missing_shards"], 2)
        self.assertEqual(payload["expected_shards"], 3)
        self.assertEqual(payload["status"], "planned")


if __name__ == "__main__":
    unittest.main()
