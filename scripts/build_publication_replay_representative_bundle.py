#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_CSV = REPO_ROOT / "reports" / "publication_replay" / "publication_replay_matrix.csv"
OUT_CONFIG_DIR = REPO_ROOT / "config" / "publication_replay_representatives_20260506"
OUT_REPORT_DIR = REPO_ROOT / "reports" / "publication_replay"
OUT_MD = OUT_REPORT_DIR / "publication_representative_bundle.md"
RUNTIME_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")
ARTIFACT_PARENT = RUNTIME_ROOT / "multimodel_v8_publication_replay_representatives_20260506"

REPRESENTATIVE_KEYS = [
    ("20210123", "N-M-T1"),
    ("20210123", "exAL-U-T1"),
    ("20210123", "exAL-M-T1"),
    ("20221225", "exAL-M-T1"),
]

LINEAGE_SPECS: dict[str, dict[str, str]] = {
    "ndlm_featurecov_rerun_postfix_20260421": {
        "base_template": "config/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421.template.yaml",
        "builder_kind": "ndlm_featurecov",
        "validator": "scripts/validate_ndlm_featurecov_rerun_prelaunch.py",
    },
    "univar_featurecov_he2_rerun_20260422": {
        "base_template": "config/multimodel_v8_univar_featurecov_he2_rerun_20260422.template.yaml",
        "builder_kind": "all9_feature",
        "validator": "scripts/validate_univar_featurecov_he2_prelaunch.py",
    },
    "featurecov_cf1_eps_sweep_20260416": {
        "base_template": "config/multimodel_v8_featurecov_cf1_eps_sweep.template.yaml",
        "builder_kind": "featurecov_cf1",
        "validator": "scripts/validate_featurecov_cf1_eps_prelaunch.py",
    },
    "exalm_t1_discount_grid_exact_20260424:set09_override": {
        "base_template": "config/multimodel_v8_exalm_t1_discount_grid_exact_20260424.template.yaml",
        "builder_kind": "exalm_t1_exact_grid",
        "validator": "scripts/validate_exalm_t1_discount_grid_prelaunch.py",
    },
}


def load_matrix_rows() -> list[dict[str, str]]:
    with MATRIX_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def slug_for_row(row: dict[str, str]) -> str:
    return f"{row['cutoff']}_{row['manuscript_label'].lower().replace('-', '_')}"


def campaign_base(row: dict[str, str]) -> str:
    return row["campaign_lineage"].split(":", 1)[0]


def selected_epsilon_from_run_id(run_id: str) -> str | None:
    match = re.search(r"_v8_(eps[^_]+)_", run_id)
    return match.group(1) if match else None


def selected_discount_profile(row: dict[str, str]) -> str | None:
    lineage = row["campaign_lineage"]
    if ":" not in lineage:
        return None
    suffix = lineage.split(":", 1)[1]
    match = re.match(r"(set\d+)", suffix)
    return match.group(1) if match else None


def disable_other_cutoffs(cfg: dict[str, Any], selected_cutoff: str) -> None:
    cutoffs_cfg = cfg.get("cutoffs")
    if not isinstance(cutoffs_cfg, dict):
        return
    for cutoff, cutoff_cfg in cutoffs_cfg.items():
        if isinstance(cutoff_cfg, dict):
            cutoff_cfg["enabled"] = str(cutoff) == selected_cutoff


def disable_other_families(cfg: dict[str, Any], selected_family: str) -> None:
    families_cfg = cfg.get("families")
    if not isinstance(families_cfg, dict):
        return
    for family_id, family_cfg in families_cfg.items():
        if isinstance(family_cfg, dict):
            family_cfg["enabled"] = str(family_id) == selected_family


def disable_other_specs(cfg: dict[str, Any], selected_spec: str | None) -> None:
    if not selected_spec:
        return
    specs_cfg = cfg.get("specs")
    if not isinstance(specs_cfg, dict):
        return
    for spec_id, spec_cfg in specs_cfg.items():
        if isinstance(spec_cfg, dict):
            spec_cfg["enabled"] = str(spec_id) == selected_spec


def disable_other_epsilons(cfg: dict[str, Any], selected_epsilon: str | None) -> None:
    if not selected_epsilon:
        return
    eps_cfg = cfg.get("epsilons")
    if not isinstance(eps_cfg, dict):
        return
    for epsilon_label, epsilon_cfg in eps_cfg.items():
        if isinstance(epsilon_cfg, dict):
            epsilon_cfg["enabled"] = str(epsilon_label) == selected_epsilon


