from __future__ import annotations

import json
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = ROOT / "Evironmetrics---REVISED-DOC-Corrected-2"
CORRECTIONS_ROOT = Path("/data/muscat_data/jaguir26/Corrections---Project-1")
os.sys.path.insert(0, str(ROOT / "scripts"))

from latest_forecast_issue_contract import (  # noqa: E402
    ARTICLE_LATEST_FORECAST_ISSUE_DOC_REL,
    FORBIDDEN_LATEST_FORECAST_ARTICLE_CLAIMS,
    LATEST_FORECAST_ISSUE_CONTRACT_REL,
    LATEST_FORECAST_ISSUE_MANIFEST_REL,
    REQUIRED_LATEST_FORECAST_ARTICLE_CLAIMS,
    REQUIRED_LATEST_FORECAST_CORRECTIONS_CLAIMS,
    check_latest_forecast_issue_manifest,
)


class HE7LatestForecastIssueContractTests(unittest.TestCase):
    def test_manifest_records_latest_only_contract(self) -> None:
        manifest_path = ARTICLE_ROOT / LATEST_FORECAST_ISSUE_MANIFEST_REL
        self.assertTrue(manifest_path.exists(), f"missing latest-forecast manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        failed = [row for row in check_latest_forecast_issue_manifest(manifest) if not row.ok]
        self.assertFalse(failed, [f"{row.item}: {row.detail}" for row in failed])

    def test_docs_exist(self) -> None:
        self.assertTrue((ROOT / LATEST_FORECAST_ISSUE_CONTRACT_REL).exists())
        self.assertTrue((ARTICLE_ROOT / ARTICLE_LATEST_FORECAST_ISSUE_DOC_REL).exists())

    def test_article_and_corrections_share_latest_only_claims(self) -> None:
        article = (ARTICLE_ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        corrections = (CORRECTIONS_ROOT / "main.tex").read_text(encoding="utf-8")
        for claim in REQUIRED_LATEST_FORECAST_ARTICLE_CLAIMS:
            self.assertIn(claim, article)
        for claim in REQUIRED_LATEST_FORECAST_CORRECTIONS_CLAIMS:
            self.assertIn(claim, corrections)
        for claim in FORBIDDEN_LATEST_FORECAST_ARTICLE_CLAIMS:
            self.assertNotIn(claim, article)

    def test_future_bundle_writers_record_alias_policy(self) -> None:
        source_files = [
            ROOT / "R" / "unified" / "stages" / "stage_forecats.R",
            ROOT / "scripts" / "forecats_batch.R",
            ROOT / "scripts" / "build_multimodel_v8_histfix_bundles.py",
        ]
        for path in source_files:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                self.assertIn("forecast_issue_policy", text)
                self.assertIn("latest_forecast_only", text)
                self.assertIn("legacy_weighted_daily_filenames_are_aliases", text)


if __name__ == "__main__":
    unittest.main()
