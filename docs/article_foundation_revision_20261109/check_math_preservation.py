#!/usr/bin/env python3
"""Check reviewed mathematical changes and preserve every other expression.

The dated appendix release supplies the parser; its historical check is unchanged.
The explicit review records positions, old expressions and approved replacements.
This check never discovers or approves changes from the manuscript under test.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1]
PARSER_PATH = WORKFLOW / 'docs/article_appendix_integration_20261109/check_math_preservation.py'
SPEC = importlib.util.spec_from_file_location('historical_math_parser', PARSER_PATH)
PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)


def fingerprint(values: list[str]) -> str:
    return hashlib.sha256(json.dumps(values, separators=(',', ':')).encode()).hexdigest()


def expected_expressions(before: list[str], review: dict) -> list[str]:
    if fingerprint(before) != review['baseline_sha256']:
        raise ValueError('Reviewed mathematical baseline does not match Git')
    result, cursor = [], 0
    for change in review['changes']:
        start, stop = change['start'], change['stop']
        if not cursor <= start <= stop <= len(before):
            raise ValueError('Invalid or overlapping mathematical review positions')
        if before[start:stop] != change['before']:
            raise ValueError('Reviewed mathematical expression differs from baseline')
        if not change.get('reason'):
            raise ValueError('Every mathematical change requires a review reason')
        result.extend(before[cursor:start])
        result.extend(change['after'])
        cursor = stop
    result.extend(before[cursor:])
    return result


def numerical_rows(source: str) -> dict[str, list[str]]:
    rows = {}
    for line in source.splitlines():
        if '&' not in line:
            continue
        plain = re.sub(r'\\textbf\{([^{}]*)\}', r'\1', line)
        cells = [cell.strip() for cell in plain.rstrip().rstrip('\\').split('&')]
        if len(cells) != 5 or cells[0] == 'Method':
            continue
        if cells[0] in rows:
            raise ValueError('Duplicate aggregate table row')
        rows[cells[0]] = cells[1:]
    if len(rows) != 14:
        raise ValueError('Aggregate table must retain fourteen methods')
    return rows


def check(article: Path) -> dict:
    baseline = json.loads((HERE / 'baseline.json').read_text())
    review = json.loads((HERE / 'approved_math_changes.json').read_text())
    commit = baseline['article_commit']
    if review['baseline_commit'] != commit:
        raise ValueError('Mathematical review refers to a different baseline')

    def historical(relative: str) -> str:
        return subprocess.check_output(['git', '-C', str(article), 'show', commit + ':' + relative], text=True)

    records = {}
    for scope, relative in [('main', 'wileyNJD-APA.tex'), ('appendix', 'appendices.tex')]:
        old, current = historical(relative), (article / relative).read_text()
        if scope == 'main':
            old, current = PARSER.body(old, integrated=True), PARSER.body(current, integrated=True)
        before, after = PARSER.expressions(old), PARSER.expressions(current)
        expected = expected_expressions(before, review[scope])
        records[scope] = {'baseline_expressions': len(before), 'current_expressions': len(after),
                          'explicit_reviewed_changes': len(review[scope]['changes']),
                          'expected_sha256': fingerprint(expected), 'actual_sha256': fingerprint(after),
                          'passed': after == expected}
    relative = 'tables/compact_publication/main_aggregate.tex'
    rows_preserved = numerical_rows(historical(relative)) == numerical_rows((article / relative).read_text())
    return {'baseline_commit': commit, 'mathematics': records,
            'aggregate_table_numerical_rows_preserved': rows_preserved,
            'passed': rows_preserved and all(value['passed'] for value in records.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = check(args.article_root.resolve())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report = {'passed': False, 'error': str(error)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
