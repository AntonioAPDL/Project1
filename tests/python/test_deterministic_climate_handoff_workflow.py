#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "prepare_deterministic_climate_handoff.py"
SPEC = importlib.util.spec_from_file_location("prepare_detclim_handoff", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DeterministicClimateHandoffWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = Path(tempfile.mkdtemp(prefix="detclim_handoff_test_"))
        self.run_dir = self.td / "manifest_run"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "extract_gefs_full" / "gefs").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "extract_gefs_full_reconciled_retry" / "gefs").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "extract_full" / "nwm").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "extract_gefs_full" / "gefs" / "gefs_point_series.csv").write_text("ok\n", encoding="utf-8")
        (self.run_dir / "extract_gefs_full_reconciled_retry" / "gefs" / "gefs_point_series.csv").write_text(
            "ok\n", encoding="utf-8"
        )
        (self.run_dir / "extract_full" / "nwm" / "nwm_point_series.csv").write_text("ok\n", encoding="utf-8")

        self.site_config = self.td / "site.yaml"
        self.site_config.write_text(
            yaml.safe_dump({"site": {"usgs_site": "11160500", "lat": 37.0, "lon": -122.0}}, sort_keys=False),
            encoding="utf-8",
        )

        self.campaign_cfg = self.td / "campaign.yaml"
        self.campaign_cfg.write_text(
            yaml.safe_dump(
                {
                    "inputs": {
                        "deterministic_climate": {
                            "enabled": True,
                            "handoff_root": None,
                        }
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        self.workflow_cfg = self.td / "workflow.yaml"
        self.workflow_cfg.write_text(yaml.safe_dump({"version": 1}, sort_keys=False), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def test_select_existing_extract_subdir_prefers_first_existing_candidate(self) -> None:
        selected = MODULE.select_existing_extract_subdir(
            run_dir=self.run_dir,
            subdirs=["extract_gefs_full_reconciled_retry", "extract_gefs_full"],
            required_relpath="gefs/gefs_point_series.csv",
        )
        self.assertEqual(selected, "extract_gefs_full_reconciled_retry")

    def test_build_plan_detects_existing_nwm_and_computes_handoff_root(self) -> None:
        cfg = {
            "manifest_run_dir": str(self.run_dir),
            "site_config": str(self.site_config),
            "gefs": {"preferred_extract_subdirs": ["extract_gefs_full_reconciled_retry", "extract_gefs_full"]},
            "nwm": {"extract_subdir": "extract_full", "workers": 4, "batch_size": 16, "file_retries": 2},
            "health": {"out_json": "health_checks/forecast_extract_health_ready.json"},
            "handoff": {"out_subdir": "handoff_forecasts", "overwrite": True},
            "campaign_sync": {"enabled": True, "config_path": str(self.campaign_cfg)},
        }

        class Args:
            config = str(self.workflow_cfg)
            dry_run = True
            force_nwm = False
            skip_campaign_sync = False

        plan = MODULE.build_plan(cfg, Args())
        self.assertEqual(plan["selected_gefs_extract_subdir"], "extract_gefs_full_reconciled_retry")
        self.assertEqual(plan["selected_nwm_extract_subdir"], "extract_full")
        self.assertFalse(plan["need_nwm_extract"])
        self.assertTrue(plan["handoff_root"].endswith("handoff_forecasts/site=11160500/run_id=manifest_run"))

    def test_sync_campaign_handoff_root_updates_template(self) -> None:
        handoff_root = self.td / "handoff_forecasts" / "site=11160500" / "run_id=manifest_run"
        MODULE.sync_campaign_handoff_root(self.campaign_cfg, handoff_root)
        payload = yaml.safe_load(self.campaign_cfg.read_text(encoding="utf-8"))
        self.assertEqual(payload["inputs"]["deterministic_climate"]["handoff_root"], str(handoff_root))


if __name__ == "__main__":
    unittest.main()
