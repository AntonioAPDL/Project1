import importlib.util
from pathlib import Path
import unittest


SCRIPT_PATH = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_ndlm_label_mapping_check.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_ndlm_label_mapping_check", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NdlmLabelMappingCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.rows = cls.module.build_rows()

    def test_row_count(self):
        self.assertEqual(len(self.rows), 15)

    def test_all_manuscript_values_match_corrected_rerun_to_table_precision(self):
        mismatches = [
            row
            for row in self.rows
            if str(row["manuscript_matches_corrected_rerun_4dp"]) != "True"
        ]
        self.assertEqual(mismatches, [])

    def test_univar_rows_are_fixed_baseline(self):
        univar_rows = [row for row in self.rows if row["model_variant"] == "ndlm_univar_keep"]
        self.assertEqual(len(univar_rows), 5)
        self.assertTrue(all(row["current_selection_class"] == "fixed_baseline" for row in univar_rows))
        self.assertTrue(all(row["current_selected_source_lineage"] == "baseline_tt" for row in univar_rows))

    def test_only_20210123_keep_row_comes_from_ndlm_relaunch(self):
        relaunch_rows = [
            row for row in self.rows if row["current_selected_source_lineage"] == "ndlm_relaunch_20260411"
        ]
        self.assertEqual(len(relaunch_rows), 1)
        row = relaunch_rows[0]
        self.assertEqual(row["manuscript_label"], "N-M-T1")
        self.assertEqual(row["cutoff"], "20210123")

    def test_old_packaged_manifest_is_stale_for_twelve_cells(self):
        stale = [
            row
            for row in self.rows
            if row["old_packaged_best9_value"] != ""
            and str(row["old_packaged_matches_current_summary_4dp"]) != "True"
        ]
        self.assertEqual(len(stale), 12)


if __name__ == "__main__":
    unittest.main()
