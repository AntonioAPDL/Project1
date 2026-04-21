import importlib.util
from pathlib import Path
import unittest


SCRIPT_PATH = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_ndlm_spec_parity_matrix.py"
)
PHASE2_CSV = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/label_mapping_check.csv"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_ndlm_spec_parity_matrix", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NdlmSpecParityMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.rows = cls.module.build_rows()
        cls.phase2_rows = cls.module.read_csv(PHASE2_CSV)

    def test_row_count(self):
        self.assertEqual(len(self.rows), 45)

    def test_three_rows_per_cutoff_and_group(self):
        counts = {}
        for row in self.rows:
            key = (row["cutoff"], row["comparison_group"])
            counts[key] = counts.get(key, 0) + 1
        self.assertEqual(set(counts.values()), {3})
        self.assertEqual(len(counts), 15)

    def test_ndlm_rows_match_phase2_source_runs(self):
        expected = {
            (row["model_variant"], row["cutoff"]): row["current_selected_source_run"]
            for row in self.phase2_rows
        }
        for row in self.rows:
            if row["model_variant"] not in {"ndlm_univar_keep", "ndlm_main_drop", "ndlm_main_keep"}:
                continue
            self.assertEqual(
                row["selected_source_run"],
                expected[(row["model_variant"], row["cutoff"])],
            )

    def test_all_rows_have_resolved_config_paths(self):
        missing = [row for row in self.rows if not Path(row["resolved_config_path"]).exists()]
        self.assertEqual(missing, [])

    def test_all_rows_share_same_fit_covariate_names(self):
        covariate_sets = {row["fit_covariate_names"] for row in self.rows}
        self.assertEqual(covariate_sets, {"ELI|ONI|PPT|SOIL|PCA"})

    def test_all_authoritative_rows_have_deterministic_climate_disabled(self):
        enabled = [row for row in self.rows if row["deterministic_climate_enabled"] == "True"]
        self.assertEqual(enabled, [])

    def test_featurecov_transfer_blocks_are_absent_in_authoritative_rows(self):
        present = [row for row in self.rows if row["transfer_covariate_base"]]
        self.assertEqual(present, [])

    def test_only_one_row_comes_from_ndlm_relaunch(self):
        relaunch = [row for row in self.rows if row["selected_source_lineage"] == "ndlm_relaunch_20260411"]
        self.assertEqual(len(relaunch), 1)
        self.assertEqual(relaunch[0]["model_variant"], "ndlm_main_keep")
        self.assertEqual(relaunch[0]["cutoff"], "20210123")


if __name__ == "__main__":
    unittest.main()
