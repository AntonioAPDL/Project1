"""Exercise explicit mathematical approval and numerical-table preservation."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'foundation_math_preservation',
    ROOT / 'docs/article_foundation_revision_20261109/check_math_preservation.py')
assert SPEC and SPEC.loader
PRESERVATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRESERVATION)


def table_rows():
    rows = ['Method & 28-day CRPS & 28-day CRPSS & 8-day CRPS & 8-day CRPSS \\\\']
    rows += [f'Method{i} & 0.{i:05d} & -0.20000 & 0.30000 & 0.40000 \\\\'
             for i in range(13)]
    rows.append('NWS & --- & --- & 0.66478 & 0.10000 \\\\')
    return rows


class FoundationPreservationTests(unittest.TestCase):
    def test_reviewed_replacement_and_insertion_preserve_other_expressions(self):
        before = ['$a$', '$q=3(7)$', '$c$', '$d$']
        review = {
            'baseline_sha256': PRESERVATION.fingerprint(before),
            'changes': [
                {'start': 1, 'stop': 2, 'before': ['$q=3(7)$'],
                 'after': [r'$q=3\cdot7$'], 'reason': 'Explicit multiplication'},
                {'start': 3, 'stop': 3, 'before': [],
                 'after': ['$e$', '$f$'], 'reason': 'Reviewed score identity'},
            ],
        }
        self.assertEqual(PRESERVATION.expected_expressions(before, review),
                         ['$a$', r'$q=3\cdot7$', '$c$', '$e$', '$f$', '$d$'])
        self.assertEqual(before, ['$a$', '$q=3(7)$', '$c$', '$d$'])

    def test_full_check_rejects_an_unreviewed_change_outside_an_approved_replacement(self):
        before_main = (r'\maketitle $a$ $b$ \begin{appendix}'
                       r'\input{appendices}\end{appendix}\bibliography{refs}')
        before_appendix = r'Appendix $z$'
        before_table = '\n'.join(table_rows())
        historical = {'wileyNJD-APA.tex': before_main,
                      'appendices.tex': before_appendix,
                      'tables/compact_publication/main_aggregate.tex': before_table}
        main_expressions = PRESERVATION.PARSER.expressions(
            PRESERVATION.PARSER.body(before_main, integrated=True))
        appendix_expressions = PRESERVATION.PARSER.expressions(before_appendix)
        review = {
            'baseline_commit': 'reviewed-baseline',
            'main': {'baseline_sha256': PRESERVATION.fingerprint(main_expressions),
                     'changes': [{'start': 0, 'stop': 1, 'before': ['$a$'],
                                  'after': ['$a+1$'], 'reason': 'Approved identity'}]},
            'appendix': {'baseline_sha256': PRESERVATION.fingerprint(appendix_expressions),
                         'changes': []},
        }
        with tempfile.TemporaryDirectory(prefix='foundation_preservation_') as directory:
            temporary = Path(directory)
            article = temporary / 'article'
            documents = temporary / 'review'
            documents.mkdir()
            for relative, content in historical.items():
                target = article / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            (documents / 'baseline.json').write_text(json.dumps({'article_commit': 'reviewed-baseline'}))
            (documents / 'approved_math_changes.json').write_text(json.dumps(review))
            current_main = before_main.replace('$a$', '$a+1$')
            (article / 'wileyNJD-APA.tex').write_text(current_main)
            with patch.object(PRESERVATION, 'HERE', documents), patch.object(
                    PRESERVATION.subprocess, 'check_output',
                    side_effect=lambda args, **kwargs: historical[args[-1].split(':', 1)[1]]):
                self.assertTrue(PRESERVATION.check(article)['passed'])
                (article / 'wileyNJD-APA.tex').write_text(current_main.replace('$b$', '$b+1$'))
                result = PRESERVATION.check(article)
                self.assertFalse(result['passed'])
                self.assertFalse(result['mathematics']['main']['passed'])
                self.assertTrue(result['mathematics']['appendix']['passed'])

    def test_incorrect_baseline_and_overlapping_or_misidentified_positions_fail(self):
        before = ['$a$', '$b$', '$c$']
        valid = {'start': 0, 'stop': 2, 'before': before[:2],
                 'after': ['$d$'], 'reason': 'Reviewed replacement'}
        for name, review in (
            ('baseline hash', {'baseline_sha256': 'wrong', 'changes': []}),
            ('overlap', {'baseline_sha256': PRESERVATION.fingerprint(before),
                         'changes': [valid, {'start': 1, 'stop': 2, 'before': ['$b$'],
                                            'after': [], 'reason': 'Overlapping deletion'}]}),
            ('wrong before', {'baseline_sha256': PRESERVATION.fingerprint(before),
                              'changes': [{**valid, 'before': ['$different$']}]}),
            ('missing reason', {'baseline_sha256': PRESERVATION.fingerprint(before),
                                'changes': [{**valid, 'reason': ''}]}),
        ):
            with self.subTest(case=name), self.assertRaises(ValueError):
                PRESERVATION.expected_expressions(before, review)

    def test_bold_formatting_preserves_numbers_and_missing_cells(self):
        plain = '\n'.join(table_rows())
        styled = plain.replace('0.00001', r'\textbf{0.00001}').replace(
            '-0.20000', r'\textbf{-0.20000}')
        self.assertEqual(PRESERVATION.numerical_rows(plain), PRESERVATION.numerical_rows(styled))
        self.assertEqual(PRESERVATION.numerical_rows(styled)['NWS'][:2], ['---', '---'])
        self.assertNotEqual(PRESERVATION.numerical_rows(plain),
                            PRESERVATION.numerical_rows(styled.replace('0.66478', '0.66479')))

    def test_missing_or_duplicate_methods_cannot_pass_the_table_check(self):
        rows = table_rows()
        for name, source in (
            ('missing', '\n'.join(rows[:-1])),
            ('duplicate', '\n'.join(rows + [rows[1]])),
        ):
            with self.subTest(case=name), self.assertRaises(ValueError):
                PRESERVATION.numerical_rows(source)


if __name__ == '__main__':
    unittest.main()
