from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts" / "build_he2_dqlm_multivar_al_drop_diagnostic_plan.py"
VALIDATOR = ROOT / "scripts" / "validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py"
LAUNCHER = ROOT / "scripts" / "launch_he2_al_m_t0_representative_diagnostics.py"
HIGHDF_SPEC = ROOT / "config" / "he2_relaunch_batches" / "al_m_t0_diagnostic_highdf_eps365_cf1_20260603.yaml"
P2_SPEC = ROOT / "config" / "he2_relaunch_batches" / "al_m_t0_scale_state_p2_force_gamma_sigma_highdf_eps365_cf1_20260604.yaml"


class He2AlMT0DiagnosticPlanTests(unittest.TestCase):
    def load_yaml(self, path: Path) -> dict:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_builder_prepares_representative_fit_only_no_launch_configs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_m_t0_diag_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            proc = subprocess.run(
                ["python3", str(BUILDER), "--artifact-root", str(artifact_root), "--lane-scope", "representative"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            matrix_dir = artifact_root / "control" / "diagnostic_matrix"
            metadata = self.load_yaml(matrix_dir / "diagnostic_matrix_metadata.yaml")
            rows = self.read_csv(matrix_dir / "diagnostic_matrix_plan.csv")
            queue_rows = self.read_csv(matrix_dir / "matrix_plan.csv")
            self.assertTrue(metadata["no_launch"])
            self.assertFalse(metadata["launch_files_written"])
            self.assertTrue(metadata["requires_user_discount_decision"])
            self.assertEqual(metadata["lane_scope"], "representative")
            self.assertEqual(len(rows), 4)
            self.assertEqual(len(queue_rows), 4)
            self.assertEqual({row["run_scope"] for row in queue_rows}, {"diagnostic_single_quantile_fit_only"})
            self.assertTrue((matrix_dir / "NO_LAUNCH_GUARD.txt").exists())
            self.assertFalse((matrix_dir / "launch_al_drop_diagnostics.sh").exists())
            for row in rows:
                self.assertEqual(row["family_id"], "dqlm_multivar_al_drop")
                self.assertEqual(row["likelihood_mode"], "al")
                self.assertEqual(row["transfer_mode"], "drop")
                self.assertEqual(row["no_launch"], "True")
                cfg = self.load_yaml(Path(row["config_path"]))
                self.assertEqual(cfg["fit"]["quantiles"], [int(row["q"]) / 100.0])
                self.assertEqual(cfg["fit"]["parallel"]["workers"], 1)
                self.assertEqual(cfg["run"]["threads"]["mc_cores"], 1)
                self.assertTrue(cfg["stages"]["data_prep_shared"])
                self.assertTrue(cfg["stages"]["fit"])
                self.assertFalse(cfg["stages"]["post"])
                self.assertFalse(cfg["stages"]["validate"])
                self.assertFalse(cfg["stages"]["report"])
                self.assertTrue(cfg["debug_he2_al_m_t0_diagnostic"]["no_launch"])

    def test_validator_accepts_discount_override_without_launching(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_m_t0_diag_override_") as tmp:
            tmp_root = Path(tmp)
            artifact_root = tmp_root / "artifact"
            spec = tmp_root / "override.yaml"
            spec.write_text(
                yaml.safe_dump(
                    {
                        "spec_id": "unit_test_al_spec",
                        "requires_user_discount_decision": False,
                        "state_evolution": {
                            "df_t": 0.999999,
                            "df_s1": 0.99999,
                            "df_s2": 0.99999,
                            "df_s67": 0.99999,
                            "df_discrep": 0.99999,
                            "lambda": 0.97,
                            "df_trans": 0.9999999,
                            "df_covs": 0.9999999,
                        },
                        "forecast_cov": {"epsilon": 90.0, "c_factor": 1.0},
                        "gamma_sigma": {"max_iter": 100},
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--discount-spec-yaml",
                    str(spec),
                    "--lane-scope",
                    "representative",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            matrix_dir = artifact_root / "control" / "diagnostic_matrix"
            rows = self.read_csv(matrix_dir / "diagnostic_matrix_plan.csv")
            self.assertEqual({row["spec_id"] for row in rows}, {"unit_test_al_spec"})
            self.assertEqual({row["forecast_cov_epsilon"] for row in rows}, {"90.0"})
            self.assertEqual({row["requires_user_discount_decision"] for row in rows}, {"False"})
            cfg = self.load_yaml(Path(rows[0]["config_path"]))
            self.assertEqual(cfg["models"]["exdqlm_multivar"]["state_evolution"]["df_t"], 0.999999)
            self.assertEqual(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"], 90.0)
            summary = self.load_yaml(artifact_root / "control" / "diagnostic_validation" / "diagnostic_validation_summary.json")
            self.assertFalse(summary["launch_performed"])
            self.assertEqual(summary["checks"]["queue_rows"], 4)

    def test_tracked_highdf_spec_is_concrete_and_validated_without_launching(self) -> None:
        spec = self.load_yaml(HIGHDF_SPEC)
        self.assertEqual(spec["spec_id"], "highdf_eps365_cf1_al_m_t0_20260603")
        self.assertFalse(spec["requires_user_discount_decision"])
        self.assertEqual(
            spec["state_evolution"],
            {
                "df_t": 0.99999999,
                "df_s1": 0.99999999,
                "df_s2": 0.99999999,
                "df_s67": 0.99999999,
                "df_discrep": 0.99999999,
                "lambda": 0.97,
                "df_trans": 0.99999999,
                "df_covs": 0.99999999,
            },
        )
        self.assertEqual(spec["forecast_cov"], {"epsilon": 365.0, "c_factor": 1.0})
        self.assertEqual(spec["gamma_sigma"], {"max_iter": 100})
        with tempfile.TemporaryDirectory(prefix="he2_al_m_t0_diag_highdf_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            proc = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--discount-spec-yaml",
                    str(HIGHDF_SPEC),
                    "--lane-scope",
                    "representative",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            matrix_dir = artifact_root / "control" / "diagnostic_matrix"
            rows = self.read_csv(matrix_dir / "diagnostic_matrix_plan.csv")
            self.assertEqual(len(rows), 4)
            self.assertEqual({row["spec_id"] for row in rows}, {"highdf_eps365_cf1_al_m_t0_20260603"})
            self.assertEqual({row["requires_user_discount_decision"] for row in rows}, {"False"})
            self.assertEqual({row["forecast_cov_epsilon"] for row in rows}, {"365.0"})
            self.assertEqual({row["c_factor"] for row in rows}, {"1.0"})
            self.assertEqual({row["max_iter"] for row in rows}, {"100"})
            queue_rows = self.read_csv(matrix_dir / "matrix_plan.csv")
            self.assertEqual({row["spec_id"] for row in queue_rows}, {"highdf_eps365_cf1_al_m_t0_20260603"})
            self.assertEqual({row["active_quantiles"] for row in queue_rows}, {"0.35", "0.65", "0.80"})
            cfg = self.load_yaml(Path(rows[0]["config_path"]))
            self.assertEqual(cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["max_iter"], 100)
            self.assertEqual(cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"], 365.0)
            self.assertEqual(cfg["models"]["exdqlm_multivar"]["state_evolution"]["df_discrep"], 0.99999999)
            self.assertFalse((matrix_dir / "launch_al_drop_diagnostics.sh").exists())

    def test_ladder_package_prepares_a0_to_a4_transfer_variants(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_m_t0_diag_ladder_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            proc = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--discount-spec-yaml",
                    str(HIGHDF_SPEC),
                    "--lane-scope",
                    "representative",
                    "--experiment-scope",
                    "ladder",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            matrix_dir = artifact_root / "control" / "diagnostic_matrix"
            metadata = self.load_yaml(matrix_dir / "diagnostic_matrix_metadata.yaml")
            rows = self.read_csv(matrix_dir / "diagnostic_matrix_plan.csv")
            queue_rows = self.read_csv(matrix_dir / "matrix_plan.csv")
            self.assertEqual(metadata["experiment_scope"], "ladder")
            self.assertEqual(metadata["n_experiments"], 5)
            self.assertEqual(len(rows), 20)
            self.assertEqual(len(queue_rows), 20)
            self.assertEqual(
                {row["experiment_id"] for row in rows},
                {
                    "a0_full_sd",
                    "a1_transfer_level_only",
                    "a2_full_zscore",
                    "a3_base_sd",
                    "a4_base_zscore",
                },
            )
            by_experiment = {row["experiment_id"]: row for row in rows}
            self.assertEqual(by_experiment["a1_transfer_level_only"]["transfer_feature_mode"], "none")
            self.assertEqual(by_experiment["a1_transfer_level_only"]["transfer_feature_columns"], "")
            self.assertEqual(by_experiment["a2_full_zscore"]["transfer_feature_scaling"], "zscore")
            self.assertEqual(by_experiment["a3_base_sd"]["transfer_feature_mode"], "base_only")
            self.assertEqual(by_experiment["a4_base_zscore"]["transfer_feature_scaling"], "zscore")
            a1_cfg = self.load_yaml(Path(by_experiment["a1_transfer_level_only"]["config_path"]))
            self.assertEqual(a1_cfg["inputs"]["transfer_function_covariates"]["mode"], "none")
            self.assertEqual(a1_cfg["inputs"]["transfer_function_covariates"]["base_covariates"], [])
            self.assertEqual(a1_cfg["inputs"]["transfer_function_covariates"]["engineered_terms"], [])
            a2_cfg = self.load_yaml(Path(by_experiment["a2_full_zscore"]["config_path"]))
            self.assertEqual(a2_cfg["inputs"]["transfer_function_covariates"]["mode"], "full")
            self.assertEqual(a2_cfg["inputs"]["transfer_function_covariates"]["scaling"], "zscore")

    def test_scale_state_policy_override_deep_merges_quantile_overrides(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_m_t0_scale_state_p2_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            proc = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--discount-spec-yaml",
                    str(P2_SPEC),
                    "--lane-scope",
                    "representative",
                    "--experiment-scope",
                    "a1",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            rows = self.read_csv(artifact_root / "control" / "diagnostic_matrix" / "diagnostic_matrix_plan.csv")
            by_q = {row["q"]: self.load_yaml(Path(row["config_path"])) for row in rows}
            q35_policy = by_q["35"]["fit"]["exdqlm_multivar"]["gamma_sigma"]["quantile_overrides"]["q35"]
            q65_policy = by_q["65"]["fit"]["exdqlm_multivar"]["gamma_sigma"]["quantile_overrides"]["q65"]
            q80_policy = by_q["80"]["fit"]["exdqlm_multivar"]["gamma_sigma"]["quantile_overrides"]["q80"]
            self.assertEqual(q35_policy["freeze_target"], "gamma_sigma")
            self.assertEqual(q65_policy["freeze_target"], "gamma_sigma")
            self.assertTrue(q35_policy["stabilization"]["state_guard_enabled"])
            self.assertTrue(q65_policy["stabilization"]["state_guard_enabled"])
            self.assertEqual(q80_policy["init"]["sigma_floor"], 0.01)
            self.assertNotIn("freeze_target", q80_policy)

    def test_single_a1_scope_prepares_transfer_level_only_rows(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_m_t0_diag_a1_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            proc = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--discount-spec-yaml",
                    str(HIGHDF_SPEC),
                    "--lane-scope",
                    "representative",
                    "--experiment-scope",
                    "a1",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            matrix_dir = artifact_root / "control" / "diagnostic_matrix"
            rows = self.read_csv(matrix_dir / "diagnostic_matrix_plan.csv")
            self.assertEqual(len(rows), 4)
            self.assertEqual({row["experiment_id"] for row in rows}, {"a1_transfer_level_only"})
            for row in rows:
                cfg = self.load_yaml(Path(row["config_path"]))
                transfer = cfg["inputs"]["transfer_function_covariates"]
                self.assertEqual(transfer["mode"], "none")
                self.assertEqual(transfer["base_covariates"], [])
                self.assertEqual(transfer["engineered_terms"], [])

    def test_representative_launcher_dry_run_records_no_process_launch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_m_t0_diag_launch_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            build_proc = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--discount-spec-yaml",
                    str(HIGHDF_SPEC),
                    "--lane-scope",
                    "representative",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(build_proc.returncode, 0, build_proc.stderr)
            launch_proc = subprocess.run(
                [
                    "python3",
                    str(LAUNCHER),
                    "--artifact-root",
                    str(artifact_root),
                    "--dry-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(launch_proc.returncode, 0, launch_proc.stderr)
            matrix_dir = artifact_root / "control" / "diagnostic_matrix"
            launch_rows = self.read_csv(matrix_dir / "diagnostic_launch_manifest.csv")
            self.assertEqual(len(launch_rows), 4)
            self.assertEqual({row["launch_action"] for row in launch_rows}, {"dry_run"})
            launch_metadata = self.load_yaml(matrix_dir / "diagnostic_launch_metadata.json")
            self.assertTrue(launch_metadata["dry_run"])
            self.assertEqual(launch_metadata["launched"], 0)

    def test_ladder_launcher_dry_run_records_all_twenty_rows(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_m_t0_diag_ladder_launch_") as tmp:
            artifact_root = Path(tmp) / "artifact"
            build_proc = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--discount-spec-yaml",
                    str(HIGHDF_SPEC),
                    "--lane-scope",
                    "representative",
                    "--experiment-scope",
                    "ladder",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(build_proc.returncode, 0, build_proc.stderr)
            launch_proc = subprocess.run(
                [
                    "python3",
                    str(LAUNCHER),
                    "--artifact-root",
                    str(artifact_root),
                    "--expected-experiment-scope",
                    "ladder",
                    "--dry-run",
                    "--max-concurrent",
                    "20",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(launch_proc.returncode, 0, launch_proc.stderr)
            matrix_dir = artifact_root / "control" / "diagnostic_matrix"
            launch_rows = self.read_csv(matrix_dir / "diagnostic_launch_manifest.csv")
            self.assertEqual(len(launch_rows), 20)
            self.assertEqual({row["launch_action"] for row in launch_rows}, {"dry_run"})
            self.assertEqual(
                {row["experiment_id"] for row in launch_rows},
                {
                    "a0_full_sd",
                    "a1_transfer_level_only",
                    "a2_full_zscore",
                    "a3_base_sd",
                    "a4_base_zscore",
                },
            )


if __name__ == "__main__":
    unittest.main()
