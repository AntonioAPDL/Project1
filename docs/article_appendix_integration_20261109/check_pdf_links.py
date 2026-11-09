#!/usr/bin/env python3
"""Validate the single article's compiled appendix numbers and internal links.

Only Python's standard library is used. Poppler supplies pdfinfo, pdftotext and
pdftohtml; their output is generated in a temporary directory. The existing PDF,
auxiliary file and log are read without modification. Expected destination pages
come from the compiled auxiliary labels, rather than a frozen pagination.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


SECTIONS = {
    "app:datahistories": "A", "app:extras": "B",
    "app:stateconstruction": "C", "app:vbupdates": "D",
}
TABLES = {
    "tab:crps_all_origins": "B1", "tab:component_comparison": "B2",
    "tab:fitting_status": "B3", "tab:quantile_check_loss": "B4",
    "tab:exact_score_sensitivity": "B5", "tab:discharge_scale_scores": "B6",
    "tab:origin_interval_coverage": "B7", "tab:components_23_31": "B8",
}
FIGURES = {
    "fig:covariates": "A1", "fig:retrospectives": "A2",
    "fig:forecast_origins_2021_early": "B1",
    "fig:forecast_origins_2021_2022": "B2",
}
ALGORITHMS = {"alg:Alg3": "D1", "alg:Alg4": "D2"}


def group(text: str, start: int) -> tuple[str, int]:
    """Read one balanced TeX brace group, allowing escaped literal braces."""
    if start >= len(text) or text[start] != "{":
        raise ValueError(f"Expected TeX group at offset {start}")
    depth, index = 1, start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if not depth:
                return text[start + 1:index], index + 1
        index += 1
    raise ValueError("Unterminated TeX group")


def auxiliary_labels(text: str) -> tuple[dict, list[str]]:
    labels, duplicates = {}, []
    for match in re.finditer(r"(?m)^\\newlabel(?=\{)", text):
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
            raise ValueError(f"Incomplete or nonnumeric compiled label: {key}")
        if key in labels:
            duplicates.append(key)
        labels[key] = {"number": fields[0], "page": int(fields[1]),
                       "title": fields[2], "anchor": fields[3]}
    return labels, duplicates


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(proof_dir: Path, stem: str) -> dict:
    checks, commands = [], []

    def check(name: str, passed: bool, details) -> None:
        checks.append({"check": name, "passed": bool(passed), "details": details})

    def run(argv: list[str]) -> str:
        result = subprocess.run(argv, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False)
        commands.append({"argv": argv, "returncode": result.returncode,
                         "stderr": result.stderr})
        if result.returncode:
            raise ValueError(f"Command failed: {argv[0]}: {result.stderr.strip()}")
        return result.stdout

    if not (proof_dir / f"{stem}.pdf").is_file() and stem == "main":
        pdfs = sorted(proof_dir.glob("*.pdf"))
        if len(pdfs) == 1:
            stem = pdfs[0].stem
    paths = {suffix: proof_dir / f"{stem}.{suffix}" for suffix in ("pdf", "aux", "log")}
    report = {"schema_version": 1, "proof_dir": str(proof_dir), "stem": stem,
              "checks": checks, "commands": commands}
    try:
        for path in paths.values():
            if not path.is_file():
                raise ValueError(f"Missing compiled proof input: {path}")
        before = {suffix: digest(path) for suffix, path in paths.items()}
        report["input_sha256"] = before
        labels, duplicates = auxiliary_labels(paths["aux"].read_text())
        report["labels"] = {key: labels.get(key) for key in
                            (*SECTIONS, *TABLES, *FIGURES, *ALGORITHMS,
                             "app:stackedstates", "app:he3ablation", "app:fitdiagnostics")}
        check("unique_auxiliary_labels", not duplicates, duplicates)
        log = paths["log"].read_text(errors="replace")
        warnings = [line.strip() for line in log.splitlines() if re.search(
            r"undefined|multiply[ -]defined|destination with the same identifier|duplicate.*destination",
            line, re.I)]
        check("no_undefined_or_duplicate_destinations", not warnings, warnings)
        for key, number in {**SECTIONS, **TABLES, **FIGURES, **ALGORITHMS}.items():
            observed = labels.get(key)
            check("label:" + key, observed is not None and observed["number"] == number,
                  {"expected_number": number, "observed": observed})
        observed_sections = {value["number"] for value in labels.values()
                             if value["anchor"].startswith("Appendix.")}
        check("four_appendix_sections", observed_sections == set(SECTIONS.values()),
              sorted(observed_sections))
        fit = labels.get("app:fitdiagnostics", {})
        component = labels.get("app:he3ablation", {})
        check("fitting_subsection_anchor", bool(fit) and
              fit.get("number") == component.get("number") == "B.2" and
              fit.get("anchor") == component.get("anchor") and
              fit.get("anchor", "").startswith("subsection."),
              {"fitting": fit, "component_subsection": component})
        selector = labels.get("app:stackedstates", {})
        check("selector_subsection_anchor", selector.get("number") == "C.5" and
              selector.get("anchor", "").startswith("subsection."), selector)

        info = run(["pdfinfo", str(paths["pdf"])])
        page_match = re.search(r"(?m)^Pages:\s+(\d+)\s*$", info)
        if not page_match:
            raise ValueError("pdfinfo did not return a page count")
        total_pages = int(page_match.group(1))
        report["page_count"] = total_pages
        text = run(["pdftotext", "-layout", str(paths["pdf"]), "-"])
        check("one_bibliography", len(re.findall(r"(?im)^\s*References\s*$", text)) == 1,
              {"reference_headings": len(re.findall(r"(?im)^\s*References\s*$", text))})
        check("no_separate_support_heading", not re.search(
            r"Supporting Information|Supplementary (?:Information|Material)", text, re.I),
              "A single article includes its appendices.")
        with tempfile.TemporaryDirectory(prefix="appendix_links_") as temporary:
            xml_path = Path(temporary) / "links.xml"
            run(["pdftohtml", "-xml", "-hidden", "-i", "-enc", "UTF-8",
                 str(paths["pdf"]), str(xml_path)])
            tree = ET.parse(xml_path)
        pages = tree.findall("page")
        check("complete_pdf_page_extraction",
              [int(page.attrib["number"]) for page in pages] == list(range(1, total_pages + 1)),
              {"xml_pages": len(pages), "pdf_pages": total_pages})
        links = []
        for page in pages:
            source_page = int(page.attrib["number"])
            for anchor in page.iter("a"):
                href = anchor.attrib.get("href", "")
                parts = urlsplit(href)
                if parts.scheme or parts.netloc or not parts.fragment.isdigit():
                    continue
                links.append({"source_page": source_page, "target_page": int(parts.fragment),
                              "text": "".join(anchor.itertext()).strip()})
        report["internal_link_count"] = len(links)
        check("internal_link_pages_exist", all(1 <= link["target_page"] <= total_pages for link in links),
              [link for link in links if not 1 <= link["target_page"] <= total_pages])
        appendix_start = labels["app:datahistories"]["page"]
        report["main_reference_page_range"] = [1, appendix_start - 1]

        def linked_number(key: str, *, pages_allowed: set[int], name: str) -> None:
            expected = labels[key]
            # Match the visible number at the start of its annotation. In
            # particular, the range A--D is not a separate visible D annotation.
            # Poppler can include sentence punctuation in an annotation (C.5.).
            # Permit that period, while keeping C.5 distinct from C.5.1.
            pattern = re.compile(r"^\s*[\[(]?" + re.escape(expected["number"]) + r"(?![A-Za-z0-9]|\.\d)")
            observed = [link for link in links if link["source_page"] in pages_allowed
                        and pattern.search(link["text"])]
            check(name, bool(observed) and all(link["target_page"] == expected["page"]
                                             for link in observed),
                  {"label": key, "expected_target_page": expected["page"], "links": observed})

        main_pages = set(range(1, appendix_start))
        for key in TABLES:
            linked_number(key, pages_allowed=main_pages, name="main_table_link:" + key)
        for key in ("app:stackedstates", "app:vbupdates"):
            linked_number(key, pages_allowed=main_pages, name="main_technical_link:" + key)
        for key in ALGORITHMS:
            linked_number(key, pages_allowed={labels["app:vbupdates"]["page"]},
                          name="algorithm_introduction_link:" + key)
        linked_number("app:stackedstates", pages_allowed={labels["alg:Alg4"]["page"]},
                      name="filtering_selector_link")
        check("inputs_unchanged", before == {suffix: digest(path) for suffix, path in paths.items()},
              "The PDF, auxiliary labels and LaTeX log are unchanged by validation.")
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        check("validator_execution", False, str(error))
    report["passed"] = bool(checks) and all(check["passed"] for check in checks)
    report["failed_checks"] = [check["check"] for check in checks if not check["passed"]]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-dir", type=Path, required=True)
    parser.add_argument("--stem", default="main")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.proof_dir.resolve(), args.stem)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print("Appendix PDF links: " + ("PASS" if result["passed"] else "FAIL") +
          f" ({len(result['checks'])} checks; {result.get('page_count', '?')} pages)")
    if result["failed_checks"]:
        print("Failed: " + ", ".join(result["failed_checks"]))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
