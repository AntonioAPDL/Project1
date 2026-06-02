from __future__ import annotations

import csv
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from he2_exdqlm_keep_authoritative import (  # noqa: E402
    EXPECTED_CUTOFFS,
    REQUIRED_OUTPUT_FILES,
    iter_runtime_checks,
    load_authoritative_spec,
)


class HE2ExDQLMKeepAuthoritativeTests(unittest.TestCase):
    def test_manifest_covers_five_ordered_winners(self) -> None:
        spec = load_authoritative_spec()
        self.assertEqual([winner.cutoff for winner in spec.winners], EXPECTED_CUTOFFS)
        self.assertEqual(spec.model_family, "exdqlm_multivar_keep")
        self.assertEqual(spec.manuscript_label, "exAL-M-T1")
        self.assertEqual(spec.model_id, "exdqlm_multivar_synth_keep")
        self.assertEqual(spec.score_scale, "log_cms_plus1")

    def test_runtime_outputs_and_crps_match_manifest(self) -> None:
        spec = load_authoritative_spec()
        failures = [row for row in iter_runtime_checks(spec) if row["status"] != "pass"]
        self.assertEqual(failures, [])
        for winner in spec.winners:
            self.assertEqual(len(spec.required_output_paths(winner)), len(REQUIRED_OUTPUT_FILES))
            self.assertEqual(spec.rdata_files(winner), [])
            row = spec.selected_crps_row(winner)
            self.assertAlmostEqual(float(row["mean_crps"]), winner.mean_crps, places=12)

    def test_built_authoritative_matrix_exists_and_has_five_rows(self) -> None:
        spec = load_authoritative_spec()
        matrix = spec.runtime_root / "control" / "authoritative_winner_matrix" / "matrix_plan.csv"
        self.assertTrue(matrix.exists(), matrix)
        with matrix.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 5)
        self.assertEqual([row["cutoff"] for row in rows], EXPECTED_CUTOFFS)
        self.assertTrue(all(row["frozen_config_path"] for row in rows))


if __name__ == "__main__":
    unittest.main()
