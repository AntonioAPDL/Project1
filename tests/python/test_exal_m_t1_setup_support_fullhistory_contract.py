from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd')
CONFIG_PATH = PROJECT_ROOT / 'config' / 'exal_m_t1_setup_support_by_cutoff_v2_20260516.json'
SUMMARY_PATH = PROJECT_ROOT / 'Evironmetrics---REVISED-DOC-Corrected-2' / 'reports' / 'article_figure_lineage_audit_20260516' / 'summary.json'
APPENDIX_MANIFEST = PROJECT_ROOT / 'Evironmetrics---REVISED-DOC-Corrected-2' / 'figures' / 'appendix_cutoff_panels' / 'manifest.csv'


class ExalMT1SetupSupportFullhistoryContractTest(unittest.TestCase):
    def test_config_uses_full_history_for_all_cutoffs(self) -> None:
        payload = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        self.assertEqual(payload['history_start_date'], '1987-05-29')
        self.assertEqual(len(payload['cutoffs']), 5)
        for entry in payload['cutoffs']:
            self.assertEqual(entry['bundle_class'], 'histfix_long_history_bundle')
            self.assertEqual(entry['support_start'], '1987-05-29')
            self.assertIn('multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512', entry['selected_run_root'])
            self.assertIn('multimodel_v8_he2_publication_shared_inputs_20260510', entry['figure_bundle_root'])

    def test_article_audit_summary_records_passed_full_history_refresh(self) -> None:
        payload = json.loads(SUMMARY_PATH.read_text(encoding='utf-8'))
        self.assertTrue(payload['setup_support_full_history_all_cutoffs'])
        self.assertTrue(payload['setup_support_gdpc_all_cutoffs'])
        self.assertTrue(payload['uppercase_lowercase_figure_trees_match'])
        self.assertEqual(payload['status_counts']['updated_now'], 14)


if __name__ == '__main__':
    unittest.main()
