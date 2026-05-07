#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
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

INPUT_REL_PATHS = [
    'inputs/shared/usgs/usgs_daily.csv',
    'inputs/shared/retros/retros.csv',
    'inputs/shared/forecasts/nws_forecast.csv',
    'inputs/shared/forecasts/glofas_forecast.csv',
    'inputs/shared/covariates/cov_01_PPT.csv',
    'inputs/shared/covariates/cov_02_SOIL.csv',
    'inputs/shared/covariates/cov_03_PCA.csv',
    'inputs/shared/covariates/covariate_features.csv',
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('w') as log:
        log.write('+ ' + ' '.join(cmd) + '\n')
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def load_config(path: Path) -> dict:
    return json.loads(path.read_text())


def only_run_dir(runs_dir: Path) -> Path:
    children = sorted([p for p in runs_dir.iterdir() if p.is_dir()])
    if len(children) != 1:
        raise RuntimeError(f'Expected exactly one run directory in {runs_dir}, found {len(children)}')
    return children[0]


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build_review(outputs_root: Path, records: list[dict]) -> None:
    review_dir = outputs_root / 'review'
    review_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = review_dir / 'figure_manifest.csv'
    with manifest_path.open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow([
            'cutoff_slug', 'cutoff_date', 'run_id', 'figure_name', 'figure_path', 'sha256', 'bytes',
            'plot_start', 'plot_end', 'forecast_start_date'
        ])
        for rec in records:
            for fig in rec['figures']:
                writer.writerow([
                    rec['slug'], rec['cutoff_date'], rec['run_id'], fig['name'], fig['path'], fig['sha256'], fig['bytes'],
                    rec['plot_start'], rec['plot_end'], rec['forecast_start_date']
                ])

    md_lines = [
        '# exAL-M-T1 Setup/Support Figures by Cutoff\n',
        '\n',
        'This bundle contains the cutoff-specific setup/input/support figures derived from the five verified exAL-M-T1 publication replay runs.\n',
        '\n',
        '## Cutoff summary\n',
        '| Cutoff | Slug | Run ID | Plot window | Forecast starts | Source run root |\n',
        '|---|---|---|---|---|---|\n',
    ]
    for rec in records:
        md_lines.append(
            f"| {rec['cutoff_date']} | `{rec['slug']}` | `{rec['run_id']}` | {rec['plot_start']} to {rec['plot_end']} | {rec['forecast_start_date']} | `{rec['source_run_root']}` |\n"
        )
    md_lines.append('\n')
    md_lines.append('## Figures\n')
    for rec in records:
        md_lines.append(f"### {rec['cutoff_date']}\n")
        md_lines.append('| Figure | File | SHA256 | Size bytes |\n')
        md_lines.append('|---|---|---|---:|\n')
        for fig in rec['figures']:
            rel = Path(fig['path']).relative_to(outputs_root)
            md_lines.append(f"| `{fig['name']}` | `{rel.as_posix()}` | `{fig['sha256']}` | {fig['bytes']} |\n")
        md_lines.append('\n')
    (review_dir / 'REVIEW.md').write_text(''.join(md_lines))

    html = [
        '<!doctype html><html><head><meta charset="utf-8"><title>exAL-M-T1 Setup/Support Review</title>',
        '<style>body{font-family:Arial,sans-serif;margin:24px;} h1,h2,h3{margin-bottom:8px;} .cutoff{margin-top:36px;} .grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;} .card{border:1px solid #ddd;border-radius:8px;padding:12px;background:#fff;} img{max-width:100%;height:auto;border:1px solid #eee;} .meta{font-size:13px;color:#333;line-height:1.4;} code{background:#f4f4f4;padding:2px 4px;border-radius:4px;}</style></head><body>',
        '<h1>exAL-M-T1 Setup/Support Figures by Cutoff</h1>',
        '<p>These figures are rendered from the verified run-scoped input bundles used by the five publication exAL-M-T1 cutoffs.</p>'
    ]
    for rec in records:
        html.append(f'<div class="cutoff"><h2>{rec["cutoff_date"]}</h2>')
        html.append(f'<p class="meta"><strong>Run:</strong> <code>{rec["run_id"]}</code><br><strong>Plot window:</strong> {rec["plot_start"]} to {rec["plot_end"]}<br><strong>Forecast starts:</strong> {rec["forecast_start_date"]}</p>')
        html.append('<div class="grid">')
        for fig in rec['figures']:
            rel = Path(os.path.relpath(fig['path'], review_dir))
            html.append('<div class="card">')
            html.append(f'<h3>{fig["name"]}</h3>')
            html.append(f'<p class="meta"><strong>SHA256:</strong> <code>{fig["sha256"][:16]}...</code><br><strong>Bytes:</strong> {fig["bytes"]}</p>')
            html.append(f'<img src="{rel.as_posix()}" alt="{fig["name"]}">')
            html.append('</div>')
        html.append('</div></div>')
    html.append('</body></html>')
    (review_dir / 'gallery.html').write_text(''.join(html))


def main() -> None:
    parser = argparse.ArgumentParser(description='Render cutoff-specific setup/support figures for the five verified exAL-M-T1 replay runs.')
    parser.add_argument('--workflow-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1] / 'config' / 'exal_m_t1_setup_support_by_cutoff_20260506.json')
    parser.add_argument('--output-root', type=Path, default=None)
    parser.add_argument('--clean', action='store_true', help='Remove the derived output root before rendering.')
    args = parser.parse_args()

    workflow_root = args.workflow_root.resolve()
    config = load_config(args.config.resolve())
    replay_root = Path(config['runtime_replay_root']).resolve()
    output_root = (args.output_root.resolve() if args.output_root else Path(config['derived_output_root']).resolve())

    if args.clean and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    render_script = workflow_root / 'scripts' / 'render_setup_support_figures.R'
    py = sys.executable

    for item in config['cutoffs']:
        slug = item['slug']
        slug_root = replay_root / slug
        run_root = only_run_dir(slug_root / 'runs')
        resolved_cfg = yaml.safe_load((run_root / 'resolved_config.yaml').read_text())
        cutoff_date = resolved_cfg['dates']['cutoff_date']
        plot_start = resolved_cfg['dates']['plot_start']
        plot_end = resolved_cfg['dates']['plot_end']
        forecast_start_date = item.get('forecast_start_date') or str(Path())
        if not forecast_start_date:
            forecast_start_date = str(Path())

        out_dir = output_root / slug
        figures_dir = out_dir / 'figures'
        inputs_dir = out_dir / 'inputs'
        logs_dir = out_dir / 'logs'
        review_dir = out_dir / 'review'
        for d in [figures_dir, inputs_dir, logs_dir, review_dir]:
            d.mkdir(parents=True, exist_ok=True)

        cmd = [
            'Rscript', '--vanilla', str(render_script),
            '--project-root', str(workflow_root),
            '--run-root', str(run_root),
            '--output-dir', str(figures_dir),
            '--cutoff-date', str(cutoff_date),
            '--forecast-start-date', str(item.get('forecast_start_date') or resolved_cfg['dates'].get('forecast_start_date') or ''),
            '--plot-start', str(plot_start),
            '--plot-end', str(plot_end),
            '--event-date', str(item.get('event_date') or ''),
            '--event-label', str(item.get('event_label') or ''),
        ]
        run(cmd, logs_dir / 'render.log')

        copy_file(run_root / 'inputs' / 'shared' / 'source_map.txt', inputs_dir / 'source_map.txt')
        copy_file(run_root / 'resolved_config.yaml', inputs_dir / 'resolved_config.yaml')
        copy_file(run_root / 'report' / 'summary.json', inputs_dir / 'summary.json')
        copy_file(run_root / 'validate' / 'compare_report.json', inputs_dir / 'compare_report.json')
        (inputs_dir / 'source_run_root.txt').write_text(str(run_root) + '\n')
        metadata = {
            'slug': slug,
            'cutoff_date': cutoff_date,
            'plot_start': plot_start,
            'plot_end': plot_end,
            'forecast_start_date': item.get('forecast_start_date') or resolved_cfg['dates'].get('forecast_start_date'),
            'event_date': item.get('event_date'),
            'event_label': item.get('event_label'),
            'run_id': run_root.name,
        }
        (inputs_dir / 'cutoff_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')

        with (inputs_dir / 'shared_input_hashes.csv').open('w', newline='') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(['relative_path', 'sha256', 'bytes'])
            for rel in INPUT_REL_PATHS:
                p = run_root / rel
                writer.writerow([rel, sha256(p), p.stat().st_size])

        figures = []
        with (review_dir / 'figure_manifest.csv').open('w', newline='') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(['figure_name', 'path', 'sha256', 'bytes'])
            for name in FIGURE_NAMES:
                p = figures_dir / name
                if not p.exists():
                    raise FileNotFoundError(f'Missing rendered figure: {p}')
                info = {'name': name, 'path': str(p), 'sha256': sha256(p), 'bytes': p.stat().st_size}
                figures.append(info)
                writer.writerow([name, str(p), info['sha256'], info['bytes']])
        review_lines = [
            f'# {cutoff_date} setup/support figures\n',
            '\n',
            f'- slug: `{slug}`\n',
            f'- run_id: `{run_root.name}`\n',
            f'- plot window: `{plot_start}` to `{plot_end}`\n',
            f'- forecast starts: `{metadata["forecast_start_date"]}`\n',
            '\n',
            '## Figures\n',
            '| Figure | SHA256 | Bytes |\n',
            '|---|---|---:|\n',
        ]
        for fig in figures:
            review_lines.append(f"| `{fig['name']}` | `{fig['sha256']}` | {fig['bytes']} |\n")
        (review_dir / 'review_notes.md').write_text(''.join(review_lines))

        records.append({
            'slug': slug,
            'cutoff_date': cutoff_date,
            'plot_start': plot_start,
            'plot_end': plot_end,
            'forecast_start_date': metadata['forecast_start_date'],
            'run_id': run_root.name,
            'source_run_root': str(run_root),
            'figures': figures,
        })

    build_review(output_root, records)
    readme = output_root / 'README.md'
    readme.write_text(
        '# exAL-M-T1 setup/support figures by cutoff\n\n'
        'This derived runtime family renders the four cutoff-dependent setup/input/support figures from the five verified exAL-M-T1 publication replay runs.\n\n'
        'Canonical source config: `config/exal_m_t1_setup_support_by_cutoff_20260506.json`\n\n'
        'Review outputs:\n'
        '- `review/REVIEW.md`\n'
        '- `review/gallery.html`\n'
        '- `review/figure_manifest.csv`\n'
    )
    print(f'Rendered setup/support cutoff family successfully at {output_root}')


if __name__ == '__main__':
    main()
