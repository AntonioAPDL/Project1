from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
KEEP_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517.template.yaml'
DROP_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517.template.yaml'
KEEP_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517.yaml'
DROP_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517.yaml'


class He2DqlmMultivarAlProdcloneDiagnosticPackageTests(unittest.TestCase):
    def test_keep_prodclone_template_is_single_cutoff_q65_case(self) -> None:
        payload = yaml.safe_load(KEEP_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['campaign']['cutoffs'], ['20221225'])
        self.assertEqual(payload['campaign']['families'], ['dqlm_multivar_al_keep'])
        self.assertEqual(payload['bundles']['cutoffs'], ['20221225'])
        self.assertEqual(
            payload['validation']['quantile_fit_smoke_cases'],
            [
                {
                    'cutoff': '20221225',
                    'family': 'dqlm_multivar_al_keep',
                    'quantiles': [0.65],
                    'fit_overrides': {
                        'exdqlm_multivar': {
                            'gamma_sigma': {
                                'min_update_iters': 50,
                                'min_total_iters': 50,
                                'max_iter': 100,
                            },
                            'legacy': {
                                'n_samp': 2000,
                            }
                        }
                    },
                }
            ],
        )
        self.assertEqual(payload['validation']['full_pipeline_quantile_family'], '__disabled__')

    def test_drop_prodclone_template_is_single_cutoff_q65_case(self) -> None:
        payload = yaml.safe_load(DROP_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['campaign']['cutoffs'], ['20221225'])
        self.assertEqual(payload['campaign']['families'], ['dqlm_multivar_al_drop'])
        self.assertEqual(payload['bundles']['cutoffs'], ['20221225'])
        self.assertEqual(
            payload['validation']['quantile_fit_smoke_cases'],
            [
                {
                    'cutoff': '20221225',
                    'family': 'dqlm_multivar_al_drop',
                    'quantiles': [0.65],
                    'fit_overrides': {
                        'exdqlm_multivar': {
                            'gamma_sigma': {
                                'min_update_iters': 50,
                                'min_total_iters': 50,
                                'max_iter': 100,
                            },
                            'legacy': {
                                'n_samp': 2000,
                            }
                        }
                    },
                }
            ],
        )
        self.assertEqual(payload['validation']['full_pipeline_quantile_family'], '__disabled__')

    def test_batches_pin_the_expected_al_families(self) -> None:
        keep = yaml.safe_load(KEEP_BATCH.read_text(encoding='utf-8')) or {}
        drop = yaml.safe_load(DROP_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(keep['selection']['families'], ['dqlm_multivar_al_keep'])
        self.assertEqual(keep['selection']['cutoffs'], ['20221225'])
        self.assertEqual(keep['overrides']['row_config_patches'][0]['config_patch']['models']['exdqlm_multivar']['likelihood_mode'], 'al')
        self.assertEqual(drop['selection']['families'], ['dqlm_multivar_al_drop'])
        self.assertEqual(drop['selection']['cutoffs'], ['20221225'])
        self.assertEqual(drop['overrides']['row_config_patches'][0]['config_patch']['models']['exdqlm_multivar']['likelihood_mode'], 'al')


if __name__ == '__main__':
    unittest.main()
