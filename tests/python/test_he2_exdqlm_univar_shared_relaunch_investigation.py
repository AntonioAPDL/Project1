from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

from build_he2_exdqlm_univar_shared_relaunch_investigation import (  # noqa: E402
    OUT_ROOT,
    build_outputs,
    write_outputs,
)


class He2ExdqlmUnivarSharedRelaunchInvestigationTests(unittest.TestCase):
    def test_build_outputs_identifies_univar_scope_and_readiness_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = build_outputs(out_root=Path(tmpdir))

        scope_rows = payload['scope_rows']
        self.assertEqual(len(scope_rows), 5)
        self.assertEqual({row['family'] for row in scope_rows}, {'exdqlm_univar'})
        self.assertEqual({row['manuscript_label'] for row in scope_rows}, {'exAL-U-T1'})
        self.assertEqual(
            [row['cutoff'] for row in scope_rows],
            ['20210123', '20211112', '20211221', '20220511', '20221225'],
        )

        readiness = payload['readiness']
        self.assertEqual(readiness['status'], 'INVESTIGATED_ONLY')
        self.assertFalse(readiness['ready_for_no_launch_packaging'])
        self.assertFalse(readiness['ready_for_launch_after_validation'])
        self.assertEqual(
            readiness['cutoffs_missing_full_history_today'],
            ['20210123', '20211112', '20221225'],
        )
        self.assertIn('shared discount-spec bundle must be projected', ' '.join(readiness['why_not_ready']))

    def test_write_outputs_documents_df_discrep_and_forecast_cov_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_root = Path(tmpdir) / 'univar_investigation'
            payload = write_outputs(out_root=out_root)

            self.assertTrue((out_root / 'HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_INVESTIGATION_20260516.md').exists())
            self.assertTrue((out_root / 'exdqlm_univar_scope_matrix.csv').exists())
            self.assertTrue((out_root / 'bundle_parity_table.csv').exists())
            self.assertTrue((out_root / 'spec_parity_table.csv').exists())
            self.assertTrue((out_root / 'reuse_adaptation_mapping_table.csv').exists())
            self.assertTrue((out_root / 'readiness_summary.json').exists())

            spec_rows = {row['item']: row for row in payload['spec_rows']}
            self.assertEqual(spec_rows['df_discrep']['mapping_status'], 'not_applicable')
            self.assertEqual(spec_rows['c_factor']['mapping_status'], 'requires_code_or_policy_decision')
            self.assertEqual(spec_rows['epsilon']['mapping_status'], 'requires_code_or_policy_decision')
            self.assertEqual(spec_rows['freeze_target']['mapping_status'], 'partial_equivalent')

            md = (out_root / 'HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_INVESTIGATION_20260516.md').read_text(encoding='utf-8')
            self.assertIn('the correct target is exactly `exdqlm_univar`', md)
            self.assertIn('`df_discrep` is not applicable to `exdqlm_univar`', md)
            self.assertIn('`epsilon` and `c_factor` are present in the univariate source config but are not read', md)


if __name__ == '__main__':
    unittest.main()