def filter_discount_profiles(cfg: dict[str, Any], selected_profile: str | None) -> None:
    if not selected_profile:
        return
    profiles = cfg.get("discount_profiles")
    if not isinstance(profiles, list):
        return
    cfg["discount_profiles"] = [
        profile
        for profile in profiles
        if isinstance(profile, dict) and str(profile.get("name", "")).strip() == selected_profile
    ]


def tighten_queue(cfg: dict[str, Any]) -> None:
    queue_cfg = cfg.setdefault("queue", {})
    if not isinstance(queue_cfg, dict):
        return
    queue_cfg["ordinary_max_concurrent"] = 1
    queue_cfg["pause_free_gb"] = 180
    queue_cfg["launch_free_gb"] = 220
    queue_cfg["heavy_free_gb"] = 240
    queue_cfg["poll_seconds"] = 15
    if "heavy_cutoff_max_concurrent" in queue_cfg:
        queue_cfg["heavy_cutoff_max_concurrent"] = 1
    if "heavy_cutoff_blocks_ordinary" in queue_cfg:
        queue_cfg["heavy_cutoff_blocks_ordinary"] = False


def row_note(row: dict[str, str]) -> str:
    if row["campaign_lineage"] == "exalm_t1_discount_grid_exact_20260424:set09_override":
        return "Publication override row; exact-input set09 representative."
    if row["campaign_lineage"] == "featurecov_cf1_eps_sweep_20260416":
        eps = selected_epsilon_from_run_id(row["run_id"]) or "unknown"
        return f"Representative cf1-sweep row; selected epsilon `{eps}`."
    return "Representative publication row."


def source_r_version(run_root: str) -> str:
    session_info = Path(run_root) / "env" / "R_sessionInfo.txt"
    if not session_info.exists():
        return ""
    for line in session_info.read_text(encoding="utf-8").splitlines():
        if line.startswith("R version "):
            return line.removeprefix("R version ").strip()
    return ""


def source_runtime_profile(run_root: str) -> str:
    version = source_r_version(run_root)
    if version.startswith("4.4.0"):
        return "authoritative_r440"
    return "system_r"


def build_template(row: dict[str, str]) -> dict[str, Any]:
    lineage = row["campaign_lineage"]
    spec = LINEAGE_SPECS[lineage]
    base_template_path = REPO_ROOT / spec["base_template"]
    cfg = deepcopy(load_yaml(base_template_path))

    slug = slug_for_row(row)
    artifact_root = ARTIFACT_PARENT / slug
    matrix_suffix = f"{slug}_v1"
    config_output_dir = REPO_ROOT / "config" / "unified_runs_publication_replay_representatives_20260506" / slug

    campaign_cfg = cfg.setdefault("campaign", {})
    campaign_cfg["campaign_id"] = f"multimodel_v8_publication_replay_{slug}_20260506"
    if lineage == "ndlm_featurecov_rerun_postfix_20260421":
        campaign_cfg["spec_id"] = "ndlm_featurecov_v1_postfix"
    elif lineage == "univar_featurecov_he2_rerun_20260422":
        campaign_cfg["spec_id"] = "univar_featurecov_he2_v1"
    elif lineage == "featurecov_cf1_eps_sweep_20260416":
        campaign_cfg["sweep_id"] = "featurecov_cf1_eps_v1"
    elif lineage == "exalm_t1_discount_grid_exact_20260424:set09_override":
        campaign_cfg["spec_id"] = "exalm_t1_discount_grid_exact_v1"
    campaign_cfg["artifact_root"] = str(artifact_root)
    campaign_cfg["matrix_dir"] = str(artifact_root / "control" / matrix_suffix)
    campaign_cfg["config_output_dir"] = str(config_output_dir)
    campaign_cfg["launch_queue"] = False

    disable_other_cutoffs(cfg, row["cutoff"])
    disable_other_families(cfg, row["family"])
    disable_other_specs(cfg, str(campaign_cfg.get("spec_id", "")))
    disable_other_epsilons(cfg, selected_epsilon_from_run_id(row["run_id"]))
    filter_discount_profiles(cfg, selected_discount_profile(row))
    tighten_queue(cfg)

    cfg["debug_publication_replay"] = {
        "cutoff": row["cutoff"],
        "cutoff_display": row["cutoff_display"],
        "manuscript_label": row["manuscript_label"],
        "campaign_lineage": row["campaign_lineage"],
        "publication_run_id": row["run_id"],
        "publication_run_root": row["run_root"],
        "publication_score_source": row["score_source"],
        "expected_crps": float(row["crps_exact"]),
        "publication_note": row["publication_note"],
        "row_note": row_note(row),
        "source_r_version": source_r_version(row["run_root"]),
        "source_runtime_profile": source_runtime_profile(row["run_root"]),
    }
    return cfg


