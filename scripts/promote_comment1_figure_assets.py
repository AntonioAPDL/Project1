#!/usr/bin/env python3
"""Promote an inspected comment-1 render into article assets and durable lineage.

This command changes presentation files only. Retained numerical CSVs/caches are
hashed before and after promotion. A registry lets regular refresh entrypoints
restore the reviewed figures only while their numerical inputs and selection IDs
still match. No authoritative runtime output is written.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(path: Path) -> list[dict]:
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def save_rows(path: Path, rows: list[dict]) -> None:
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--render-root', required=True, type=Path)
    p.add_argument('--article-root', required=True, type=Path)
    p.add_argument('--additional-provenance', type=Path, help='Inspected component-title revision provenance, with input_hashes.')
    p.add_argument('--additional-target', action='append', default=[], help='Additional inspected article-relative presentation target; repeat as needed.')
    args = p.parse_args()
    root, render = args.article_root.resolve(), args.render_root.resolve()
    report = json.loads((render / 'render_manifest.json').read_text())
    snapshot_path = Path(report['snapshot'])
    if sha(snapshot_path) != report['snapshot_sha256']:
        raise ValueError('Render snapshot content changed; promotion refused.')
    snapshot = json.loads(snapshot_path.read_text())
    expected_inputs = {str(Path(row['path']).resolve()): row['sha256'] for row in snapshot['files'] if row.get('exists') and row.get('sha256')}
    for row in report['inputs']:
        expected = expected_inputs.get(str(Path(row['source']).resolve()))
        if expected is not None and expected != row['sha256']:
            raise ValueError(f'Render input does not match frozen snapshot: {row["source"]}')
    selected = [r for r in snapshot['selected_runs'] if r['run_id'] in {a.get('run_id') for a in report['assets']}]
    expected_selection = {(cutoff, 'exAL-M-T1') for cutoff in ['20210123', '20211112', '20211221', '20220511', '20221225']}
    expected_selection.add(('20221225', 'exAL-U-T1'))
    if {(row['cutoff'], row['label']) for row in selected} != expected_selection:
        p.error('Render selection differs from the six planned publication runs.')
    if len(selected) != 6 or len(report['assets']) != 14:
        p.error('Final promotion requires all five multivariate panels, December univariate and context with PNG/PDF pairs.')
    registry_root = root / 'artifacts/comment1_figure_revision'
    if (registry_root / 'registry.json').exists():
        p.error('Presentation registry already exists; preserve it and use a separately reviewed revision.')
    freeze_rows = load_rows(root / 'artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv')
    freeze_ids = {(row['cutoff'].replace('-', ''), row['manuscript_label']): row.get('artifact_run_id') or row['run_id'] for row in freeze_rows}
    for row in selected:
        if freeze_ids.get((row['cutoff'], row['label'])) != row['run_id']:
            raise ValueError(f'Current article selected run differs from inspected render: {row["run_id"]}')
    # Check every output and local numerical CSV before the first article write.
    for asset in report['assets']:
        if sha(Path(asset['asset'])) != asset['sha256']:
            raise ValueError(f'Rendered asset changed: {asset["asset"]}')
    for row in selected:
        family = 'five_cutoff_main_model_synthesis' if row['label'] == 'exAL-M-T1' else 'five_cutoff_reference_synthesis'
        source = render / 'runs' / row['run_id'] / 'post/outputs' / row['run_id']
        for suffix in ['quantiles.csv', 'sample_subset.csv']:
            name = f'{row["model_id"]}_cutoff_window_{suffix}'
            local = root / 'artifacts' / family / f'{row["cutoff"]}_exal_m_t1' / name
            if sha(local) != sha(source / name):
                raise ValueError(f'Article numerical CSV differs from inspected render: {local}')
    numeric = [x for x in report['inputs'] if x['source'].endswith(('.csv', '.rds'))]
    for row in numeric:
        if sha(Path(row['source'])) != row['sha256']:
            raise ValueError(f'Render input changed: {row["source"]}')
    additional_provenance = json.loads(args.additional_provenance.read_text()) if args.additional_provenance else None
    if additional_provenance:
        for row in additional_provenance['input_hashes']:
            if sha(Path(row['path'])) != row['sha256']:
                raise ValueError(f'Additional presentation input changed: {row["path"]}')
            numeric.append({'source': row['path'], 'sha256': row['sha256']})
    for rel in args.additional_target:
        target = root / rel
        if not target.resolve().is_relative_to(root) or not target.is_file():
            raise ValueError(f'Invalid additional presentation target: {rel}')
    touched: set[Path] = set()
    protected: dict[Path, str] = {}

    def track(path: Path) -> None:
        if not path.resolve().is_relative_to(root):
            raise ValueError(f'Target escapes article: {path}')
        touched.add(path)

    def copy(source: Path, target: Path) -> None:
        track(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    def mark_json(path: Path, addition: dict) -> None:
        value = json.loads(path.read_text())
        value['presentation_revision'] = addition
        track(path)
        path.write_text(json.dumps(value, indent=2) + '\n')

    revision = {'id': 'publication_comment1_v3',
                'registry': 'artifacts/comment1_figure_revision/registry.json',
                'render_manifest': 'artifacts/comment1_figure_revision/render_manifest.json',
                'mean': 'E[log(1 + discharge_cms)] from complete retained predictive matrices',
                'interval_probabilities': [0.025, 0.975], 'sample_path_cap': 10,
                'origin_line': 'T; first forecast T+1', 'reference_guides': report['reference_guides']}
    for asset in report['assets']:
        source = Path(asset['asset'])
        if sha(source) != asset['sha256']:
            raise ValueError(f'Rendered asset changed: {source}')
        copy(source, root / asset['article_path'])
    family_paths = []
    for r in selected:
        mid, cutoff = r['model_id'], r['cutoff']
        source = render / 'runs' / r['run_id'] / 'post/outputs' / r['run_id']
        is_multi = r['label'] == 'exAL-M-T1'
        family = 'five_cutoff_main_model_synthesis' if is_multi else 'five_cutoff_reference_synthesis'
        dest = root / 'artifacts' / family / f'{cutoff}_exal_m_t1'
        family_paths.append(dest)
        for suffix in ['quantiles.csv', 'sample_subset.csv']:
            name = f'{mid}_cutoff_window_{suffix}'
            protected[dest / name] = sha(dest / name)
            if protected[dest / name] != sha(source / name):
                raise ValueError(f'Frozen article numerical CSV differs from selected run: {dest / name}')
        for tail in ['', '_with_raw_ensembles']:
            for ext in ['png', 'pdf']:
                name = f'{mid}_cutoff_window_posterior_samples{tail}.{ext}'
                copy(source / name, dest / name)
                date = f'{cutoff[:4]}_{cutoff[4:6]}_{cutoff[6:]}'
                prefix = 'multivariate' if is_multi else 'reference'
                family_dir = f'{prefix}_synthesis_by_cutoff'
                basename = f'cutoff_{date}_{prefix}_synthesis' + ('_with_reference_ensembles' if tail else '')
                copy(source / name, root / 'Figures' / family_dir / f'{basename}.{ext}')
        for name in ['publication_style_used.yaml', 'publication_figure_manifest.csv', f'{mid}_focus_render_numeric_contract.csv']:
            copy(source / name, dest / name)
        pub = load_rows(dest / 'publication_figure_manifest.csv')
        for row in pub:
            for key in ['canonical_png', 'pdf_path', 'quantiles_path', 'sample_subset_path', 'style_snapshot_path']:
                if row.get(key):
                    row[key] = str((dest / Path(row[key]).name).relative_to(root))
            row['style_source_path'] = 'workflow:config/post_publication_figures.yaml'
        save_rows(dest / 'publication_figure_manifest.csv', pub)
        meta = dest / 'source_metadata.json'
        mark_json(meta, revision)
        rows = load_rows(dest / 'manifest.csv')
        for row in rows:
            name = row['bundle_file']
            path = dest / name
            row['target_path'] = str(path.relative_to(root))
            row['sha256'], row['bytes'] = sha(path), str(path.stat().st_size)
            if path in touched:
                row['source_path'] = str((Path('artifacts/comment1_figure_revision/files') / path.relative_to(root)))
        save_rows(dest / 'manifest.csv', rows)
        track(dest / 'manifest.csv')
        (dest / 'SHA256SUMS.txt').write_text(''.join(f'{sha(dest / row["bundle_file"])}  {row["bundle_file"]}\n' for row in rows))
        track(dest / 'SHA256SUMS.txt')
    # The appendix's reference follows a separate historical-support alias.
    hist = root / 'artifacts/historical_support_from_current_models'
    for ext in ['png', 'pdf']:
        copy(root / f'Figures/manuscript/reference_synthesis_univariate.{ext}', hist / f'figures/reference_synthesis_univariate.{ext}')
    rows = load_rows(hist / 'manifest.csv')
    for row in rows:
        if row['label'] == 'fig:synth2':
            target = hist / 'figures/reference_synthesis_univariate.png'
            row['generation_mode'] = 'rendered_from_retained_predictive_caches'
            row['source_path'] = 'artifacts/five_cutoff_reference_synthesis/20221225_exal_m_t1/exdqlm_univar_synth_cutoff_window_posterior_samples.png'
            row['sha256'] = sha(target)
    save_rows(hist / 'manifest.csv', rows)
    track(hist / 'manifest.csv')
    sums = (hist / 'SHA256SUMS.txt').read_text().splitlines()
    sums = [f'{sha(hist / "figures/reference_synthesis_univariate.png")}  figures/reference_synthesis_univariate.png' if line.endswith('figures/reference_synthesis_univariate.png') else line for line in sums]
    (hist / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n')
    track(hist / 'SHA256SUMS.txt')
    mark_json(hist / 'bundle_metadata.json', revision)
    # Retain the old setup figure lineage; replace only its displayed context.
    context = root / 'artifacts/five_cutoff_setup_support/20221225_exal_m_t1'
    for ext in ['png', 'pdf']:
        copy(root / f'Figures/manuscript/forecast_products_context.{ext}', context / f'figures/forecats.{ext}')
    rows = load_rows(context / 'review/figure_manifest.csv')
    for row in rows:
        if row['figure_name'] == 'forecats.png':
            target = context / 'figures/forecats.png'
            row['path'] = str(target.relative_to(root))
            row['sha256'], row['bytes'] = sha(target), str(target.stat().st_size)
    save_rows(context / 'review/figure_manifest.csv', rows)
    track(context / 'review/figure_manifest.csv')
    extra = context / 'metadata/presentation_revision.json'
    extra.write_text(json.dumps(revision, indent=2) + '\n')
    track(extra)
    # Keep existing whole-family manifests accurate, including optional primary
    # companions generated by the same six-run rendering pass.
    for name in ['multivariate_synthesis_by_cutoff', 'reference_synthesis_by_cutoff']:
        manifest = root / 'Figures' / name / 'manifest.csv'
        rows = load_rows(manifest)
        for row in rows:
            relative = 'Figures/' + row['target_path'].split('/', 1)[1]
            target = root / relative
            row['target_path'] = relative
            if target in touched:
                row['sha256'], row['bytes'] = sha(target), str(target.stat().st_size)
                row['source_path'] = 'artifacts/comment1_figure_revision/files/' + relative
        save_rows(manifest, rows)
        track(manifest)
    for path, before in protected.items():
        if sha(path) != before:
            raise ValueError(f'Numerical CSV changed during promotion: {path}')
    for rel in args.additional_target:
        track(root / rel)
    # The archive contains only changed display files/metadata, never model fits.
    registry_root.mkdir(parents=True, exist_ok=True)
    copy(render / 'render_manifest.json', registry_root / 'render_manifest.json')
    touched.discard(registry_root / 'render_manifest.json')
    if args.additional_provenance:
        shutil.copy2(args.additional_provenance, registry_root / 'component_revision_provenance.json')
    restore = []
    for target in sorted(touched):
        rel = target.relative_to(root)
        stored = Path('files') / rel
        archive = registry_root / stored
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, archive)
        restore.append({'target': str(rel), 'stored': str(stored), 'sha256': sha(archive)})
    registry = {'schema': 'comment1-presentation-registry-v1', 'revision': revision,
                'selected_runs': [{k: r[k] for k in ['cutoff', 'label', 'run_id']} for r in selected],
                'numeric_inputs': [{'source': row['source'], 'sha256': row['sha256']} for row in numeric],
                'article_numeric_inputs': [{'path': str(path.relative_to(root)), 'sha256': digest} for path, digest in protected.items()],
                'restore': restore}
    (registry_root / 'registry.json').write_text(json.dumps(registry, indent=2) + '\n')
    sys.path.insert(0, str(root / 'scripts'))
    from comment1_figure_revision import verify_comment1_figure_revision
    verify_comment1_figure_revision(root)
    print(f'Promoted and registered {len(restore)} presentation assets/metadata files; {len(protected)} article numerical CSVs unchanged.')


if __name__ == '__main__':
    main()
