import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT_PATH = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_exal_discount_probe_parity_audit.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_exal_discount_probe_parity_audit",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ExalDiscountProbeParityAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.rows = cls.module.build_rows()

    def test_expected_row_count(self):
        self.assertEqual(len(self.rows), 15)

    def test_probe_pair_is_discount_only_for_all_cutoffs(self):
        probe_rows = [row for row in self.rows if row["pair_key"] == "custom_vs_ndlm_tight"]
        self.assertEqual(len(probe_rows), 5)
        self.assertTrue(all(row["overall_only_discount_difference"] == "True" for row in probe_rows))

    def test_baseline_vs_completed_probes_are_not_discount_only(self):
        baseline_rows = [
            row
            for row in self.rows
            if row["pair_key"] in {"baseline_vs_custom", "baseline_vs_ndlm_tight"}
        ]
        self.assertTrue(all(row["overall_only_discount_difference"] == "False" for row in baseline_rows))

    def test_baseline_vs_probes_have_same_structured_diff_files(self):
        expected = (
            "covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|"
            "covariates/covariate_features.csv|"
            "deterministic_climate/deterministic_precip_future.csv|"
            "deterministic_climate/deterministic_soil_future.csv"
        )
        baseline_rows = [
            row
            for row in self.rows
            if row["pair_key"] in {"baseline_vs_custom", "baseline_vs_ndlm_tight"}
        ]
        self.assertEqual({row["diff_files"] for row in baseline_rows}, {expected})

    def test_baseline_vs_probes_first_feature_diff_starts_at_forecast_window(self):
        baseline_rows = [
            row
            for row in self.rows
            if row["pair_key"] in {"baseline_vs_custom", "baseline_vs_ndlm_tight"}
        ]
        self.assertEqual(
            {row["first_features_diff_date"] for row in baseline_rows},
            {"2021-01-24", "2021-11-13", "2021-12-22", "2022-05-12", "2022-12-26"},
        )


if __name__ == "__main__":
    unittest.main()
