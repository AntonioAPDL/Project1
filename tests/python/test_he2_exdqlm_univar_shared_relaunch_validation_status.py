from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

import build_he2_exdqlm_univar_shared_relaunch_validation_status as status_builder  # noqa: E402


class He2ExdqlmUnivarSharedRelaunchValidationStatusTests(unittest.TestCase):
    def test_build_payload_reports_in_progress_state_without_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            validation_outdir = root / 'validation'
            report_root = root / 'report'
            template_path = root / 'template.yaml'
            fit_root = validation_outdir / 'smoke_runs' / 'fit_quantile_univar' / 'exdqlm_univar' / '20210123' / 'fit_smoke_exdqlm_univar_20210123_qsubset'
            full_pipeline_root = validation_outdir / 'smoke_runs' / 'full_pipeline' / 'quantile' / 'exdqlm_univar' / '20210123' / 'full_pipeline_exdqlm_univar_20210123_qsubset'
            fit_log = fit_root / 'fit' / 'exdqlm_univar' / 'q=50' / 'logs'
            fit_out = fit_root / 'fit' / 'exdqlm_univar' / 'q=50' / 'outputs'
            fit_log.mkdir(parents=True, exist_ok=True)
            fit_out.mkdir(parents=True, exist_ok=True)
            full_fit_log = full_pipeline_root / 'fit' / 'exdqlm_univar' / 'q=50' / 'logs'
            full_fit_log.mkdir(parents=True, exist_ok=True)
            template_path.write_text('validation:\n  full_pipeline_quantile_smoke_cases:\n    - cutoff: \"20210123\"\n', encoding='utf-8')

            for cutoff in ['20210123', '20211112', '20211221', '20220511', '20221225']:
                (validation_outdir / f'{cutoff}.stdout.log').write_text('Unified run complete.\n', encoding='utf-8')
                (validation_outdir / f'{cutoff}.stderr.log').write_text('data_prep_shared: shared input validation passed under /tmp/x\n', encoding='utf-8')
            (validation_outdir / 'exdqlm_univar.stdout.log').write_text('Unified run complete.\n', encoding='utf-8')
            (validation_outdir / 'exdqlm_univar.stderr.log').write_text('data_prep_shared: shared input validation passed under /tmp/x\n', encoding='utf-8')
            (validation_outdir / 'test_2.stderr.log').write_text('..............................\n----------------------------------------------------------------------\nRan 30 tests in 1.234s\n\nOK\n', encoding='utf-8')
            (fit_log / 'univar_legacy.log').write_text(
                '[univ_legacy_env_delta] df_t=0.99999999 df_s1=0.99999000 df_s2=0.99999000 df_s67=0.99999000 lambda=0.97000000\n'
                'VB converged: 18 iterations, 146.004 seconds \n'
                'Sampling finished:  21.832 seconds \n'
                'Variables saved to: /tmp/variables_50_exAL_synth_DISC_uni.RData \n',
                encoding='utf-8',
            )
            (fit_log / 'univar_theory_summary.log').write_text('implementation_mode=legacy_bridge\n', encoding='utf-8')
            (fit_out / 'variables_50_exAL_synth_DISC_uni.RData').write_text('stub', encoding='utf-8')
            (full_fit_log / 'univar_legacy.log').write_text('[1] 0\n', encoding='utf-8')

            with mock.patch.object(status_builder, 'VALIDATION_OUTDIR', validation_outdir), \
                    mock.patch.object(status_builder, 'SUMMARY_JSON', validation_outdir / 'prelaunch_validation_summary.json'), \
                    mock.patch.object(status_builder, 'REPORT_ROOT', report_root), \
                    mock.patch.object(status_builder, 'OUT_JSON', report_root / 'validation.json'), \
                    mock.patch.object(status_builder, 'OUT_MD', report_root / 'validation.md'), \
                    mock.patch.object(status_builder, 'FIT_SMOKE_ROOT', fit_root), \
                    mock.patch.object(status_builder, 'TEMPLATE', template_path), \
                    mock.patch.object(status_builder, 'FULL_PIPELINE_ROOT', validation_outdir / 'smoke_runs' / 'full_pipeline' / 'quantile' / 'exdqlm_univar'), \
                    mock.patch.object(status_builder, '_validator_is_running', return_value=True):
                payload = status_builder.build_payload()

            self.assertEqual(payload['status'], 'validation_in_progress')
            self.assertTrue(payload['validator_running'])
            self.assertEqual(payload['cutoff_smoke_checks']['passed'], 5)
            self.assertTrue(payload['family_smoke_check']['passed'])
            self.assertTrue(payload['test_block_check']['passed'])
            self.assertTrue(payload['fit_smoke_check']['passed'])
            self.assertEqual(payload['full_pipeline_checks']['started'], 1)
            self.assertEqual(payload['full_pipeline_checks']['passed'], 0)
            self.assertEqual(payload['full_pipeline_checks']['expected'], 1)
            self.assertFalse(payload['ready_for_launch_after_validation'])

    def test_build_payload_prefers_summary_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            validation_outdir = root / 'validation'
            report_root = root / 'report'
            validation_outdir.mkdir(parents=True, exist_ok=True)
            summary_json = validation_outdir / 'prelaunch_validation_summary.json'
            summary_json.write_text(json.dumps({
                'builder': {'generated_configs': 5},
                'selected_rows': ['row1'],
                'checks': {
                    'bundle_rows': {'passed': 5},
                    'generated_configs': {'passed': 5},
                    'plan_rows': {'passed': 5},
                    'smoke_runs': {'passed': 4, 'skipped': 0},
                },
                'smoke_runs': [{'name': 'case1', 'status': 'passed'}],
            }), encoding='utf-8')

            with mock.patch.object(status_builder, 'VALIDATION_OUTDIR', validation_outdir), \
                    mock.patch.object(status_builder, 'SUMMARY_JSON', summary_json), \
                    mock.patch.object(status_builder, 'REPORT_ROOT', report_root), \
                    mock.patch.object(status_builder, 'OUT_JSON', report_root / 'validation.json'), \
                    mock.patch.object(status_builder, 'OUT_MD', report_root / 'validation.md'):
                payload = status_builder.build_payload()

            self.assertEqual(payload['status'], 'validated')
            self.assertTrue(payload['ready_for_launch_after_validation'])
            self.assertEqual(payload['checks']['smoke_runs']['passed'], 4)


if __name__ == '__main__':
    unittest.main()
