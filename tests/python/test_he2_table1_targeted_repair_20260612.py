from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "config" / "he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml"
BATCH = ROOT / "config" / "he2_relaunch_batches" / "table1_targeted_repair_20260612.yaml"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


class HE2Table1TargetedRepair20260612Tests(unittest.TestCase):
    EXPECTED_RUN_IDS = {
        "multimodel_20210123_v8_he2tbl1fix20260612_ndlm_main_drop",
        "multimodel_20210123_v8_he2tbl1fix20260612_ndlm_main_keep",
        "multimodel_20210123_v8_he2tbl1fix20260612_dqlm_univar_al",
        "multimodel_20210123_v8_he2tbl1fix20260612_exdqlm_univar",
        "multimodel_20210123_v8_he2tbl1fix20260612_exdqlm_multivar_drop",
        "multimodel_20211112_v8_he2tbl1fix20260612_dqlm_univar_al",
        "multimodel_20211112_v8_he2tbl1fix20260612_exdqlm_univar",
        "multimodel_20211112_v8_he2tbl1fix20260612_exdqlm_multivar_drop",
        "multimodel_20211221_v8_he2tbl1fix20260612_ndlm_univar_keep",
        "multimodel_20211221_v8_he2tbl1fix20260612_ndlm_main_keep",
        "multimodel_20211221_v8_he2tbl1fix20260612_dqlm_univar_al",
        "multimodel_20211221_v8_he2tbl1fix20260612_exdqlm_univar",
        "multimodel_20211221_v8_he2tbl1fix20260612_exdqlm_multivar_drop",
        "multimodel_20220511_v8_he2tbl1fix20260612_dqlm_univar_al",
        "multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop",
        "multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_keep",
        "multimodel_20220511_v8_he2tbl1fix20260612_exdqlm_univar",
        "multimodel_20220511_v8_he2tbl1fix20260612_exdqlm_multivar_drop",
        "multimodel_20221225_v8_he2tbl1fix20260612_ndlm_univar_keep",
        "multimodel_20221225_v8_he2tbl1fix20260612_ndlm_main_keep",
        "multimodel_20221225_v8_he2tbl1fix20260612_dqlm_univar_al",
        "multimodel_20221225_v8_he2tbl1fix20260612_dqlm_multivar_al_drop",
        "multimodel_20221225_v8_he2tbl1fix20260612_exdqlm_univar",
        "multimodel_20221225_v8_he2tbl1fix20260612_exdqlm_multivar_drop",
    }

    def patch_by_label(self, label: str) -> dict:
        payload = load_yaml(BATCH)
        for patch in payload["overrides"]["row_config_patches"]:
            if patch.get("manuscript_label") == label:
                return patch["config_patch"]
        raise LookupError(label)

    def test_template_is_isolated_and_points_to_batch(self) -> None:
        payload = load_yaml(TEMPLATE)
        self.assertEqual(payload["campaign"]["campaign_spec_id"], "he2tbl1fix20260612")
        self.assertIn("table1_targeted_repair_20260612", payload["campaign"]["artifact_root"])
        self.assertEqual(
            payload["selection"]["batch_file"],
            "config/he2_relaunch_batches/table1_targeted_repair_20260612.yaml",
        )
        self.assertEqual(payload["bundles"]["bundle_run_id"], "20260510_publication_shared_r01")
        self.assertEqual(payload["bundles"]["data_start"], "1987-05-29")
        self.assertEqual(payload["validation"]["smoke_fit_overrides"]["ndlm_main"]["gamma_sigma"]["max_iter"], 1)
        self.assertEqual(payload["validation"]["full_pipeline_ndlm_family"], "__disabled__")

    def test_univariate_full_pipeline_smoke_has_required_quantile_pair(self) -> None:
        payload = load_yaml(TEMPLATE)
        quantiles = payload["validation"]["full_pipeline_univar_quantiles"]
        self.assertGreaterEqual(len(quantiles), 2)
        self.assertIn(0.05, quantiles)
        self.assertIn(0.50, quantiles)

    def test_batch_selects_exact_requested_rows(self) -> None:
        payload = load_yaml(BATCH)
        self.assertEqual(set(payload["selection"]["run_ids"]), self.EXPECTED_RUN_IDS)
        self.assertEqual(len(payload["selection"]["run_ids"]), 24)

    def test_common_quantile_warmup_is_uniform_40(self) -> None:
        payload = load_yaml(BATCH)
        common_patch = payload["overrides"]["common_config_patch"]
        self.assertEqual(
            common_patch["fit"]["exdqlm_univar"]["gamma_sigma"]["warmup_freeze_iters"],
            40,
        )
        multivar_gs = common_patch["fit"]["exdqlm_multivar"]["gamma_sigma"]
        self.assertEqual(multivar_gs["warmup_freeze_iters"], 40)
        for q_key in ("q20", "q35", "q50", "q65", "q80"):
            self.assertEqual(
                multivar_gs["quantile_overrides"][q_key]["warmup_freeze_iters"],
                40,
            )

    def test_ndlm_main_override_matches_requested_spec(self) -> None:
        for label in ("N-M-T0", "N-M-T1"):
            state = self.patch_by_label(label)["models"]["ndlm_main"]["state_evolution"]
            self.assertEqual(
                state,
                {
                    "df_t": 0.99999999,
                    "df_s1": 0.99999999,
                    "df_s2": 0.99999999,
                    "df_s67": 0.99999999,
                    "df_discrep": 0.99999999,
                    "lambda": 0.97,
                    "df_trans": 0.99999999,
                    "df_covs": 0.99999999,
                },
            )
            fc = self.patch_by_label(label)["models"]["ndlm_main"]["prior"]["forecast_cov"]
            self.assertIsNone(fc["epsilon"])
            self.assertEqual(fc["c_factor"], 1.0)

    def test_exal_univar_override_matches_requested_spec(self) -> None:
        patch = self.patch_by_label("exAL-U-T1")
        state = patch["models"]["exdqlm_univar"]["state_evolution"]
        self.assertEqual(
            state,
            {
                "df_t": 0.99999999,
                "df_s1": 0.99999999,
                "df_s2": 0.99999999,
                "df_s67": 0.99999999,
                "lambda": 0.97,
                "df_trans": 0.9999999,
                "df_covs": 0.9999999,
            },
        )
        self.assertEqual(patch["models"]["exdqlm_univar"]["likelihood_mode"], "exal")

    def test_multivar_quantile_overrides_match_requested_specs(self) -> None:
        expected = {
            "exAL-M-T0": {
                "df_t": 0.99999999,
                "df_s1": 0.99999999,
                "df_s2": 0.99999999,
                "df_s67": 0.99999999,
                "df_discrep": 0.99999999,
                "lambda": 0.97,
                "df_trans": 0.9999999,
                "df_covs": 0.9999999,
            },
            "AL-M-T0": {
                "df_t": 0.99999999,
                "df_s1": 0.99999999,
                "df_s2": 0.99999999,
                "df_s67": 0.99999999,
                "df_discrep": 0.99999999,
                "lambda": 0.97,
                "df_trans": 0.99999999,
                "df_covs": 0.99999999,
            },
            "AL-M-T1": {
                "df_t": 0.9999999,
                "df_s1": 0.9999999,
                "df_s2": 0.9999999,
                "df_s67": 0.9999999,
                "df_discrep": 0.9999999,
                "lambda": 0.97,
                "df_trans": 0.9999999,
                "df_covs": 0.9999999,
            },
        }
        for label, state in expected.items():
            patch = self.patch_by_label(label)
            self.assertEqual(patch["models"]["exdqlm_multivar"]["state_evolution"], state)
            fc = patch["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]
            self.assertEqual(fc, {"epsilon": 365.0, "c_factor": 1.0})

    def test_al_univar_and_ndlm_univar_are_selected_without_new_specific_override(self) -> None:
        payload = load_yaml(BATCH)
        selected = set(payload["selection"]["run_ids"])
        self.assertIn("multimodel_20211221_v8_he2tbl1fix20260612_ndlm_univar_keep", selected)
        self.assertIn("multimodel_20221225_v8_he2tbl1fix20260612_ndlm_univar_keep", selected)
        self.assertIn("multimodel_20210123_v8_he2tbl1fix20260612_dqlm_univar_al", selected)
        labels_with_specific_patch = {
            patch.get("manuscript_label")
            for patch in payload["overrides"]["row_config_patches"]
            if patch.get("manuscript_label")
        }
        self.assertNotIn("N-U-T1", labels_with_specific_patch)
        self.assertNotIn("AL-U-T1", labels_with_specific_patch)


if __name__ == "__main__":
    unittest.main()
