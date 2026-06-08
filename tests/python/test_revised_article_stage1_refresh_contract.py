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
        bindings = json.loads((ARTICLE_ROOT / 'config' / 'runtime_bindings.json').read_text(encoding='utf-8'))
        self.assertIn('refresh_cutoff_synthesis_families.py', text)
        self.assertIn('load_runtime_bindings', text)
        self.assertEqual(
            bindings['exal_m_t1']['keep_runtime_root'],
            '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524',
        )
        self.assertEqual(
            bindings['exal_m_t1']['authoritative_keep_manifest'],
            '/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml',
        )
        self.assertIn('--univar-runtime-root', text)
        self.assertIn('--multivar-support-run-root', text)
        self.assertEqual(
            bindings['exal_m_t1']['historical_support_replay_run_root'],
            '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_historical_support_replay_20260517/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep_historical_support_replay',
        )
        self.assertIn('--strict-current-model-support', text)
        self.assertIn('historical_support_from_current_models', text)

    def test_manuscript_asset_manifest_points_selected_model_note_to_corrected_relaunch(self) -> None:
        payload = json.loads((ARTICLE_ROOT / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text(encoding='utf-8'))
        fig = next(item for item in payload['figures'] if item['label'] == 'fig:synth1')
        self.assertEqual(fig['source_path'], 'artifacts/representative_selected_model_2022_12_25/representative_synthesis_multivariate.png')
        self.assertIn('exAL-M-T1', fig['note'])

    def test_benchmark_table_note_and_freeze_contract_match_final_nine_family_promotion(self) -> None:
        payload = json.loads((ARTICLE_ROOT / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text(encoding='utf-8'))
        note = payload['tables']['tab:benchmark_crps_models']['note']
        self.assertIn('All nine Bayesian benchmark families', note)
        self.assertIn('final CRPS table source', note)
        self.assertNotIn('three NDLM', note)
        self.assertNotIn('transitional', note)

        text = (ARTICLE_ROOT / 'scripts' / 'refresh_he2_manifest_snapshot.py').read_text(encoding='utf-8')
        self.assertIn('he2_publication_parity_gate.md', text)
        self.assertIn('he2_publication_parity_gate.csv', text)
        self.assertIn('he2_publication_parity_gate_summary.json', text)

        summary = json.loads((ARTICLE_ROOT / 'artifacts' / 'he2_publication_freeze' / 'he2_publication_parity_gate_summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['promoted_rows'], 45)
        self.assertEqual(summary['pending_rows'], 0)
        self.assertTrue(summary['final_9_model_benchmark_ready'])
        self.assertEqual(
            set(summary['promoted_labels']),
            {'N-U-T1', 'N-M-T0', 'N-M-T1', 'AL-M-T0', 'AL-M-T1', 'AL-U-T1', 'exAL-M-T0', 'exAL-M-T1', 'exAL-U-T1'},
        )

    def test_generated_benchmark_table_carries_promoted_family_crps_values(self) -> None:
        rows = (ARTICLE_ROOT / 'tables' / 'generated_tex' / 'benchmark_crps_bayesian_rows.tex').read_text(encoding='utf-8')
        self.assertIn('N-U-T1 & 0.3359 & 0.1706 & 1.1935 & 0.1508 & 2.4997', rows)
        self.assertIn('N-M-T0 & 1.8456 & 0.3802 & 0.6596 & 0.6701 & 0.6440', rows)
        self.assertIn('AL-M-T1 & 0.1459 & 0.0555 & 0.2778 & 0.0572 & 0.6276', rows)
        self.assertIn('exAL-M-T0 & 1.2215 & 1.7987 & 1.0850 & 2.1310 & 1.2113', rows)
        self.assertIn('exAL-M-T1 & \\textbf{0.1397} & \\textbf{0.0472} & \\textbf{0.2654} & \\textbf{0.0323} & 0.6655', rows)

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
