"""Exercise active presentation-table validation without altering result bundles."""
from pathlib import Path
import json
import importlib.util
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from article_repository_binding import active_article_root
from current_article_contract import active_table_path, canonical_method_label
from validate_publication_freeze import parse_flat_tex
from validate_revision_cross_repo_wiring import parse_flat_table, parse_panel_table

ARTICLE = active_article_root(ROOT)
SPEC = importlib.util.spec_from_file_location('editorial_release_checks',
    ROOT / 'docs/article_editorial_revision_20261109/run_checks.py')
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)


class BaselinePreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.main = self.root / 'wileyNJD-APA.tex'
        self.data = self.root / 'scientific-results.txt'
        self.main.write_text('Original text')
        self.data.write_text('Original numerical evidence')
        self.baseline = {'article_commit': 'pinned', 'files': {
            p.name: {'mode': '100644', 'blob': RELEASE.blob(p)}
            for p in (self.main, self.data)}}

    def test_approved_text_edit_is_allowed_but_changes_snapshot_identity(self):
        before = RELEASE.preservation(self.root, self.baseline)
        self.main.write_text('Revised exposition')
        after = RELEASE.preservation(self.root, self.baseline)
        self.assertTrue(before['passed'])
        self.assertTrue(after['passed'])
        self.assertNotEqual(before['current_baseline_content_sha256'],
                            after['current_baseline_content_sha256'])
        self.assertEqual(after['changed_existing_files'], ['wileyNJD-APA.tex'])

    def test_unapproved_result_change_and_missing_file_fail_closed(self):
        self.data.write_text('Changed numerical evidence')
        self.assertFalse(RELEASE.preservation(self.root, self.baseline)['passed'])
        self.data.unlink()
        result = RELEASE.preservation(self.root, self.baseline)
        self.assertFalse(result['passed'])
        self.assertEqual(result['missing'], ['scientific-results.txt'])

    def test_mode_change_fails_even_if_content_unchanged(self):
        self.data.chmod(0o755)
        result = RELEASE.preservation(self.root, self.baseline)
        self.assertFalse(result['passed'])
        self.assertEqual(result['changed_modes'], ['scientific-results.txt'])


class EditorialWiringTests(unittest.TestCase):
    def test_reader_names_resolve_only_declared_reference_identities(self):
        for display, identity in {
            'GloFAS': 'RAW-GLOFAS', 'NWS': 'RAW-NWS',
            'Seasonal climatology': 'CLIM-SEASONAL',
            'Persistence': 'PERSISTENCE', 'GloFAS EMOS': 'EMOS-GLOFAS',
        }.items():
            self.assertEqual(canonical_method_label(display), identity)
            self.assertEqual(canonical_method_label(identity), identity)
        self.assertEqual(canonical_method_label('unrecognized method'), 'unrecognized method')

    def test_both_validators_read_unchanged_numbers_from_active_flat_tables(self):
        for label, filename in (
            ('tab:benchmark_crps_models', 'benchmark_crps_main_table.tex'),
            ('tab:benchmark_crps_models_nws_horizon', 'benchmark_crps_nws_horizon_table.tex'),
            ('tab:he3_ablation_crps', 'he3_ablation_crps_main_table.tex'),
            ('tab:he3_ablation_crps_nws_horizon', 'he3_ablation_crps_nws_horizon_table.tex'),
        ):
            active = active_table_path(ARTICLE, label)
            historical = ARTICLE / 'tables/generated_tex' / filename
            self.assertEqual(active.parent.name, 'editorial_revision')
            self.assertTrue(parse_flat_tex(active))
            self.assertEqual(parse_flat_tex(active), parse_flat_tex(historical))
            self.assertEqual(parse_flat_table(active, 5), parse_flat_table(historical, 5))

    def test_origin_heading_change_preserves_all_quantile_panel_values(self):
        active = active_table_path(ARTICLE, 'tab:he4_quantile_check_loss')
        historical = ARTICLE / 'tables/generated_tex/he4_quantile_check_loss_main_table.tex'
        self.assertEqual(len(parse_panel_table(active, 7)), 20)
        self.assertEqual(parse_panel_table(active, 7), parse_panel_table(historical, 7))

    def test_unused_old_table_cannot_satisfy_active_manifest_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'active.tex').write_text('A & 0.10 & 0.20 & 0.30 & 0.40 & 0.50 \\\\\n')
            (root / 'unused.tex').write_text('A & 0.90 & 0.20 & 0.30 & 0.40 & 0.50 \\\\\n')
            (root / 'wileyNJD-APA.tex').write_text(r'\input{active.tex}')
            manifest = {'tables': {'tab:test': {'table_tex_path': 'unused.tex'}}}
            (root / 'MANUSCRIPT_ASSET_MANIFEST.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'not an active manuscript dependency'):
                active_table_path(root, 'tab:test')
            manifest['tables']['tab:test']['table_tex_path'] = 'active.tex'
            (root / 'MANUSCRIPT_ASSET_MANIFEST.json').write_text(json.dumps(manifest))
            selected = active_table_path(root, 'tab:test')
            expected = {'A': [0.10, 0.20, 0.30, 0.40, 0.50]}
            self.assertEqual(parse_flat_tex(selected), expected)
            selected.write_text('A & 0.11 & 0.20 & 0.30 & 0.40 & 0.50 \\\\\n')
            self.assertNotEqual(parse_flat_tex(selected), expected)
            self.assertNotEqual(parse_flat_table(selected, 5), expected)


if __name__ == '__main__':
    unittest.main()
