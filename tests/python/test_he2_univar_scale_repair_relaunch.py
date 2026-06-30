from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "config" / "he2_bayesian_publication_relaunch_univar_al_exal_scale_repair_20260629.template.yaml"
BATCH = ROOT / "config" / "he2_relaunch_batches" / "univar_al_exal_scale_repair_20260629.yaml"
BUILDER = ROOT / "scripts" / "build_he2_bayesian_publication_relaunch_configs.py"
VALIDATOR = ROOT / "scripts" / "validate_he2_bayesian_publication_relaunch_prelaunch.py"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


class He2UnivarScaleRepairRelaunchTests(unittest.TestCase):
    def test_template_and_batch_encode_repair_scope(self) -> None:
        template = load_yaml(TEMPLATE)
        batch = load_yaml(BATCH)

        self.assertTrue(template["campaign"]["artifact_root"].endswith("multimodel_v8_he2_univar_al_exal_scale_repair_20260629"))
        self.assertEqual(template["bundles"]["bundle_run_id"], "20260510_publication_shared_r01")
        self.assertEqual(template["bundles"]["data_start"], "1987-05-29")
        self.assertEqual(set(template["campaign"]["families"]), {"exdqlm_univar", "dqlm_univar_al"})
        self.assertEqual(set(batch["selection"]["families"]), {"exdqlm_univar", "dqlm_univar_al"})
        self.assertEqual(batch["resources"]["fit_parallel_workers"], 7)
        self.assertEqual(batch["resources"]["mc_cores"], 7)
        self.assertEqual(batch["queue"]["ordinary_max_concurrent"], 4)
        self.assertEqual(batch["queue"]["heavy_cutoff_max_concurrent"], 4)
        self.assertFalse(batch["queue"]["heavy_cutoff_blocks_ordinary"])

        scale_contract = template["scale_contract"]
        self.assertEqual(scale_contract["legacy_fit_input_scale"], "log1p_cms")
        self.assertEqual(scale_contract["legacy_post_input_scale"], "log1p_cms")
        self.assertEqual(scale_contract["analysis_scale_fit_internal"], "log1p_cms")
        self.assertEqual(scale_contract["analysis_scale_post_internal"], "log1p_cms")
        self.assertEqual(scale_contract["transform_policy"], "log1p_only")

    def test_builder_generates_log1p_only_al_and_exal_rows(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_univar_scale_repair_builder_") as tmp:
            tmp_root = Path(tmp)
            artifact_root = tmp_root / "artifact"
            matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
            config_dir = artifact_root / "control" / "generated_configs"
            completed = subprocess.run(
                [
                    "python3",
                    str(BUILDER),
                    "--config",
                    str(TEMPLATE),
                    "--batch-file",
                    str(BATCH),
                    "--artifact-root",
                    str(artifact_root),
                    "--matrix-dir",
                    str(matrix_dir),
                    "--config-output-dir",
                    str(config_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            rows = read_csv(matrix_dir / "selection_summary.csv")
            self.assertEqual(len(rows), 10)
            self.assertEqual({row["family_id"] for row in rows}, {"exdqlm_univar", "dqlm_univar_al"})
            self.assertEqual(sum(int(row["quantile_submodels"]) for row in rows), 70)

            launch_settings = (matrix_dir / "launch_settings.env").read_text(encoding="utf-8")
            self.assertIn("ORDINARY_MAX_CONCURRENT=4", launch_settings)
            self.assertIn("HEAVY_CUTOFF_MAX_CONCURRENT=4", launch_settings)
            self.assertIn("HEAVY_CUTOFF_BLOCKS_ORDINARY=0", launch_settings)

            frozen = read_csv(matrix_dir / "frozen_spec_manifest.csv")
            self.assertEqual(len(frozen), 10)
            for row in frozen:
                self.assertEqual(row["legacy_fit_input_scale"], "log1p_cms")
                self.assertEqual(row["legacy_post_input_scale"], "log1p_cms")
                self.assertEqual(row["analysis_scale_fit_internal"], "log1p_cms")
                self.assertEqual(row["analysis_scale_post_internal"], "log1p_cms")
                self.assertEqual(row["transform_policy"], "log1p_only")
                self.assertEqual(row["active_quantile_count"], "7")
                self.assertEqual(row["fit_parallel_workers"], "7")
                self.assertEqual(row["run_mc_cores"], "7")
                if row["family"] == "exdqlm_univar":
                    self.assertEqual(row["likelihood_mode"], "exal")
                elif row["family"] == "dqlm_univar_al":
                    self.assertEqual(row["likelihood_mode"], "al")
                else:
                    self.fail(f"unexpected family {row['family']}")

            generated_config = load_yaml(Path(rows[0]["config_path"]))
            self.assertEqual(generated_config["scale_contract"]["transform_policy"], "log1p_only")
            self.assertEqual(generated_config["inputs"]["fit"]["retros_storage_scale"], "log1p_cms")
            self.assertEqual(generated_config["inputs"]["fit"]["nws_storage_scale"], "raw_cms")
            self.assertEqual(generated_config["inputs"]["fit"]["glofas_storage_scale"], "raw_cms")

    def test_prelaunch_validator_guards_univariate_scale_contract(self) -> None:
        text = VALIDATOR.read_text(encoding="utf-8")
        for needle in [
            "FORBIDDEN_LEGACY_UNIVAR_TRANSFORMS",
            "_validate_legacy_univar_scale_source_contract",
            "_validate_generated_config_scale_contract",
            "generated_config_scale_contract",
            "transform_policy",
            "log1p_only",
        ]:
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
