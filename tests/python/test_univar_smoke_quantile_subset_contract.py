from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SMOKE_FAST = ROOT / "R" / "environmetrics" / "40_figures_smoke_fast.R"


class UnivarSmokeQuantileSubsetContractTests(unittest.TestCase):
    def test_smoke_module_uses_active_quantile_helpers(self) -> None:
        text = SMOKE_FAST.read_text(encoding="utf-8")
        self.assertIn("fetch_univar_active_q_probs_smoke", text)
        self.assertIn("select_univar_quantile_samples", text)
        self.assertIn("quantile_prob_label", text)
        self.assertIn("univar_active_q_probs.rds", text)

    def test_forecast_window_no_longer_hardcodes_full_seven_quantile_indices(self) -> None:
        text = SMOKE_FAST.read_text(encoding="utf-8")
        self.assertNotIn("xb_forecast[1, , ]", text)
        self.assertNotIn("xb_forecast[4, , ]", text)
        self.assertNotIn("xb_forecast[7, , ]", text)
        self.assertNotIn("y_forecast[4, , ]", text)


if __name__ == "__main__":
    unittest.main()
