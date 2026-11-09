"""Distinguish compiled table and figure links sharing appendix numbers."""
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'foundation_pdf_links', ROOT / 'docs/article_foundation_revision_20261109/check_pdf_links.py')
assert SPEC and SPEC.loader
LINKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINKS)

LABELS = {label: {'page': page} for label, page in (
    ('tab:crps_all_origins', 15), ('tab:component_comparison', 16),
    ('fig:forecast_origins_2021_early', 22), ('fig:forecast_origins_2021_2022', 23))}
XML = '''<pdf2xml><page number="8">
<text>Figures <a href="proof.html#22">B1 </a>and <a href="proof.html#23">B2 </a>use the same conventions.</text>
<text>Raw NWS has eight leads. Table <a href="proof.html#15">B1</a> gives the results.</text>
</page><page number="10">
<text>Both horizons (Table <a href="proof.html#16">B2). </a>However, other comparisons remain relevant.</text>
</page></pdf2xml>'''


def checks(source=XML):
    return LINKS.contextual_checks(ET.fromstring(source).findall('page'), LABELS, set(range(1, 12)))


class FoundationPdfLinkTests(unittest.TestCase):
    def test_correct_colliding_numbers_use_visible_exhibit_types(self):
        observed = checks()
        self.assertEqual(len(observed), 4)
        self.assertTrue(all(check['passed'] for check in observed))
        for check in observed:
            self.assertEqual(len(check['details']['links']), 1)
            self.assertEqual(check['details']['ambiguous_links'], [])

    def test_swapped_figure_and_table_targets_fail_despite_valid_page_numbers(self):
        source = XML.replace('#22', '#TEMP').replace('#15', '#22').replace('#TEMP', '#15')
        failures = {check['check'] for check in checks(source) if not check['passed']}
        self.assertEqual(failures, {'main_table_link:tab:crps_all_origins',
                                    'main_figure_link:fig:forecast_origins_2021_early'})

    def test_figure_link_cannot_satisfy_a_missing_table_reference(self):
        root = ET.fromstring(XML)
        page = root.find('page')
        page.remove(page.findall('text')[1])
        observed = LINKS.contextual_checks(root.findall('page'), LABELS, set(range(1, 12)))
        failed = [check for check in observed if not check['passed']]
        self.assertEqual([check['check'] for check in failed], ['main_table_link:tab:crps_all_origins'])
        self.assertEqual(failed[0]['details']['links'], [])

    def test_ambiguous_visible_prefix_fails_instead_of_using_destination_to_guess(self):
        for prefix in ('See ', 'Figures illustrate the method; see '):
            with self.subTest(prefix=prefix):
                source = XML.replace('Raw NWS has eight leads. Table ', prefix)
                observed = checks(source)
                ambiguous = [check for check in observed if check['details']['ambiguous_links']]
                self.assertEqual(len(ambiguous), 2)
                self.assertTrue(all(not check['passed'] for check in ambiguous))

    def test_inline_formatting_and_hyperlinked_type_preserve_context(self):
        source = XML.replace('Figures <a href="proof.html#22">B1 </a>',
                             '<b>Figures</b> <a href="proof.html#22"><i>B1</i> </a>')
        source = source.replace('Table <a href="proof.html#15">B1</a>',
                                '<a href="proof.html#15">Table B1</a>')
        self.assertTrue(all(check['passed'] for check in checks(source)))


if __name__ == '__main__':
    unittest.main()
