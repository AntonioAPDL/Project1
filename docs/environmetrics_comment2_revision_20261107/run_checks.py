#!/usr/bin/env python3
"""Repeat bounded point-2 checks in a fresh /tmp report directory; never fit models."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-root', type=Path, default=here.parents[1])
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.workflow_root.resolve(), args.report_dir.resolve()
    if not out.is_relative_to(Path('/tmp')) or out.exists():
        parser.error('--report-dir must be a new directory under /tmp')
    out.mkdir(parents=True)
    article = root/'Evironmetrics---REVISED-DOC-Corrected-2'
    records = []

    def run(name: str, argv: list[str]) -> None:
        proc = subprocess.run(argv, cwd=root, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        (out/(name+'.log')).write_text(proc.stdout)
        count = re.search(r'Ran (\d+) tests?', proc.stdout)
        records.append(dict(name=name, argv=argv, cwd=str(root), returncode=proc.returncode,
                            python_tests=int(count.group(1)) if count else 0))
        print(name+': '+('PASS' if proc.returncode == 0 else 'FAIL'), flush=True)

    py = sys.executable
    run('existing_contracts', [py, '-B', str(root/'docs/environmetrics_comment1_plan_20261107/implementation/run_checks.py'),
                              '--report-dir', str(out/'existing_contracts')])
    run('component_diagnostic_tests', [py, '-B', '-m', 'unittest', 'discover', '-s',
        'tests/python', '-p', 'test_comment2_component_diagnostics.py', '-v'])
    run('article_integration_tests', [py, '-B', '-m', 'unittest', 'discover', '-s',
        str(article/'tests'), '-p', 'test_comment2_revision.py', '-v'])
    run('external_baseline_tests', ['Rscript', '--vanilla', '-e',
        'testthat::test_file("tests/testthat/test_comment2_external_baselines.R", '
        'reporter="summary", stop_on_failure=TRUE, stop_on_warning=TRUE)'])
    run('point2_bundle_and_tables', [py, '-B', str(article/'scripts/comment2_revision.py'), '--check'])
    run('point2_preservation', [py, '-B', str(root/'docs/environmetrics_comment1_plan_20261107/readiness/audit_readiness.py'),
        '--compare', str(here/'preparation/baseline_snapshot.json'), '--out', str(out/'preservation.json')])
    archived = article/'artifacts/comment2_revision/reproduce'
    hashes = {}
    for rel in ['scripts/build_comment2_external_baselines.R', 'config/comment2_external_baselines.json',
                'scripts/audit_comment2_component_diagnostics.py']:
        live = hashlib.sha256((root/rel).read_bytes()).hexdigest()
        frozen = hashlib.sha256((archived/rel).read_bytes()).hexdigest()
        hashes[rel] = dict(live_sha256=live, archived_sha256=frozen, equal=live == frozen)
    (out/'code_archive_check.json').write_text(json.dumps(hashes, indent=2)+'\n')
    old = json.loads((out/'existing_contracts/check_summary.json').read_text())
    r1 = (out/'existing_contracts/r_publication_figures.log').read_text()
    r2 = (out/'external_baseline_tests.log').read_text()
    assertion_counts = []
    for log, name in [(r1, 'post_publication_figures'), (r2, 'comment2_external_baselines')]:
        match = re.search(re.escape(name)+r': (\.+)', log)
        assertion_counts.append(len(match.group(1)) if match else None)
    summary = dict(created_utc=datetime.now(timezone.utc).isoformat(), commands=records,
                   python_tests=old['python_tests']+sum(r['python_tests'] for r in records),
                   r_assertions=assertion_counts, code_archive_matches=all(x['equal'] for x in hashes.values()),
                   all_passed=all(r['returncode'] == 0 for r in records) and
                              old['all_passed'] and all(x['equal'] for x in hashes.values()))
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ('python_tests','r_assertions','code_archive_matches','all_passed')}, indent=2))
    return 0 if summary['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
