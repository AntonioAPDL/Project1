from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / 'scripts'))

from build_he2_exdqlm_univar_shared_relaunch_plan import (  # noqa: E402
    FAMILY,
    MANUSCRIPT_LABEL,
    SHARED_DISCOUNT_SET,
    build_payload,
    write_outputs,
)


class He2ExdqlmUnivarSharedRelaunchPlanTests(unittest.TestCase):
    def test_build_payload_freezes_absent_forecast_cov_and_df_discrep_contract(self) -> None:
        payload = build_payload()
        summary = payload['summary']
        self.assertEqual(summary['family'], FAMILY)
        self.assertEqual(summary['manuscript_label'], MANUSCRIPT_LABEL)
        self.assertEqual(summary['shared_discount_set'], SHARED_DISCOUNT_SET)
        self.assertEqual(summary['forecast_cov_contract'], 'not_applied_by_design')
        self.assertEqual(summary['df_discrep_contract'], 'absent_by_design')
        self.assertNotIn('df_discrep', summary['shared_state_evolution'])
        self.assertEqual(summary['shared_state_evolution']['df_s1'], 0.99999)
        self.assertEqual(summary['q50_stabilization_contract']['freeze_target'], 'not_operative_under_legacy_bridge')
        self.assertEqual(summary['q50_stabilization_contract']['terminal_sampling_guard'], 'not_supported_by_univar_runner')
        self.assertEqual(len(payload['shared_spec_rows']), 5)
        self.assertEqual({row['forecast_cov_contract'] for row in payload['shared_spec_rows']}, {'not_applied_by_design'})
        self.assertEqual({row['df_discrep_contract'] for row in payload['shared_spec_rows']}, {'absent_by_design'})
        self.assertEqual(len(payload['stage_schedule']), 4)
        self.assertEqual(payload['stage_schedule'][1]['stage'], 'Stage 1')

    def test_write_outputs_materializes_report_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_root = Path(tmpdir) / 'plan'
            payload = write_outputs(out_root=out_root)
            self.assertTrue((out_root / 'shared_relaunch_spec.csv').exists())
            self.assertTrue((out_root / 'current_source_scope.csv').exists())
            self.assertTrue((out_root / 'state_projection_comparison.csv').exists())
            self.assertTrue((out_root / 'canonical_input_bundle_contract.csv').exists())
            self.assertTrue((out_root / 'validation_schedule.json').exists())
            self.assertTrue((out_root / 'workflow_refresh_schedule.json').exists())
            self.assertTrue((out_root / 'HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md').exists())
            text = (out_root / 'HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md').read_text(encoding='utf-8')
            self.assertIn('forecast-covariance knobs (`epsilon`, `c_factor`) remain absent by design', text)
            self.assertIn('q50 gamma/sigma stabilization knobs from the multivariate relaunch are not operative', text)
            self.assertIn('five_cutoff_crps_validation_sources', text)
            self.assertEqual(payload['summary']['shared_discount_set'], SHARED_DISCOUNT_SET)


if __name__ == '__main__':
    unittest.main()
