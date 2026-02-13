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

import nws_version_bias_event_analysis as mod  # noqa: E402


class NWSVersionBiasEventTests(unittest.TestCase):
    def test_parse_version_windows_and_lookup(self) -> None:
        windows = mod.parse_version_windows(
            [
                {"version": "NWS2.0", "start": "2019-06-19", "end": "2019-11-24", "source_key": "S"},
                {"version": "NWS2.1", "start": "2019-11-25", "end": "2023-09-19", "source_key": "S"},
            ]
        )
        self.assertEqual(windows[0].version, "NWS2.0")
        self.assertEqual(windows[1].version, "NWS2.1")

        self.assertEqual(mod.version_for_date(date(2019, 11, 24), windows).version, "NWS2.0")
        self.assertEqual(mod.version_for_date(date(2019, 11, 25), windows).version, "NWS2.1")
        self.assertIsNone(mod.version_for_date(date(2019, 1, 1), windows))

    def test_parse_version_windows_overlap_error(self) -> None:
        with self.assertRaises(ValueError):
            mod.parse_version_windows(
                [
                    {"version": "a", "start": "2020-01-01", "end": "2020-01-10", "source_key": "S"},
                    {"version": "b", "start": "2020-01-10", "end": "2020-02-01", "source_key": "S"},
                ]
            )

    def test_parse_version_windows_overlap_allowed(self) -> None:
        windows = mod.parse_version_windows(
            [
                {"version": "NWS2.1", "start": "1979-02-01", "end": "2020-12-31", "source_key": "old"},
                {"version": "NWS3.0", "start": "1979-02-01", "end": "2023-02-01", "source_key": "new"},
            ],
            allow_overlap=True,
        )
        self.assertEqual(len(windows), 2)
        self.assertEqual({w.version for w in windows}, {"NWS2.1", "NWS3.0"})

    def test_build_bias_compare_by_version(self) -> None:
        windows = mod.parse_version_windows(
            [
                {"version": "NWS2.1", "start": "2021-01-01", "end": "2021-12-31", "source_key": "S1"},
                {"version": "NWS3.0", "start": "2022-01-01", "end": None, "source_key": "S2"},
            ]
        )

        forecast_bias = pd.DataFrame(
            {
                "issue_date": [date(2021, 1, 1), date(2022, 1, 1)],
                "target_date": [date(2021, 1, 2), date(2022, 1, 2)],
                "lead_days": [1, 1],
                "center_key": ["NWS_NWM", "NWS_NWM"],
                "center_label": ["NWS/NWM", "NWS/NWM"],
                "ensemble_mean_cms": [9.0, 11.0],
                "usgs_cms": [10.0, 12.0],
                "bias_forecast_cms": [1.0, 1.0],
            }
        )
        canonical = pd.DataFrame({"date": [date(2021, 1, 2), date(2022, 1, 2)], "usgs_cms": [10.0, 12.0]})
        sources = {
            "S1": pd.DataFrame({"date": [date(2021, 1, 2)], "retro_log1p": [8.0], "retro_cms": [0.0]}),
            "S2": pd.DataFrame({"date": [date(2022, 1, 2)], "retro_log1p": [10.5], "retro_cms": [0.0]}),
        }

        out = mod.build_bias_compare_by_version(forecast_bias, canonical, windows, sources)
        self.assertEqual(len(out), 2)

        a = out[out["nws_version"] == "NWS2.1"].iloc[0]
        self.assertAlmostEqual(float(a["bias_retro_cms"]), 2.0)
        self.assertAlmostEqual(float(a["delta_bias_cms"]), -1.0)

        b = out[out["nws_version"] == "NWS3.0"].iloc[0]
        self.assertAlmostEqual(float(b["bias_retro_cms"]), 1.5)
        self.assertAlmostEqual(float(b["delta_bias_cms"]), -0.5)


if __name__ == "__main__":
    unittest.main()
