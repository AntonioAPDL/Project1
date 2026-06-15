from __future__ import annotations

import json
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = ROOT / "Evironmetrics---REVISED-DOC-Corrected-2"
CORRECTIONS_ROOT = Path("/data/muscat_data/jaguir26/Corrections---Project-1")
os.sys.path.insert(0, str(ROOT / "scripts"))

from runtime_feasibility_contract import (  # noqa: E402
    ARTICLE_RUNTIME_DOC_REL,
    FORBIDDEN_RUNTIME_DECOMPOSITION_CLAIMS,
    REQUIRED_RUNTIME_ARTICLE_CLAIMS,
    REQUIRED_RUNTIME_CORRECTIONS_CLAIMS,
    RUNTIME_CONTRACT_REL,
    RUNTIME_MANIFEST_REL,
    check_runtime_manifest,
)


class HE1RuntimeContractTests(unittest.TestCase):
    def test_runtime_manifest_records_conservative_contract(self) -> None:
        manifest_path = ARTICLE_ROOT / RUNTIME_MANIFEST_REL
        self.assertTrue(manifest_path.exists(), f"missing runtime manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checks = check_runtime_manifest(manifest)
        failed = [row for row in checks if not row.ok]
        self.assertFalse(failed, [f"{row.item}: {row.detail}" for row in failed])
        self.assertFalse(manifest["claims_policy"]["report_fit_forecast_decomposition"])

    def test_runtime_docs_exist(self) -> None:
        self.assertTrue((ROOT / RUNTIME_CONTRACT_REL).exists())
        self.assertTrue((ARTICLE_ROOT / ARTICLE_RUNTIME_DOC_REL).exists())

    def test_article_and_corrections_share_runtime_claims(self) -> None:
        article = (ARTICLE_ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        corrections = (CORRECTIONS_ROOT / "main.tex").read_text(encoding="utf-8")
        for claim in REQUIRED_RUNTIME_ARTICLE_CLAIMS:
            self.assertIn(claim, article)
        for claim in REQUIRED_RUNTIME_CORRECTIONS_CLAIMS:
            self.assertIn(claim, corrections)
        for claim in FORBIDDEN_RUNTIME_DECOMPOSITION_CLAIMS:
            self.assertNotIn(claim, article)
            self.assertNotIn(claim, corrections)


if __name__ == "__main__":
    unittest.main()
