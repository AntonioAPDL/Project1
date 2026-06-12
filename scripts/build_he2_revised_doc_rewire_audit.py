from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLE_ROOT = ROOT / 'Evironmetrics---REVISED-DOC-Corrected-2'
OUT_DIR = ROOT / 'reports' / 'he2_revised_doc_rewire_audit_20260517'


def read_json(path: Path):
    return json.loads(path.read_text())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = read_json(ARTICLE_ROOT / 'MANUSCRIPT_ASSET_MANIFEST.json')
    fig_manifest = {row['label']: row for row in read_csv(ARTICLE_ROOT / 'reports' / 'manuscript_asset_review' / 'figure_manifest.csv')}
    table_manifest = {row['label']: row for row in read_csv(ARTICLE_ROOT / 'reports' / 'manuscript_asset_review' / 'table_manifest.csv')}
    lineage_rows = {row['figure_path']: row for row in read_csv(ARTICLE_ROOT / 'reports' / 'article_figure_lineage_audit_20260516' / 'figure_lineage_status.csv')}
    lineage_summary = read_json(ARTICLE_ROOT / 'reports' / 'article_figure_lineage_audit_20260516' / 'summary.json')

    rep_bundle = read_json(ARTICLE_ROOT / 'artifacts' / 'representative_selected_model_2022_12_25' / 'bundle_metadata.json')
    hist_bundle = read_json(ARTICLE_ROOT / 'artifacts' / 'historical_support_from_current_models' / 'bundle_metadata.json')
    hist_render_meta = read_json(ARTICLE_ROOT / 'artifacts' / 'historical_support_from_current_models' / 'figures' / 'render_metadata.json')

    exal_summary = read_json(ROOT / 'reports' / 'he2_exal_revised_doc_audit_20260517' / 'summary.json')
    master_summary = read_json(ROOT / 'reports' / 'he2_master_workflow_audit_20260517' / 'summary.json')
    crps_summary = read_json(ROOT / 'reports' / 'he2_crps_table_readiness_20260517' / 'crps_table_readiness.json')
    family_tracker = {row['label']: row for row in read_csv(ROOT / 'reports' / 'he2_master_workflow_audit_20260517' / 'family_tracker.csv')}

    asset_rows: list[dict[str, object]] = []

    def figure_plan(fig: dict[str, object]) -> tuple[str, str, str, str]:
        label = fig['label']
        source_class = fig['source_class']
        if source_class == 'setup_support_v2_representative':
            return (
                'synced_to_canonical_support_bundle',
                'trusted_for_revised_doc',
                'keep_current; refresh only if setup-support v2 contract changes',
                'no',
            )
        if label == 'fig:synth1':
            return (
                'synced_to_latest_keep_output_but_output_quality_flagged',
                'run_side_quality_issue_confirmed',
                'current keep synthesis is synced but numerically implausible; treat this as a keep-output quality investigation before any rerun decision',
                'conditional',
            )
        if label in {'fig:dry_quantile', 'fig:rainy_quantile', 'fig:80_components'}:
            return (
                'synced_via_historical_support_replay_with_repaired_scale_contract',
                'trusted_after_rerender',
                'keep current; rerender from the same replay root only if the historical-support replay or scale contract changes',
                'conditional_on_replay_change',
            )
        if label == 'fig:synth2':
            return (
                'synced_to_latest_univar_output_via_support_bundle',
                'trusted_for_revised_doc_with_dependency_note',
                'keep current; refresh only if 2022-12-25 exAL univar rerun changes',
                'conditional_on_univar_rerun',
            )
        return (
            'needs_manual_classification',
            'manual_review',
            'manual review required',
            'unknown',
        )

    for fig in manifest['figures']:
        status, action_gate, recommended_action, rerun_needed = figure_plan(fig)
        fig_row = fig_manifest[fig['label']]
        lineage = lineage_rows.get(fig['manuscript_path'], {})
        asset_rows.append({
            'asset_kind': 'figure',
            'label': fig['label'],
            'manuscript_path': fig['manuscript_path'],
            'category': fig['category'],
            'role': fig['role'],
            'source_class': fig['source_class'],
            'article_source_path': fig['source_path'],
            'lineage_source_lineage': lineage.get('source_lineage', ''),
            'lineage_source_script': lineage.get('source_script', ''),
            'current_model_output_wired': fig['current_model_output_wired'],
            'current_status': status,
            'action_gate': action_gate,
            'recommended_action': recommended_action,
            'needs_model_rerun': rerun_needed,
            'local_check_path': str(ARTICLE_ROOT / fig['manuscript_path']),
            'notes': fig['note'],
        })

    for label, tbl in manifest['tables'].items():
        trow = table_manifest[label]
        if label == 'tab:benchmark_crps_models':
            current_status = 'frozen_non_authoritative_benchmark_source'
            action_gate = 'hold_until_family_set_ready'
            recommended_action = (
                'keep frozen; do not refresh until NDLM is canonical-bundle aligned, AL multivar keep/drop are complete, '
                'and exAL benchmark reconciliation is resolved'
            )
            rerun_needed = 'yes_family_set'
        else:
            current_status = 'synced_to_representative_keep_exports'
            action_gate = 'trusted_with_dependency_note'
            recommended_action = 'keep current; regenerate only if representative 2022-12-25 exAL keep rerun changes'
            rerun_needed = 'conditional_on_keep_rerun'
        asset_rows.append({
            'asset_kind': 'table',
            'label': label,
            'manuscript_path': tbl['table_tex_path'],
            'category': 'table',
            'role': tbl['role'],
            'source_class': tbl['source_class'],
            'article_source_path': ', '.join(tbl['sources'].values()),
            'lineage_source_lineage': '',
            'lineage_source_script': 'scripts/build_generated_table_includes.py',
            'current_model_output_wired': trow['source_class'] == 'current_selected_model_representative',
            'current_status': current_status,
            'action_gate': action_gate,
            'recommended_action': recommended_action,
            'needs_model_rerun': rerun_needed,
            'local_check_path': str(ARTICLE_ROOT / tbl['table_tex_path']),
            'notes': tbl['note'],
        })

    asset_fieldnames = [
        'asset_kind', 'label', 'manuscript_path', 'category', 'role', 'source_class', 'article_source_path',
        'lineage_source_lineage', 'lineage_source_script', 'current_model_output_wired', 'current_status',
        'action_gate', 'recommended_action', 'needs_model_rerun', 'local_check_path', 'notes'
    ]
    write_csv(OUT_DIR / 'manuscript_asset_tracker.csv', asset_rows, asset_fieldnames)

    generated_family_rows = [
        {
            'generated_family': 'representative_selected_model_2022_12_25',
            'role': 'representative keep bundle',
            'source_runtime_root': rep_bundle['runtime_run_root'],
            'article_path': 'artifacts/representative_selected_model_2022_12_25',
            'status': 'synced_to_latest_keep_rerun_but_quality_flagged',
            'primary_risk': 'replay_mean_crps_is_extreme_for_representative_keep',
            'recommended_action': 'treat as a run-side quality problem, not a rewiring problem; investigate keep model behavior before any rerun decision',
            'needs_model_rerun': 'conditional',
        },
        {
            'generated_family': 'historical_support_from_current_models',
            'role': 'dry/wet/component/univar support bundle',
            'source_runtime_root': hist_bundle['multivar_source']['historical_support_render_run_root'],
            'article_path': 'artifacts/historical_support_from_current_models',
            'status': 'synced_with_repaired_scale_contract',
            'primary_risk': 'none_detected_in_scale_contract_after_rerender',
            'recommended_action': 'keep current; reuse the retained support replay/state-summary contract for future rewires',
            'needs_model_rerun': 'conditional_on_replay_change',
        },
        {
            'generated_family': 'five_cutoff_setup_support',
            'role': 'canonical setup/support bundle',
            'source_runtime_root': lineage_summary['setup_support_runtime_root'],
            'article_path': 'artifacts/five_cutoff_setup_support',
            'status': 'trusted_current',
            'primary_risk': 'none_detected_in_current_audit',
            'recommended_action': 'keep current; only refresh if setup/support input contract changes',
            'needs_model_rerun': 'no',
        },
        {
            'generated_family': 'multivariate_synthesis_by_cutoff',
            'role': 'advisor-facing five-cutoff keep synthesis family',
            'source_runtime_root': lineage_summary['completed_keep_output_root'],
            'article_path': 'figures/multivariate_synthesis_by_cutoff',
            'status': 'synced_to_latest_keep_reruns',
            'primary_risk': 'visual quality may reflect substantive keep rerun issues rather than stale wiring',
            'recommended_action': 'use for debugging source quality; if they look bad, investigate keep run outputs before rewriting article assets',
            'needs_model_rerun': 'conditional',
        },
        {
            'generated_family': 'reference_synthesis_by_cutoff',
            'role': 'advisor-facing five-cutoff univar synthesis family',
            'source_runtime_root': lineage_summary['completed_univar_output_root'],
            'article_path': 'figures/reference_synthesis_by_cutoff',
            'status': 'synced_to_latest_univar_reruns',
            'primary_risk': 'depends on whether exAL univar remains the final reference family',
            'recommended_action': 'keep current; refresh only if univar rerun changes',
            'needs_model_rerun': 'conditional_on_univar_rerun',
        },
        {
            'generated_family': 'benchmark_crps_main_table',
            'role': 'manuscript benchmark table source layer',
            'source_runtime_root': 'artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv + artifacts/five_cutoff_crps_validation_sources',
            'article_path': 'tables/generated_tex/benchmark_crps_main_table.tex',
            'status': 'frozen_hold',
            'primary_risk': 'not rebuilt from unified authoritative family set',
            'recommended_action': 'hold until NDLM canonical reruns and AL multivar launches are complete and exAL benchmark rows are reconciled',
            'needs_model_rerun': 'yes_family_set',
        },
    ]
    family_fieldnames = [
        'generated_family', 'role', 'source_runtime_root', 'article_path', 'status', 'primary_risk',
        'recommended_action', 'needs_model_rerun'
    ]
    write_csv(OUT_DIR / 'generated_family_tracker.csv', generated_family_rows, family_fieldnames)

    rerun_gate_rows = [
        {
            'label': 'exAL-M-T1',
            'family': 'exdqlm_multivar_keep',
            'current_family_state': family_tracker['exAL-M-T1']['current_status'],
            'revised_doc_role': 'setup/support representative, representative synthesis, historical support, representative tables',
            'rewire_decision_now': 'rewiring_complete_hold_rerun_decision_for_run_side_quality_review',
            'when_rerun_is_required': 'only if the keep run-side quality investigation confirms that the latest synced outputs are not scientifically acceptable',
            'approved_tuning_policy': 'warm-up/stabilization first; epsilon/c_factor only with explicit approval',
        },
        {
            'label': 'exAL-M-T0',
            'family': 'exdqlm_multivar_drop',
            'current_family_state': family_tracker['exAL-M-T0']['current_status'],
            'revised_doc_role': 'benchmark-table family only in current manuscript',
            'rewire_decision_now': 'no figure rerun needed; hold until benchmark-table rebuild phase',
            'when_rerun_is_required': 'only if benchmark reconciliation or drop-family diagnostics show current rerun outputs are not acceptable',
            'approved_tuning_policy': 'warm-up/stabilization first; epsilon/c_factor only with explicit approval',
        },
        {
            'label': 'exAL-U-T1',
            'family': 'exdqlm_univar',
            'current_family_state': family_tracker['exAL-U-T1']['current_status'],
            'revised_doc_role': 'reference synthesis, benchmark-table family',
            'rewire_decision_now': 'no immediate rerun for figures; keep current reference synthesis wiring',
            'when_rerun_is_required': 'only if benchmark reconciliation or univar quality audit shows current rerun outputs are not acceptable',
            'approved_tuning_policy': 'warm-up/stabilization first; epsilon/c_factor only with explicit approval',
        },
        {
            'label': 'AL-M-T1',
            'family': 'dqlm_multivar_al_keep',
            'current_family_state': family_tracker['AL-M-T1']['current_status'],
            'revised_doc_role': 'future benchmark-table family',
            'rewire_decision_now': 'do not launch yet; reopen as explicit warm-up/stabilization investigation',
            'when_rerun_is_required': 'after q65 issue is isolated and a no-launch validator passes',
            'approved_tuning_policy': 'warm-up/stabilization first; no epsilon/c_factor changes without approval',
        },
        {
            'label': 'AL-M-T0',
            'family': 'dqlm_multivar_al_drop',
            'current_family_state': family_tracker['AL-M-T0']['current_status'],
            'revised_doc_role': 'future benchmark-table family',
            'rewire_decision_now': 'do not launch yet; reopen as explicit warm-up/stabilization investigation',
            'when_rerun_is_required': 'after q65 issue is isolated and a no-launch validator passes',
            'approved_tuning_policy': 'warm-up/stabilization first; no epsilon/c_factor changes without approval',
        },
        {
            'label': 'AL-U-T1',
            'family': 'dqlm_univar_al',
            'current_family_state': family_tracker['AL-U-T1']['current_status'],
            'revised_doc_role': 'future benchmark-table family',
            'rewire_decision_now': 'no immediate action for revised-doc assets; wait until benchmark-table rebuild phase',
            'when_rerun_is_required': 'only if family-level audit later finds output-quality or bundle-contract issues',
            'approved_tuning_policy': 'warm-up/stabilization first; no epsilon/c_factor changes without approval',
        },
        {
            'label': 'NDLM-family',
            'family': 'ndlm_main_keep / ndlm_main_drop / ndlm_univar_keep',
            'current_family_state': 'completed_but_not_current_bundle_aligned',
            'revised_doc_role': 'benchmark-table family set and future table refreshes',
            'rewire_decision_now': 'plan canonical shared-bundle rerelaunch before touching benchmark table',
            'when_rerun_is_required': 'required before benchmark CRPS rebuild',
            'approved_tuning_policy': 'preserve NDLM identity while migrating only the input bundle and transform contract',
        },
    ]
    rerun_fieldnames = [
        'label', 'family', 'current_family_state', 'revised_doc_role', 'rewire_decision_now',
        'when_rerun_is_required', 'approved_tuning_policy'
    ]
    write_csv(OUT_DIR / 'family_rewire_gate_tracker.csv', rerun_gate_rows, rerun_fieldnames)

    summary = {
        'manuscript_figure_count': len(manifest['figures']),
        'manuscript_table_count': len(manifest['tables']),
        'figures_currently_wired_to_current_outputs': sum(1 for fig in manifest['figures'] if fig['current_model_output_wired']),
        'representative_keep_bundle_source': rep_bundle['runtime_run_root'],
        'representative_keep_replay_mean_crps': rep_bundle['replay_mean_crps'],
        'historical_support_render_run_root': hist_bundle['multivar_source']['historical_support_render_run_root'],
        'historical_support_display_flow_scale': hist_render_meta['display_flow_scale'],
        'historical_support_internal_flow_scale': hist_render_meta['internal_flow_scale'],
        'historical_support_scale_contract_suspect': hist_render_meta['internal_flow_scale'] != 'log1p_cms',
        'benchmark_table_should_be_refreshed_now': False,
        'benchmark_table_blocker': crps_summary['decision'],
        'ndlm_canonical_bundle_aligned': crps_summary['ndlm_bundle_alignment']['aligned_to_20260510_canonical_shared_bundle'],
        'al_multivar_ready': False,
        'recommended_next_phase': 'model_family_quality_audit_and_rerun_gate_review',
    }
    (OUT_DIR / 'rewire_summary.json').write_text(json.dumps(summary, indent=2) + '\n')

    md: list[str] = []
    md.append('# HE2 Revised-Doc Wiring And Rewire Audit (2026-05-17)\n\n')
    md.append('## Purpose\n\n')
    md.append('This audit turns the revised-doc figure/table state into a single rewiring plan. It separates three different failure modes so we stop mixing them together:\n\n')
    md.append('1. **Wiring problems**: the manuscript is pointing at the wrong artifact family or old runtime root.\n')
    md.append('2. **Renderer problems**: the manuscript is pointing at the right family, but the generator transforms or displays it incorrectly.\n')
    md.append('3. **Model-output problems**: the manuscript is pointing at the right latest output, but the latest output itself is scientifically or numerically suspect.\n\n')
    md.append('## Executive Summary\n\n')
    md.append(f"- Manuscript assets tracked here: `{len(manifest['figures'])}` figures and `{len(manifest['tables'])}` tables.\n")
    md.append(f"- Article figure lineage status counts: `{json.dumps(lineage_summary['status_counts'])}`.\n")
    md.append(f"- Representative keep bundle source: `{rep_bundle['runtime_run_root']}`.\n")
    md.append(f"- Representative keep bundle currently records `replay_mean_crps = {rep_bundle['replay_mean_crps']}` against `published_crps = {rep_bundle['published_crps']}`.\n")
    md.append(f"- Historical-support render metadata now records `display_flow_scale = {hist_render_meta['display_flow_scale']}` and `internal_flow_scale = {hist_render_meta['internal_flow_scale']}`.\n")
    md.append('- Benchmark table should remain frozen now.\n\n')
    md.append('## Core Findings\n\n')
    md.append('### 1. What is well wired right now\n\n')
    md.append('- Setup/support manuscript figures are wired to the canonical `five_cutoff_setup_support` bundle and its validated `20260516` full-history/GDPC contract.\n')
    md.append('- The manuscript representative synthesis figure (`fig:synth1`) is synced to the latest `20260516` `exAL-M-T1` keep rerun and copied through `artifacts/representative_selected_model_2022_12_25/`.\n')
    md.append('- The appendix support reference synthesis (`fig:synth2`) is synced to the latest `20260516` exAL univar rerun.\n')
    md.append('- Representative keep-side appendix/source tables (`components`, `gamma`, `sigma`) are generated from the representative keep bundle and are wired correctly at the article layer.\n\n')
    md.append('### 2. What is synced but not yet trustworthy\n\n')
    md.append('- `fig:synth1` is **current**, but the current representative keep bundle already records an extreme replay CRPS. That means the figure may look bad because the latest rerun output is bad, not because the article is stale.\n')
    md.append('- The dry/wet historical-support figures and the 80-month component figure are **current**, and the renderer scale contract has now been repaired to `log1p_cms -> log1p_cms` for this replay lane.\n\n')
    md.append('### 3. What should stay frozen\n\n')
    md.append('- The benchmark CRPS table should stay frozen. It is still sourced from the frozen publication manifest plus raw baselines and should not be refreshed until NDLM is canonical-bundle aligned, AL multivariate families are complete, and exAL benchmark rows are reconciled.\n\n')
    md.append('## Action Matrix\n\n')
    md.append('| Area | Current state | What to do next | Needs model rerun? |\n')
    md.append('|---|---|---|---:|\n')
    md.append('| Setup/support manuscript figures | trusted and current | keep current | no |\n')
    md.append('| Representative keep synthesis figure | current but quality-flagged | audit latest keep outputs before promoting any new table layer | conditional |\n')
    md.append('| Historical-support dry/wet/component figures | current with repaired scale contract | keep current and reuse the replay/state-summary contract for future rewires | conditional on replay change |\n')
    md.append('| Representative keep appendix/source tables | current | keep current unless representative keep rerun changes | conditional |\n')
    md.append('| Benchmark CRPS table | frozen non-authoritative | hold | yes family set |\n\n')
    md.append('## Recommended Phase Order\n\n')
    md.append('### Phase A: Repair article-side historical-support rendering\n\n')
    md.append('Goal: make Figures 5, 6, and A1 trustworthy without touching model specs.\n\n')
    md.append('Status: complete in this audit cycle.\n\n')
    md.append('Completed tasks:\n')
    md.append('- patched `Evironmetrics---REVISED-DOC-Corrected-2/scripts/render_current_model_output_support_figures.R` so the internal scale is read from the replay contract instead of hardcoding `log_log1p_cms`;\n')
    md.append('- regenerated `artifacts/historical_support_from_current_models/`;\n')
    md.append('- rebuilt article refresh/audit outputs;\n')
    md.append('- synced the rerendered historical-support figures into the manuscript figure tree.\n\n')
    md.append('### Phase B: Audit current exAL keep output quality\n\n')
    md.append('Goal: determine whether the weird forecast-window synthesis figures reflect a real keep-run problem.\n\n')
    md.append('Tasks:\n')
    md.append('- audit representative keep `2022-12-25` post outputs, CRPS summaries, forecast-window quantiles, and source-map lineage;\n')
    md.append('- compare representative keep behavior across the five cutoff-wide synthesis figures;\n')
    md.append('- decide whether the issue is plotting-only, post-metric-only, or a true model-output problem.\n\n')
    md.append('Rerun policy for this phase:\n')
    md.append('- do **not** change `epsilon` / `c_factor` first;\n')
    md.append('- if a rerun is needed, warm-up/stabilization changes come first;\n')
    md.append('- only after that, consider quantile-specific tuning with explicit approval.\n\n')
    md.append('### Phase C: Hold benchmark table and build final rewrite-ready binding layer\n\n')
    md.append('Goal: make future rewires safe and explicit.\n\n')
    md.append('Status: complete for the current revised-doc refresh layer.\n\n')
    md.append('Completed tasks:\n')
    md.append('- kept the benchmark CRPS table frozen;\n')
    md.append('- introduced a single article-to-runtime binding file so refresh scripts stop relying on embedded defaults;\n')
    md.append('- made each asset family (`setup_support`, `representative_keep`, `historical_support`, `cutoff_synthesis`, `benchmark_table`) choose its runtime roots from that binding layer;\n')
    md.append('- future reruns can now be rewired by editing one binding file and rerunning one audited refresh entrypoint.\n\n')
    md.append('### Phase D: Model-family rerun gates\n\n')
    md.append('- `exAL-M-T1`: rerun only if Phase B confirms the current representative keep outputs are genuinely broken.\n')
    md.append('- `exAL-M-T0` and `exAL-U-T1`: no immediate rerun for revised-doc figures; revisit only during benchmark-table rebuild.\n')
    md.append('- `AL-M-T1` and `AL-M-T0`: reopen only as warm-up/stabilization investigations.\n')
    md.append('- NDLM families: canonical shared-bundle rerelaunch is required before benchmark-table rebuild.\n\n')
    md.append('## Deliverables In This Audit Package\n\n')
    md.append('- `manuscript_asset_tracker.csv`: one row per manuscript figure/table with current wiring state, action gate, and rerun need.\n')
    md.append('- `generated_family_tracker.csv`: one row per generated asset family with the current runtime root and rewiring recommendation.\n')
    md.append('- `family_rewire_gate_tracker.csv`: family-level rerun/rewire decisions.\n')
    md.append('- `rewire_summary.json`: machine-readable top summary.\n')
    (OUT_DIR / 'HE2_REVISED_DOC_WIRING_AND_REWIRE_AUDIT_20260517.md').write_text(''.join(md))

    print(f'Wrote revised-doc rewire audit to {OUT_DIR}')


if __name__ == '__main__':
    main()
