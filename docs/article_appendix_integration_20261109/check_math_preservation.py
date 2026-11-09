#!/usr/bin/env python3
"""Check that appendix integration preserves ordered mathematical expressions.

Read the pre-integration commit from the neighboring baseline.json. Only the
requested JSON report is written; manuscript sources and Git state are read-only.
The comparison covers inline/display math and complete equation environments in
the main body and appendix fragment, plus the calibration table's tabular block.
Whitespace and equation labels are ignored within mathematical expressions;
every other character, expression order and environment delimiter is preserved.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


MATH = re.compile(
    r"\\begin\{(?P<env>alignat\*?|align\*?|equation\*?|gather\*?|"
    r"multline\*?|eqnarray\*?|displaymath|math)\}.*?\\end\{(?P=env)\}"
    r"|\\\(.*?\\\)|\\\[.*?\\\]"
    r"|(?<!\\)\$\$.*?(?<!\\)\$\$"
    r"|(?<!\\)\$(?!\$).*?(?<!\\)\$",
    re.DOTALL,
)
LABEL = re.compile(r"\\label\s*\{[^{}]*\}")
TABULAR = re.compile(rb"\\begin\{tabular\}.*?\\end\{tabular\}", re.DOTALL)


def historical(article: Path, commit: str, relative: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(article), "show", f"{commit}:{relative}"]
    )


def body(source: str, *, integrated: bool = False) -> str:
    if source.count(r"\maketitle") != 1:
        raise ValueError("Expected exactly one title boundary")
    if source.count(r"\bibliography{") != 1:
        raise ValueError("Expected exactly one bibliography boundary")
    result = source.split(r"\maketitle", 1)[1].split(r"\bibliography{", 1)[0]
    if integrated:
        if result.count(r"\begin{appendix}") != 1:
            raise ValueError("Expected exactly one integrated appendix boundary")
        result = result.split(r"\begin{appendix}", 1)[0]
    return result


def expressions(source: str) -> list[str]:
    return [re.sub(r"\s+", "", LABEL.sub("", match.group()))
            for match in MATH.finditer(source)]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compare_math(before: str, after: str) -> dict:
    expected, observed = expressions(before), expressions(after)
    differences = []
    for position in range(max(len(expected), len(observed))):
        old = expected[position] if position < len(expected) else None
        new = observed[position] if position < len(observed) else None
        if old != new:
            differences.append({"expression_index": position + 1,
                                "baseline": old, "current": new})
    encode = lambda values: json.dumps(values, ensure_ascii=False,
                                      separators=(",", ":")).encode()
    return {"baseline_expression_count": len(expected),
            "current_expression_count": len(observed),
            "baseline_sha256": digest(encode(expected)),
            "current_sha256": digest(encode(observed)),
            "differences": differences,
            "passed": expected == observed}


def calibration_block(source: bytes) -> bytes:
    blocks = TABULAR.findall(source)
    if len(blocks) != 1:
        raise ValueError("Expected exactly one calibration tabular block")
    return blocks[0]


def check(article: Path, baseline_path: Path) -> dict:
    baseline = json.loads(baseline_path.read_text())
    commit = baseline["article_commit"]
    before_main = historical(article, commit, "wileyNJD-APA.tex").decode()
    before_appendix = historical(article, commit, "supporting_information.tex").decode()
    current_main = (article / "wileyNJD-APA.tex").read_text()
    current_appendix = (article / "appendices.tex").read_text()
    main = compare_math(body(before_main), body(current_main, integrated=True))
    appendix = compare_math(body(before_appendix), current_appendix)
    relative = "tables/compact_publication/main_calibration.tex"
    expected = calibration_block(historical(article, commit, relative))
    observed = calibration_block((article / relative).read_bytes())
    calibration = {"path": relative,
                   "comparison": "Complete tabular block, byte-identical; note outside block excluded",
                   "baseline_sha256": digest(expected),
                   "current_sha256": digest(observed),
                   "passed": expected == observed}
    return {"created_utc": datetime.now(timezone.utc).isoformat(),
            "article_root": str(article), "baseline_file": str(baseline_path),
            "baseline_commit": commit,
            "normalization": "Remove whitespace and label commands only; preserve ordered expressions and all other characters",
            "main_math": main, "appendix_math": appendix,
            "calibration_table": calibration,
            "passed": main["passed"] and appendix["passed"] and calibration["passed"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    article = args.article_root.resolve()
    baseline_path = Path(__file__).resolve().with_name("baseline.json")
    try:
        report = check(article, baseline_path)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report = {"article_root": str(article), "baseline_file": str(baseline_path),
                  "passed": False, "error": str(error)}
    report_path = args.report.resolve()
    if report_path == baseline_path or article == report_path or article in report_path.parents:
        parser.error("Write the report outside the article repository and baseline file")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"passed": report["passed"], "report": str(report_path),
                      "main_expressions": report.get("main_math", {}).get("current_expression_count"),
                      "appendix_expressions": report.get("appendix_math", {}).get("current_expression_count")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
