#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

from render_canonical_climate_index_diagnostics import render_single_index_plot  # noqa: E402


class CanonicalClimateIndexDiagnosticsTests(unittest.TestCase):
    def test_render_single_index_plot_writes_png(self) -> None:
        td = Path(tempfile.mkdtemp(prefix='climate_diag_plot_test_'))
        try:
            monthly = pd.DataFrame(
                {
                    'month_start': pd.to_datetime(['2021-01-01', '2021-02-01', '2021-03-01', '2021-04-01']),
                    'value': [0.2, 0.5, 0.1, 0.4],
                }
            )
            raw_daily = pd.DataFrame(
                {
                    'time': pd.date_range('2021-01-01', periods=120, freq='D').strftime('%Y-%m-%d'),
                    'oni': [0.1 + 0.01 * i for i in range(120)],
                }
            )
            std_daily = pd.DataFrame(
                {
                    'time': raw_daily['time'],
                    'oni': [(x - raw_daily['oni'].mean()) / raw_daily['oni'].std(ddof=1) for x in raw_daily['oni']],
                }
            )
            out = td / 'oni_diagnostic.png'
            render_single_index_plot(
                index_id='oni',
                display_name='ONI',
                monthly_long=monthly,
                raw_daily=raw_daily,
                std_daily=std_daily,
                mean=raw_daily['oni'].mean(),
                std=raw_daily['oni'].std(ddof=1),
                output_path=out,
                canonical_start='2021-01-01',
                canonical_end='2021-04-30',
                linear_tail_days=30,
            )
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)
        finally:
            for child in td.glob('*'):
                child.unlink()
            td.rmdir()


if __name__ == '__main__':
    unittest.main()
