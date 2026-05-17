from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPERS = ROOT / 'R' / 'environmetrics' / '02_helpers_core.R'


class UnivarPostQuantileSynthesisFallbackTests(unittest.TestCase):
    def test_helper_uses_export_compatible_quantile_synthesis_fallback(self) -> None:
        text = HELPERS.read_text(encoding='utf-8')
        self.assertIn('getNamespaceExports("exdqlm")', text)
        self.assertIn('"exdqlm_synthesize_from_draws"', text)
        self.assertIn('"quantileSynthesis"', text)
        self.assertIn('package \'exdqlm\' does not export a quantile synthesis entrypoint', text)


if __name__ == '__main__':
    unittest.main()
