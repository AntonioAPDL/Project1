#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]

CUTOFFS = [
    ("20210123", "eps360cf1", 0.156860),
    ("20211112", "eps180cf1", 0.028384),
    ("20211221", "eps1cf1", 0.236937),
    ("20220511", "eps180cf1", 0.020966),
    ("20221225", "eps360cf1", 0.614397),
]
REFRESH_CUTOFF = "20221225"
REFRESH_SOURCE_RUN_ID = "multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep"
REFRESH_SOURCE_CRPS = 0.4375250570387207


def base_source_config(cutoff: str, epsilon: str) -> dict:
    return {
        "config_version": 1,
        "run": {
            "run_id": f"multimodel_{cutoff}_v8_{epsilon}_exdqlm_multivar_keep_featurecov_cf1",
            "run_root": "/tmp/source_runs",
            "seed": 777,
            "overwrite": False,
            "auto_suffix_on_collision": False,
            "dry_run": False,
            "threads": {"mc_cores": 7},
        },
        "stages": {
            "forecats": False,
            "data_prep_shared": True,
            "fit": True,
            "post": True,
            "validate": True,
            "report": True,
        },
        "models": {
            "run_exdqlm_multivar": True,
            "run_exdqlm_univar": False,
            "run_ndlm_main": False,
            "run_ndlm_univar": False,
            "exdqlm_multivar": {
                "implementation_mode": "legacy_bridge",
                "likelihood_mode": "exal",
                "forecast_transfer_mode": "keep",
                "state_evolution": {
                    "df_t": 0.99999999,
                    "df_s1": 0.9999,
                    "df_s2": 0.9999,
                    "df_s67": 0.9999,
                    "df_discrep": 0.999,
                    "lambda": 0.97,
                    "df_trans": 0.9999999,
                    "df_covs": 0.99999,
                },
            },
        },
        "fit": {
            "parallel": {"mode": "global_models", "workers": 7},
            "warm_start": {"enabled": False},
            "exdqlm_multivar": {
                "gamma_sigma": {
                    "warmup_freeze_iters": 5,
                    "min_update_iters": 50,
                    "min_total_iters": 50,
                    "max_iter": 100,
                },
                "forecast_health": {
                    "enabled": True,
                    "fail_fast": True,
                    "write_reports": True,
                    "latent_limit": 650,
                    "sigma_limit": 100,
                    "state_limit": 1000,
                },
                "legacy": {"use_covariates": True},
            },
        },
    }


