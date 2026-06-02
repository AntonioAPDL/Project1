from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_exdqlm_multivar_drop_20211112_q50_repair import (  # noqa: E402
    DIAGNOSTIC_TAG,
    Q50_REPAIR_PATCH,
    REPAIR_TAG,
    TARGET_CUTOFF,
    TARGET_FAMILY,
    build_package,
    repair_batch_payload,
)


def load_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    return payload


class HE2ExdqlmMultivarDropQ50RepairTests(unittest.TestCase):
    def test_repair_batch_is_single_cutoff_and_preserves_scientific_contract(self) -> None:
        payload = repair_batch_payload()
        self.assertEqual(payload["selection"]["cutoffs"], [TARGET_CUTOFF])
        self.assertEqual(payload["selection"]["families"], [TARGET_FAMILY])
        self.assertEqual(payload["resources"]["fit_parallel_workers"], 7)
        self.assertEqual(payload["queue"]["ordinary_max_concurrent"], 1)

        family_patch = next(
            row for row in payload["overrides"]["row_config_patches"] if row.get("family") == TARGET_FAMILY and not row.get("cutoff")
        )
        model_patch = family_patch["config_patch"]["models"]["exdqlm_multivar"]
        self.assertEqual(model_patch["likelihood_mode"], "exal")
        self.assertEqual(model_patch["forecast_transfer_mode"], "drop")
        self.assertEqual(model_patch["structure"]["enabled_harmonic_indices"], [1, 2, 3])

        q50 = family_patch["config_patch"]["fit"]["exdqlm_multivar"]["gamma_sigma"]["quantile_overrides"]["q50"]
        self.assertEqual(q50["stabilization"]["median_state_hold_after_guard_iters"], 10)
        self.assertEqual(q50["stabilization"]["median_state_blend_alpha"], 1.0)
        self.assertEqual(q50["stabilization"]["median_cov_blend_alpha"], 1.0)
        self.assertEqual(q50["stabilization"]["median_max_abs_gamma_step"], 0.075)
        self.assertEqual(q50["stabilization"]["median_max_abs_log_sigma_step"], 0.15)
        self.assertEqual(q50["terminal_sampling_guard"]["mode"], "fail_fast")
        self.assertTrue(q50["terminal_sampling_guard"]["require_frozen"])
        patch_q50 = Q50_REPAIR_PATCH["fit"]["exdqlm_multivar"]["gamma_sigma"]["quantile_overrides"]["q50"]
        self.assertEqual(q50["freeze_target"], patch_q50["freeze_target"])
        self.assertEqual(q50["terminal_sampling_guard"], patch_q50["terminal_sampling_guard"])
        self.assertEqual(q50["stabilization"], patch_q50["stabilization"])
        self.assertEqual(q50["init"]["mode"], "robust")

    def test_builder_writes_q50_diagnostic_and_full_final_configs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = build_package(Path(tmp) / "q50repair")
            diag = load_yaml(Path(summary["diagnostic_config"]))
            final = load_yaml(Path(summary["final_config"]))
            metadata = load_yaml(Path(summary["metadata"]))

            self.assertTrue(diag["run"]["run_id"].endswith(DIAGNOSTIC_TAG))
            self.assertTrue(final["run"]["run_id"].endswith(REPAIR_TAG))
            self.assertEqual(diag["fit"]["quantiles"], [0.5])
            self.assertEqual(diag["fit"]["active_quantiles"], [0.5])
            self.assertEqual(diag["fit"]["parallel"]["workers"], 1)
            self.assertFalse(diag["stages"]["post"])
            self.assertFalse(diag["stages"]["validate"])
            self.assertFalse(diag["stages"]["report"])

            self.assertEqual(final["fit"]["parallel"]["workers"], 7)
            self.assertTrue(final["stages"]["post"])
            self.assertTrue(final["stages"]["validate"])
            self.assertTrue(final["stages"]["report"])
            self.assertEqual(metadata["target_cutoff"], TARGET_CUTOFF)
            self.assertTrue(Path(summary["diagnostic_launch_script"]).exists())
            self.assertTrue(Path(summary["final_launch_script"]).exists())


class TerminalSamplingGuardSourceContractTests(unittest.TestCase):
    def test_frozen_terminal_endpoint_blocks_sampling_independent_of_lag_gate(self) -> None:
        for script in ["DISC_Optimal_Synth_Ranges_W.r", "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r"]:
            with self.subTest(script=script):
                text = (ROOT / script).read_text(encoding="utf-8")
                self.assertIn("terminal_sampling_guard_recent_enough <-", text)
                self.assertIn(
                    "terminal_sampling_guard_blocked <- if (isTRUE(DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_REQUIRE_FROZEN))",
                    text,
                )
                self.assertIn("isTRUE(terminal_sampling_guard_frozen) ||", text)
                self.assertIn("isTRUE(terminal_sampling_guard_blocked))", text)
                old_gate = (
                    "terminal_guard_lag_iters <= DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_MAX_GUARD_LAG_ITERS &&\n"
                    "    (!isTRUE(DISC_GAMSIG_TERMINAL_SAMPLING_GUARD_REQUIRE_FROZEN)"
                )
                self.assertNotIn(old_gate, text)


if __name__ == "__main__":
    unittest.main()
