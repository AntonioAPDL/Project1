#!/usr/bin/env python3
from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from build_multimodel_v8_exalm_t1_discount_grid_configs import (  # noqa: E402
    FAMILY_ID,
    _discount_profiles,
    _profile_model_overrides,
)
from multimodel_v8_lib import load_yaml  # noqa: E402


class ExalmT1DiscountGridToolingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template = load_yaml(ROOT / "config" / "multimodel_v8_exalm_t1_discount_grid_exact_20260424.template.yaml")

    def test_template_is_narrow_exalm_t1_scope_with_exact_snapshot_contract(self) -> None:
        self.assertEqual(self.template["queue"]["ordinary_max_concurrent"], 4)
        self.assertEqual(self.template["queue"]["heavy_cutoff_max_concurrent"], 4)
        self.assertFalse(self.template["queue"]["heavy_cutoff_blocks_ordinary"])
        self.assertEqual(self.template["fit_parallel"]["mode"], "global_models")
        self.assertEqual(self.template["fit_parallel"]["default_workers"], 7)
        self.assertEqual(
            self.template["campaign"]["campaign_id"],
            "multimodel_v8_exalm_t1_discount_grid_exact_20260424",
        )
        self.assertEqual(self.template["campaign"]["spec_id"], "exalm_t1_discount_grid_exact_v1")

        enabled = [name for name, family in self.template["families"].items() if family.get("enabled", True)]
        self.assertEqual(enabled, [FAMILY_ID])
        family = self.template["families"][FAMILY_ID]
        self.assertEqual(family["model_id"], "exdqlm_multivar_synth_keep")
        self.assertEqual(family["model_key"], "exdqlm_multivar")
        self.assertEqual(family["likelihood_mode"], "exal")
        self.assertEqual(family["transfer_mode"], "keep")

    def test_template_contains_the_requested_nine_discount_sets(self) -> None:
        profiles = _discount_profiles(self.template)
        self.assertEqual([profile["name"] for profile in profiles], [f"set{i:02d}" for i in range(1, 10)])

        observed = {profile["name"]: profile["state_evolution"] for profile in profiles}
        self.assertEqual(observed["set01"]["df_t"], 0.99999)
        self.assertEqual(observed["set01"]["df_s1"], 0.9999)
        self.assertEqual(observed["set01"]["df_discrep"], 0.9999)
        self.assertEqual(observed["set01"]["df_covs"], 0.99995)

        self.assertEqual(observed["set02"]["df_t"], 0.99999999)
        self.assertEqual(observed["set02"]["df_s1"], 0.9995)
        self.assertEqual(observed["set02"]["df_discrep"], 0.998)
        self.assertEqual(observed["set02"]["df_covs"], 0.99999)

        self.assertEqual(observed["set04"]["df_s1"], 0.9999)
        self.assertEqual(observed["set04"]["df_discrep"], 0.99999)
        self.assertEqual(observed["set07"]["lambda"], 0.98)
        self.assertEqual(observed["set08"]["lambda"], 0.975)
        self.assertEqual(observed["set09"]["df_s1"], 0.9998)
        self.assertEqual(observed["set09"]["df_discrep"], 0.998)
        self.assertEqual(observed["set09"]["df_covs"], 0.9999999)

    def test_profile_model_overrides_only_touch_multivar_state_evolution(self) -> None:
        profile = _discount_profiles(self.template)[0]
        overrides = _profile_model_overrides(profile)
        self.assertEqual(set(overrides), {"exdqlm_multivar"})
        self.assertEqual(set(overrides["exdqlm_multivar"]), {"state_evolution"})
        self.assertNotIn("exdqlm_univar", overrides)
        self.assertEqual(overrides["exdqlm_multivar"]["state_evolution"]["df_discrep"], 0.9999)


if __name__ == "__main__":
    unittest.main()
