from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

from validate_he2_bayesian_publication_relaunch_prelaunch import _pick_row, write_temp_smoke_config


class HE2PublicationRelaunchValidatorTests(unittest.TestCase):
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
