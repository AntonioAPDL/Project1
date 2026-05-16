#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTICLE_ROOT = ROOT / 'Evironmetrics---REVISED-DOC-2'
DEFAULT_MULTIVAR_RUN_ROOT = Path(
    '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/'
    'multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512/'
    'runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep'
)
DEFAULT_UNIVAR_OUTPUT_ROOT = Path(
    '/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/'
    'multimodel_v8_univar_featurecov_he2_rerun_20260422/'
    'runs/multimodel_20221225_v8_univar_featurecov_he2_v1_exdqlm_univar/'
    'post/outputs/multimodel_20221225_v8_univar_featurecov_he2_v1_exdqlm_univar'
)
DEFAULT_OUT_ROOT = ROOT / 'reports' / 'current_model_output_support_contract_audit_20260516'

FIT_Q_FILES = [
    'fit/exdqlm_multivar/keep/q=05/outputs/DISC_variables_5_exAL_synth_DISC.RData',
    'fit/exdqlm_multivar/keep/q=20/outputs/DISC_variables_20_exAL_synth_DISC.RData',
    'fit/exdqlm_multivar/keep/q=35/outputs/DISC_variables_35_exAL_synth_DISC.RData',
    'fit/exdqlm_multivar/keep/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData',
    'fit/exdqlm_multivar/keep/q=65/outputs/DISC_variables_65_exAL_synth_DISC.RData',
    'fit/exdqlm_multivar/keep/q=80/outputs/DISC_variables_80_exAL_synth_DISC.RData',
    'fit/exdqlm_multivar/keep/q=95/outputs/DISC_variables_95_exAL_synth_DISC.RData',
]


def main() -> int:
    article_root = DEFAULT_ARTICLE_ROOT
    multivar_run_root = DEFAULT_MULTIVAR_RUN_ROOT
    univar_output_root = DEFAULT_UNIVAR_OUTPUT_ROOT
    out_root = DEFAULT_OUT_ROOT
    out_root.mkdir(parents=True, exist_ok=True)

    missing_fit = [str(multivar_run_root / rel) for rel in FIT_Q_FILES if not (multivar_run_root / rel).exists()]
    univar_png = univar_output_root / 'exdqlm_univar_synth_cutoff_window_posterior_samples.png'
    refresh_status = article_root / 'artifacts' / 'historical_support_from_current_models' / 'refresh_status.json'
    refresh_payload = json.loads(refresh_status.read_text(encoding='utf-8')) if refresh_status.exists() else {}

    payload = {
        'status': 'repair_open' if missing_fit else 'ready',
        'article_root': str(article_root),
        'multivar_run_root': str(multivar_run_root),
        'univar_output_root': str(univar_output_root),
        'missing_multivar_fit_artifacts': missing_fit,
        'univar_png_exists': univar_png.exists(),
        'refresh_status_json': str(refresh_status),
        'refresh_status': refresh_payload,
        'recommended_resolution': [
            'prefer a corrected retained support-cache artifact over an implicit fit-cache dependency',
            'keep the corrected setup/support, forecast-context, and cutoff-synthesis families authoritative',
            'treat the historical-support rebuild as a separate corrected-lineage repair lane until retained artifacts exist',
        ],
    }
    (out_root / 'current_model_output_support_contract_audit_20260516.json').write_text(
        json.dumps(payload, indent=2) + '\n',
        encoding='utf-8',
    )

    lines: list[str] = []
    lines.append('# Current-Model Output Support Contract Audit')
    lines.append('')
    lines.append('Date: 2026-05-16')
    lines.append('')
    lines.append('## Summary')
    lines.append('')
    lines.append(f"- status: `{payload['status']}`")
    lines.append(f"- multivariate corrected run root: `{multivar_run_root}`")
    lines.append(f"- univariate reference output root: `{univar_output_root}`")
    lines.append('')
    lines.append('## Findings')
    lines.append('')
    lines.append(f"- missing corrected multivariate fit-cache artifacts: `{len(missing_fit)}`")
    lines.append(f"- univariate reference synthesis PNG present: `{univar_png.exists()}`")
    if refresh_payload:
        lines.append(f"- latest refresh status: `{refresh_payload.get('status')}`")
        lines.append(f"- latest refresh return code: `{refresh_payload.get('returncode')}`")
    lines.append('')
    if missing_fit:
        lines.append('Missing fit-cache artifacts:')
        lines.append('')
        for item in missing_fit:
            lines.append(f'- `{item}`')
        lines.append('')
    lines.append('## Decision')
    lines.append('')
    lines.append('- the corrected article refresh should continue to treat setup/support, forecast-context, and synthesis families as authoritative')
    lines.append('- the historical-support rebuild must move to a retained corrected artifact contract rather than implicitly requiring fit caches to still exist')
    lines.append('- until that retained artifact exists, the frozen historical-support bundle is preserved with explicit status logging')
    lines.append('')
    lines.append('## Next repair step')
    lines.append('')
    lines.append('- choose between a dedicated retained support-cache artifact or a post-exported historical-support bundle for the corrected 2022-05-11 multivariate run')
    lines.append('')

    (out_root / 'CURRENT_MODEL_OUTPUT_SUPPORT_CONTRACT_AUDIT_20260516.md').write_text(
        '\n'.join(lines),
        encoding='utf-8',
    )
    print(out_root / 'CURRENT_MODEL_OUTPUT_SUPPORT_CONTRACT_AUDIT_20260516.md')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
