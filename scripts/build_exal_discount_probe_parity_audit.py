#!/usr/bin/env python3

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
RUNTIME_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")
OUTPUT_DIR = REPO_ROOT / "reports" / "quantile_discount_probe_analysis"
CSV_OUT = OUTPUT_DIR / "exal_multivar_keep_discount_probe_parity_audit.csv"
MD_OUT = OUTPUT_DIR / "exal_multivar_keep_discount_probe_parity_audit.md"

CUSTOM_SELECTION = (
    RUNTIME_ROOT
    / "multimodel_v8_quantile_featurecov_custom_discount_probe_20260422"
    / "control"
    / "quantile_featurecov_custom_discount_probe_v1"
    / "selection_summary.csv"
)

NDLM_TIGHT_SELECTION = (
    RUNTIME_ROOT
    / "multimodel_v8_quantile_featurecov_ndlm_discount_probe_20260422"
    / "control"
    / "quantile_featurecov_ndlm_discount_probe_v1"
    / "selection_summary.csv"
)

TARGET_FILES = [
    "parameters/parameters.txt",
    "retros/retros.csv",
    "forecasts/nws_forecast.csv",
    "forecasts/glofas_forecast.csv",
    "covariates/cov_01_PPT.csv",
    "covariates/cov_02_SOIL.csv",
    "covariates/cov_03_PCA.csv",
    "covariates/covariate_features.csv",
    "deterministic_climate/deterministic_precip_future.csv",
    "deterministic_climate/deterministic_soil_future.csv",
]

PAIR_SPECS = [
    ("baseline_vs_custom", "Current HE2 baseline", "Featurecov custom discount probe"),
    ("baseline_vs_ndlm_tight", "Current HE2 baseline", "Featurecov NDLM-tight discount probe"),
    ("custom_vs_ndlm_tight", "Featurecov custom discount probe", "Featurecov NDLM-tight discount probe"),
]

