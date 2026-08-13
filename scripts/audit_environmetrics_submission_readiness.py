#!/usr/bin/env python3
"""Run a full Environmetrics submission-readiness audit.

The audit is intentionally a wrapper over existing validators plus additional
repository hygiene, LaTeX asset, text-marker, and public-release checks. It
writes a dated report under `_codex_work/` and does not relaunch model runs or
modify runtime artifacts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_ROOT = ROOT / "Evironmetrics---REVISED-DOC-Corrected-2"
CORRECTIONS_ROOT = Path("/data/muscat_data/jaguir26/Corrections---Project-1")
PUBLIC_REPRO_ROOT = ROOT.parent / "san-lorenzo-exdqlm-reproducibility"

FORBIDDEN_SUFFIXES = {
    ".RData",
    ".rda",
    ".rdata",
    ".nc",
    ".grib",
    ".grib2",
    ".zarr",
    ".pkl",
    ".pickle",
    ".parquet",
    ".feather",
    ".h5",
    ".hdf5",
}

TEXT_SUFFIXES = {
    ".R",
    ".Rmd",
    ".bib",
    ".bst",
    ".cff",
    ".cls",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".sty",
    ".tex",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_FILENAMES = {"Makefile", "LICENSE", ".gitignore"}

ARTICLE_FORBIDDEN_TRACKED_PREFIXES = (
    "isba2026_poster/",
    "reports/",
    "local_notes/",
)
ARTICLE_FORBIDDEN_TRACKED_NAMES = {
    "wileyNJD-APA.pdf",
    "main.pdf",
    "output.pdf",
    "wileyNJD-APA.aux",
    "wileyNJD-APA.log",
    "wileyNJD-APA.blg",
    "main.aux",
    "main.log",
    "output.aux",
    "output.log",
}
CORRECTIONS_FORBIDDEN_TRACKED_PREFIXES = ("local_notes/",)
CORRECTIONS_FORBIDDEN_TRACKED_NAMES = {
    "tracker_master.csv",
    "WORKFLOW.md",
    "CORRECTIONS_ARTICLE_CROSSWALK_AUDIT_PLAN_20260614.md",
    "main.aux",
    "main.log",
    "main.out",
    "main.pdf",
}

TEXT_MARKERS = (
    "https://github.com/AntonioAPDL/Project1",
    "PROJECT1_URL",
    "chatgpt",
    "codex",
    "ai-generated",
    "ai generated",
    "ai wording",
    "TODO",
    "FIXME",
    "\\todo",
    "\\hl{",
    "\\textcolor{red}",
    "\\sout{",
    "TBD",
    "???",
)

COMPILE_PROBLEM_PATTERNS = (
    "LaTeX Error",
    "Emergency stop",
    "Fatal error",
    "undefined citations",
    "There were undefined references",
    "LaTeX Warning: Citation",
    "LaTeX Warning: Reference",
)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class CommandRecord:
    name: str
    cmd: list[str]
    cwd: Path
    returncode: int
    stdout_path: Path
    stderr_path: Path

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class AuditState:
    report_dir: Path
    checks: list[Check] = field(default_factory=list)
    commands: list[CommandRecord] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(name, ok, detail))

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks) and all(command.ok for command in self.commands)


def is_text_like(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES or path.name in TEXT_FILENAMES


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def run_command(state: AuditState, name: str, cmd: list[str], cwd: Path, timeout: int | None = None) -> CommandRecord:
    logs = state.report_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")
    stdout_path = logs / f"{safe_name}.stdout.txt"
    stderr_path = logs / f"{safe_name}.stderr.txt"
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    record = CommandRecord(name, cmd, cwd, proc.returncode, stdout_path, stderr_path)
    state.commands.append(record)
    return record


def git_value(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def git_lines(cwd: Path, *args: str) -> list[str]:
    out = subprocess.check_output(["git", *args], cwd=cwd)
    return [item.decode("utf-8") for item in out.split(b"\0") if item]


def tracked_files(repo: Path) -> list[str]:
    return sorted(git_lines(repo, "ls-files", "-z"))


def text_for_tracked_file(repo: Path, tracked: str) -> str | None:
    path = repo / tracked
    if not path.is_file() or not is_text_like(path):
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def check_git_repo(state: AuditState, label: str, repo: Path, fetch: bool) -> None:
    if fetch:
        run_command(state, f"git_fetch_{label}", ["git", "fetch", "origin"], repo, timeout=120)
    status = git_value(repo, "status", "--porcelain")
    branch_status = git_value(repo, "status", "--short", "--branch")
    local_sha = git_value(repo, "rev-parse", "HEAD")
    remote_sha = git_value(repo, "rev-parse", "origin/main")
    remote_url = git_value(repo, "remote", "get-url", "origin")
    state.add(f"{label}: clean worktree", status == "", branch_status)
    state.add(
        f"{label}: local main matches origin/main",
        local_sha == remote_sha,
        f"local={local_sha[:12]} remote={remote_sha[:12]} remote_url={remote_url}",
    )


def check_tracked_hygiene(
    state: AuditState,
    label: str,
    repo: Path,
    forbidden_prefixes: tuple[str, ...] = (),
    forbidden_names: set[str] | None = None,
    max_file_mb: int | None = None,
) -> None:
    forbidden_names = forbidden_names or set()
    files = tracked_files(repo)
    bad_prefixes = [path for path in files if path.startswith(forbidden_prefixes)]
    bad_names = [path for path in files if Path(path).name in forbidden_names or path in forbidden_names]
    bad_suffixes = [path for path in files if Path(path).suffix in FORBIDDEN_SUFFIXES]
    state.add(f"{label}: no forbidden tracked prefixes", not bad_prefixes, ", ".join(bad_prefixes[:20]))
    state.add(f"{label}: no forbidden tracked build/process names", not bad_names, ", ".join(bad_names[:20]))
    state.add(f"{label}: no forbidden tracked runtime formats", not bad_suffixes, ", ".join(bad_suffixes[:20]))
    if max_file_mb is not None:
        limit = max_file_mb * 1024 * 1024
        oversized = []
        for path in files:
            full = repo / path
            if full.is_file() and full.stat().st_size > limit:
                oversized.append(f"{path} ({full.stat().st_size / (1024 * 1024):.1f} MB)")
        state.add(f"{label}: no tracked files over {max_file_mb} MB", not oversized, ", ".join(oversized[:20]))


def check_text_markers(state: AuditState, label: str, repo: Path, include_prefixes: tuple[str, ...] | None = None) -> None:
    hits: list[str] = []
    for path in tracked_files(repo):
        if include_prefixes is not None and not path.startswith(include_prefixes):
            continue
        text = text_for_tracked_file(repo, path)
        if text is None:
            continue
        lower = text.lower()
        for marker in TEXT_MARKERS:
            haystack = lower if marker.lower() == marker else text
            needle = marker if marker.lower() != marker else marker.lower()
            if needle in haystack:
                hits.append(f"{path}: {marker}")
    state.add(f"{label}: no stale/internal/draft text markers", not hits, "; ".join(hits[:30]))


def check_public_local_paths(state: AuditState, repo: Path) -> None:
    allowed = {"provenance/source_file_crosswalk.csv", "provenance/runtime_source_crosswalk.csv"}
    hits = []
    for path in tracked_files(repo):
        if path in allowed:
            continue
        text = text_for_tracked_file(repo, path)
        if text is None:
            continue
        if "/data/muscat_data/" in text or "/data/jaguir26/" in text:
            hits.append(path)
    state.add("public repo: no private absolute paths outside crosswalks", not hits, ", ".join(hits[:30]))


def check_latex_assets(state: AuditState, label: str, repo: Path, tex_files: list[str]) -> None:
    missing: list[str] = []
    include_graphics = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", re.DOTALL)
    input_re = re.compile(r"\\input\{([^}]+)\}")
    graphic_extensions = ("", ".pdf", ".png", ".jpg", ".jpeg", ".eps")
    for tex in tex_files:
        tex_path = repo / tex
        text = tex_path.read_text(encoding="utf-8")
        for raw in include_graphics.findall(text):
            target = raw.strip()
            if "\\" in target:
                continue
            candidates = [repo / target if ext == "" else repo / f"{target}{ext}" for ext in graphic_extensions]
            if not any(candidate.exists() for candidate in candidates):
                missing.append(f"{tex}: includegraphics {target}")
        for raw in input_re.findall(text):
            target = raw.strip()
            if "\\" in target:
                continue
            candidates = [repo / target, repo / f"{target}.tex"]
            if not any(candidate.exists() for candidate in candidates):
                missing.append(f"{tex}: input {target}")
    state.add(f"{label}: all local LaTeX graphics/inputs exist", not missing, "; ".join(missing[:30]))


def check_compile_log(state: AuditState, label: str, log_path: Path) -> None:
    if not log_path.exists():
        state.add(f"{label}: compile log exists", False, str(log_path))
        return
    text = log_path.read_text(encoding="utf-8", errors="replace")
    hits = []
    for marker in COMPILE_PROBLEM_PATTERNS:
        if marker in {"LaTeX Warning: Citation", "LaTeX Warning: Reference"}:
            if marker in text and "undefined" in text:
                hits.append(marker)
        elif marker in text:
            hits.append(marker)
    state.add(f"{label}: no unresolved compile markers", not hits, ", ".join(hits))


def compile_article(state: AuditState) -> None:
    job = "audit_wileyNJD-APA"
    commands = [
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"-jobname={job}", "wileyNJD-APA.tex"],
        ["bibtex", job],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"-jobname={job}", "wileyNJD-APA.tex"],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"-jobname={job}", "wileyNJD-APA.tex"],
    ]
    for i, cmd in enumerate(commands, start=1):
        run_command(state, f"compile_article_{i}_{cmd[0]}", cmd, ARTICLE_ROOT, timeout=240)
    pdf = ARTICLE_ROOT / f"{job}.pdf"
    state.add("article compile: audit PDF exists", pdf.exists() and pdf.stat().st_size > 0, str(pdf))
    check_compile_log(state, "article compile", ARTICLE_ROOT / f"{job}.log")


def compile_corrections(state: AuditState) -> None:
    run_command(state, "compile_corrections_make", ["make"], CORRECTIONS_ROOT, timeout=180)
    pdf = CORRECTIONS_ROOT / "main.pdf"
    state.add("corrections compile: PDF exists", pdf.exists() and pdf.stat().st_size > 0, str(pdf))
    check_compile_log(state, "corrections compile", CORRECTIONS_ROOT / "main.log")


def optional_pdfinfo(state: AuditState) -> None:
    if shutil.which("pdfinfo") is None:
        state.add("optional pdfinfo available", True, "pdfinfo not installed; skipped page-count audit")
        return
    run_command(state, "pdfinfo_article_audit_pdf", ["pdfinfo", "audit_wileyNJD-APA.pdf"], ARTICLE_ROOT, timeout=30)
    run_command(state, "pdfinfo_corrections_pdf", ["pdfinfo", "main.pdf"], CORRECTIONS_ROOT, timeout=30)


def run_existing_validators(state: AuditState) -> None:
    run_command(state, "workflow_validate_publication_freeze", ["python3", "scripts/validate_publication_freeze.py"], ROOT, timeout=240)
    run_command(
        state,
        "workflow_validate_revision_cross_repo_wiring",
        ["python3", "scripts/validate_revision_cross_repo_wiring.py", "--after-patch"],
        ROOT,
        timeout=240,
    )
    run_command(state, "workflow_validate_current_authority_sync", ["bash", "scripts/validate_current_authority_sync.sh"], ROOT, timeout=360)
    run_command(
        state,
        "workflow_test_software_availability_contract",
        ["python3", "-m", "pytest", "tests/python/test_software_availability_contract.py", "-q"],
        ROOT,
        timeout=180,
    )
    run_command(
        state,
        "article_test_a1_and_table_contracts",
        ["python3", "-m", "pytest", "tests/test_article_a1_and_table_contracts.py", "-q"],
        ARTICLE_ROOT,
        timeout=180,
    )
    run_command(
        state,
        "article_test_corrections_generated_table_sync",
        ["python3", "-m", "pytest", "tests/test_corrections_generated_table_sync.py", "-q"],
        ARTICLE_ROOT,
        timeout=180,
    )
    run_command(state, "public_repro_make_validate", ["make", "validate"], PUBLIC_REPRO_ROOT, timeout=180)


def write_report(state: AuditState, started: dt.datetime, finished: dt.datetime) -> Path:
    report = state.report_dir / "submission_readiness_audit_report.md"
    lines = [
        "# Environmetrics Submission Readiness Audit",
        "",
        f"Started: {started.isoformat(timespec='seconds')}",
        f"Finished: {finished.isoformat(timespec='seconds')}",
        f"Result: {'PASS' if state.ok else 'FAIL'}",
        "",
        "## Repository Roots",
        "",
        f"- Workflow: `{ROOT}`",
        f"- Revised article: `{ARTICLE_ROOT}`",
        f"- Corrections response: `{CORRECTIONS_ROOT}`",
        f"- Public reproducibility: `{PUBLIC_REPRO_ROOT}`",
        "",
        "## Checks",
        "",
        "| Status | Check | Detail |",
        "|---|---|---|",
    ]
    for check in state.checks:
        detail = check.detail.replace("\n", " ")[:500]
        lines.append(f"| {'PASS' if check.ok else 'FAIL'} | {check.name} | {detail} |")
    lines.extend(["", "## Commands", "", "| Status | Name | Command | CWD | Logs |", "|---|---|---|---|---|"])
    for command in state.commands:
        cmd = " ".join(command.cmd)
        stdout = command.stdout_path.relative_to(state.report_dir).as_posix()
        stderr = command.stderr_path.relative_to(state.report_dir).as_posix()
        lines.append(
            f"| {'PASS' if command.ok else 'FAIL'} | {command.name} | `{cmd}` | `{command.cwd}` | `{stdout}`, `{stderr}` |"
        )
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-fetch", action="store_true", help="Do not fetch remotes before SHA comparisons.")
    parser.add_argument("--report-dir", type=Path, default=None, help="Override the dated report directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = dt.datetime.now(dt.timezone.utc).astimezone()
    stamp = started.strftime("%Y%m%d_%H%M%S")
    report_dir = args.report_dir or (ROOT / "_codex_work" / f"submission_readiness_audit_{stamp}")
    report_dir.mkdir(parents=True, exist_ok=True)
    state = AuditState(report_dir=report_dir)

    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    repos = {
        "workflow": ROOT,
        "article": ARTICLE_ROOT,
        "corrections": CORRECTIONS_ROOT,
        "public_repro": PUBLIC_REPRO_ROOT,
    }
    for label, repo in repos.items():
        check_git_repo(state, label, repo, fetch=not args.skip_fetch)

    check_tracked_hygiene(state, "workflow", ROOT)
    check_tracked_hygiene(
        state,
        "article",
        ARTICLE_ROOT,
        ARTICLE_FORBIDDEN_TRACKED_PREFIXES,
        ARTICLE_FORBIDDEN_TRACKED_NAMES,
    )
    check_tracked_hygiene(
        state,
        "corrections",
        CORRECTIONS_ROOT,
        CORRECTIONS_FORBIDDEN_TRACKED_PREFIXES,
        CORRECTIONS_FORBIDDEN_TRACKED_NAMES,
    )
    check_tracked_hygiene(state, "public repo", PUBLIC_REPRO_ROOT, max_file_mb=100)

    check_text_markers(state, "article", ARTICLE_ROOT)
    check_text_markers(state, "corrections", CORRECTIONS_ROOT)
    check_text_markers(state, "public repo", PUBLIC_REPRO_ROOT)
    check_public_local_paths(state, PUBLIC_REPRO_ROOT)

    check_latex_assets(state, "article", ARTICLE_ROOT, ["main.tex", "wileyNJD-APA.tex"])
    check_latex_assets(state, "corrections", CORRECTIONS_ROOT, ["main.tex"])

    compile_article(state)
    compile_corrections(state)
    optional_pdfinfo(state)
    run_existing_validators(state)

    for label, repo in repos.items():
        check_git_repo(state, f"{label}_post_audit", repo, fetch=False)

    finished = dt.datetime.now(dt.timezone.utc).astimezone()
    report = write_report(state, started, finished)
    print(f"Audit report: {report}")
    print(f"Audit result: {'PASS' if state.ok else 'FAIL'}")
    return 0 if state.ok else 1


if __name__ == "__main__":
    sys.exit(main())
