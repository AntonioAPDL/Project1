from __future__ import annotations

import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = ROOT / "Evironmetrics---REVISED-DOC-Corrected-2"
CORRECTIONS_ROOT = Path("/data/muscat_data/jaguir26/Corrections---Project-1")
os.sys.path.insert(0, str(ROOT / "scripts"))

from reviewer1_uncertainty_contract import (  # noqa: E402
    ARTICLE_R1_UNCERTAINTY_DOC_REL,
    R1_UNCERTAINTY_CONTRACT_REL,
    check_r1_uncertainty_text,
)


class R1M1UncertaintyContractTests(unittest.TestCase):
    def test_docs_exist(self) -> None:
        self.assertTrue((ROOT / R1_UNCERTAINTY_CONTRACT_REL).exists())
        self.assertTrue((ARTICLE_ROOT / ARTICLE_R1_UNCERTAINTY_DOC_REL).exists())

    def test_article_and_corrections_preserve_uncertainty_framing(self) -> None:
        article = (ARTICLE_ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        corrections = (CORRECTIONS_ROOT / "main.tex").read_text(encoding="utf-8")
        failed = [row for row in check_r1_uncertainty_text(article, corrections) if not row.ok]
        self.assertFalse(failed, [f"{row.item}: {row.detail}" for row in failed])


if __name__ == "__main__":
    unittest.main()
