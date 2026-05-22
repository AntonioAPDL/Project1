from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import monitor_he2_exdqlm_multivar_keep_allcutoffs as monitor


class HE2ExDQLMKeepAllCutoffMonitorTests(unittest.TestCase):
    def test_history_length_matches_full_history_cutoff_contract(self) -> None:
        self.assertEqual(monitor.history_length("20221225"), 12995)
        self.assertEqual(monitor.history_length("2021-01-23"), 12294)

    def test_parse_quantiles_accepts_manifest_pipe_and_numeric_forms(self) -> None:
        self.assertEqual(monitor.parse_quantiles("05|20|95"), ["05", "20", "95"])
        self.assertEqual(monitor.parse_quantiles("0.05,0.5,0.95"), ["05", "50", "95"])

    def test_snapshot_reads_progress_and_scales_state_norm_by_history_length(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_root = root / "artifact"
            matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
            run_id = "multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep"
            q_root = artifact_root / "runs" / run_id / "fit" / "exdqlm_multivar" / "keep" / "q=05"
            q_root.joinpath("logs").mkdir(parents=True)
            q_root.joinpath("outputs").mkdir(parents=True)
            matrix_dir.mkdir(parents=True)

            with (matrix_dir / "matrix_plan.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["order_index", "cutoff", "lane", "run_id", "active_quantiles"],
                )
                writer.writeheader()
                writer.writerow({
                    "order_index": "1",
                    "cutoff": "20210123",
                    "lane": "exdqlm_multivar_keep",
                    "run_id": run_id,
                    "active_quantiles": "05|50",
                })
            with (matrix_dir / "matrix_status.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["run_id", "phase", "status"])
                writer.writeheader()
                writer.writerow({"run_id": run_id, "phase": "fit", "status": "pending"})

            q_root.joinpath("logs", "fit.log").write_text(
                "\n".join([
                    "[gamsig_guard] p0=0.05 iter=3",
                    "[state_guard] p0=0.05 iter=4",
                    "[pseudodata_guard_fail] p0=0.05 iter=5",
                    "[gamsig_progress] p0=0.05 iter=7 elbo=-12.3 crit_elbo=0.01 sigma_exp=0.4 gamma_exp=-0.2 state_norm_sq=100 gamsig_update_iters=3 frozen=false",
                ]) + "\n",
                encoding="utf-8",
            )

            rows = monitor.build_snapshot_rows(artifact_root, matrix_dir, data_start="1987-05-29")
            q05 = next(row for row in rows if row["q"] == "q05")
            self.assertEqual(q05["iter"], "7")
            self.assertEqual(q05["elbo"], "-12.3")
            self.assertEqual(q05["guard_count"], 2)
            self.assertEqual(q05["pseudodata_guard_fail_count"], 1)
            expected_scaled = 100.0 / monitor.history_length("20210123")
            self.assertAlmostEqual(float(q05["state_norm_sq_per_history_day"]), expected_scaled)

            out_dir = root / "monitor_out"
            rc = monitor.main([
                "--artifact-root", str(artifact_root),
                "--matrix-dir", str(matrix_dir),
                "--out-dir", str(out_dir),
                "--once",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue((out_dir / "LIVE_STATUS.md").exists())
            self.assertTrue((out_dir / "live_status_latest.csv").exists())
            latest_text = (out_dir / "LIVE_STATUS.md").read_text(encoding="utf-8")
            self.assertIn("state/T", latest_text)
            self.assertIn("q05", latest_text)


if __name__ == "__main__":
    unittest.main()
