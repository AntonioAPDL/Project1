from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'reports' / 'he2_exal_m_t1_end_to_end_audit_20221225_20260518'


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        {
            'order_id': 1,
            'stage': 'history_location_summary',
            'function_name': 'smoke_build_multivar_hist_location_summary',
            'source_file': 'R/environmetrics/40_figures_smoke_fast.R',
            'line_ref': '1259-1266',
            'object_name': 'mu (history row-level location summary)',
            'semantic_type': 'internal exAL location-side quantity before predictive synthesis',
            'scale_contract': 'transformed to log1p_cms after construction',
            'key_formula_or_step': 'mu = xb + sigma * abs(gamma) * C_fn(p0, gamma) * s_t',
            'interpretation_risk': 'high',
            'notes': 'This is likely not the same as the final predictive quantile curve; it is a row-level location object used upstream of predictive generation.',
        },
        {
            'order_id': 2,
            'stage': 'history_predictive_draws',
            'function_name': 'smoke_build_multivar_synth_hist',
            'source_file': 'R/environmetrics/40_figures_smoke_fast.R',
            'line_ref': '1160-1179',
            'object_name': 'y_hist_cube',
            'semantic_type': 'row-level predictive sample cube in history window',
            'scale_contract': 'predictive draws transformed to log1p_cms before synthesis',
            'key_formula_or_step': 'u ~ Uniform; y_hist = inverse CDF AL(u, mu, sigma, p_exAL)',
            'interpretation_risk': 'medium',
            'notes': 'This is already a predictive quantity, unlike the location summary cache.',
        },
        {
            'order_id': 3,
            'stage': 'history_synthesis',
            'function_name': 'smoke_build_multivar_synth_hist',
            'source_file': 'R/environmetrics/40_figures_smoke_fast.R',
            'line_ref': '1182-1186',
            'object_name': 'synth_hist / hist_q',
            'semantic_type': 'synthesized historical predictive sample matrix and empirical quantiles',
            'scale_contract': 'log1p_cms',
            'key_formula_or_step': 'synthesize_samples(y_hist_cube, q_probs)',
            'interpretation_risk': 'low',
            'notes': 'This is one of the best candidate objects for interpretable historical predictive quantiles.',
        },
        {
            'order_id': 4,
            'stage': 'forecast_location_summary',
            'function_name': 'smoke_build_multivar_forecast_location_summary',
            'source_file': 'R/environmetrics/40_figures_smoke_fast.R',
            'line_ref': '776-869',
            'object_name': 'mean_internal / sd_internal -> mean_mat',
            'semantic_type': 'projected row-level USGS forecast location moments before predictive sampling',
            'scale_contract': 'transformed to log1p_cms after state projection',
            'key_formula_or_step': 'project latent state to USGS channel with smoke_project_state_gaussian',
            'interpretation_risk': 'high',
            'notes': 'This is a projected location object and should not automatically be read as the predictive quantile dynamic.',
        },
        {
            'order_id': 5,
            'stage': 'forecast_predictive_draws',
            'function_name': 'smoke_build_multivar_synth_f',
            'source_file': 'R/environmetrics/40_figures_smoke_fast.R',
            'line_ref': '708-760',
            'object_name': 'xbs -> y_reps_f_new',
            'semantic_type': 'row-level forecast predictive draws before synthesis',
            'scale_contract': 'internal post scale then transformed to log1p_cms via guard',
            'key_formula_or_step': 'xbs ~ Normal(projected mean, projected sd); y = rexal(p0, xbs, sigma, gamma)',
            'interpretation_risk': 'medium',
            'notes': 'This is the direct predictive object behind forecast synthesis.',
        },
        {
            'order_id': 6,
            'stage': 'forecast_transform_guard',
            'function_name': 'post_transform_internal_array_to_log1p',
            'source_file': 'R/environmetrics/02_helpers_core.R',
            'line_ref': '442-499',
            'object_name': 'forecast_log1p_guard',
            'semantic_type': 'transform guard / scale-contract enforcement',
            'scale_contract': 'identity for representative run because analysis_scale_post_internal=log1p_cms',
            'key_formula_or_step': 'guarded transform from internal predictive draws to log1p output contract',
            'interpretation_risk': 'low',
            'notes': 'This is where the representative stale log_log1p path was fixed.',
        },
        {
            'order_id': 7,
            'stage': 'forecast_synthesis',
            'function_name': 'smoke_build_multivar_synth_f',
            'source_file': 'R/environmetrics/40_figures_smoke_fast.R',
            'line_ref': '762-771',
            'object_name': 'synth_f',
            'semantic_type': 'synthesized forecast predictive sample matrix',
            'scale_contract': 'log1p_cms',
            'key_formula_or_step': 'synthesize_samples(forecast_log1p_guard$values, q_probs)',
            'interpretation_risk': 'low',
            'notes': 'This is the core forecast-window predictive object behind the canonical synthesis figure.',
        },
        {
            'order_id': 8,
            'stage': 'forecast_quantile_export',
            'function_name': 'publication_figure_rewrite / post export',
            'source_file': 'R/environmetrics/40_figures_smoke_fast.R',
            'line_ref': 'post-runner export path',
            'object_name': 'exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv',
            'semantic_type': 'exported synthesized forecast predictive quantile table',
            'scale_contract': 'log1p_cms',
            'key_formula_or_step': 'empirical quantiles from synth_f exported to csv',
            'interpretation_risk': 'low',
            'notes': 'This is what downstream review plots should use when we want predictive quantiles, not location summaries.',
        },
    ]

    fields = [
        'order_id', 'stage', 'function_name', 'source_file', 'line_ref', 'object_name',
        'semantic_type', 'scale_contract', 'key_formula_or_step', 'interpretation_risk', 'notes'
    ]
    write_csv(out_dir / 'object_semantics_codepath.csv', rows, fields)

    summary = {
        'audit_id': 'he2_exal_m_t1_object_semantics_codepath_audit_20221225_20260518',
        'row_count': len(rows),
        'main_interpretation': [
            'location-summary caches are not the same object as predictive quantile exports',
            'history and forecast predictive synthesis both pass through predictive draw objects before quantile export',
            'the representative scale bug was in the forecast transform guard path, not in the conceptual distinction between location summaries and predictive samples'
        ]
    }
    (out_dir / 'object_semantics_codepath_summary.json').write_text(json.dumps(summary, indent=2) + '\n')

    md = [
        '# HE2 exAL-M-T1 Object Semantics Codepath Audit',
        '',
        '## Main Takeaway',
        '',
        '- The workflow contains at least two distinct object families that can look superficially similar on the same scale:',
        '  - row-level location summaries',
        '  - row-level predictive draws / synthesized predictive quantiles',
        '- This distinction is likely central to the current confusion.',
        '',
        '## Outputs',
        '',
        f'- codepath table: `{out_dir / "object_semantics_codepath.csv"}`',
        '',
        '## Most Important Interpretation Risk',
        '',
        '- Plotting `multivar_*_usgs_location_summary_log1p.rds` as though it were the predictive quantile dynamic may be semantically wrong even if the scale is correct.',
    ]
    (out_dir / 'HE2_EXAL_M_T1_OBJECT_SEMANTICS_CODEPATH_AUDIT_20221225_20260518.md').write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
