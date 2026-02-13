from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

import pandas as pd

import sys

REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
TOOLS_DIR = REPO_ROOT / "repro" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import bias_event_analysis  # noqa: E402


class BiasEventAnalysisTests(unittest.TestCase):
    def test_parse_event_date_sanitized(self) -> None:
        ev = bias_event_analysis.parse_event_date("c2021-11-12")
        self.assertEqual(ev.parsed.isoformat(), "2021-11-12")
        self.assertTrue(ev.sanitized)

    def test_parse_event_date_direct(self) -> None:
        ev = bias_event_analysis.parse_event_date("2021-12-10")
        self.assertEqual(ev.parsed.isoformat(), "2021-12-10")
        self.assertFalse(ev.sanitized)

    def test_event_stats_for_center(self) -> None:
        df = pd.DataFrame(
            {
                "target_date": pd.to_datetime(["2021-01-20", "2021-01-21", "2021-01-22", "2021-01-23", "2021-01-24", "2021-01-25", "2021-01-26"]),
                "center_key": ["NWS_NWM"] * 7,
                "bias_retro_cms": [1, 1, 1, 2, 3, 3, 3],
                "bias_forecast_cms": [2, 2, 2, 3, 4, 4, 4],
                "delta_bias_cms": [1, 1, 1, 1, 1, 1, 1],
            }
        )
        out = bias_event_analysis.event_stats_for_center(df, date(2021, 1, 23), "NWS_NWM", local_days=2)
        self.assertTrue(out["event_row_available"])
        self.assertAlmostEqual(float(out["event_bias_retro_cms"]), 2.0)
        self.assertAlmostEqual(float(out["pre_mean_bias_retro_cms"]), 1.0)
        self.assertAlmostEqual(float(out["post_mean_bias_retro_cms"]), 3.0)
        self.assertAlmostEqual(float(out["post_minus_pre_bias_retro_cms"]), 2.0)


if __name__ == "__main__":
    unittest.main()
