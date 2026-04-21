import importlib.util
from pathlib import Path
import unittest


SCRIPT_PATH = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_ndlm_covariate_contract_audit.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_ndlm_covariate_contract_audit",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NdlmCovariateContractAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.rows = cls.module.build_rows()

    def test_row_count(self):
        self.assertEqual(len(self.rows), 45)

    def test_every_row_has_reference_config(self):
        missing = [
            row for row in self.rows if not Path(row["reference_featurecov_config_path"]).exists()
        ]
        self.assertEqual(missing, [])

    def test_reference_contract_is_featurecov_for_all_rows(self):
        reference_classes = {row["reference_contract_class"] for row in self.rows}
        self.assertEqual(reference_classes, {"featurecov_engineered_blended"})

    def test_authoritative_rows_use_legacy_base_covariate_contract(self):
        authoritative_classes = {row["authoritative_contract_class"] for row in self.rows}
        self.assertEqual(authoritative_classes, {"legacy_base_covariates"})

    def test_all_authoritative_rows_use_old_five_covariates(self):
        covariate_sets = {row["authoritative_fit_covariate_names"] for row in self.rows}
        self.assertEqual(covariate_sets, {"ELI|ONI|PPT|SOIL|PCA"})

    def test_all_reference_rows_expect_reduced_featurecov_covariates(self):
        covariate_sets = {row["reference_fit_covariate_names"] for row in self.rows}
        self.assertEqual(covariate_sets, {"PPT|SOIL|PCA"})

    def test_no_authoritative_row_has_engineered_covariate_runtime_artifacts(self):
        present = [
            row
            for row in self.rows
            if row["authoritative_covariate_features_runtime_present"] == "True"
        ]
        self.assertEqual(present, [])

    def test_no_authoritative_row_has_deterministic_climate_runtime_artifacts(self):
        present = [
            row
            for row in self.rows
            if row["authoritative_deterministic_climate_runtime_present"] == "True"
        ]
        self.assertEqual(present, [])

    def test_transfer_mode_semantics_remain_aligned(self):
        mismatched = [
            row for row in self.rows if row["transfer_mode_match_reference"] != "True"
        ]
        self.assertEqual(mismatched, [])

    def test_no_row_matches_full_featurecov_contract(self):
        matches = [
            row for row in self.rows if row["overall_featurecov_contract_match"] == "True"
        ]
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
