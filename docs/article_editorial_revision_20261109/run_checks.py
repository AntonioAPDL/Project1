#!/usr/bin/env python3
"""Check the editorial release, its retained results and the exact PDF sources.

This wrapper adds editorial-preservation and actual-dependency checks to the
existing active-article gate. It starts no fits and changes no research outputs.
Reports must be written to a fresh directory under /tmp.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

WORKFLOW = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW / 'scripts'))
from article_repository_binding import assert_article_write_target

ALLOWED_EXISTING_CHANGES = {
    'wileyNJD-APA.tex', 'wileyNJD-APA.bib', 'MANUSCRIPT_ASSET_MANIFEST.json',
    'scripts/manuscript_text_contract.py', 'scripts/build_manuscript_review.py',
    'tests/test_article_a1_and_table_contracts.py',
}


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def preservation(article: Path, baseline: dict) -> dict:
    changed, missing, modes = [], [], []
    current = []
    for rel, entry in baseline['files'].items():
        path = article / rel
        if not path.is_file():
            missing.append(rel)
            current.append((rel, 'missing', 'missing'))
            continue
        identity = blob(path)
        if identity != entry['blob']:
            changed.append(rel)
        mode = '100755' if path.stat().st_mode & 0o111 else '100644'
        current.append((rel, identity, mode))
        if mode != entry['mode']:
            modes.append(rel)
    unexpected = sorted(set(changed) - ALLOWED_EXISTING_CHANGES)
    return dict(baseline_commit=baseline['article_commit'],
        baseline_file_count=len(baseline['files']), changed_existing_files=changed,
        unchanged_existing_count=len(baseline['files']) - len(changed) - len(missing),
        current_baseline_content_sha256=hashlib.sha256(
            json.dumps(sorted(current), separators=(',', ':')).encode()).hexdigest(),
        missing=missing, changed_modes=modes, unexpected_changes=unexpected,
        passed=not missing and not modes and not unexpected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-root', type=Path, default=WORKFLOW)
    parser.add_argument('--article-root', type=Path)
    parser.add_argument('--corrections-root', type=Path)
    parser.add_argument('--public-root', type=Path)
    parser.add_argument('--he3-runtime-root', type=Path)
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    workflow = args.workflow_root.resolve()
    article = assert_article_write_target(args.article_root, workflow)
    out = args.report_dir.resolve()
    if out.exists() or not out.is_relative_to(Path('/tmp')):
        parser.error('--report-dir must be a fresh directory under /tmp')
    out.mkdir(parents=True)
    baseline = json.loads((Path(__file__).parent / 'baseline.json').read_text())
    before = preservation(article, baseline)
    (out / 'baseline_preservation_before.json').write_text(json.dumps(before, indent=2) + '\n')
    if not before['passed']:
        print('Unexpected baseline changes; see baseline_preservation_before.json')
        return 1
    env = os.environ.copy()
    env['ENVIRONMETRICS_ARTICLE_ROOT'] = str(article)
    records = []

    def run(name, command, cwd):
        command = list(map(str, command))
        result = subprocess.run(command, cwd=cwd, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / (name + '.log')).write_text(result.stdout)
        records.append(dict(name=name, argv=command, cwd=str(cwd), returncode=result.returncode))
        print(name + ': ' + ('PASS' if result.returncode == 0 else 'FAIL'), flush=True)

    py = sys.executable
    legacy = [py, '-B', workflow / 'docs/article_repository_migration_20261108/run_checks.py',
              '--workflow-root', workflow, '--article-root', article,
              '--report-dir', out / 'active_article']
    for flag, value in (('--corrections-root', args.corrections_root),
                        ('--public-root', args.public_root),
                        ('--he3-runtime-root', args.he3_runtime_root)):
        if value is not None:
            legacy.extend([flag, value.resolve()])
    run('active_article_gate', legacy, workflow)
    run('editorial_table_and_integration_tests',
        [py, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_editorial*.py', '-v'], article)
    run('editorial_cross_repo_tests', [py, '-B', '-m', 'unittest', 'discover',
        '-s', 'tests/python', '-p', 'test_article_editorial_wiring.py', '-v'], workflow)
    run('editorial_refresh_check',
        [py, '-B', article / 'scripts/refresh_editorial_revision.py', '--check'], article)
    run('review_build', [py, '-B', article / 'scripts/build_manuscript_review.py',
        '--output-dir', out / 'proof', '--jobname', 'editorial_review'], article)
    after = preservation(article, baseline)
    (out / 'baseline_preservation_after.json').write_text(json.dumps(after, indent=2) + '\n')
    summary = dict(created_utc=datetime.now(timezone.utc).isoformat(),
        workflow_root=str(workflow), article_root=str(article), commands=records,
        baseline_preservation=after, passed=all(r['returncode'] == 0 for r in records)
        and before == after and after['passed'])
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'passed': summary['passed'], 'commands': len(records),
                      'unchanged_baseline_files': after['unchanged_existing_count']}, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
