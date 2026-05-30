from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_he2_exdqlm_multivar_keep_grid_smoke_matrix as smoke  # noqa: E402
import evaluate_he2_exdqlm_multivar_keep_grid as evaluator  # noqa: E402
from multimodel_v8_lib import runs_dir  # noqa: E402


class HE2ExDQLMKeepGridNextStepsTests(unittest.TestCase):
    def test_smoke_builder_memory_gate_defaults_match_runbook(self) -> None:
        args = smoke.parse_args([])
        self.assertEqual(float(args.pause_mem_gb), 80.0)
        self.assertEqual(float(args.launch_mem_gb), 120.0)
        self.assertEqual(float(args.heavy_mem_gb), 120.0)

    def test_smoke_rewrite_config_moves_run_to_smoke_root(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="keep_grid_smoke_test_"))
        try:
            source_cfg = td / "source.yaml"
            source_cfg.write_text(
                yaml.safe_dump(
                    {
                        "run": {"run_id": "old", "run_root": "/old/runs"},
                        "fit": {"quantiles": [0.05, 0.5, 0.95]},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            artifact_root = td / "artifact"
            config_path = artifact_root / "control/generated_configs/new.yaml"
            cfg = smoke.rewrite_config(
                source_cfg,
                artifact_root=artifact_root,
                run_id="new_run",
                config_path=config_path,
                tag="smoke",
                source_run_id="source_run",
                source_grid_spec_id="c01_eps365",
            )
            self.assertEqual(cfg["run"]["run_id"], "new_run")
            self.assertEqual(cfg["run"]["run_root"], str(runs_dir(artifact_root)))
            self.assertEqual(cfg["run"]["resolved_run_root"], str(runs_dir(artifact_root) / "new_run"))
            self.assertEqual(cfg["run"]["resolved_config_path"], str(config_path))
            self.assertEqual(cfg["debug_he2_exdqlm_keep_grid_smoke"]["source_grid_spec_id"], "c01_eps365")
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_grid_evaluator_selects_only_eligible_lowest_crps_spec(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="keep_grid_eval_test_"))
        try:
            artifact_root = td / "artifact"
            matrix_dir = artifact_root / "control/publication_relaunch_matrix"
            matrix_dir.mkdir(parents=True)
            plan = pd.DataFrame(
                [
                    {
                        "order_index": 1,
                        "cutoff": "20211112",
                        "grid_spec_id": "c01_eps365",
                        "discount_case_id": "c01",
                        "epsilon_value": 365,
                        "forecast_cov_epsilon": 365,
                        "c_factor": 1,
                        "df_t": 0.9999,
                        "df_s1": 0.9995,
                        "df_s2": 0.9995,
                        "df_s67": 0.9999,
                        "df_discrep": 0.999,
                        "lambda": 0.97,
                        "df_trans": 0.9999999,
                        "df_covs": 0.9999999,
                        "lane": "exdqlm_multivar_keep",
                        "run_id": "run_good",
                        "config_path": "/tmp/good.yaml",
                    },
                    {
                        "order_index": 2,
                        "cutoff": "20211112",
                        "grid_spec_id": "c05_eps030",
                        "discount_case_id": "c05",
                        "epsilon_value": 30,
                        "forecast_cov_epsilon": 30,
                        "c_factor": 1,
                        "df_t": 0.9999,
                        "df_s1": 0.9993,
                        "df_s2": 0.9993,
                        "df_s67": 0.9995,
                        "df_discrep": 0.9988,
                        "lambda": 0.97,
                        "df_trans": 0.9999999,
                        "df_covs": 0.99999,
                        "lane": "exdqlm_multivar_keep",
                        "run_id": "run_bad",
                        "config_path": "/tmp/bad.yaml",
                    },
                ]
            )
            plan.to_csv(matrix_dir / "matrix_plan.csv", index=False)

            for run_id, report_status in [("run_good", "pass"), ("run_bad", "fail")]:
                run_root = runs_dir(artifact_root) / run_id
                run_root.mkdir(parents=True)
                manifest = {
                    "stages": {
                        "forecats": {"status": "pass"},
                        "data_prep_shared": {"status": "pass"},
                        "fit": {"status": "pass"},
                        "post": {"status": "pass" if report_status == "pass" else "fail"},
                        "validate": {"status": report_status},
                        "report": {"status": report_status},
                    }
                }
                if run_id == "run_good":
                    manifest["rdata_cleanup"] = {"after_post": {"before": 7, "removed": 7, "remaining": 0}}
                (run_root / "run_manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

            out_root = runs_dir(artifact_root) / "run_good" / "post/outputs/run_good"
            tables = out_root / "tables"
            tables.mkdir(parents=True)
            good_log = runs_dir(artifact_root) / "run_good" / "fit/exdqlm_multivar/keep/q=20/logs/fit.log"
            good_log.parent.mkdir(parents=True)
            good_log.write_text(
                "\n".join([
                    "[gamsig_rollback] p0=0.2 iter=46 reason=guard_triggered detail=incoherent gamma/sigma moments",
                    "[latent_parameter_guard] p0=0.2 bad_psi=0/1 bad_chi=2/100 action=clamp_to_floor",
                    "[sampling_phase] p0=0.2 phase=sampling_finalize elapsed=10s detail=n_samp=2000",
                ]) + "\n",
                encoding="utf-8",
            )
            bad_log = runs_dir(artifact_root) / "run_bad" / "fit/exdqlm_multivar/keep/q=20/logs/fit.log"
            bad_log.parent.mkdir(parents=True)
            bad_log.write_text("[pseudodata_guard_fail] p0=0.2 iter=47\nExecution halted\n", encoding="utf-8")
            (out_root / "post_artifacts_summary.json").write_text(
                json.dumps({"contract": {"status": True, "missing_paths": []}}),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {
                        "model_id": evaluator.TARGET_MODEL_ID,
                        "score_scale": evaluator.TARGET_SCORE_SCALE,
                        "lead_day": 1,
                        "forecast_date": "2021-11-13",
                        "crps": 0.2,
                    },
                    {
                        "model_id": evaluator.TARGET_MODEL_ID,
                        "score_scale": evaluator.TARGET_SCORE_SCALE,
                        "lead_day": 2,
                        "forecast_date": "2021-11-14",
                        "crps": 0.1,
                    },
                ]
            ).to_csv(tables / "crps_forecast_per_time.csv", index=False)
            pd.DataFrame([{"model_id": evaluator.TARGET_MODEL_ID, "status": "pass"}]).to_csv(
                tables / "crps_input_health.csv", index=False
            )
            pd.DataFrame(
                [
                    {
                        "model_id": evaluator.TARGET_MODEL_ID,
                        "anchor_curve_crossing_share": 0,
                        "empirical_curve_crossing_share": 0,
                    }
                ]
            ).to_csv(out_root / f"{evaluator.TARGET_MODEL_ID}_forecast_quantile_synthesis_summary.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "transfer_mode": "keep",
                        "forecast_has_transfer": True,
                        "n_forecast_rows": 28,
                        "finite_zeta_forecast": 28,
                        "finite_mu_without_transfer_forecast": 28,
                    }
                ]
            ).to_csv(out_root / "multivar_transfer_contract_q50.csv", index=False)
            pd.DataFrame([{"parameter": "elbo", "component": 1, "last": -1.0}]).to_csv(
                out_root / "multivar_trace_summary_q50.csv", index=False
            )

            gates, tables_by_name = evaluator.build_gate_summary(plan, artifact_root)
            summary, winners, pooled = evaluator.summarize_crps(tables_by_name["crps_per_time"], gates)
            self.assertEqual(int(gates["eligible"].sum()), 1)
            good_gate = gates.loc[gates["run_id"] == "run_good"].iloc[0]
            self.assertEqual(good_gate["stability_status"], "guarded_pass")
            self.assertEqual(int(good_gate["gamsig_rollback_count"]), 1)
            self.assertEqual(int(good_gate["latent_parameter_guard_count"]), 1)
            self.assertTrue(bool(good_gate["rdata_cleanup_ok"]))
            bad_gate = gates.loc[gates["run_id"] == "run_bad"].iloc[0]
            self.assertEqual(bad_gate["stability_status"], "failed")
            self.assertIn("pseudodata_guard_fail", bad_gate["stability_failure_reason"])
            self.assertEqual(winners.iloc[0]["grid_spec_id"], "c01_eps365")
            self.assertAlmostEqual(float(winners.iloc[0]["mean_crps"]), 0.15)
            self.assertEqual(winners.iloc[0]["stability_status"], "guarded_pass")
            self.assertFalse(summary.empty)
            self.assertFalse(pooled.empty)
            self.assertIn("stability_diagnostics", tables_by_name)
            self.assertFalse(tables_by_name["stability_diagnostics"].empty)
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
