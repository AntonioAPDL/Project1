from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd')
SUMMARY = ROOT / 'reports' / 'he2_exal_m_t1_20221225_reference_relaunch_20260518' / 'summary.json'
CFG = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime') / 'multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518' / 'control' / 'generated_configs' / 'multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml'


def test_reference_relaunch_summary_contract() -> None:
    summary = json.loads(SUMMARY.read_text())
    assert summary['status'] == 'prepared_not_launched'
    assert summary['candidate_max_iter'] == 200
    assert summary['current_max_iter'] == 100
    assert summary['candidate_epsilon'] == 30.0
    assert summary['cleanup_rdata_after_post'] is False
    assert summary['candidate_common_warmup_freeze_iters'] == 10
    assert summary['recommended_common_warmup_freeze_iters'] == 10
    assert summary['recommended_max_iter'] == 200


def test_reference_relaunch_generated_config_contract() -> None:
    cfg = yaml.safe_load(CFG.read_text())
    fit_mv = cfg['fit']['exdqlm_multivar']
    state = cfg['models']['exdqlm_multivar']['state_evolution']
    assert fit_mv['gamma_sigma']['max_iter'] == 200
    assert fit_mv['gamma_sigma']['warmup_freeze_iters'] == 10
    assert fit_mv['legacy']['forecast_cov']['epsilon'] == 30.0
    assert fit_mv['gamma_sigma']['quantile_overrides']['q35']['freeze_target'] == 'states'
    assert fit_mv['gamma_sigma']['quantile_overrides']['q35']['warmup_freeze_iters'] == 10
    assert fit_mv['gamma_sigma']['quantile_overrides']['q50']['warmup_freeze_iters'] == 10
    assert fit_mv['gamma_sigma']['quantile_overrides']['q50']['terminal_sampling_guard']['mode'] == 'fail_fast'
    assert state['df_s1'] == 0.99999
    assert state['df_discrep'] == 0.99999
    assert cfg['scale_contract']['analysis_scale_fit_internal'] == 'log1p_cms'
