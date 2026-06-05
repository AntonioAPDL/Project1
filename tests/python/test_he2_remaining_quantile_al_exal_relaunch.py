from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
AL_DROP_BUILDER = ROOT / "scripts" / "build_he2_dqlm_multivar_al_drop_from_exal_drop.py"
AL_DROP_VALIDATOR = ROOT / "scripts" / "validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py"
AL_DROP_DIAGNOSTIC_BUILDER = ROOT / "scripts" / "build_he2_dqlm_multivar_al_drop_diagnostic_plan.py"
AL_DROP_DIAGNOSTIC_VALIDATOR = ROOT / "scripts" / "validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py"
UNIVAR_TEMPLATE = ROOT / "config" / "he2_bayesian_publication_relaunch_univar_al_exal_20260603.template.yaml"
UNIVAR_BATCH = ROOT / "config" / "he2_relaunch_batches" / "univar_al_exal_publication_relaunch_20260603.yaml"
AL_DROP_DIAGNOSTIC_SPEC_TEMPLATE = ROOT / "config" / "he2_relaunch_batches" / "al_m_t0_diagnostic_discount_spec_template_20260603.yaml"
AL_DROP_P3_PRODUCTION_SPEC = ROOT / "config" / "he2_relaunch_batches" / "al_m_t0_p3_production_overlay_20260605.yaml"
LAUNCHER = ROOT / "scripts" / "launch_he2_remaining_quantile_al_exal.py"


