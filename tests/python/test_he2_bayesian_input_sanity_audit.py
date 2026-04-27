#!/usr/bin/env python3
from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_bayesian_input_sanity_audit import (  # noqa: E402
    ARTIFACT_SPECS,
    CUTOFFS,
    MODEL_ORDER,
    build_rows,
)


class He2BayesianInputSanityAuditTests(unittest.TestCase):
    def test_build_rows_resolves_full_current_he2_matrix(self) -> None:
        rows = build_rows()
        self.assertEqual(len(rows), 45)
        observed_cutoffs = sorted({row["cutoff"] for row in rows})
        observed_families = sorted({row["family"] for row in rows})
        self.assertEqual(observed_cutoffs, sorted(CUTOFFS))
        self.assertEqual(observed_families, sorted(MODEL_ORDER))

    def test_artifact_contract_covers_expected_shared_inputs(self) -> None:
        observed = [name for name, _ in ARTIFACT_SPECS]
        self.assertEqual(
            observed,
            [
                "parameters",
                "retros",
                "nws_forecast",
                "glofas_forecast",
                "cov_01_PPT",
                "cov_02_SOIL",
                "cov_03_PCA",
                "covariate_features",
                "deterministic_precip_future",
                "deterministic_soil_future",
            ],
        )


if __name__ == "__main__":
    unittest.main()
