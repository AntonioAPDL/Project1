from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

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
                    fieldnames=["order_index", "cutoff", "grid_spec_id", "epsilon", "lane", "run_id", "active_quantiles"],
                )
                writer.writeheader()
                writer.writerow({
                    "order_index": "1",
                    "cutoff": "20210123",
                    "grid_spec_id": "c01_eps365",
                    "epsilon": "365",
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
                    "[gamsig_rollback] p0=0.05 iter=3 reason=guard_triggered detail=incoherent gamma/sigma moments",
                    "[latent_parameter_guard] p0=0.05 bad_psi=0/1 bad_chi=12/100 action=clamp_to_floor",
                    "[state_guard] p0=0.05 iter=4",
                    "[pseudodata_guard] p0=0.05 iter=5 scope=history metric=FFF max_abs=1200",
                    "[pseudodata_guard_fail] p0=0.05 iter=5",
                    "[gamsig_near_zero_fallback] p0=0.05 context=vb_main iter=6 j=3 status=near_zero_sigma_only_fallback anchor=full_candidate gamma_hat=0.01 threshold=0.05",
                    "[gamsig_progress] p0=0.05 iter=7 elbo=-12.3 crit_elbo=0.01 sigma_exp=0.4 gamma_exp=-0.2 state_norm_sq=100 gamsig_update_iters=3 near_zero_fallback_count=1 frozen=false",
                ]) + "\n",
                encoding="utf-8",
            )
            (artifact_root / "runs" / run_id / "run_manifest.yaml").write_text(
                yaml.safe_dump({"rdata_cleanup": {"after_post": {"before": 1, "removed": 1, "remaining": 0}}}),
                encoding="utf-8",
            )

            rows = monitor.build_snapshot_rows(artifact_root, matrix_dir, data_start="1987-05-29")
            q05 = next(row for row in rows if row["q"] == "q05")
            self.assertEqual(q05["grid_spec_id"], "c01_eps365")
            self.assertEqual(q05["epsilon_label"], "365")
            self.assertEqual(q05["iter"], "7")
            self.assertEqual(q05["elbo"], "-12.3")
            self.assertEqual(q05["guard_count"], 3)
            self.assertEqual(q05["gamsig_rollback_count"], 1)
            self.assertEqual(q05["latent_parameter_guard_count"], 1)
            self.assertEqual(q05["pseudodata_guard_event_count"], 1)
            self.assertEqual(q05["pseudodata_guard_fail_count"], 1)
            self.assertEqual(q05["pseudodata_guard_total_count"], 2)
            self.assertEqual(q05["near_zero_fallback_count"], 1)
            self.assertEqual(q05["near_zero_fallback_log_count"], 1)
            self.assertEqual(q05["output_state"], "fit_or_post_pending")
            self.assertEqual(q05["rdata_cleanup_after_post_remaining"], 0)
            self.assertEqual(q05["failure_layer"], "pseudodata")
            expected_scaled = 100.0 / monitor.history_length("20210123")
            expected_sqrt_scaled = 10.0 / monitor.history_length("20210123")
            self.assertAlmostEqual(float(q05["state_norm_sq_per_history_day"]), expected_scaled)
            self.assertAlmostEqual(float(q05["sqrt_state_norm_over_history_len"]), expected_sqrt_scaled)

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
            self.assertIn("sqrt(state)/T", latest_text)
            self.assertIn("state/T", latest_text)
            self.assertIn("| cutoff | spec | q |", latest_text)
            self.assertIn("c01_eps365", latest_text)
            self.assertIn("latent", latest_text)
            self.assertIn("q05", latest_text)


if __name__ == "__main__":
    unittest.main()
