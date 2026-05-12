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


if __name__ == "__main__":
    unittest.main()
