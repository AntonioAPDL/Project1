#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path

import yaml

FIGURE_NAMES = [
    'usgs.png',
    'precip_soilmoisture_climatePC1_faceted_labeled.png',
    'retrospective_log_discharge_plot_faceted.png',
    'forecats.png',
]


def load_config(path: Path) -> dict:
    return json.loads(path.read_text())


def read_first_last_retros_date(path: Path) -> tuple[str, str]:
    rows = list(csv.DictReader(path.open()))
    if not rows:
        raise AssertionError(f'No rows found in {path}')
    date_key = 'Date' if 'Date' in rows[0] else 'date'
    return rows[0][date_key], rows[-1][date_key]


def ensure(path: Path, label: str) -> None:
    if not path.exists():
        raise AssertionError(f'Missing {label}: {path}')


def validate_cutoff(entry: dict, output_root: Path, config: dict) -> dict:
    slug_root = output_root / entry['slug']
    figures_dir = slug_root / 'figures'
    meta_dir = slug_root / 'metadata'
    review_dir = slug_root / 'review'
    logs_dir = slug_root / 'logs'

    for name in FIGURE_NAMES:
        ensure(figures_dir / name, f'figure {name}')
    for name in ['source_model_run.txt', 'source_figure_bundle.txt', 'policy_summary.yaml', 'support_window.yaml', 'coverage_audit.yaml', 'scale_contract.yaml', 'input_hashes.csv', 'cutoff_entry.json']:
        ensure(meta_dir / name, f'metadata {name}')
    ensure(logs_dir / 'render.log', 'render.log')
    ensure(review_dir / 'figure_manifest.csv', 'review manifest')

    source_model_run = (meta_dir / 'source_model_run.txt').read_text().strip()
    source_figure_bundle = (meta_dir / 'source_figure_bundle.txt').read_text().strip()
    if source_model_run != entry['selected_run_root']:
        raise AssertionError(f'{entry["slug"]}: source_model_run mismatch')
    if source_figure_bundle != entry['figure_bundle_root']:
        raise AssertionError(f'{entry["slug"]}: source_figure_bundle mismatch')

    support = yaml.safe_load((meta_dir / 'support_window.yaml').read_text())
    coverage = yaml.safe_load((meta_dir / 'coverage_audit.yaml').read_text())
    policy = yaml.safe_load((meta_dir / 'policy_summary.yaml').read_text())

    if support['support_end'] != entry['cutoff_date']:
        raise AssertionError(f'{entry["slug"]}: support_end {support["support_end"]} != cutoff_date {entry["cutoff_date"]}')

    cutoff_date = dt.date.fromisoformat(entry['cutoff_date'])
    expected_plot_start = (cutoff_date - dt.timedelta(days=config['forecast_plot_pre_days'])).isoformat()
    expected_plot_end = (cutoff_date + dt.timedelta(days=config['forecast_plot_post_days'])).isoformat()
    expected_forecast_start = (cutoff_date + dt.timedelta(days=1)).isoformat()
    if support['support_start'] != config['history_start_date']:
        raise AssertionError(f'{entry["slug"]}: support_start {support["support_start"]} != requested history start {config["history_start_date"]}')
    if support['history_start_requested'] != config['history_start_date']:
        raise AssertionError(f'{entry["slug"]}: history_start_requested mismatch')
    if support['plot_start'] != expected_plot_start:
        raise AssertionError(f'{entry["slug"]}: plot_start {support["plot_start"]} != expected {expected_plot_start}')
    if support['plot_end'] != expected_plot_end:
        raise AssertionError(f'{entry["slug"]}: plot_end {support["plot_end"]} != expected {expected_plot_end}')
    if support['forecast_start_date'] != expected_forecast_start:
        raise AssertionError(f'{entry["slug"]}: forecast_start_date {support["forecast_start_date"]} != expected {expected_forecast_start}')
    if int(support['forecast_plot_pre_days']) != int(config['forecast_plot_pre_days']):
        raise AssertionError(f'{entry["slug"]}: forecast_plot_pre_days mismatch')
    if int(support['forecast_plot_post_days']) != int(config['forecast_plot_post_days']):
        raise AssertionError(f'{entry["slug"]}: forecast_plot_post_days mismatch')

    for key in ['usgs', 'ppt', 'soil', 'pca']:
        if coverage[key]['available_start'] != config['history_start_date']:
            raise AssertionError(f'{entry["slug"]}: {key} available_start {coverage[key]["available_start"]} != requested history start')
        if int(coverage[key]['missing_days_requested_window']) != 0:
            raise AssertionError(f'{entry["slug"]}: {key} has missing requested-window days')
        if not bool(coverage[key]['full_history_available']):
            raise AssertionError(f'{entry["slug"]}: {key} should have full history available')

    retro = coverage['retrospective']
    if support['retrospective_available_start'] != retro['available_start']:
        raise AssertionError(f'{entry["slug"]}: retrospective support window start does not match coverage audit')
    if int(retro['missing_days_available_window']) != 0:
        raise AssertionError(f'{entry["slug"]}: retrospective has missing days within available window')

    if entry['bundle_class'] == 'short_window_synth_bundle' and 'nws_synth_retro_ens_mean' not in policy['nws_policy_summary']:
        raise AssertionError(f'{entry["slug"]}: missing synthetic-retro marker in NWS policy')
    if entry['bundle_class'] == 'histfix_long_history_bundle':
        npol = policy['nws_policy_summary']
        if 'nws_retro_v21' not in npol or 'nws_retro_v30' not in npol:
            raise AssertionError(f'{entry["slug"]}: histfix NWS policy summary incomplete')
        if not bool(retro['full_history_available']):
            raise AssertionError(f'{entry["slug"]}: histfix cutoff should have full retrospective history available')
    else:
        if bool(retro['full_history_available']):
            raise AssertionError(f'{entry["slug"]}: short-window cutoff should not report full retrospective history available')

    rows = list(csv.DictReader((review_dir / 'figure_manifest.csv').open()))
    if len(rows) != 4:
        raise AssertionError(f'{entry["slug"]}: expected 4 figure manifest rows, found {len(rows)}')
    names = sorted(row['figure_name'] for row in rows)
    if names != sorted(FIGURE_NAMES):
        raise AssertionError(f'{entry["slug"]}: figure manifest names mismatch {names}')

    return {
        'slug': entry['slug'],
        'cutoff_date': entry['cutoff_date'],
        'status': 'PASS',
        'support_start': support['support_start'],
        'retrospective_available_start': support['retrospective_available_start'],
        'plot_start': support['plot_start'],
        'plot_end': support['plot_end'],
        'forecast_start_date': support['forecast_start_date'],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Validate corrected exAL-M-T1 setup/support v2 outputs.')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--slugs', nargs='*', default=None)
    args = parser.parse_args()

    config = load_config(args.config.resolve())
    output_root = args.output_root.resolve()
    wanted = set(args.slugs or [])
    rows = []
    for entry in config['cutoffs']:
        if wanted and entry['slug'] not in wanted:
            continue
        rows.append(validate_cutoff(entry, output_root, config))

    print('Validated exAL-M-T1 setup/support v2 outputs:')
    for row in rows:
        print(
            f"- {row['cutoff_date']} ({row['slug']}): PASS | requested history {row['support_start']} -> {row['cutoff_date']} | "
            f"retros available from {row['retrospective_available_start']} | forecast window {row['plot_start']} -> {row['plot_end']}"
        )


if __name__ == '__main__':
    main()
