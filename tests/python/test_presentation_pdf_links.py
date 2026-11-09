"""Current numbering, caption pages and visible exhibit context stay consistent."""
import copy
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'presentation_pdf_links', ROOT / 'docs/article_presentation_revision_20261109/check_pdf_links.py')
assert SPEC and SPEC.loader
LINKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINKS)

SOURCE = r'''
\section{Results}
\label{tab:main}
\begin{appendix}
\section{Data}\label{fig:context}
\section{Additional results}
\label{tab:origins}\label{tab:components}\label{tab:quantiles}
\label{fig:early}\label{fig:late}
\end{appendix}
'''
INVENTORY = {'submitted_assets': [
    {'label': label, 'kind': kind, 'scope': scope}
    for label, kind, scope in (
        ('tab:main', 'table', 'main'), ('fig:context', 'figure', 'appendix'),
        ('tab:origins', 'table', 'appendix'), ('tab:components', 'table', 'appendix'),
        ('tab:quantiles', 'table', 'appendix'), ('fig:early', 'figure', 'appendix'),
        ('fig:late', 'figure', 'appendix'))]}
EXPECTED = LINKS.expected_exhibits(INVENTORY, SOURCE)
LABELS = {label: {'page': page} for label, page in (
    ('tab:main', 8), ('fig:context', 12), ('tab:origins', 15),
    ('tab:components', 16), ('tab:quantiles', 17), ('fig:early', 21), ('fig:late', 22))}
XML = '''<pdf2xml><page number="8">
<text>Table <a href="proof.html#8">1</a> gives aggregates.</text>
<text>Tables <a href="proof.html#15">B1</a>, <a href="proof.html#16">B2</a> and <a href="proof.html#17">B3</a> give details.</text>
<text>Figures <a href="proof.html#21">B1</a> and <a href="proof.html#22">B2</a> show the remaining origins.</text>
</page><page number="11"><text>Figure <a href="proof.html#12">A1</a> shows the data.</text></page>
<page number="12"><text>FIGURE A1</text></page>
<page number="15"><text>TABLE B1</text></page>
<page number="16"><text>TABLE B2</text></page>
<page number="17"><text>TABLE B3</text></page>
<page number="21"><text>FIGURE B1</text></page>
<page number="22"><text>FIGURE B2</text></page></pdf2xml>'''


def context_checks(xml=XML, expected=EXPECTED, labels=LABELS):
    return LINKS.contextual_checks(ET.fromstring(xml).findall('page'), labels, expected, set(range(1, 11)))


