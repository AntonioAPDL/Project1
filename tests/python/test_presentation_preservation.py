"""Ensure typography changes cannot silently substitute mathematical values."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('presentation_preservation',
    ROOT / 'docs/article_presentation_revision_20261109/check_preservation.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PresentationPreservationTests(unittest.TestCase):
    def test_bold_unwrap_preserves_nested_scientific_notation(self):
        before = r'\begin{tabular}{lrr} A & $1.20\times10^{12}$ & --- \\ \end{tabular}'
        after = r'\begin{tabular}{lrr} A & \textbf{$1.20\times10^{12}$} & --- \\ \end{tabular}'
        self.assertEqual(MODULE.tabular(before), MODULE.tabular(after))

    def test_changed_number_or_missing_entry_remains_detectable(self):
        original = r'\begin{tabular}{lrr} A & 1.20 & --- \\ \end{tabular}'
        for changed in (original.replace('1.20', r'\textbf{1.21}'), original.replace('---', '0.00')):
            with self.subTest(changed=changed):
                self.assertNotEqual(MODULE.tabular(original), MODULE.tabular(changed))

    def test_starred_coefficient_table_keeps_estimates_and_intervals(self):
        source = r'\begin{tabular*}{\textwidth}{lr} \textbf{Mean} & $[-0.10,0.20]$ \\ \end{tabular*}'
        self.assertIn('$[-0.10,0.20]$', MODULE.tabular(source))
        self.assertNotEqual(MODULE.tabular(source), MODULE.tabular(source.replace('0.20', '0.21')))

    def test_row_deletion_and_duplication_cannot_pass(self):
        original = r'\begin{tabular}{lr} A & 1 \\ B & 2 \\ \end{tabular}'
        for changed in (original.replace(r'B & 2 \\', ''), original.replace(r'B & 2 \\', r'B & 2 \\ B & 2 \\')):
            self.assertNotEqual(MODULE.tabular(original), MODULE.tabular(changed))

    def test_unbalanced_bold_or_duplicate_blocks_fail(self):
        with self.assertRaisesRegex(ValueError, 'Unbalanced'):
            MODULE.strip_bold(r'\textbf{1.2')
        block = r'\begin{tabular}{r} 1 \end{tabular}'
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            MODULE.tabular(block + block)

    def test_math_reformatting_is_allowed_but_changed_value_is_not(self):
        old = r'\[q=(J+1)\cdot p+m+1\]'
        spacing = r'\[q = (J+1) \cdot p + m + 1\label{eq:q}\]'
        self.assertTrue(MODULE.PARSER.compare_math(old, spacing)['passed'])
        self.assertFalse(MODULE.PARSER.compare_math(old, spacing.replace('m + 1', 'm + 2'))['passed'])


if __name__ == '__main__':
    unittest.main()
