#!/usr/bin/env python3
"""Capture comment-1 source/asset readiness without changing research files.

Only --out is written. It must be a JSON file under /tmp or this readiness
directory. No fitting, rendering, refresh, downloads, or Git writes are performed.
Use --compare to check protected numerical files against a prior snapshot.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[2]


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def table_cells(path: Path) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "&" not in line or not line.rstrip().endswith(r"\\"):
            continue
        cells = []
        for cell in line.split("&")[1:]:
            cells.extend(re.findall(r"(?<![A-Za-z])[-−]?\d+(?:\.\d+)?", cell))
        if cells:
            rows.append(cells)
    return rows


def capture(workflow: Path, article: Path, response: Path, public: Path) -> dict:
    files: dict[str, dict] = {}

    def add(path: Path, role: str, protected: bool = False) -> None:
        path = path.absolute()
        if str(path) in files:
            files[str(path)]["protected"] |= protected
            return
        identity = ("article:" + str(path.relative_to(article)) if path.is_relative_to(article)
                    else "workflow:" + str(path.relative_to(workflow)) if path.is_relative_to(workflow)
                    else "external:" + str(path))
        item = {"path": str(path), "identity": identity, "role": role, "protected": protected,
                "required": role != "reference_pdf", "exists": path.is_file()}
        if path.is_file():
            before = path.stat()
            item.update(bytes=before.st_size, sha256=digest(path))
            after = path.stat()
            item["stable_during_read"] = (
                before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns
            )
        files[str(path)] = item

    source_paths = [
        "wileyNJD-APA.tex", "main.tex", "wileyNJD-APA.bib", "WileyNJD-v2.cls",
        "WileyNJD-APA.bst", "MANUSCRIPT_ASSET_MANIFEST.json", "config/runtime_bindings.json",
        "scripts/article_repo_layout.py", "scripts/article_runtime_bindings.py",
        "scripts/exal_m_t1_authoritative.py", "scripts/refresh_cutoff_synthesis_families.py",
        "scripts/refresh_current_model_output_support_figures.py",
        "scripts/refresh_all_generated_assets.py", "scripts/sync_legacy_uppercase_figures.py",
        "scripts/validate_manuscript_figure_paths.py", "scripts/build_generated_table_includes.py",
        "tests/test_article_a1_and_table_contracts.py",
    ]
    for rel in source_paths:
        add(article / rel, "article_source")
    add(article / "wileyNJD-APA.pdf", "reference_pdf")
    for rel in [
        "R/unified/post_publication_figures.R", "config/post_publication_figures.yaml",
        "scripts/render_publication_post_figures.R",
        "scripts/render_focus_publication_posterior_plot.R", "scripts/forecats_plot_bundle.R",
        "scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py",
        "config/exal_m_t1_setup_support_by_cutoff_v2_20260516.json",
        "scripts/reviewer1_overview_contract.py", "scripts/reviewer1_uncertainty_contract.py",
        "scripts/runtime_feasibility_contract.py", "scripts/validate_publication_freeze.py",
        "tests/python/test_article_legacy_uppercase_figures_sync.py",
        "R/unified/families/exdqlm_multivar_structure.R",
    ]:
        add(workflow / rel, "workflow_source")

    authority = article / "artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv"
    add(authority, "frozen_authority", True)
    # Archive CSV contents are not included in this report: only identity hashes.
    metadata_names = {"manifest.csv", "figure_manifest.csv", "publication_figure_manifest.csv",
                      "artifact_inventory.csv"}
    for path in sorted((article / "artifacts").rglob("*.csv")):
        add(path, "frozen_csv", path.name not in metadata_names)
    cells = {}
    for path in sorted((article / "tables/generated_tex").glob("*.tex")):
        add(path, "generated_table_source")
        if path.stem.endswith(("_rows", "_body")):
            cells["article:" + str(path.relative_to(article))] = table_cells(path)

    selected = []
    with authority.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["manuscript_label"] not in {"exAL-M-T1", "exAL-U-T1"}:
                continue
            run = Path(row["artifact_run_root"] or row["run_root"])
            out = run / "post/outputs" / run.name
            multivar = row["manuscript_label"] == "exAL-M-T1"
            model = "exdqlm_multivar_synth_keep" if multivar else "exdqlm_univar_synth"
            add(out / "figure_manifest.csv", "run_figure_metadata")
            for suffix in ["cutoff_window_quantiles.csv", "cutoff_window_sample_subset.csv"]:
                add(out / f"{model}_{suffix}", "selected_predictive_csv", True)
            for name in ["nws_post_adapter.csv", "glofas_post_adapter.csv", "retros_post_adapter.csv"]:
                add(run / "post/inputs" / name, "selected_plot_adapter", True)
            caches = sorted((run / "post/cache").glob("*synth*log1p*.rds"))
            for path in caches:
                add(path, "selected_predictive_cache", True)
            selected.append({
                "cutoff": row["cutoff"], "label": row["manuscript_label"],
                "run_id": row["run_id"], "artifact_run_root": str(run),
                "outputs_dir": str(out), "model_id": model, "cache_count": len(caches),
                "cache_bytes": sum(path.stat().st_size for path in caches),
            })

    validator_path = article / "scripts/validate_manuscript_figure_paths.py"
    spec = importlib.util.spec_from_file_location("comment1_figure_paths", validator_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    tex_path = article / "wileyNJD-APA.tex"
    tex = tex_path.read_text(encoding="utf-8")
    search = module.parse_graphicspath(tex)
    includes = []
    for ref in module.parse_includegraphics(tex):
        path = module.resolve_include(article, tex_path, search, ref)
        includes.append({"include": ref, "resolved": str(path) if path else None})
        if path:
            add(path, "resolved_figure")
    upper = article / "Figures"
    lower = article / "figures"
    upper_files = {str(p.relative_to(upper)) for p in upper.rglob("*") if p.is_file()}
    lower_files = {str(p.relative_to(lower)) for p in lower.rglob("*") if p.is_file()}

    repos = []
    for name, path in [
        ("workflow", workflow), ("article", article),
        ("previous_response", response), ("public_reproduction", public),
    ]:
        repos.append({"name": name, "path": str(path), "head": git(path, "rev-parse", "HEAD"),
                      "status": git(path, "status", "--short", "--branch")})
    disk = os.statvfs(workflow)
    report = {
        "schema": "comment1_readiness_v1",
        "audit_tool_sha256": digest(Path(__file__).resolve()),
        "snapshot_local": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "scope": "Presentation planning; current publication results are authoritative.",
        "workflow_root": str(workflow), "article_root": str(article), "repositories": repos,
        "free_disk_gib": round(disk.f_bavail * disk.f_frsize / 1024**3, 2),
        "selected_runs": selected, "figure_includes": includes,
        "figure_case": {
            "current_canonical": "Figures", "upper_file_count": len(upper_files),
            "lower_file_count": len(lower_files), "upper_only_count": len(upper_files - lower_files),
            "lower_only_count": len(lower_files - upper_files),
        },
        "table_numeric_cells": cells,
        "files": sorted(files.values(), key=lambda x: x["path"]),
        "limitations": [
            "Snapshot is not manuscript implementation or figure regeneration.",
            "Existing contract failures are recorded separately in baseline_checks.json.",
            "Process observations are recorded separately and must be refreshed before promotion.",
            "Rendered PDF still requires human reading and final-size figure inspection.",
        ],
    }
    report["counts"] = {
        "files": len(files), "protected": sum(x["protected"] for x in files.values()),
        "missing": sum(not x["exists"] for x in files.values()),
        "missing_required": sum(not x["exists"] and x["required"] for x in files.values()),
        "unstable": sum(x.get("stable_during_read") is False for x in files.values()),
        "hashed_bytes": sum(x.get("bytes", 0) for x in files.values()),
        "selected_runs": len(selected), "includes": len(includes),
        "unresolved_includes": sum(x["resolved"] is None for x in includes),
    }
    return report


def compare(current: dict, previous: dict) -> dict:
    now = {x["identity"]: x for x in current["files"]}
    protected_changes, presentation_changes = [], []
    for before in previous["files"]:
        after = now.get(before["identity"])
        if after is None or not after["exists"] or before.get("sha256") != after.get("sha256"):
            (protected_changes if before["protected"] else presentation_changes).append(before["path"])
    table_changes = [key for key, value in previous["table_numeric_cells"].items()
                     if current["table_numeric_cells"].get(key) != value]
    selection_changed = current["selected_runs"] != previous["selected_runs"]
    return {"protected_file_changes": protected_changes,
            "presentation_or_source_changes": presentation_changes,
            "table_numeric_cell_changes": table_changes, "selected_runs_changed": selection_changed,
            "protected_invariants_unchanged": not (protected_changes or table_changes or selection_changed)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--article-root", type=Path)
    parser.add_argument("--response-root", type=Path, default=DEFAULT_ROOT.parent / "Corrections---Project-1")
    parser.add_argument("--public-root", type=Path, default=DEFAULT_ROOT.parent / "san-lorenzo-exdqlm-reproducibility")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.suffix != ".json" or not any(out.is_relative_to(p) for p in [Path("/tmp"), HERE]):
        parser.error("--out must be a JSON path under /tmp or this readiness directory")
    if out.exists():
        parser.error("--out already exists; choose a new path to preserve the previous capture")
    root = args.workflow_root.resolve()
    article = (args.article_root or root / "Evironmetrics---REVISED-DOC-Corrected-2").resolve()
    report = capture(root, article, args.response_root.resolve(), args.public_root.resolve())
    if args.compare:
        report["comparison"] = compare(report, json.loads(args.compare.read_text(encoding="utf-8")))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "counts": report["counts"],
                      "comparison": report.get("comparison")}, indent=2))
    return 0 if (not report["counts"]["missing_required"] and not report["counts"]["unstable"]
                 and not report["counts"]["unresolved_includes"]
                 and report.get("comparison", {}).get("protected_invariants_unchanged", True)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
