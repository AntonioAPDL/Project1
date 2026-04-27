#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
RUNTIME_ROOT = ROOT.parent / "project1_ucsc_phd_runtime"
OUT_DIR = ROOT / "reports" / "he2_publication_manifest"

CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]
FAMILY_ORDER = [
    "ndlm_univar_keep",
    "ndlm_main_drop",
    "ndlm_main_keep",
    "dqlm_univar_al",
    "dqlm_multivar_al_drop",
    "dqlm_multivar_al_keep",
    "exdqlm_univar",
    "exdqlm_multivar_drop",
    "exdqlm_multivar_keep",
]
FAMILY_TO_LABEL = {
    "ndlm_univar_keep": "N-U-T1",
    "ndlm_main_drop": "N-M-T0",
    "ndlm_main_keep": "N-M-T1",
    "dqlm_univar_al": "AL-U-T1",
    "dqlm_multivar_al_drop": "AL-M-T0",
    "dqlm_multivar_al_keep": "AL-M-T1",
    "exdqlm_univar": "exAL-U-T1",
    "exdqlm_multivar_drop": "exAL-M-T0",
    "exdqlm_multivar_keep": "exAL-M-T1",
}
FAMILY_TO_MODEL_KEY = {
    "ndlm_univar_keep": "ndlm_univar",
    "ndlm_main_drop": "ndlm_main",
    "ndlm_main_keep": "ndlm_main",
    "dqlm_univar_al": "exdqlm_univar",
    "dqlm_multivar_al_drop": "exdqlm_multivar",
    "dqlm_multivar_al_keep": "exdqlm_multivar",
    "exdqlm_univar": "exdqlm_univar",
    "exdqlm_multivar_drop": "exdqlm_multivar",
    "exdqlm_multivar_keep": "exdqlm_multivar",
}
MODEL_ID_TO_FAMILY = {
    "exdqlm_multivar_synth_keep": "exdqlm_multivar_keep",
    "dqlm_multivar_al_synth_keep": "dqlm_multivar_al_keep",
    "exdqlm_multivar_synth_drop": "exdqlm_multivar_drop",
    "dqlm_multivar_al_synth_drop": "dqlm_multivar_al_drop",
    "exdqlm_univar_synth": "exdqlm_univar",
    "dqlm_univar_al_synth": "dqlm_univar_al",
    "ndlm_main_synth_keep": "ndlm_main_keep",
    "ndlm_main_synth_drop": "ndlm_main_drop",
    "ndlm_univar_synth_keep": "ndlm_univar_keep",
}
FAMILY_TO_MODEL_ID = {family: model_id for model_id, family in MODEL_ID_TO_FAMILY.items()}
ARTIFACT_SPECS = [
    ("parameters", "inputs/shared/parameters/parameters.txt"),
    ("retros", "inputs/shared/retros/retros.csv"),
    ("nws_forecast", "inputs/shared/forecasts/nws_forecast.csv"),
    ("glofas_forecast", "inputs/shared/forecasts/glofas_forecast.csv"),
    ("usgs_daily", "inputs/shared/usgs/usgs_daily.csv"),
    ("cov_01_PPT", "inputs/shared/covariates/cov_01_PPT.csv"),
    ("cov_02_SOIL", "inputs/shared/covariates/cov_02_SOIL.csv"),
    ("cov_03_PCA", "inputs/shared/covariates/cov_03_PCA.csv"),
    ("covariate_features", "inputs/shared/covariates/covariate_features.csv"),
    ("deterministic_precip_future", "inputs/shared/deterministic_climate/deterministic_precip_future.csv"),
    ("deterministic_soil_future", "inputs/shared/deterministic_climate/deterministic_soil_future.csv"),
]
REQUIRED_ALIGNMENT_ARTIFACTS = [
    name for name, _rel in ARTIFACT_SPECS if name != "usgs_daily"
]
CSV_FIELDS = [
    "cutoff",
    "cutoff_display",
    "manuscript_label",
    "family",
    "run_id",
    "run_root",
    "artifact_run_id",
    "artifact_run_root",
    "resolved_config_path",
    "artifact_resolved_config_path",
    "reused_external_pass",
    "campaign_lineage",
    "publication_note",
    "replaced_source_run_id",
    "crps_exact",
    "crps_display4",
    "score_source",
    "score_scale",
    "horizon_days",
    "n_valid",
    "implementation_mode",
    "likelihood_mode",
    "forecast_transfer_mode",
    "fit_covariate_names",
    "fit_covariate_paths_json",
    "deterministic_climate_enabled",
    "deterministic_climate_json",
    "covariate_features_enabled",
    "lag_orders",
    "include_squares",
    "include_interaction",
    "covariate_features_json",
    "state_evolution_json",
    "prior_json",
    "seasonality_json",
    "within_cutoff_shared_inputs_aligned",
]
INPUT_FIELDS = [
    "cutoff",
    "manuscript_label",
    "family",
    "run_id",
    "artifact",
    "path",
    "exists",
    "sha256_16",
]
ALIGNMENT_FIELDS = [
    "cutoff",
    "artifact",
    "all_equal",
    "distinct_hashes",
    "missing_count",
    "hash_groups_json",
    "missing_labels",
]
OVERRIDE_EXAL_20221225 = {
    "run_id": "multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep",
    "campaign_lineage": "exalm_t1_discount_grid_exact_20260424:set09_override",
    "publication_note": (
        "HE2 publication override: exact-input apples-to-apples exAL-M-T1 discount-grid winner "
        "replaces the earlier cf1 sweep source run for cutoff 20221225."
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def cutoff_display(cutoff: str) -> str:
    return datetime.strptime(cutoff, "%Y%m%d").strftime("%m/%d/%Y")


def display4(value: float) -> str:
    return f"{value:.4f}"


def json_compact(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def as_existing_path(value: object) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.exists() and path.is_file():
        return path
    return None


def resolve_artifact(run_root: Path, rel: str, cfg: dict[str, Any]) -> Path | None:
    direct = run_root / rel
    if direct.exists() and direct.is_file():
        return direct

    fit = (cfg.get("inputs") or {}).get("fit") or {}
    if rel == "inputs/shared/parameters/parameters.txt":
        return as_existing_path(fit.get("parameters_path", ""))
    if rel == "inputs/shared/retros/retros.csv":
        return as_existing_path(fit.get("retros_path", ""))
    if rel == "inputs/shared/forecasts/nws_forecast.csv":
        return as_existing_path(fit.get("nws_forecast_path", ""))
    if rel == "inputs/shared/forecasts/glofas_forecast.csv":
        return as_existing_path(fit.get("glofas_forecast_path", ""))
    if rel == "inputs/shared/usgs/usgs_daily.csv":
        return as_existing_path(fit.get("usgs_cache_path", ""))
    if rel.startswith("inputs/shared/covariates/"):
        name_map = {
            "inputs/shared/covariates/cov_01_PPT.csv": "PPT",
            "inputs/shared/covariates/cov_02_SOIL.csv": "SOIL",
            "inputs/shared/covariates/cov_03_PCA.csv": "PCA",
        }
        wanted = name_map.get(rel)
        if wanted:
            for cov in fit.get("covariates") or []:
                if cov.get("name") == wanted:
                    return as_existing_path(cov.get("path", ""))
    return None


def artifact_context(pointer_run_root: Path) -> tuple[Path, Path, bool]:
    reuse_pointer = pointer_run_root / "reuse_pointer.yaml"
    if reuse_pointer.exists():
        pointer_cfg = read_yaml(reuse_pointer)
        artifact_root = Path(str(pointer_cfg["reuse_source_run_root"]))
        artifact_cfg = Path(str(pointer_cfg["reuse_source_config"]))
        return artifact_root, artifact_cfg, True
    return pointer_run_root, pointer_run_root / "resolved_config.yaml", False


def score_row_for_family(run_root: Path, family: str) -> dict[str, str]:
    table = run_root / "post" / "outputs" / run_root.name / "tables" / "crps_forecast_summary.csv"
    rows = read_csv(table)
    for row in rows:
        if row.get("model_variant") == family:
            return row
    raise ValueError(f"Missing model_variant={family} in {table}")


def compare_score_row(compare_dir: Path, family: str) -> dict[str, str]:
    table = compare_dir / "crps_forecast_summary_all_models.csv"
    rows = read_csv(table)
    model_id = FAMILY_TO_MODEL_ID[family]
    for row in rows:
        if row.get("model_id") == model_id:
            return row
    raise ValueError(f"Missing model_id={model_id} in {table}")


def resolve_multivar_rows() -> list[dict[str, str]]:
    best_path = (
        RUNTIME_ROOT
        / "multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/final_featurecov_cf1_eps_analysis/best_by_cutoff_long.csv"
    )
    rows = []
    for cutoff in CUTOFFS:
        best_rows = [
            row
            for row in read_csv(best_path)
            if row["cutoff"] == cutoff
            and row["model_variant"] in {
                "exdqlm_multivar_keep",
                "dqlm_multivar_al_keep",
                "exdqlm_multivar_drop",
                "dqlm_multivar_al_drop",
            }
        ]
        for best_row in best_rows:
            family = best_row["model_variant"]
            compare_dir = (
                RUNTIME_ROOT
                / f"multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/multimodel_{cutoff}_v8_{best_row['best_epsilon_label']}_compare"
            )
            prov_rows = read_csv(compare_dir / "source_provenance.csv")
            match = next(row for row in prov_rows if row.get("family_id") == family)
            run_id = match["source_run"]
            run_root = RUNTIME_ROOT / "multimodel_v8_featurecov_cf1_eps_sweep_20260416/runs" / run_id
            rows.append(
                {
                    "cutoff": cutoff,
                    "family": family,
                    "run_id": run_id,
                    "run_root": str(run_root),
                    "compare_dir": str(compare_dir),
                    "campaign_lineage": "featurecov_cf1_eps_sweep_20260416",
                    "publication_note": "",
                    "replaced_source_run_id": "",
                }
            )
    return rows


def resolve_univar_rows() -> list[dict[str, str]]:
    rows = []
    base = RUNTIME_ROOT / "multimodel_v8_univar_featurecov_he2_rerun_20260422"
    for cutoff in CUTOFFS:
        prov_rows = read_csv(base / f"reports/multimodel_{cutoff}_v8_univar_featurecov_he2_v1_compare/source_provenance.csv")
        for row in prov_rows:
            family = MODEL_ID_TO_FAMILY.get(row["model_id"], "")
            if family not in {"exdqlm_univar", "dqlm_univar_al"}:
                continue
            run_id = row["source_run"]
            rows.append(
                {
                    "cutoff": cutoff,
                    "family": family,
                    "run_id": run_id,
                    "run_root": str(base / "runs" / run_id),
                    "compare_dir": str(base / f"reports/multimodel_{cutoff}_v8_univar_featurecov_he2_v1_compare"),
                    "campaign_lineage": "univar_featurecov_he2_rerun_20260422",
                    "publication_note": "",
                    "replaced_source_run_id": "",
                }
            )
    return rows


def resolve_ndlm_rows() -> list[dict[str, str]]:
    rows = []
    base = RUNTIME_ROOT / "multimodel_v8_ndlm_featurecov_rerun_postfix_20260421"
    for cutoff in CUTOFFS:
        prov_rows = read_csv(base / f"reports/multimodel_{cutoff}_v8_ndlm_featurecov_v1_postfix_compare/source_provenance.csv")
        for row in prov_rows:
            family = MODEL_ID_TO_FAMILY.get(row["model_id"], "")
            if family not in {"ndlm_main_keep", "ndlm_main_drop", "ndlm_univar_keep"}:
                continue
            run_id = row["source_run"]
            rows.append(
                {
                    "cutoff": cutoff,
                    "family": family,
                    "run_id": run_id,
                    "run_root": str(base / "runs" / run_id),
                    "compare_dir": str(base / f"reports/multimodel_{cutoff}_v8_ndlm_featurecov_v1_postfix_compare"),
                    "campaign_lineage": "ndlm_featurecov_rerun_postfix_20260421",
                    "publication_note": "",
                    "replaced_source_run_id": "",
                }
            )
    return rows


def apply_override(rows: list[dict[str, str]]) -> None:
    for row in rows:
        if row["cutoff"] == "20221225" and row["family"] == "exdqlm_multivar_keep":
            row["replaced_source_run_id"] = row["run_id"]
            row["run_id"] = OVERRIDE_EXAL_20221225["run_id"]
            row["run_root"] = str(
                RUNTIME_ROOT
                / "multimodel_v8_exalm_t1_discount_grid_exact_20260424/runs"
                / OVERRIDE_EXAL_20221225["run_id"]
            )
            row["compare_dir"] = str(
                RUNTIME_ROOT
                / "multimodel_v8_exalm_t1_discount_grid_exact_20260424/control/exalm_t1_discount_grid_exact_v1"
            )
            row["campaign_lineage"] = OVERRIDE_EXAL_20221225["campaign_lineage"]
            row["publication_note"] = OVERRIDE_EXAL_20221225["publication_note"]
            return
    raise RuntimeError("Could not find exAL-M-T1 20221225 row to override")


def build_resolved_rows() -> list[dict[str, str]]:
    rows = resolve_multivar_rows() + resolve_univar_rows() + resolve_ndlm_rows()
    apply_override(rows)
    rows = sorted(rows, key=lambda row: (row["cutoff"], FAMILY_ORDER.index(row["family"])))
    if len(rows) != 45:
        raise RuntimeError(f"Expected 45 publication rows, found {len(rows)}")
    return rows


def build_outputs() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    manifest_rows: list[dict[str, str]] = []
    input_rows: list[dict[str, str]] = []

    resolved_rows = build_resolved_rows()
    for row in resolved_rows:
        run_root = Path(row["run_root"])
        cfg_path = run_root / "resolved_config.yaml"
        artifact_root, artifact_cfg_path, reused = artifact_context(run_root)
        cfg = read_yaml(artifact_cfg_path)
        fit = (cfg.get("inputs") or {}).get("fit") or {}
        det = (cfg.get("inputs") or {}).get("deterministic_climate") or {}
        covfeat = (cfg.get("inputs") or {}).get("covariate_features") or {}
        fit_covariates = fit.get("covariates") or []
        cov_names = [cov.get("name", "") for cov in fit_covariates if cov.get("name")]
        cov_paths = {cov.get("name", ""): cov.get("path", "") for cov in fit_covariates if cov.get("name")}
        model_cfg = (cfg.get("models") or {}).get(FAMILY_TO_MODEL_KEY[row["family"]]) or {}
        local_score_table = artifact_root / "post" / "outputs" / artifact_root.name / "tables" / "crps_forecast_summary.csv"
        if local_score_table.exists():
            score = score_row_for_family(artifact_root, row["family"])
            score_source = str(local_score_table)
        else:
            score = compare_score_row(Path(row["compare_dir"]), row["family"])
            score_source = str(Path(row["compare_dir"]) / "crps_forecast_summary_all_models.csv")

        for artifact, rel in ARTIFACT_SPECS:
            path = resolve_artifact(artifact_root, rel, cfg)
            input_rows.append(
                {
                    "cutoff": row["cutoff"],
                    "manuscript_label": FAMILY_TO_LABEL[row["family"]],
                    "family": row["family"],
                    "run_id": row["run_id"],
                    "artifact": artifact,
                    "path": str(path) if path else "",
                    "exists": "True" if path and path.exists() else "False",
                    "sha256_16": sha16(path) if path and path.exists() else "",
                }
            )

        manifest_rows.append(
            {
                "cutoff": row["cutoff"],
                "cutoff_display": cutoff_display(row["cutoff"]),
                "manuscript_label": FAMILY_TO_LABEL[row["family"]],
                "family": row["family"],
                "run_id": row["run_id"],
                "run_root": str(run_root),
                "artifact_run_id": artifact_root.name,
                "artifact_run_root": str(artifact_root),
                "resolved_config_path": str(cfg_path),
                "artifact_resolved_config_path": str(artifact_cfg_path),
                "reused_external_pass": str(reused),
                "campaign_lineage": row["campaign_lineage"],
                "publication_note": row["publication_note"],
                "replaced_source_run_id": row["replaced_source_run_id"],
                "crps_exact": str(float(score["mean_crps"])),
                "crps_display4": display4(float(score["mean_crps"])),
                "score_source": score_source,
                "score_scale": score["score_scale"],
                "horizon_days": score["horizon_days"],
                "n_valid": score["n_valid"],
                "implementation_mode": str(model_cfg.get("implementation_mode", "")),
                "likelihood_mode": str(model_cfg.get("likelihood_mode", "normal")),
                "forecast_transfer_mode": str(model_cfg.get("forecast_transfer_mode", "")),
                "fit_covariate_names": "|".join(cov_names),
                "fit_covariate_paths_json": json_compact(cov_paths),
                "deterministic_climate_enabled": str(bool(det.get("enabled", False))),
                "deterministic_climate_json": json_compact(det),
                "covariate_features_enabled": str(bool(covfeat.get("enabled", False))),
                "lag_orders": "|".join(str(x) for x in (covfeat.get("lag_orders") or [])),
                "include_squares": str(bool(covfeat.get("include_squares", False))),
                "include_interaction": str(bool(covfeat.get("include_interaction", False))),
                "covariate_features_json": json_compact(covfeat),
                "state_evolution_json": json_compact(model_cfg.get("state_evolution") or {}),
                "prior_json": json_compact(model_cfg.get("prior") or {}),
                "seasonality_json": json_compact(model_cfg.get("seasonality") or {}),
                "within_cutoff_shared_inputs_aligned": "",
            }
        )

    alignment_rows: list[dict[str, str]] = []
    for cutoff in CUTOFFS:
        cutoff_inputs = [row for row in input_rows if row["cutoff"] == cutoff]
        for artifact, _rel in ARTIFACT_SPECS:
            subset = [row for row in cutoff_inputs if row["artifact"] == artifact]
            groups: dict[str, list[str]] = defaultdict(list)
            for item in subset:
                if item["exists"] == "True":
                    groups[item["sha256_16"]].append(item["manuscript_label"])
            missing = [item["manuscript_label"] for item in subset if item["exists"] != "True"]
            all_equal = len(groups) == 1 and not missing
            alignment_rows.append(
                {
                    "cutoff": cutoff,
                    "artifact": artifact,
                    "all_equal": "True" if all_equal else "False",
                    "distinct_hashes": str(len(groups)),
                    "missing_count": str(len(missing)),
                    "hash_groups_json": json_compact({k: sorted(v) for k, v in groups.items()}),
                    "missing_labels": "|".join(sorted(missing)),
                }
            )

    aligned_cutoffs = {
        cutoff: all(
            row["all_equal"] == "True"
            for row in alignment_rows
            if row["cutoff"] == cutoff and row["artifact"] in REQUIRED_ALIGNMENT_ARTIFACTS
        )
        for cutoff in CUTOFFS
    }
    for row in manifest_rows:
        row["within_cutoff_shared_inputs_aligned"] = str(aligned_cutoffs[row["cutoff"]])

    return manifest_rows, input_rows, alignment_rows


def validate(manifest_rows: list[dict[str, str]], alignment_rows: list[dict[str, str]]) -> None:
    if len(manifest_rows) != 45:
        raise RuntimeError(f"Expected 45 manifest rows, found {len(manifest_rows)}")
    observed_labels = sorted({row["manuscript_label"] for row in manifest_rows})
    if observed_labels != sorted(FAMILY_TO_LABEL.values()):
        raise RuntimeError(f"Unexpected manuscript labels: {observed_labels}")
    for row in manifest_rows:
        if row["fit_covariate_names"] != "PPT|SOIL|PCA":
            raise RuntimeError(f"Unexpected covariate contract in {row['run_id']}: {row['fit_covariate_names']}")
        if row["deterministic_climate_enabled"] != "True":
            raise RuntimeError(f"Deterministic climate disabled in {row['run_id']}")
        if row["covariate_features_enabled"] != "True":
            raise RuntimeError(f"Covariate features disabled in {row['run_id']}")
        if row["lag_orders"] != "1|2|3":
            raise RuntimeError(f"Unexpected lag orders in {row['run_id']}: {row['lag_orders']}")
        if row["include_squares"] != "True" or row["include_interaction"] != "True":
            raise RuntimeError(f"Feature transform contract failed in {row['run_id']}")
        if row["within_cutoff_shared_inputs_aligned"] != "True":
            raise RuntimeError(f"Shared input alignment failed for cutoff {row['cutoff']}")
    for row in alignment_rows:
        if row["artifact"] not in REQUIRED_ALIGNMENT_ARTIFACTS:
            continue
        if row["all_equal"] != "True":
            raise RuntimeError(f"Artifact mismatch: cutoff={row['cutoff']} artifact={row['artifact']}")
    override = next(
        row for row in manifest_rows if row["cutoff"] == "20221225" and row["manuscript_label"] == "exAL-M-T1"
    )
    if override["run_id"] != OVERRIDE_EXAL_20221225["run_id"]:
        raise RuntimeError(f"Unexpected override run: {override['run_id']}")
    if override["crps_display4"] != "0.4375":
        raise RuntimeError(f"Unexpected override CRPS: {override['crps_display4']}")


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([head, sep, *body])


def write_markdown(manifest_rows: list[dict[str, str]], alignment_rows: list[dict[str, str]]) -> None:
    cutoff_rows = []
    for cutoff in CUTOFFS:
        aligned = sum(
            1
            for row in alignment_rows
            if row["cutoff"] == cutoff
            and row["artifact"] in REQUIRED_ALIGNMENT_ARTIFACTS
            and row["all_equal"] == "True"
        )
        cutoff_rows.append([cutoff_display(cutoff), f"{aligned} / {len(REQUIRED_ALIGNMENT_ARTIFACTS)}", "Aligned"])

    current_rows = []
    for row in manifest_rows:
        if row["cutoff"] == "20221225" and row["manuscript_label"] == "exAL-M-T1":
            note = "updated winner"
        else:
            note = ""
        current_rows.append(
            [
                row["cutoff_display"],
                row["manuscript_label"],
                row["crps_display4"],
                row["run_id"],
                row["campaign_lineage"],
                note,
            ]
        )

    unique_likelihoods = sorted({row["likelihood_mode"] for row in manifest_rows})
    md = f"""# HE2 Bayesian Publication Manifest

This report freezes the **current manuscript-facing HE2 Bayesian table** at the run level for all `9 x 5 = 45` cells.

Headline checks:
- published Bayesian HE2 cells documented: `{len(manifest_rows)}`
- cutoffs documented: `{len(CUTOFFS)}`
- required shared-input artifacts checked within each cutoff: `{len(REQUIRED_ALIGNMENT_ARTIFACTS)}`
- fit covariate contract observed: `PPT|SOIL|PCA`
- deterministic-climate enabled flags observed: `True`
- covariate-features enabled flags observed: `True`
- lag orders observed: `1|2|3`
- square terms observed: `True`
- interaction term observed: `True`
- likelihood modes observed: `{', '.join(unique_likelihoods)}`

Special publication update:
- `12/25/2022 / exAL-M-T1` now resolves to `{OVERRIDE_EXAL_20221225['run_id']}` with mean CRPS `0.4375`, replacing the earlier cf1-sweep source row for that single HE2 cell.

## Within-Cutoff Input Congruence

{markdown_table(["Cutoff", "Artifact Checks Passing", "Result"], cutoff_rows)}

Archival caveat:
- `usgs_daily.csv` was not preserved inside some older multivariate quantile run roots, so the strict within-cutoff congruence gate is evaluated on the **10 fit/forecast/blended-covariate artifacts** rather than on the auxiliary USGS cache file.

## Publication Rows

{markdown_table(["Cutoff", "Label", "CRPS", "Run ID", "Campaign", "Note"], current_rows)}

## Outputs

- manifest: `{OUT_DIR / 'he2_bayesian_publication_manifest.csv'}`
- inputs: `{OUT_DIR / 'he2_bayesian_publication_inputs.csv'}`
- alignment: `{OUT_DIR / 'he2_bayesian_publication_alignment.csv'}`
"""
    (OUT_DIR / "he2_bayesian_publication_manifest.md").write_text(md + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows, input_rows, alignment_rows = build_outputs()
    validate(manifest_rows, alignment_rows)
    write_csv(OUT_DIR / "he2_bayesian_publication_manifest.csv", manifest_rows, CSV_FIELDS)
    write_csv(OUT_DIR / "he2_bayesian_publication_inputs.csv", input_rows, INPUT_FIELDS)
    write_csv(OUT_DIR / "he2_bayesian_publication_alignment.csv", alignment_rows, ALIGNMENT_FIELDS)
    write_markdown(manifest_rows, alignment_rows)
    print(f"manifest={OUT_DIR / 'he2_bayesian_publication_manifest.csv'}")
    print(f"inputs={OUT_DIR / 'he2_bayesian_publication_inputs.csv'}")
    print(f"alignment={OUT_DIR / 'he2_bayesian_publication_alignment.csv'}")
    print(f"markdown={OUT_DIR / 'he2_bayesian_publication_manifest.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
