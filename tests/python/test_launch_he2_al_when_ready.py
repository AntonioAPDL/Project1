from __future__ import annotations

import unittest

from scripts.launch_he2_al_when_ready import validation_status


class LaunchHe2AlWhenReadyTests(unittest.TestCase):
    def test_validation_status_accepts_passed_and_skipped_smokes(self) -> None:
        summary = {
            "checks": {"smoke_runs": {"count": 3, "passed": 2, "skipped": 1}},
            "smoke_runs": [
                {"scope": "fit_quantile", "family": "a", "cutoff": "20210123", "status": "passed"},
                {"scope": "cutoff", "family": "a", "cutoff": "20211112", "status": "passed"},
                {"scope": "family", "family": "a", "cutoff": "", "status": "skipped"},
            ],
        }
        ok, detail = validation_status(summary)
        self.assertTrue(ok)
        self.assertEqual(detail, "passed")

    def test_validation_status_rejects_failed_smokes(self) -> None:
        summary = {
            "checks": {"smoke_runs": {"count": 1, "passed": 0, "skipped": 0}},
            "smoke_runs": [
                {"scope": "fit_quantile", "family": "a", "cutoff": "20210123", "status": "failed"},
            ],
        }
        ok, detail = validation_status(summary)
        self.assertFalse(ok)
        self.assertIn("failed", detail)

    def test_validation_status_rejects_inconsistent_counts(self) -> None:
        summary = {
            "checks": {"smoke_runs": {"count": 3, "passed": 2, "skipped": 0}},
            "smoke_runs": [
                {"scope": "fit_quantile", "family": "a", "cutoff": "20210123", "status": "passed"},
                {"scope": "cutoff", "family": "a", "cutoff": "20211112", "status": "passed"},
                {"scope": "family", "family": "a", "cutoff": "", "status": "skipped"},
            ],
        }
        ok, detail = validation_status(summary)
        self.assertFalse(ok)
        self.assertIn("mismatch", detail)


if __name__ == "__main__":
    unittest.main()
