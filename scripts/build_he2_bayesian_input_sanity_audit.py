#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
JROOT = ROOT.parent

CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]
MODEL_ORDER = [
    "exdqlm_multivar_keep",
    "dqlm_multivar_al_keep",
    "exdqlm_multivar_drop",
    "dqlm_multivar_al_drop",
    "exdqlm_univar",
    "dqlm_univar_al",
    "ndlm_main_keep",
    "ndlm_main_drop",
    "ndlm_univar_keep",
]
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
ARTIFACT_SPECS = [
    ("parameters", "inputs/shared/parameters/parameters.txt"),
    ("retros", "inputs/shared/retros/retros.csv"),
    ("nws_forecast", "inputs/shared/forecasts/nws_forecast.csv"),
    ("glofas_forecast", "inputs/shared/forecasts/glofas_forecast.csv"),
    ("cov_01_PPT", "inputs/shared/covariates/cov_01_PPT.csv"),
    ("cov_02_SOIL", "inputs/shared/covariates/cov_02_SOIL.csv"),
    ("cov_03_PCA", "inputs/shared/covariates/cov_03_PCA.csv"),
    ("covariate_features", "inputs/shared/covariates/covariate_features.csv"),
    ("deterministic_precip_future", "inputs/shared/deterministic_climate/deterministic_precip_future.csv"),
    ("deterministic_soil_future", "inputs/shared/deterministic_climate/deterministic_soil_future.csv"),
]


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve_multivar_rows() -> list[dict[str, str]]:
    best_path = JROOT / "project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/final_featurecov_cf1_eps_analysis/best_by_cutoff_long.csv"
    best_rows = load_csv(best_path)
    out: list[dict[str, str]] = []
    for cutoff in CUTOFFS:
        cutoff_rows = [r for r in best_rows if r["cutoff"] == cutoff and r["model_variant"] in MODEL_ORDER[:4]]
        keep_row = next(r for r in cutoff_rows if r["model_variant"] == "exdqlm_multivar_keep")
        compare_path = JROOT / f"project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/multimodel_{cutoff}_v8_{keep_row['best_epsilon_label']}_compare/source_provenance.csv"
        for row in load_csv(compare_path):
            family = row.get("family_id", "")
            if family not in MODEL_ORDER[:4]:
                continue
            run_id = row["source_run"]
            candidates = [JROOT / f"project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/runs/{run_id}"]
            run_root = next((p for p in candidates if p.exists()), None)
            if run_root is None:
                raise FileNotFoundError(f"Could not resolve multivar run root for {cutoff}/{family}: {run_id}")
            out.append({"cutoff": cutoff, "family": family, "run_id": run_id, "run_root": str(run_root)})
    return out


def resolve_univar_rows() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    run_root_base = JROOT / "project1_ucsc_phd_runtime/multimodel_v8_univar_featurecov_he2_rerun_20260422/runs"
    for cutoff in CUTOFFS:
        compare_path = JROOT / f"project1_ucsc_phd_runtime/multimodel_v8_univar_featurecov_he2_rerun_20260422/reports/multimodel_{cutoff}_v8_univar_featurecov_he2_v1_compare/source_provenance.csv"
        for row in load_csv(compare_path):
            family = MODEL_ID_TO_FAMILY.get(row["model_id"], "")
            if family not in {"exdqlm_univar", "dqlm_univar_al"}:
                continue
            run_id = row["source_run"]
            run_root = run_root_base / run_id
            if not run_root.exists():
                raise FileNotFoundError(f"Could not resolve univar run root for {cutoff}/{family}: {run_id}")
            out.append({"cutoff": cutoff, "family": family, "run_id": run_id, "run_root": str(run_root)})
    return out


def resolve_ndlm_rows() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    run_root_base = JROOT / "project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/runs"
    for cutoff in CUTOFFS:
        compare_path = JROOT / f"project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/reports/multimodel_{cutoff}_v8_ndlm_featurecov_v1_postfix_compare/source_provenance.csv"
        for row in load_csv(compare_path):
            family = MODEL_ID_TO_FAMILY.get(row["model_id"], "")
            if family not in {"ndlm_main_keep", "ndlm_main_drop", "ndlm_univar_keep"}:
                continue
            run_id = row["source_run"]
            run_root = run_root_base / run_id
            if not run_root.exists():
                raise FileNotFoundError(f"Could not resolve NDLM run root for {cutoff}/{family}: {run_id}")
            out.append({"cutoff": cutoff, "family": family, "run_id": run_id, "run_root": str(run_root)})
    return out


