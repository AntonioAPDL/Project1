import importlib.util
from pathlib import Path
import unittest


SCRIPT_PATH = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_ndlm_wishart_prior_audit.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_ndlm_wishart_prior_audit", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NdlmWishartPriorAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.rows = cls.module.build_rows()

    def test_row_count(self):
        self.assertEqual(len(self.rows), 10)

    def test_all_rows_are_theory_aligned(self):
        bad = [row for row in self.rows if row["runtime_implementation_mode"] != "theory_aligned"]
        self.assertEqual(bad, [])

    def test_all_rows_use_terminal_q_hist_anchor(self):
        bad = [row for row in self.rows if row["runtime_anchor_mode"] != "terminal_Q_hist"]
        self.assertEqual(bad, [])

    def test_all_rows_fall_back_to_default_epsilon0(self):
        bad = [row for row in self.rows if row["runtime_uses_default_epsilon0"] != "True"]
        self.assertEqual(bad, [])

    def test_dof_offset_and_scale_mult_are_used_in_active_fit_code(self):
        self.assertTrue(all(row["code_uses_c_factor"] == "True" for row in self.rows))
        self.assertTrue(all(row["code_uses_epsilon0"] == "True" for row in self.rows))
        self.assertTrue(all(row["code_uses_jitter"] == "True" for row in self.rows))
        self.assertTrue(all(row["code_uses_dof_offset"] == "True" for row in self.rows))
        self.assertTrue(all(row["code_uses_scale_mult"] == "True" for row in self.rows))

    def test_all_rows_have_fit_contract_artifacts(self):
        relaunch = [row for row in self.rows if row["selected_source_lineage"] == "ndlm_relaunch_20260411"]
        baseline = [row for row in self.rows if row["selected_source_lineage"] == "baseline_20260402"]
        self.assertEqual(len(relaunch), 1)
        self.assertEqual(relaunch[0]["contract_check_exists"], "True")
        self.assertEqual(relaunch[0]["fit_diag_exists"], "True")
        self.assertTrue(all(row["contract_check_exists"] == "True" for row in baseline))
        self.assertTrue(all(row["fit_diag_exists"] == "True" for row in self.rows))


if __name__ == "__main__":
    unittest.main()
