import csv
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import scripts.build_glofas_operational_split_plan as split_plan


class GlofasOperationalSplitPlanTests(unittest.TestCase):
    def test_balanced_chunk_sizes(self):
        self.assertEqual(split_plan.balanced_chunk_sizes(1176, 6), [196, 196, 196, 196, 196, 196])
        self.assertEqual(split_plan.balanced_chunk_sizes(10, 3), [4, 3, 3])

    def test_build_splits_preserves_all_issue_dates(self):
        issue_dates = split_plan.enumerate_issue_dates(
            split_plan.clip_intervals(
                [split_plan.Interval(split_plan.parse_ymd("2019-11-05"), split_plan.parse_ymd("2019-11-14"))],
                split_plan.parse_ymd("2019-11-05"),
                split_plan.parse_ymd("2019-11-14"),
            )
        )
        splits = split_plan.build_splits(issue_dates, num_splits=3, smoke_days_per_split=0)
        rebuilt = [d for item in splits for d in item.issue_dates]
        self.assertEqual(rebuilt, issue_dates)
        self.assertEqual([len(item.issue_dates) for item in splits], [4, 3, 3])

    def test_cli_writes_expected_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "plan"
            cmd = [
                "python3",
                "scripts/build_glofas_operational_split_plan.py",
                "--out-dir",
                str(out_dir),
                "--num-splits",
                "6",
            ]
            subprocess.run(cmd, check=True)
            with (out_dir / "split_summary.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 6)
            self.assertEqual(sum(int(row["issue_count"]) for row in rows), 1176)
            metadata = json.loads((out_dir / "plan_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["num_splits"], 6)
            self.assertEqual(metadata["total_issue_dates"], 1176)


if __name__ == "__main__":
    unittest.main()
