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
    REQUIRED_ALIGNMENT_ARTIFACTS,
    build_outputs,
)


class He2BayesianPublicationManifestTests(unittest.TestCase):
    def test_build_outputs_resolves_full_publication_matrix(self) -> None:
        manifest_rows, input_rows, alignment_rows = build_outputs()
        self.assertEqual(len(manifest_rows), 45)
        self.assertEqual(len(input_rows), 45 * len(ARTIFACT_SPECS))
        self.assertEqual(len(alignment_rows), len(CUTOFFS) * len(ARTIFACT_SPECS))
        self.assertEqual(sorted({row["manuscript_label"] for row in manifest_rows}), sorted(FAMILY_TO_LABEL.values()))

    def test_override_row_points_to_exact_discount_grid_winner(self) -> None:
        manifest_rows, _input_rows, _alignment_rows = build_outputs()
        row = next(
            row
            for row in manifest_rows
            if row["cutoff"] == "20221225" and row["manuscript_label"] == "exAL-M-T1"
        )
        self.assertEqual(
            row["run_id"],
            "multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep",
        )
        self.assertEqual(row["crps_display4"], "0.4375")
        self.assertEqual(row["campaign_lineage"], "exalm_t1_discount_grid_exact_20260424:set09_override")
        self.assertTrue(row["replaced_source_run_id"])

    def test_all_rows_share_current_featurecov_contract(self) -> None:
        manifest_rows, _input_rows, alignment_rows = build_outputs()
        for row in manifest_rows:
            self.assertEqual(row["fit_covariate_names"], "PPT|SOIL|PCA")
            self.assertEqual(row["deterministic_climate_enabled"], "True")
            self.assertEqual(row["covariate_features_enabled"], "True")
            self.assertEqual(row["lag_orders"], "1|2|3")
            self.assertEqual(row["include_squares"], "True")
            self.assertEqual(row["include_interaction"], "True")
            self.assertEqual(row["within_cutoff_shared_inputs_aligned"], "True")
        self.assertTrue(
            all(
                row["all_equal"] == "True"
                for row in alignment_rows
                if row["artifact"] in REQUIRED_ALIGNMENT_ARTIFACTS
            )
        )


if __name__ == "__main__":
    unittest.main()
