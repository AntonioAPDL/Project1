from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIVAR_SOURCE = ROOT / 'R' / 'unified' / 'families' / 'exdqlm_univar' / '03_updates_vb_or_fitloop.R'
MULTIVAR_SOURCE = ROOT / 'DISC_Optimal_Synth_Ranges_W_transfer_forecast.r'
CONFIG_TEMPLATE = ROOT / 'config' / 'multimodel_v8_all9_featurecov.template.yaml'
MANIFEST_MD = ROOT / 'reports' / 'he2_publication_manifest' / 'he2_bayesian_publication_manifest.md'


class HistoricalAlContractSourceTests(unittest.TestCase):
    def test_univar_source_contains_explicit_al_gamma_zero_and_sigma_only_branches(self) -> None:
        text = UNIVAR_SOURCE.read_text(encoding='utf-8')
        self.assertIn("identical(likelihood_mode, \"al\")", text)
        self.assertIn("gamma <- if (identical(likelihood_mode, \"al\")) 0", text)
        self.assertIn("Es <- if (identical(likelihood_mode, \"al\")) rep(0, Tn)", text)
        self.assertIn("gamma_eff <- if (identical(likelihood_mode, \"al\")) 0 else gamma", text)
        self.assertIn("map <- tryCatch(univar_theory_exal_map(p0, 0), error = function(e) NULL)", text)
        self.assertIn("map <- univar_theory_exal_map(p0, gamma_eff)", text)

    def test_multivar_source_contains_explicit_al_mode_and_sigma_only_optimizer(self) -> None:
        text = MULTIVAR_SOURCE.read_text(encoding='utf-8')
        self.assertIn("DISC_W_AL_MODE <- identical(DISC_W_LIKELIHOOD_MODE, \"al\")", text)
        self.assertIn("if (isTRUE(DISC_W_AL_MODE)) {", text)
        self.assertIn("E.sts=z,E.sts2=z", text)
        self.assertIn("gam <- if (isTRUE(DISC_W_AL_MODE)) 0 else", text)
        self.assertIn("theta_g_fixed <- qlogis(", text)
        self.assertIn("stats::optimize(sigma_obj, interval = log(c(1e-5, 1e3)))", text)

    def test_current_template_and_manifest_preserve_historical_al_family_ids(self) -> None:
        cfg_text = CONFIG_TEMPLATE.read_text(encoding='utf-8')
        manifest_text = MANIFEST_MD.read_text(encoding='utf-8')
        self.assertIn('dqlm_multivar_al_keep:', cfg_text)
        self.assertIn('dqlm_multivar_al_drop:', cfg_text)
        self.assertIn('dqlm_univar_al:', cfg_text)
        self.assertIn('AL-M-T1', manifest_text)
        self.assertIn('AL-M-T0', manifest_text)
        self.assertIn('AL-U-T1', manifest_text)


if __name__ == '__main__':
    unittest.main()
