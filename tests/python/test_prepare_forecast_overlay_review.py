import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from prepare_forecast_overlay_review import SeriesSpec, maybe_stage_series, validate_series  # noqa: E402


class ForecastOverlayReviewTests(unittest.TestCase):
    def test_validate_series_accepts_valid_csv(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "prism.csv"
            pd.DataFrame(
                {
                    "Date": ["2023-01-20", "2023-01-24"],
                    "PRCP_mm": [1.0, 2.0],
                }
            ).to_csv(p, index=False)
            meta = validate_series(p, value_column="PRCP_mm", min_required_date=date(2023, 1, 24))
            self.assertEqual(meta["rows"], 2)
            self.assertEqual(meta["max_date"], "2023-01-24")

    def test_maybe_stage_series_copies_missing_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "source.csv"
            dst = Path(td) / "nested" / "canonical.csv"
            pd.DataFrame(
                {
                    "Date": ["2023-01-20", "2023-01-24"],
                    "Daily_Avg_Soil_Moisture": [0.2, 0.3],
                }
            ).to_csv(src, index=False)
            spec = SeriesSpec(
                name="era5_soil",
                canonical_csv=dst,
                reuse_source_csv=src,
                value_column="Daily_Avg_Soil_Moisture",
                min_required_date=date(2023, 1, 24),
            )
            result = maybe_stage_series(spec, force_restage=False, dry_run=False)
            self.assertTrue(dst.exists())
            self.assertTrue(result["copied"])
            self.assertEqual(result["canonical"]["max_date"], "2023-01-24")


if __name__ == "__main__":
    unittest.main()

