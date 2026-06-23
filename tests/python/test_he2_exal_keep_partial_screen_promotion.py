import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

import sys

sys.path.insert(0, str(ROOT / "scripts"))

from validate_he2_exal_keep_partial_screen_promotion import (  # noqa: E402
    DEFAULT_OVERLAY,
    SELECTED_LINEAGE_PREFIXES,
    partial_replacements,
)

PARTIAL_AUTHORITY_TEMPLATE = (
    ROOT
    / "config"
    / "he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml"
)


class PartialScreenPromotionTests(unittest.TestCase):
    def test_overlay_has_exact_selected_exal_keep_replacements(self) -> None:
        rows = partial_replacements(DEFAULT_OVERLAY)
        self.assertEqual({row["cutoff"] for row in rows}, {"20211221", "20220511", "20221225"})
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["family"], "exdqlm_multivar_keep")
            self.assertEqual(row["manuscript_label"], "exAL-M-T1")
            self.assertTrue(any(str(row["campaign_lineage"]).startswith(prefix) for prefix in SELECTED_LINEAGE_PREFIXES))
            self.assertIn("crps_improvement", row["replacement_reason"])
            self.assertTrue(str(row["run_root"]).endswith(row["run_id"]))

    def test_current_overlay_preserves_table1_repair_rows(self) -> None:
        payload = yaml.safe_load(DEFAULT_OVERLAY.read_text(encoding="utf-8"))
        replacements = payload["replacements"]
        table1 = [
            row
            for row in replacements
            if str(row.get("campaign_lineage", payload["campaign_lineage"])).startswith(
                "he2_table1_targeted_repair_20260612:"
            )
        ]
        selected = [
            row
            for row in replacements
            if any(str(row.get("campaign_lineage", "")).startswith(prefix) for prefix in SELECTED_LINEAGE_PREFIXES)
        ]
        self.assertEqual(len(replacements), 19)
        self.assertEqual(len(table1), 16)
        self.assertEqual(len(selected), 3)

    def test_partial_authority_refresh_template_targets_only_promoted_rows(self) -> None:
        payload = yaml.safe_load(PARTIAL_AUTHORITY_TEMPLATE.read_text(encoding="utf-8"))
        expected_cutoffs = ["20211221", "20220511", "20221225"]
        self.assertEqual(payload["campaign"]["cutoffs"], expected_cutoffs)
        self.assertEqual(payload["selection"]["cutoffs"], expected_cutoffs)
        self.assertEqual(payload["campaign"]["families"], ["exdqlm_multivar_keep"])
        self.assertEqual(payload["selection"]["families"], ["exdqlm_multivar_keep"])
        self.assertEqual(payload["selection"]["manuscript_labels"], ["exAL-M-T1"])
        self.assertTrue(str(payload["campaign"]["artifact_root"]).endswith("partial_authority_refresh_20260623"))
        self.assertTrue(payload["grid"]["cleanup_rdata_after_post"])
        self.assertFalse(payload["grid"]["allow_run_failures"])
        self.assertEqual(payload["queue"]["ordinary_max_concurrent"], 3)
        self.assertEqual(payload["resources"]["fit_parallel_workers"], 7)
        self.assertEqual(payload["resources"]["mc_cores"], 7)


if __name__ == "__main__":
    unittest.main()
