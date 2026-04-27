import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT_PATH = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_exal_discount_probe_comparison.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_exal_discount_probe_comparison",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ExalDiscountProbeComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.rows = cls.module.build_rows()

    def test_expected_profile_count(self):
        profile_keys = {row["profile_key"] for row in self.rows}
        self.assertEqual(
            profile_keys,
            {
                "he2_current_cf1",
                "custom_user_requested_v1",
                "featurecov_ndlm_tight_v1",
                "featurecov_hybrid_midpoint_v1",
                "older_baseline_probe_v1",
            },
        )

    def test_completed_profiles_are_baseline_custom_and_ndlm_tight(self):
        completed = {
            row["profile_key"]
            for row in self.rows
            if row["campaign_state"] in {"completed_reference", "completed"}
        }
        self.assertEqual(
            completed,
            {
                "he2_current_cf1",
                "custom_user_requested_v1",
                "featurecov_ndlm_tight_v1",
            },
        )

    def test_baseline_wins_every_cutoff_against_completed_probes(self):
        by_cutoff: dict[str, list[dict[str, str]]] = {}
        for row in self.rows:
            if row["campaign_state"] not in {"completed_reference", "completed"}:
                continue
            by_cutoff.setdefault(row["cutoff"], []).append(row)
        winners = {}
        for cutoff, rows in by_cutoff.items():
            winners[cutoff] = min(rows, key=lambda item: float(item["probe_crps"]))["profile_key"]
        self.assertEqual(set(winners.values()), {"he2_current_cf1"})

    def test_ndlm_tight_probe_is_worse_in_all_cutoffs(self):
        probe_rows = [
            row for row in self.rows if row["profile_key"] == "featurecov_ndlm_tight_v1"
        ]
        self.assertEqual(len(probe_rows), 5)
        self.assertTrue(all(float(row["delta_vs_he"]) > 0.0 for row in probe_rows))

    def test_custom_probe_has_two_catastrophic_cutoffs(self):
        probe_rows = [
            row for row in self.rows if row["profile_key"] == "custom_user_requested_v1"
        ]
        catastrophic = [row for row in probe_rows if float(row["probe_crps"]) > 1.0e6]
        catastrophic_cutoffs = {row["cutoff"] for row in catastrophic}
        self.assertEqual(catastrophic_cutoffs, {"20211221", "20220511"})


if __name__ == "__main__":
    unittest.main()
