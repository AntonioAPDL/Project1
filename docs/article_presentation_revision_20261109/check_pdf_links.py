#!/usr/bin/env python3
"""Check the current article's numbered exhibits and compiled internal links.

Expected table and figure labels come from the active publication inventory;
numbers come from their reachable TeX order and appendix sections. Visible
Table/Figure context disambiguates colliding numbers. Historical release
validators and their evidence are not modified or imported.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
DEFAULT_ARTICLE = HERE.parents[1] / 'Evironmetrics----Corrected-3'
SECTIONS = {'app:datahistories': 'A', 'app:extras': 'B',
            'app:stateconstruction': 'C', 'app:vbupdates': 'D'}
ALGORITHMS = {'alg:Alg3': 'D1', 'alg:Alg4': 'D2'}
REMOVED_LABELS = {'tab:fitting_status', 'app:fitdiagnostics'}
PREFIX = re.compile(r'\b(Figures?|Tables?)\b', re.I)
REFERENCE_LIST = re.compile(r'(?:\s|[A-Z]?\d+(?:\.\d+)*|and\b|or\b|to\b|[,;:&()\[\]–—-])*', re.I)
NUMBER = re.compile(r'^\s*(?:(?:Figures?|Tables?)\s+)?[\[(]?([A-Z]?\d+)(?![A-Za-z0-9]|\.\d)', re.I)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group(text: str, start: int) -> tuple[str, int]:
    if start >= len(text) or text[start] != '{':
        raise ValueError(f'Expected TeX group at offset {start}')
    depth, index = 1, start + 1
    while index < len(text):
        if text[index] == '\\':
            index += 2
            continue
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if not depth:
                return text[start + 1:index], index + 1
        index += 1
    raise ValueError('Unterminated TeX group')


def auxiliary_labels(text: str) -> tuple[dict, list[str]]:
    labels, duplicates = {}, []
    for match in re.finditer(r'(?m)^\\newlabel(?=\{)', text):
        key, position = group(text, match.end())
        value, _ = group(text, position)
        fields, position = [], 0
        while position < len(value):
            if value[position].isspace():
                position += 1
                continue
            field, position = group(value, position)
            fields.append(field)
        if len(fields) < 4 or not fields[1].isdigit():
            raise ValueError(f'Incomplete or nonnumeric compiled label: {key}')
        if key in labels:
            duplicates.append(key)
        labels[key] = {'number': fields[0], 'page': int(fields[1]),
                       'title': fields[2], 'anchor': fields[3]}
    return labels, duplicates


def reachable_source(article_root: Path, entry: str) -> tuple[str, dict[str, str]]:
    """Expand literal TeX inputs; only read files within the article directory."""
    inputs = {}

    def expand(relative: str, stack: tuple[Path, ...]) -> str:
        path = (article_root / relative).resolve()
        if not path.suffix:
            path = path.with_suffix('.tex')
        path.relative_to(article_root.resolve())
        if path in stack:
            raise ValueError(f'Cyclic TeX input: {path}')
        source = path.read_text()
        inputs[str(path.relative_to(article_root.resolve()))] = digest(path)
        source = re.sub(r'(?<!\\)%[^\n]*', '', source)
        return re.sub(r'\\(?:input|include)\{([^{}]+)\}',
                      lambda match: expand(match.group(1), (*stack, path)), source)

    return expand(entry, ()), inputs


def expected_exhibits(inventory: dict, source: str) -> dict[str, dict]:
    """Assign counters independently from compiled labels or link targets."""
    appendix = re.search(r'\\begin\{appendix\}', source)
    if not appendix:
        raise ValueError('Integrated appendix environment is absent')
    section_positions = [match.start() for match in
                         re.finditer(r'\\section\s*\{', source[appendix.end():])]
    section_positions = [position + appendix.end() for position in section_positions]
    ordered = []
    for asset in inventory['submitted_assets']:
        if asset['kind'] not in {'table', 'figure'}:
            continue
        label = asset['label']
        occurrences = list(re.finditer(r'\\label\s*\{' + re.escape(label) + r'\}', source))
        if len(occurrences) != 1:
            raise ValueError(f'Expected exactly one reachable definition of {label}; found {len(occurrences)}')
        position = occurrences[0].start()
        scope = 'appendix' if position > appendix.start() else 'main'
        if scope != asset['scope']:
            raise ValueError(f'Inventory/source scope mismatch: {label}')
        section_count = sum(position > section_position for section_position in section_positions)
        prefix = chr(64 + section_count) if scope == 'appendix' and section_count else ''
        if scope == 'appendix' and not prefix:
            raise ValueError(f'Appendix exhibit outside a section: {label}')
        ordered.append((position, label, asset['kind'], scope, prefix))
    counters, result = defaultdict(int), {}
    for _, label, kind, scope, prefix in sorted(ordered):
        counters[kind, prefix] += 1
        if label in result:
            raise ValueError(f'Duplicate inventory label: {label}')
        result[label] = {'kind': kind, 'scope': scope,
                         'number': prefix + str(counters[kind, prefix])}
    return result


def text_and_anchors(element: ET.Element) -> tuple[str, list[dict]]:
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


def continued_reference_kind(previous: tuple[ET.Element, str] | None,
                             element: ET.Element, before: str) -> tuple[str | None, str | None]:
    """Carry a visible type only across adjacent, nearby coordinated lines."""
    if previous is None or not REFERENCE_LIST.fullmatch(before) or not re.match(
            r'^\s*(?:(?:and|or|to)\b|[–—-])', before, re.I):
        return None, None
    previous_element, previous_text = previous
    try:
        height = max(float(previous_element.attrib['height']), float(element.attrib['height']))
        advance = float(element.attrib['top']) - float(previous_element.attrib['top'])
        indent = abs(float(element.attrib['left']) - float(previous_element.attrib['left']))
    except (KeyError, ValueError):
        return None, None
    # Poppler emits text nodes in document order. Require the immediately
    # preceding line in the same text column, with ordinary line spacing.
    if height <= 0 or not 0 < advance <= 2.2 * height or indent > 1.5 * height:
        return None, None
    prefixes = list(PREFIX.finditer(previous_text))
    if not prefixes or not REFERENCE_LIST.fullmatch(previous_text[prefixes[-1].end():]):
        return None, None
    prefix = prefixes[-1]
    kind = 'figure' if prefix.group(1).lower().startswith('figure') else 'table'
    return kind, previous_text


def contextual_links(pages: list[ET.Element], pages_allowed: set[int]) -> list[dict]:
    links = []
    for page in pages:
        source_page = int(page.attrib['number'])
        if source_page not in pages_allowed:
            continue
        previous = None
        for element in page.iter('text'):
            text, anchors = text_and_anchors(element)
            for anchor in anchors:
                number_match = NUMBER.search(anchor['text'])
                if not number_match:
                    continue
                before = text[:anchor['start'] + number_match.start(1)]
                prefixes, kind, continued_from = list(PREFIX.finditer(before)), None, None
                if prefixes:
                    prefix = prefixes[-1]
                    if REFERENCE_LIST.fullmatch(before[prefix.end():]):
                        kind = 'figure' if prefix.group(1).lower().startswith('figure') else 'table'
                if kind is None:
                    kind, continued_from = continued_reference_kind(previous, element, before)
                target = urlsplit(anchor['href'])
                target_page = (int(target.fragment) if not target.scheme and not target.netloc
                               and target.fragment.isdigit() else None)
                links.append({'source_page': source_page, 'target_page': target_page,
                              'number': number_match.group(1).upper(), 'kind': kind,
                              'text': anchor['text'].strip(), 'context': text,
                              'continued_from': continued_from})
            previous = (element, text)
    return links


def contextual_checks(pages: list[ET.Element], labels: dict, expected: dict,
                      main_pages: set[int]) -> list[dict]:
    """Require main-body links and verify every typed exhibit link in the PDF."""
    all_pages = {int(page.attrib['number']) for page in pages}
    all_links = contextual_links(pages, all_pages)
    checks = []
    for label, item in expected.items():
        kind, number = item['kind'], item['number']
        observed = [link for link in all_links if (link['kind'], link['number']) == (kind, number)]
        main_links = [link for link in observed if link['source_page'] in main_pages]
        # Main figures/tables and Appendix B's comparisons/predictions must be
        # referenced in the main article. Appendix A's context figures are
        # introduced locally and checked there.
        require_main = item['scope'] == 'main' or number.startswith('B')
        ambiguous = [link for link in all_links if link['number'] == number and
                     link['kind'] is None and number.startswith(('A', 'B'))]
        target_page = labels.get(label, {}).get('page')
        checks.append({'check': 'exhibit_links:' + label,
                       'passed': bool(observed) and (bool(main_links) or not require_main)
                       and not ambiguous and target_page is not None
                       and all(link['target_page'] == target_page for link in observed),
                       'details': {'expected_target_page': target_page, 'requires_main_link': require_main,
                                   'links': observed, 'main_links': main_links,
                                   'ambiguous_links': ambiguous}})
    known = {(item['kind'], item['number']) for item in expected.values()}
    stale = [link for link in all_links if link['kind'] and (link['kind'], link['number']) not in known]
    checks.append({'check': 'no_unknown_exhibit_references', 'passed': not stale, 'details': stale})
    return checks


def caption_checks(pages: list[ET.Element], labels: dict, expected: dict) -> list[dict]:
    """Caption headings provide a PDF-level check independent of aux pages."""
    headings = defaultdict(list)
    for page in pages:
        for element in page.iter('text'):
            text = ''.join(element.itertext()).strip()
            match = re.fullmatch(r'(TABLE|FIGURE)\s+([A-Z]?\d+)', text)
            if match:
                headings[match.group(1).lower(), match.group(2)].append(int(page.attrib['number']))
    checks = []
    for label, item in expected.items():
        observed = headings[item['kind'], item['number']]
        expected_page = labels.get(label, {}).get('page')
        checks.append({'check': 'caption_page:' + label,
                       'passed': observed == [expected_page],
                       'details': {'expected_page': expected_page, 'caption_pages': observed}})
    unknown = {f'{kind} {number}': values for (kind, number), values in headings.items()
               if (kind, number) not in {(item['kind'], item['number']) for item in expected.values()}}
    checks.append({'check': 'no_uninventoried_caption', 'passed': not unknown, 'details': unknown})
    return checks


def removed_content_checks(source: str, labels: dict, pdf_text: str) -> list[dict]:
    source_labels = set(re.findall(r'\\(?:label|ref)\s*\{([^{}]+)\}', source))
    stale = sorted(REMOVED_LABELS & (source_labels | set(labels)))
    display = re.findall(r'Recorded\s+stopping\s+classifications|Component-Removal\s+Comparisons\s+and\s+Fitting\s+Evidence',
                         pdf_text, re.I)
    return [{'check': 'removed_classification_labels_absent', 'passed': not stale, 'details': stale},
            {'check': 'removed_classification_display_absent', 'passed': not display, 'details': display}]


def validate(proof_dir: Path, stem: str = 'main', article_root: Path = DEFAULT_ARTICLE) -> dict:
    checks, commands = [], []

    def check(name: str, passed: bool, details) -> None:
        checks.append({'check': name, 'passed': bool(passed), 'details': details})

    def run(argv: list[str]) -> str:
        result = subprocess.run(argv, text=True, capture_output=True, check=False)
        commands.append({'argv': argv, 'returncode': result.returncode, 'stderr': result.stderr})
        if result.returncode:
            raise ValueError(f'Command failed: {argv[0]}: {result.stderr.strip()}')
        return result.stdout

    if not (proof_dir / f'{stem}.pdf').is_file() and stem == 'main':
        pdfs = sorted(proof_dir.glob('*.pdf'))
        if len(pdfs) == 1:
            stem = pdfs[0].stem
    paths = {suffix: proof_dir / f'{stem}.{suffix}' for suffix in ('pdf', 'aux', 'log')}
    report = {'schema_version': 1, 'proof_dir': str(proof_dir), 'stem': stem,
              'article_root': str(article_root), 'checks': checks, 'commands': commands}
    try:
        before = {suffix: digest(path) for suffix, path in paths.items()}
        inventory_path = article_root / 'PUBLICATION_PACKAGE.json'
        inventory_digest = digest(inventory_path)
        inventory = json.loads(inventory_path.read_text())
        entry = inventory['documents']['main']['entry']
        source, source_hashes = reachable_source(article_root, entry)
        expected = expected_exhibits(inventory, source)
        report.update(input_sha256=before, inventory_sha256=inventory_digest,
                      source_sha256=source_hashes, expected_exhibits=expected)
        labels, duplicates = auxiliary_labels(paths['aux'].read_text())
        report['labels'] = labels
        check('unique_auxiliary_labels', not duplicates, duplicates)
        log = paths['log'].read_text(errors='replace')
        warnings = [line.strip() for line in log.splitlines() if re.search(
            r'undefined|multiply[ -]defined|destination with the same identifier|duplicate.*destination', line, re.I)]
        check('no_undefined_or_duplicate_destinations', not warnings, warnings)
        for key, number in {**SECTIONS, **ALGORITHMS,
                            **{key: item['number'] for key, item in expected.items()}}.items():
            observed = labels.get(key)
            check('label:' + key, observed is not None and observed['number'] == number,
                  {'expected_number': number, 'observed': observed})
        expected_assets = set(expected)
        compiled_assets = {key for key in labels if key.startswith(('tab:', 'fig:'))}
        check('compiled_exhibits_match_active_inventory', compiled_assets == expected_assets,
              {'unexpected': sorted(compiled_assets - expected_assets),
               'missing': sorted(expected_assets - compiled_assets)})
        main_three = expected.get('tab:no_refit_calibration', {})
        check('main_table_3_retained', main_three.get('number') == '3' and main_three.get('scope') == 'main', main_three)
        observed_sections = {value['number'] for value in labels.values() if value['anchor'].startswith('Appendix.')}
        check('four_appendix_sections', observed_sections == set(SECTIONS.values()), sorted(observed_sections))
        selector = labels.get('app:stackedstates', {})
        check('selector_subsection_anchor', selector.get('number') == 'C.5' and
              selector.get('anchor', '').startswith('subsection.'), selector)
        component = labels.get('app:he3ablation', {})
        check('component_subsection_anchor', component.get('number') == 'B.2' and
              component.get('anchor', '').startswith('subsection.'), component)
        info = run(['pdfinfo', str(paths['pdf'])])
        page_match = re.search(r'(?m)^Pages:\s+(\d+)\s*$', info)
        if not page_match:
            raise ValueError('pdfinfo did not return a page count')
        total_pages = int(page_match.group(1))
        report['page_count'] = total_pages
        text = run(['pdftotext', '-layout', str(paths['pdf']), '-'])
        reference_count = len(re.findall(r'(?im)^\s*References\s*$', text))
        check('one_bibliography', reference_count == 1, {'reference_headings': reference_count})
        check('no_separate_support_heading', not re.search(
            r'Supporting Information|Supplementary (?:Information|Material)', text, re.I),
              'One article includes its appendices.')
        checks.extend(removed_content_checks(source, labels, text))
        with tempfile.TemporaryDirectory(prefix='presentation_links_') as directory:
            xml_path = Path(directory) / 'links.xml'
            run(['pdftohtml', '-xml', '-hidden', '-i', '-enc', 'UTF-8', str(paths['pdf']), str(xml_path)])
            pages = ET.parse(xml_path).findall('page')
        check('complete_pdf_page_extraction',
              [int(page.attrib['number']) for page in pages] == list(range(1, total_pages + 1)),
              {'xml_pages': len(pages), 'pdf_pages': total_pages})
        invalid_labels = {key: value['page'] for key, value in labels.items()
                          if not 1 <= value['page'] <= total_pages}
        check('compiled_label_pages_exist', not invalid_labels, invalid_labels)
        links = []
        for page in pages:
            for anchor in page.iter('a'):
                parts = urlsplit(anchor.attrib.get('href', ''))
                if parts.scheme or parts.netloc or not parts.fragment.isdigit():
                    continue
                links.append({'source_page': int(page.attrib['number']), 'target_page': int(parts.fragment),
                              'text': ''.join(anchor.itertext()).strip()})
        report['internal_link_count'] = len(links)
        invalid_links = [link for link in links if not 1 <= link['target_page'] <= total_pages]
        check('internal_link_pages_exist', not invalid_links, invalid_links)
        appendix_start = labels['app:datahistories']['page']
        main_pages = set(range(1, appendix_start))
        report['main_reference_page_range'] = [1, appendix_start - 1]
        checks.extend(caption_checks(pages, labels, expected))
        checks.extend(contextual_checks(pages, labels, expected, main_pages))

        def linked_number(key: str, pages_allowed: set[int], name: str) -> None:
            expected_label = labels[key]
            pattern = re.compile(r'^\s*[\[(]?' + re.escape(expected_label['number']) + r'(?![A-Za-z0-9]|\.\d)')
            observed = [link for link in links if link['source_page'] in pages_allowed and pattern.search(link['text'])]
            check(name, bool(observed) and all(link['target_page'] == expected_label['page'] for link in observed),
                  {'label': key, 'expected_target_page': expected_label['page'], 'links': observed})

        for key in ('app:stackedstates', 'app:vbupdates'):
            linked_number(key, main_pages, 'main_technical_link:' + key)
        for key in ALGORITHMS:
            linked_number(key, {labels['app:vbupdates']['page']}, 'algorithm_introduction_link:' + key)
        linked_number('app:stackedstates', {labels['alg:Alg4']['page']}, 'filtering_selector_link')
        check('inputs_unchanged', before == {suffix: digest(path) for suffix, path in paths.items()} and
              inventory_digest == digest(inventory_path) and
              source_hashes == {path: digest(article_root / path) for path in source_hashes},
              'Compiled proof, active inventory and reachable TeX inputs are unchanged by validation.')
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        check('validator_execution', False, str(error))
    report['failed_checks'] = [check['check'] for check in checks if not check['passed']]
    report['passed'] = bool(checks) and not report['failed_checks']
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path, default=DEFAULT_ARTICLE)
    parser.add_argument('--proof-dir', type=Path, required=True)
    parser.add_argument('--stem', default='main')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.proof_dir.resolve(), args.stem, args.article_root.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print('Presentation PDF links: ' + ('PASS' if result['passed'] else 'FAIL') +
          f" ({len(result['checks'])} checks; {result.get('page_count', '?')} pages)")
    if result['failed_checks']:
        print('Failed: ' + ', '.join(result['failed_checks']))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
