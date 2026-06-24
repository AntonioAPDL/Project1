#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from validate_publication_freeze import (  # noqa: E402
    HE3_LABEL_BY_VARIANT,
    HE3_VARIANTS,
    NON_PROMOTED_WORSE_REPAIRS,
    parse_flat_tex,
    same_display,
)


class PublicationFreezeValidationTests(unittest.TestCase):
    def test_he3_variant_labels_are_complete(self) -> None:
        self.assertEqual(set(HE3_LABEL_BY_VARIANT), set(HE3_VARIANTS))
        self.assertEqual(HE3_LABEL_BY_VARIANT["full"], "exAL-M-T1 (full)")
        self.assertEqual(HE3_LABEL_BY_VARIANT["noH3"], "exAL-M-T1-noH3")

    def test_non_promoted_worse_repair_set_is_locked(self) -> None:
        self.assertEqual(len(NON_PROMOTED_WORSE_REPAIRS), 8)
        self.assertIn(("20221225", "exAL-M-T0"), NON_PROMOTED_WORSE_REPAIRS)
        self.assertIn(("20210123", "exAL-U-T1"), NON_PROMOTED_WORSE_REPAIRS)

    def test_parse_flat_tex_handles_bold_numeric_cells(self) -> None:
        with tempfile.TemporaryDirectory(prefix="publication_freeze_tex_") as td:
            path = Path(td) / "table.tex"
            path.write_text(
                "\\begin{tabular}{lccccc}\n"
                "Ablation model & A & B & C & D & E \\\\\n"
                "exAL-M-T1 (full) & \\textbf{0.13971} & \\textbf{0.04724} & \\textbf{0.26045} & \\textbf{0.02273} & \\textbf{0.53806} \\\\\n"
                "exAL-M-T1-noH3 & 1.08281 & 1.03562 & 2.68667 & 0.72940 & 4.14478 \\\\\n"
                "\\end{tabular}\n",
                encoding="utf-8",
            )
            rows = parse_flat_tex(path)
        self.assertEqual(rows["exAL-M-T1 (full)"][0], 0.13971)
        self.assertEqual(rows["exAL-M-T1-noH3"][-1], 4.14478)

    def test_same_display_uses_five_decimal_rounding(self) -> None:
        self.assertTrue(same_display(0.1397088548478634, 0.13971))
        self.assertFalse(same_display(0.1397088548478634, 0.13980))


if __name__ == "__main__":
    unittest.main()
