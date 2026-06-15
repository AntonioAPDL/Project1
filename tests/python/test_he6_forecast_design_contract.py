from __future__ import annotations

import json
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = ROOT / "Evironmetrics---REVISED-DOC-Corrected-2"
CORRECTIONS_ROOT = Path("/data/muscat_data/jaguir26/Corrections---Project-1")
os.sys.path.insert(0, str(ROOT / "scripts"))

from forecast_design_contract import (  # noqa: E402
    ARTICLE_FORECAST_DESIGN_DOC_REL,
    FORBIDDEN_FORECAST_DESIGN_CLAIMS,
    FORECAST_DESIGN_CONTRACT_REL,
    FORECAST_DESIGN_MANIFEST_REL,
    REQUIRED_FORECAST_DESIGN_ARTICLE_CLAIMS,
    REQUIRED_FORECAST_DESIGN_CORRECTIONS_CLAIMS,
    check_forecast_design_manifest,
)


class HE6ForecastDesignContractTests(unittest.TestCase):
    def test_manifest_records_out_of_sample_contract(self) -> None:
        manifest_path = ARTICLE_ROOT / FORECAST_DESIGN_MANIFEST_REL
        self.assertTrue(manifest_path.exists(), f"missing forecast-design manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checks = check_forecast_design_manifest(manifest)
        failed = [row for row in checks if not row.ok]
        self.assertFalse(failed, [f"{row.item}: {row.detail}" for row in failed])

    def test_docs_exist(self) -> None:
        self.assertTrue((ROOT / FORECAST_DESIGN_CONTRACT_REL).exists())
        self.assertTrue((ARTICLE_ROOT / ARTICLE_FORECAST_DESIGN_DOC_REL).exists())

    def test_article_and_corrections_share_forecast_design_claims(self) -> None:
        article = (ARTICLE_ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        corrections = (CORRECTIONS_ROOT / "main.tex").read_text(encoding="utf-8")
        for claim in REQUIRED_FORECAST_DESIGN_ARTICLE_CLAIMS:
            self.assertIn(claim, article)
        for claim in REQUIRED_FORECAST_DESIGN_CORRECTIONS_CLAIMS:
            self.assertIn(claim, corrections)
        for claim in FORBIDDEN_FORECAST_DESIGN_CLAIMS:
            self.assertNotIn(claim, article)
            self.assertNotIn(claim, corrections)


if __name__ == "__main__":
    unittest.main()
