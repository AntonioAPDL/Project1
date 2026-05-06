#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_CSV = REPO_ROOT / "reports" / "he2_publication_manifest" / "he2_bayesian_publication_manifest.csv"
OUT_DIR = REPO_ROOT / "reports" / "publication_replay"
OUT_CSV = OUT_DIR / "publication_replay_matrix.csv"
OUT_MD = OUT_DIR / "publication_replay_matrix.md"

REPRESENTATIVE_ROWS = {
    ("20210123", "N-M-T1"),
    ("20210123", "exAL-U-T1"),
    ("20210123", "exAL-M-T1"),
    ("20221225", "exAL-M-T1"),
}


def load_rows() -> list[dict[str, str]]:
    with MANIFEST_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_json_field(value: str) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(value)


def campaign_root_from_run_root(run_root: Path) -> Path:
    parts = run_root.parts
    runs_idx = parts.index("runs")
    return Path(*parts[:runs_idx])


def extract_eps_token(run_id: str) -> str | None:
    match = re.search(r"_v8_(eps[^_]+)_", run_id)
    return match.group(1) if match else None


def extract_set_token(run_id: str) -> str | None:
    match = re.search(r"_v1_(set\d+)_", run_id)
    return match.group(1) if match else None


def lineage_base(campaign_lineage: str) -> str:
    return campaign_lineage.split(":", 1)[0]


def derive_compare_bundle_dir(row: dict[str, str]) -> Path:
    run_root = Path(row["run_root"])
    root = campaign_root_from_run_root(run_root)
    cutoff = row["cutoff"]
    lineage = row["campaign_lineage"]
    base = lineage_base(lineage)

    if base == "ndlm_featurecov_rerun_postfix_20260421":
        return root / "reports" / f"multimodel_{cutoff}_v8_ndlm_featurecov_v1_postfix_compare"
    if base == "univar_featurecov_he2_rerun_20260422":
        return root / "reports" / f"multimodel_{cutoff}_v8_univar_featurecov_he2_v1_compare"
    if base == "featurecov_cf1_eps_sweep_20260416":
        eps = extract_eps_token(row["run_id"])
        if eps is None:
            raise ValueError(f"Could not derive epsilon token from run_id={row['run_id']}")
        return root / "reports" / f"multimodel_{cutoff}_v8_{eps}_compare"
    if base == "exalm_t1_discount_grid_exact_20260424":
        set_name = extract_set_token(row["run_id"])
        replaced = row.get("replaced_source_run_id", "")
        eps = extract_eps_token(replaced)
        if set_name is None or eps is None:
            raise ValueError(f"Could not derive set/epsilon from row={row['run_id']}")
        return root / "reports" / f"multimodel_{cutoff}_v8_{set_name}_{eps}_compare"
    raise ValueError(f"Unhandled campaign lineage: {lineage}")


def publication_role(row: dict[str, str]) -> str:
    cutoff = row["cutoff"]
    label = row["manuscript_label"]
    if cutoff == "20221225" and label == "exAL-M-T1":
        return "HE2 publication override; HE3 full-reference dependency"
    return "HE2 Bayesian publication row"


def replay_env_recommendation(row: dict[str, str]) -> str:
    if row["cutoff"] == "20221225" and row["manuscript_label"] == "exAL-M-T1":
        return "Use exact-input lineage plus authoritative R 4.4 replay for fit-sensitive checks"
    return "Use publication campaign artifacts first; recreate native campaign runtime before fresh reruns"


