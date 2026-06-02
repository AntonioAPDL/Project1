from __future__ import annotations

import unittest
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from he2_exdqlm_multivar_drop_q50_policy import Q50_REPAIR_STABILIZATION  # noqa: E402

TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.template.yaml'
BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.yaml'


class He2ExdqlmMultivarDropSharedspecPackageTests(unittest.TestCase):
    def test_template_targets_drop_family_and_expected_validator_cases(self) -> None:
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['campaign']['families'], ['exdqlm_multivar_drop'])
        self.assertIn('exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516', payload['campaign']['artifact_root'])
        self.assertEqual(payload['validation']['cutoff_smoke_family'], 'exdqlm_multivar_drop')
        self.assertEqual(payload['validation']['quantile_fit_smoke_family'], 'exdqlm_multivar_drop')
        self.assertEqual(payload['validation']['full_pipeline_quantile_family'], 'exdqlm_multivar_drop')
        self.assertEqual(
            payload['validation']['quantile_fit_smoke_cases'],
            [
                {'cutoff': '20210123', 'family': 'exdqlm_multivar_drop', 'quantiles': [0.50]},
                {'cutoff': '20211221', 'family': 'exdqlm_multivar_drop', 'quantiles': [0.50]},
                {'cutoff': '20221225', 'family': 'exdqlm_multivar_drop', 'quantiles': [0.50, 0.65]},
            ],
        )

    def test_batch_freezes_shared_spec_and_drop_manuscript_label(self) -> None:
        payload = yaml.safe_load(BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_drop'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 7)
        self.assertEqual(payload['resources']['mc_cores'], 7)

        family_patch = payload['overrides']['row_config_patches'][0]
        self.assertEqual(family_patch['family'], 'exdqlm_multivar_drop')
        self.assertEqual(family_patch['manuscript_label'], 'exAL-M-T0')

        fit = family_patch['config_patch']['fit']['exdqlm_multivar']
        self.assertEqual(fit['legacy']['forecast_cov']['epsilon'], 30.0)
        self.assertEqual(fit['legacy']['forecast_cov']['c_factor'], 1.0)
        self.assertEqual(fit['gamma_sigma']['quantile_overrides']['q50']['freeze_target'], 'states')
        self.assertEqual(
            fit['gamma_sigma']['quantile_overrides']['q50']['stabilization']['median_state_hold_after_guard_iters'],
            10,
        )
        self.assertEqual(fit['gamma_sigma']['quantile_overrides']['q50']['stabilization'], Q50_REPAIR_STABILIZATION)

        state = family_patch['config_patch']['models']['exdqlm_multivar']['state_evolution']
        self.assertEqual(state['df_t'], 0.99999999)
        self.assertEqual(state['df_s1'], 0.99999)
        self.assertEqual(state['df_s2'], 0.99999)
        self.assertEqual(state['df_s67'], 0.99999)
        self.assertEqual(state['df_discrep'], 0.99999)
        self.assertEqual(state['lambda'], 0.97)
        self.assertEqual(state['df_trans'], 0.9999999)
        self.assertEqual(state['df_covs'], 0.9999999)


if __name__ == '__main__':
    unittest.main()