class PresentationPdfLinkTests(unittest.TestCase):
    def test_new_numbering_follows_reachable_source_not_inventory_order(self):
        self.assertEqual(EXPECTED['tab:quantiles']['number'], 'B3')
        self.assertEqual(EXPECTED['fig:early']['number'], 'B1')
        self.assertEqual(EXPECTED['fig:context']['number'], 'A1')
        inventory = copy.deepcopy(INVENTORY)
        inventory['submitted_assets'].reverse()
        self.assertEqual(LINKS.expected_exhibits(inventory, SOURCE), EXPECTED)

    def test_missing_retained_table_definition_fails(self):
        with self.assertRaisesRegex(ValueError, 'tab:quantiles'):
            LINKS.expected_exhibits(INVENTORY, SOURCE.replace(r'\label{tab:quantiles}', ''))

    def test_duplicate_definition_and_scope_mismatch_fail(self):
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            LINKS.expected_exhibits(INVENTORY, SOURCE + r'\label{tab:quantiles}')
        inventory = copy.deepcopy(INVENTORY)
        inventory['submitted_assets'][0]['scope'] = 'appendix'
        with self.assertRaisesRegex(ValueError, 'scope mismatch'):
            LINKS.expected_exhibits(inventory, SOURCE)

    def test_correct_colliding_numbers_and_renumbered_b3_are_accepted(self):
        checks = context_checks()
        self.assertTrue(all(check['passed'] for check in checks), checks)
        quantile_check = next(check for check in checks if check['check'].endswith('tab:quantiles'))
        self.assertEqual(quantile_check['details']['main_links'][0]['number'], 'B3')

    def test_figure_link_cannot_satisfy_a_missing_table_reference(self):
        xml = XML.replace('<a href="proof.html#15">B1</a>, ', '')
        failures = [check['check'] for check in context_checks(xml) if not check['passed']]
        self.assertEqual(failures, ['exhibit_links:tab:origins'])

    def test_wrong_table_and_figure_destinations_fail(self):
        xml = XML.replace('#15', '#TEMP').replace('#21', '#15').replace('#TEMP', '#21')
        failures = {check['check'] for check in context_checks(xml) if not check['passed']}
        self.assertEqual(failures, {'exhibit_links:tab:origins', 'exhibit_links:fig:early'})

    def test_ambiguous_reference_fails_without_destination_guessing(self):
        xml = XML.replace('Tables ', 'See ')
        checks = context_checks(xml)
        ambiguous = [check for check in checks if isinstance(check['details'], dict) and check['details'].get('ambiguous_links')]
        self.assertTrue(ambiguous)
        self.assertTrue(all(not check['passed'] for check in ambiguous))

    def test_stale_removed_label_reference_or_display_fails(self):
        for source, labels, text in (
            (r'\ref{tab:fitting_status}', {}, ''),
            ('', {'app:fitdiagnostics': {}}, ''),
            ('', {}, 'Recorded stopping classifications for the comparison fits.'),
        ):
            with self.subTest(source=source, labels=labels, text=text):
                self.assertTrue(any(not check['passed'] for check in
                                    LINKS.removed_content_checks(source, labels, text)))
        self.assertTrue(all(check['passed'] for check in LINKS.removed_content_checks(
            r'\label{tab:quantile_check_loss}', {}, 'TABLE B3: Mean quantile check loss.')))

    def test_obsolete_number_cannot_pass_as_known_reference(self):
        checks = context_checks(XML.replace('B3</a>', 'B8</a>'))
        failures = {check['check'] for check in checks if not check['passed']}
        self.assertIn('exhibit_links:tab:quantiles', failures)
        self.assertIn('no_unknown_exhibit_references', failures)

    def test_caption_page_disagrees_with_aux_and_link_target(self):
        expected = {'tab:quantiles': EXPECTED['tab:quantiles']}
        labels = {'tab:quantiles': {'page': 16}}
        xml = '<pdf2xml><page number="17"><text>TABLE B3</text></page></pdf2xml>'
        checks = LINKS.caption_checks(ET.fromstring(xml).findall('page'), labels, expected)
        self.assertFalse(checks[0]['passed'])
        self.assertEqual(checks[0]['details']['caption_pages'], [17])

    def test_inline_formats_and_hyperlinked_type_keep_visible_context(self):
        xml = XML.replace('Figures <a href="proof.html#21">B1</a>',
                          '<b>Figures</b> <a href="proof.html#21"><i>B1</i></a>')
        xml = xml.replace('Table <a href="proof.html#8">1</a>',
                          '<a href="proof.html#8">Table 1</a>')
        self.assertTrue(all(check['passed'] for check in context_checks(xml)))


    def test_wrapped_coordinated_tables_and_figures_keep_visible_type(self):
        xml = '''<pdf2xml><page number="9">
        <text top="100" left="67" height="13">Results appear in Tables <a href="p.html#18">B4</a></text>
        <text top="120" left="67" height="13">and <a href="p.html#19">B5</a> distinguish the scores.</text>
        <text top="160" left="67" height="13">Figures <a href="p.html#21">B1</a></text>
        <text top="180" left="67" height="13">and <a href="p.html#22">B2</a> use the same scale.</text>
        </page></pdf2xml>'''
        pages = ET.fromstring(xml).findall('page')
        links = LINKS.contextual_links(pages, {9})
        self.assertEqual([(link['kind'], link['number']) for link in links],
                         [('table', 'B4'), ('table', 'B5'), ('figure', 'B1'), ('figure', 'B2')])
        self.assertIn('Tables', links[1]['continued_from'])
        self.assertIn('Figures', links[3]['continued_from'])
        expected = {'table:4': {'kind': 'table', 'number': 'B4', 'scope': 'appendix'},
                    'table:5': {'kind': 'table', 'number': 'B5', 'scope': 'appendix'},
                    'figure:1': {'kind': 'figure', 'number': 'B1', 'scope': 'appendix'},
                    'figure:2': {'kind': 'figure', 'number': 'B2', 'scope': 'appendix'}}
        labels = {key: {'page': page} for key, page in zip(expected, (18, 19, 21, 22))}
        self.assertTrue(all(check['passed'] for check in
                            LINKS.contextual_checks(pages, labels, expected, {9})))
        wrong_pages = ET.fromstring(xml.replace('#19', '#18')).findall('page')
        failures = [check['check'] for check in
                    LINKS.contextual_checks(wrong_pages, labels, expected, {9}) if not check['passed']]
        self.assertEqual(failures, ['exhibit_links:table:5'])

    def test_unrelated_prose_and_sentence_boundary_prevent_type_inheritance(self):
        cases = (
            '<text top="120" left="67" height="13">Other results are descriptive.</text>'
            '<text top="140" left="67" height="13">and <a href="p.html#19">B5</a> appears here.</text>',
            '<text top="120" left="67" height="13">and other results appear in <a href="p.html#19">B5</a>.</text>',
            '<text top="120" left="67" height="13">See <a href="p.html#19">B5</a>.</text>',
        )
        for continuation in cases:
            with self.subTest(continuation=continuation):
                xml = '<pdf2xml><page number="9"><text top="100" left="67" height="13">Tables '
                xml += '<a href="p.html#18">B4</a></text>' + continuation + '</page></pdf2xml>'
                links = LINKS.contextual_links(ET.fromstring(xml).findall('page'), {9})
                self.assertIsNone(links[-1]['kind'])
        xml = '''<pdf2xml><page number="9">
        <text top="100" left="67" height="13">Tables <a href="p.html#18">B4</a>.</text>
        <text top="120" left="67" height="13">and <a href="p.html#19">B5</a> appears here.</text>
        </page></pdf2xml>'''
        self.assertIsNone(LINKS.contextual_links(ET.fromstring(xml).findall('page'), {9})[-1]['kind'])

    def test_wrapped_reference_cannot_inherit_across_pages_columns_or_large_gap(self):
        previous = '<text top="100" left="67" height="13">Tables <a href="p.html#18">B4</a></text>'
        for top, left in ((160, 67), (120, 300), (90, 67)):
            with self.subTest(top=top, left=left):
                xml = '<pdf2xml><page number="9">' + previous
                xml += f'<text top="{top}" left="{left}" height="13">and <a href="p.html#19">B5</a>.</text>'
                xml += '</page></pdf2xml>'
                self.assertIsNone(LINKS.contextual_links(ET.fromstring(xml).findall('page'), {9})[-1]['kind'])
        xml = '<pdf2xml><page number="9">' + previous + '</page><page number="10">'
        xml += '<text top="120" left="67" height="13">and <a href="p.html#19">B5</a>.</text></page></pdf2xml>'
        self.assertIsNone(LINKS.contextual_links(ET.fromstring(xml).findall('page'), {9, 10})[-1]['kind'])


if __name__ == '__main__':
    unittest.main()
