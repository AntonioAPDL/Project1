import csv
import importlib.util
import sys
import tempfile
from pathlib import Path
import unittest


SCRIPT_PATH = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/validate_nmt1_static_parity.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("validate_nmt1_static_parity", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Nmt1StaticParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_numeric_equivalent_csv_formatting_mismatch_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            left = Path(tmp) / "left.csv"
            right = Path(tmp) / "right.csv"
            self.write_csv(
                left,
                [
                    {"date": "2021-01-01", "flow": "0.0100000000000000"},
                    {"date": "2021-01-02", "flow": "1.2300000000000000"},
                ],
            )
            self.write_csv(
                right,
                [
                    {"date": "2021-01-01", "flow": "0.01"},
                    {"date": "2021-01-02", "flow": "1.23"},
                ],
            )
            status, details = self.module.classify_input_pair(left, right, tol=1e-12)
            self.assertEqual(status, "pass_numeric_equivalent")
            self.assertTrue(details["numeric_equivalent"])
            self.assertGreater(details["text_diff_rows"], 0)
            self.assertLessEqual(details["max_abs_numeric_diff"], 1e-12)

    def test_schema_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            left = Path(tmp) / "left.csv"
            right = Path(tmp) / "right.csv"
            self.write_csv(left, [{"date": "2021-01-01", "flow": "1.0"}])
            self.write_csv(right, [{"date": "2021-01-01", "value": "1.0"}])
            status, details = self.module.classify_input_pair(left, right, tol=1e-12)
            self.assertEqual(status, "fail_numeric_or_schema")
            self.assertFalse(details["header_equal"])

    def test_date_range_mismatch_fails_even_with_equal_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            left = Path(tmp) / "left.csv"
            right = Path(tmp) / "right.csv"
            self.write_csv(left, [{"date": "2021-01-01", "flow": "1.0"}])
            self.write_csv(right, [{"date": "2021-01-02", "flow": "1.0"}])
            status, details = self.module.classify_input_pair(left, right, tol=1e-12)
            self.assertEqual(status, "fail_numeric_or_schema")
            self.assertFalse(details["numeric_equivalent"])

    def test_harmonic_indices_normalize_to_canonical_values(self):
        ndlm_cfg = {
            "models": {
                "ndlm_main": {
                    "seasonality": {
                        "harmonics": [1, 2, 1 / 6.8068493],
                    }
                }
            }
        }
        ex_cfg = {
            "models": {
                "exdqlm_multivar": {
                    "structure": {
                        "enabled_harmonic_indices": [1, 2, 3],
                    }
                }
            }
        }
        left = self.module.normalize_harmonics_from_config(ndlm_cfg, "ndlm_main")
        right = self.module.normalize_harmonics_from_config(ex_cfg, "exdqlm_multivar")
        self.assertTrue(self.module.harmonics_equal(left, right))
        self.assertAlmostEqual(right[2], 0.146910847578189, places=14)

    def test_literal_three_is_not_the_third_harmonic_value(self):
        actual_values_cfg = {
            "models": {
                "ndlm_main": {
                    "seasonality": {
                        "harmonics": [1, 2, 3],
                    }
                }
            }
        }
        indexed_cfg = {
            "models": {
                "exdqlm_multivar": {
                    "structure": {
                        "enabled_harmonic_indices": [1, 2, 3],
                    }
                }
            }
        }
        literal = self.module.normalize_harmonics_from_config(actual_values_cfg, "ndlm_main")
        indexed = self.module.normalize_harmonics_from_config(indexed_cfg, "exdqlm_multivar")
        self.assertFalse(self.module.harmonics_equal(literal, indexed))

    def test_run_root_from_score_path(self):
        path = Path(
            "/tmp/run/post/outputs/run/tables/crps_forecast_per_time.csv"
        )
        self.assertEqual(self.module.run_root_from_score_path(path), Path("/tmp/run"))

    def test_not_comparable_fields_include_exal_latents(self):
        rows = self.module.build_not_comparable_rows()
        fields = {row["field"] for row in rows}
        self.assertIn("s_t", fields)
        self.assertIn("u_t", fields)
        self.assertIn("sigma_gamma_laplace", fields)

    def test_spec_comparison_classifies_discount_difference_as_documented(self):
        rows = [
            {
                "cutoff": "20210123",
                "row_label": "N-M-T1",
                "authority_class": "article_crps_table",
                "field": "state.df_t",
                "parity_class": "documented_difference",
                "value": "0.99999999",
            },
            {
                "cutoff": "20210123",
                "row_label": "exAL-M-T1",
                "authority_class": "article_crps_table",
                "field": "state.df_t",
                "parity_class": "documented_difference",
                "value": "0.9995",
            },
            {
                "cutoff": "20210123",
                "row_label": "exAL-M-T1-retained-current",
                "authority_class": "current_retained_exdqlm_figures",
                "field": "state.df_t",
                "parity_class": "documented_difference",
                "value": "0.9995",
            },
        ]
        out = [
            row
            for row in self.module.compare_specs(rows)
            if row["cutoff"] == "20210123" and row["field"] == "state.df_t"
        ]
        self.assertEqual({row["status"] for row in out}, {"documented_difference"})

    def test_transfer_covariate_normalization_ignores_decorator_fields(self):
        left = {
            "base_covariates": ["PPT", "SOIL", "PCA"],
            "engineered_terms": ["PPT_sq", "SOIL_sq"],
            "mode": "full",
            "scaling": "sd",
        }
        right = {
            "base_covariates": ["PPT", "SOIL", "PCA"],
            "engineered_terms": ["PPT_sq", "SOIL_sq"],
        }
        self.assertEqual(
            self.module.normalized_config_value("inputs.transfer_function_covariates", left),
            self.module.normalized_config_value("inputs.transfer_function_covariates", right),
        )


if __name__ == "__main__":
    unittest.main()
