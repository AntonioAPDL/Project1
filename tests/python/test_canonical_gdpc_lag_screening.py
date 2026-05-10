from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd')
SCRIPT = ROOT / 'scripts' / 'screen_canonical_gdpc_lags.py'


class CanonicalGdpcLagScreeningTest(unittest.TestCase):
    def test_screening_selects_best_converged_bic(self) -> None:
        with tempfile.TemporaryDirectory(prefix='canonical_gdpc_screening_') as tmpdir:
            tmp = Path(tmpdir)
            artifact_root = tmp / 'artifact'
            std_root = artifact_root / 'intermediate'
            review_root = artifact_root / 'review' / 'stationarity'
            std_root.mkdir(parents=True, exist_ok=True)
            review_root.mkdir(parents=True, exist_ok=True)

            dates = pd.date_range('2000-01-01', periods=90, freq='D')
            x = np.linspace(0, 4 * np.pi, len(dates))
            df = pd.DataFrame(
                {
                    'time': dates.strftime('%Y-%m-%d'),
                    'oni': np.sin(x),
                    'amo': np.cos(x) + 0.15 * np.sin(2 * x),
                    'pna': np.sin(x + 0.7) + 0.1 * np.cos(3 * x),
                }
            )
            std_csv = std_root / 'combined_climate_indices_daily_standardized_20000101_20000330.csv'
            df.to_csv(std_csv, index=False)
            (review_root / 'CANONICAL_GDPC_STATIONARITY_AUDIT.md').write_text('# dummy\n', encoding='utf-8')

            config = {
                'version': 'vtest',
                'artifact_root': str(artifact_root),
                'canonical_window': {'start_date': '2000-01-01', 'end_date': '2000-03-30'},
                'gdpc': {
                    'method': 'gdpc',
                    'component_name': 'GDPC1',
                    'k': 1,
                    'tol': 1.0e-3,
                    'niter_max': 100,
                    'crit': 'BIC',
                    'require_convergence': True,
                    'blas_threads': 1,
                    'sign_rule': {'method': 'positive_correlation', 'anchor_index_id': 'oni'},
                },
                'screening': {
                    'enabled': True,
                    'candidate_k_values': [1, 2],
                    'criterion': 'BIC',
                    'tol': 1.0e-3,
                    'niter_max': 100,
                    'require_convergence': False,
                    'selection_rule': {
                        'primary_metric': 'criterion_value',
                        'objective': 'minimize',
                        'require_converged_fit': True,
                        'tie_breakers': ['lower_runtime_seconds', 'smaller_k'],
                    },
                },
                'compatibility_aliases': [],
                'indices': [],
            }
            cfg_path = tmp / 'config.yaml'
            cfg_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')

            subprocess.run(
                ['python3', str(SCRIPT), '--config', str(cfg_path)],
                cwd=ROOT,
                check=True,
            )

            summary_json = artifact_root / 'review' / 'lag_screening' / 'gdpc_k_screening_summary.json'
            payload = json.loads(summary_json.read_text(encoding='utf-8'))
            rows = payload['rows']
            self.assertEqual(sorted(row['k'] for row in rows), [1, 2])
            converged = [row for row in rows if row['converged']]
            self.assertTrue(converged)
            best = sorted(converged, key=lambda row: (row['criterion_value'], row['runtime_seconds'], row['k']))[0]
            self.assertEqual(payload['selection']['selected_k'], best['k'])


if __name__ == '__main__':
    unittest.main()
