#!/usr/bin/env python3
"""Repeat the bounded comment-1 checks; no fitting or asset refresh is launched.

Use a new --report-dir under /tmp. Every subprocess command and its output are
recorded there. The separate article build_manuscript_review.py builds the PDF.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-root', type=Path, default=here.parents[2])
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.workflow_root.resolve(), args.report_dir.resolve()
    if not out.is_relative_to(Path('/tmp')) or out.exists():
        parser.error('--report-dir must be a new directory under /tmp')
    out.mkdir(parents=True)
    article = root / 'Evironmetrics---REVISED-DOC-Corrected-2'
    response = root.parent / 'Corrections---Project-1'
    public = root.parent / 'san-lorenzo-exdqlm-reproducibility'
    he3 = root.parent / 'project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625'
    records = []

    def run(name: str, argv: list[str]) -> None:
        proc = subprocess.run(argv, cwd=root, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        log = out / f'{name}.log'
        log.write_text(proc.stdout, encoding='utf-8')
        count = re.search(r'Ran (\d+) tests?', proc.stdout)
        records.append({'name': name, 'argv': argv, 'cwd': str(root),
                        'returncode': proc.returncode, 'log': str(log),
                        'unittest_count': int(count.group(1)) if count else None})
        print(f'{name}: ' + ('PASS' if not proc.returncode else f'FAIL (see {log})'), flush=True)

    for pattern in [
        'test_r1_overview_contract.py', 'test_r1_m1_uncertainty_contract.py',
        'test_he1_runtime_contract.py', 'test_he6_forecast_design_contract.py',
        'test_he7_latest_forecast_issue_contract.py', 'test_reviewer1_remaining_contracts.py',
        'test_article_legacy_uppercase_figures_sync.py', 'test_comment1_figure_render_guards.py',
    ]:
        run(pattern.removesuffix('.py'), [sys.executable, '-B', '-m', 'unittest', 'discover',
            '-s', 'tests/python', '-p', pattern, '-v'])
    for pattern in ['test_article_a1_and_table_contracts.py', 'test_manuscript_text_contract.py',
                    'test_comment1_figure_revision.py']:
        run(pattern.removesuffix('.py'), [sys.executable, '-B', '-m', 'unittest', 'discover',
            '-s', str(article / 'tests'), '-p', pattern, '-v'])
    run('r_publication_figures', ['Rscript', '--vanilla', '-e',
        'testthat::test_file("tests/testthat/test_post_publication_figures.R", '
        'reporter="summary", stop_on_failure=TRUE, stop_on_warning=TRUE)'])
    run('figure_paths', [sys.executable, '-B', str(article / 'scripts/validate_manuscript_figure_paths.py'),
                        '--article-root', str(article)])
    run('presentation_registry', [sys.executable, '-B', str(article / 'scripts/comment1_figure_revision.py'),
                                  '--article-root', str(article), '--check'])
    run('output_lineage', [sys.executable, '-B', str(article / 'scripts/validate_authoritative_output_lineage.py'),
        '--article-root', str(article), '--corrections-root', str(response),
        '--report-dir', str(out / 'lineage')])
    run('publication_freeze', [sys.executable, '-B', str(root / 'scripts/validate_publication_freeze.py'),
        '--workflow-root', str(root), '--article-root', str(article), '--corrections-root', str(response),
        '--he3-runtime-root', str(he3), '--report-dir', str(out / 'publication_freeze')])
    run('cross_repo_wiring', [sys.executable, '-B', str(root / 'scripts/validate_revision_cross_repo_wiring.py'),
        '--workflow-root', str(root), '--article-root', str(article), '--corrections-root', str(response),
        '--output-dir', str(out / 'cross_repo'), '--check-only', '--strict'])
    run('numerical_invariants', [sys.executable, '-B', str(here.parent / 'readiness/audit_readiness.py'),
        '--workflow-root', str(root), '--article-root', str(article), '--response-root', str(response),
        '--public-root', str(public), '--compare', str(here.parent / 'readiness/baseline_snapshot.json'),
        '--out', str(out / 'invariant_snapshot.json')])
    summary = {'snapshot_local': datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(),
               'workflow_root': str(root), 'commands': records,
               'python_tests': sum(x['unittest_count'] or 0 for x in records),
               'failed_commands': [x['name'] for x in records if x['returncode']],
               'all_passed': all(not x['returncode'] for x in records)}
    (out / 'check_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: summary[k] for k in ['python_tests', 'failed_commands', 'all_passed']}, indent=2))
    return 0 if summary['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
