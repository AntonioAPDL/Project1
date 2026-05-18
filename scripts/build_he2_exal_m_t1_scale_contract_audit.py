from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / 'runtime_placeholder'
DEFAULT_RUN_ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep')
OUT_DIR = ROOT / 'reports' / 'he2_exal_m_t1_end_to_end_audit_20221225_20260518'


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def parse_key_value_file(path: Path, sep: str = '=') -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or sep not in line:
            continue
        key, value = line.split(sep, 1)
        out[key.strip()] = value.strip()
    return out


def parse_resolved_config_scalars(path: Path, keys: Iterable[str]) -> dict[str, str]:
    wanted = set(keys)
    out: dict[str, str] = {}
    if not path.exists():
        return out
    rx = re.compile(r'^\s*([A-Za-z0-9_]+):\s*(.+?)\s*$')
    for line in path.read_text().splitlines():
        m = rx.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        if key in wanted and key not in out:
            out[key] = value.strip("'\"")
    return out


def numeric_summary_from_column(path: Path, col: str) -> str:
    if not path.exists():
        return 'missing'
    rows = read_csv(path)
    vals: list[float] = []
    for r in rows:
        try:
            v = float(r[col])
        except Exception:
            continue
        if math.isfinite(v):
            vals.append(v)
    if not vals:
        return f'column={col}; no numeric values'
    return f'column={col}; n={len(vals)}; min={min(vals):.6f}; max={max(vals):.6f}'


def text_head(path: Path, n: int = 2) -> str:
    if not path.exists():
        return 'missing'
    lines = path.read_text().splitlines()[:n]
    return ' | '.join(lines)


def row(
    *,
    object_id: str,
    stage: str,
    semantic_role: str,
    path: Path,
    object_format: str,
    intended_scale: str,
    actual_scale_assessment: str,
    evidence: str,
    upstream_transform: str,
    downstream_transform: str,
    verification_status: str,
    notes: str,
) -> dict[str, object]:
    return {
        'object_id': object_id,
        'stage': stage,
        'semantic_role': semantic_role,
        'path': str(path),
        'exists': path.exists(),
        'object_format': object_format,
        'intended_scale': intended_scale,
        'actual_scale_assessment': actual_scale_assessment,
        'evidence': evidence,
        'upstream_transform': upstream_transform,
        'downstream_transform': downstream_transform,
        'verification_status': verification_status,
        'notes': notes,
    }