class He3ToolingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = Path(tempfile.mkdtemp(prefix="he3_ablation_"))
        self.runtime_root = self.td / "runtime"
        self.cf1_root = self.runtime_root / "cf1"
        self.he3_root = self.runtime_root / "he3"
        self.cf1_config_dir = self.td / "configs_cf1"
        self.he3_config_dir = self.td / "configs_he3"
        self.matrix_dir = self.he3_root / "control" / "he3_exdqlm_ablation_v1"
        self.best_csv = self.cf1_root / "reports" / "final_featurecov_cf1_eps_analysis" / "best_by_cutoff_long.csv"

        self.cf1_config_dir.mkdir(parents=True, exist_ok=True)
        self.best_csv.parent.mkdir(parents=True, exist_ok=True)

        best_rows = []
        for cutoff, epsilon, crps in CUTOFFS:
            run_id = f"multimodel_{cutoff}_v8_{epsilon}_exdqlm_multivar_keep_featurecov_cf1"
            cfg_path = self.cf1_config_dir / f"{run_id}.yaml"
            with cfg_path.open("w", encoding="utf-8") as handle:
                yaml.safe_dump(base_source_config(cutoff, epsilon), handle, sort_keys=False)

            run_dir = self.cf1_root / "runs" / run_id
            tables_dir = run_dir / "post" / "outputs" / run_id / "tables"
            tables_dir.mkdir(parents=True, exist_ok=True)
            with (run_dir / "run_manifest.yaml").open("w", encoding="utf-8") as handle:
                yaml.safe_dump(
                    {"stages": {"report": {"status": "pass"}}},
                    handle,
                    sort_keys=False,
                )
            pd.DataFrame(
                [{"model_id": "exdqlm_multivar_synth_keep", "mean_crps": crps}]
            ).to_csv(tables_dir / "crps_forecast_summary.csv", index=False)
            pd.DataFrame(
                [
                    {"lead_day": lead, "model_id": "exdqlm_multivar_synth_keep", "crps": crps + lead / 100.0}
                    for lead in range(1, 29)
                ]
            ).to_csv(tables_dir / "crps_forecast_per_time.csv", index=False)

            best_rows.append(
                {
                    "cutoff": cutoff,
                    "rank_within_cutoff": 1,
                    "model_variant": "exdqlm_multivar_keep",
                    "class": "bayes",
                    "transfer_mode": "keep",
                    "horizon_days": 28,
                    "forecast_window_crps": crps,
                    "best_epsilon_label": epsilon,
                    "best_epsilon_value": 1.0,
                    "best_c_factor": 1.0,
                    "selection_basis": "unit_test",
                }
            )
            best_rows.append(
                {
                    "cutoff": cutoff,
                    "rank_within_cutoff": 2,
                    "model_variant": "exdqlm_multivar_drop",
                    "class": "bayes",
                    "transfer_mode": "drop",
                    "horizon_days": 28,
                    "forecast_window_crps": crps + 0.5,
                    "best_epsilon_label": epsilon,
                    "best_epsilon_value": 1.0,
                    "best_c_factor": 1.0,
                    "selection_basis": "unit_test",
                }
            )
        pd.DataFrame(best_rows).to_csv(self.best_csv, index=False)

        self.template_path = self.td / "he3.template.yaml"
        template = {
            "version": 1,
            "campaign": {
                "campaign_id": "he3_test",
                "study_id": "he3_test_v1",
                "artifact_root": str(self.he3_root),
                "matrix_dir": str(self.matrix_dir),
                "config_output_dir": str(self.he3_config_dir),
            },
            "source": {
                "cf1_sweep_root": str(self.cf1_root),
                "cf1_config_dir": str(self.cf1_config_dir),
                "best_by_cutoff_csv": str(self.best_csv),
                "selected_model_variant": "exdqlm_multivar_keep",
            },
            "queue": {
                "ordinary_max_concurrent": 4,
                "heavy_cutoff_max_concurrent": 1,
                "pause_free_gb": 180,
                "launch_free_gb": 220,
                "heavy_free_gb": 240,
                "poll_seconds": 60,
            },
            "fit_parallel": {"workers": 7},
            "pilot_sequence": ["20211112", "20221225"],
            "variants": {
                "full": {
                    "enabled": True,
                    "reuse_reference": True,
                    "manuscript_label": "exAL-M-T1",
                    "include_trend": True,
                    "enabled_harmonic_indices": [1, 2, 3],
                    "use_covariates": True,
                    "forecast_transfer_mode": "keep",
                },
                "noTrend": {
                    "enabled": True,
                    "reuse_reference": False,
                    "manuscript_label": "exAL-M-T1-noTrend",
                    "include_trend": False,
                    "enabled_harmonic_indices": [1, 2, 3],
                    "use_covariates": True,
                    "forecast_transfer_mode": "keep",
                },
                "noTF": {
                    "enabled": True,
                    "reuse_reference": False,
                    "manuscript_label": "exAL-M-noTF",
                    "include_trend": True,
                    "enabled_harmonic_indices": [1, 2, 3],
                    "use_covariates": False,
                    "forecast_transfer_mode": "drop",
                },
                "noH1": {
                    "enabled": True,
                    "reuse_reference": False,
                    "manuscript_label": "exAL-M-T1-noH1",
                    "include_trend": True,
                    "enabled_harmonic_indices": [2, 3],
                    "use_covariates": True,
                    "forecast_transfer_mode": "keep",
                },
                "noH2": {
                    "enabled": True,
                    "reuse_reference": False,
                    "manuscript_label": "exAL-M-T1-noH2",
                    "include_trend": True,
                    "enabled_harmonic_indices": [1, 3],
                    "use_covariates": True,
                    "forecast_transfer_mode": "keep",
                },
                "noH3": {
                    "enabled": True,
                    "reuse_reference": False,
                    "manuscript_label": "exAL-M-T1-noH3",
                    "include_trend": True,
                    "enabled_harmonic_indices": [1, 2],
                    "use_covariates": True,
                    "forecast_transfer_mode": "keep",
                },
            },
        }
        with self.template_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(template, handle, sort_keys=False)

        self.refresh_source_run_dir = (
            self.runtime_root
            / "discount_exact"
            / "runs"
            / REFRESH_SOURCE_RUN_ID
        )
        self.refresh_source_run_dir.mkdir(parents=True, exist_ok=True)
        refresh_cfg = base_source_config(REFRESH_CUTOFF, "eps360cf1")
        refresh_cfg["run"]["run_id"] = REFRESH_SOURCE_RUN_ID
        refresh_cfg["run"]["run_root"] = str(self.refresh_source_run_dir.parent)
        refresh_cfg["models"]["exdqlm_multivar"]["state_evolution"] = {
            "df_t": 0.99999999,
            "df_s1": 0.9998,
            "df_s2": 0.9998,
            "df_s67": 0.9999,
            "df_discrep": 0.998,
            "lambda": 0.97,
            "df_trans": 0.9999999,
            "df_covs": 0.9999999,
        }
        with (self.refresh_source_run_dir / "resolved_config.yaml").open("w", encoding="utf-8") as handle:
            yaml.safe_dump(refresh_cfg, handle, sort_keys=False)
        tables_dir = self.refresh_source_run_dir / "post" / "outputs" / REFRESH_SOURCE_RUN_ID / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)
        with (self.refresh_source_run_dir / "run_manifest.yaml").open("w", encoding="utf-8") as handle:
            yaml.safe_dump({"stages": {"report": {"status": "pass"}}}, handle, sort_keys=False)
        pd.DataFrame(
            [{"model_id": "exdqlm_multivar_synth_keep", "mean_crps": REFRESH_SOURCE_CRPS}]
        ).to_csv(tables_dir / "crps_forecast_summary.csv", index=False)
        pd.DataFrame(
            [
                {"lead_day": lead, "model_id": "exdqlm_multivar_synth_keep", "crps": REFRESH_SOURCE_CRPS + lead / 100.0}
                for lead in range(1, 29)
            ]
        ).to_csv(tables_dir / "crps_forecast_per_time.csv", index=False)

    def tearDown(self) -> None:
        shutil.rmtree(self.td, ignore_errors=True)

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(args),
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

    def test_build_matrix_creates_expected_rows_and_variant_configs(self) -> None:
        self.run_script(
            "python3",
            "scripts/build_he3_exdqlm_ablation_matrix.py",
            "--template",
            str(self.template_path),
        )
        plan = pd.read_csv(self.matrix_dir / "matrix_plan.csv")
        plan["cutoff"] = plan["cutoff"].astype(str).str.zfill(8)
        self.assertEqual(len(plan), 30)
        self.assertEqual(int((plan["launch_mode"] == "reuse_reference").sum()), 5)
        self.assertEqual(int((plan["launch_mode"] == "launch").sum()), 25)

        no_tf = plan[(plan["cutoff"] == "20210123") & (plan["variant"] == "noTF")].iloc[0]
        cfg = yaml.safe_load(Path(no_tf["config_path"]).read_text(encoding="utf-8"))
        self.assertEqual(cfg["models"]["exdqlm_multivar"]["forecast_transfer_mode"], "drop")
        self.assertFalse(cfg["fit"]["exdqlm_multivar"]["legacy"]["use_covariates"])
        self.assertEqual(cfg["models"]["exdqlm_multivar"]["structure"]["enabled_harmonic_indices"], [1, 2, 3])

    def test_validator_passes_for_fresh_matrix(self) -> None:
        self.run_script(
            "python3",
            "scripts/build_he3_exdqlm_ablation_matrix.py",
            "--template",
            str(self.template_path),
        )
        self.run_script(
            "python3",
            "scripts/validate_he3_exdqlm_ablation.py",
            "--matrix-dir",
            str(self.matrix_dir),
            "--template",
            str(self.template_path),
        )
        status = pd.read_csv(self.matrix_dir / "matrix_status.csv")
        full_rows = status[status["launch_mode"] == "reuse_reference"]
        self.assertTrue((full_rows["status"] == "pass").all())
        self.assertTrue((status[status["launch_mode"] == "launch"]["status"] == "not_started").all())

    def test_build_and_validate_support_focused_refresh_override(self) -> None:
        refresh_template_path = self.td / "he3_refresh.template.yaml"
        refresh_cfg = yaml.safe_load(self.template_path.read_text(encoding="utf-8"))
        refresh_cfg["campaign"]["campaign_id"] = "he3_refresh_test"
        refresh_cfg["campaign"]["study_id"] = "he3_refresh_test_v1"
        refresh_cfg["campaign"]["artifact_root"] = str(self.td / "refresh_artifacts")
        refresh_cfg["campaign"]["matrix_dir"] = str(self.td / "refresh_artifacts" / "control" / "he3_refresh")
        refresh_cfg["campaign"]["config_output_dir"] = str(self.td / "refresh_configs")
        refresh_cfg["source"]["cutoff_filter"] = [REFRESH_CUTOFF]
        refresh_cfg["source"]["cutoff_overrides"] = {
            REFRESH_CUTOFF: {
                "source_label": "set09",
                "source_run_id": REFRESH_SOURCE_RUN_ID,
                "source_run_dir": str(self.refresh_source_run_dir),
                "source_config_path": str(self.refresh_source_run_dir / "resolved_config.yaml"),
                "source_full_crps": REFRESH_SOURCE_CRPS,
            }
        }
        refresh_cfg["fit_parallel"]["workers"] = 1
        refresh_cfg["queue"]["ordinary_max_concurrent"] = 4
        refresh_cfg["queue"]["heavy_cutoff_max_concurrent"] = 4
        refresh_cfg["pilot_sequence"] = [REFRESH_CUTOFF]
        with refresh_template_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(refresh_cfg, handle, sort_keys=False)

        self.run_script(
            "python3",
            "scripts/build_he3_exdqlm_ablation_matrix.py",
            "--template",
            str(refresh_template_path),
        )
        refresh_matrix_dir = Path(refresh_cfg["campaign"]["matrix_dir"])
        plan = pd.read_csv(refresh_matrix_dir / "matrix_plan.csv")
        plan["cutoff"] = plan["cutoff"].astype(str).str.zfill(8)
        self.assertEqual(len(plan), 6)
        self.assertEqual(int((plan["launch_mode"] == "reuse_reference").sum()), 1)
        self.assertEqual(int((plan["launch_mode"] == "launch").sum()), 5)
        self.assertEqual(plan["cutoff"].nunique(), 1)
        full_row = plan[plan["variant"] == "full"].iloc[0]
        self.assertEqual(full_row["source_run_id"], REFRESH_SOURCE_RUN_ID)
        self.assertAlmostEqual(float(full_row["source_full_crps"]), REFRESH_SOURCE_CRPS)
        self.assertEqual(full_row["best_epsilon_label"], "set09")

        no_tf = plan[plan["variant"] == "noTF"].iloc[0]
        cfg = yaml.safe_load(Path(no_tf["config_path"]).read_text(encoding="utf-8"))
        self.assertEqual(cfg["fit"]["parallel"]["workers"], 1)
        self.assertEqual(cfg["run"]["threads"]["mc_cores"], 1)
        self.assertEqual(
            cfg["models"]["exdqlm_multivar"]["state_evolution"]["df_s1"],
            0.9998,
        )

        self.run_script(
            "python3",
            "scripts/validate_he3_exdqlm_ablation.py",
            "--matrix-dir",
            str(refresh_matrix_dir),
            "--template",
            str(refresh_template_path),
        )
        status = pd.read_csv(refresh_matrix_dir / "matrix_status.csv")
        self.assertEqual(len(status), 6)
        self.assertTrue((status[status["launch_mode"] == "reuse_reference"]["status"] == "pass").all())
        self.assertTrue((status[status["launch_mode"] == "launch"]["status"] == "not_started").all())

    def test_no_trend_block_diag_helper_accepts_vector_ff(self) -> None:
        r_code = r"""
library(exdqlm)
library(Matrix)
source("R/unified/families/exdqlm_multivar_structure.R")
built <- exdqlm_multivar_build_structure(
  m_yy = 1.0,
  kk = 0.5,
  df_t = 0.99,
  df_s1 = 0.98,
  df_s2 = 0.97,
  df_s67 = 0.96,
  lam1 = 0.9,
  lam2 = 0.8,
  include_trend = FALSE,
  enabled_harmonic_indices = c(1L, 2L, 3L),
  default_harmonics = exdqlm_multivar_default_harmonics(),
  season_period = 363.5854,
  trend_c0_scale = 1.0,
  season_c0_scale = 0.5
)
gg_block <- exdqlm_multivar_create_block_diag(built$model$GG, 4)
ff_block <- exdqlm_multivar_create_block_diag(built$model$FF, 4)
cat(sprintf("%d,%d|%d,%d", nrow(gg_block), ncol(gg_block), nrow(ff_block), ncol(ff_block)))
"""
        proc = self.run_script("Rscript", "--vanilla", "-e", r_code)
        self.assertEqual(proc.stdout.strip(), "24,24|24,4")

    def test_multivar_legacy_output_suffix_tracks_no_tf_contract(self) -> None:
        self.run_script(
            "python3",
            "scripts/build_he3_exdqlm_ablation_matrix.py",
            "--template",
            str(self.template_path),
        )
        cfg_path = (
            self.he3_config_dir
            / "multimodel_20211112_v8_eps180cf1_exdqlm_multivar_keep_he3_noTF.yaml"
        )
        r_code = f"""
source("R/unified/config.R")
cfg <- yaml::read_yaml("{cfg_path}")
cat(unified_resolve_exdqlm_multivar_legacy_output_suffix(cfg, default = "DISC"))
"""
        proc = self.run_script("Rscript", "--vanilla", "-e", r_code)
        self.assertEqual(proc.stdout.strip(), "simp")

    def test_audit_script_confirms_inheritance_and_runtime_hashes(self) -> None:
        self.run_script(
            "python3",
            "scripts/build_he3_exdqlm_ablation_matrix.py",
            "--template",
            str(self.template_path),
        )
        self.run_script(
            "python3",
            "scripts/validate_he3_exdqlm_ablation.py",
            "--matrix-dir",
            str(self.matrix_dir),
            "--template",
            str(self.template_path),
        )
        plan = pd.read_csv(self.matrix_dir / "matrix_plan.csv")
        required_rel_paths = [
            "inputs/shared/covariates/covariate_features.csv",
            "inputs/shared/covariates/cov_01_PPT.csv",
            "inputs/shared/covariates/cov_02_SOIL.csv",
            "inputs/shared/covariates/cov_03_PCA.csv",
            "fit/inputs/parameters.txt",
            "fit/inputs/retros_fit_adapter.csv",
            "fit/inputs/nws_fit_adapter.csv",
            "fit/inputs/glofas_fit_adapter.csv",
        ]

        for _, row in plan.iterrows():
            source_run_dir = Path(row["source_run_dir"])
            for rel_path in required_rel_paths:
                path = source_run_dir / rel_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"{row['cutoff']}|{rel_path}\n", encoding="utf-8")

            if row["launch_mode"] != "launch":
                continue

            run_dir = self.he3_root / "runs" / row["run_id"]
            for rel_path in required_rel_paths:
                dst = run_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text((source_run_dir / rel_path).read_text(encoding="utf-8"), encoding="utf-8")

            target_model_id = row["target_model_id"]
            tables_dir = run_dir / "post" / "outputs" / row["run_id"] / "tables"
            tables_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                [{"model_id": target_model_id, "mean_crps": 0.75}]
            ).to_csv(tables_dir / "crps_forecast_summary.csv", index=False)
            pd.DataFrame(
                [
                    {"lead_day": lead, "model_id": target_model_id, "crps": 0.75 + lead / 100.0}
                    for lead in range(1, 29)
                ]
            ).to_csv(tables_dir / "crps_forecast_per_time.csv", index=False)
            with (run_dir / "run_manifest.yaml").open("w", encoding="utf-8") as handle:
                yaml.safe_dump(
                    {"stages": {"report": {"status": "pass"}}},
                    handle,
                    sort_keys=False,
                )

        audit_dir = self.td / "audit"
        self.run_script(
            "python3",
            "scripts/audit_he3_exdqlm_ablation.py",
            "--matrix-dir",
            str(self.matrix_dir),
            "--output-dir",
            str(audit_dir),
            "--best-by-cutoff-csv",
            str(self.best_csv),
        )
        audit = pd.read_csv(audit_dir / "he3_ablation_audit.csv")
        self.assertEqual(len(audit), 25)
        self.assertTrue(audit["overall_ok"].all())
        lead = pd.read_csv(audit_dir / "he3_ablation_lead_buckets.csv")
        self.assertIn("lead_22_28", lead.columns)
        self.assertEqual(int((lead["variant"] == "full").sum()), 5)

    def test_sync_ablation_tables_updates_article_and_corrections_outputs(self) -> None:
        matrix_dir = self.td / "sync_matrix"
        artifact_root = self.td / "sync_artifacts"
        report_dir = artifact_root / "reports" / "he3_exdqlm_ablation"
        matrix_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)
        with (matrix_dir / "matrix_metadata.yaml").open("w", encoding="utf-8") as handle:
            yaml.safe_dump({"artifact_root": str(artifact_root)}, handle, sort_keys=False)

        variants = ["full", "noTrend", "noTF", "noH1", "noH2", "noH3"]
        rows = []
        for cutoff_idx, (cutoff, _epsilon, _crps) in enumerate(CUTOFFS):
            for variant_idx, variant in enumerate(variants):
                rows.append(
                    {
                        "cutoff": cutoff,
                        "cutoff_display": f"display-{cutoff}",
                        "variant": variant,
                        "manuscript_label": variant,
                        "mean_crps": 0.10 + cutoff_idx / 10.0 + variant_idx / 100.0,
                        "status": "pass",
                        "best_epsilon_label": "cXX_epsYYY",
                    }
                )
        pd.DataFrame(rows).to_csv(report_dir / "he3_ablation_long.csv", index=False)
        pd.DataFrame(rows).to_csv(report_dir / "he3_ablation_wide.csv", index=False)
        (report_dir / "he3_ablation_summary.md").write_text("# summary\n", encoding="utf-8")
        (report_dir / "he3_table_rows.tex").write_text("% rows\n", encoding="utf-8")
        audit_dir = report_dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"ok": True}]).to_csv(audit_dir / "he3_ablation_audit.csv", index=False)
        pd.DataFrame([{"lead_01_07": 0.1}]).to_csv(audit_dir / "he3_ablation_lead_buckets.csv", index=False)
        (audit_dir / "he3_ablation_audit.md").write_text("# audit\n", encoding="utf-8")

        article_root = self.td / "article"
        raw_root = article_root / "artifacts" / "five_cutoff_crps_validation_sources"
        for cutoff, _epsilon, _crps in CUTOFFS:
            slug = {
                "20210123": "20210123_exal_m_t1",
                "20211112": "20211112_exal_m_t1",
                "20211221": "20211221_exal_m_t1",
                "20220511": "20220511_exal_m_t1",
                "20221225": "20221225_exal_m_t1",
            }[cutoff]
            table_dir = raw_root / slug
            table_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                [
                    {"model_id": "glofas_ensemble", "mean_crps": 1.1},
                    {"model_id": "nws_nwm_ensemble", "mean_crps": 1.2},
                ]
            ).to_csv(table_dir / "crps_forecast_summary.csv", index=False)
        (article_root / "tables" / "generated_tex").mkdir(parents=True, exist_ok=True)
        (article_root / "tables" / "generated_tex" / "manifest.csv").write_text(
            "table_label,row_label,source_class,source_note\n",
            encoding="utf-8",
        )
        (article_root / "MANUSCRIPT_ASSET_MANIFEST.json").write_text(
            json.dumps({"tables": {}}) + "\n",
            encoding="utf-8",
        )
        (article_root / "wileyNJD-APA.tex").write_text(
            "Before\n\\section{INTERPRETATION OF THE SELECTED SPECIFICATION}\nAfter\n",
            encoding="utf-8",
        )

        corrections_root = self.td / "corrections"
        corrections_root.mkdir(parents=True, exist_ok=True)
        (corrections_root / "main.tex").write_text(
            "\\begin{center}\n"
            "\\scriptsize\n"
            "\\setlength{\\tabcolsep}{4pt}\n"
            "\\begin{tabular}{>{\\ttfamily}l c c c c c}\n"
            "\\toprule\n"
            "Ablation model & old \\\\\n"
            "\\bottomrule\n"
            "\\end{tabular}\n"
            "\\end{center}\n",
            encoding="utf-8",
        )

        self.run_script(
            "python3",
            "scripts/sync_he3_ablation_article_tables.py",
            "--matrix-dir",
            str(matrix_dir),
            "--article-root",
            str(article_root),
            "--corrections-root",
            str(corrections_root),
        )

        table_text = (article_root / "tables" / "generated_tex" / "he3_ablation_crps_main_table.tex").read_text(
            encoding="utf-8"
        )
        self.assertIn("exAL-M-T1-noTrend", table_text)
        self.assertIn("\\textbf{0.1000}", table_text)
        self.assertIn(
            "\\input{tables/generated_tex/he3_ablation_crps_main_table.tex}",
            (article_root / "wileyNJD-APA.tex").read_text(encoding="utf-8"),
        )
        manifest = json.loads((article_root / "MANUSCRIPT_ASSET_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertIn("tab:he3_ablation_crps", manifest["tables"])
        corrections_text = (corrections_root / "main.tex").read_text(encoding="utf-8")
        self.assertIn("RAW-GLOFAS", corrections_text)
        self.assertNotIn("Ablation model & old", corrections_text)


if __name__ == "__main__":
    unittest.main()
