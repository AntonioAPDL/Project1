from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml'
BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'dqlm_univar_al_all_cutoffs_sharedspec_20260517.yaml'


class He2DqlmUnivarAlSharedspecPackageTests(unittest.TestCase):
    def test_template_targets_al_univar_family(self) -> None:
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['campaign']['families'], ['dqlm_univar_al'])
        self.assertIn('dqlm_univar_al_all_cutoffs_sharedspec_20260517', payload['campaign']['artifact_root'])
        self.assertEqual(payload['validation']['cutoff_smoke_family'], 'dqlm_univar_al')
        self.assertEqual(payload['validation']['univar_quantile_fit_smoke_family'], 'dqlm_univar_al')
        self.assertEqual(payload['validation']['full_pipeline_quantile_family'], '__disabled__')
        self.assertEqual(payload['validation']['full_pipeline_univar_quantile_family'], 'dqlm_univar_al')
        self.assertEqual(payload['validation']['full_pipeline_univar_quantiles'], [0.35, 0.50, 0.65])

    def test_batch_pins_likelihood_mode_al_and_leaves_non_applicable_knobs_absent(self) -> None:
        payload = yaml.safe_load(BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['families'], ['dqlm_univar_al'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 7)
        self.assertEqual(payload['resources']['mc_cores'], 7)
        family_patch = payload['overrides']['row_config_patches'][0]
        self.assertEqual(family_patch['family'], 'dqlm_univar_al')
        self.assertEqual(family_patch['manuscript_label'], 'AL-U-T1')
        model = family_patch['config_patch']['models']['exdqlm_univar']
        self.assertEqual(model['likelihood_mode'], 'al')
        self.assertEqual(model['implementation_mode'], 'legacy_bridge')
        state = model['state_evolution']
        self.assertEqual(state['df_t'], 0.99999999)
        self.assertEqual(state['df_s1'], 0.99999)
        self.assertEqual(state['df_s2'], 0.99999)
        self.assertEqual(state['df_s67'], 0.99999)
        self.assertEqual(state['lambda'], 0.97)
        self.assertEqual(state['df_trans'], 0.9999999)
        self.assertEqual(state['df_covs'], 0.9999999)
        self.assertNotIn('df_discrep', state)
        self.assertNotIn('fit', family_patch['config_patch'])


if __name__ == '__main__':
    unittest.main()
