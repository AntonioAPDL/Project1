from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_20260510.template.yaml'
ALL_CUTOFFS_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml'


class HE2PublicationRelaunchTemplateTests(unittest.TestCase):
    def test_template_exists_and_has_expected_campaign_contract(self) -> None:
        self.assertTrue(TEMPLATE.exists())
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(len(payload['campaign']['cutoffs']), 5)
        self.assertEqual(len(payload['bundles']['cutoffs']), 5)
        self.assertEqual(payload['campaign']['campaign_spec_id'], 'he2pubgdpc1r1')
        self.assertEqual(payload['validation']['fit_smoke_family'], 'ndlm_univar_keep')
        self.assertEqual(payload['validation']['fit_smoke_cutoff'], '20210123')

    def test_template_exposes_selection_resource_and_profile_controls(self) -> None:
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        selection = payload['selection']
        self.assertEqual(selection['cutoffs'], [])
        self.assertEqual(selection['families'], [])
        self.assertEqual(selection['manuscript_labels'], [])
        self.assertEqual(selection['run_ids'], [])
        self.assertEqual(selection['model_classes'], [])
        self.assertEqual(selection['quantiles'], [])
        self.assertEqual(selection['batch_file'], '')

        resources = payload['resources']
        self.assertIn('fit_parallel_workers', resources)
        self.assertIn('mc_cores', resources)

        profiles = payload['profiles']
        self.assertEqual(profiles['active'], 'default')
        self.assertIn('serial_debug', profiles['definitions'])
        self.assertIn('single_core_full', profiles['definitions'])
        self.assertEqual(profiles['definitions']['serial_debug']['resources']['fit_parallel_workers'], 1)
        self.assertEqual(profiles['definitions']['single_core_full']['resources']['mc_cores'], 1)

    def test_template_validation_includes_quantile_and_full_pipeline_smokes(self) -> None:
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        validation = payload['validation']
        self.assertIn('smoke_fit_overrides', validation)
        self.assertEqual(validation['smoke_fit_overrides']['exdqlm_multivar']['gamma_sigma']['max_iter'], 10)
        self.assertEqual(validation['smoke_fit_overrides']['exdqlm_univar']['gamma_sigma']['min_total_iters'], 10)
        self.assertEqual(validation['quantile_fit_smoke_family'], 'exdqlm_multivar_keep')
        self.assertEqual(validation['quantile_fit_smoke_quantiles'], [0.05])
        self.assertEqual(validation['full_pipeline_ndlm_family'], 'ndlm_univar_keep')
        self.assertEqual(validation['full_pipeline_quantile_family'], 'exdqlm_univar')
        self.assertEqual(validation['full_pipeline_quantiles'], [0.05])

    def test_all_cutoffs_template_hardens_queue_and_covers_both_cutoff_classes(self) -> None:
        payload = yaml.safe_load(ALL_CUTOFFS_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['queue']['pause_free_gb'], 25)
        self.assertEqual(payload['queue']['launch_free_gb'], 35)
        self.assertEqual(payload['queue']['heavy_free_gb'], 35)
        self.assertEqual(payload['profiles']['definitions']['disk_guarded_serial']['resources']['fit_parallel_workers'], 7)

        validation = payload['validation']
        self.assertEqual([case['cutoff'] for case in validation['quantile_fit_smoke_cases']], ['20210123', '20211221'])
        self.assertEqual([case['cutoff'] for case in validation['full_pipeline_quantile_smoke_cases']], ['20210123', '20211221'])
        self.assertEqual(validation['quantile_fit_smoke_cases'][0]['quantiles'], [0.2, 0.35, 0.5, 0.65, 0.8])


if __name__ == '__main__':
    unittest.main()
