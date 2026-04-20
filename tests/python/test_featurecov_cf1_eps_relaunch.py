#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from relaunch_multimodel_v8_featurecov_cf1_eps_campaign import (  # noqa: E402
    choose_ordinary_max_concurrent,
    collect_relaunch_snapshot,
    find_queue_controllers,
    read_launch_settings,
)


class FeaturecovCf1EpsRelaunchTests(unittest.TestCase):
    def test_read_launch_settings_parses_env_lines(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="featurecov_relaunch_env_"))
        try:
            env_path = td / "launch_settings.env"
            env_path.write_text(
                "ARTIFACT_ROOT=/tmp/artifact\nORDINARY_MAX_CONCURRENT=12\n# comment\nPOLL_SECONDS=60\n",
                encoding="utf-8",
            )
            settings = read_launch_settings(env_path)
            self.assertEqual(settings["ARTIFACT_ROOT"], "/tmp/artifact")
            self.assertEqual(settings["ORDINARY_MAX_CONCURRENT"], "12")
            self.assertEqual(settings["POLL_SECONDS"], "60")
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_find_queue_controllers_filters_to_matrix_dir(self) -> None:
        import subprocess

        matrix_dir = Path("/tmp/matrix_a")
        fake_ps = (
            "101 python3 scripts/run_multimodel_v8_queue.py --matrix-dir /tmp/matrix_a --artifact-root /tmp/a\n"
            "102 python3 scripts/run_multimodel_v8_queue.py --matrix-dir /tmp/matrix_b --artifact-root /tmp/b\n"
        )
        completed = subprocess.CompletedProcess(args=["ps"], returncode=0, stdout=fake_ps, stderr="")
        with mock.patch(
            "relaunch_multimodel_v8_featurecov_cf1_eps_campaign.subprocess.run",
            return_value=completed,
        ):
            rows = find_queue_controllers(matrix_dir)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pid"], "101")

    def test_choose_ordinary_max_concurrent_defaults_to_safe_cap(self) -> None:
        self.assertEqual(choose_ordinary_max_concurrent(12, None, 6), 6)
        self.assertEqual(choose_ordinary_max_concurrent(4, None, 6), 4)
        self.assertEqual(choose_ordinary_max_concurrent(12, 9, 6), 9)

    def test_collect_relaunch_snapshot_detects_orphan_pending(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="featurecov_relaunch_snapshot_"))
        try:
            matrix_dir = td / "matrix"
            matrix_dir.mkdir(parents=True, exist_ok=True)
            artifact_root = td / "artifact_root"
            runs_root = artifact_root / "runs"
            plan_path = matrix_dir / "matrix_plan.csv"
            plan_path.write_text(
                "order_index,cutoff,epsilon,lane,run_id,config_path\n"
                "1,20211221,eps90cf1,exdqlm_multivar_keep,multimodel_20211221_v8_eps90cf1_exdqlm_multivar_keep_featurecov_cf1,/tmp/keep.yaml\n"
                "2,20211221,eps90cf1,exdqlm_multivar_drop,multimodel_20211221_v8_eps90cf1_exdqlm_multivar_drop_featurecov_cf1,/tmp/drop.yaml\n",
                encoding="utf-8",
            )
            for run_id in [
                "multimodel_20211221_v8_eps90cf1_exdqlm_multivar_keep_featurecov_cf1",
                "multimodel_20211221_v8_eps90cf1_exdqlm_multivar_drop_featurecov_cf1",
            ]:
                run_root = runs_root / run_id
                run_root.mkdir(parents=True, exist_ok=True)
                manifest = {
                    "stages": {
                        "data_prep_shared": {"status": "pass"},
                        "fit": {"status": "pending"},
                        "post": {"status": "pending"},
                        "validate": {"status": "pending"},
                        "report": {"status": "pending"},
                    },
                    "timestamps": {"started_at_utc": "2026-04-18T00:00:00Z", "finished_at_utc": ""},
                }
                (run_root / "run_manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

            active_rows = [
                {
                    "pid": "123",
                    "command": "/usr/lib64/R/bin/exec/R --file=scripts/unified_run.R --args --config "
                    "/tmp/multimodel_20211221_v8_eps90cf1_exdqlm_multivar_keep_featurecov_cf1.yaml",
                }
            ]
            with mock.patch(
                "relaunch_multimodel_v8_featurecov_cf1_eps_campaign.pgrep_active_v8",
                return_value=active_rows,
            ):
                snapshot = collect_relaunch_snapshot(matrix_dir, artifact_root)

            self.assertEqual(snapshot["counts"]["pending"], 2)
            self.assertEqual(
                snapshot["orphan_pending_run_ids"],
                ["multimodel_20211221_v8_eps90cf1_exdqlm_multivar_drop_featurecov_cf1"],
            )
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
