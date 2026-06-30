import importlib.util
import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestLog1pTransformPolicy(unittest.TestCase):
    def test_active_top_level_configs_do_not_use_loglog1p(self) -> None:
        config_paths = [
            PROJECT_ROOT / "config" / "unified_run.template.yaml",
            PROJECT_ROOT / "config" / "nws_operational_latest.yaml",
            *sorted((PROJECT_ROOT / "config").glob("forecats_pipeline*.yaml")),
            *sorted((PROJECT_ROOT / "config").glob("forecats_batch.site=11160500*.yaml")),
        ]
        self.assertGreater(len(config_paths), 0)
        for path in config_paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("log_log1p_cms", text, msg=str(path))

    def test_flow_scale_rejects_loglog1p(self) -> None:
        module_path = PROJECT_ROOT / "scripts" / "flow_scale.py"
        spec = importlib.util.spec_from_file_location("flow_scale", module_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with self.assertRaises(ValueError):
            module.forward_transform_cms([0.0, 1.0], "log_log1p_cms")
        with self.assertRaises(ValueError):
            module.inverse_transform_to_cms([0.0, 1.0], "log_log1p_cms")

    def test_unified_template_defaults_internal_scales_to_log1p(self) -> None:
        payload = yaml.safe_load((PROJECT_ROOT / "config" / "unified_run.template.yaml").read_text(encoding="utf-8"))
        scale_contract = payload["scale_contract"]
        self.assertEqual(scale_contract["legacy_fit_input_scale"], "log1p_cms")
        self.assertEqual(scale_contract["legacy_post_input_scale"], "log1p_cms")
        self.assertEqual(scale_contract["analysis_scale_fit_internal"], "log1p_cms")
        self.assertEqual(scale_contract["analysis_scale_post_internal"], "log1p_cms")

    def test_active_keep_runner_does_not_apply_second_log(self) -> None:
        runner = (PROJECT_ROOT / "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r").read_text(encoding="utf-8")
        self.assertNotIn("nws_forecast[,-1] <- log(nws_forecast[,-1])", runner)
        self.assertNotIn("glofas_forecast[,-1] <- log(glofas_forecast[,-1])", runner)
        self.assertIn("Forecast adapters now provide log1p(cms)", runner)

    def test_retrospective_builder_does_not_apply_second_log(self) -> None:
        retro_builder = (PROJECT_ROOT / "R" / "disc_w" / "03_covariates_standardize.R").read_text(encoding="utf-8")
        self.assertNotIn("Y <- log(Y)", retro_builder)
        self.assertIn("shared retrospective contract is already log1p(cms)", retro_builder)

    def test_legacy_univariate_bridge_uses_explicit_scale_contract(self) -> None:
        runner = (PROJECT_ROOT / "OptimalModelSLexAL.r").read_text(encoding="utf-8")
        self.assertNotIn("nws_forecast[,-1] <- log(nws_forecast[,-1])", runner)
        self.assertNotIn("glofas_forecast[,-1] <- log(glofas_forecast[,-1])", runner)
        self.assertNotIn("Y <- log(Y)", runner)
        self.assertIn("univar_legacy_resolve_scale_contract", runner)
        self.assertIn("univar_legacy_transform_flow_frame_cols", runner)
        self.assertIn("univar_legacy_transform_flow_values_to_internal_scale", runner)

    def test_univariate_fit_diagnostics_are_named_and_labeled_log1p(self) -> None:
        figures = (PROJECT_ROOT / "R" / "environmetrics" / "40_figures_smoke_fast.R").read_text(encoding="utf-8")
        self.assertIn("univar_fit_mu_vs_observed_log1p.png", figures)
        self.assertIn("univar_fit_mu_vs_observed_recent_log1p.png", figures)
        self.assertIn('ylab = "log(1 + flow)"', figures)
        self.assertIn("truth[valid] <- flow_log1p[ok][idx_map[valid]]", figures)
        self.assertNotIn("univar_fit_mu_vs_observed_loglog.png", figures)
        self.assertNotIn("univar_fit_mu_vs_observed_recent_loglog.png", figures)
        self.assertNotIn('ylab = "log(log(flow + 1))"', figures)
        self.assertNotIn("truth[valid] <- log(flow_log1p[ok][idx_map[valid]])", figures)

    def test_loglog1p_is_diagnostic_only_near_zero(self) -> None:
        # Exact-zero retrospectives are valid under log1p_cms but invalid under
        # log(log1p(cms)); this is why the repair target remains log1p_cms.
        import math

        self.assertEqual(math.log1p(0.0), 0.0)
        with self.assertRaises(ValueError):
            math.log(math.log1p(0.0))


if __name__ == "__main__":
    unittest.main()
