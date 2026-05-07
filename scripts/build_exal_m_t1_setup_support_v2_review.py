#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import os
from pathlib import Path

FIGURE_NAMES = [
    'usgs.png',
    'precip_soilmoisture_climatePC1_faceted_labeled.png',
    'retrospective_log_discharge_plot_faceted.png',
    'forecats.png',
]


def load_cutoff_records(output_root: Path) -> list[dict]:
    records: list[dict] = []
    for cutoff_dir in sorted(p for p in output_root.iterdir() if p.is_dir() and p.name[:8].isdigit()):
        meta_dir = cutoff_dir / 'metadata'
        review_dir = cutoff_dir / 'review'
        figure_manifest = review_dir / 'figure_manifest.csv'
        if not figure_manifest.exists():
            continue
        entry = json.loads((meta_dir / 'cutoff_entry.json').read_text())
        policy = __import__('yaml').safe_load((meta_dir / 'policy_summary.yaml').read_text())
        support = __import__('yaml').safe_load((meta_dir / 'support_window.yaml').read_text())
        coverage = __import__('yaml').safe_load((meta_dir / 'coverage_audit.yaml').read_text())
        rows = list(csv.DictReader(figure_manifest.open()))
        records.append({
            'cutoff_dir': cutoff_dir,
            'entry': entry,
            'policy': policy,
            'support': support,
            'coverage': coverage,
            'rows': rows,
        })
    return records


