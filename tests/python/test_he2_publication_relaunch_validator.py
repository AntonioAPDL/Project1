from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

from validate_he2_bayesian_publication_relaunch_prelaunch import _choose_smoke_row, _normalize_ndlm_smoke_cases, _pick_row, write_temp_smoke_config
from validate_he2_bayesian_publication_relaunch_prelaunch import _normalize_quantile_smoke_cases, _prune_r_artifacts


class HE2PublicationRelaunchValidatorTests(unittest.TestCase):
    def test_normalize_quantile_smoke_cases_supports_explicit_case_list(self) -> None:
        validation_cfg = {
            'quantile_fit_smoke_cases': [
                {'family': 'exdqlm_multivar_keep', 'cutoff': '20210123', 'quantiles': [0.2, 0.35]},
                {'family': 'exdqlm_multivar_keep', 'cutoff': '20211221', 'quantiles': [0.5, 0.65, 0.8], 'label': 'full_history'},
            ]
        }
        cases = _normalize_quantile_smoke_cases(
            validation_cfg,
            cases_key='quantile_fit_smoke_cases',
            family_key='quantile_fit_smoke_family',
            cutoff_key='quantile_fit_smoke_cutoff',
            quantiles_key='quantile_fit_smoke_quantiles',
            default_family='exdqlm_multivar_keep',
            default_cutoff='20210123',
            default_quantiles=[0.05],
        )
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0]['cutoff'], '20210123')
        self.assertEqual(cases[0]['quantiles'], [0.2, 0.35])
        self.assertEqual(cases[1]['cutoff'], '20211221')
        self.assertEqual(cases[1]['label'], 'full_history')

    def test_normalize_quantile_smoke_cases_honors_disabled_family_sentinel(self) -> None:
        validation_cfg = {
            'full_pipeline_quantile_family': '__disabled__',
            'full_pipeline_quantile_cutoff': '20210123',
            'full_pipeline_quantiles': [0.35, 0.50, 0.65],
            'full_pipeline_quantile_smoke_cases': [],
        }
        cases = _normalize_quantile_smoke_cases(
            validation_cfg,
            cases_key='full_pipeline_quantile_smoke_cases',
            family_key='full_pipeline_quantile_family',
            cutoff_key='full_pipeline_quantile_cutoff',
            quantiles_key='full_pipeline_quantiles',
            default_family='exdqlm_multivar_keep',
            default_cutoff='20210123',
            default_quantiles=[0.05],
        )
        self.assertEqual(cases, [])

    def test_normalize_ndlm_smoke_cases_supports_explicit_case_list(self) -> None:
        validation_cfg = {
            'full_pipeline_ndlm_cases': [
                {'family': 'ndlm_univar_keep', 'cutoff': '20210123'},
                {'family': 'ndlm_main_drop', 'cutoff': '20210123', 'label': 'drop_smoke'},
                {'family': 'ndlm_main_keep', 'cutoff': '20221225', 'fit_overrides': {'ndlm_main': {'gamma_sigma': {'max_iter': 25}}}},
            ]
        }
        cases = _normalize_ndlm_smoke_cases(
            validation_cfg,
            cases_key='full_pipeline_ndlm_cases',
            family_key='full_pipeline_ndlm_family',
            cutoff_key='full_pipeline_ndlm_cutoff',
            default_family='ndlm_univar_keep',
            default_cutoff='20210123',
        )
        self.assertEqual([case['family'] for case in cases], ['ndlm_univar_keep', 'ndlm_main_drop', 'ndlm_main_keep'])
        self.assertEqual(cases[1]['label'], 'drop_smoke')
        self.assertEqual(cases[2]['cutoff'], '20221225')
        self.assertEqual(cases[2]['fit_overrides']['ndlm_main']['gamma_sigma']['max_iter'], 25)

    def test_normalize_ndlm_smoke_cases_honors_disabled_family_sentinel(self) -> None:
        cases = _normalize_ndlm_smoke_cases(
            {'full_pipeline_ndlm_family': '__disabled__'},
            cases_key='full_pipeline_ndlm_cases',
            family_key='full_pipeline_ndlm_family',
            cutoff_key='full_pipeline_ndlm_cutoff',
            default_family='ndlm_univar_keep',
            default_cutoff='20210123',
        )
        self.assertEqual(cases, [])

    def test_prune_r_artifacts_removes_only_r_binary_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            keep = root / 'keep.txt'
            keep.write_text('ok', encoding='utf-8')
            rdata = root / 'fit' / 'outputs' / 'big.RData'
            rdata.parent.mkdir(parents=True, exist_ok=True)
            rdata.write_bytes(b'a' * 16)
            rds = root / 'fit' / 'outputs' / 'cache.rds'
            rds.write_bytes(b'b' * 8)

            result = _prune_r_artifacts(root)
            self.assertEqual(result['removed_files'], 2)
            self.assertEqual(result['removed_bytes'], 24)
            self.assertTrue(keep.exists())
            self.assertFalse(rdata.exists())
            self.assertFalse(rds.exists())

    def test_choose_smoke_row_returns_none_when_class_missing(self) -> None:
        rows = [
            {'family_id': 'exdqlm_multivar_keep', 'cutoff': '20210123', 'model_class': 'quantile_multivariate'},
        ]
        row = _choose_smoke_row(rows, preferred_family='ndlm_univar_keep', preferred_cutoff='20210123', class_name='ndlm')
        self.assertIsNone(row)

    def test_choose_smoke_row_falls_back_within_available_class_scope(self) -> None:
        rows = [
            {'family_id': 'ndlm_main_keep', 'cutoff': '20211112', 'model_class': 'ndlm'},
            {'family_id': 'ndlm_univar_keep', 'cutoff': '20210123', 'model_class': 'ndlm'},
        ]
        row = _choose_smoke_row(rows, preferred_family='missing_ndlm', preferred_cutoff='20210123', class_name='ndlm')
        self.assertEqual(row['family_id'], 'ndlm_univar_keep')
        self.assertEqual(row['cutoff'], '20210123')

    def test_pick_row_supports_univariate_quantile_full_pipeline_selection(self) -> None:
        rows = [
            {'family_id': 'exdqlm_univar', 'cutoff': '20210123', 'model_class': 'quantile_univariate'},
            {'family_id': 'exdqlm_multivar_keep', 'cutoff': '20210123', 'model_class': 'quantile_multivariate'},
        ]
        row = _pick_row(rows, family='exdqlm_univar', cutoff='20210123', class_name='quantile_univariate')
        self.assertEqual(row['family_id'], 'exdqlm_univar')

    def test_write_temp_smoke_config_applies_fit_overrides_and_stage_flags(self) -> None:
        src_payload = {
            'run': {
                'run_id': 'orig',
                'run_root': '/tmp/orig',
                'threads': {'mc_cores': 4},
            },
            'stages': {
                'data_prep_shared': True,
                'forecats': True,
                'fit': True,
                'post': True,
                'validate': True,
                'report': True,
            },
            'fit': {
                'quantiles': [0.05, 0.5, 0.95],
                'parallel': {'workers': 7},
                'exdqlm_multivar': {
                    'gamma_sigma': {
                        'min_update_iters': 50,
                        'min_total_iters': 50,
                        'max_iter': 100,
                    },
                    'legacy': {'n_samp': 2000},
                },
            },
        }
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            src = tmp / 'source.yaml'
            src.write_text(yaml.safe_dump(src_payload, sort_keys=False), encoding='utf-8')
            out = write_temp_smoke_config(
                src,
                run_id='smoke_run',
                run_root=tmp / 'run',
                stage_mode='fit',
                quantile_subset=[0.05],
                fit_parallel_workers=1,
                mc_cores=1,
                fit_overrides={
                    'exdqlm_multivar': {
                        'gamma_sigma': {
                            'min_update_iters': 3,
                            'min_total_iters': 10,
                            'max_iter': 10,
                        },
                        'legacy': {'n_samp': 512},
                    }
                },
            )
            payload = yaml.safe_load(out.read_text(encoding='utf-8')) or {}
            self.assertEqual(payload['run']['run_id'], 'smoke_run')
            self.assertEqual(payload['run']['threads']['mc_cores'], 1)
            self.assertTrue(payload['stages']['data_prep_shared'])
            self.assertTrue(payload['stages']['fit'])
            self.assertFalse(payload['stages']['post'])
            self.assertFalse(payload['stages']['validate'])
            self.assertFalse(payload['stages']['report'])
            self.assertEqual(payload['fit']['quantiles'], [0.05])
            self.assertEqual(payload['fit']['parallel']['workers'], 1)
            self.assertEqual(payload['fit']['exdqlm_multivar']['gamma_sigma']['min_update_iters'], 3)
            self.assertEqual(payload['fit']['exdqlm_multivar']['gamma_sigma']['min_total_iters'], 10)
            self.assertEqual(payload['fit']['exdqlm_multivar']['gamma_sigma']['max_iter'], 10)
            self.assertEqual(payload['fit']['exdqlm_multivar']['legacy']['n_samp'], 512)


if __name__ == '__main__':
    unittest.main()
