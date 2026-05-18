from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports' / 'he2_exal_m_t1_end_to_end_audit_20221225_20260518'


def test_he2_exal_m_t1_end_to_end_audit_builders() -> None:
    subprocess.run(['python3', 'scripts/build_he2_exal_m_t1_scale_contract_audit.py'], cwd=ROOT, check=True)
    subprocess.run(['python3', 'scripts/build_he2_exal_m_t1_prefit_lineage_audit.py'], cwd=ROOT, check=True)
    subprocess.run(['python3', 'scripts/build_he2_exal_m_t1_object_semantics_codepath_audit.py'], cwd=ROOT, check=True)
    subprocess.run(['python3', 'scripts/build_he2_exal_m_t1_final_diagnosis.py'], cwd=ROOT, check=True)
    subprocess.run(['python3', 'scripts/build_he2_exal_m_t1_end_to_end_audit_status.py'], cwd=ROOT, check=True)

    scale_summary = json.loads((OUT / 'scale_contract_summary.json').read_text())
    prefit_summary = json.loads((OUT / 'prefit_lineage_summary.json').read_text())
    status_summary = json.loads((OUT / 'status_summary.json').read_text())

    assert scale_summary['object_count'] >= 15
    assert scale_summary['resolved_scales']['analysis_scale_fit_internal'] == 'log1p_cms'
    assert scale_summary['resolved_scales']['analysis_scale_post_internal'] == 'log1p_cms'

    assert prefit_summary['last200_start_date'] == '2022-06-09'
    assert prefit_summary['history_transform_exact_match'] is False
    assert prefit_summary['forecast_member_transform_exact_match'] is False
    assert prefit_summary['fit_ingress_matches_log_of_log1p_history_response'] is True
    assert prefit_summary['all_response_series_match_log_of_shared_retros_exactly'] is True
    assert prefit_summary['fit_forecast_codepath_uses_log_raw_members'] is True

    status = status_summary['status']
    assert status['scale_contract_audit'] == 'done'
    assert status['pre_fit_lineage_audit'] == 'done'
    assert status['object_semantics_decomposition'] == 'done'
    assert status['final_diagnosis_memo'] == 'done'

    history_rows = list(csv.DictReader((OUT / 'prefit_history_lineage_reference_dates.csv').open()))
    first = history_rows[0]
    assert first['date'] == '1987-05-29'
    assert first['delta_shared_retros_vs_derived'] == '-0.000000000000'
    assert first['delta_fit_vs_derived'] != '0.000000000000'
    assert first['delta_fit_vs_loglog1p'] in ('-0.000000000000', '0.000000000000')

    response_rows = list(csv.DictReader((OUT / 'prefit_response_contract_checks.csv').open()))
    assert [r['series'] for r in response_rows] == ['USGS', 'GloFAS', 'NWS3.0']
    assert all(r['fit_matches_log_of_shared_retros_exactly'] == 'True' for r in response_rows)

    scale_rows = list(csv.DictReader((OUT / 'scale_contract_inventory.csv').open()))
    fit_row = next(r for r in scale_rows if r['object_id'] == 'fit_ingress_matrix')
    assert fit_row['intended_scale'] == 'log1p_cms'
    assert fit_row['actual_scale_assessment'] == 'log1p_cms'
