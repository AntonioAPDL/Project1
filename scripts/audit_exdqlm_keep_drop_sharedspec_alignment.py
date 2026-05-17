#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
KEEP_CONFIG_ROOT = Path(
    '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/'
    'multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/'
    'control/generated_configs'
)
DROP_CONFIG_ROOT = Path(
    '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/'
    'multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516/'
    'control/generated_configs'
)
OUT_ROOT = ROOT / 'reports' / 'he2_exdqlm_multivar_drop_shared_relaunch_plan_20260516'
OUT_JSON = OUT_ROOT / 'keep_drop_sharedspec_alignment.json'
OUT_MD = OUT_ROOT / 'KEEP_DROP_SHAREDSPEC_ALIGNMENT_20260516.md'
CUTOFFS = ['20210123', '20211112', '20211221', '20220511', '20221225']


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def _nested(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        cur = cur[key]
    return cur


def _drop_none_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _drop_none_values(child)
            for key, child in value.items()
            if child is not None
        }
    if isinstance(value, list):
        return [_drop_none_values(child) for child in value]
    return value


def _row_alignment(cutoff: str) -> dict[str, Any]:
    keep_cfg = _load_yaml(KEEP_CONFIG_ROOT / f'multimodel_{cutoff}_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml')
    drop_cfg = _load_yaml(DROP_CONFIG_ROOT / f'multimodel_{cutoff}_v8_he2pubgdpc1r1_exdqlm_multivar_drop.yaml')

    same_bundle_fields = {
        'canonical_bundle_root': _nested(keep_cfg, 'debug_he2_publication_relaunch', 'canonical_bundle_root')
        == _nested(drop_cfg, 'debug_he2_publication_relaunch', 'canonical_bundle_root'),
        'canonical_bundle_meta': _nested(keep_cfg, 'debug_he2_publication_relaunch', 'canonical_bundle_meta')
        == _nested(drop_cfg, 'debug_he2_publication_relaunch', 'canonical_bundle_meta'),
        'support_manifest': _nested(keep_cfg, 'debug_he2_publication_relaunch', 'support_manifest')
        == _nested(drop_cfg, 'debug_he2_publication_relaunch', 'support_manifest'),
        'fit_covariate_contract': _nested(keep_cfg, 'debug_he2_publication_relaunch', 'canonical_fit_covariate_contract')
        == _nested(drop_cfg, 'debug_he2_publication_relaunch', 'canonical_fit_covariate_contract'),
        'fit_covariate_paths': _nested(keep_cfg, 'inputs', 'fit', 'covariates')
        == _nested(drop_cfg, 'inputs', 'fit', 'covariates'),
        'deterministic_climate': _drop_none_values(keep_cfg['inputs']['deterministic_climate'])
        == _drop_none_values(drop_cfg['inputs']['deterministic_climate']),
    }

    same_spec_fields = {
        'forecast_cov': _nested(keep_cfg, 'fit', 'exdqlm_multivar', 'legacy', 'forecast_cov')
        == _nested(drop_cfg, 'fit', 'exdqlm_multivar', 'legacy', 'forecast_cov'),
        'state_evolution': _nested(keep_cfg, 'models', 'exdqlm_multivar', 'state_evolution')
        == _nested(drop_cfg, 'models', 'exdqlm_multivar', 'state_evolution'),
        'q50_override': _nested(keep_cfg, 'fit', 'exdqlm_multivar', 'gamma_sigma', 'quantile_overrides', 'q50')
        == _nested(drop_cfg, 'fit', 'exdqlm_multivar', 'gamma_sigma', 'quantile_overrides', 'q50'),
        'q35_override': _nested(keep_cfg, 'fit', 'exdqlm_multivar', 'gamma_sigma', 'quantile_overrides', 'q35')
        == _nested(drop_cfg, 'fit', 'exdqlm_multivar', 'gamma_sigma', 'quantile_overrides', 'q35'),
        'q65_override': _nested(keep_cfg, 'fit', 'exdqlm_multivar', 'gamma_sigma', 'quantile_overrides', 'q65')
        == _nested(drop_cfg, 'fit', 'exdqlm_multivar', 'gamma_sigma', 'quantile_overrides', 'q65'),
        'q80_override': _nested(keep_cfg, 'fit', 'exdqlm_multivar', 'gamma_sigma', 'quantile_overrides', 'q80')
        == _nested(drop_cfg, 'fit', 'exdqlm_multivar', 'gamma_sigma', 'quantile_overrides', 'q80'),
        'threads': _nested(keep_cfg, 'run', 'threads') == _nested(drop_cfg, 'run', 'threads'),
        'parallel_workers': _nested(keep_cfg, 'fit', 'parallel') == _nested(drop_cfg, 'fit', 'parallel'),
    }

    expected_differences = {
        'manuscript_label': {
            'keep': _nested(keep_cfg, 'debug_he2_publication_relaunch', 'manuscript_label'),
            'drop': _nested(drop_cfg, 'debug_he2_publication_relaunch', 'manuscript_label'),
        },
        'family': {
            'keep': _nested(keep_cfg, 'debug_he2_publication_relaunch', 'family'),
            'drop': _nested(drop_cfg, 'debug_he2_publication_relaunch', 'family'),
        },
        'forecast_transfer_mode': {
            'keep': _nested(keep_cfg, 'debug_he2_publication_relaunch', 'forecast_transfer_mode'),
            'drop': _nested(drop_cfg, 'debug_he2_publication_relaunch', 'forecast_transfer_mode'),
        },
        'run_id': {
            'keep': _nested(keep_cfg, 'run', 'run_id'),
            'drop': _nested(drop_cfg, 'run', 'run_id'),
        },
        'run_root': {
            'keep': _nested(keep_cfg, 'run', 'run_root'),
            'drop': _nested(drop_cfg, 'run', 'run_root'),
        },
    }

    return {
        'cutoff': cutoff,
        'same_bundle_fields': same_bundle_fields,
        'same_spec_fields': same_spec_fields,
        'expected_differences': expected_differences,
        'bundle_alignment_passed': all(same_bundle_fields.values()),
        'spec_alignment_passed': all(same_spec_fields.values()),
    }


def build_payload() -> dict[str, Any]:
    rows = [_row_alignment(cutoff) for cutoff in CUTOFFS]
    return {
        'cutoffs': rows,
        'all_bundle_fields_aligned': all(row['bundle_alignment_passed'] for row in rows),
        'all_spec_fields_aligned': all(row['spec_alignment_passed'] for row in rows),
    }


def write_outputs() -> dict[str, Any]:
    payload = build_payload()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')

    lines = ['# keep vs drop sharedspec alignment', '', '| Cutoff | Bundles | Spec |', '|---|---|---|']
    for row in payload['cutoffs']:
        lines.append(
            f"| `{row['cutoff']}` | `{'pass' if row['bundle_alignment_passed'] else 'fail'}` | `{'pass' if row['spec_alignment_passed'] else 'fail'}` |"
        )
    lines.extend(
        [
            '',
            f"- all bundle fields aligned: `{payload['all_bundle_fields_aligned']}`",
            f"- all shared spec fields aligned: `{payload['all_spec_fields_aligned']}`",
            '- expected differences are limited to manuscript label, family id, transfer mode, and run identity fields.',
            '',
        ]
    )
    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')
    return payload


def main() -> int:
    payload = write_outputs()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
