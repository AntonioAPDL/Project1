#!/usr/bin/env python3
"""Retain the appendix proof checks and distinguish colliding exhibit numbers.

Tables B1/B2 and Figures B1/B2 have the same visible numbers. Their link types
must therefore come from the visible Figure(s)/Table(s) text, not destinations.
The historical validator remains unchanged; its two ambiguous table checks are
replaced by four contextual checks, retaining every other compiled-proof check.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
HISTORICAL_PATH = HERE.parent / 'article_appendix_integration_20261109/check_pdf_links.py'
SPEC = importlib.util.spec_from_file_location('historical_appendix_pdf_links', HISTORICAL_PATH)
assert SPEC and SPEC.loader
HISTORICAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HISTORICAL)

EXHIBITS = {
    ('table', 'B1'): 'tab:crps_all_origins',
    ('table', 'B2'): 'tab:component_comparison',
    ('figure', 'B1'): 'fig:forecast_origins_2021_early',
    ('figure', 'B2'): 'fig:forecast_origins_2021_2022',
}
REPLACED_CHECKS = {'main_table_link:' + EXHIBITS['table', number] for number in ('B1', 'B2')}
NUMBER = re.compile(r'^\s*(?:(?:Figures?|Tables?)\s+)?[\[(]?(B[12])(?![A-Za-z0-9]|\.\d)', re.I)
PREFIX = re.compile(r'\b(Figures?|Tables?)\b', re.I)
# The visible type may carry across "B1 and B2", but not arbitrary prose.
REFERENCE_LIST = re.compile(r'(?:\s|[A-Z]?\d+(?:\.\d+)*|and\b|or\b|to\b|[,;:&()\[\]–—-])*', re.I)


def text_and_anchors(element: ET.Element) -> tuple[str, list[dict]]:
    """Flatten one text line while retaining anchor offsets through inline tags."""
    parts, anchors, length = [], [], 0

    def append(value: str | None) -> None:
        nonlocal length
        if value:
            parts.append(value)
            length += len(value)

    def visit(node: ET.Element) -> None:
        start = length
        append(node.text)
        for child in node:
            visit(child)
            append(child.tail)
        if node.tag == 'a':
            anchors.append({'start': start, 'text': ''.join(node.itertext()),
                            'href': node.attrib.get('href', '')})

    visit(element)
    return ''.join(parts), sorted(anchors, key=lambda value: value['start'])


def contextual_links(pages: list[ET.Element], main_pages: set[int]) -> list[dict]:
    links = []
    for page in pages:
        source_page = int(page.attrib['number'])
        if source_page not in main_pages:
            continue
        for element in page.iter('text'):
            text, anchors = text_and_anchors(element)
            for anchor in anchors:
                number_match = NUMBER.search(anchor['text'])
                if not number_match:
                    continue
                number = number_match.group(1).upper()
                before = text[:anchor['start'] + number_match.start(1)]
                prefixes = list(PREFIX.finditer(before))
                kind = None
                if prefixes:
                    prefix = prefixes[-1]
                    if REFERENCE_LIST.fullmatch(before[prefix.end():]):
                        kind = 'figure' if prefix.group(1).lower().startswith('figure') else 'table'
                target = urlsplit(anchor['href'])
                target_page = (int(target.fragment) if not target.scheme and not target.netloc
                               and target.fragment.isdigit() else None)
                links.append({'source_page': source_page, 'target_page': target_page,
                              'number': number, 'kind': kind,
                              'text': anchor['text'].strip(), 'context': text})
    return links


def contextual_checks(pages: list[ET.Element], labels: dict, main_pages: set[int]) -> list[dict]:
    links = contextual_links(pages, main_pages)
    checks = []
    for (kind, number), label in EXHIBITS.items():
        expected_page = labels[label]['page']
        observed = [link for link in links if (link['kind'], link['number']) == (kind, number)]
        ambiguous = [link for link in links if link['number'] == number and link['kind'] is None]
        checks.append({
            'check': 'main_' + kind + '_link:' + label,
            'passed': bool(observed) and not ambiguous and
                      all(link['target_page'] == expected_page for link in observed),
            'details': {'label': label, 'expected_target_page': expected_page,
                        'links': observed, 'ambiguous_links': ambiguous},
        })
    return checks


def validate(proof_dir: Path, stem: str = 'main') -> dict:
    report = HISTORICAL.validate(proof_dir, stem)
    replaced = [check for check in report['checks'] if check['check'] in REPLACED_CHECKS]
    report['historical_checks_replaced'] = replaced
    report['historical_validator'] = str(HISTORICAL_PATH)
    report['checks'] = [check for check in report['checks'] if check['check'] not in REPLACED_CHECKS]
    report['schema_version'] = 2
    actual_stem = report['stem']
    paths = {suffix: proof_dir / f'{actual_stem}.{suffix}' for suffix in ('pdf', 'aux', 'log')}
    try:
        if len(replaced) != 2:
            raise ValueError('Historical validator did not reach both checks being replaced')
        labels, _ = HISTORICAL.auxiliary_labels(paths['aux'].read_text())
        with tempfile.TemporaryDirectory(prefix='foundation_pdf_links_') as directory:
            xml_path = Path(directory) / 'links.xml'
            command = ['pdftohtml', '-xml', '-hidden', '-i', '-enc', 'UTF-8',
                       str(paths['pdf']), str(xml_path)]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            report['commands'].append({'argv': command, 'returncode': result.returncode,
                                       'stderr': result.stderr})
            if result.returncode:
                raise ValueError('Contextual PDF extraction failed: ' + result.stderr.strip())
            pages = ET.parse(xml_path).findall('page')
        main_pages = set(range(1, labels['app:datahistories']['page']))
        report['checks'].extend(contextual_checks(pages, labels, main_pages))
        unchanged = report.get('input_sha256') == {
            suffix: HISTORICAL.digest(path) for suffix, path in paths.items()}
        if not unchanged:
            for check in report['checks']:
                if check['check'] == 'inputs_unchanged':
                    check['passed'] = False
                    check['details'] = 'Compiled inputs changed during contextual validation.'
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        report['checks'].extend({'check': 'main_' + kind + '_link:' + label,
                                 'passed': False, 'details': {'error': str(error)}}
                                for (kind, _), label in EXHIBITS.items())
    report['failed_checks'] = [check['check'] for check in report['checks'] if not check['passed']]
    report['passed'] = bool(report['checks']) and not report['failed_checks']
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof-dir', type=Path, required=True)
    parser.add_argument('--stem', default='main')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.proof_dir.resolve(), args.stem)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print('Foundation PDF links: ' + ('PASS' if report['passed'] else 'FAIL') +
          f" ({len(report['checks'])} checks; {report.get('page_count', '?')} pages)")
    if report['failed_checks']:
        print('Failed: ' + ', '.join(report['failed_checks']))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
