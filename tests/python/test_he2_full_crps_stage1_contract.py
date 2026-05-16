from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / 'scripts'))

from build_he2_full_crps_stage1_contract import (  # noqa: E402
    DEFAULT_ALIGNMENT_AUDIT,
    DEFAULT_HISTORICAL_AUDIT,
    DEFAULT_INPUT_AUDIT_SUMMARY,
    QUARANTINED_BUILDERS,
    build_outputs,
    write_outputs,
)


class He2FullCrpsStage1ContractTests(unittest.TestCase):
    def test_build_outputs_excludes_completed_reference_family_and_groups_remaining_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = build_outputs(
                historical_audit_path=DEFAULT_HISTORICAL_AUDIT,
                alignment_audit_path=DEFAULT_ALIGNMENT_AUDIT,
                input_audit_summary_path=DEFAULT_INPUT_AUDIT_SUMMARY,
                out_root=Path(tmpdir),
            )

        matrix_rows = payload['matrix_rows']
        self.assertEqual(len(matrix_rows), 40)
        self.assertNotIn('exdqlm_multivar_keep', {row['family'] for row in matrix_rows})
        self.assertEqual({row['wave'] for row in matrix_rows}, {'wave_a_ndlm', 'wave_b_univariate_bridge', 'wave_c_multivariate_bridge'})
        self.assertEqual(payload['summary']['counts']['rows_by_wave']['wave_a_ndlm'], 15)
        self.assertEqual(payload['summary']['counts']['rows_by_wave']['wave_b_univariate_bridge'], 10)
        self.assertEqual(payload['summary']['counts']['rows_by_wave']['wave_c_multivariate_bridge'], 15)
        self.assertEqual(
            payload['summary']['cutoffs_requiring_corrected_full_history_attention'],
            ['20210123', '20211112', '20221225'],
        )
        self.assertIn('epsilon_winner', payload['summary']['counts']['rows_by_selected_spec_class'])
        self.assertIn('ndlm_postfix_winner', payload['summary']['counts']['rows_by_selected_spec_class'])
        self.assertIn('univar_winner', payload['summary']['counts']['rows_by_selected_spec_class'])

    def test_write_outputs_freezes_source_configs_and_documents_quarantined_builders(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_root = Path(tmpdir) / 'stage1'
            payload = write_outputs(
                historical_audit_path=DEFAULT_HISTORICAL_AUDIT,
                alignment_audit_path=DEFAULT_ALIGNMENT_AUDIT,
                input_audit_summary_path=DEFAULT_INPUT_AUDIT_SUMMARY,
                out_root=out_root,
            )

            self.assertTrue((out_root / 'remaining_family_relaunch_matrix.csv').exists())
            self.assertTrue((out_root / 'remaining_family_spec_freeze.csv').exists())
            self.assertTrue((out_root / 'wave_a_ndlm_rows.csv').exists())
            self.assertTrue((out_root / 'launcher_qualification.json').exists())
            self.assertTrue((out_root / 'HE2_FULL_CRPS_STAGE1_LAUNCHER_QUALIFICATION_20260516.md').exists())

            frozen_paths = [Path(row['frozen_resolved_config_path']) for row in payload['matrix_rows'][:3]]
            for frozen in frozen_paths:
                self.assertTrue(frozen.exists())

            launcher_text = (out_root / 'HE2_FULL_CRPS_STAGE1_LAUNCHER_QUALIFICATION_20260516.md').read_text(encoding='utf-8')
            for builder in QUARANTINED_BUILDERS:
                self.assertIn(builder, launcher_text)
            self.assertIn('Wave A is the approved first relaunch wave', launcher_text)


if __name__ == '__main__':
    unittest.main()
