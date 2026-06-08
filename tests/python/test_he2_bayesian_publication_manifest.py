#!/usr/bin/env python3
from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_bayesian_publication_manifest import (  # noqa: E402
    ARTIFACT_SPECS,
    CUTOFFS,
    FAMILY_TO_LABEL,
    PROMOTED_AL_DROP_ROOT,
    PROMOTED_AL_KEEP_ROOT,
    PROMOTED_EXAL_DROP_ROOT,
    PROMOTED_NDLM_ROOT,
    PROMOTED_UNIVAR_AL_EXAL_ROOT,
    PROMOTED_FAMILY_LINEAGES,
    REQUIRED_ALIGNMENT_ARTIFACTS,
    build_outputs,
)
from he2_exdqlm_keep_authoritative import load_authoritative_spec  # noqa: E402


class He2BayesianPublicationManifestTests(unittest.TestCase):
    def test_build_outputs_resolves_full_publication_matrix(self) -> None:
        manifest_rows, input_rows, alignment_rows = build_outputs()
        self.assertEqual(len(manifest_rows), 45)
        self.assertEqual(len(input_rows), 45 * len(ARTIFACT_SPECS))
        self.assertEqual(len(alignment_rows), len(CUTOFFS) * len(ARTIFACT_SPECS))
        self.assertEqual(sorted({row["manuscript_label"] for row in manifest_rows}), sorted(FAMILY_TO_LABEL.values()))

    def test_exal_keep_rows_point_to_authoritative_grid_winners(self) -> None:
        manifest_rows, _input_rows, _alignment_rows = build_outputs()
        authoritative = load_authoritative_spec()
        for winner in authoritative.winners:
            row = next(
                row
                for row in manifest_rows
                if row["cutoff"] == winner.cutoff and row["manuscript_label"] == "exAL-M-T1"
            )
            self.assertEqual(row["run_id"], winner.run_id)
            self.assertAlmostEqual(float(row["crps_exact"]), winner.mean_crps, places=12)
            self.assertEqual(row["campaign_lineage"], "exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner")

    def test_multivar_quantile_rows_point_to_canonical_promoted_roots(self) -> None:
        manifest_rows, _input_rows, _alignment_rows = build_outputs()
        authoritative = load_authoritative_spec()
        winners = authoritative.winner_by_cutoff()
        for cutoff in CUTOFFS:
            winner = winners[cutoff]
            al_keep = next(row for row in manifest_rows if row["cutoff"] == cutoff and row["manuscript_label"] == "AL-M-T1")
            self.assertEqual(al_keep["run_id"], f"multimodel_{cutoff}_v8_he2grid_{winner.grid_spec_id}_dqlm_multivar_al_keep")
            self.assertTrue(al_keep["run_root"].startswith(str(PROMOTED_AL_KEEP_ROOT)))
            self.assertEqual(al_keep["campaign_lineage"], PROMOTED_FAMILY_LINEAGES["dqlm_multivar_al_keep"])
            self.assertEqual(al_keep["likelihood_mode"], "al")
            self.assertEqual(al_keep["forecast_transfer_mode"], "keep")
            self.assertEqual(al_keep["reused_external_pass"], "False")

            exal_drop = next(row for row in manifest_rows if row["cutoff"] == cutoff and row["manuscript_label"] == "exAL-M-T0")
            self.assertEqual(exal_drop["run_id"], f"multimodel_{cutoff}_v8_he2pubgdpc1r1_exdqlm_multivar_drop")
            self.assertTrue(exal_drop["run_root"].startswith(str(PROMOTED_EXAL_DROP_ROOT)))
            self.assertEqual(exal_drop["campaign_lineage"], PROMOTED_FAMILY_LINEAGES["exdqlm_multivar_drop"])
            self.assertEqual(exal_drop["likelihood_mode"], "exal")
            self.assertEqual(exal_drop["forecast_transfer_mode"], "drop")
            self.assertEqual(exal_drop["reused_external_pass"], "False")

            al_drop = next(row for row in manifest_rows if row["cutoff"] == cutoff and row["manuscript_label"] == "AL-M-T0")
            self.assertEqual(al_drop["run_id"], f"multimodel_{cutoff}_v8_he2pubgdpc1r1_dqlm_multivar_al_drop")
            self.assertTrue(al_drop["run_root"].startswith(str(PROMOTED_AL_DROP_ROOT)))
            self.assertEqual(al_drop["campaign_lineage"], PROMOTED_FAMILY_LINEAGES["dqlm_multivar_al_drop"])
            self.assertEqual(al_drop["likelihood_mode"], "al")
            self.assertEqual(al_drop["forecast_transfer_mode"], "drop")
            self.assertEqual(al_drop["reused_external_pass"], "False")

    def test_univar_al_exal_rows_point_to_20260603_promoted_root(self) -> None:
        manifest_rows, _input_rows, _alignment_rows = build_outputs()
        for cutoff in CUTOFFS:
            al = next(row for row in manifest_rows if row["cutoff"] == cutoff and row["manuscript_label"] == "AL-U-T1")
            self.assertEqual(al["run_id"], f"multimodel_{cutoff}_v8_he2pubgdpc1r1_dqlm_univar_al")
            self.assertTrue(al["run_root"].startswith(str(PROMOTED_UNIVAR_AL_EXAL_ROOT)))
            self.assertEqual(al["campaign_lineage"], PROMOTED_FAMILY_LINEAGES["dqlm_univar_al"])
            self.assertEqual(al["likelihood_mode"], "al")
            self.assertEqual(al["reused_external_pass"], "False")

            exal = next(row for row in manifest_rows if row["cutoff"] == cutoff and row["manuscript_label"] == "exAL-U-T1")
            self.assertEqual(exal["run_id"], f"multimodel_{cutoff}_v8_he2pubgdpc1r1_exdqlm_univar")
            self.assertTrue(exal["run_root"].startswith(str(PROMOTED_UNIVAR_AL_EXAL_ROOT)))
            self.assertEqual(exal["campaign_lineage"], PROMOTED_FAMILY_LINEAGES["exdqlm_univar"])
            self.assertEqual(exal["likelihood_mode"], "exal")
            self.assertEqual(exal["reused_external_pass"], "False")

    def test_ndlm_rows_point_to_20260607_promoted_root(self) -> None:
        manifest_rows, _input_rows, _alignment_rows = build_outputs()
        expected = {
            "N-U-T1": ("ndlm_univar_keep", "keep"),
            "N-M-T0": ("ndlm_main_drop", "drop"),
            "N-M-T1": ("ndlm_main_keep", "keep"),
        }
        for cutoff in CUTOFFS:
            for label, (family, transfer_mode) in expected.items():
                row = next(row for row in manifest_rows if row["cutoff"] == cutoff and row["manuscript_label"] == label)
                self.assertEqual(row["run_id"], f"multimodel_{cutoff}_v8_he2pubgdpc1r1_{family}")
                self.assertTrue(row["run_root"].startswith(str(PROMOTED_NDLM_ROOT)))
                self.assertEqual(row["campaign_lineage"], PROMOTED_FAMILY_LINEAGES[family])
                self.assertEqual(row["likelihood_mode"], "normal")
                self.assertEqual(row["forecast_transfer_mode"], transfer_mode)
                self.assertEqual(row["reused_external_pass"], "False")
                self.assertIn("20260607", row["campaign_lineage"])

    def test_all_rows_share_current_featurecov_contract(self) -> None:
        manifest_rows, _input_rows, alignment_rows = build_outputs()
        for row in manifest_rows:
            self.assertEqual(row["fit_covariate_names"], "PPT|SOIL|PCA")
            self.assertEqual(row["deterministic_climate_enabled"], "True")
            self.assertEqual(row["covariate_features_enabled"], "True")
            self.assertEqual(row["lag_orders"], "1|2|3")
            self.assertEqual(row["include_squares"], "True")
            self.assertEqual(row["include_interaction"], "True")
        required = [row for row in alignment_rows if row["artifact"] in REQUIRED_ALIGNMENT_ARTIFACTS]
        self.assertEqual(sum(row["all_equal"] == "True" for row in required), len(CUTOFFS) * len(REQUIRED_ALIGNMENT_ARTIFACTS))
        self.assertEqual(len(required), len(CUTOFFS) * len(REQUIRED_ALIGNMENT_ARTIFACTS))
        self.assertTrue(all(row["within_cutoff_shared_inputs_aligned"] == "True" for row in manifest_rows))


if __name__ == "__main__":
    unittest.main()
