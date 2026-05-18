from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from audit_he2_bayesian_publication_relaunch_liveness import classify_liveness, normalize_quantile_label


class HE2PublicationRelaunchLivenessAuditTests(unittest.TestCase):
    def test_normalize_quantile_label_accepts_common_forms(self) -> None:
        self.assertEqual(normalize_quantile_label("50"), "50")
        self.assertEqual(normalize_quantile_label("q50"), "50")
        self.assertEqual(normalize_quantile_label("q=0.5"), "50")
        self.assertEqual(normalize_quantile_label("0.35"), "35")

    def test_classify_liveness_marks_health_file_as_complete(self) -> None:
        verdict = classify_liveness(
            stage="fit",
            status="pending",
            process_found=True,
            state="S",
            pcpu=0.0,
            log_age_seconds=4000.0,
            wchar_delta=0,
            write_delta=0,
            health_exists=True,
            rdata_exists=True,
        )
        self.assertEqual(verdict, "submodel_complete")

    def test_classify_liveness_marks_cpu_bound_sampling_as_active(self) -> None:
        verdict = classify_liveness(
            stage="fit",
            status="pending",
            process_found=True,
            state="R",
            pcpu=99.2,
            log_age_seconds=4000.0,
            wchar_delta=0,
            write_delta=0,
            health_exists=False,
            rdata_exists=False,
        )
        self.assertEqual(verdict, "active_cpu_bound")

    def test_classify_liveness_marks_old_idle_pending_run_as_likely_stalled(self) -> None:
        verdict = classify_liveness(
            stage="fit",
            status="pending",
            process_found=True,
            state="S",
            pcpu=0.0,
            log_age_seconds=7200.0,
            wchar_delta=0,
            write_delta=0,
            health_exists=False,
            rdata_exists=False,
        )
        self.assertEqual(verdict, "likely_stalled")


if __name__ == "__main__":
    unittest.main()
