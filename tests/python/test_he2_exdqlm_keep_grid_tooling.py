from __future__ import annotations

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

import build_he2_exdqlm_multivar_keep_grid_configs as grid  # noqa: E402
import validate_he2_exdqlm_multivar_keep_grid_prelaunch as prelaunch  # noqa: E402


class HE2ExDQLMKeepGridToolingTests(unittest.TestCase):
    def test_user_grid_manifest_has_expected_cartesian_scope(self) -> None:
        manifest = ROOT / "config" / "he2_grid_specs" / "exdqlm_multivar_keep_epsilon_discount_grid_20260524.csv"
        specs = grid.load_grid_specs(manifest)
        self.assertEqual(len(specs), 30)
        self.assertEqual(set(specs["discount_case_id"]), {"c01", "c02", "c03", "c04", "c05", "c06"})
        expected_eps = {30.0, 60.0, 90.0, 180.0, 365.0}
        for case_id, case_rows in specs.groupby("discount_case_id"):
            self.assertEqual(set(case_rows["epsilon"]), expected_eps, case_id)
        self.assertTrue((specs["max_iter"] == 100).all())
        self.assertTrue((specs["min_update_iters"] == 50).all())
        c05 = specs.loc[specs["grid_spec_id"] == "c05_eps030"].iloc[0]
        self.assertEqual(float(c05["df_discrep"]), 0.9988)
        self.assertEqual(float(c05["df_s1"]), 0.9993)
        self.assertEqual(float(c05["df_s2"]), 0.9993)

    def test_spec_patch_wires_discount_epsilon_component_gate_and_quantiles(self) -> None:
        manifest = ROOT / "config" / "he2_grid_specs" / "exdqlm_multivar_keep_epsilon_discount_grid_20260524.csv"
        specs = grid.load_grid_specs(manifest)
        spec = specs.loc[specs["grid_spec_id"] == "c06_eps030"].iloc[0]
        patch = grid.build_spec_patch(spec, {"enabled": True, "quantile": 0.5, "pre_days": 30, "fail_fast": True})
        state = patch["models"]["exdqlm_multivar"]["state_evolution"]
        self.assertEqual(state["df_t"], 0.99999)
        self.assertEqual(state["df_discrep"], 0.9995)
        self.assertEqual(state["df_covs"], 0.999999)
        self.assertEqual(state["lambda"], 0.97)
        self.assertEqual(patch["fit"]["quantiles"], [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95])
        gamsig = patch["fit"]["exdqlm_multivar"]["gamma_sigma"]
        self.assertTrue(gamsig["coherence_guard"]["enabled"])
        self.assertTrue(gamsig["coherence_guard"]["rollback_on_guard"])
        self.assertEqual(gamsig["terminal_sampling_guard"]["mode"], "fail_fast")
        self.assertEqual(gamsig["terminal_sampling_guard"]["max_guard_lag_iters"], 20)
        self.assertTrue(patch["fit"]["exdqlm_multivar"]["pseudodata_guard"]["enabled"])
        self.assertEqual(patch["fit"]["exdqlm_multivar"]["pseudodata_guard"]["mode"], "fail")
        self.assertEqual(patch["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["epsilon"], 30.0)
        self.assertEqual(patch["fit"]["exdqlm_multivar"]["legacy"]["forecast_cov"]["c_factor"], 1.0)
        self.assertTrue(patch["post"]["multivar_component_diagnostics"]["enabled"])
        self.assertTrue(patch["post"]["multivar_component_diagnostics"]["fail_fast"])

    def test_grid_run_ids_are_cutoff_and_spec_specific(self) -> None:
        self.assertEqual(
            grid.grid_run_id("20221225", "c01_eps365"),
            "multimodel_20221225_v8_he2grid_c01_eps365_exdqlm_multivar_keep",
        )
        self.assertEqual(
            grid.grid_run_id("20210123", "case 1 / eps=365"),
            "multimodel_20210123_v8_he2grid_case_1_eps_365_exdqlm_multivar_keep",
        )

    def test_grid_template_uses_memory_aware_queue_defaults(self) -> None:
        template = ROOT / "config" / "he2_bayesian_publication_relaunch_exdqlm_multivar_keep_epsilon_discount_grid_20260524.template.yaml"
        cfg = yaml.safe_load(template.read_text(encoding="utf-8"))
        queue = cfg["queue"]
        self.assertEqual(int(queue["ordinary_max_concurrent"]), 4)
        self.assertEqual(int(queue["heavy_cutoff_max_concurrent"]), 4)
        self.assertEqual(float(queue["pause_mem_gb"]), 120.0)
        self.assertEqual(float(queue["launch_mem_gb"]), 170.0)
        self.assertEqual(float(queue["heavy_mem_gb"]), 190.0)

    def test_prelaunch_validator_accepts_dynamic_spec_count(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="keep_grid_prelaunch_dynamic_"))
        try:
            artifact_root = td / "artifact"
            matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
            config_dir = artifact_root / "control" / "generated_configs"
            matrix_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)

            specs = pd.DataFrame(
                [
                    {
                        "grid_spec_id": "screen01_eps030",
                        "discount_case_id": "screen01",
                        "epsilon": 30,
                        "c_factor": 1,
                        "df_t": 0.999999,
                        "df_s1": 0.9995,
                        "df_s2": 0.9995,
                        "df_s67": 0.9999,
                        "df_discrep": 0.999,
                        "lambda": 0.97,
                        "df_trans": 0.9999999,
                        "df_covs": 0.9999999,
                        "max_iter": 120,
                        "min_update_iters": 50,
                    },
                    {
                        "grid_spec_id": "screen02_eps090",
                        "discount_case_id": "screen02",
                        "epsilon": 90,
                        "c_factor": 1,
                        "df_t": 0.9999999,
                        "df_s1": 0.99995,
                        "df_s2": 0.99995,
                        "df_s67": 0.9999,
                        "df_discrep": 0.999,
                        "lambda": 0.97,
                        "df_trans": 0.999999,
                        "df_covs": 0.999999,
                        "max_iter": 120,
                        "min_update_iters": 50,
                    },
                ]
            )
            specs.to_csv(matrix_dir / "grid_spec_manifest_resolved.csv", index=False)

            rows = []
            registry = []
            for _, spec in specs.iterrows():
                for cutoff in sorted(prelaunch.EXPECTED_CUTOFFS):
                    cutoff_dash = f"{cutoff[:4]}-{cutoff[4:6]}-{cutoff[6:8]}"
                    run_id = grid.grid_run_id(cutoff, str(spec["grid_spec_id"]))
                    config_path = config_dir / f"{run_id}.yaml"
                    bundle_path = td / "bundles" / f"cutoff_date={cutoff_dash}" / "run_id=20260510_publication_shared_r01" / "bundle_meta.yaml"
                    bundle_path.parent.mkdir(parents=True, exist_ok=True)
                    bundle_path.write_text("ok: true\n", encoding="utf-8")
                    cfg = {
                        "run": {
                            "run_id": run_id,
                            "run_root": str(artifact_root / "runs"),
                            "resolved_run_root": str(artifact_root / "runs" / run_id),
                            "threads": {"mc_cores": 7},
                        },
                        "models": {
                            "run_exdqlm_multivar": True,
                            "run_exdqlm_univar": False,
                            "run_ndlm_main": False,
                            "run_ndlm_univar": False,
                            "exdqlm_multivar": {
                                "forecast_transfer_mode": "keep",
                                "structure": {"enabled_harmonic_indices": [1, 2, 3]},
                                "state_evolution": {
                                    "df_t": float(spec["df_t"]),
                                    "df_s1": float(spec["df_s1"]),
                                    "df_s2": float(spec["df_s2"]),
                                    "df_s67": float(spec["df_s67"]),
                                    "df_discrep": float(spec["df_discrep"]),
                                    "lambda": float(spec["lambda"]),
                                    "df_trans": float(spec["df_trans"]),
                                    "df_covs": float(spec["df_covs"]),
                                },
                            },
                        },
                        "fit": {
                            "quantiles": prelaunch.EXPECTED_QUANTILES,
                            "parallel": {"workers": 7},
                            "exdqlm_multivar": {
                                "legacy": {
                                    "forecast_cov": {
                                        "epsilon": float(spec["epsilon"]),
                                        "c_factor": float(spec["c_factor"]),
                                    }
                                }
                            },
                        },
                        "dates": {"data_start": "1987-05-29"},
                        "scale_contract": {
                            "analysis_scale_fit_internal": "log1p_cms",
                            "analysis_scale_post_internal": "log1p_cms",
                            "transform_policy": "log1p_only",
                        },
                        "post": {
                            "smoke_fast": True,
                            "force_isolation_smoke_fast": True,
                            "multivar_component_diagnostics": {
                                "enabled": True,
                                "fail_fast": True,
                                "quantile": 0.50,
                                "pre_days": 30,
                            },
                        },
                        "stages": {
                            "forecats": False,
                            "data_prep_shared": True,
                            "fit": True,
                            "post": True,
                            "validate": True,
                            "report": True,
                        },
                        "inputs": {
                            "forecats": {"existing_bundle_path": str(bundle_path)},
                            "transfer_function_covariates": {
                                "base_covariates": prelaunch.EXPECTED_TRANSFER_BASE,
                                "engineered_terms": prelaunch.EXPECTED_TRANSFER_ENGINEERED,
                            },
                            "covariate_features": {
                                "lag_orders": [1, 2, 3],
                                "include_squares": True,
                                "include_interaction": True,
                            },
                        },
                        "debug_he2_exdqlm_keep_grid": {"grid_spec_id": str(spec["grid_spec_id"])},
                    }
                    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
                    plan_row = {
                        "run_id": run_id,
                        "grid_spec_id": str(spec["grid_spec_id"]),
                        "cutoff": cutoff,
                        "active_quantiles": prelaunch.EXPECTED_QUANTILE_LABELS,
                        "config_path": str(config_path),
                    }
                    rows.append(plan_row)
                    reg_row = {"run_id": run_id, **{col: spec[col] for col in prelaunch.FLOAT_FIELDS}, "epsilon": spec["epsilon"], "c_factor": spec["c_factor"]}
                    registry.append(reg_row)

            pd.DataFrame(rows).to_csv(matrix_dir / "matrix_plan.csv", index=False)
            pd.DataFrame(registry).to_csv(matrix_dir / "grid_run_registry.csv", index=False)
            pd.DataFrame(rows).to_csv(matrix_dir / "frozen_spec_manifest.csv", index=False)
            metadata = {
                "artifact_root": str(artifact_root),
                "allow_run_failures": True,
                "skip_compare_bundles": True,
                "queue": {
                    "ordinary_max_concurrent": 4,
                    "pause_mem_gb": 120,
                    "launch_mem_gb": 170,
                    "heavy_mem_gb": 190,
                },
                "resources": {"fit_parallel_workers": 7, "mc_cores": 7},
            }
            (matrix_dir / "matrix_metadata.yaml").write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")

            rec, summary = prelaunch.validate_matrix(matrix_dir, artifact_root)
            self.assertEqual(summary["failures"], 0, rec.failures[:5])
            self.assertEqual(summary["specs"], 2)
            self.assertEqual(summary["plan_rows"], 10)
            self.assertEqual(summary["quantile_fits"], 70)
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
