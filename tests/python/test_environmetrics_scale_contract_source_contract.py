from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_INPUTS_SOURCE = ROOT / "R" / "environmetrics" / "10_data_inputs.R"
STAGE_FIT_SOURCE = ROOT / "R" / "unified" / "stages" / "stage_fit.R"
STAGE_POST_SOURCE = ROOT / "R" / "unified" / "stages" / "stage_post.R"
RUN_FIGURES_SOURCE = ROOT / "scripts" / "run_environmetrics_figures.R"


class EnvironmetricsScaleContractSourceContractTests(unittest.TestCase):
    def test_data_inputs_uses_scale_aware_conversion_bridge(self) -> None:
        text = DATA_INPUTS_SOURCE.read_text(encoding="utf-8")
        self.assertIn('UNIFIED_LEGACY_POST_INPUT_SCALE', text)
        self.assertIn('UNIFIED_ANALYSIS_SCALE_POST_INTERNAL', text)
        self.assertIn('UNIFIED_LEGACY_FIT_INPUT_SCALE', text)
        self.assertIn('UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL', text)
        self.assertIn('unified_convert_scale', text)
        self.assertIn('transform_flow_values_to_analysis_scale', text)
        self.assertIn('transform_flow_frame_cols_to_analysis_scale', text)
        self.assertIn('Y[] <- transform_flow_values_to_analysis_scale(Y, "retros_response")', text)
        self.assertNotIn('Y <- log(Y) #log-log, since already logged', text)
        self.assertNotIn('nws_forecast[, nws_value_cols] <- log(', text)
        self.assertNotIn('glofas_forecast[, glofas_value_cols] <- log(', text)

    def test_stage_fit_exports_scale_contract_env_vars(self) -> None:
        text = STAGE_FIT_SOURCE.read_text(encoding="utf-8")
        self.assertIn('UNIFIED_LEGACY_FIT_INPUT_SCALE = as.character(cfg$scale_contract$legacy_fit_input_scale)', text)
        self.assertIn('UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL = as.character(cfg$scale_contract$analysis_scale_fit_internal)', text)
        self.assertIn('UNIFIED_TRANSFORM_POLICY = as.character(unified_get(', text)

    def test_stage_post_exports_fit_and_post_scale_contract_env_vars(self) -> None:
        text = STAGE_POST_SOURCE.read_text(encoding="utf-8")
        self.assertIn('UNIFIED_LEGACY_FIT_INPUT_SCALE = as.character(cfg$scale_contract$legacy_fit_input_scale)', text)
        self.assertIn('UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL = as.character(cfg$scale_contract$analysis_scale_fit_internal)', text)
        self.assertIn('UNIFIED_LEGACY_POST_INPUT_SCALE = as.character(cfg$scale_contract$legacy_post_input_scale)', text)
        self.assertIn('UNIFIED_ANALYSIS_SCALE_POST_INTERNAL = as.character(cfg$scale_contract$analysis_scale_post_internal)', text)
        self.assertIn('UNIFIED_TRANSFORM_POLICY = as.character(unified_get(', text)

    def test_run_figures_logs_scale_contract_for_auditability(self) -> None:
        text = RUN_FIGURES_SOURCE.read_text(encoding="utf-8")
        self.assertIn('UNIFIED_LEGACY_FIT_INPUT_SCALE', text)
        self.assertIn('UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL', text)
        self.assertIn('UNIFIED_LEGACY_POST_INPUT_SCALE', text)
        self.assertIn('UNIFIED_ANALYSIS_SCALE_POST_INTERNAL', text)
        self.assertIn('UNIFIED_TRANSFORM_POLICY', text)


if __name__ == "__main__":
    unittest.main()
