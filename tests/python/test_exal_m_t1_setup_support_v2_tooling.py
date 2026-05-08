#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

from render_exal_m_t1_setup_support_by_cutoff_v2 import load_config  # noqa: E402


class ExalMT1SetupSupportV2ToolingTests(unittest.TestCase):
    def test_config_has_five_cutoffs_and_representative_slug(self) -> None:
        cfg = load_config(ROOT / 'config' / 'exal_m_t1_setup_support_by_cutoff_v2_20260507.json')
        self.assertEqual(len(cfg['cutoffs']), 5)
        self.assertEqual(cfg['representative_article_cutoff'], '20221225_exal_m_t1')
        self.assertEqual(cfg['history_start_date'], '1987-05-29')
        self.assertEqual(cfg['forecast_plot_pre_days'], 28)
        self.assertEqual(cfg['forecast_plot_post_days'], 28)
        self.assertEqual(cfg['flow_figure_display_scale'], 'log1p_cms')

    def test_entries_point_to_existing_roots_and_expected_bundle_classes(self) -> None:
        cfg = load_config(ROOT / 'config' / 'exal_m_t1_setup_support_by_cutoff_v2_20260507.json')
        classes = {entry['slug']: entry['bundle_class'] for entry in cfg['cutoffs']}
        self.assertEqual(classes['20210123_exal_m_t1'], 'short_window_synth_bundle')
        self.assertEqual(classes['20211112_exal_m_t1'], 'short_window_synth_bundle')
        self.assertEqual(classes['20211221_exal_m_t1'], 'histfix_long_history_bundle')
        self.assertEqual(classes['20220511_exal_m_t1'], 'histfix_long_history_bundle')
        self.assertEqual(classes['20221225_exal_m_t1'], 'histfix_long_history_bundle')
        for entry in cfg['cutoffs']:
            self.assertTrue(Path(entry['selected_run_root']).exists())
            self.assertTrue(Path(entry['figure_bundle_root']).exists())
            self.assertRegex(entry['published_crps'], r'^0\.\d{4}$')

    def test_support_start_contract_matches_bundle_class(self) -> None:
        cfg = load_config(ROOT / 'config' / 'exal_m_t1_setup_support_by_cutoff_v2_20260507.json')
        for entry in cfg['cutoffs']:
            retros_path = Path(entry['selected_run_root']) / 'inputs' / 'shared' / 'retros' / 'retros.csv'
            with retros_path.open(newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.assertGreater(len(rows), 0)
            date_key = 'Date' if 'Date' in rows[0] else 'date'
            self.assertEqual(rows[-1][date_key], entry['cutoff_date'])
            if entry['bundle_class'] == 'short_window_synth_bundle':
                self.assertEqual(rows[0][date_key], entry['support_start'])
            else:
                self.assertEqual(entry['support_start'], cfg['history_start_date'])
                self.assertTrue((Path(entry['figure_bundle_root']) / 'inputs' / 'retros_source_lineage.csv').exists())


if __name__ == '__main__':
    unittest.main()
