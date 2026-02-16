from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

import sys

REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
TOOLS_DIR = REPO_ROOT / "repro" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import cutoff_version_pairing as mod  # noqa: E402


class CutoffVersionPairingTests(unittest.TestCase):
    def test_parse_cutoff_date_strict(self) -> None:
        self.assertEqual(mod.parse_cutoff_date("2025-12-25"), date(2025, 12, 25))
        with self.assertRaises(ValueError):
            mod.parse_cutoff_date("2025/12/25")

    def test_nws_resolve_known_recent_cutoff(self) -> None:
        out = mod.resolve_nws_nwm(date(2025, 12, 25))
        self.assertEqual(out.forecast_version, "3.0")
        self.assertEqual(out.retrospective_version, "3.0")
        self.assertEqual(out.decision, "conditional")
        self.assertEqual(out.recommended_strategy, "same_version_with_gap_reporting")
        self.assertEqual(out.recommended_bias_training_version, "3.0")
        self.assertTrue(any("release dates" in note for note in out.notes))

    def test_nws_resolve_early_cutoff_without_retro(self) -> None:
        out = mod.resolve_nws_nwm(date(2017, 1, 1))
        self.assertEqual(out.forecast_version, "1.0")
        self.assertEqual(out.retrospective_version, mod.NOT_FOUND)
        self.assertEqual(out.decision, "ambiguous")
        self.assertEqual(out.recommended_strategy, "hold_for_metadata_review")

    def test_glofas_partial_exact_match(self) -> None:
        out = mod.resolve_glofas(date(2020, 1, 10))
        self.assertEqual(out.forecast_version, "2.1")
        self.assertEqual(out.retrospective_version, "2.1")
        self.assertEqual(out.reforecast_version, mod.NOT_FOUND)
        self.assertEqual(out.decision, "conditional")
        self.assertEqual(out.recommended_strategy, "exact_historical_plus_nearest_reforecast")
        self.assertEqual(out.recommended_bias_training_version, "2.1")
        self.assertEqual(out.recommended_reforecast_version, "2.2")

    def test_glofas_3x_ambiguous_uses_nearest_shared_anchor(self) -> None:
        out = mod.resolve_glofas(date(2022, 12, 25))
        self.assertEqual(out.forecast_version, "3.4")
        self.assertEqual(out.decision, "ambiguous")
        self.assertEqual(out.recommended_strategy, "nearest_shared_anchor")
        self.assertEqual(out.recommended_bias_training_version, "3.1")
        self.assertEqual(out.recommended_reforecast_version, "3.1")

    def test_glofas_recent_ambiguous_4x(self) -> None:
        out = mod.resolve_glofas(date(2025, 12, 25))
        self.assertEqual(out.forecast_version, "4.4")
        self.assertEqual(out.retrospective_version, mod.NOT_FOUND)
        self.assertEqual(out.reforecast_version, mod.NOT_FOUND)
        self.assertEqual(out.decision, "ambiguous")
        self.assertEqual(out.recommended_strategy, "nearest_shared_anchor")
        self.assertEqual(out.recommended_bias_training_version, "4.0")
        self.assertEqual(out.recommended_reforecast_version, "4.0")
        self.assertTrue(any("temporary freeze" in note for note in out.notes))

    def test_build_report_and_text_output(self) -> None:
        report = mod.build_report(date(2025, 12, 25))
        self.assertEqual(report["cutoff_date"], "2025-12-25")
        self.assertEqual(len(report["results"]), 2)

        text = mod.render_text(report)
        self.assertIn("Center: NWS/NWM", text)
        self.assertIn("Center: GloFAS", text)
        self.assertIn("Recommended strategy", text)


if __name__ == "__main__":
    unittest.main()
