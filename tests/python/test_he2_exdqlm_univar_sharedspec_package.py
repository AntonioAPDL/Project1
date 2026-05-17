from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml'
BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml'


class He2ExdqlmUnivarSharedspecPackageTests(unittest.TestCase):
    def test_template_targets_univar_family_and_expected_validator_scope(self) -> None:
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['campaign']['families'], ['exdqlm_univar'])
        self.assertIn('exdqlm_univar_all_cutoffs_sharedspec_20260516', payload['campaign']['artifact_root'])
        self.assertEqual(payload['validation']['cutoff_smoke_family'], 'exdqlm_univar')
        self.assertEqual(payload['validation']['univar_quantile_fit_smoke_family'], 'exdqlm_univar')
        self.assertEqual(payload['validation']['full_pipeline_quantile_family'], 'exdqlm_univar')
        self.assertEqual(
            payload['validation']['full_pipeline_quantile_smoke_cases'],
            [
                {'cutoff': '20210123', 'family': 'exdqlm_univar', 'quantiles': [0.35, 0.50, 0.65]},
            ],
        )

    def test_batch_freezes_shared_state_and_supported_q50_override_only(self) -> None:
        payload = yaml.safe_load(BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['families'], ['exdqlm_univar'])
        self.assertEqual(payload['selection']['model_classes'], ['quantile_univariate'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 7)
        self.assertEqual(payload['resources']['mc_cores'], 7)

        family_patch = payload['overrides']['row_config_patches'][0]
        self.assertEqual(family_patch['family'], 'exdqlm_univar')
        self.assertEqual(family_patch['manuscript_label'], 'exAL-U-T1')

        config_patch = family_patch['config_patch']
        self.assertNotIn('fit', config_patch)

        state = config_patch['models']['exdqlm_univar']['state_evolution']
        self.assertEqual(state['df_t'], 0.99999999)
        self.assertEqual(state['df_s1'], 0.99999)
        self.assertEqual(state['df_s2'], 0.99999)
        self.assertEqual(state['df_s67'], 0.99999)
        self.assertEqual(state['lambda'], 0.97)
        self.assertEqual(state['df_trans'], 0.9999999)
        self.assertEqual(state['df_covs'], 0.9999999)
        self.assertNotIn('df_discrep', state)


if __name__ == '__main__':
    unittest.main()
