from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_multimodel_v8_queue import launch_allowed


class MultimodelV8QueueContractTest(unittest.TestCase):
    def test_default_heavy_cutoff_behavior_is_serial(self) -> None:
        candidate = pd.Series({"cutoff": "20221225"})
        active = [{"command": "R --config /tmp/multimodel_20210123_v8_epsTT_l1.yaml"}]
        allowed, note = launch_allowed(
            candidate=candidate,
            active=active,
            free_gb=500.0,
            ordinary_max_concurrent=15,
            pause_free_gb=180.0,
            launch_free_gb=220.0,
            heavy_free_gb=240.0,
        )
        self.assertFalse(allowed)
        self.assertIn("heavy cutoff waits", note)

    def test_heavy_override_allows_parallel_heavy_and_ordinary_rows(self) -> None:
        heavy_candidate = pd.Series({"cutoff": "20221225"})
        ordinary_candidate = pd.Series({"cutoff": "20211221"})
        active = [{"command": "R --config /tmp/multimodel_20210123_v8_epsTT_l1.yaml"}]

        allowed_heavy, _ = launch_allowed(
            candidate=heavy_candidate,
            active=active,
            free_gb=500.0,
            ordinary_max_concurrent=15,
            pause_free_gb=180.0,
            launch_free_gb=220.0,
            heavy_free_gb=240.0,
            heavy_cutoff_max_concurrent=15,
            heavy_cutoff_blocks_ordinary=False,
        )
        self.assertTrue(allowed_heavy)

        active_with_heavy = active + [{"command": "R --config /tmp/multimodel_20221225_v8_ndlm_featurecov_v1_postfix_ndlm_main_keep.yaml"}]
        allowed_ordinary, _ = launch_allowed(
            candidate=ordinary_candidate,
            active=active_with_heavy,
            free_gb=500.0,
            ordinary_max_concurrent=15,
            pause_free_gb=180.0,
            launch_free_gb=220.0,
            heavy_free_gb=240.0,
            heavy_cutoff_max_concurrent=15,
            heavy_cutoff_blocks_ordinary=False,
        )
        self.assertTrue(allowed_ordinary)


if __name__ == "__main__":
    unittest.main()
