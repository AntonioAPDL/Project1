import importlib.util
from collections import defaultdict
from pathlib import Path
import unittest


SCRIPT_PATH = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_ndlm_input_hash_audit.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_ndlm_input_hash_audit", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NdlmInputHashAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.rows = cls.module.build_rows()

    def test_row_count(self):
        self.assertEqual(len(self.rows), 405)

    def test_all_effective_artifacts_exist(self):
        missing = [row for row in self.rows if row["effective_exists"] != "True"]
        self.assertEqual(missing, [])

    def test_all_group_contracts_are_hash_aligned(self):
        groups = defaultdict(set)
        for row in self.rows:
            key = (row["cutoff"], row["comparison_group"], row["artifact_name"])
            groups[key].add(row["sha256"])
        bad = {key: hashes for key, hashes in groups.items() if len(hashes) != 1}
        self.assertEqual(bad, {})

    def test_some_literal_configured_paths_are_stale(self):
        stale = [row for row in self.rows if row["configured_exists"] == "False"]
        self.assertTrue(stale)

    def test_archived_snapshot_is_primary_effective_source(self):
        archived = [row for row in self.rows if row["effective_path_source"] == "archived_snapshot"]
        self.assertEqual(len(archived), len(self.rows))

    def test_relaunch_row_uses_distinct_paths_but_hash_aligned_inputs(self):
        relaunch = [row for row in self.rows if row["selected_source_lineage"] == "ndlm_relaunch_20260411"]
        self.assertEqual(len(relaunch), 9)
        keys = defaultdict(set)
        for row in self.rows:
            if row["cutoff"] == "20210123" and row["comparison_group"] == "multivar_keep":
                keys[row["artifact_name"]].add(row["sha256"])
        self.assertTrue(all(len(hashes) == 1 for hashes in keys.values()))


if __name__ == "__main__":
    unittest.main()
