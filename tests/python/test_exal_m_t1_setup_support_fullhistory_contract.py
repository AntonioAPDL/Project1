from __future__ import annotations

import csv
import json
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from article_repository_binding import active_article_root


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / 'config' / 'exal_m_t1_setup_support_by_cutoff_v2_20260516.json'
ARTICLE_ROOT = active_article_root(PROJECT_ROOT)
APPENDIX_MANIFEST = active_article_root(PROJECT_ROOT) / 'figures' / 'appendix_cutoff_panels' / 'manifest.csv'


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
        # The lineage report is ignored output, so regenerate it outside the
        # article rather than depending on files left by a previous checkout.
        sys.path.insert(0, str(ARTICLE_ROOT / 'scripts'))
        spec = importlib.util.spec_from_file_location('isolated_lineage_audit', ARTICLE_ROOT / 'scripts/build_article_figure_lineage_audit.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        original_layout = audit.build_layout(ARTICLE_ROOT)
        with tempfile.TemporaryDirectory() as output:
            class IsolatedLayout:
                reports_dir = Path(output)

                def ensure_base_dirs(self):
                    pass

                def __getattr__(self, name):
                    return getattr(original_layout, name)

            with patch.object(audit, 'build_layout', return_value=IsolatedLayout()), patch.object(sys, 'argv', ['lineage', '--article-root', str(ARTICLE_ROOT)]):
                audit.main()
            payload = json.loads((Path(output) / 'article_figure_lineage_audit_20260516/summary.json').read_text(encoding='utf-8'))
            with (Path(output) / 'article_figure_lineage_audit_20260516/figure_lineage_status.csv').open(newline='') as handle:
                statuses = {row['figure_path']: row for row in csv.DictReader(handle)}
        self.assertTrue(payload['setup_support_full_history_all_cutoffs'])
        self.assertTrue(payload['setup_support_gdpc_all_cutoffs'])
        self.assertTrue(payload['lowercase_compatibility_tree_empty'])
        manifest = json.loads((ARTICLE_ROOT / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text())
        setup_labels = {'fig:sanlorenzo', 'fig:covariates', 'fig:retrospectives', 'fig:ensembles'}
        setup_figures = [row for row in manifest['figures'] if row['label'] in setup_labels]
        self.assertEqual(len(setup_figures), 4)
        for row in setup_figures:
            self.assertEqual(statuses[row['manuscript_path']]['status'], 'updated_now')
            self.assertEqual(statuses[row['manuscript_path']]['source_lineage'], 'corrected_setup_support_v2_20260516')


if __name__ == '__main__':
    unittest.main()
