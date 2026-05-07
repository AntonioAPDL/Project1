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


def validate_cutoff(entry: dict, output_root: Path) -> dict:
    slug_root = output_root / entry['slug']
    figures_dir = slug_root / 'figures'
    meta_dir = slug_root / 'metadata'
    review_dir = slug_root / 'review'
    logs_dir = slug_root / 'logs'

    for name in FIGURE_NAMES:
        ensure(figures_dir / name, f'figure {name}')
    for name in ['source_model_run.txt', 'source_figure_bundle.txt', 'policy_summary.yaml', 'support_window.yaml', 'input_hashes.csv', 'cutoff_entry.json']:
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
    policy = yaml.safe_load((meta_dir / 'policy_summary.yaml').read_text())

    first_date, last_date = read_first_last_retros_date(Path(entry['selected_run_root']) / 'inputs' / 'shared' / 'retros' / 'retros.csv')
    if support['support_start'] != first_date:
        raise AssertionError(f'{entry["slug"]}: support_start {support["support_start"]} != selected-run retros start {first_date}')
    if support['support_end'] != entry['cutoff_date']:
        raise AssertionError(f'{entry["slug"]}: support_end {support["support_end"]} != cutoff_date {entry["cutoff_date"]}')
    if last_date != entry['cutoff_date']:
        raise AssertionError(f'{entry["slug"]}: selected-run retros end {last_date} != cutoff_date {entry["cutoff_date"]}')

    bundle_meta = yaml.safe_load((Path(entry['figure_bundle_root']) / 'meta.yaml').read_text())
    forecast_start_date = bundle_meta['dates'].get('forecast_start_date')
    if not forecast_start_date:
        forecast_start_date = str(dt.date.fromisoformat(bundle_meta['dates']['cutoff_date']) + dt.timedelta(days=1))
    if support['plot_start'] != bundle_meta['dates']['plot_start']:
        raise AssertionError(f'{entry["slug"]}: plot_start mismatch with bundle meta')
    if support['plot_end'] != bundle_meta['dates']['plot_end']:
        raise AssertionError(f'{entry["slug"]}: plot_end mismatch with bundle meta')
    if support['forecast_start_date'] != forecast_start_date:
        raise AssertionError(f'{entry["slug"]}: forecast_start_date mismatch with bundle meta')

    if entry['bundle_class'] == 'short_window_synth_bundle' and 'nws_synth_retro_ens_mean' not in policy['nws_policy_summary']:
        raise AssertionError(f'{entry["slug"]}: missing synthetic-retro marker in NWS policy')
    if entry['bundle_class'] == 'histfix_long_history_bundle':
        npol = policy['nws_policy_summary']
        if 'nws_retro_v21' not in npol or 'nws_retro_v30' not in npol:
            raise AssertionError(f'{entry["slug"]}: histfix NWS policy summary incomplete')

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
        rows.append(validate_cutoff(entry, output_root))

    print('Validated exAL-M-T1 setup/support v2 outputs:')
    for row in rows:
        print(f"- {row['cutoff_date']} ({row['slug']}): PASS | support {row['support_start']} -> {row['cutoff_date']} | forecast window {row['plot_start']} -> {row['plot_end']}")


if __name__ == '__main__':
    main()
