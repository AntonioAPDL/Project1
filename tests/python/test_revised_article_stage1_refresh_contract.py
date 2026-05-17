from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = ROOT / 'Evironmetrics---REVISED-DOC-2'
os.sys.path.insert(0, str(ARTICLE_ROOT / 'scripts'))

from article_repo_layout import build_layout  # noqa: E402


class RevisedArticleStage1RefreshContractTests(unittest.TestCase):
    def test_article_layout_exposes_cutoff_wide_synthesis_dirs(self) -> None:
        layout = build_layout(ARTICLE_ROOT)
        self.assertEqual(layout.cutoff_multivariate_synthesis_dir.name, 'multivariate_synthesis_by_cutoff')
        self.assertEqual(layout.cutoff_reference_synthesis_dir.name, 'reference_synthesis_by_cutoff')
        self.assertEqual(layout.five_cutoff_main_model_synthesis_dir.name, 'five_cutoff_main_model_synthesis')
        self.assertEqual(layout.five_cutoff_reference_synthesis_dir.name, 'five_cutoff_reference_synthesis')
        self.assertEqual(layout.five_cutoff_synthesis_review_dir.name, 'five_cutoff_synthesis_review')

    def test_refresh_entrypoint_wires_cutoff_synthesis_refresh_and_corrected_runtime_roots(self) -> None:
        text = (ARTICLE_ROOT / 'scripts' / 'refresh_all_generated_assets.py').read_text(encoding='utf-8')
        self.assertIn('refresh_cutoff_synthesis_families.py', text)
        self.assertIn('multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516', text)
        self.assertIn('--univar-runtime-root', text)
        self.assertIn('--multivar-support-run-root', text)
        self.assertIn('historical_support_replay_20260517', text)
        self.assertIn('--strict-current-model-support', text)
        self.assertIn('historical_support_from_current_models', text)

    def test_manuscript_asset_manifest_points_selected_model_note_to_corrected_relaunch(self) -> None:
        payload = json.loads((ARTICLE_ROOT / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text(encoding='utf-8'))
        fig = next(item for item in payload['figures'] if item['label'] == 'fig:synth1')
        self.assertEqual(fig['source_path'], 'artifacts/representative_selected_model_2022_12_25/representative_synthesis_multivariate.png')
        self.assertIn('he2pubgdpc1r1', fig['note'])

    def test_figure_polish_audit_contract_references_cutoff_wide_synthesis_manifests(self) -> None:
        text = (ARTICLE_ROOT / 'scripts' / 'build_figure_polish_status_audit.py').read_text(encoding='utf-8')
        self.assertIn('figures/multivariate_synthesis_by_cutoff/manifest.csv', text)
        self.assertIn('figures/reference_synthesis_by_cutoff/manifest.csv', text)

    def test_historical_support_refresh_supports_retained_support_contract(self) -> None:
        text = (ARTICLE_ROOT / 'scripts' / 'refresh_current_model_output_support_figures.py').read_text(encoding='utf-8')
        self.assertIn('rendered_from_historical_support_replay', text)
        self.assertIn('rendered_from_retained_state_summary', text)
        self.assertIn('historical_support_state_summaries.rds', text)


if __name__ == '__main__':
    unittest.main()
