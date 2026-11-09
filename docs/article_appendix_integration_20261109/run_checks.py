#!/usr/bin/env python3
"""Validate one article with integrated appendices, without fitting any model.

Retain historical releases unchanged. Reuse the active numerical checks and add
single-root scope, local PDF links and scientific-source preservation checks.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

WORKFLOW = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW / 'scripts'))
from article_repository_binding import assert_article_write_target

# Only exposition, its local validation/build tools and regeneration guidance
# change. Every original scientific source and renderer remains byte-identical.
ALLOWED_EXISTING = {
    '.gitignore', 'PUBLICATION_PACKAGE.json', 'README.md',
    'docs/article_readme_template.txt', 'docs/compact_publication.txt',
    'wileyNJD-APA.tex',
    'scripts/build_manuscript_review.py',
    'scripts/check_wiley_submission_requirements.py',
    'scripts/compact_publication.py', 'scripts/manuscript_text_contract.py',
    'scripts/publication_package.py',
    'tests/test_article_a1_and_table_contracts.py',
    'tests/test_compact_publication.py', 'tests/test_editorial_integration.py',
    'tests/test_manuscript_text_contract.py',
    'tables/compact_publication/main_calibration.tex',
    'artifacts/compact_publication/manifest.json',
}
ALLOWED_DELETIONS = {'supporting_information.tex'}


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def preservation(article: Path, baseline: dict) -> dict:
    changed, missing, modes, identities = [], [], [], []
    for relative, before in baseline['files'].items():
        path = article / relative
        if not path.is_file():
            if relative not in ALLOWED_DELETIONS:
                missing.append(relative)
            continue
        identity = blob(path)
        if identity != before['blob']:
            changed.append(relative)
        mode = '100755' if path.stat().st_mode & 0o111 else '100644'
        expected_mode = before['mode']
        if mode != expected_mode:
            modes.append(relative)
        identities.append((relative, identity, mode))
    unexpected = sorted(set(changed) - ALLOWED_EXISTING)
    if not (article / 'appendices.tex').is_file():
        missing.append('appendices.tex')
    if (article / 'supporting_information.tex').exists():
        unexpected.append('supporting_information.tex:obsolete_document_root')
    return {'baseline_commit': baseline['article_commit'],
            'baseline_file_count': len(baseline['files']),
            'changed_existing_files': changed, 'missing': missing,
            'unexpected_content_changes': unexpected, 'unexpected_modes': modes,
            'snapshot_sha256': hashlib.sha256(json.dumps(sorted(identities)).encode()).hexdigest(),
            'passed': not missing and not unexpected and not modes}


def implementation_snapshot(article: Path) -> dict[str, str]:
    """Include new publication files and changed workflow tools in the freeze."""
    result = {}
    for prefix, root in [('article', article), ('workflow', WORKFLOW)]:
        files = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-c', '-o',
                                         '--exclude-standard', '-z']).decode().split('\0')
        for relative in set(files) - {''}:
            if prefix == 'workflow' and not (relative.startswith(('scripts/', 'tests/python/',
                                                   'docs/article_appendix_integration_20261109/'))):
                continue
            path = root / relative
            if path.is_file():
                result[prefix + ':' + relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path)
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    article = assert_article_write_target(args.article_root, WORKFLOW)
    output = args.report_dir.resolve()
    if output.exists() or not output.is_relative_to(Path('/tmp')):
        parser.error('--report-dir must be fresh and under /tmp')
    output.mkdir(parents=True)
    baseline = json.loads((Path(__file__).parent / 'baseline.json').read_text())
    before = preservation(article, baseline)
    (output / 'preservation_before.json').write_text(json.dumps(before, indent=2) + '\n')
    if not before['passed']:
        print('Unapproved source changes; inspect preservation_before.json')
        return 1
    implementation_before = implementation_snapshot(article)
    (output / 'implementation_before.json').write_text(json.dumps(implementation_before, indent=2) + '\n')
    env = os.environ.copy()
    env['ENVIRONMETRICS_ARTICLE_ROOT'] = str(article)
    commands = []
    unique_tests = set()

    def run(name, argv, cwd):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output / (name + '.log')).write_text(result.stdout)
        unexpected_skip = bool(re.search(r'\bskipped=\d+|\bSKIPPED\b|══ Skipped|── .*Skip', result.stdout))
        commands.append({'name': name, 'argv': list(map(str, argv)), 'cwd': str(cwd),
                         'returncode': result.returncode, 'unexpected_skip': unexpected_skip})
        print(name + ': ' + ('PASS' if result.returncode == 0 and not unexpected_skip else 'FAIL'), flush=True)

    py = sys.executable
    run('mathematical_preservation', [py, '-B', Path(__file__).parent / 'check_math_preservation.py',
                                      '--article-root', article,
                                      '--report', output / 'mathematical_preservation.json'], WORKFLOW)
    run('existing_scientific_gate', [py, '-B', WORKFLOW / 'docs/article_repository_migration_20261108/run_checks.py',
                                   '--report-dir', output / 'scientific'], WORKFLOW)
    run('article_tests', [py, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], article)
    run('workflow_compact_wiring', [py, '-B', '-m', 'unittest', 'discover', '-s', 'tests/python',
                                   '-p', 'test_article_editorial_wiring.py', '-v'], WORKFLOW)
    run('retained_editorial_replay', [py, '-B', article / 'scripts/refresh_editorial_revision.py', '--check'], article)
    run('compact_display_replay', [py, '-B', article / 'scripts/compact_publication.py', '--check'], article)
    run('publication_package', [py, '-B', article / 'scripts/publication_package.py', '--check'], article)
    run('independent_proofs', [py, '-B', article / 'scripts/publication_package.py',
                              '--build-dir', output / 'proofs'], article)
    run('compiled_appendix_links', [py, '-B', Path(__file__).parent / 'check_pdf_links.py',
                                   '--proof-dir', output / 'proofs/main',
                                   '--report', output / 'appendix_links.json'], WORKFLOW)
    run('live_overleaf_ancestry', [py, '-B', article / 'scripts/check_overleaf_sync.py'], article)
    protected = {}
    for name, expected in baseline['protected_repositories'].items():
        root = Path(expected['path'])
        current = {
            'head': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
            'tree': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD^{tree}'], text=True).strip(),
            'status': subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip(),
        }
        protected[name] = {**current, 'unchanged': all(current[k] == expected[k] for k in current)}
    (output / 'protected_repositories.json').write_text(json.dumps(protected, indent=2) + '\n')
    after = preservation(article, baseline)
    implementation_after = implementation_snapshot(article)
    (output / 'implementation_after.json').write_text(json.dumps(implementation_after, indent=2) + '\n')
    (output / 'preservation_after.json').write_text(json.dumps(after, indent=2) + '\n')
    for log in output.rglob('*.log'):
        text = log.read_text(errors='replace')
        unique_tests.update(re.findall(r'^(test_\w+) \(([^)]+)\) \.\.\.', text, re.M))
    summary = {'created_utc': datetime.now(timezone.utc).isoformat(),
               'article_root': str(article), 'commands': commands,
               'unique_python_test_ids': len(unique_tests),
               'source_preservation': after,
               'protected_repositories': protected,
               'sources_unchanged_during_validation': before == after,
               'implementation_file_count': len(implementation_before),
               'implementation_unchanged_during_validation': implementation_before == implementation_after,
               'passed': all(c['returncode'] == 0 and not c['unexpected_skip'] for c in commands)
                         and before == after and after['passed']
                         and implementation_before == implementation_after
                         and all(item['unchanged'] for item in protected.values())}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'passed': summary['passed'], 'unique_python_test_ids': len(unique_tests)}, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
