import csv
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
INPUT_CSV = ROOT / "data/canonical_gdpc_master/v20260509/intermediate/combined_climate_indices_daily_standardized_19870529_20230122.csv"
SCRIPT = ROOT / "scripts/build_canonical_climate_stationarity_audit.R"


class CanonicalClimateStationarityAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="gdpc_stationarity_audit_"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_stationarity_audit_outputs_exist_and_have_expected_shape(self):
        subprocess.run(
            [
                "Rscript",
                str(SCRIPT),
                "--input-csv",
                str(INPUT_CSV),
                "--output-dir",
                str(self.tmpdir),
                "--window-label",
                "1987-05-29 -> 2023-01-22",
            ],
            check=True,
            env={**os.environ, "LC_ALL": "C.UTF-8"},
        )

        csv_path = self.tmpdir / "stationarity_audit.csv"
        md_path = self.tmpdir / "CANONICAL_GDPC_STATIONARITY_AUDIT.md"

        self.assertTrue(csv_path.exists())
        self.assertTrue(md_path.exists())

        with csv_path.open(newline="") as fh:
            rows = list(csv.DictReader(fh))

        self.assertEqual(len(rows), 17)
        self.assertIn("series", rows[0])
        self.assertIn("stationarity_class", rows[0])
        self.assertIn("slope_per_year", rows[0])

        report = md_path.read_text()
        self.assertIn("Recommendation: keep all 17 standardized daily climate indices in levels", report)


if __name__ == "__main__":
    unittest.main()
