from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
SCRIPT = ROOT / "scripts" / "build_he2_exal_m_t1_discount_refresh_scaffold.py"
SOURCE_CONFIG = (
    Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")
    / "multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518"
    / "control"
    / "generated_configs"
    / "multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep_bridgefix_20260518.yaml"
)


class DiscountRefreshScaffoldTest(unittest.TestCase):
    def test_builder_applies_discount_forecast_cov_and_gamsig_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            target_runtime_root = tmp / "runtime"
            report_dir = tmp / "report"
            spec_path = tmp / "discount_spec.yaml"
            spec_path.write_text(
                yaml.safe_dump(
                    {
                        "spec_label": "unitcheck",
                        "state_evolution": {
                            "df_t": 0.99999,
                            "df_s1": 0.9999,
                            "df_s2": 0.9999,
                            "df_s67": 0.9999,
                            "df_discrep": 0.9999,
                            "lambda": 0.97,
                            "df_trans": 0.9999999,
                            "df_covs": 0.99999,
                        },
                        "fit": {
                            "warm_start": {
                                "enabled": True,
                                "mode": "resume",
                                "source_run_root": "/tmp/warmstart_source",
                            },
                            "exdqlm_multivar": {
                                "legacy": {
                                    "forecast_cov": {
                                        "c_factor": 1.0,
                                        "epsilon": 365.0,
                                    }
                                },
                                "gamma_sigma": {
                                    "max_iter": 300,
                                    "freeze_target": "gamma_sigma",
                                    "state_refresh_schedule": {
                                        "enabled": True,
                                        "start_iter": 11,
                                        "end_iter": 200,
                                        "hold_iters": 10,
                                        "refresh_iters": 1,
                                    },
                                    "init": {
                                        "mode": "robust",
                                        "gamma": 0.0,
                                        "sigma_floor": 0.001,
                                        "sigma_scale": 1.0,
                                    },
                                    "priors": {
                                        "sigma": {
                                            "mean": 0.01,
                                            "variance": 1e3,
                                        },
                                        "gamma": {
                                            "location": 0.0,
                                            "scale": 1e10,
                                            "df": 1.0,
                                        },
                                    },
                                },
                            }
                        },
                        "models": {
                            "exdqlm_multivar": {
                                "structure": {
                                    "include_trend": True,
                                    "enabled_harmonic_indices": [1],
                                }
                            }
                        },
                        "inputs": {
                            "transfer_function_covariates": {
                                "base_covariates": ["PPT"],
                                "engineered_terms": [],
                            }
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--source-config",
                    str(SOURCE_CONFIG),
                    "--target-runtime-root",
                    str(target_runtime_root),
                    "--cleanup-report-dir",
                    str(report_dir),
                    "--discount-spec",
                    str(spec_path),
                ],
                check=True,
            )

            generated = (
                target_runtime_root
                / "control"
                / "generated_configs"
                / "multimodel_20221225_v8_he2pubgdpc1r1_unitcheck_exdqlm_multivar_keep.yaml"
            )
            cfg = yaml.safe_load(generated.read_text(encoding="utf-8"))

            state = cfg["models"]["exdqlm_multivar"]["state_evolution"]
            self.assertEqual(state["df_s1"], 0.9999)
            self.assertEqual(state["df_discrep"], 0.9999)
            self.assertEqual(state["df_covs"], 0.99999)

            fcov = cfg["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]
            self.assertEqual(fcov["c_factor"], 1.0)
            self.assertEqual(fcov["epsilon"], 365.0)

            gamsig = cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]
            self.assertEqual(gamsig["max_iter"], 300)
            self.assertEqual(gamsig["freeze_target"], "gamma_sigma")
            self.assertTrue(gamsig["state_refresh_schedule"]["enabled"])
            self.assertEqual(gamsig["state_refresh_schedule"]["start_iter"], 11)
            self.assertEqual(gamsig["state_refresh_schedule"]["end_iter"], 200)
            self.assertEqual(gamsig["state_refresh_schedule"]["hold_iters"], 10)
            self.assertEqual(gamsig["state_refresh_schedule"]["refresh_iters"], 1)
            self.assertEqual(gamsig["init"]["gamma"], 0.0)
            self.assertEqual(gamsig["init"]["sigma_floor"], 0.001)
            self.assertEqual(gamsig["init"]["sigma_scale"], 1.0)
            self.assertEqual(gamsig["priors"]["sigma"]["mean"], 0.01)
            self.assertEqual(gamsig["priors"]["sigma"]["variance"], 1000.0)

            for q_label in ["q20", "q35", "q50", "q65", "q80"]:
                self.assertEqual(gamsig["quantile_overrides"][q_label]["init"]["sigma_floor"], 0.001)
                self.assertEqual(gamsig["quantile_overrides"][q_label]["init"]["sigma_scale"], 1.0)
            self.assertNotIn("freeze_target", gamsig["quantile_overrides"]["q35"])
            self.assertNotIn("freeze_target", gamsig["quantile_overrides"]["q50"])

            structure = cfg["models"]["exdqlm_multivar"]["structure"]
            self.assertTrue(structure["include_trend"])
            self.assertEqual(structure["enabled_harmonic_indices"], [1])

            transfer_cov = cfg["inputs"]["transfer_function_covariates"]
            self.assertEqual(transfer_cov["base_covariates"], ["PPT"])
            self.assertEqual(transfer_cov["engineered_terms"], [])

            warm_start = cfg["fit"]["warm_start"]
            self.assertTrue(warm_start["enabled"])
            self.assertEqual(warm_start["mode"], "resume")
            self.assertEqual(warm_start["source_run_root"], "/tmp/warmstart_source")

            launch_script = (
                target_runtime_root
                / "control"
                / "launch_multimodel_20221225_v8_he2pubgdpc1r1_unitcheck_exdqlm_multivar_keep_with_cleanup.sh"
            )
            self.assertIn("run_unified_with_cleanup.sh", launch_script.read_text(encoding="utf-8"))

    def test_builder_can_prepare_no_cleanup_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            target_runtime_root = tmp / "runtime"
            report_dir = tmp / "report"
            spec_path = tmp / "discount_spec.yaml"
            spec_path.write_text(
                yaml.safe_dump(
                    {
                        "spec_label": "retaincheck",
                        "state_evolution": {
                            "df_t": 0.99999,
                            "df_s1": 0.9999,
                            "df_s2": 0.9999,
                            "df_s67": 0.9999,
                            "df_discrep": 0.9999,
                            "lambda": 0.97,
                            "df_trans": 0.9999999,
                            "df_covs": 0.99999,
                        },
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--source-config",
                    str(SOURCE_CONFIG),
                    "--target-runtime-root",
                    str(target_runtime_root),
                    "--cleanup-report-dir",
                    str(report_dir),
                    "--discount-spec",
                    str(spec_path),
                    "--cleanup-mode",
                    "without_cleanup",
                ],
                check=True,
            )

            launch_script = (
                target_runtime_root
                / "control"
                / "launch_multimodel_20221225_v8_he2pubgdpc1r1_retaincheck_exdqlm_multivar_keep_without_cleanup.sh"
            )
            self.assertTrue(launch_script.exists())
            text = launch_script.read_text(encoding="utf-8")
            self.assertIn("run_unified_without_cleanup.sh", text)

            summary = yaml.safe_load((report_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["cleanup_mode"], "without_cleanup")


if __name__ == "__main__":
    unittest.main()