FIELDNAMES = [
    "cutoff",
    "pair_key",
    "left_label",
    "right_label",
    "legacy_knobs_match",
    "transfer_mode_match",
    "fit_covariates_match",
    "covariate_feature_settings_match",
    "deterministic_climate_settings_match",
    "warm_start_effectively_disabled_match",
    "parallel_workers_left",
    "parallel_workers_right",
    "discount_block_equal",
    "hash_match_count",
    "hash_diff_count",
    "diff_files",
    "first_ppt_diff_date",
    "first_soil_diff_date",
    "first_features_diff_date",
    "first_precip_future_diff_date",
    "first_soil_future_diff_date",
    "overall_only_discount_difference",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return yaml.safe_load(handle)


def sha256_short(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def canonical_cutoff_map() -> dict[str, dict[str, Path]]:
    rows = read_csv(CUSTOM_SELECTION)
    mapping: dict[str, dict[str, Path]] = {}
    for row in rows:
        if row["family_id"] != "exdqlm_multivar_keep":
            continue
        cutoff = row["cutoff"]
        mapping[cutoff] = {
            "baseline_run_root": Path(row["selected_source_config"]).parent,
            "custom_run_root": (
                RUNTIME_ROOT
                / "multimodel_v8_quantile_featurecov_custom_discount_probe_20260422"
                / "runs"
                / row["run_id"]
            ),
        }

    ndlm_rows = read_csv(NDLM_TIGHT_SELECTION)
    for row in ndlm_rows:
        if row["family_id"] != "exdqlm_multivar_keep":
            continue
        cutoff = row["cutoff"]
        mapping[cutoff]["ndlm_tight_run_root"] = (
            RUNTIME_ROOT
            / "multimodel_v8_quantile_featurecov_ndlm_discount_probe_20260422"
            / "runs"
            / row["run_id"]
        )
    return mapping


def model_config(run_root: Path) -> dict[str, Any]:
    return load_yaml(run_root / "resolved_config.yaml")


def extract_core_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": config["models"]["exdqlm_multivar"]["state_evolution"],
        "transfer_mode": config["models"]["exdqlm_multivar"]["forecast_transfer_mode"],
        "legacy": config["fit"]["exdqlm_multivar"]["legacy"],
        "fit_covariates": [item["name"] for item in config["inputs"]["fit"]["covariates"]],
        "covariate_features": config["inputs"]["covariate_features"],
        "deterministic_climate": config["inputs"]["deterministic_climate"],
        "warm_start": config.get("fit", {}).get("warm_start", {}),
        "parallel_workers": config.get("fit", {}).get("parallel", {}).get("workers"),
    }


def effective_warm_start_disabled(block: dict[str, Any]) -> bool:
    return not bool(block.get("enabled", False))


def compare_file_hashes(left_root: Path, right_root: Path) -> tuple[int, int, list[str]]:
    diffs: list[str] = []
    matches = 0
    for rel in TARGET_FILES:
        left = left_root / "inputs" / "shared" / rel
        right = right_root / "inputs" / "shared" / rel
        if left.exists() and right.exists() and sha256_short(left) == sha256_short(right):
            matches += 1
        else:
            diffs.append(rel)
    return matches, len(diffs), diffs


def first_diff_date(left_path: Path, right_path: Path) -> str:
    if not left_path.exists() or not right_path.exists():
        return ""
    with left_path.open(newline="") as left_handle, right_path.open(newline="") as right_handle:
        left_rows = list(csv.DictReader(left_handle))
        right_rows = list(csv.DictReader(right_handle))
    for left_row, right_row in zip(left_rows, right_rows):
        if left_row != right_row:
            for key in ("date", "Date", "target_date"):
                if key in left_row:
                    return str(left_row[key])
            return "<non-date diff>"
    return ""


def build_rows() -> list[dict[str, str]]:
    mapping = canonical_cutoff_map()
    rows: list[dict[str, str]] = []
    for cutoff, roots in sorted(mapping.items()):
        configs = {
            "Current HE2 baseline": extract_core_config(model_config(roots["baseline_run_root"])),
            "Featurecov custom discount probe": extract_core_config(model_config(roots["custom_run_root"])),
            "Featurecov NDLM-tight discount probe": extract_core_config(model_config(roots["ndlm_tight_run_root"])),
        }
        run_roots = {
            "Current HE2 baseline": roots["baseline_run_root"],
            "Featurecov custom discount probe": roots["custom_run_root"],
            "Featurecov NDLM-tight discount probe": roots["ndlm_tight_run_root"],
        }

        for pair_key, left_label, right_label in PAIR_SPECS:
            left_cfg = configs[left_label]
            right_cfg = configs[right_label]
            left_root = run_roots[left_label]
            right_root = run_roots[right_label]
            hash_matches, hash_diffs, diff_files = compare_file_hashes(left_root, right_root)

            rows.append(
                {
                    "cutoff": cutoff,
                    "pair_key": pair_key,
                    "left_label": left_label,
                    "right_label": right_label,
                    "legacy_knobs_match": str(left_cfg["legacy"] == right_cfg["legacy"]),
                    "transfer_mode_match": str(left_cfg["transfer_mode"] == right_cfg["transfer_mode"]),
                    "fit_covariates_match": str(left_cfg["fit_covariates"] == right_cfg["fit_covariates"]),
                    "covariate_feature_settings_match": str(
                        left_cfg["covariate_features"] == right_cfg["covariate_features"]
                    ),
                    "deterministic_climate_settings_match": str(
                        left_cfg["deterministic_climate"] == right_cfg["deterministic_climate"]
                    ),
                    "warm_start_effectively_disabled_match": str(
                        effective_warm_start_disabled(left_cfg["warm_start"])
                        == effective_warm_start_disabled(right_cfg["warm_start"])
                        and effective_warm_start_disabled(left_cfg["warm_start"])
                    ),
                    "parallel_workers_left": str(left_cfg["parallel_workers"]),
                    "parallel_workers_right": str(right_cfg["parallel_workers"]),
                    "discount_block_equal": str(left_cfg["state"] == right_cfg["state"]),
                    "hash_match_count": str(hash_matches),
                    "hash_diff_count": str(hash_diffs),
                    "diff_files": "|".join(diff_files),
                    "first_ppt_diff_date": first_diff_date(
                        left_root / "inputs" / "shared" / "covariates" / "cov_01_PPT.csv",
                        right_root / "inputs" / "shared" / "covariates" / "cov_01_PPT.csv",
                    ),
                    "first_soil_diff_date": first_diff_date(
                        left_root / "inputs" / "shared" / "covariates" / "cov_02_SOIL.csv",
                        right_root / "inputs" / "shared" / "covariates" / "cov_02_SOIL.csv",
                    ),
                    "first_features_diff_date": first_diff_date(
                        left_root / "inputs" / "shared" / "covariates" / "covariate_features.csv",
                        right_root / "inputs" / "shared" / "covariates" / "covariate_features.csv",
                    ),
                    "first_precip_future_diff_date": first_diff_date(
                        left_root
                        / "inputs"
                        / "shared"
                        / "deterministic_climate"
                        / "deterministic_precip_future.csv",
                        right_root
                        / "inputs"
                        / "shared"
                        / "deterministic_climate"
                        / "deterministic_precip_future.csv",
                    ),
                    "first_soil_future_diff_date": first_diff_date(
                        left_root
                        / "inputs"
                        / "shared"
                        / "deterministic_climate"
                        / "deterministic_soil_future.csv",
                        right_root
                        / "inputs"
                        / "shared"
                        / "deterministic_climate"
                        / "deterministic_soil_future.csv",
                    ),
                    "overall_only_discount_difference": str(
                        left_cfg["legacy"] == right_cfg["legacy"]
                        and left_cfg["transfer_mode"] == right_cfg["transfer_mode"]
                        and left_cfg["fit_covariates"] == right_cfg["fit_covariates"]
                        and left_cfg["covariate_features"] == right_cfg["covariate_features"]
                        and left_cfg["deterministic_climate"] == right_cfg["deterministic_climate"]
                        and effective_warm_start_disabled(left_cfg["warm_start"])
                        and effective_warm_start_disabled(right_cfg["warm_start"])
                        and hash_diffs == 0
                    ),
                }
            )
    return rows


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def build_markdown(rows: list[dict[str, str]]) -> str:
    by_pair: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_pair[row["pair_key"]].append(row)

    summary_rows = []
    for pair_key, pair_rows in by_pair.items():
        summary_rows.append(
            [
                pair_key,
                pair_rows[0]["left_label"],
                pair_rows[0]["right_label"],
                sum(row["overall_only_discount_difference"] == "True" for row in pair_rows),
                len(pair_rows),
                pair_rows[0]["hash_diff_count"],
                pair_rows[0]["diff_files"],
            ]
        )

    cutoff_rows = []
    for row in rows:
        if row["pair_key"] != "baseline_vs_custom":
            continue
        ndlm_row = next(
            item
            for item in rows
            if item["pair_key"] == "baseline_vs_ndlm_tight" and item["cutoff"] == row["cutoff"]
        )
        cutoff_rows.append(
            [
                row["cutoff"],
                row["hash_match_count"],
                row["diff_files"],
                row["first_features_diff_date"],
                ndlm_row["hash_match_count"],
                ndlm_row["diff_files"],
                ndlm_row["first_features_diff_date"],
            ]
        )

    return f"""# exAL-M-T1 Discount Probe Parity Audit

This audit checks whether the completed `exAL-M-T1` discount-factor probe runs differ from the current HE2 `exAL-M-T1` row **only** in the discount-factor block.

## Main Conclusion

- The two completed probe campaigns, `Featurecov custom discount probe` and `Featurecov NDLM-tight discount probe`, are **discount-only variants of each other** for `exdqlm_multivar_keep`.
- They are **not** discount-only variants of the current HE2 `exAL-M-T1` baseline.
- Relative to the current HE2 baseline, both completed probe campaigns use the same raw parameters, retrospective series, NWS forecast, GloFAS forecast, and PCA file, but they use **different forecast-window PPT/SOIL covariate files, a different engineered covariate-feature file, and different deterministic-climate future files**.
- The first real covariate divergence starts at the forecast window, not in the historical segment.

## Pair Summary

{markdown_table(
    [
        "Pair key",
        "Left",
        "Right",
        "Only-discount rows",
        "Rows",
        "Per-row hash diff count",
        "Diff files",
    ],
    summary_rows,
)}

## Cutoff-Level Baseline vs Probe Input Differences

{markdown_table(
    [
        "Cutoff",
        "Baseline vs custom matches",
        "Baseline vs custom diff files",
        "First feature diff date",
        "Baseline vs NDLM-tight matches",
        "Baseline vs NDLM-tight diff files",
        "First feature diff date",
    ],
    cutoff_rows,
)}

## Interpretation

- The completed probes are a clean discount-only comparison **with each other**.
- They are **not** a clean discount-only comparison against the current HE2 `exAL-M-T1` row.
- So the earlier CRPS comparison showing that neither completed probe beats the HE2 row is still useful operationally, but it is **confounded** if interpreted as a pure discount-factor sensitivity test relative to the current HE2 baseline.
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
