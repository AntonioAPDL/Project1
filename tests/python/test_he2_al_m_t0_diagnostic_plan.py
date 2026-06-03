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
            self.assertTrue(metadata["no_launch"])
            self.assertFalse(metadata["launch_files_written"])
            self.assertTrue(metadata["requires_user_discount_decision"])
            self.assertEqual(metadata["lane_scope"], "representative")
            self.assertEqual(len(rows), 4)
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


if __name__ == "__main__":
    unittest.main()
