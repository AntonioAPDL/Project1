from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def parse_source_map(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        if '=' not in raw:
            continue
        k, v = raw.split('=', 1)
        out[k.strip()] = v.strip()
    return out


def index_by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {r[key]: r for r in rows if key in r and r[key]}


def safe_float(v: str | None) -> float | None:
    if v is None or v == '':
        return None
    try:
        x = float(v)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def fmt(v: float | None) -> str:
    if v is None or not math.isfinite(v):
        return ''
    return f'{v:.12f}'


def log1p_if_possible(v: float | None) -> float | None:
    if v is None or v < -1:
        return None
    return math.log1p(v)


def log_if_positive(v: float | None) -> float | None:
    if v is None or v <= 0:
        return None
    return math.log(v)


def mean_first_members(row: dict[str, str], prefixes: tuple[str, ...]) -> float | None:
    vals: list[float] = []
    for key in prefixes:
        v = safe_float(row.get(key))
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    return sum(vals) / len(vals)


def main() -> None:
    run_root = DEFAULT_RUN_ROOT
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    source_map = parse_source_map(run_root / 'inputs' / 'shared' / 'source_map.txt')
    raw_usgs = read_csv(Path(source_map['source.usgs']))
    shared_usgs = read_csv(run_root / 'inputs' / 'shared' / 'usgs' / 'usgs_daily.csv')
    shared_retros = read_csv(run_root / 'inputs' / 'shared' / 'retros' / 'retros.csv')
    post_retros = read_csv(run_root / 'post' / 'inputs' / 'retros_post_adapter.csv')
    fit_matrix = read_csv(run_root / 'post' / 'outputs' / run_root.name / 'data_cbind_tY_X.csv')
    fit_dates = read_csv(run_root / 'post' / 'outputs' / run_root.name / 'timestamps.csv')
    shared_glofas = read_csv(run_root / 'inputs' / 'shared' / 'forecasts' / 'glofas_forecast.csv')
    post_glofas = read_csv(run_root / 'post' / 'inputs' / 'glofas_post_adapter.csv')
    shared_nws = read_csv(run_root / 'inputs' / 'shared' / 'forecasts' / 'nws_forecast.csv')
    post_nws = read_csv(run_root / 'post' / 'inputs' / 'nws_post_adapter.csv')

    raw_idx = index_by(raw_usgs, 'date')
    shared_usgs_idx = index_by(shared_usgs, 'date')
    shared_retros_idx = index_by(shared_retros, 'Date')
    post_retros_idx = index_by(post_retros, 'Date')
    if len(fit_dates) != len(fit_matrix):
        raise ValueError(f'timestamps and fit matrix row counts differ: {len(fit_dates)} vs {len(fit_matrix)}')
    fit_idx = {d['x']: r for d, r in zip(fit_dates, fit_matrix)}
    shared_glofas_idx = index_by(shared_glofas, 'target_date')
    post_glofas_idx = index_by(post_glofas, 'target_date')
    shared_nws_idx = index_by(shared_nws, 'target_date')
    post_nws_idx = index_by(post_nws, 'target_date')

    last200_start = fit_dates[-200]['x']
    ref_dates = ['1987-05-29', '2012-01-01', '2017-01-01', last200_start, '2022-12-25']
    history_rows: list[dict[str, object]] = []
    for dt in ref_dates:
        raw_cms = safe_float((raw_idx.get(dt) or {}).get('discharge_cms'))
        shared_cms = safe_float((shared_usgs_idx.get(dt) or {}).get('discharge_cms'))
        derived_log1p = log1p_if_possible(raw_cms)
        derived_loglog1p = log_if_positive(derived_log1p)
        retros_usgs = safe_float((shared_retros_idx.get(dt) or {}).get('USGS'))
        post_usgs = safe_float((post_retros_idx.get(dt) or {}).get('USGS'))
        fit_usgs = safe_float((fit_idx.get(dt) or {}).get('USGS'))
        history_rows.append({
            'date': dt,
            'raw_usgs_cms': fmt(raw_cms),
            'shared_usgs_cms': fmt(shared_cms),
            'derived_log1p_from_raw': fmt(derived_log1p),
            'derived_log_of_log1p_from_raw': fmt(derived_loglog1p),
            'shared_retros_usgs_log1p': fmt(retros_usgs),
            'post_retros_usgs_log1p': fmt(post_usgs),
            'fit_ingress_usgs_exported': fmt(fit_usgs),
            'delta_shared_retros_vs_derived': fmt(None if derived_log1p is None or retros_usgs is None else retros_usgs - derived_log1p),
            'delta_post_retros_vs_derived': fmt(None if derived_log1p is None or post_usgs is None else post_usgs - derived_log1p),
            'delta_fit_vs_derived': fmt(None if derived_log1p is None or fit_usgs is None else fit_usgs - derived_log1p),
            'delta_fit_vs_loglog1p': fmt(None if derived_loglog1p is None or fit_usgs is None else fit_usgs - derived_loglog1p),
        })

    forecast_dates = ['2022-12-26', '2022-12-27', '2022-12-28']
    forecast_rows: list[dict[str, object]] = []
    for dt in forecast_dates:
        sg = shared_glofas_idx.get(dt, {})
        pg = post_glofas_idx.get(dt, {})
        sn = shared_nws_idx.get(dt, {})
        pn = post_nws_idx.get(dt, {})
        glofas_raw_m0 = safe_float(sg.get('member_00'))
        glofas_post_m0 = safe_float(pg.get('member_00'))
        nws_raw_m1 = safe_float(sn.get('member_01'))
        nws_post_m1 = safe_float(pn.get('member_01'))
        forecast_rows.append({
            'target_date': dt,
            'glofas_member_00_raw_cms': fmt(glofas_raw_m0),
            'glofas_member_00_log1p_expected': fmt(log1p_if_possible(glofas_raw_m0)),
            'glofas_member_00_log_raw_fit_code': fmt(log_if_positive(glofas_raw_m0)),
            'glofas_member_00_post_log1p': fmt(glofas_post_m0),
            'delta_glofas_post_vs_expected': fmt(None if glofas_raw_m0 is None or glofas_post_m0 is None else glofas_post_m0 - math.log1p(glofas_raw_m0)),
            'nws_member_01_raw_cms': fmt(nws_raw_m1),
            'nws_member_01_log1p_expected': fmt(log1p_if_possible(nws_raw_m1)),
            'nws_member_01_log_raw_fit_code': fmt(log_if_positive(nws_raw_m1)),
            'nws_member_01_post_log1p': fmt(nws_post_m1),
            'delta_nws_post_vs_expected': fmt(None if nws_raw_m1 is None or nws_post_m1 is None else nws_post_m1 - math.log1p(nws_raw_m1)),
            'glofas_mean_first3_raw_cms': fmt(mean_first_members(sg, ('member_00', 'member_01', 'member_02'))),
            'glofas_mean_first3_post_log1p': fmt(mean_first_members(pg, ('member_00', 'member_01', 'member_02'))),
            'nws_mean_first3_raw_cms': fmt(mean_first_members(sn, ('member_01', 'member_02', 'member_03'))),
            'nws_mean_first3_post_log1p': fmt(mean_first_members(pn, ('member_01', 'member_02', 'member_03'))),
        })

    response_contract_rows: list[dict[str, object]] = []
    all_loglog_exact = True
    for col in ('USGS', 'GloFAS', 'NWS3.0'):
        diffs_to_log1p: list[float] = []
        diffs_to_loglog: list[float] = []
        for src_row, fit_row in zip(shared_retros, fit_matrix):
            src = safe_float(src_row.get(col))
            fit_val = safe_float(fit_row.get(col))
            if src is None or fit_val is None:
                continue
            loglog = log_if_positive(src)
            diffs_to_log1p.append(abs(fit_val - src))
            if loglog is not None:
                diffs_to_loglog.append(abs(fit_val - loglog))
        max_diff_log1p = max(diffs_to_log1p) if diffs_to_log1p else None
        max_diff_loglog = max(diffs_to_loglog) if diffs_to_loglog else None
        exact_loglog = (max_diff_loglog is not None and max_diff_loglog < 1e-12)
        all_loglog_exact = all_loglog_exact and exact_loglog
        response_contract_rows.append({
            'series': col,
            'n_rows_checked': len(diffs_to_log1p),
            'max_abs_diff_fit_vs_shared_retros_log1p': fmt(max_diff_log1p),
            'max_abs_diff_fit_vs_log_of_shared_retros': fmt(max_diff_loglog),
            'fit_matches_log_of_shared_retros_exactly': exact_loglog,
        })

    hist_fields = list(history_rows[0].keys())
    fc_fields = list(forecast_rows[0].keys())
    write_csv(out_dir / 'prefit_history_lineage_reference_dates.csv', history_rows, hist_fields)
    write_csv(out_dir / 'prefit_forecast_member_transform_checks.csv', forecast_rows, fc_fields)
    write_csv(out_dir / 'prefit_response_contract_checks.csv', response_contract_rows, list(response_contract_rows[0].keys()))

    history_exact = all((r['delta_shared_retros_vs_derived'] in ('', '0.000000000000') and r['delta_fit_vs_derived'] in ('', '0.000000000000')) for r in history_rows)
    forecast_exact = all((r['delta_glofas_post_vs_expected'] in ('', '0.000000000000') and r['delta_nws_post_vs_expected'] in ('', '0.000000000000')) for r in forecast_rows)
    fit_matches_loglog = all(r['delta_fit_vs_loglog1p'] in ('', '-0.000000000000', '0.000000000000') for r in history_rows)
    summary = {
        'audit_id': 'he2_exal_m_t1_prefit_lineage_audit_20221225_20260518',
        'history_reference_dates': ref_dates,
        'forecast_reference_dates': forecast_dates,
        'history_transform_exact_match': history_exact,
        'forecast_member_transform_exact_match': forecast_exact,
        'fit_ingress_matches_log_of_log1p_history_response': fit_matches_loglog,
        'all_response_series_match_log_of_shared_retros_exactly': all_loglog_exact,
        'fit_forecast_codepath_uses_log_raw_members': True,
        'last200_start_date': last200_start,
    }
    (out_dir / 'prefit_lineage_summary.json').write_text(json.dumps(summary, indent=2) + '\n')

    md = [
        '# HE2 exAL-M-T1 Pre-Fit Lineage Audit',
        '',
        f'- run root: `{run_root}`',
        '',
        '## What This Checks',
        '',
        '- Raw USGS -> shared USGS -> shared retros -> post retros -> fit ingress for a small set of reference dates.',
        '- Shared forecast members -> post forecast adapters for GloFAS and NWS on the first three forecast days after cutoff.',
        '',
        '## Main Read',
        '',
        f'- history lineage exact-match flag: `{history_exact}`',
        f'- forecast member transform exact-match flag: `{forecast_exact}`',
        f'- fit ingress matches `log(log1p(raw USGS))` on sampled history dates: `{fit_matches_loglog}`',
        f'- all three retrospective response series match `log(shared_retros)` exactly across the full run: `{all_loglog_exact}`',
        '- active fit input code path applies `log(raw)` to forecast members and `log(log1p(raw))` to retrospective response series',
        f'- last-200 historical window starts at `{last200_start}`',
        '',
        '## Outputs',
        '',
        f'- history table: `{out_dir / "prefit_history_lineage_reference_dates.csv"}`',
        f'- forecast transform table: `{out_dir / "prefit_forecast_member_transform_checks.csv"}`',
        f'- response contract table: `{out_dir / "prefit_response_contract_checks.csv"}`',
    ]
    (out_dir / 'HE2_EXAL_M_T1_PREFIT_LINEAGE_AUDIT_20221225_20260518.md').write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
