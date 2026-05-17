#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from build_multimodel_v8_matrix_configs import build_v8_config  # noqa: E402
from build_multimodel_v8_compare_bundle import LaneSpec, build_bundle  # noqa: E402
from check_multimodel_v8_matrix_health import build_status  # noqa: E402
from multimodel_v8_lib import TARGET_MODELS, build_lane_plan_rows, load_yaml, parse_epsilon_spec_list, reports_dir, runs_dir, v7_template_config_path  # noqa: E402
from run_multimodel_v8_queue import compare_cells_from_plan, pgrep_active_v8  # noqa: E402


class MultimodelV8ToolingTests(unittest.TestCase):
    def test_build_v8_config_uses_gapfixed_pre1080_provider_for_20221225(self) -> None:
        template = load_yaml(v7_template_config_path("20221225", "l1"))
        artifact_root = ROOT / "tmp" / "v8_test_artifacts"
        cfg = build_v8_config(
            template_cfg=template,
            run_id="multimodel_20221225_v8_epsTT_l1",
            epsilon_label="epsTT",
            epsilon_value=None,
            lane="l1",
            cutoff="20221225",
            artifact_root=artifact_root,
        )
        bundle_path = str(cfg["inputs"]["forecats"]["existing_bundle_path"])
        self.assertIn("20260404_single_retro_policy_pre1080_gapfix_r01", bundle_path)
        self.assertNotIn("pre20", bundle_path)

    def test_build_v8_config_scopes_mv_lane_correctly(self) -> None:
        template = load_yaml(v7_template_config_path("20211112", "l1"))
        artifact_root = ROOT / "tmp" / "v8_test_artifacts"
        cfg = build_v8_config(
            template_cfg=template,
            run_id="multimodel_20211112_v8_eps30_l1_mv",
            epsilon_label="eps30",
            epsilon_value=30.0,
            lane="l1_mv",
            cutoff="20211112",
            artifact_root=artifact_root,
        )
        self.assertTrue(cfg["models"]["run_exdqlm_multivar"])
        self.assertFalse(cfg["models"]["run_exdqlm_univar"])
        self.assertFalse(cfg["models"]["run_ndlm_main"])
        self.assertFalse(cfg["models"]["run_ndlm_univar"])
        self.assertEqual(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"], 30.0)
        self.assertEqual(cfg["run"]["run_root"], str(runs_dir(artifact_root)))
        self.assertTrue(cfg["stages"]["forecats"])
        self.assertTrue(cfg["post"]["smoke_fast"])
        self.assertEqual(cfg["inputs"]["forecats"]["mode"], "use_existing")
        self.assertTrue(str(cfg["inputs"]["forecats"]["existing_bundle_path"]).endswith("meta.yaml"))
        self.assertTrue(cfg["inputs"]["shared"]["prefer_forecats_snapshot"])
        self.assertEqual(cfg["models"]["exdqlm_univar"]["implementation_mode"], "legacy_bridge")
        self.assertEqual(
            cfg["debug_v8_matrix"]["compare_bundle_outdir"],
            str(reports_dir(artifact_root) / "multimodel_20211112_v8_eps30_compare"),
        )

    def test_build_v8_config_can_override_multivar_c_factor_and_parallel_settings(self) -> None:
        template = load_yaml(v7_template_config_path("20221225", "l2"))
        artifact_root = ROOT / "tmp" / "v8_test_artifacts"
        cfg = build_v8_config(
            template_cfg=template,
            run_id="multimodel_20221225_v8_eps25cf1_l2_mv",
            epsilon_label="eps25cf1",
            epsilon_value=25.0,
            lane="l2_mv",
            cutoff="20221225",
            artifact_root=artifact_root,
            multivar_c_factor=1.0,
            fit_parallel_mode="global_models",
            fit_parallel_workers=14,
        )
        self.assertEqual(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["c_factor"], 1.0)
        self.assertEqual(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"], 25.0)
        self.assertEqual(cfg["fit"]["parallel"]["mode"], "global_models")
        self.assertEqual(cfg["fit"]["parallel"]["workers"], 14)
        self.assertEqual(cfg["run"]["threads"]["mc_cores"], 14)
        self.assertEqual(cfg["debug_v8_matrix"]["multivar_c_factor"], 1.0)
        self.assertEqual(cfg["debug_v8_matrix"]["fit_parallel_mode"], "global_models")
        self.assertEqual(cfg["debug_v8_matrix"]["fit_parallel_workers"], 14)

    def test_compare_bundle_mixes_tt_and_mv_sources_explicitly(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="v8_bundle_test_"))
        artifact_root = td / "artifact_root"
        try:
            for run_id in [
                "multimodel_20211112_v8_epsTT_l1",
                "multimodel_20211112_v8_epsTT_l2",
                "multimodel_20211112_v8_eps30_l1_mv",
                "multimodel_20211112_v8_eps30_l2_mv",
            ]:
                (runs_dir(artifact_root) / run_id / "post" / "outputs" / run_id / "tables").mkdir(parents=True, exist_ok=True)

            def write_lane(run_id: str, rows: list[dict], fig_rows: list[dict]) -> None:
                root = runs_dir(artifact_root) / run_id / "post" / "outputs" / run_id
                crps = pd.DataFrame(rows)
                health = pd.DataFrame([
                    {
                        "model_id": r["model_id"],
                        "model_family": r["model_family"],
                        "model_variant": r["model_variant"],
                        "transfer_mode": r["transfer_mode"],
                        "status": "pass",
                        "max_abs_observed": 1.0,
                    }
                    for r in rows if r["model_id"] not in {"glofas_ensemble", "nws_nwm_ensemble"}
                ])
                crps.to_csv(root / "tables" / "crps_forecast_summary.csv", index=False)
                health.to_csv(root / "tables" / "crps_input_health.csv", index=False)
                pd.DataFrame(fig_rows).to_csv(root / "figure_manifest.csv", index=False)

            common_cols = {
                "cutoff_date": "2021-11-12",
                "forecast_start_date": "2021-11-13",
                "horizon_days": 28,
                "n_valid": 28,
                "median_crps": 0.1,
                "sd_crps": 0.01,
                "min_crps": 0.01,
                "max_crps": 0.2,
                "n_samples_nominal": 7,
                "n_samples_eff_min": 7,
                "n_samples_eff_max": 7,
                "score_method": "quantile_check_loss_sum",
                "tau_rule": "k_over_m_plus_1",
                "score_scale": "log_cms_plus1",
            }
            l1_rows = []
            l2_rows = []
            for spec in TARGET_MODELS:
                row = dict(common_cols)
                row.update({
                    "model_id": spec["model_id"],
                    "model_family": "synthesis",
                    "model_variant": spec["model_variant"],
                    "transfer_mode": spec["transfer_mode"] or pd.NA,
                    "mean_crps": 1.0 if "multivar" in spec["model_id"] else 0.5,
                    "source_run": "placeholder",
                })
                if spec["baseline_lane"] == "l1":
                    l1_rows.append(row)
                else:
                    l2_rows.append(row)
            # Add ensemble baselines to l1 baseline only.
            l1_rows.extend([
                dict(common_cols, model_id="glofas_ensemble", model_family="ensemble", model_variant="glofas", transfer_mode=pd.NA, mean_crps=1.3, source_run="placeholder"),
                dict(common_cols, model_id="nws_nwm_ensemble", model_family="ensemble", model_variant="nws_nwm", transfer_mode=pd.NA, mean_crps=0.9, source_run="placeholder"),
            ])
            mv_l1_rows = [dict(r, mean_crps=0.7) for r in l1_rows if "multivar" in str(r["model_id"])]
            mv_l2_rows = [dict(r, mean_crps=0.6) for r in l2_rows if "multivar" in str(r["model_id"])]

            def fig_rows(rows, run_id):
                return [
                    {"model_id": r["model_id"], "plot_type": "cutoff_window_posterior_samples", "path": f"/tmp/{run_id}_{r['model_id']}.png", "source_run": run_id, "note": "ut"}
                    for r in rows if r["model_id"] in {spec["model_id"] for spec in TARGET_MODELS}
                ]

            write_lane("multimodel_20211112_v8_epsTT_l1", l1_rows, fig_rows(l1_rows, "tt_l1"))
            write_lane("multimodel_20211112_v8_epsTT_l2", l2_rows, fig_rows(l2_rows, "tt_l2"))
            write_lane("multimodel_20211112_v8_eps30_l1_mv", mv_l1_rows, fig_rows(mv_l1_rows, "mv_l1"))
            write_lane("multimodel_20211112_v8_eps30_l2_mv", mv_l2_rows, fig_rows(mv_l2_rows, "mv_l2"))

            outdir = td / "out_bundle"
            build_bundle(
                cutoff="20211112",
                epsilon="eps30",
                baseline_l1=LaneSpec("v8_epsTT_l1", "multimodel_20211112_v8_epsTT_l1", "baseline_tt"),
                baseline_l2=LaneSpec("v8_epsTT_l2", "multimodel_20211112_v8_epsTT_l2", "baseline_tt"),
                mv_l1=LaneSpec("v8_eps30_l1_mv", "multimodel_20211112_v8_eps30_l1_mv", "epsilon_specific_mv"),
                mv_l2=LaneSpec("v8_eps30_l2_mv", "multimodel_20211112_v8_eps30_l2_mv", "epsilon_specific_mv"),
                outdir=outdir,
                artifact_root=artifact_root,
            )
            prov = pd.read_csv(outdir / "source_provenance.csv")
            self.assertEqual(len(prov), 9)
            self.assertTrue((prov.loc[prov["model_id"].str.contains("multivar"), "source_type"] == "epsilon_specific_mv").all())
            self.assertTrue((prov.loc[~prov["model_id"].str.contains("multivar"), "source_type"] == "baseline_tt").all())
            crps = pd.read_csv(outdir / "crps_forecast_summary_all_models.csv")
            mv_rows = crps.loc[crps["model_id"].str.contains("multivar")]
            self.assertTrue((mv_rows["source_type"] == "epsilon_specific_mv").all())
            inv_rows = crps.loc[~crps["model_id"].str.contains("multivar") & crps["model_id"].isin([s["model_id"] for s in TARGET_MODELS])]
            self.assertTrue((inv_rows["source_type"] == "baseline_tt").all())
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_health_checker_parses_plan_and_manifest(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="v8_health_test_"))
        try:
            matrix_dir = td / "matrix"
            matrix_dir.mkdir(parents=True, exist_ok=True)
            artifact_root = td / "artifact_root"
            plan = pd.DataFrame([
                {
                    "order_index": 1,
                    "cutoff": "20990101",
                    "epsilon": "epsTT",
                    "epsilon_value": "TT",
                    "lane": "l1",
                    "run_scope": "full_tt",
                    "run_id": "multimodel_20990101_v8_epsTT_l1",
                    "config_path": "/tmp/cfg.yaml",
                    "compare_outdir": "/tmp/out",
                    "priority_group": 1,
                    "max_concurrent_class": "ordinary",
                }
            ])
            plan.to_csv(matrix_dir / "matrix_plan.csv", index=False)
            run_root = runs_dir(artifact_root) / "multimodel_20990101_v8_epsTT_l1"
            manifest_path = run_root / "run_manifest.yaml"
            run_root.mkdir(parents=True, exist_ok=True)
            manifest = {
                "stages": {
                    "fit": {"status": "pass", "log_path": str(run_root / "fit" / "logs" / "fit_stage.log")},
                    "post": {"status": "pending", "log_path": str(run_root / "post" / "logs" / "post_runner.log"), "started_at_utc": "2026-04-01T00:00:00Z", "finished_at_utc": ""},
                    "validate": {"status": "pending", "log_path": str(run_root / "validate" / "validate.log")},
                    "report": {"status": "pending", "log_path": str(run_root / "report" / "summary.md")},
                },
                "timestamps": {"started_at_utc": "2026-04-01T00:00:00Z", "finished_at_utc": ""},
            }
            (run_root / "post" / "module" / "logs").mkdir(parents=True, exist_ok=True)
            (run_root / "post" / "logs").mkdir(parents=True, exist_ok=True)
            (run_root / "post" / "logs" / "post_runner.log").write_text("live\n", encoding="utf-8")
            (run_root / "post" / "module" / "logs" / "child.log").write_text("newer\n", encoding="utf-8")
            manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
            df = build_status(matrix_dir, artifact_root=artifact_root)
            self.assertEqual(df.iloc[0]["phase"], "post")
            self.assertEqual(df.iloc[0]["status"], "pending")
            self.assertTrue(df.iloc[0]["latest_log_mtime"])
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_plan_rows_skip_duplicate_v4_epsilon(self) -> None:
        plan = build_lane_plan_rows()
        eps_labels = {row.epsilon_label for row in plan}
        self.assertNotIn("eps_v4", eps_labels)
        self.assertEqual(eps_labels, {"epsTT", "eps30", "eps90", "eps180", "eps360"})

    def test_custom_epsilon_specs_support_targeted_extension(self) -> None:
        epsilon_map = parse_epsilon_spec_list(["eps25=25", "eps20=20", "eps15=15", "eps10=10", "eps5=5", "eps1=1"])
        self.assertEqual(list(epsilon_map.keys()), ["eps25", "eps20", "eps15", "eps10", "eps5", "eps1"])
        self.assertEqual(epsilon_map["eps25"], 25.0)
        plan = build_lane_plan_rows(cutoffs=["20221225"], epsilon_map=epsilon_map, include_tt=False)
        self.assertEqual(len(plan), 12)
        self.assertTrue(all(row.cutoff == "20221225" for row in plan))
        self.assertTrue(all(row.lane in {"l1_mv", "l2_mv"} for row in plan))
        self.assertEqual({row.epsilon_label for row in plan}, set(epsilon_map.keys()))

    def test_custom_null_tt_label_stays_multivar_only(self) -> None:
        epsilon_map = parse_epsilon_spec_list(["epsTTcf1=tt", "eps30cf1=30"])
        plan = build_lane_plan_rows(cutoffs=["20211112"], epsilon_map=epsilon_map, include_tt=True)
        self.assertEqual(len(plan), 4)
        self.assertEqual({row.epsilon_label for row in plan}, {"epsTTcf1", "eps30cf1"})
        self.assertTrue(all(row.lane in {"l1_mv", "l2_mv"} for row in plan))
        self.assertTrue(all(row.run_scope == "multivar_only" for row in plan))

    def test_compare_cells_follow_custom_plan_not_hardcoded_epsilons(self) -> None:
        plan = pd.DataFrame([
            {"order_index": 1, "cutoff": "20221225", "epsilon": "eps25", "lane": "l1_mv"},
            {"order_index": 2, "cutoff": "20221225", "epsilon": "eps25", "lane": "l2_mv"},
            {"order_index": 3, "cutoff": "20221225", "epsilon": "eps20", "lane": "l1_mv"},
            {"order_index": 4, "cutoff": "20221225", "epsilon": "eps20", "lane": "l2_mv"},
        ])
        self.assertEqual(compare_cells_from_plan(plan), [("20221225", "eps25"), ("20221225", "eps20")])

    def test_pgrep_active_v8_matches_real_r_command_shape(self) -> None:
        import subprocess
        from unittest import mock

        fake_ps = (
            "123 /usr/lib64/R/bin/exec/R --no-echo --no-restore --vanilla "
            "--file=scripts/unified_run.R --args --config "
            "/data/muscat_data/jaguir26/project1_ucsc_phd/config/unified_runs/"
            "multimodel_20211112_v8_epsTT_l1.yaml\n"
            "124 /usr/lib64/R/bin/exec/R --no-echo --no-restore --vanilla "
            "--file=scripts/unified_run.R --args --config "
            "/data/muscat_data/jaguir26/project1_ucsc_phd/config/unified_runs/"
            "multimodel_20211112_v8_epsTT_l1.yaml\n"
            "125 /usr/lib64/R/bin/exec/R --no-echo --no-restore --vanilla "
            "--file=scripts/unified_run.R --args --config "
            "/data/muscat_data/jaguir26/project1_ucsc_phd/config/unified_runs/"
            "multimodel_20211112_v8_epsTT_l2.yaml\n"
        )
        completed = subprocess.CompletedProcess(args=["ps"], returncode=0, stdout=fake_ps, stderr="")
        with mock.patch("run_multimodel_v8_queue.subprocess.run", return_value=completed):
            rows = pgrep_active_v8()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["pid"], "123")
        self.assertIn("multimodel_20211112_v8_epsTT_l1", rows[0]["command"])

    def test_pgrep_active_v8_can_scope_to_artifact_root(self) -> None:
        import subprocess
        from unittest import mock

        fake_ps = (
            "123 /usr/lib64/R/bin/exec/R --no-echo --no-restore --vanilla "
            "--file=scripts/unified_run.R --args --config "
            "/tmp/keep/control/generated_configs/multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml\n"
            "124 /usr/lib64/R/bin/exec/R --no-echo --no-restore --vanilla "
            "--file=scripts/unified_run.R --args --config "
            "/tmp/drop/control/generated_configs/multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_multivar_drop.yaml\n"
        )
        completed = subprocess.CompletedProcess(args=["ps"], returncode=0, stdout=fake_ps, stderr="")
        with mock.patch("run_multimodel_v8_queue.subprocess.run", return_value=completed):
            keep_rows = pgrep_active_v8("/tmp/keep")
            drop_rows = pgrep_active_v8("/tmp/drop")
            all_rows = pgrep_active_v8()
        self.assertEqual(len(keep_rows), 1)
        self.assertIn("multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_multivar_keep", keep_rows[0]["command"])
        self.assertEqual(len(drop_rows), 1)
        self.assertIn("multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_multivar_drop", drop_rows[0]["command"])
        self.assertEqual(len(all_rows), 2)


if __name__ == "__main__":
    unittest.main()
