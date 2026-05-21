import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def write_source_config(path: Path) -> None:
    payload = {
        "run": {
            "run_id": "fixture_run",
            "run_root": "/tmp/fixture_run_root",
            "overwrite": False,
            "auto_suffix_on_collision": True,
            "threads": {"mc_cores": 1},
        },
        "fit": {
            "quantiles": [0.5],
            "parallel": {"workers": 1},
            "exdqlm_multivar": {
                "gamma_sigma": {
                    "max_iter": 10,
                    "warmup_freeze_iters": 3,
                    "min_update_iters": 7,
                    "min_total_iters": 8,
                    "quantile_overrides": {
                        "q50": {
                            "warmup_freeze_iters": 2,
                            "min_update_iters": 6,
                            "min_total_iters": 9,
                        }
                    },
                }
            },
        },
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


class TestExdqlmKeepAblationTooling(unittest.TestCase):
    def test_fixed_gamsig_ablation_exports_freeze_controls(self) -> None:
        script = PROJECT_ROOT / "repro" / "audits" / "prepare_exdqlm_keep_guarded_repro.py"
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            source_config = tmp / "source.yaml"
            write_source_config(source_config)
            result = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--source-config",
                    str(source_config),
                    "--tag",
                    "fixture_fixed_gamsig",
                    "--runtime-root",
                    str(tmp / "runtime"),
                    "--report-root",
                    str(tmp / "reports"),
                    "--max-iter",
                    "12",
                    "--quantiles",
                    "0.05,0.5",
                    "--workers",
                    "1",
                    "--ablation-mode",
                    "fixed-gamsig",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )
            manifest = json.loads(result.stdout)
            launch_text = Path(manifest["launch_path"]).read_text(encoding="utf-8")
            generated_cfg = yaml.safe_load(Path(manifest["config_path"]).read_text(encoding="utf-8"))
            policy = generated_cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]
            self.assertIn('export DISC_GAMSIG_FREEZE_TARGET="gamma_sigma"', launch_text)
            self.assertIn('export DISC_GAMSIG_FREEZE_ITERS="17"', launch_text)
            self.assertIn('export DISC_GAMSIG_MIN_UPDATE_ITERS="0"', launch_text)
            self.assertIn('export DISC_LATENT_ABLATION_MODE="free"', launch_text)
            self.assertEqual(policy["warmup_freeze_iters"], 17)
            self.assertEqual(policy["min_update_iters"], 0)
            self.assertEqual(policy["min_total_iters"], 12)
            self.assertEqual(policy["quantile_overrides"]["q50"]["warmup_freeze_iters"], 17)
            self.assertEqual(policy["quantile_overrides"]["q50"]["min_update_iters"], 0)
            self.assertEqual(policy["quantile_overrides"]["q50"]["min_total_iters"], 12)
            self.assertEqual(manifest["ablation_mode"], "fixed-gamsig")

    def test_latent_cap_ablation_exports_latent_controls(self) -> None:
        script = PROJECT_ROOT / "repro" / "audits" / "prepare_exdqlm_keep_guarded_repro.py"
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            source_config = tmp / "source.yaml"
            write_source_config(source_config)
            result = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--source-config",
                    str(source_config),
                    "--tag",
                    "fixture_latent_cap",
                    "--runtime-root",
                    str(tmp / "runtime"),
                    "--report-root",
                    str(tmp / "reports"),
                    "--max-iter",
                    "12",
                    "--workers",
                    "1",
                    "--ablation-mode",
                    "latent-cap-e-inv-u",
                    "--latent-e-inv-u-cap",
                    "1234",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )
            manifest = json.loads(result.stdout)
            launch_text = Path(manifest["launch_path"]).read_text(encoding="utf-8")
            self.assertIn('export DISC_LATENT_ABLATION_MODE="cap_e_inv_u"', launch_text)
            self.assertIn('export DISC_LATENT_E_INV_U_CAP="1234.0"', launch_text)
            self.assertNotIn("DISC_GAMSIG_FREEZE_TARGET", launch_text)
            self.assertEqual(manifest["ablation_mode"], "latent-cap-e-inv-u")

    def test_ablation_matrix_preparer_writes_master_launcher(self) -> None:
        script = PROJECT_ROOT / "repro" / "audits" / "prepare_exdqlm_keep_ablation_matrix.py"
        with tempfile.TemporaryDirectory() as tmp_raw:
            tmp = Path(tmp_raw)
            source_config = tmp / "source.yaml"
            write_source_config(source_config)
            result = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--source-config",
                    str(source_config),
                    "--tag",
                    "fixture_matrix",
                    "--runtime-root",
                    str(tmp / "runtime"),
                    "--report-root",
                    str(tmp / "reports"),
                    "--max-iter",
                    "12",
                    "--workers",
                    "1",
                    "--conditions",
                    "fixed-gamsig,latent-cap-e-inv-u",
                    "--quantiles",
                    "0.05,0.5",
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )
            manifest = json.loads(result.stdout)
            launch_path = Path(manifest["launch_path"])
            self.assertTrue(launch_path.exists())
            launch_text = launch_path.read_text(encoding="utf-8")
            self.assertIn("fixed-gamsig", launch_text)
            self.assertIn("latent-cap-e-inv-u", launch_text)
            self.assertEqual(manifest["conditions"], ["fixed-gamsig", "latent-cap-e-inv-u"])
            self.assertEqual(len(manifest["runs"]), 2)


if __name__ == "__main__":
    unittest.main()
