#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_MANIFEST_CSV = ROOT / 'reports' / 'he2_publication_manifest' / 'he2_bayesian_publication_manifest.csv'
DEFAULT_BUNDLE_ARTIFACT_ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510')
DEFAULT_RELAUNCH_ARTIFACT_ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_20260510')
DEFAULT_BUNDLE_RUN_ID = '20260510_publication_shared_r01'
DEFAULT_DATA_START = '1987-05-29'
DEFAULT_CAMPAIGN_SPEC_ID = 'he2pubgdpc1r1'
EXPECTED_CUTOFFS = ['20210123', '20211112', '20211221', '20220511', '20221225']
EXPECTED_CUTOFF_TO_DATE = OrderedDict([
    ('20210123', '2021-01-23'),
    ('20211112', '2021-11-12'),
    ('20211221', '2021-12-21'),
    ('20220511', '2022-05-11'),
    ('20221225', '2022-12-25'),
])
EXPECTED_FAMILY_ORDER = [
    'ndlm_univar_keep',
    'ndlm_main_drop',
    'ndlm_main_keep',
    'dqlm_univar_al',
    'dqlm_multivar_al_drop',
    'dqlm_multivar_al_keep',
    'exdqlm_univar',
    'exdqlm_multivar_drop',
    'exdqlm_multivar_keep',
]
EXPECTED_MANUSCRIPT_LABEL_ORDER = [
    'N-U-T1',
    'N-M-T0',
    'N-M-T1',
    'AL-U-T1',
    'AL-M-T0',
    'AL-M-T1',
    'exAL-U-T1',
    'exAL-M-T0',
    'exAL-M-T1',
]
AUTHORITATIVE_COMPARE_BY_CUTOFF = {
    '20210123': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/reports/multimodel_20210123_v8_epsTT_compare'),
    '20211112': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/reports/multimodel_20211112_v8_epsTT_compare'),
    '20211221': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407/reports/multimodel_20211221_v8_epsTT_compare'),
    '20220511': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407/reports/multimodel_20220511_v8_epsTT_compare'),
    '20221225': Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/reports/multimodel_20221225_v8_epsTT_compare'),
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f'YAML root is not a mapping: {path}')
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open('w', encoding='utf-8') as handle:
        yaml.safe_dump(data, handle, sort_keys=False, default_flow_style=False)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def family_rank(family: str) -> int:
    try:
        return EXPECTED_FAMILY_ORDER.index(family)
    except ValueError:
        return len(EXPECTED_FAMILY_ORDER)


def label_rank(label: str) -> int:
    try:
        return EXPECTED_MANUSCRIPT_LABEL_ORDER.index(label)
    except ValueError:
        return len(EXPECTED_MANUSCRIPT_LABEL_ORDER)


def row_kind(family: str) -> str:
    if family.startswith('ndlm_'):
        return 'ndlm'
    if 'univar' in family:
        return 'quantile_univariate'
    return 'quantile_multivariate'


def submodel_count(family: str) -> int:
    return 1 if family.startswith('ndlm_') else 7


def bundle_cutoff_date(cutoff: str) -> str:
    return EXPECTED_CUTOFF_TO_DATE[cutoff]


def bundle_root(bundle_artifact_root: str | Path, cutoff: str, bundle_run_id: str) -> Path:
    artifact_root = Path(bundle_artifact_root).resolve()
    cutoff_date = bundle_cutoff_date(cutoff)
    return artifact_root / 'stable_inputs' / 'site=11160500' / f'cutoff_date={cutoff_date}' / f'run_id={bundle_run_id}'


def bundle_meta_path(bundle_artifact_root: str | Path, cutoff: str, bundle_run_id: str) -> Path:
    return bundle_root(bundle_artifact_root, cutoff, bundle_run_id) / 'meta.yaml'


def support_root(bundle_artifact_root: str | Path) -> Path:
    return Path(bundle_artifact_root).resolve() / 'supporting_inputs'


def canonical_shared_paths(bundle_artifact_root: str | Path, cutoff: str, bundle_run_id: str) -> dict[str, Path]:
    root = bundle_root(bundle_artifact_root, cutoff, bundle_run_id)
    support = support_root(bundle_artifact_root)
    return {
        'bundle_root': root,
        'bundle_meta': root / 'meta.yaml',
        'parameters': support / 'parameters' / 'parameters.txt',
        'retros': root / 'retros.csv',
        'nws_forecast': root / 'nws_forecast.csv',
        'glofas_forecast': root / 'glofas_forecast.csv',
        'cov_eli': support / 'covariates' / 'cov_01_ELI.csv',
        'cov_oni': support / 'covariates' / 'cov_02_ONI.csv',
        'cov_ppt': support / 'covariates' / 'cov_03_PPT.csv',
        'cov_soil': support / 'covariates' / 'cov_04_SOIL.csv',
        'cov_pca': support / 'covariates' / 'cov_05_PCA.csv',
        'support_manifest': support / 'support_manifest.json',
    }


def load_publication_manifest_rows(path: Path | None = None) -> list[dict[str, str]]:
    manifest_path = path or PUBLICATION_MANIFEST_CSV
    rows = read_csv_rows(manifest_path)
    rows.sort(key=lambda row: (EXPECTED_CUTOFFS.index(row['cutoff']), label_rank(row['manuscript_label']), family_rank(row['family'])))
    return rows


def publication_row_map_by_cutoff_label(path: Path | None = None) -> dict[tuple[str, str], dict[str, str]]:
    rows = load_publication_manifest_rows(path)
    return {(row['cutoff'], row['manuscript_label']): row for row in rows}


def selected_window_retros_by_cutoff(path: Path | None = None, manuscript_label: str = 'exAL-M-T1') -> dict[str, Path]:
    rows = load_publication_manifest_rows(path)
    out: dict[str, Path] = {}
    for row in rows:
        if row['manuscript_label'] != manuscript_label:
            continue
        run_root = Path(row['run_root'])
        retros = run_root / 'inputs' / 'shared' / 'retros' / 'retros.csv'
        if retros.exists():
            out[row['cutoff']] = retros
    return out


def spec_token(row: dict[str, str]) -> str:
    campaign = row['campaign_lineage']
    run_id = row['run_id']
    if campaign.startswith('featurecov_cf1_eps_sweep_20260416'):
        for part in run_id.split('_'):
            if part.startswith('eps') and part.endswith('cf1'):
                return part
        return 'featurecov_cf1_selected'
    if campaign.startswith('exalm_t1_discount_grid_exact_20260424'):
        if '_set' in run_id:
            return 'set' + run_id.split('_set', 1)[1].split('_', 1)[0]
        return 'set09'
    if campaign.startswith('univar_featurecov_he2_rerun_20260422'):
        return 'univar_featurecov_he2_v1'
    if campaign.startswith('ndlm_featurecov_rerun_postfix_20260421'):
        return 'ndlm_featurecov_v1_postfix'
    return campaign
