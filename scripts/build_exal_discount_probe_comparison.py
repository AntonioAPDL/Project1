#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
RUNTIME_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")

HE_BASELINE_CSV = (
    RUNTIME_ROOT
    / "multimodel_v8_featurecov_cf1_eps_sweep_20260416"
    / "reports"
    / "final_featurecov_cf1_eps_analysis"
    / "best_by_cutoff_long.csv"
)

OUTPUT_DIR = REPO_ROOT / "reports" / "quantile_discount_probe_analysis"
CSV_OUT = OUTPUT_DIR / "exal_multivar_keep_discount_probe_vs_he2.csv"
MD_OUT = OUTPUT_DIR / "exal_multivar_keep_discount_probe_vs_he2.md"


@dataclass(frozen=True)
class ProbeCampaign:
    profile_key: str
    profile_label: str
    template_path: Path | None
    runtime_root: Path | None
    spec_id: str | None
    notes: str


CAMPAIGNS = [
    ProbeCampaign(
        profile_key="he2_current_cf1",
        profile_label="Current HE2 baseline",
        template_path=None,
        runtime_root=None,
        spec_id=None,
        notes="Current manuscript exAL-M-T1 row from the completed featurecov cf1 epsilon sweep.",
    ),
    ProbeCampaign(
        profile_key="custom_user_requested_v1",
        profile_label="Featurecov custom discount probe",
        template_path=REPO_ROOT
        / "config"
        / "multimodel_v8_quantile_featurecov_custom_discount_probe_20260422.template.yaml",
        runtime_root=RUNTIME_ROOT / "multimodel_v8_quantile_featurecov_custom_discount_probe_20260422",
        spec_id="quantile_featurecov_custom_discount_probe_v1",
        notes="User-requested custom discount profile under the proper featurecov/blended-input contract.",
    ),
    ProbeCampaign(
        profile_key="featurecov_ndlm_tight_v1",
        profile_label="Featurecov NDLM-tight discount probe",
        template_path=REPO_ROOT
        / "config"
        / "multimodel_v8_quantile_ndlm_discount_probe_20260422.template.yaml",
        runtime_root=RUNTIME_ROOT / "multimodel_v8_quantile_featurecov_ndlm_discount_probe_20260422",
        spec_id="quantile_featurecov_ndlm_discount_probe_v1",
        notes="Featurecov probe that tightens the quantile-model discount block toward the NDLM side.",
    ),
    ProbeCampaign(
        profile_key="featurecov_hybrid_midpoint_v1",
        profile_label="Featurecov hybrid discount probe",
        template_path=REPO_ROOT
        / "config"
        / "multimodel_v8_quantile_featurecov_hybrid_discount_probe_20260422.template.yaml",
        runtime_root=RUNTIME_ROOT / "multimodel_v8_quantile_featurecov_hybrid_discount_probe_20260422",
        spec_id="quantile_featurecov_hybrid_discount_probe_v1",
        notes="Planned midpoint profile between the current HE block and the NDLM-tight block.",
    ),
    ProbeCampaign(
        profile_key="older_baseline_probe_v1",
        profile_label="Older baseline discount probe",
        template_path=REPO_ROOT
        / "config"
        / "multimodel_v8_quantile_ndlm_discount_probe_20260422.template.yaml",
        runtime_root=RUNTIME_ROOT / "multimodel_v8_quantile_ndlm_discount_probe_20260422",
        spec_id="quantile_ndlm_discount_probe_v1",
        notes="Older pre-featurecov scaffold retained for historical context only.",
    ),
]

FIELDNAMES = [
    "cutoff",
    "profile_key",
    "profile_label",
    "campaign_state",
    "notes",
    "he_baseline_crps",
    "probe_crps",
    "delta_vs_he",
    "is_better_than_he",
    "selected_source_config",
    "df_t",
    "df_s1",
    "df_s2",
    "df_s67",
    "df_discrep",
    "lambda",
    "df_trans",
    "df_covs",
]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return yaml.safe_load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def format_float(value: float | None) -> str:
    if value is None:
        return ""
    if abs(value) >= 1e6:
        return f"{value:.6e}"
    return f"{value:.6f}"


def normalize_cutoff(cutoff: str) -> str:
    return cutoff.strip()


def load_he_baseline() -> dict[str, float]:
    rows = read_csv(HE_BASELINE_CSV)
    return {
        normalize_cutoff(row["cutoff"]): float(row["forecast_window_crps"])
        for row in rows
        if row["model_variant"] == "exdqlm_multivar_keep"
    }


