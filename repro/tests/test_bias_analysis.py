from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

import sys

REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
TOOLS_DIR = REPO_ROOT / "repro" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import bias_analysis  # noqa: E402


class BiasAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="bias_analysis_ut_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_select_run_dir_latest_and_explicit(self) -> None:
        cutoff_dir = self.tmpdir / "cutoff_date=2020-01-01"
        run_a = cutoff_dir / "run_id=older"
        run_b = cutoff_dir / "run_id=newer"
        run_a.mkdir(parents=True)
        run_b.mkdir(parents=True)

        os.utime(run_a, (1000, 1000))
        os.utime(run_b, (2000, 2000))

        selected = bias_analysis.select_run_dir(cutoff_dir, selector="latest_mtime", explicit_run_id=None)
        self.assertEqual(selected.name, "run_id=newer")

        selected_explicit = bias_analysis.select_run_dir(
            cutoff_dir,
            selector="explicit",
            explicit_run_id="older",
        )
        self.assertEqual(selected_explicit.name, "run_id=older")

    def test_build_bias_formulas(self) -> None:
        intervals = bias_analysis.parse_intervals([{"start": "2020-01-01", "end": "2020-01-03"}])
        lookup = bias_analysis.build_window_lookup(intervals)
        centers = [
            bias_analysis.CenterSpec(
                key="NWS_NWM",
                label="NWS/NWM",
                retros_col="NWS3.0",
                forecast_file="nws_weighted_daily.csv",
            )
        ]

        retros_wide = pd.DataFrame(
            {
                "date": [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)],
                "usgs_cms": [10.0, 12.0, 14.0],
                "retro_NWS_NWM_cms": [9.0, 11.0, 15.0],
            }
        )

        retro_bias = bias_analysis.build_retro_bias(retros_wide, centers, lookup)
        self.assertEqual(len(retro_bias), 3)
        self.assertAlmostEqual(float(retro_bias.loc[0, "bias_retro_cms"]), 1.0)
        self.assertAlmostEqual(float(retro_bias.loc[2, "bias_retro_cms"]), -1.0)

        forecast_means = pd.DataFrame(
            {
                "issue_date": [date(2019, 12, 31), date(2020, 1, 1), date(2020, 1, 2)],
                "target_date": [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)],
                "lead_days": [1, 1, 1],
                "center_key": ["NWS_NWM", "NWS_NWM", "NWS_NWM"],
                "center_label": ["NWS/NWM", "NWS/NWM", "NWS/NWM"],
                "ensemble_mean_cms": [8.0, 10.0, 13.0],
            }
        )

        forecast_bias = bias_analysis.build_forecast_bias(forecast_means, retros_wide, lookup)
        compare_df = bias_analysis.build_bias_compare(forecast_bias, retro_bias)

        # Bias_forecast = USGS - forecast_mean
        self.assertAlmostEqual(float(compare_df.loc[0, "bias_forecast_cms"]), 2.0)
        self.assertAlmostEqual(float(compare_df.loc[1, "bias_forecast_cms"]), 2.0)
        self.assertAlmostEqual(float(compare_df.loc[2, "bias_forecast_cms"]), 1.0)

        # Delta = Bias_forecast - Bias_retro
        self.assertAlmostEqual(float(compare_df.loc[0, "delta_bias_cms"]), 1.0)
        self.assertAlmostEqual(float(compare_df.loc[1, "delta_bias_cms"]), 1.0)
        self.assertAlmostEqual(float(compare_df.loc[2, "delta_bias_cms"]), 2.0)

    def test_compute_coverage_respects_horizon_eligibility(self) -> None:
        intervals = bias_analysis.parse_intervals([{"start": "2020-01-01", "end": "2020-01-03"}])
        centers = [
            bias_analysis.CenterSpec(
                key="GLOFAS",
                label="GloFAS",
                retros_col="GloFAS",
                forecast_file="glofas_weighted_daily.csv",
            )
        ]

        compare_df = pd.DataFrame(
            {
                "window_id": [intervals[0].window_id],
                "lead_days": [1],
                "center_key": ["GLOFAS"],
                "bias_forecast_cms": [0.5],
                "bias_retro_cms": [0.2],
            }
        )

        cutoff_dates = [date(2019, 12, 31), date(2020, 1, 1)]
        coverage = bias_analysis.compute_coverage(
            compare_df=compare_df,
            cutoff_dates=cutoff_dates,
            centers=centers,
            horizons=[1],
            intervals=intervals,
        )

        self.assertEqual(len(coverage), 1)
        row = coverage.iloc[0]
        # Eligible targets for h=1 are 2020-01-01 and 2020-01-02; 2020-01-03 lacks cutoff 2020-01-02.
        self.assertEqual(int(row["expected_count"]), 2)
        self.assertEqual(int(row["actual_count"]), 1)
        self.assertEqual(int(row["missing_count"]), 1)

    def test_resolve_center_groups_defaults(self) -> None:
        centers = [
            bias_analysis.CenterSpec(
                key="NWS_NWM",
                label="NWS/NWM",
                retros_col="NWS3.0",
                forecast_file="nws_weighted_daily.csv",
            ),
            bias_analysis.CenterSpec(
                key="GLOFAS",
                label="GloFAS",
                retros_col="GloFAS",
                forecast_file="glofas_weighted_daily.csv",
            ),
        ]
        groups = bias_analysis.resolve_center_groups({"center_groups": None}, centers)
        self.assertEqual(groups[0].key, "all")
        self.assertEqual(groups[0].center_keys, ("NWS_NWM", "GLOFAS"))
        group_keys = {g.key for g in groups}
        self.assertIn("nws_nwm", group_keys)
        self.assertIn("glofas", group_keys)

    def test_parse_numeric_limits(self) -> None:
        self.assertEqual(bias_analysis.parse_numeric_limits([-30, 30], "x"), (-30.0, 30.0))
        self.assertIsNone(bias_analysis.parse_numeric_limits(None, "x"))
        with self.assertRaises(ValueError):
            bias_analysis.parse_numeric_limits([30, -30], "x")
        with self.assertRaises(ValueError):
            bias_analysis.parse_numeric_limits([1], "x")


if __name__ == "__main__":
    unittest.main()
