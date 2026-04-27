#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from multimodel_v8_lib import load_yaml  # noqa: E402
from build_multimodel_v8_quantile_ndlm_discount_probe_matrix_configs import _build_run_config  # noqa: E402


class QuantileNdlmDiscountProbeToolingTests(unittest.TestCase):
    def _make_source_snapshot(self, td: Path, *, run_name: str, family: str) -> Path:
        run_root = td / "source_artifact" / "runs" / run_name
        shared_root = run_root / "inputs" / "shared"
        (shared_root / "parameters").mkdir(parents=True, exist_ok=True)
        (shared_root / "retros").mkdir(parents=True, exist_ok=True)
        (shared_root / "forecasts").mkdir(parents=True, exist_ok=True)
        (shared_root / "forecats_bundle").mkdir(parents=True, exist_ok=True)
        (shared_root / "covariates").mkdir(parents=True, exist_ok=True)
        (shared_root / "parameters" / "parameters.txt").write_text("alpha=1\n", encoding="utf-8")
        (shared_root / "retros" / "retros.csv").write_text("Date,USGS,GloFAS,NWS3.0\n2021-01-01,1,2,3\n", encoding="utf-8")
        (shared_root / "forecasts" / "nws_forecast.csv").write_text("Date,value\n2021-01-24,1\n", encoding="utf-8")
        (shared_root / "forecasts" / "glofas_forecast.csv").write_text("Date,value\n2021-01-24,1\n", encoding="utf-8")
        (shared_root / "forecats_bundle" / "meta.yaml").write_text("bundle: ok\n", encoding="utf-8")
        (shared_root / "covariates" / "cov_01_PPT.csv").write_text("Date,PPT\n2021-01-01,1\n", encoding="utf-8")
        (shared_root / "covariates" / "cov_02_SOIL.csv").write_text("Date,SOIL\n2021-01-01,1\n", encoding="utf-8")
        (shared_root / "covariates" / "cov_03_PCA.csv").write_text("Date,PCA\n2021-01-01,1\n", encoding="utf-8")

        cfg = load_yaml(ROOT / "config" / "unified_run.template.yaml")
        cfg["run"]["run_id"] = run_name
        cfg["run"]["run_root"] = str(run_root.parent.parent)
        cfg["inputs"]["fit"]["covariates"] = [
            {"name": "PPT", "path": str(shared_root / "covariates" / "cov_01_PPT.csv")},
            {"name": "SOIL", "path": str(shared_root / "covariates" / "cov_02_SOIL.csv")},
            {"name": "PCA", "path": str(shared_root / "covariates" / "cov_03_PCA.csv")},
        ]
        cfg["inputs"]["deterministic_climate"]["enabled"] = True
        cfg["inputs"]["covariate_features"] = {
            "enabled": True,
            "output_filename": "covariate_features.csv",
            "lag_orders": [1, 2, 3],
            "include_squares": True,
            "include_interaction": True,
        }
        cfg["inputs"]["fit"]["parameters_path"] = str(shared_root / "parameters" / "parameters.txt")
        cfg["inputs"]["fit"]["retros_path"] = str(shared_root / "retros" / "retros.csv")
        cfg["inputs"]["fit"]["nws_forecast_path"] = str(shared_root / "forecasts" / "nws_forecast.csv")
        cfg["inputs"]["fit"]["glofas_forecast_path"] = str(shared_root / "forecasts" / "glofas_forecast.csv")
        cfg["inputs"]["forecats"]["existing_bundle_path"] = str(shared_root / "forecats_bundle" / "meta.yaml")
        cfg["models"]["run_exdqlm_multivar"] = family == "multivar"
        cfg["models"]["run_exdqlm_univar"] = family == "univar"
        cfg["models"]["run_ndlm_main"] = False
        cfg["models"]["run_ndlm_univar"] = False
        if family == "multivar":
            cfg["models"]["exdqlm_multivar"]["likelihood_mode"] = "al"
            cfg["models"]["exdqlm_multivar"]["forecast_transfer_mode"] = "keep"
        else:
            cfg["models"]["exdqlm_univar"]["likelihood_mode"] = "al"

        resolved = run_root / "resolved_config.yaml"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        return resolved

    def test_build_run_config_preserves_corrected_multivar_featurecov_contract(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="quantile_probe_multivar_"))
        try:
            source_cfg = self._make_source_snapshot(td, run_name="source_multivar", family="multivar")
            fallback_usgs = td / "fallback" / "usgs_daily.csv"
            fallback_usgs.parent.mkdir(parents=True, exist_ok=True)
            fallback_usgs.write_text("date,discharge_cms\n2021-01-01,1.0\n", encoding="utf-8")

            cfg = _build_run_config(
                template_cfg=load_yaml(source_cfg),
                run_id="multimodel_20211112_v8_probe_dqlm_multivar_al_keep",
                artifact_root=td / "artifact_root",
                family_id="dqlm_multivar_al_keep",
                family_cfg={
                    "model_id": "dqlm_multivar_al_synth_keep",
                    "model_key": "exdqlm_multivar",
                    "likelihood_mode": "al",
                    "transfer_mode": "keep",
                },
                campaign_spec_id="quantile_featurecov_ndlm_discount_probe_v1",
                fit_parallel_mode="global_models",
                fit_parallel_workers=7,
                inputs_overrides={"fit": {"usgs_cache_path": str(fallback_usgs)}},
                model_overrides={
                    "exdqlm_multivar": {
                        "state_evolution": {
                            "df_s1": 0.99999999,
                            "df_s2": 0.99999999,
                            "df_s67": 0.99999999,
                            "df_discrep": 0.99999999,
                            "df_covs": 0.99999999,
                        }
                    }
                },
                selection={
                    "source_run": "source_multivar",
                    "source_type": "featurecov_cf1_eps_sweep",
                    "compare_dir": "/tmp/compare",
                    "mean_crps": 0.1,
                    "source_config": str(source_cfg),
                    "selected_epsilon_label": "eps180cf1",
                    "selected_epsilon": 180.0,
                },
            )
            self.assertEqual([row["name"] for row in cfg["inputs"]["fit"]["covariates"]], ["PPT", "SOIL", "PCA"])
            self.assertTrue(cfg["inputs"]["deterministic_climate"]["enabled"])
            self.assertTrue(cfg["inputs"]["covariate_features"]["enabled"])
            self.assertEqual(cfg["inputs"]["covariate_features"]["lag_orders"], [1, 2, 3])
            self.assertTrue(cfg["inputs"]["covariate_features"]["include_squares"])
            self.assertTrue(cfg["inputs"]["covariate_features"]["include_interaction"])
            self.assertEqual(Path(cfg["inputs"]["fit"]["usgs_cache_path"]).resolve(), fallback_usgs.resolve())
            state = cfg["models"]["exdqlm_multivar"]["state_evolution"]
            self.assertEqual(state["df_s1"], 0.99999999)
            self.assertEqual(state["df_s2"], 0.99999999)
            self.assertEqual(state["df_s67"], 0.99999999)
            self.assertEqual(state["df_discrep"], 0.99999999)
            self.assertEqual(state["df_covs"], 0.99999999)
            self.assertEqual(cfg["fit"]["parallel"]["workers"], 7)
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_build_run_config_preserves_corrected_univar_featurecov_contract(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="quantile_probe_univar_"))
        try:
            source_cfg = self._make_source_snapshot(td, run_name="source_univar", family="univar")
            fallback_usgs = td / "fallback" / "usgs_daily.csv"
            fallback_usgs.parent.mkdir(parents=True, exist_ok=True)
            fallback_usgs.write_text("date,discharge_cms\n2021-01-01,1.0\n", encoding="utf-8")

            cfg = _build_run_config(
                template_cfg=load_yaml(source_cfg),
                run_id="multimodel_20210123_v8_probe_dqlm_univar_al",
                artifact_root=td / "artifact_root",
                family_id="dqlm_univar_al",
                family_cfg={
                    "model_id": "dqlm_univar_al_synth",
                    "model_key": "exdqlm_univar",
                    "likelihood_mode": "al",
                },
                campaign_spec_id="quantile_featurecov_ndlm_discount_probe_v1",
                fit_parallel_mode="global_models",
                fit_parallel_workers=7,
                inputs_overrides={"fit": {"usgs_cache_path": str(fallback_usgs)}},
                model_overrides={
                    "exdqlm_univar": {
                        "state_evolution": {
                            "df_s1": 0.99999999,
                            "df_s2": 0.99999999,
                            "df_s67": 0.99999999,
                            "df_covs": 0.99999999,
                        }
                    }
                },
                selection={
                    "source_run": "source_univar",
                    "source_type": "featurecov_relaunch",
                    "compare_dir": "/tmp/compare",
                    "mean_crps": 0.1,
                    "source_config": str(source_cfg),
                    "selected_epsilon_label": "univar_featurecov_he2_v1",
                    "selected_epsilon": None,
                },
            )
            self.assertEqual([row["name"] for row in cfg["inputs"]["fit"]["covariates"]], ["PPT", "SOIL", "PCA"])
            self.assertTrue(cfg["inputs"]["deterministic_climate"]["enabled"])
            self.assertTrue(cfg["inputs"]["covariate_features"]["enabled"])
            self.assertEqual(cfg["inputs"]["covariate_features"]["lag_orders"], [1, 2, 3])
            self.assertEqual(Path(cfg["inputs"]["fit"]["usgs_cache_path"]).resolve(), fallback_usgs.resolve())
            state = cfg["models"]["exdqlm_univar"]["state_evolution"]
            self.assertEqual(state["df_s1"], 0.99999999)
            self.assertEqual(state["df_s2"], 0.99999999)
            self.assertEqual(state["df_s67"], 0.99999999)
            self.assertEqual(state["df_covs"], 0.99999999)
            self.assertNotIn("df_discrep", state)
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_template_uses_four_row_batches_and_seven_quantile_workers(self) -> None:
        template = load_yaml(ROOT / "config" / "multimodel_v8_quantile_ndlm_discount_probe_20260422.template.yaml")
        self.assertEqual(template["queue"]["ordinary_max_concurrent"], 4)
        self.assertEqual(template["queue"]["heavy_cutoff_max_concurrent"], 4)
        self.assertFalse(template["queue"]["heavy_cutoff_blocks_ordinary"])
        families = template["families"]
        observed = {family_id: int(families[family_id]["fit_parallel_workers"]) for family_id in families}
        self.assertEqual(observed, {family_id: 7 for family_id in families})

    def test_hybrid_template_uses_same_parallel_contract_with_midpoint_overrides(self) -> None:
        template = load_yaml(ROOT / "config" / "multimodel_v8_quantile_featurecov_hybrid_discount_probe_20260422.template.yaml")
        self.assertEqual(template["queue"]["ordinary_max_concurrent"], 4)
        self.assertEqual(template["queue"]["heavy_cutoff_max_concurrent"], 4)
        self.assertFalse(template["queue"]["heavy_cutoff_blocks_ordinary"])
        families = template["families"]
        observed = {family_id: int(families[family_id]["fit_parallel_workers"]) for family_id in families}
        self.assertEqual(observed, {family_id: 7 for family_id in families})

        multivar = template["model_overrides"]["exdqlm_multivar"]["state_evolution"]
        self.assertEqual(multivar["df_s1"], 0.99999)
        self.assertEqual(multivar["df_s2"], 0.99999)
        self.assertEqual(multivar["df_s67"], 0.99999)
        self.assertEqual(multivar["df_discrep"], 0.99999)
        self.assertEqual(multivar["df_covs"], 0.999999)

        univar = template["model_overrides"]["exdqlm_univar"]["state_evolution"]
        self.assertEqual(univar["df_s1"], 0.99999)
        self.assertEqual(univar["df_s2"], 0.99999)
        self.assertEqual(univar["df_s67"], 0.99999)
        self.assertEqual(univar["df_covs"], 0.999999)

    def test_custom_template_uses_requested_discount_profile(self) -> None:
        template = load_yaml(ROOT / "config" / "multimodel_v8_quantile_featurecov_custom_discount_probe_20260422.template.yaml")
        self.assertEqual(template["queue"]["ordinary_max_concurrent"], 4)
        self.assertEqual(template["queue"]["heavy_cutoff_max_concurrent"], 4)
        self.assertFalse(template["queue"]["heavy_cutoff_blocks_ordinary"])
        families = template["families"]
        observed = {family_id: int(families[family_id]["fit_parallel_workers"]) for family_id in families}
        self.assertEqual(observed, {family_id: 7 for family_id in families})

        multivar = template["model_overrides"]["exdqlm_multivar"]["state_evolution"]
        self.assertEqual(multivar["df_t"], 0.99999)
        self.assertEqual(multivar["df_s1"], 0.9995)
        self.assertEqual(multivar["df_s2"], 0.9995)
        self.assertEqual(multivar["df_s67"], 0.9999)
        self.assertEqual(multivar["df_discrep"], 0.997)
        self.assertEqual(multivar["lambda"], 0.97)
        self.assertEqual(multivar["df_trans"], 0.9999999)
        self.assertEqual(multivar["df_covs"], 0.9999)

        univar = template["model_overrides"]["exdqlm_univar"]["state_evolution"]
        self.assertEqual(univar["df_t"], 0.99999)
        self.assertEqual(univar["df_s1"], 0.9995)
        self.assertEqual(univar["df_s2"], 0.9995)
        self.assertEqual(univar["df_s67"], 0.9999)
        self.assertEqual(univar["lambda"], 0.97)
        self.assertEqual(univar["df_trans"], 0.9999999)
        self.assertEqual(univar["df_covs"], 0.9999)


if __name__ == "__main__":
    unittest.main()