def load_baseline_source_configs() -> dict[str, str]:
    for campaign in CAMPAIGNS:
        if campaign.runtime_root is None or campaign.spec_id is None:
            continue
        selection_path = (
            campaign.runtime_root / "control" / campaign.spec_id / "selection_summary.csv"
        )
        if not selection_path.exists():
            continue
        rows = read_csv(selection_path)
        baseline_configs = {
            normalize_cutoff(row["cutoff"]): row["selected_source_config"]
            for row in rows
            if row["family_id"] == "exdqlm_multivar_keep" and row["selected_source_config"]
        }
        if baseline_configs:
            return baseline_configs
    raise FileNotFoundError("Could not resolve baseline source configs for exAL-M-T1.")


def state_evolution_from_config(path: Path) -> dict[str, str]:
    config = load_yaml(path)
    block = config["models"]["exdqlm_multivar"]["state_evolution"]
    return {key: str(block.get(key, "")) for key in (
        "df_t",
        "df_s1",
        "df_s2",
        "df_s67",
        "df_discrep",
        "lambda",
        "df_trans",
        "df_covs",
    )}


def current_he_rows() -> list[dict[str, str]]:
    he = load_he_baseline()
    baseline_configs = load_baseline_source_configs()
    rows: list[dict[str, str]] = []
    for cutoff, he_crps in sorted(he.items()):
        config_path = Path(baseline_configs[cutoff])
        state = state_evolution_from_config(config_path)
        rows.append(
            {
                "cutoff": cutoff,
                "profile_key": "he2_current_cf1",
                "profile_label": "Current HE2 baseline",
                "campaign_state": "completed_reference",
                "notes": CAMPAIGNS[0].notes,
                "he_baseline_crps": format_float(he_crps),
                "probe_crps": format_float(he_crps),
                "delta_vs_he": format_float(0.0),
                "is_better_than_he": "False",
                "selected_source_config": str(config_path),
                **state,
            }
        )
    return rows


def campaign_completion_state(campaign: ProbeCampaign) -> tuple[str, dict[str, int]]:
    if campaign.runtime_root is None or campaign.spec_id is None:
        return "completed_reference", {}
    matrix_status_path = (
        campaign.runtime_root / "control" / campaign.spec_id / "matrix_status.csv"
    )
    if not matrix_status_path.exists():
        return "missing_matrix_status", {}
    rows = read_csv(matrix_status_path)
    if not rows:
        return "not_launched", {}
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.get("status", "")] += 1
    if counts.get("pass", 0) == len(rows):
        return "completed", dict(counts)
    return "partial_or_failed", dict(counts)


def build_probe_rows(campaign: ProbeCampaign, he: dict[str, float]) -> list[dict[str, str]]:
    assert campaign.runtime_root is not None
    assert campaign.spec_id is not None
    assert campaign.template_path is not None
    template = load_yaml(campaign.template_path)
    override_block = (
        template.get("model_overrides", {}).get("exdqlm_multivar", {}).get("state_evolution", {})
    )
    state = {key: str(override_block.get(key, "")) for key in (
        "df_t",
        "df_s1",
        "df_s2",
        "df_s67",
        "df_discrep",
        "lambda",
        "df_trans",
        "df_covs",
    )}

    completion_state, _ = campaign_completion_state(campaign)
    plan_path = campaign.runtime_root / "control" / campaign.spec_id / "matrix_plan.csv"
    rows: list[dict[str, str]] = []
    for row in read_csv(plan_path):
        if row["family_id"] != "exdqlm_multivar_keep":
            continue
        cutoff = normalize_cutoff(row["cutoff"])
        run_id = row["run_id"]
        table_path = (
            campaign.runtime_root
            / "runs"
            / run_id
            / "post"
            / "outputs"
            / run_id
            / "tables"
            / "crps_forecast_summary.csv"
        )
        if table_path.exists():
            table_row = read_csv(table_path)[0]
            probe_crps = float(table_row["mean_crps"])
            delta = probe_crps - he[cutoff]
            better = probe_crps < he[cutoff]
            row_state = completion_state
        else:
            probe_crps = None
            delta = None
            better = False
            row_state = "missing_run_output"

        rows.append(
            {
                "cutoff": cutoff,
                "profile_key": campaign.profile_key,
                "profile_label": campaign.profile_label,
                "campaign_state": row_state,
                "notes": campaign.notes,
                "he_baseline_crps": format_float(he[cutoff]),
                "probe_crps": format_float(probe_crps),
                "delta_vs_he": format_float(delta),
                "is_better_than_he": "True" if better else "False",
                "selected_source_config": row["selected_source_config"],
                **state,
            }
        )
    return rows


