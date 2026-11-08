#!/usr/bin/env python3
"""Read-only native checks and deterministic replay of migrated article bundles."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def article_files(root):
    return sorted(p for p in root.rglob('*') if p.is_file()
                  and '.git' not in p.parts and '__pycache__' not in p.parts
                  and p.name != 'wileyNJD-APA.pdf')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article', type=Path, required=True)
    parser.add_argument('--reviewed-article', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    article = args.article.resolve(strict=True)
    reviewed = args.reviewed_article.resolve(strict=True)
    output = args.output_dir
    output.mkdir(parents=False, exist_ok=False)
    before_files = article_files(article)
    before = {p.relative_to(article).as_posix(): sha(p) for p in before_files}
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')

    def checked(name, command, cwd):
        began = time.monotonic()
        result = subprocess.run(command, cwd=cwd, env=environment, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output / f'{name}.log').write_text(result.stdout)
        record = {'name': name, 'command': command, 'cwd': str(cwd),
                  'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - began,
                  'output_log': f'{name}.log'}
        if result.returncode:
            raise RuntimeError(f'{name} failed: {result.stdout}')
        return record

    calls = [('comment1_check', ['python3', '-B', 'scripts/comment1_figure_revision.py', '--check'], article),
             ('comment2_check', ['python3', '-B', 'scripts/comment2_revision.py', '--check'], article),
             ('no_refit_check', ['python3', '-B', 'scripts/no_refit_revision.py', '--check'], article)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        native = list(executor.map(lambda call: checked(*call), calls))
    temporary = Path(tempfile.mkdtemp(prefix='corrected3_portable_replay_', dir='/tmp'))
    empty = temporary / 'empty'; empty.mkdir()
    core = article / 'artifacts/no_refit_revision'
    core_output = temporary / 'core_replay'
    core_command = ['Rscript', '--vanilla', str(core/'reproduce/scripts/build_no_refit_review_diagnostics.R'),
                    '--inputs-manifest', str(core/'inputs/manifest.json'), '--output-dir', str(core_output)]
    core_run = checked('core_portable_replay', core_command, empty)
    core_parity = []
    for original in sorted((core/'results').iterdir()):
        if not original.is_file():
            continue
        rebuilt = core_output/'results'/original.name
        if not rebuilt.is_file() or sha(original) != sha(rebuilt):
            raise AssertionError(f'Core replay byte mismatch: {original.name}')
        core_parity.append({'file': original.name, 'bytes': original.stat().st_size, 'sha256': sha(original)})
    assert sum(p['file'].endswith('.csv') for p in core_parity) == 14
    assert sum(p['file'].endswith('.png') for p in core_parity) == 1
    synthesis = core/'synthesis_diagnostics'
    synthesis_check = checked('synthesis_checksum_check', ['Rscript', '--vanilla',
        str(synthesis/'reproduce/build_no_refit_synthesis_diagnostics.R'),
        '--output-dir', str(synthesis), '--check'], empty)
    synthesis_output = temporary/'synthesis_replay'
    synthesis_run = checked('synthesis_compact_replay', ['Rscript', '--vanilla',
        str(synthesis/'reproduce/build_no_refit_synthesis_diagnostics.R'),
        '--inputs-dir', str(synthesis/'inputs'), '--output-dir', str(synthesis_output)], empty)
    synthesis_parity = []
    for original in sorted(synthesis.glob('*.csv')):
        rebuilt = synthesis_output/original.name
        if not rebuilt.is_file() or sha(original) != sha(rebuilt):
            raise AssertionError(f'Compact synthesis byte mismatch: {original.name}')
        synthesis_parity.append({'file': original.name, 'bytes': original.stat().st_size, 'sha256': sha(original)})
    after = {p.relative_to(article).as_posix(): sha(p) for p in article_files(article)}
    assert before == after, 'Article source/assets changed during read-only checks'

    latex_suffixes = {'.tex', '.bib', '.cls', '.sty', '.bst'}
    editable = []
    for p in before_files:
        relative = p.relative_to(article)
        if p.suffix.lower() in latex_suffixes and (reviewed/relative).is_file():
            assert sha(p) == sha(reviewed/relative), f'Editable LaTeX bytes differ: {relative}'
            editable.append({'file': relative.as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)})
    sizes = sorted(({'file': p.relative_to(article).as_posix(), 'bytes': p.stat().st_size}
                    for p in before_files), key=lambda z: z['bytes'], reverse=True)
    main_tex = article/'wileyNJD-APA.tex'
    main_tex.read_text(encoding='utf-8')
    report = {'status': 'PASSED', 'article_root': str(article),
        'native_checks': native, 'core_replay': core_run,
        'core_results_byte_identical': core_parity,
        'core_replay_verification': json.loads((core_output/'verification/verification.json').read_text()),
        'synthesis_checksum_check': synthesis_check, 'synthesis_compact_replay': synthesis_run,
        'synthesis_results_byte_identical': synthesis_parity,
        'synthesis_replay_verification': json.loads((synthesis_output/'verification.json').read_text()),
        'article_files_rechecked': len(before), 'changed_article_files': [],
        'tree_inventory_sha256': hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
        'latex_source_files_identical_to_reviewed_article': editable,
        'overleaf_objective_observations': {'file_count_excluding_git_cache_and_root_proof_pdf': len(before_files),
            'total_logical_bytes': sum(z['bytes'] for z in sizes), 'largest_files': sizes[:10],
            'main_tex_present_utf8': True,
            'main_tex_sha256': sha(main_tex),
            'latex_source_count_compared': len(editable),
            'excluded_generated_root_pdf': 'wileyNJD-APA.pdf',
            'synchronization_tested': False,
            'limitation': 'Filesystem checks establish source and artifact portability; no Overleaf UI or synchronization operation was available or tested.'},
        'temporary_replay_directory': str(temporary),
        'no_fits_new_draws_or_training': True,
        'script_sha256': sha(Path(__file__))}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    with (output/'article_source_hashes.csv').open('w', newline='') as f:
        writer = csv.writer(f); writer.writerow(['path', 'sha256'])
        writer.writerows(sorted(before.items()))
    print(json.dumps({'status': 'PASSED', 'core_csvs_identical': 14, 'core_pngs_identical': 1,
        'synthesis_csvs_identical': len(synthesis_parity), 'article_files_unchanged': len(before),
        'latex_files_identical': len(editable), 'report': str((output/'report.json').resolve())}, indent=2))


if __name__ == '__main__':
    main()
