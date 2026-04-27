#!/usr/bin/env python3

from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path


ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
SCRIPT = ROOT / "scripts" / "build_exalm_t1_discount_grid_exact_comparison.py"
CSV_OUT = ROOT / "reports" / "quantile_discount_probe_analysis" / "exalm_t1_discount_grid_exact_vs_he2.csv"


class ExalmT1DiscountGridExactComparisonTest(unittest.TestCase):
    def test_script_builds_expected_comparison_csv(self) -> None:
        subprocess.run(["python3", str(SCRIPT)], check=True)

        with CSV_OUT.open(newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 45)
        self.assertEqual({row["cutoff"] for row in rows}, {"20210123", "20211112", "20211221", "20220511", "20221225"})
        self.assertEqual({row["discount_set"] for row in rows}, {f"set{i:02d}" for i in range(1, 10)})
        self.assertTrue(all(row["baseline_crps"] for row in rows))
        self.assertTrue(all(row["apples_to_apples_contract"] in {"True", "False"} for row in rows))


if __name__ == "__main__":
    unittest.main()
