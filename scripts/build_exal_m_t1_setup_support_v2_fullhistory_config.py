#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

CUTOFFS = [
    ('20210123_exal_m_t1', '2021-01-23'),
    ('20211112_exal_m_t1', '2021-11-12'),
    ('20211221_exal_m_t1', '2021-12-21'),
    ('20220511_exal_m_t1', '2022-05-11'),
    ('20221225_exal_m_t1', '2022-12-25'),
]


def _policy_summaries(bundle_meta: dict) -> tuple[str, str]:
    histfix = bundle_meta.get('histfix', {})
    nws = histfix.get('nws_source_policy', {})
    primary = nws.get('primary_source_id')
    tail = nws.get('tail_fill_source_id')
    if primary and tail:
        nws_summary = f'{primary} with {tail} tail fill after natural coverage end'
    elif primary:
        nws_summary = primary
    else:
        nws_summary = 'unknown'
    glofas_summary = histfix.get('glofas_source_id') or 'unknown'
    return nws_summary, glofas_summary


def build_config(runtime_root: Path, output_root: Path) -> dict:
    cutoffs = []
    for slug, cutoff_date in CUTOFFS:
        cutoff_token = cutoff_date.replace('-', '')
        cfg_path = runtime_root / 'control' / 'generated_configs' / f'multimodel_{cutoff_token}_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml'
        if not cfg_path.exists():
            raise FileNotFoundError(f'Missing generated config: {cfg_path}')
        cfg = yaml.safe_load(cfg_path.read_text())
        dbg = cfg['debug_he2_publication_relaunch']
        bundle_root = Path(dbg['canonical_bundle_root']).resolve()
        bundle_meta = yaml.safe_load((bundle_root / 'meta.yaml').read_text())
        nws_summary, glofas_summary = _policy_summaries(bundle_meta)
        selected_run_root = (runtime_root / 'runs' / cfg['run']['run_id']).resolve()
        cutoffs.append({
            'slug': slug,
            'cutoff_date': cutoff_date,
            'published_crps': dbg['publication_crps_display4'],
            'selected_run_root': str(selected_run_root),
            'figure_bundle_root': str(bundle_root),
            'bundle_class': 'histfix_long_history_bundle',
            'nws_policy_summary': nws_summary,
            'glofas_policy_summary': glofas_summary,
            'support_start': '1987-05-29',
        })
    return {
        'runtime_output_root': str(output_root),
        'representative_article_cutoff': '20221225_exal_m_t1',
        'history_start_date': '1987-05-29',
        'forecast_plot_pre_days': 28,
        'forecast_plot_post_days': 28,
        'flow_figure_display_scale': 'log1p_cms',
        'cutoffs': cutoffs,
    }


def build_report(config: dict, runtime_root: Path, report_root: Path) -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / 'config_snapshot.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    rows = [
        '# exAL-M-T1 Setup/Support Full-History Refresh Contract\n\n',
        f'- Source keep runtime root: `{runtime_root}`\n',
        f'- Output setup/support runtime root: `{config["runtime_output_root"]}`\n',
        '- History contract: `1987-05-29 -> cutoff` for USGS, PPT, SOIL, GDPC, and retrospective support\n',
        '- Figure-bundle lineage: canonical HE2 publication shared inputs (`20260510`)\n',
        '- Selected keep-model lineage anchor: completed `he2pubgdpc1r1` `exdqlm_multivar_keep` run roots from `20260512`\n\n',
        '| Cutoff | Selected keep run root | Canonical bundle root | NWS lineage | GloFAS lineage |\n',
        '|---|---|---|---|---|\n',
    ]
    for entry in config['cutoffs']:
        rows.append(
            f"| {entry['cutoff_date']} | `{entry['selected_run_root']}` | `{entry['figure_bundle_root']}` | `{entry['nws_policy_summary']}` | `{entry['glofas_policy_summary']}` |\n"
        )
    (report_root / 'EXAL_M_T1_SETUP_SUPPORT_FULLHISTORY_REFRESH_20260516.md').write_text(''.join(rows), encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description='Build the corrected full-history exAL-M-T1 setup/support config from the completed he2pubgdpc1r1 keep runtime.')
    parser.add_argument('--keep-runtime-root', type=Path, default=Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512'))
    parser.add_argument('--config-out', type=Path, default=Path(__file__).resolve().parents[1] / 'config' / 'exal_m_t1_setup_support_by_cutoff_v2_20260516.json')
    parser.add_argument('--output-root', type=Path, default=Path('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exal_m_t1_setup_support_by_cutoff_v2_20260516'))
    parser.add_argument('--report-root', type=Path, default=Path(__file__).resolve().parents[1] / 'reports' / 'exal_m_t1_setup_support_fullhistory_refresh_20260516')
    args = parser.parse_args()

    runtime_root = args.keep_runtime_root.resolve()
    config = build_config(runtime_root, args.output_root.resolve())
    args.config_out.parent.mkdir(parents=True, exist_ok=True)
    args.config_out.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    build_report(config, runtime_root, args.report_root.resolve())
    print(args.config_out)


if __name__ == '__main__':
    main()
