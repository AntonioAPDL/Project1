#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

from canonical_climate_indices_lib import (  # noqa: E402
    interpolate_monthly_to_daily,
    monthly_wide_to_long,
    parse_psl_monthly_text,
    standardize_daily_matrix,
)


class CanonicalClimateIndicesPipelineTests(unittest.TestCase):
    def test_parse_psl_monthly_text_extracts_monthly_block(self) -> None:
        payload = """header line\nmore header\n1987  1.0 2.0 3.0 4.0 5.0 6.0 7.0 8.0 9.0 10.0 11.0 12.0\n1988  2.0 3.0 4.0 5.0 6.0 7.0 8.0 9.0 10.0 11.0 12.0 13.0\nfooter\n"""
        df = parse_psl_monthly_text(payload)
        self.assertEqual(list(df.columns), ['Year'] + [f'Month_{idx}' for idx in range(1, 13)])
        self.assertEqual(df['Year'].tolist(), [1987, 1988])
        self.assertEqual(float(df.loc[0, 'Month_1']), 1.0)
        self.assertEqual(float(df.loc[1, 'Month_12']), 13.0)

    def test_monthly_wide_to_long_filters_requested_window(self) -> None:
        df = pd.DataFrame(
            {
                'Year': [1987, 1988],
                **{f'Month_{idx}': [float(idx), float(idx + 12)] for idx in range(1, 13)},
            }
        )
        out = monthly_wide_to_long(df, start_month='1987-05-01', end_month='1988-02-01')
        self.assertEqual(out['month_start'].min().strftime('%Y-%m-%d'), '1987-05-01')
        self.assertEqual(out['month_start'].max().strftime('%Y-%m-%d'), '1988-02-01')
        self.assertEqual(len(out), 10)

    def test_interpolate_monthly_to_daily_produces_full_daily_grid(self) -> None:
        monthly = pd.DataFrame(
            {
                'month_start': pd.to_datetime(['1987-01-01', '1987-02-01', '1987-03-01', '1987-04-01']),
                'value': [0.0, 1.0, 0.5, 1.5],
            }
        )
        daily = interpolate_monthly_to_daily(
            monthly,
            start_date='1987-01-15',
            end_date='1987-03-20',
            linear_tail_days=30,
        )
        self.assertEqual(daily['time'].iloc[0], '1987-01-15')
        self.assertEqual(daily['time'].iloc[-1], '1987-03-20')
        self.assertEqual(len(daily), 65)
        self.assertFalse(daily['value'].isna().any())

    def test_standardize_daily_matrix_yields_unit_scale_columns(self) -> None:
        df = pd.DataFrame(
            {
                'time': ['1987-05-29', '1987-05-30', '1987-05-31', '1987-06-01'],
                'oni': [1.0, 2.0, 3.0, 4.0],
                'nao': [2.0, 4.0, 6.0, 8.0],
            }
        )
        out, stats = standardize_daily_matrix(df, date_col='time', ddof=1)
        self.assertEqual(len(stats), 2)
        for col in ['oni', 'nao']:
            self.assertTrue(math.isclose(float(out[col].mean()), 0.0, abs_tol=1e-12))
            self.assertTrue(math.isclose(float(out[col].std(ddof=1)), 1.0, rel_tol=1e-12, abs_tol=1e-12))


if __name__ == '__main__':
    unittest.main()
