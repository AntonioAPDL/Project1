from __future__ import annotations

import sys
import tempfile
import unittest
from io import StringIO
from unittest import mock
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_multimodel_v8_queue
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

    def test_memory_gate_blocks_ordinary_launch_when_available_ram_is_low(self) -> None:
        candidate = pd.Series({"cutoff": "20211221"})
        allowed, note = launch_allowed(
            candidate=candidate,
            active=[],
            free_gb=500.0,
            ordinary_max_concurrent=15,
            pause_free_gb=180.0,
            launch_free_gb=220.0,
            heavy_free_gb=240.0,
            mem_available_gb=149.0,
            launch_mem_gb=150.0,
        )
        self.assertFalse(allowed)
        self.assertIn("mem_available_gb", note)

    def test_memory_gate_blocks_heavy_launch_with_heavy_threshold(self) -> None:
        candidate = pd.Series({"cutoff": "20221225"})
        allowed, note = launch_allowed(
            candidate=candidate,
            active=[],
            free_gb=500.0,
            ordinary_max_concurrent=15,
            pause_free_gb=180.0,
            launch_free_gb=220.0,
            heavy_free_gb=240.0,
            mem_available_gb=199.0,
            launch_mem_gb=150.0,
            heavy_mem_gb=200.0,
            heavy_cutoff_max_concurrent=15,
            heavy_cutoff_blocks_ordinary=False,
        )
        self.assertFalse(allowed)
        self.assertIn("heavy cutoff requires mem_available_gb", note)

    def test_memory_gate_allows_launch_when_ram_is_unobserved(self) -> None:
        candidate = pd.Series({"cutoff": "20211221"})
        allowed, _ = launch_allowed(
            candidate=candidate,
            active=[],
            free_gb=500.0,
            ordinary_max_concurrent=15,
            pause_free_gb=180.0,
            launch_free_gb=220.0,
            heavy_free_gb=240.0,
            mem_available_gb=None,
            launch_mem_gb=150.0,
        )
        self.assertTrue(allowed)

    def test_default_queue_runner_keeps_rdata_through_post_then_cleanup(self) -> None:
        class DummyProc:
            pid = 12345

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "unit_test_queue_launch.log"
            with mock.patch.object(run_multimodel_v8_queue.subprocess, "Popen", return_value=DummyProc()) as popen:
                pid = run_multimodel_v8_queue.launch_run(
                    ROOT / "config" / "example.yaml",
                    log_path,
                )

        self.assertEqual(pid, 12345)
        cmd = popen.call_args.args[0]
        self.assertEqual(cmd[:2], ["bash", "scripts/run_unified_with_cleanup.sh"])
        self.assertEqual(cmd[-2:], ["--config", str(ROOT / "config" / "example.yaml")])
        wrapper_text = (ROOT / "scripts" / "run_unified_with_cleanup.sh").read_text(encoding="utf-8")
        self.assertIn("CLEANUP_RDATA_AFTER_POST=1", wrapper_text)
        self.assertIn("/data/muscat_data/jaguir26/libs/boost/lib", wrapper_text)
        self.assertIn("LD_LIBRARY_PATH", wrapper_text)

    def test_queue_runner_can_launch_no_cleanup_smoke(self) -> None:
        class DummyProc:
            pid = 12346

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "unit_test_queue_launch_no_cleanup.log"
            with mock.patch.object(run_multimodel_v8_queue.subprocess, "Popen", return_value=DummyProc()) as popen:
                pid = run_multimodel_v8_queue.launch_run(
                    ROOT / "config" / "example.yaml",
                    log_path,
                    cleanup_rdata_after_post=False,
                )

        self.assertEqual(pid, 12346)
        cmd = popen.call_args.args[0]
        self.assertEqual(cmd[:2], ["bash", "scripts/run_unified_without_cleanup.sh"])
        self.assertEqual(cmd[-2:], ["--config", str(ROOT / "config" / "example.yaml")])
        wrapper_text = (ROOT / "scripts" / "run_unified_without_cleanup.sh").read_text(encoding="utf-8")
        self.assertIn("CLEANUP_RDATA_AFTER_POST=0", wrapper_text)
        self.assertIn("/data/muscat_data/jaguir26/libs/boost/lib", wrapper_text)
        self.assertIn("LD_LIBRARY_PATH", wrapper_text)

    def test_health_refresh_warning_does_not_raise(self) -> None:
        completed = run_multimodel_v8_queue.subprocess.CompletedProcess(args=["python3"], returncode=7)
        with mock.patch.object(run_multimodel_v8_queue.subprocess, "run", return_value=completed):
            log_handle = StringIO()
            run_multimodel_v8_queue.refresh_health(Path("/tmp/matrix"), log_handle)
        self.assertIn("health refresh warning returncode=7", log_handle.getvalue())


if __name__ == "__main__":
    unittest.main()
