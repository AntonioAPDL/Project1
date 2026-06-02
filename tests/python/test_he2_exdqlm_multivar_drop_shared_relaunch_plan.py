from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / 'scripts'))

from build_he2_exdqlm_multivar_drop_shared_relaunch_plan import (  # noqa: E402
    FAMILY,
    SHARED_C_FACTOR,
    SHARED_DISCOUNT_SET,
    SHARED_EPSILON,
    build_payload,
    write_outputs,
)
from he2_exdqlm_multivar_drop_q50_policy import Q50_REPAIR_STABILIZATION


class He2ExdqlmMultivarDropSharedRelaunchPlanTests(unittest.TestCase):
    def test_build_payload_selects_shared_familywide_spec_and_stage_schedule(self) -> None:
        payload = build_payload()
        summary = payload['summary']
        self.assertEqual(summary['family'], FAMILY)
        self.assertEqual(summary['shared_discount_set'], SHARED_DISCOUNT_SET)
        self.assertEqual(summary['shared_epsilon'], SHARED_EPSILON)
        self.assertEqual(summary['shared_c_factor'], SHARED_C_FACTOR)
        self.assertEqual(summary['shared_state_evolution']['lambda'], 0.97)
        self.assertEqual(summary['shared_state_evolution']['df_discrep'], 0.99999)
        self.assertEqual(summary['q50_stabilization']['median_state_hold_after_guard_iters'], 10)
        self.assertEqual(summary['q50_stabilization']['median_state_blend_alpha'], 1.0)
        self.assertEqual(summary['q50_stabilization']['median_cov_blend_alpha'], 1.0)
        self.assertEqual(summary['q50_stabilization']['median_max_abs_gamma_step'], 0.075)
        self.assertEqual(summary['q50_stabilization']['median_max_abs_log_sigma_step'], 0.15)
        for key, value in Q50_REPAIR_STABILIZATION.items():
            self.assertEqual(summary['q50_stabilization'][key], value)
        self.assertEqual(payload['discount_ranking_rows'][0]['discount_set'], 'set08')
        self.assertEqual(len(payload['shared_spec_rows']), 5)
        self.assertEqual({row['shared_discount_set'] for row in payload['shared_spec_rows']}, {SHARED_DISCOUNT_SET})
        self.assertEqual({row['shared_epsilon'] for row in payload['shared_spec_rows']}, {SHARED_EPSILON})
        self.assertEqual(len(payload['stage_schedule']), 4)
        self.assertEqual(payload['stage_schedule'][0]['stage'], 'Stage 0')

    def test_write_outputs_materializes_report_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_root = Path(tmpdir) / 'plan'
            payload = write_outputs(out_root=out_root)

            self.assertTrue((out_root / 'shared_relaunch_spec.csv').exists())
            self.assertTrue((out_root / 'discount_set_ranking.csv').exists())
            self.assertTrue((out_root / 'canonical_input_bundle_contract.csv').exists())
            self.assertTrue((out_root / 'stage_schedule.json').exists())
            self.assertTrue((out_root / 'article_refresh_schedule.json').exists())
            self.assertTrue((out_root / 'HE2_EXDQLM_MULTIVAR_DROP_SHARED_RELAUNCH_PLAN_20260516.md').exists())

            text = (out_root / 'HE2_EXDQLM_MULTIVAR_DROP_SHARED_RELAUNCH_PLAN_20260516.md').read_text(encoding='utf-8')
            self.assertIn('shared forecast-covariance spec', text)
            self.assertIn('Stage 2', text)
            self.assertIn('historical_support_from_current_models', text)
            self.assertEqual(payload['summary']['shared_discount_set'], SHARED_DISCOUNT_SET)


if __name__ == '__main__':
    unittest.main()
