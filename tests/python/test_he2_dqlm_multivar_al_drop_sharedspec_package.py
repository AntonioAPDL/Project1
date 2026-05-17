from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml'
BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.yaml'


class He2DqlmMultivarAlDropSharedspecPackageTests(unittest.TestCase):
    def test_template_targets_al_drop_family(self) -> None:
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['campaign']['families'], ['dqlm_multivar_al_drop'])
        self.assertIn('dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517', payload['campaign']['artifact_root'])
        self.assertEqual(payload['validation']['cutoff_smoke_family'], 'dqlm_multivar_al_drop')
        self.assertEqual(payload['validation']['quantile_fit_smoke_family'], 'dqlm_multivar_al_drop')
        self.assertEqual(payload['validation']['full_pipeline_quantile_family'], 'dqlm_multivar_al_drop')
        self.assertEqual(payload['validation']['univar_quantile_fit_smoke_family'], 'dqlm_univar_al')
        self.assertEqual(payload['validation']['full_pipeline_univar_quantile_family'], 'dqlm_univar_al')
        self.assertEqual(
            payload['validation']['quantile_fit_smoke_cases'],
            [
                {'cutoff': '20210123', 'family': 'dqlm_multivar_al_drop', 'quantiles': [0.5]},
                {'cutoff': '20221225', 'family': 'dqlm_multivar_al_drop', 'quantiles': [0.65]},
            ],
        )
        self.assertEqual(
            payload['validation']['full_pipeline_quantile_smoke_cases'],
            [
                {'cutoff': '20210123', 'family': 'dqlm_multivar_al_drop', 'quantiles': [0.5]},
            ],
        )

    def test_batch_reuses_sharedspec_and_pins_likelihood_mode_al(self) -> None:
        payload = yaml.safe_load(BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['families'], ['dqlm_multivar_al_drop'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 7)
        self.assertEqual(payload['resources']['mc_cores'], 7)
        family_patch = payload['overrides']['row_config_patches'][0]
        self.assertEqual(family_patch['family'], 'dqlm_multivar_al_drop')
        self.assertEqual(family_patch['manuscript_label'], 'AL-M-T0')
        fit = family_patch['config_patch']['fit']['exdqlm_multivar']
        self.assertEqual(fit['legacy']['forecast_cov']['epsilon'], 30.0)
        self.assertEqual(fit['legacy']['forecast_cov']['c_factor'], 1.0)
        self.assertEqual(fit['gamma_sigma']['quantile_overrides']['q50']['freeze_target'], 'states')
        model = family_patch['config_patch']['models']['exdqlm_multivar']
        self.assertEqual(model['likelihood_mode'], 'al')
        self.assertEqual(model['state_evolution']['df_discrep'], 0.99999)


if __name__ == '__main__':
    unittest.main()