def write_bundle(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    manifest_rows: list[dict[str, str]] = []
    OUT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for row in rows:
        lineage = row["campaign_lineage"]
        spec = LINEAGE_SPECS[lineage]
        slug = slug_for_row(row)
        cfg = build_template(row)
        template_path = OUT_CONFIG_DIR / f"{slug}.template.yaml"
        write_yaml(template_path, cfg)

        builder_kind = spec["builder_kind"]
        builder_map = {
            "ndlm_featurecov": "scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py",
            "all9_feature": "scripts/build_multimodel_v8_all9_feature_matrix_configs.py",
            "featurecov_cf1": "scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py",
            "exalm_t1_exact_grid": "scripts/build_multimodel_v8_exalm_t1_discount_grid_configs.py",
        }
        manifest_rows.append(
            {
                "slug": slug,
                "cutoff": row["cutoff"],
                "cutoff_display": row["cutoff_display"],
                "manuscript_label": row["manuscript_label"],
                "campaign_lineage": lineage,
                "family": row["family"],
                "builder_kind": builder_kind,
                "builder_script": builder_map[builder_kind],
                "validator_script": spec["validator"],
                "template_path": str(template_path),
                "artifact_root": str(cfg["campaign"]["artifact_root"]),
                "matrix_dir": str(cfg["campaign"]["matrix_dir"]),
                "config_output_dir": str(cfg["campaign"]["config_output_dir"]),
                "expected_crps": row["crps_exact"],
                "publication_run_id": row["run_id"],
                "selected_epsilon": selected_epsilon_from_run_id(row["run_id"]) or "",
                "selected_discount_profile": selected_discount_profile(row) or "",
                "source_r_version": source_r_version(row["run_root"]),
                "source_runtime_profile": source_runtime_profile(row["run_root"]),
                "note": row_note(row),
            }
        )
    return manifest_rows


def write_markdown(rows: list[dict[str, str]]) -> None:
    lines = [
        "# Publication Representative Replay Bundle",
        "",
        "This bundle stages one representative replay row for each publication lineage",
        "tracked in the current Bayesian HE2 table.",
        "",
        "| Slug | Cutoff | Label | Lineage | Family | Source R | Runtime profile | Expected CRPS | Notes |",
        "|---|---|---|---|---|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['slug']}` | {row['cutoff_display']} | `{row['manuscript_label']}` | "
            f"`{row['campaign_lineage']}` | `{row['family']}` | `{row['source_r_version'] or 'unknown'}` | "
            f"`{row['source_runtime_profile']}` | {float(row['expected_crps']):.4f} | {row['note']} |"
        )
    lines.extend(
        [
            "",
            "## Generated templates",
            "",
            f"- directory: `{OUT_CONFIG_DIR}`",
            "",
            "## Launch expectation",
            "",
            "- each row uses its own isolated artifact root under",
            f"  `{ARTIFACT_PARENT}`",
            "- runtime selection is source-run aware and reuses the recorded",
            "  publication `R 4.4.0` stack when required",
            "- cutoff and family scope are restricted to one publication row per lineage",
            "- cf1 replay is restricted to the selected publication epsilon",
            "- exact-grid replay is restricted to the publication `set09` profile",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = load_matrix_rows()
    selected = []
    for cutoff, label in REPRESENTATIVE_KEYS:
        match = next((row for row in rows if row["cutoff"] == cutoff and row["manuscript_label"] == label), None)
        if match is None:
            raise SystemExit(f"Missing representative row for cutoff={cutoff} label={label}")
        selected.append(match)

    manifest_rows = write_bundle(selected)
    write_markdown(manifest_rows)
    print(OUT_CONFIG_DIR)
    print(OUT_MD)


if __name__ == "__main__":
    main()