def build_matrix(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    matrix: list[dict[str, str]] = []
    for row in rows:
        state = parse_json_field(row["state_evolution_json"])
        prior = parse_json_field(row["prior_json"])
        forecast_cov = prior.get("forecast_cov", {}) if isinstance(prior, dict) else {}
        compare_dir = derive_compare_bundle_dir(row)
        run_root = Path(row["run_root"])
        artifact_run_root = Path(row.get("artifact_run_root") or row["run_root"])
        artifact_run_id = row.get("artifact_run_id") or row["run_id"]
        artifact_resolved_config_path = row.get("artifact_resolved_config_path") or row["resolved_config_path"]
        artifact_campaign_root = campaign_root_from_run_root(artifact_run_root)
        artifact_root = artifact_run_root / "post" / "outputs" / artifact_run_id
        score_source = Path(row["score_source"])

        record = {
            "cutoff": row["cutoff"],
            "cutoff_display": row["cutoff_display"],
            "manuscript_label": row["manuscript_label"],
            "family": row["family"],
            "publication_role": publication_role(row),
            "representative_lineage_row": str((row["cutoff"], row["manuscript_label"]) in REPRESENTATIVE_ROWS),
            "campaign_lineage": row["campaign_lineage"],
            "campaign_root": str(campaign_root_from_run_root(run_root)),
            "artifact_campaign_root": str(artifact_campaign_root),
            "replay_env_recommendation": replay_env_recommendation(row),
            "run_id": row["run_id"],
            "run_root": row["run_root"],
            "resolved_config_path": row["resolved_config_path"],
            "artifact_run_id": artifact_run_id,
            "artifact_run_root": str(artifact_run_root),
            "artifact_resolved_config_path": artifact_resolved_config_path,
            "reused_external_pass": row["reused_external_pass"],
            "run_manifest_path": str(run_root / "run_manifest.yaml"),
            "report_summary_path": str(run_root / "report" / "summary.json"),
            "inputs_shared_path": str(run_root / "inputs" / "shared"),
            "artifact_run_manifest_path": str(artifact_run_root / "run_manifest.yaml"),
            "artifact_report_summary_path": str(artifact_run_root / "report" / "summary.json"),
            "artifact_inputs_shared_path": str(artifact_run_root / "inputs" / "shared"),
            "compare_bundle_dir": str(compare_dir),
            "source_provenance_path": str(compare_dir / "source_provenance.csv"),
            "score_source": row["score_source"],
            "crps_forecast_per_time_path": str(artifact_root / "tables" / "crps_forecast_per_time.csv"),
            "posterior_table_exports_manifest_path": str(artifact_root / "tables" / "posterior_table_exports_manifest.csv"),
            "posterior_table_exports_readme_path": str(artifact_root / "tables" / "posterior_table_exports_README.md"),
            "publication_figure_manifest_path": str(artifact_root / "publication_figure_manifest.csv"),
            "run_manifest_exists": str((run_root / "run_manifest.yaml").exists()),
            "report_summary_exists": str((run_root / "report" / "summary.json").exists()),
            "inputs_shared_exists": str((run_root / "inputs" / "shared").exists()),
            "artifact_run_manifest_exists": str((artifact_run_root / "run_manifest.yaml").exists()),
            "artifact_report_summary_exists": str((artifact_run_root / "report" / "summary.json").exists()),
            "artifact_inputs_shared_exists": str((artifact_run_root / "inputs" / "shared").exists()),
            "compare_bundle_exists": str(compare_dir.exists()),
            "source_provenance_exists": str((compare_dir / "source_provenance.csv").exists()),
            "score_source_exists": str(score_source.exists()),
            "crps_forecast_per_time_exists": str((artifact_root / "tables" / "crps_forecast_per_time.csv").exists()),
            "posterior_table_exports_manifest_exists": str((artifact_root / "tables" / "posterior_table_exports_manifest.csv").exists()),
            "posterior_table_exports_readme_exists": str((artifact_root / "tables" / "posterior_table_exports_README.md").exists()),
            "publication_figure_manifest_exists": str((artifact_root / "publication_figure_manifest.csv").exists()),
            "crps_exact": row["crps_exact"],
            "crps_display4": row["crps_display4"],
            "score_scale": row["score_scale"],
            "horizon_days": row["horizon_days"],
            "n_valid": row["n_valid"],
            "implementation_mode": row["implementation_mode"],
            "likelihood_mode": row["likelihood_mode"],
            "forecast_transfer_mode": row["forecast_transfer_mode"],
            "fit_covariate_names": row["fit_covariate_names"],
            "deterministic_climate_enabled": row["deterministic_climate_enabled"],
            "covariate_features_enabled": row["covariate_features_enabled"],
            "lag_orders": row["lag_orders"],
            "include_squares": row["include_squares"],
            "include_interaction": row["include_interaction"],
            "df_t": state.get("df_t", ""),
            "df_s1": state.get("df_s1", ""),
            "df_s2": state.get("df_s2", ""),
            "df_s67": state.get("df_s67", ""),
            "df_discrep": state.get("df_discrep", ""),
            "lambda": state.get("lambda", ""),
            "df_trans": state.get("df_trans", ""),
            "df_covs": state.get("df_covs", ""),
            "prior_forecast_cov_c_factor": forecast_cov.get("c_factor", ""),
            "prior_forecast_cov_epsilon": forecast_cov.get("epsilon", ""),
            "prior_forecast_cov_dof_offset": forecast_cov.get("dof_offset", ""),
            "prior_forecast_cov_scale_mult": forecast_cov.get("scale_mult", ""),
            "prior_forecast_cov_jitter": forecast_cov.get("jitter", ""),
            "publication_note": row["publication_note"],
            "replaced_source_run_id": row["replaced_source_run_id"],
            "within_cutoff_shared_inputs_aligned": row["within_cutoff_shared_inputs_aligned"],
        }
        matrix.append(record)
    return matrix


def write_csv(rows: list[dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_md(rows: list[dict[str, str]]) -> None:
    lineage_counts: dict[str, int] = {}
    for row in rows:
        lineage_counts[row["campaign_lineage"]] = lineage_counts.get(row["campaign_lineage"], 0) + 1

    representative = [row for row in rows if row["representative_lineage_row"] == "True"]
    lines = [
        "# Publication Replay Matrix",
        "",
        "This matrix locks the current manuscript-facing HE2 Bayesian publication lineage",
        "to explicit run roots, compare bundles, score files, and output contracts.",
        "",
        f"- rows: `{len(rows)}`",
        f"- representative lineage rows: `{len(representative)}`",
        "",
        "## Source of truth",
        "",
        "- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`",
        "- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`",
        "",
        "## Campaign counts",
        "",
        "| Campaign lineage | Rows |",
        "|---|---:|",
    ]
    for lineage, count in sorted(lineage_counts.items()):
        lines.append(f"| `{lineage}` | {count} |")

    lines.extend(
        [
            "",
            "## Representative rows",
            "",
            "| Cutoff | Label | Campaign lineage | Replay environment recommendation |",
            "|---|---|---|---|",
        ]
    )
    for row in representative:
        lines.append(
            f"| {row['cutoff_display']} | `{row['manuscript_label']}` | "
            f"`{row['campaign_lineage']}` | {row['replay_env_recommendation']} |"
        )

    lines.extend(
        [
            "",
            "## Important note",
            "",
            "The `12/25/2022 / exAL-M-T1` row is treated as a publication override. It",
            "no longer points to the earlier `featurecov_cf1` run; it points to the",
            "exact-input discount-grid winner under `set09`.",
            "",
            f"Full matrix: `{OUT_CSV}`",
            "",
        ]
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = load_rows()
    matrix = build_matrix(rows)
    write_csv(matrix)
    write_md(matrix)
    print(OUT_CSV)
    print(OUT_MD)


if __name__ == "__main__":
    main()