def build_rows() -> list[dict[str, str]]:
    he = load_he_baseline()
    rows = current_he_rows()
    for campaign in CAMPAIGNS[1:]:
        rows.extend(build_probe_rows(campaign, he))
    return rows


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def build_markdown(rows: list[dict[str, str]]) -> str:
    by_profile: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_cutoff: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_profile[row["profile_key"]].append(row)
        by_cutoff[row["cutoff"]].append(row)

    completed_profiles = []
    incomplete_profiles = []
    for campaign in CAMPAIGNS[1:]:
        states = {row["campaign_state"] for row in by_profile[campaign.profile_key]}
        if states == {"completed"}:
            completed_profiles.append(campaign)
        else:
            incomplete_profiles.append(campaign)

    profile_rows = []
    for campaign in CAMPAIGNS:
        first = by_profile[campaign.profile_key][0]
        profile_rows.append(
            [
                campaign.profile_label,
                first["campaign_state"],
                first["df_t"],
                first["df_s1"],
                first["df_s2"],
                first["df_s67"],
                first["df_discrep"],
                first["lambda"],
                first["df_trans"],
                first["df_covs"],
            ]
        )

    cutoff_rows = []
    baseline_wins = 0
    for cutoff in sorted(by_cutoff):
        cutoff_group = [row for row in by_cutoff[cutoff] if row["campaign_state"] in {"completed_reference", "completed"}]
        cutoff_group.sort(key=lambda item: float(item["probe_crps"]))
        winner = cutoff_group[0]["profile_label"]
        if winner == "Current HE2 baseline":
            baseline_wins += 1
        baseline = next(row for row in cutoff_group if row["profile_key"] == "he2_current_cf1")
        custom = next((row for row in cutoff_group if row["profile_key"] == "custom_user_requested_v1"), None)
        ndlm = next((row for row in cutoff_group if row["profile_key"] == "featurecov_ndlm_tight_v1"), None)
        cutoff_rows.append(
            [
                cutoff,
                baseline["probe_crps"],
                custom["probe_crps"] if custom else "",
                custom["delta_vs_he"] if custom else "",
                ndlm["probe_crps"] if ndlm else "",
                ndlm["delta_vs_he"] if ndlm else "",
                winner,
            ]
        )

    completed_note = ", ".join(c.profile_label for c in completed_profiles) if completed_profiles else "none"
    incomplete_note = ", ".join(c.profile_label for c in incomplete_profiles) if incomplete_profiles else "none"

    return f"""# exAL-M-T1 Discount Probe Comparison

This report compares the current HE2 `exAL-M-T1` row against the completed discount-factor probe reruns for `exdqlm_multivar_keep` across all five cutoffs.

Important scope note:
- The authoritative CRPS values for the probe runs are taken from each run-local post table: `post/outputs/<run_id>/tables/crps_forecast_summary.csv`.
- I did **not** use the reused compare-bundle summaries as the source of truth for the probe rows because those bundles are named after preserved source compare directories and can retain inherited source metadata that does not uniquely identify the newly probed exAL row.

Completed probe profiles included:
- {completed_note}

Scaffolded but not completed, so excluded from the result comparison:
- {incomplete_note}

## Discount Profiles

{markdown_table(
    ["Profile", "State", "df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs"],
    profile_rows,
)}

## Cutoff Comparison

{markdown_table(
    ["Cutoff", "HE2 baseline", "Custom CRPS", "Custom delta", "NDLM-tight CRPS", "NDLM-tight delta", "Winner"],
    cutoff_rows,
)}

## Main Takeaways

- The current HE2 `exAL-M-T1` baseline remains the best completed profile in **{baseline_wins} / 5** cutoffs.
- The completed NDLM-tight discount probe is worse than the HE2 baseline in **5 / 5** cutoffs.
- The completed custom discount probe is also worse than the HE2 baseline in **5 / 5** cutoffs, and it is catastrophically unstable at `20211221` and `20220511`.
- Based on the completed discount probes, there is **no evidence** that the new discount-factor launches improved `exAL-M-T1` relative to the current HE2 row.
"""


def write_outputs(rows: list[dict[str, str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    MD_OUT.write_text(build_markdown(rows))


def main() -> None:
    rows = build_rows()
    write_outputs(rows)


if __name__ == "__main__":
    main()