def resolve_artifact(run_root: Path, rel: str, cfg: dict[str, Any]) -> tuple[Path | None, str]:
    shared_path = run_root / rel
    if shared_path.exists():
        return shared_path, "shared_snapshot"

    if rel == "inputs/shared/parameters/parameters.txt":
        path = Path(cfg["inputs"]["fit"]["parameters_path"])
        return (path if path.exists() else None), "resolved_config"
    if rel == "inputs/shared/retros/retros.csv":
        path = Path(cfg["inputs"]["fit"]["retros_path"])
        return (path if path.exists() else None), "resolved_config"
    if rel == "inputs/shared/forecasts/nws_forecast.csv":
        path = Path(cfg["inputs"]["fit"]["nws_forecast_path"])
        return (path if path.exists() else None), "resolved_config"
    if rel == "inputs/shared/forecasts/glofas_forecast.csv":
        path = Path(cfg["inputs"]["fit"]["glofas_forecast_path"])
        return (path if path.exists() else None), "resolved_config"
    if rel == "inputs/shared/covariates/cov_01_PPT.csv":
        path = next((Path(x["path"]) for x in cfg["inputs"]["fit"]["covariates"] if x["name"] == "PPT"), None)
        return (path if path and path.exists() else None), "resolved_config"
    if rel == "inputs/shared/covariates/cov_02_SOIL.csv":
        path = next((Path(x["path"]) for x in cfg["inputs"]["fit"]["covariates"] if x["name"] == "SOIL"), None)
        return (path if path and path.exists() else None), "resolved_config"
    if rel == "inputs/shared/covariates/cov_03_PCA.csv":
        path = next((Path(x["path"]) for x in cfg["inputs"]["fit"]["covariates"] if x["name"] == "PCA"), None)
        return (path if path and path.exists() else None), "resolved_config"

    return None, "missing"


def build_rows() -> list[dict[str, str]]:
    rows = resolve_multivar_rows() + resolve_univar_rows() + resolve_ndlm_rows()
    rows = sorted(rows, key=lambda r: (r["cutoff"], MODEL_ORDER.index(r["family"])))
    if len(rows) != 45:
        raise RuntimeError(f"Expected 45 authoritative HE2 rows, found {len(rows)}")
    return rows