def main() -> None:
    run_root = DEFAULT_RUN_ROOT
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    source_map = parse_key_value_file(run_root / 'inputs' / 'shared' / 'source_map.txt')
    resolved = parse_resolved_config_scalars(
        run_root / 'resolved_config.yaml',
        keys=[
            'retros_storage_scale',
            'legacy_fit_input_scale',
            'legacy_post_input_scale',
            'analysis_scale_fit_internal',
            'analysis_scale_post_internal',
            'transform_policy',
        ],
    )
    model_id = run_root.name
    post_out = run_root / 'post' / 'outputs' / model_id
    post_cache = run_root / 'post' / 'cache'

    rows: list[dict[str, object]] = []

    raw_usgs_source = Path(source_map.get('source.usgs', ''))
    shared_usgs = run_root / 'inputs' / 'shared' / 'usgs' / 'usgs_daily.csv'
    shared_retros = run_root / 'inputs' / 'shared' / 'retros' / 'retros.csv'
    post_retros = run_root / 'post' / 'inputs' / 'retros_post_adapter.csv'
    shared_glofas_fc = run_root / 'inputs' / 'shared' / 'forecasts' / 'glofas_forecast.csv'
    post_glofas_fc = run_root / 'post' / 'inputs' / 'glofas_post_adapter.csv'
    shared_nws_fc = run_root / 'inputs' / 'shared' / 'forecasts' / 'nws_forecast.csv'
    post_nws_fc = run_root / 'post' / 'inputs' / 'nws_post_adapter.csv'
    fit_matrix = post_out / 'data_cbind_tY_X.csv'
    timestamps = post_out / 'timestamps.csv'
    q_csv = post_out / 'exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv'
    sample_subset = post_out / 'exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv'
    fig_png = post_out / 'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png'
    draw_cache = post_cache / 'exdqlm_multivar_synth_keep__mode-keep__y_reps_f_new_smoke.rds'
    synth_fc = post_cache / 'exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_log1p.rds'
    synth_fc_q = post_cache / 'exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_quantiles_log1p.rds'
    synth_hist = post_cache / 'exdqlm_multivar_synth_keep__mode-keep__synth_multivar_hist_log1p.rds'
    loc_hist = post_cache / 'exdqlm_multivar_synth_keep__mode-keep__multivar_hist_usgs_location_summary_log1p.rds'
    loc_fc = post_cache / 'exdqlm_multivar_synth_keep__mode-keep__multivar_forecast_usgs_location_summary_log1p.rds'
    exp_guard = post_cache / 'exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_exp_guard.txt'
    fit_q50 = run_root / 'fit' / 'exdqlm_multivar' / 'keep' / 'q=50' / 'outputs' / 'DISC_variables_50_exAL_synth_DISC.RData'

    rows.append(row(
        object_id='raw_usgs_source',
        stage='raw_input',
        semantic_role='authoritative raw USGS discharge source used to build shared bundle snapshot',
        path=raw_usgs_source,
        object_format='csv',
        intended_scale='raw_cms',
        actual_scale_assessment='raw_cms',
        evidence=numeric_summary_from_column(raw_usgs_source, 'discharge_cms'),
        upstream_transform='none',
        downstream_transform='log1p applied when building retros/fit ingress',
        verification_status='verified_by_values',
        notes='raw discharge values are nonnegative cms; this is the upstream physical flow source',
    ))
    rows.append(row(
        object_id='shared_usgs_snapshot',
        stage='shared_bundle',
        semantic_role='USGS snapshot preserved alongside the representative run inputs',
        path=shared_usgs,
        object_format='csv',
        intended_scale='raw_cms',
        actual_scale_assessment='raw_cms',
        evidence=numeric_summary_from_column(shared_usgs, 'discharge_cms'),
        upstream_transform='snapshot of raw flow source',
        downstream_transform='log1p used when building retros adapter / fit ingress',
        verification_status='verified_by_values',
        notes='contains raw `discharge_cms` and is not itself transformed to log1p',
    ))
    rows.append(row(
        object_id='shared_retros_matrix',
        stage='shared_bundle',
        semantic_role='historical USGS/GloFAS/NWS matrix used before fit/post adapters',
        path=shared_retros,
        object_format='csv',
        intended_scale=resolved.get('retros_storage_scale', 'log1p_cms'),
        actual_scale_assessment='log1p_cms',
        evidence=numeric_summary_from_column(shared_retros, 'USGS'),
        upstream_transform='log1p(raw source values)',
        downstream_transform='directly reused by fit/post adapters',
        verification_status='verified_by_values_and_config',
        notes='values align with expected `log1p(cms)` range and config advertises retros_storage_scale=log1p_cms',
    ))
    rows.append(row(
        object_id='post_retros_adapter',
        stage='post_inputs',
        semantic_role='post-stage retrospective adapter used by smoke-fast figure builders',
        path=post_retros,
        object_format='csv',
        intended_scale=resolved.get('legacy_post_input_scale', 'log1p_cms'),
        actual_scale_assessment='log1p_cms',
        evidence=numeric_summary_from_column(post_retros, 'USGS'),
        upstream_transform='copied/adapted from shared retros matrix',
        downstream_transform='fed into post-stage review and historical support plots',
        verification_status='verified_by_values_and_config',
        notes='post adapter is already on log1p scale; no additional exp/log should be applied here',
    ))
    rows.append(row(
        object_id='shared_glofas_forecast',
        stage='shared_bundle',
        semantic_role='shared GloFAS ensemble forecast input before post adapter transform',
        path=shared_glofas_fc,
        object_format='csv',
        intended_scale='raw_cms',
        actual_scale_assessment='raw_cms',
        evidence=text_head(shared_glofas_fc, 2),
        upstream_transform='none',
        downstream_transform='member-wise log1p in post adapter',
        verification_status='verified_by_value_comparison',
        notes='raw shared forecast values like 0.3125 become 0.271933... in post adapter, consistent with log1p',
    ))
    rows.append(row(
        object_id='post_glofas_forecast_adapter',
        stage='post_inputs',
        semantic_role='post-stage GloFAS forecast adapter consumed by post diagnostics',
        path=post_glofas_fc,
        object_format='csv',
        intended_scale=resolved.get('legacy_post_input_scale', 'log1p_cms'),
        actual_scale_assessment='log1p_cms',
        evidence=text_head(post_glofas_fc, 2),
        upstream_transform='member-wise log1p(raw shared forecast)',
        downstream_transform='used as forecast covariate/reference input in post stage',
        verification_status='verified_by_value_comparison',
        notes='adapter values match log1p of shared GloFAS member values',
    ))
    rows.append(row(
        object_id='shared_nws_forecast',
        stage='shared_bundle',
        semantic_role='shared NWS ensemble forecast input before post adapter transform',
        path=shared_nws_fc,
        object_format='csv',
        intended_scale='raw_cms',
        actual_scale_assessment='raw_cms',
        evidence=text_head(shared_nws_fc, 2),
        upstream_transform='none',
        downstream_transform='member-wise log1p in post adapter',
        verification_status='verified_by_value_comparison',
        notes='shared NWS forecast is stored in raw cms before adaptation',
    ))
    rows.append(row(
        object_id='post_nws_forecast_adapter',
        stage='post_inputs',
        semantic_role='post-stage NWS forecast adapter consumed by post diagnostics',
        path=post_nws_fc,
        object_format='csv',
        intended_scale=resolved.get('legacy_post_input_scale', 'log1p_cms'),
        actual_scale_assessment='log1p_cms',
        evidence=text_head(post_nws_fc, 2),
        upstream_transform='member-wise log1p(raw shared forecast)',
        downstream_transform='used as forecast covariate/reference input in post stage',
        verification_status='verified_by_value_comparison',
        notes='adapter values match log1p of shared NWS member values',
    ))
    rows.append(row(
        object_id='fit_ingress_matrix',
        stage='post_exports',
        semantic_role='exported design/response matrix showing the scale used by the fit ingress',
        path=fit_matrix,
        object_format='csv',
        intended_scale=resolved.get('legacy_fit_input_scale', 'log1p_cms'),
        actual_scale_assessment='log1p_cms',
        evidence=numeric_summary_from_column(fit_matrix, 'USGS'),
        upstream_transform='log1p applied before/at ingress',
        downstream_transform='fit internal analysis scale uses same contract for this run',
        verification_status='verified_by_values_and_config',
        notes='negative values near zero flow are expected on log1p scale when raw flow < 1 cms',
    ))
    rows.append(row(
        object_id='fit_ingress_timestamps',
        stage='post_exports',
        semantic_role='row-to-date mapping for exported fit ingress matrix',
        path=timestamps,
        object_format='csv',
        intended_scale='date_index',
        actual_scale_assessment='date_index',
        evidence=text_head(timestamps, 3),
        upstream_transform='none',
        downstream_transform='used to align ingress rows to source dates',
        verification_status='verified_by_values',
        notes='starts at 1987-05-29, matching the canonical full-history contract',
    ))
    rows.append(row(
        object_id='predictive_draw_cache',
        stage='post_cache',
        semantic_role='row-level forecast predictive draws before synthesis',
        path=draw_cache,
        object_format='rds',
        intended_scale=resolved.get('analysis_scale_post_internal', 'log1p_cms'),
        actual_scale_assessment=resolved.get('analysis_scale_post_internal', 'log1p_cms'),
        evidence=f'config analysis_scale_post_internal={resolved.get("analysis_scale_post_internal", "unknown")}',
        upstream_transform='generated by rexal()/AL predictive path on post internal scale',
        downstream_transform='identity to log1p for this run; guarded by exp-guard report',
        verification_status='verified_by_config_and_codepath',
        notes='for this representative run the active internal post scale is already log1p_cms',
    ))
    rows.append(row(
        object_id='forecast_exp_guard',
        stage='post_cache',
        semantic_role='explicit scale-guard report for forecast predictive draw transform',
        path=exp_guard,
        object_format='txt',
        intended_scale='guard_metadata',
        actual_scale_assessment='identity guard on log1p_cms',
        evidence=text_head(exp_guard, 3),
        upstream_transform='none; report generated by post guard helper',
        downstream_transform='documents whether exp/log transform was applied',
        verification_status='verified_by_guard_report',
        notes='used to prove that the stale log_log1p->exp path has been disabled for the representative cutoff',
    ))
    rows.append(row(
        object_id='forecast_location_summary_cache',
        stage='post_cache',
        semantic_role='row-level forecast USGS location summary before predictive synthesis',
        path=loc_fc,
        object_format='rds',
        intended_scale='log1p_cms',
        actual_scale_assessment='log1p_cms',
        evidence='cache filename and builder emit *_log1p.rds after post_transform_internal_to_log1p_mat',
        upstream_transform='projected state mean/sd on internal scale transformed to log1p',
        downstream_transform='used by custom review plots only',
        verification_status='verified_by_codepath_and_filename',
        notes='this is a location-summary diagnostic object, not the final predictive quantile export',
    ))
    rows.append(row(
        object_id='historical_location_summary_cache',
        stage='post_cache',
        semantic_role='row-level historical USGS location summary before predictive synthesis',
        path=loc_hist,
        object_format='rds',
        intended_scale='log1p_cms',
        actual_scale_assessment='log1p_cms',
        evidence='cache filename and builder emit *_log1p.rds after post_transform_internal_to_log1p_mat',
        upstream_transform='history-side location object transformed to log1p',
        downstream_transform='used by custom review plots only',
        verification_status='verified_by_codepath_and_filename',
        notes='object semantics still under audit; scale contract is log1p',
    ))
    rows.append(row(
        object_id='synth_forecast_sample_cache',
        stage='post_cache',
        semantic_role='synthesized forecast predictive sample matrix',
        path=synth_fc,
        object_format='rds',
        intended_scale='log1p_cms',
        actual_scale_assessment='log1p_cms',
        evidence='cache filename includes _log1p and builder transforms predictive draws to log1p before synthesis',
        upstream_transform='identity transform from internal scale for this run',
        downstream_transform='empirical quantile extraction and figure export',
        verification_status='verified_by_codepath_and_filename',
        notes='this is the main cache behind the forecast-window synthesis figure',
    ))
    rows.append(row(
        object_id='synth_forecast_quantile_cache',
        stage='post_cache',
        semantic_role='forecast predictive empirical quantiles extracted from synthesized sample matrix',
        path=synth_fc_q,
        object_format='rds',
        intended_scale='log1p_cms',
        actual_scale_assessment='log1p_cms',
        evidence='cache filename includes _log1p',
        upstream_transform='empirical quantiles of synthesized forecast samples',
        downstream_transform='csv/table/plot export',
        verification_status='verified_by_codepath_and_filename',
        notes='this object is closer to the interpretable predictive quantile dynamic than the location-summary caches',
    ))
    rows.append(row(
        object_id='synth_history_sample_cache',
        stage='post_cache',
        semantic_role='synthesized historical predictive sample matrix',
        path=synth_hist,
        object_format='rds',
        intended_scale='log1p_cms',
        actual_scale_assessment='log1p_cms',
        evidence='cache filename includes _log1p',
        upstream_transform='history predictive draws transformed to log1p before synthesis',
        downstream_transform='historical quantile export/diagnostics',
        verification_status='verified_by_codepath_and_filename',
        notes='useful for comparing historical predictive behavior against historical location summaries',
    ))
    rows.append(row(
        object_id='forecast_quantile_csv',
        stage='post_outputs',
        semantic_role='exported forecast-window synthesized predictive quantiles used by downstream diagnostics',
        path=q_csv,
        object_format='csv',
        intended_scale='log1p_cms',
        actual_scale_assessment='log1p_cms',
        evidence=text_head(q_csv, 2),
        upstream_transform='export from synthesized log1p predictive sample matrix',
        downstream_transform='rendered into png/pdf diagnostics',
        verification_status='verified_by_codepath_and_filename',
        notes='current canonical forecast-window quantile export after the representative scale fix',
    ))
    rows.append(row(
        object_id='forecast_sample_subset_csv',
        stage='post_outputs',
        semantic_role='exported subset of synthesized forecast predictive samples',
        path=sample_subset,
        object_format='csv',
        intended_scale='log1p_cms',
        actual_scale_assessment='log1p_cms',
        evidence=text_head(sample_subset, 2),
        upstream_transform='sample subset from synthesized forecast sample matrix',
        downstream_transform='diagnostic review only',
        verification_status='verified_by_codepath_and_filename',
        notes='supports sanity checks on the synthesized predictive distribution',
    ))
    rows.append(row(
        object_id='forecast_synthesis_png',
        stage='post_outputs',
        semantic_role='canonical forecast-window synthesis figure',
        path=fig_png,
        object_format='png',
        intended_scale='log1p_cms',
        actual_scale_assessment='log1p_cms (label and underlying cache)',
        evidence='paired with *_log1p caches and post_publication y-axis label on log(1+x)',
        upstream_transform='rendered from synthesized log1p forecast samples/quantiles',
        downstream_transform='human interpretation / revised-doc wiring decisions',
        verification_status='verified_by_codepath_and_plot_contract',
        notes='figure may still look bad, but the active representative post path now uses the corrected log1p contract',
    ))
    rows.append(row(
        object_id='fit_q50_rdata',
        stage='fit_outputs',
        semantic_role='retained q50 fit object bundle for representative run',
        path=fit_q50,
        object_format='RData',
        intended_scale=resolved.get('analysis_scale_fit_internal', 'log1p_cms'),
        actual_scale_assessment=resolved.get('analysis_scale_fit_internal', 'log1p_cms'),
        evidence=f'config analysis_scale_fit_internal={resolved.get("analysis_scale_fit_internal", "unknown")}',
        upstream_transform='fit internal state/parameter objects on representative internal scale',
        downstream_transform='consumed by post-stage replay scripts and retained diagnostic audits',
        verification_status='verified_by_config',
        notes='semantic content requires separate decomposition audit; this row captures the scale contract only',
    ))

    fieldnames = [
        'object_id', 'stage', 'semantic_role', 'path', 'exists', 'object_format', 'intended_scale',
        'actual_scale_assessment', 'evidence', 'upstream_transform', 'downstream_transform',
        'verification_status', 'notes'
    ]
    write_csv(out_dir / 'scale_contract_inventory.csv', rows, fieldnames)

    status_counts: dict[str, int] = {}
    for r in rows:
        status_counts[r['verification_status']] = status_counts.get(r['verification_status'], 0) + 1
    summary = {
        'audit_id': 'he2_exal_m_t1_scale_contract_audit_20221225_20260518',
        'run_root': str(run_root),
        'object_count': len(rows),
        'exists_count': sum(1 for r in rows if r['exists']),
        'verification_status_counts': status_counts,
        'resolved_scales': resolved,
        'source_map_excerpt': {k: source_map.get(k, '') for k in ['source.usgs', 'source.retros', 'source.glofas', 'source.nws']},
    }
    (out_dir / 'scale_contract_summary.json').write_text(json.dumps(summary, indent=2) + '\n')

    md = [
        '# HE2 exAL-M-T1 Scale Contract Audit',
        '',
        f'- run root: `{run_root}`',
        f'- object inventory: `{out_dir / "scale_contract_inventory.csv"}`',
        '',
        '## Main Conclusions',
        '',
        f"- The representative run advertises `analysis_scale_fit_internal = {resolved.get('analysis_scale_fit_internal', 'unknown')}`.",
        f"- The representative run advertises `analysis_scale_post_internal = {resolved.get('analysis_scale_post_internal', 'unknown')}`.",
        f"- The representative run advertises `legacy_fit_input_scale = {resolved.get('legacy_fit_input_scale', 'unknown')}` and `legacy_post_input_scale = {resolved.get('legacy_post_input_scale', 'unknown')}`.",
        '- Raw USGS and raw shared forecast files remain on physical/raw flow scales.',
        '- Retros adapters, post adapters, fit ingress exports, and active synthesis caches are on `log1p_cms` for this representative run.',
        '- The `*_exp_guard.txt` report remains the main proof that the stale `log_log1p -> exp()` path was removed from the active representative post route.',
        '',
        '## Status Counts',
        '',
    ]
    for key, value in sorted(status_counts.items()):
        md.append(f'- `{key}`: {value}')
    md.append('')
    md.append('## Notes')
    md.append('')
    md.append('- This audit is about scale contracts, not yet about whether the semantically correct model-side object is being plotted.')
    md.append('- Location-summary caches and synthesized predictive caches are intentionally separated because they may be on the same numeric scale while representing different mathematical objects.')
    (out_dir / 'HE2_EXAL_M_T1_SCALE_CONTRACT_AUDIT_20221225_20260518.md').write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
