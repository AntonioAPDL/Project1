from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = ROOT / 'Evironmetrics---REVISED-DOC-Corrected-2'
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
        self.assertEqual(
            bindings['exal_m_t1']['selected_support_output_root'],
            '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_selected_output_support_20260612_minus_trend/runs/multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_authoritative_support_samplewise_a1_minus_trend_20260612/post/outputs/multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep_authoritative_support_samplewise_a1_minus_trend_20260612',
        )
        self.assertIn('--univar-runtime-root', text)
        self.assertIn('--multivar-support-run-root', text)
        self.assertIn('--authoritative-selected-support-output-root', text)
        self.assertIn('refresh_authoritative_selected_model_support_figures.py', text)
        self.assertIn('validate_authoritative_output_lineage.py', text)
        self.assertEqual(
            bindings['exal_m_t1']['historical_support_replay_run_root'],
            '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_historical_support_replay_20260517/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep_historical_support_replay',
        )
        self.assertIn('--strict-current-model-support', text)
        self.assertIn('historical_support_from_current_models', text)
        self.assertIn('--skip-authoritative-selected-support', text)

    def test_manuscript_asset_manifest_points_selected_model_note_to_corrected_relaunch(self) -> None:
        payload = json.loads((ARTICLE_ROOT / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text(encoding='utf-8'))
        fig = next(item for item in payload['figures'] if item['label'] == 'fig:synth1')
        self.assertEqual(fig['source_path'], 'artifacts/representative_selected_model_2022_12_25/representative_synthesis_multivariate_with_reference_ensembles.png')
        self.assertIn('exAL-M-T1', fig['note'])

    def test_benchmark_table_note_and_freeze_contract_match_final_nine_family_promotion(self) -> None:
        payload = json.loads((ARTICLE_ROOT / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text(encoding='utf-8'))
        note = payload['tables']['tab:benchmark_crps_models']['note']
        self.assertIn('frozen HE2 publication manifest', note)
        self.assertIn('28-day raw GloFAS row', note)
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
        self.assertIn('N-U-T1 & 0.33592 & 0.17059 & 1.19344 & 0.15077 & 2.49968', rows)
        self.assertIn('N-M-T0 & 1.84333 & 0.38023 & 0.65964 & 0.67014 & 0.64404', rows)
        self.assertIn('AL-M-T1 & 0.14592 & 0.05551 & 0.27775 & 0.05467 & 0.62764', rows)
        self.assertIn('exAL-M-T0 & 0.75682 & 1.72135 & 0.97762 & 1.02087 & 1.21132', rows)
        self.assertIn('exAL-M-T1 & \\textbf{0.13971} & \\textbf{0.04724} & \\textbf{0.26045} & \\textbf{0.02273} & \\textbf{0.53806}', rows)

    def test_figure_polish_audit_contract_references_cutoff_wide_synthesis_manifests(self) -> None:
        text = (ARTICLE_ROOT / 'scripts' / 'build_figure_polish_status_audit.py').read_text(encoding='utf-8')
        self.assertIn('figures/multivariate_synthesis_by_cutoff/manifest.csv', text)
        self.assertIn('figures/reference_synthesis_by_cutoff/manifest.csv', text)

    def test_historical_support_refresh_supports_retained_support_contract(self) -> None:
        text = (ARTICLE_ROOT / 'scripts' / 'refresh_current_model_output_support_figures.py').read_text(encoding='utf-8')
        self.assertIn('rendered_from_historical_support_replay', text)
        self.assertIn('rendered_from_retained_state_summary', text)
        self.assertIn('historical_support_state_summaries.rds', text)

    def test_selected_output_replay_retains_rdata_on_post_failure(self) -> None:
        launch_text = (ROOT / 'scripts' / 'launch_he2_selected_output_support_replay.py').read_text(encoding='utf-8')
        builder_text = (ROOT / 'scripts' / 'build_he2_selected_output_support_replay_config.py').read_text(encoding='utf-8')
        self.assertIn('authoritative_support_r4_20260609.yaml', launch_text)
        self.assertIn('env["CLEANUP_RDATA_ON_FAILURE"] = "0"', launch_text)
        self.assertIn('"cleanup_on_failure": False', launch_text)
        self.assertIn('"cleanup_expected_on_failure": False', builder_text)
        self.assertIn('"cleanup_on_failure_env": "CLEANUP_RDATA_ON_FAILURE=0"', builder_text)


if __name__ == '__main__':
    unittest.main()
