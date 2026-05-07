#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

FIGURE_NAMES = [
    'usgs.png',
    'precip_soilmoisture_climatePC1_faceted_labeled.png',
    'retrospective_log_discharge_plot_faceted.png',
    'forecats.png',
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('w') as log:
        log.write('+ ' + ' '.join(cmd) + '\n')
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def load_config(path: Path) -> dict:
    return json.loads(path.read_text())


def first_last_retros_dates(path: Path) -> tuple[str, str]:
    rows = list(csv.DictReader(path.open()))
    if not rows:
        raise RuntimeError(f'No rows found in {path}')
    date_key = 'Date' if 'Date' in rows[0] else 'date'
    return rows[0][date_key], rows[-1][date_key]


def build_policy_summary(entry: dict, bundle_meta: dict) -> dict:
    notes: list[str] = []
    gapfix = bundle_meta.get('processing', {}).get('gapfix')
    if gapfix and gapfix.get('applied'):
        notes.append(f"gapfix applied to {gapfix.get('source_id')} on {', '.join(gapfix.get('dates_filled', []))}")
    if entry['bundle_class'] == 'histfix_long_history_bundle':
        notes.append('histfix lineage should show nws_retro_v21 early support and nws_retro_v30 tail fill near cutoff')
    return {
        'bundle_class': entry['bundle_class'],
        'nws_policy_summary': entry['nws_policy_summary'],
        'glofas_policy_summary': entry['glofas_policy_summary'],
        'notes': '; '.join(notes),
        'bundle_run_id': bundle_meta.get('run', {}).get('run_id') or bundle_meta.get('run', {}).get('bundle_kind', ''),
    }


def build_input_hash_rows(entry: dict, support_start: str, plot_start: str, plot_end: str) -> list[dict]:
    selected = Path(entry['selected_run_root'])
    bundle = Path(entry['figure_bundle_root'])
    rows: list[dict] = []

    def add(label: str, path: Path) -> None:
        rows.append({
            'label': label,
            'path': str(path),
            'sha256': sha256(path),
            'bytes': path.stat().st_size,
        })

    add('selected_run_usgs_daily', selected / 'inputs/shared/usgs/usgs_daily.csv')
    add('selected_run_retros', selected / 'inputs/shared/retros/retros.csv')
    add('selected_run_nws_forecast', selected / 'inputs/shared/forecasts/nws_forecast.csv')
    add('selected_run_glofas_forecast', selected / 'inputs/shared/forecasts/glofas_forecast.csv')
    add('selected_run_cov_ppt', selected / 'inputs/shared/covariates/cov_01_PPT.csv')
    add('selected_run_cov_soil', selected / 'inputs/shared/covariates/cov_02_SOIL.csv')
    add('selected_run_cov_pca', selected / 'inputs/shared/covariates/cov_03_PCA.csv')
    add('selected_run_cov_features', selected / 'inputs/shared/covariates/covariate_features.csv')
    add('figure_bundle_meta', bundle / 'meta.yaml')
    if (bundle / 'snapshot_source_map.txt').exists():
        add('figure_bundle_snapshot_source_map', bundle / 'snapshot_source_map.txt')
    add('figure_bundle_retros_daily', bundle / 'inputs/retros_daily.csv')
    if (bundle / 'inputs/retros_source_lineage.csv').exists():
        add('figure_bundle_retros_source_lineage', bundle / 'inputs/retros_source_lineage.csv')
    add('figure_bundle_glofas_weighted_daily', bundle / 'inputs/glofas_weighted_daily.csv')
    add('figure_bundle_nws_weighted_daily', bundle / 'inputs/nws_weighted_daily.csv')
    add('figure_bundle_glofas_members', bundle / 'inputs/glofas_members.csv')
    add('figure_bundle_nws_members', bundle / 'inputs/nws_members.csv')
    if (bundle / 'retros.csv').exists():
        add('figure_bundle_retros_wide', bundle / 'retros.csv')
    if (bundle / 'glofas_forecast.csv').exists():
        add('figure_bundle_glofas_forecast', bundle / 'glofas_forecast.csv')
    if (bundle / 'nws_forecast.csv').exists():
        add('figure_bundle_nws_forecast', bundle / 'nws_forecast.csv')
    return rows


def write_cutoff_artifacts(entry: dict, bundle_meta: dict, support_start: str, support_end: str, slug_root: Path) -> None:
    meta_dir = slug_root / 'metadata'
    review_dir = slug_root / 'review'
    figures_dir = slug_root / 'figures'
    meta_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    (meta_dir / 'source_model_run.txt').write_text(entry['selected_run_root'] + '\n')
    (meta_dir / 'source_figure_bundle.txt').write_text(entry['figure_bundle_root'] + '\n')
    (meta_dir / 'cutoff_entry.json').write_text(json.dumps(entry, indent=2) + '\n')

    forecast_start_date = bundle_meta['dates'].get('forecast_start_date')
    if not forecast_start_date:
        cutoff_date = bundle_meta['dates']['cutoff_date']
        forecast_start_date = str(dt.date.fromisoformat(cutoff_date) + dt.timedelta(days=1))

    support_window = {
        'support_start': support_start,
        'support_end': support_end,
        'plot_start': bundle_meta['dates']['plot_start'],
        'plot_end': bundle_meta['dates']['plot_end'],
        'forecast_start_date': forecast_start_date,
    }
    yaml.safe_dump(support_window, (meta_dir / 'support_window.yaml').open('w'), sort_keys=False)
    yaml.safe_dump(build_policy_summary(entry, bundle_meta), (meta_dir / 'policy_summary.yaml').open('w'), sort_keys=False)

    hash_rows = build_input_hash_rows(entry, support_start, bundle_meta['dates']['plot_start'], bundle_meta['dates']['plot_end'])
    with (meta_dir / 'input_hashes.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['label', 'path', 'sha256', 'bytes'])
        for row in hash_rows:
            writer.writerow([row['label'], row['path'], row['sha256'], row['bytes']])

    with (review_dir / 'figure_manifest.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['figure_name', 'path', 'sha256', 'bytes'])
        for name in FIGURE_NAMES:
            p = figures_dir / name
            writer.writerow([name, str(p), sha256(p), p.stat().st_size])


def main() -> None:
    parser = argparse.ArgumentParser(description='Render the corrected exAL-M-T1 setup/support figures by cutoff.')
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1] / 'config' / 'exal_m_t1_setup_support_by_cutoff_v2_20260507.json')
    parser.add_argument('--output-root', type=Path, default=None)
    parser.add_argument('--slugs', nargs='*', default=None)
    parser.add_argument('--clean', action='store_true')
    parser.add_argument('--skip-review', action='store_true')
    parser.add_argument('--skip-validate', action='store_true')
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config = load_config(args.config.resolve())
    output_root = args.output_root.resolve() if args.output_root else Path(config['runtime_output_root']).resolve()
    wanted = set(args.slugs or [])

    if args.clean and output_root.exists() and not wanted:
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    render_script = project_root / 'scripts' / 'render_setup_support_bundle_v2.R'
    py = sys.executable

    for entry in config['cutoffs']:
        if wanted and entry['slug'] not in wanted:
            continue
        slug_root = output_root / entry['slug']
        if args.clean and slug_root.exists():
            shutil.rmtree(slug_root)
        (slug_root / 'figures').mkdir(parents=True, exist_ok=True)
        (slug_root / 'logs').mkdir(parents=True, exist_ok=True)

        selected_retros = Path(entry['selected_run_root']) / 'inputs' / 'shared' / 'retros' / 'retros.csv'
        support_start, support_end = first_last_retros_dates(selected_retros)
        if support_start != entry['support_start']:
            raise RuntimeError(
                f"Config support_start mismatch for {entry['slug']}: config={entry['support_start']} selected_run={support_start}"
            )
        if support_end != entry['cutoff_date']:
            raise RuntimeError(
                f"Selected-run cutoff mismatch for {entry['slug']}: config cutoff={entry['cutoff_date']} selected_run retros end={support_end}"
            )

        cmd = [
            'Rscript', '--vanilla', str(render_script),
            '--project-root', str(project_root),
            '--selected-run-root', entry['selected_run_root'],
            '--figure-bundle-root', entry['figure_bundle_root'],
            '--bundle-class', entry['bundle_class'],
            '--output-dir', str((slug_root / 'figures').resolve()),
            '--support-start', support_start,
            '--cutoff-date', entry['cutoff_date'],
        ]
        run(cmd, slug_root / 'logs' / 'render.log')

        bundle_meta = yaml.safe_load((Path(entry['figure_bundle_root']) / 'meta.yaml').read_text())
        write_cutoff_artifacts(entry, bundle_meta, support_start, support_end, slug_root)

    review_script = project_root / 'scripts' / 'build_exal_m_t1_setup_support_v2_review.py'
    validate_script = project_root / 'scripts' / 'validate_exal_m_t1_setup_support_v2.py'
    if not args.skip_review:
        subprocess.run([py, str(review_script), '--output-root', str(output_root)], check=True)
    if not args.skip_validate:
        validate_cmd = [py, str(validate_script), '--config', str(args.config.resolve()), '--output-root', str(output_root)]
        if wanted:
            validate_cmd.extend(['--slugs', *sorted(wanted)])
        subprocess.run(validate_cmd, check=True)

    readme = output_root / 'README.md'
    readme.write_text(
        '# exAL-M-T1 setup/support figures by cutoff (v2)\n\n'
        'This runtime family renders the corrected cutoff-specific setup/input/support figures from the CRPS-linked exAL-M-T1 run roots and the authoritative forecats/histfix bundles.\n\n'
        f'Config: `{args.config.resolve()}`\n\n'
        'Review outputs:\n'
        '- `review/REVIEW.md`\n'
        '- `review/gallery.html`\n'
        '- `review/figure_manifest.csv`\n'
    )
    print(f'Rendered exAL-M-T1 setup/support v2 family at {output_root}')


if __name__ == '__main__':
    main()
