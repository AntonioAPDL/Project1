from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "multimodel_v8_ndlm_featurecov_rerun.template.yaml"
BUILDER = ROOT / "scripts" / "build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py"


def parse_builder_stdout(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in {
            "artifact_root",
            "matrix_dir",
            "config_output_dir",
            "generated_configs",
            "plan_rows",
            "selection_rows",
            "spec_rows",
        }:
            out[key.strip()] = value.strip()
    return out


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


class NdLmFeaturecovRerunBuilderTest(unittest.TestCase):
    def test_builder_emits_corrected_featurecov_ndlm_configs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ndlm_featurecov_builder_") as tmpdir:
            tmp = Path(tmpdir)
            artifact_root = tmp / "artifact_root"
            matrix_dir = tmp / "matrix_dir"
            config_dir = tmp / "configs"
            proc = subprocess.run(
                [
                    "python3",
                    str(BUILDER),
                    "--config",
                    str(CONFIG),
                    "--artifact-root",
                    str(artifact_root),
                    "--matrix-dir",
                    str(matrix_dir),
                    "--config-output-dir",
                    str(config_dir),
                    "--cutoffs",
                    "20210123",
                    "20211112",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
            info = parse_builder_stdout(proc.stdout)
            self.assertEqual(info["generated_configs"], "6")
            self.assertEqual(info["plan_rows"], "6")
            self.assertEqual(info["selection_rows"], "6")
            self.assertGreaterEqual(int(info["spec_rows"]), 20)

            with (matrix_dir / "matrix_plan.csv").open("r", encoding="utf-8") as handle:
                plan_rows = list(csv.DictReader(handle))
            self.assertEqual(len(plan_rows), 6)
            families = {row["family_id"] for row in plan_rows}
            self.assertEqual(families, {"ndlm_main_keep", "ndlm_main_drop", "ndlm_univar_keep"})
            cutoffs = {row["cutoff"] for row in plan_rows}
            self.assertEqual(cutoffs, {"20210123", "20211112"})

            configs = sorted(config_dir.glob("*.yaml"))
            self.assertEqual(len(configs), 6)
            for path in configs:
                payload = load_yaml(path)
                covs = payload["inputs"]["fit"]["covariates"]
                self.assertEqual([row["name"] for row in covs], ["PPT", "SOIL", "PCA"])
                self.assertTrue(payload["inputs"]["deterministic_climate"]["enabled"])
                self.assertTrue(payload["inputs"]["covariate_features"]["enabled"])
                self.assertFalse(payload["inputs"]["shared"]["prefer_forecats_snapshot"])
                self.assertTrue(Path(payload["inputs"]["fit"]["usgs_cache_path"]).is_file())
                debug = payload["debug_ndlm_featurecov_rerun"]
                self.assertIn("selected_source_run", debug)
                if payload["models"]["run_ndlm_main"]:
                    prior = payload["models"]["ndlm_main"]["prior"]["forecast_cov"]
                    self.assertEqual(prior["dof_offset"], 4)
                    self.assertEqual(prior["scale_mult"], 1.0)
                    self.assertEqual(payload["models"]["ndlm_main"]["state_evolution"]["df_covs"], 0.99999999)
                if payload["models"]["run_ndlm_univar"]:
                    prior = payload["models"]["ndlm_univar"]["prior"]
                    self.assertEqual(prior["n0"], 20)
                    self.assertEqual(prior["S0"], 1)
                    self.assertEqual(payload["models"]["ndlm_univar"]["state_evolution"]["df_covs"], 0.99999999)


if __name__ == "__main__":
    unittest.main()