def main() -> int:
    out_root = ROOT / "reports/he2_bayesian_input_sanity_audit"
    out_root.mkdir(parents=True, exist_ok=True)

    rows = build_rows()
    detail_rows: list[dict[str, Any]] = []
    cutoff_artifact_summary: list[dict[str, Any]] = []
    contract_rows: list[dict[str, Any]] = []

    for row in rows:
        cfg = read_yaml(Path(row["run_root"]) / "resolved_config.yaml")
        fit_covariates = cfg.get("inputs", {}).get("fit", {}).get("covariates", []) or []
        cov_names = [x["name"] for x in fit_covariates if isinstance(x, dict) and x.get("name")]
        det_cfg = cfg.get("inputs", {}).get("deterministic_climate", {}) or {}
        covfeat_cfg = cfg.get("inputs", {}).get("covariate_features", {}) or {}
        contract_rows.append(
            {
                "cutoff": row["cutoff"],
                "family": row["family"],
                "run_id": row["run_id"],
                "run_root": row["run_root"],
                "covariate_names": "|".join(cov_names),
                "deterministic_climate_enabled": bool(det_cfg.get("enabled", False)),
                "covariate_features_enabled": bool(covfeat_cfg.get("enabled", False)),
                "lag_orders": "|".join(str(x) for x in (covfeat_cfg.get("lag_orders") or [])),
                "include_squares": bool(covfeat_cfg.get("include_squares", False)),
                "include_interaction": bool(covfeat_cfg.get("include_interaction", False)),
            }
        )

        for artifact, rel in ARTIFACT_SPECS:
            resolved_path, source_kind = resolve_artifact(Path(row["run_root"]), rel, cfg)
            detail_rows.append(
                {
                    "cutoff": row["cutoff"],
                    "family": row["family"],
                    "run_id": row["run_id"],
                    "artifact": artifact,
                    "path": str(resolved_path) if resolved_path else "",
                    "source_kind": source_kind,
                    "hash16": sha16(resolved_path) if resolved_path and resolved_path.exists() else "",
                    "exists": bool(resolved_path and resolved_path.exists()),
                }
            )

    for cutoff in CUTOFFS:
        cutoff_rows = [r for r in detail_rows if r["cutoff"] == cutoff]
        for artifact, _ in ARTIFACT_SPECS:
            artifact_rows = [r for r in cutoff_rows if r["artifact"] == artifact]
            hashes = defaultdict(list)
            for r in artifact_rows:
                if r["exists"]:
                    hashes[r["hash16"]].append(r["family"])
            missing = [r["family"] for r in artifact_rows if not r["exists"]]
            cutoff_artifact_summary.append(
                {
                    "cutoff": cutoff,
                    "artifact": artifact,
                    "distinct_hashes": len(hashes),
                    "missing_count": len(missing),
                    "all_equal": len(hashes) == 1 and len(missing) == 0,
                    "hash_groups": json.dumps({k: sorted(v) for k, v in hashes.items()}, sort_keys=True),
                    "missing_families": "|".join(sorted(missing)),
                }
            )

    detail_path = out_root / "he2_bayesian_input_sanity_detail.csv"
    summary_path = out_root / "he2_bayesian_input_sanity_summary.csv"
    contract_path = out_root / "he2_bayesian_input_sanity_contracts.csv"

    with detail_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(detail_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detail_rows)

    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cutoff_artifact_summary[0].keys()))
        writer.writeheader()
        writer.writerows(cutoff_artifact_summary)

    with contract_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(contract_rows[0].keys()))
        writer.writeheader()
        writer.writerows(contract_rows)

    md_lines = [
        "# HE2 Bayesian Input Sanity Audit",
        "",
        "This audit checks the authoritative current HE2 Bayesian rows (9 models x 5 cutoffs) and verifies whether, within each cutoff, they use the same shared historical inputs, forecast inputs, forecast-window covariate products, and blended-feature files.",
        "",
        "## Headline",
        "",
    ]
    total_summary = len(cutoff_artifact_summary)
    passed_summary = sum(1 for r in cutoff_artifact_summary if r["all_equal"])
    md_lines.extend(
        [
            f"- artifact checks passed: `{passed_summary} / {total_summary}`",
            f"- cutoffs audited: `{len(CUTOFFS)}`",
            f"- Bayesian HE2 rows audited: `{len(rows)}`",
            "",
            "## By Cutoff",
            "",
            "| Cutoff | Artifact Checks Passing | Result |",
            "|---|---:|---|",
        ]
    )
    for cutoff in CUTOFFS:
        subset = [r for r in cutoff_artifact_summary if r["cutoff"] == cutoff]
        passed = sum(1 for r in subset if r["all_equal"])
        status = "All shared inputs/covariate products aligned" if passed == len(subset) else "See summary CSV for exceptions"
        md_lines.append(f"| `{cutoff}` | `{passed} / {len(subset)}` | {status} |")

    cov_name_sets = sorted({r["covariate_names"] for r in contract_rows})
    det_flags = sorted({str(r["deterministic_climate_enabled"]) for r in contract_rows})
    feature_flags = sorted({str(r["covariate_features_enabled"]) for r in contract_rows})
    md_lines.extend(
        [
            "",
            "## Contract Check",
            "",
            f"- covariate name sets observed: `{cov_name_sets}`",
            f"- deterministic-climate enabled flags observed: `{det_flags}`",
            f"- covariate-features enabled flags observed: `{feature_flags}`",
            "",
            "## Outputs",
            "",
            f"- detail: `{detail_path}`",
            f"- summary: `{summary_path}`",
            f"- contracts: `{contract_path}`",
        ]
    )
    (out_root / "he2_bayesian_input_sanity_audit.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"detail_csv={detail_path}")
    print(f"summary_csv={summary_path}")
    print(f"contracts_csv={contract_path}")
    print(f"markdown={out_root / 'he2_bayesian_input_sanity_audit.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
