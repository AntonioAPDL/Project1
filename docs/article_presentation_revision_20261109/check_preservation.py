#!/usr/bin/env python3
"""Preserve mathematical expressions, tabular values and archived evidence."""
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
SPEC = importlib.util.spec_from_file_location('preserved_mathematics', PARSER_PATH)
PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)
TABULAR = re.compile(r'\\begin\{(?P<environment>tabular\*?)\}.*?\\end\{(?P=environment)\}', re.S)
ALGORITHMS = re.compile(r'\\begin\{algorithm\}.*?\\end\{algorithm\}', re.S)


def strip_bold(source: str) -> str:
    """Unwrap balanced textbf arguments, retaining nested scientific notation."""
    result, cursor = [], 0
    while (start := source.find(r'\textbf{', cursor)) >= 0:
        result.append(source[cursor:start])
        first = start + len(r'\textbf{')
        index, depth = first, 1
        while index < len(source) and depth:
            if source[index] == '\\':
                index += 2
                continue
            depth += (source[index] == '{') - (source[index] == '}')
            index += 1
        if depth:
            raise ValueError('Unbalanced bold argument')
        result.append(strip_bold(source[first:index - 1]))
        cursor = index
    result.append(source[cursor:])
    return ''.join(result)


def tabular(source: str) -> str:
    blocks = [match.group() for match in TABULAR.finditer(source)]
    if len(blocks) != 1:
        raise ValueError('Expected exactly one complete tabular block')
    return re.sub(r'\s+', '', strip_bold(blocks[0]))


def check(article: Path) -> dict:
    baseline = json.loads((HERE / 'baseline.json').read_text())
    commit = baseline['article_commit']

    def before(relative: str) -> str:
        return subprocess.check_output(['git', '-C', str(article), 'show', commit + ':' + relative], text=True)

    mathematics = {}
    for scope, relative in [('main', 'wileyNJD-APA.tex'), ('appendix', 'appendices.tex')]:
        old, current = before(relative), (article / relative).read_text()
        if scope == 'main':
            old, current = PARSER.body(old, integrated=True), PARSER.body(current, integrated=True)
        mathematics[scope] = PARSER.compare_math(old, current)
    tables = {}
    table_paths = sorted(p for p in baseline['files'] if p.startswith('tables/compact_publication/') and p.endswith('.tex'))
    table_paths.append('tables/editorial_revision/representative_covariate_effects_table.tex')
    for relative in table_paths:
        expected, actual = tabular(before(relative)), tabular((article / relative).read_text())
        tables[relative] = {'baseline_sha256': hashlib.sha256(expected.encode()).hexdigest(),
                            'current_sha256': hashlib.sha256(actual.encode()).hexdigest(),
                            'passed': expected == actual}
    old_appendix, appendix = before('appendices.tex'), (article / 'appendices.tex').read_text()
    algorithms_unchanged = ALGORITHMS.findall(old_appendix) == ALGORITHMS.findall(appendix)
    archived = 'tables/compact_publication/si_fitting_status.tex'
    archived_unchanged = before(archived).encode() == (article / archived).read_bytes()
    return {'baseline_commit': commit, 'mathematics': mathematics, 'tables': tables,
            'normalization': 'Ordered mathematical expressions: whitespace/labels only. Complete tabular blocks: balanced bold wrappers and whitespace only.',
            'algorithms_byte_identical': algorithms_unchanged,
            'removed_table_archive_byte_identical': archived_unchanged,
            'passed': all(v['passed'] for v in mathematics.values())
                      and all(v['passed'] for v in tables.values())
                      and algorithms_unchanged and archived_unchanged}


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
