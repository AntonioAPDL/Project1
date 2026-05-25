from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_he2_exdqlm_multivar_keep_grid_configs as grid  # noqa: E402


class HE2ExDQLMKeepGridToolingTests(unittest.TestCase):
    def test_user_grid_manifest_has_expected_cartesian_scope(self) -> None:
        manifest = ROOT / "config" / "he2_grid_specs" / "exdqlm_multivar_keep_epsilon_discount_grid_20260524.csv"
        specs = grid.load_grid_specs(manifest)
        self.assertEqual(len(specs), 30)
        self.assertEqual(set(specs["discount_case_id"]), {"c01", "c02", "c03", "c04", "c05", "c06"})
        expected_eps = {30.0, 60.0, 90.0, 180.0, 365.0}
        for case_id, case_rows in specs.groupby("discount_case_id"):
            self.assertEqual(set(case_rows["epsilon"]), expected_eps, case_id)
        self.assertTrue((specs["max_iter"] == 100).all())
        self.assertTrue((specs["min_update_iters"] == 50).all())
        c05 = specs.loc[specs["grid_spec_id"] == "c05_eps030"].iloc[0]
        self.assertEqual(float(c05["df_discrep"]), 0.9988)
        self.assertEqual(float(c05["df_s1"]), 0.9993)
        self.assertEqual(float(c05["df_s2"]), 0.9993)

    def test_spec_patch_wires_discount_epsilon_component_gate_and_quantiles(self) -> None:
        manifest = ROOT / "config" / "he2_grid_specs" / "exdqlm_multivar_keep_epsilon_discount_grid_20260524.csv"
        specs = grid.load_grid_specs(manifest)
        spec = specs.loc[specs["grid_spec_id"] == "c06_eps030"].iloc[0]
        patch = grid.build_spec_patch(spec, {"enabled": True, "quantile": 0.5, "pre_days": 30, "fail_fast": True})
        state = patch["models"]["exdqlm_multivar"]["state_evolution"]
        self.assertEqual(state["df_t"], 0.99999)
        self.assertEqual(state["df_discrep"], 0.9995)
        self.assertEqual(state["df_covs"], 0.999999)
        self.assertEqual(state["lambda"], 0.97)
        self.assertEqual(patch["fit"]["quantiles"], [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95])
        self.assertEqual(patch["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"], 30.0)
        self.assertEqual(patch["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["c_factor"], 1.0)
        self.assertTrue(patch["post"]["multivar_component_diagnostics"]["enabled"])
        self.assertTrue(patch["post"]["multivar_component_diagnostics"]["fail_fast"])

    def test_grid_run_ids_are_cutoff_and_spec_specific(self) -> None:
        self.assertEqual(
            grid.grid_run_id("20221225", "c01_eps365"),
            "multimodel_20221225_v8_he2grid_c01_eps365_exdqlm_multivar_keep",
        )
        self.assertEqual(
            grid.grid_run_id("20210123", "case 1 / eps=365"),
            "multimodel_20210123_v8_he2grid_case_1_eps_365_exdqlm_multivar_keep",
        )


if __name__ == "__main__":
    unittest.main()
