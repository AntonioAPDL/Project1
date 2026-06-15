from __future__ import annotations

import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = ROOT / "Evironmetrics---REVISED-DOC-Corrected-2"
CORRECTIONS_ROOT = Path("/data/muscat_data/jaguir26/Corrections---Project-1")
os.sys.path.insert(0, str(ROOT / "scripts"))

from reviewer1_remaining_contracts import (  # noqa: E402
    ARTICLE_R1_REMAINING_DOC_REL,
    R1_REMAINING_CONTRACT_REL,
    REVIEWER1_REMAINING_SPECS,
    check_reviewer1_remaining_text,
)


class Reviewer1RemainingContractTests(unittest.TestCase):
    def test_docs_exist(self) -> None:
        self.assertTrue((ROOT / R1_REMAINING_CONTRACT_REL).exists())
        self.assertTrue((ARTICLE_ROOT / ARTICLE_R1_REMAINING_DOC_REL).exists())

    def test_all_remaining_item_ids_are_covered_once(self) -> None:
        expected = {
            "R1-M2",
            "R1-M3",
            "R1-M4",
            "R1-M5",
            "R1-m1",
            "R1-m2",
            "R1-m3",
            "R1-m4",
            "R1-m5",
            "R1-m6",
            "R1-m7",
            "R1-m8",
            "R1-m9",
        }
        observed = [spec.item_id for spec in REVIEWER1_REMAINING_SPECS]
        self.assertEqual(set(observed), expected)
        self.assertEqual(len(observed), len(expected))

    def test_article_generated_tables_and_corrections_preserve_remaining_contract(self) -> None:
        generated_tables = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ARTICLE_ROOT / "tables" / "generated_tex").glob("*.tex"))
        )
        article = (ARTICLE_ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8") + "\n" + generated_tables
        corrections = (CORRECTIONS_ROOT / "main.tex").read_text(encoding="utf-8")
        failed = [row for row in check_reviewer1_remaining_text(article, corrections) if not row.ok]
        self.assertFalse(failed, [f"{row.item}: {row.detail}" for row in failed])


if __name__ == "__main__":
    unittest.main()