class He2RemainingQuantileAlExalRelaunchTests(unittest.TestCase):
    def load_yaml(self, path: Path) -> dict:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_required_tracked_files_exist(self) -> None:
        for path in [
            AL_DROP_BUILDER,
            AL_DROP_VALIDATOR,
            AL_DROP_DIAGNOSTIC_BUILDER,
            AL_DROP_DIAGNOSTIC_VALIDATOR,
            AL_DROP_DIAGNOSTIC_SPEC_TEMPLATE,
            AL_DROP_P3_PRODUCTION_SPEC,
            UNIVAR_TEMPLATE,
            UNIVAR_BATCH,
            LAUNCHER,
        ]:
            self.assertTrue(path.exists(), path)

    def test_univar_template_and_batch_scope(self) -> None:
        template = self.load_yaml(UNIVAR_TEMPLATE)
        batch = self.load_yaml(UNIVAR_BATCH)
        self.assertEqual(
            template["campaign"]["artifact_root"],
            "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603",
        )
        self.assertEqual(template["bundles"]["bundle_run_id"], "20260510_publication_shared_r01")
        self.assertEqual(template["bundles"]["data_start"], "1987-05-29")
        self.assertEqual(set(template["campaign"]["families"]), {"exdqlm_univar", "dqlm_univar_al"})
        self.assertEqual(set(batch["selection"]["families"]), {"exdqlm_univar", "dqlm_univar_al"})
        self.assertEqual(batch["resources"]["fit_parallel_workers"], 7)
        self.assertEqual(batch["queue"]["ordinary_max_concurrent"], 2)
        self.assertFalse(batch["queue"]["heavy_cutoff_blocks_ordinary"])
        validation = template["validation"]
        self.assertEqual(validation["full_pipeline_quantile_smoke_cases"][0]["family"], "exdqlm_univar")
        self.assertEqual(validation["full_pipeline_quantile_smoke_cases"][0]["quantiles"], [0.35, 0.5])
        self.assertEqual(validation["full_pipeline_univar_quantile_family"], "dqlm_univar_al")
        self.assertEqual(validation["full_pipeline_univar_quantiles"], [0.35, 0.5])
        family_patches = {
            item["family"]: item["config_patch"]["models"]["exdqlm_univar"]
            for item in batch["overrides"]["row_config_patches"]
            if "family" in item and "models" in item.get("config_patch", {})
        }
        self.assertEqual(family_patches["exdqlm_univar"]["likelihood_mode"], "exal")
        self.assertEqual(family_patches["dqlm_univar_al"]["likelihood_mode"], "al")
        for patch in family_patches.values():
            state = patch["state_evolution"]
            self.assertEqual(state["df_t"], 0.99999999)
            self.assertEqual(state["df_s1"], 0.99999)
            self.assertEqual(state["df_s2"], 0.99999)
            self.assertEqual(state["df_s67"], 0.99999)
            self.assertEqual(state["lambda"], 0.97)

    def test_univar_builder_selects_ten_rows_and_canonical_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_univar_al_exal_builder_") as tmp:
            tmp_root = Path(tmp)
            artifact_root = tmp_root / "artifact"
            matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
            config_dir = artifact_root / "control" / "generated_configs"
            cmd = [
                "python3",
                "scripts/build_he2_bayesian_publication_relaunch_configs.py",
                "--config",
                str(UNIVAR_TEMPLATE),
                "--batch-file",
                str(UNIVAR_BATCH),
                "--profile",
                "disk_guarded_parallel",
                "--artifact-root",
                str(artifact_root),
                "--matrix-dir",
                str(matrix_dir),
                "--config-output-dir",
                str(config_dir),
            ]
            completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            rows = self.read_csv(matrix_dir / "selection_summary.csv")
            self.assertEqual(len(rows), 10)
            self.assertEqual({row["family_id"] for row in rows}, {"exdqlm_univar", "dqlm_univar_al"})
            self.assertEqual(sum(int(row["quantile_submodels"]) for row in rows), 70)
            frozen = self.read_csv(matrix_dir / "frozen_spec_manifest.csv")
            self.assertEqual(len(frozen), 10)
            for row in frozen:
                self.assertEqual(row["legacy_fit_input_scale"], "log1p_cms")
                self.assertEqual(row["legacy_post_input_scale"], "log1p_cms")
                self.assertEqual(row["active_quantile_count"], "7")
                self.assertEqual(row["fit_parallel_workers"], "7")
                self.assertEqual(row["run_mc_cores"], "7")
                if row["family"] == "exdqlm_univar":
                    self.assertEqual(row["likelihood_mode"], "exal")
                if row["family"] == "dqlm_univar_al":
                    self.assertEqual(row["likelihood_mode"], "al")
            audit = self.read_csv(matrix_dir / "cutoff_bundle_audit.csv")
            self.assertEqual({row["retros_start"] for row in audit}, {"1987-05-29"})
            self.assertEqual({row["deterministic_precip_source"] for row in audit}, {"gefs_apcp"})
            self.assertEqual({row["deterministic_soil_source"] for row in audit}, {"gefs_soilw_0_0.1m"})

    def test_al_drop_builder_clones_promoted_exal_drop_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_drop_clone_builder_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            completed = subprocess.run(
                ["python3", str(AL_DROP_BUILDER), "--artifact-root", str(artifact_root)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
            rows = self.read_csv(matrix_dir / "matrix_plan.csv")
            self.assertEqual(len(rows), 5)
            self.assertEqual({row["family_id"] for row in rows}, {"dqlm_multivar_al_drop"})
            self.assertEqual(sum(int(row["quantile_submodels"]) for row in rows), 35)
            for row in rows:
                cfg = self.load_yaml(Path(row["config_path"]))
                self.assertEqual(cfg["models"]["exdqlm_multivar"]["likelihood_mode"], "al")
                self.assertEqual(cfg["models"]["exdqlm_multivar"]["forecast_transfer_mode"], "drop")
                self.assertEqual(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"], 30.0)
                self.assertEqual(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["c_factor"], 1.0)
                self.assertEqual(cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["max_iter"], 100)
                self.assertEqual(cfg["scale_contract"]["legacy_fit_input_scale"], "log1p_cms")
                self.assertEqual(cfg["models"]["exdqlm_multivar"]["structure"]["enabled_harmonic_indices"], [1, 2, 3])
            clone_rows = self.read_csv(matrix_dir / "source_clone_manifest.csv")
            self.assertEqual({row["only_intended_scientific_change"] for row in clone_rows}, {"likelihood_mode exal -> al"})

    def test_al_drop_builder_applies_p3_production_overlay_for_smoke_cutoffs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_drop_p3_builder_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            completed = subprocess.run(
                [
                    "python3",
                    str(AL_DROP_BUILDER),
                    "--artifact-root",
                    str(artifact_root),
                    "--policy-spec-yaml",
                    str(AL_DROP_P3_PRODUCTION_SPEC),
                    "--cutoffs",
                    "20211112,20220511",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
            rows = self.read_csv(matrix_dir / "matrix_plan.csv")
            self.assertEqual([row["cutoff"] for row in rows], ["20211112", "20220511"])
            self.assertEqual({row["policy_spec_id"] for row in rows}, {"al_m_t0_p3_production_highdf_eps365_cf1_20260605"})
            for row in rows:
                cfg = self.load_yaml(Path(row["config_path"]))
                self.assertEqual(cfg["models"]["exdqlm_multivar"]["likelihood_mode"], "al")
                self.assertEqual(cfg["models"]["exdqlm_multivar"]["forecast_transfer_mode"], "drop")
                self.assertEqual(cfg["models"]["exdqlm_multivar"]["structure"]["enabled_harmonic_indices"], [1, 2, 3])
                self.assertEqual([item["name"] for item in cfg["inputs"]["fit"]["covariates"]], ["PPT", "SOIL", "PCA"])
                self.assertEqual(cfg["inputs"]["covariate_features"]["lag_orders"], [1, 2, 3])
                self.assertTrue(cfg["inputs"]["covariate_features"]["include_squares"])
                self.assertTrue(cfg["inputs"]["covariate_features"]["include_interaction"])
                self.assertEqual(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"], 365.0)
                self.assertEqual(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["c_factor"], 1.0)
                self.assertTrue(cfg["fit"]["exdqlm_multivar"]["legacy"]["post_save_objective_enabled"])
                self.assertFalse(cfg["fit"]["exdqlm_multivar"]["legacy"]["post_save_jsd_enabled"])
                state = cfg["models"]["exdqlm_multivar"]["state_evolution"]
                self.assertEqual(state["df_t"], 0.99999999)
                self.assertEqual(state["df_s1"], 0.99999999)
                self.assertEqual(state["df_s2"], 0.99999999)
                self.assertEqual(state["df_s67"], 0.99999999)
                self.assertEqual(state["df_discrep"], 0.99999999)
                self.assertEqual(state["df_trans"], 0.99999999)
                self.assertEqual(state["df_covs"], 0.99999999)
                gamma_sigma = cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]
                self.assertEqual(gamma_sigma["max_iter"], 160)
                self.assertEqual(gamma_sigma["min_update_iters"], 50)
                self.assertEqual(gamma_sigma["min_total_iters"], 50)
                self.assertEqual(gamma_sigma["quantile_overrides"]["q35"]["freeze_target"], "gamma_sigma")
                self.assertEqual(gamma_sigma["quantile_overrides"]["q65"]["freeze_target"], "gamma_sigma")
                self.assertNotIn("q50", gamma_sigma["quantile_overrides"])
                self.assertFalse(
                    any(
                        isinstance(value, dict) and value.get("freeze_target") == "states"
                        for value in gamma_sigma["quantile_overrides"].values()
                    )
                )
                self.assertTrue(gamma_sigma["quantile_overrides"]["q35"]["stabilization"]["state_guard_enabled"])
                self.assertTrue(gamma_sigma["quantile_overrides"]["q65"]["stabilization"]["state_guard_enabled"])
                self.assertEqual(cfg["debug_he2_dqlm_al_drop_policy_overlay"]["spec_id"], "al_m_t0_p3_production_highdf_eps365_cf1_20260605")
                self.assertEqual(cfg["debug_he2_dqlm_al_drop_policy_overlay"]["gamma_sigma_dropped_quantile_overrides"], ["q50"])

    def test_al_drop_p3_prelaunch_validator_accepts_overlay_without_smoke(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_drop_p3_validator_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            completed = subprocess.run(
                [
                    "python3",
                    str(AL_DROP_VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--policy-spec-yaml",
                    str(AL_DROP_P3_PRODUCTION_SPEC),
                    "--cutoffs",
                    "20211112,20220511",
                    "--skip-smoke",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary_path = next((artifact_root / "control").glob("prelaunch_validation_*/prelaunch_validation_summary.json"))
            summary = self.load_yaml(summary_path)
            self.assertEqual(summary["policy_spec_id"], "al_m_t0_p3_production_highdf_eps365_cf1_20260605")
            self.assertEqual(summary["selected_cutoffs"], ["20211112", "20220511"])
            self.assertEqual(summary["checks"]["smoke_runs"]["skipped"], 1)

    def test_launcher_blocks_al_m_t0_by_default(self) -> None:
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("--include-blocked-al-drop", text)
        self.assertIn("blocked_not_launched", text)
        self.assertIn("requires targeted diagnostics/new discount spec before relaunch", text)


if __name__ == "__main__":
    unittest.main()
