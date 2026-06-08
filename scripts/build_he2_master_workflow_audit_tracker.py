#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_publication_parity_gate import build_gate  # noqa: E402
from he2_exdqlm_keep_authoritative import load_authoritative_spec  # noqa: E402

OUT_ROOT = ROOT / "reports" / "he2_master_workflow_audit_20260517"
ARTICLE_ROOT = ROOT / "Evironmetrics---REVISED-DOC-2"
ARTICLE_LINEAGE_SUMMARY = ARTICLE_ROOT / "reports" / "article_figure_lineage_audit_20260516" / "summary.json"
ARTICLE_SUPPORT_REFRESH = ARTICLE_ROOT / "artifacts" / "historical_support_from_current_models" / "refresh_status.json"
ARTICLE_MANIFEST = ARTICLE_ROOT / "MANUSCRIPT_ASSET_MANIFEST.json"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def family_rows(gate_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in gate_rows:
        grouped[row["manuscript_label"]].append(row)

    out: list[dict[str, str]] = []
    for label in sorted(grouped):
        rows = grouped[label]
        first = rows[0]
        promoted = first["target_status"] == "authoritative_promoted"
        blocked = first["target_status"] == "blocked_canonical_input_promotion"
        out.append(
            {
                "label": label,
                "family": first["family"],
                "cutoff_rows": str(len(rows)),
                "submodels_represented": str(sum(int(row["target_submodels"]) for row in rows)),
                "current_status": (
                    "authoritative_current_bundle_promoted"
                    if promoted
                    else ("blocked_pending_targeted_diagnostics" if blocked else "pending_same_bundle_promotion")
                ),
                "authoritative_state": (
                    "production_authoritative"
                    if promoted
                    else ("blocked_transition_pending" if blocked else "transition_pending")
                ),
                "required_action": "none" if promoted else first["required_action"],
                "paper_table_gate": first["paper_table_gate"],
                "notes": (
                    "Canonical-bundle promoted family is wired into the publication manifest."
                    if promoted
                    else (
                        "Blocked by AL-M-T0 sigma/PSD diagnostics; requires a targeted diagnostic or new AL-specific "
                        "discount spec before relaunch."
                        if blocked
                        else "Needs rerun or promotion onto the same 20260510 canonical input bundle before final all-model paper claims."
                    )
                ),
            }
        )
    return out


def build_tracker() -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    gate_rows, gate_summary = build_gate()
    spec = load_authoritative_spec()
    families = family_rows(gate_rows)
    article_state = {
        "asset_manifest_exists": ARTICLE_MANIFEST.exists(),
        "lineage_summary": read_json(ARTICLE_LINEAGE_SUMMARY),
        "historical_support_refresh": read_json(ARTICLE_SUPPORT_REFRESH),
    }
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ultimate_goal": "Freeze the fully promoted canonical-bundle HE2 Bayesian benchmark and refresh the manuscript tables from that final 45-row manifest.",
        "authoritative_exal_keep_manifest": str(spec.manifest_path),
        "authoritative_exal_keep_runtime_root": str(spec.runtime_root),
        "canonical_contract": {
            "scale": "log1p_cms",
            "score_scale": spec.score_scale,
            "retrospective_start": spec.metadata.get("data_start", "1987-05-29"),
            "shared_bundle_root": spec.metadata.get("bundle_artifact_root", ""),
            "shared_bundle_run_id": spec.metadata.get("bundle_run_id", ""),
            "covariates": ["PPT", "SOIL", "PCA(alias=GDPC1)"],
            "covariate_features": {"lags": [1, 2, 3], "include_squares": True, "include_interaction": True},
            "active_quantiles": spec.metadata.get("active_quantiles", "05|20|35|50|65|80|95"),
        },
        "publication_parity_gate": gate_summary,
        "remaining_model_input_parity_required": gate_summary["pending_rows"] > 0,
        "remaining_8_model_input_parity_required": False,
        "families": families,
        "article_state": article_state,
    }
    return families, gate_rows, summary


def render_markdown(families: list[dict[str, str]], summary: dict[str, Any]) -> str:
    gate = summary["publication_parity_gate"]
    lines = [
        "# HE2 Master Workflow Audit And Tracker",
        "",
        f"Date: {summary['generated_at_utc']}",
        "",
        "## Current Decision",
        "",
        "All nine HE2 Bayesian benchmark families are now promoted onto canonical-bundle roots.",
        "The full 9-model HE2 benchmark table is ready for the current paper snapshot after the June 7 NDLM promotion.",
        "",
        "## Canonical Contract",
        "",
        f"- source manifest: `{summary['authoritative_exal_keep_manifest']}`",
        f"- runtime root: `{summary['authoritative_exal_keep_runtime_root']}`",
        f"- shared bundle root: `{summary['canonical_contract']['shared_bundle_root']}`",
        f"- shared bundle run id: `{summary['canonical_contract']['shared_bundle_run_id']}`",
        f"- retrospective start: `{summary['canonical_contract']['retrospective_start']}`",
        "- scale: `log1p_cms`, scored as `log_cms_plus1`",
        "- covariates: `PPT`, `SOIL`, `PCA(alias=GDPC1)` with lags `1,2,3`, squares, and interaction",
        "",
        "## Publication Gate",
        "",
        f"- promoted rows: `{gate['promoted_rows']}`",
        f"- pending rows: `{gate['pending_rows']}`",
        f"- pending families: `{gate['remaining_model_families_pending']}`",
        f"- pending submodels: `{gate['remaining_submodels_pending']}`",
        f"- within-cutoff input-alignment checks passing now: `{gate['within_cutoff_alignment_passes']} / {gate['within_cutoff_alignment_checks']}`",
        f"- final 9-model benchmark ready: `{gate['final_9_model_benchmark_ready']}`",
        "",
        "## Family State",
        "",
        "| Label | Family | Rows | State | Required Action |",
        "|---|---|---:|---|---|",
    ]
    for row in families:
        lines.append(
            f"| `{row['label']}` | `{row['family']}` | {row['cutoff_rows']} | `{row['current_status']}` | `{row['required_action']}` |"
        )
    lines.extend(
        [
            "",
            "## Next Work",
            "",
            "1. Keep the workflow manifest and parity gate as the source of truth for the manuscript CRPS table.",
            "2. Refresh the article-side HE2 publication freeze from the workflow manifest.",
            "3. Regenerate the article TeX table includes and asset-review reports.",
            "4. Treat any future model-spec exploration as a new comparison grid, not as a modification of this frozen publication snapshot.",
            "",
            "## Outputs",
            "",
            f"- family tracker: `{OUT_ROOT / 'family_tracker.csv'}`",
            f"- cell tracker: `{OUT_ROOT / 'cutoff_tracker.csv'}`",
            f"- summary: `{OUT_ROOT / 'summary.json'}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    families, gate_rows, summary = build_tracker()
    write_csv(OUT_ROOT / "family_tracker.csv", families)
    write_csv(OUT_ROOT / "cutoff_tracker.csv", gate_rows)
    (OUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    report = OUT_ROOT / "HE2_MASTER_WORKFLOW_AUDIT_AND_TRACKER_20260517.md"
    report.write_text(render_markdown(families, summary), encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