def build_review(output_root: Path) -> None:
    review_root = output_root / 'review'
    review_root.mkdir(parents=True, exist_ok=True)
    records = load_cutoff_records(output_root)

    manifest_path = review_root / 'figure_manifest.csv'
    with manifest_path.open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow([
            'slug', 'cutoff_date', 'published_crps', 'bundle_class', 'support_start', 'support_end',
            'retrospective_available_start', 'retrospective_full_history_available',
            'plot_start', 'plot_end', 'forecast_start_date', 'figure_name', 'figure_path', 'sha256', 'bytes'
        ])
        for record in records:
            entry = record['entry']
            support = record['support']
            coverage = record['coverage']
            for row in record['rows']:
                writer.writerow([
                    entry['slug'], entry['cutoff_date'], entry['published_crps'], entry['bundle_class'],
                    support['support_start'], support['support_end'],
                    support['retrospective_available_start'], coverage['retrospective']['full_history_available'],
                    support['plot_start'], support['plot_end'], support['forecast_start_date'],
                    row['figure_name'], row['path'], row['sha256'], row['bytes']
                ])

    md_lines = [
        '# exAL-M-T1 Setup/Support v2 Review\n\n',
        'This review bundle contains the corrected cutoff-specific setup/input/support figures rendered from the CRPS-linked `exAL-M-T1` run roots and the authoritative forecats/histfix bundles.\n\n',
        '## Cutoff summary\n',
        '| Cutoff | Slug | Bundle class | Requested history | Retrospective available from | Forecast window | Published CRPS |\n',
        '|---|---|---|---|---|---|---:|\n',
    ]
    for record in records:
        entry = record['entry']
        support = record['support']
        md_lines.append(
            f"| {entry['cutoff_date']} | `{entry['slug']}` | `{entry['bundle_class']}` | {support['support_start']} to {support['support_end']} | {support['retrospective_available_start']} | {support['plot_start']} to {support['plot_end']} | {entry['published_crps']} |\n"
        )
    md_lines.append('\n## Policy summary\n')
    md_lines.append('| Cutoff | NWS policy | GloFAS policy | Notes |\n')
    md_lines.append('|---|---|---|---|\n')
    for record in records:
        entry = record['entry']
        policy = record['policy']
        md_lines.append(
            f"| {entry['cutoff_date']} | {policy['nws_policy_summary']} | {policy['glofas_policy_summary']} | {policy.get('notes','')} |\n"
        )
    md_lines.append('\n## Coverage audit\n')
    md_lines.append('| Cutoff | USGS full history | PPT full history | SOIL full history | PCA full history | Retros full history | Retros available start |\n')
    md_lines.append('|---|---|---|---|---|---|---|\n')
    for record in records:
        entry = record['entry']
        coverage = record['coverage']
        md_lines.append(
            f"| {entry['cutoff_date']} | {coverage['usgs']['full_history_available']} | {coverage['ppt']['full_history_available']} | "
            f"{coverage['soil']['full_history_available']} | {coverage['pca']['full_history_available']} | "
            f"{coverage['retrospective']['full_history_available']} | {coverage['retrospective']['available_start']} |\n"
        )
    md_lines.append('\n')
    (review_root / 'REVIEW.md').write_text(''.join(md_lines))

    html_lines = [
        '<!doctype html><html><head><meta charset="utf-8"><title>exAL-M-T1 Setup/Support v2 Review</title>',
        '<style>body{font-family:Arial,sans-serif;margin:24px;} .cutoff{margin-top:36px;} .grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;} .card{border:1px solid #ddd;border-radius:8px;padding:12px;background:#fff;} img{max-width:100%;height:auto;border:1px solid #eee;} .meta{font-size:13px;color:#333;line-height:1.45;} code{background:#f4f4f4;padding:2px 4px;border-radius:4px;}</style></head><body>',
        '<h1>exAL-M-T1 Setup/Support v2 Review</h1>',
        '<p>This gallery is the canonical review surface for the corrected cutoff-specific setup/input/support figure family.</p>'
    ]
    for record in records:
        entry = record['entry']
        support = record['support']
        policy = record['policy']
        coverage = record['coverage']
        html_lines.append(f'<div class="cutoff"><h2>{html.escape(entry["cutoff_date"])}</h2>')
        html_lines.append(
            '<p class="meta">'
            f'<strong>Slug:</strong> <code>{html.escape(entry["slug"])}</code><br>'
            f'<strong>Bundle class:</strong> <code>{html.escape(entry["bundle_class"])}</code><br>'
            f'<strong>Requested history:</strong> {html.escape(support["support_start"])} to {html.escape(support["support_end"])}<br>'
            f'<strong>Retrospective available from:</strong> {html.escape(support["retrospective_available_start"])}<br>'
            f'<strong>Forecast window:</strong> {html.escape(support["plot_start"])} to {html.escape(support["plot_end"])}<br>'
            f'<strong>NWS policy:</strong> {html.escape(policy["nws_policy_summary"])}<br>'
            f'<strong>GloFAS policy:</strong> {html.escape(policy["glofas_policy_summary"])}<br>'
            f'<strong>Coverage audit:</strong> USGS={html.escape(str(coverage["usgs"]["full_history_available"]))}, '
            f'PPT={html.escape(str(coverage["ppt"]["full_history_available"]))}, '
            f'SOIL={html.escape(str(coverage["soil"]["full_history_available"]))}, '
            f'PCA={html.escape(str(coverage["pca"]["full_history_available"]))}, '
            f'Retros={html.escape(str(coverage["retrospective"]["full_history_available"]))}'
            '</p>'
        )
        html_lines.append('<div class="grid">')
        for row in record['rows']:
            rel = Path(os.path.relpath(row['path'], review_root))
            html_lines.append('<div class="card">')
            html_lines.append(f'<h3>{html.escape(row["figure_name"])}</h3>')
            html_lines.append(f'<p class="meta"><strong>SHA256:</strong> <code>{html.escape(row["sha256"][:16])}...</code><br><strong>Bytes:</strong> {html.escape(row["bytes"])}</p>')
            html_lines.append(f'<img src="{rel.as_posix()}" alt="{html.escape(row["figure_name"])}">')
            html_lines.append('</div>')
        html_lines.append('</div></div>')
    html_lines.append('</body></html>')
    (review_root / 'gallery.html').write_text(''.join(html_lines))


def main() -> None:
    parser = argparse.ArgumentParser(description='Build runtime review artifacts for exAL-M-T1 setup/support v2 outputs.')
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    build_review(args.output_root.resolve())
    print(f'Built v2 review artifacts at {args.output_root.resolve() / "review"}')


if __name__ == '__main__':
    main()
