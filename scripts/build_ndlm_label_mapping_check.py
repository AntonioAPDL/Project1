#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
CORRECTIONS_MAIN = Path("/data/muscat_data/jaguir26/Corrections---Project-1/main.tex")
FEATURECOV_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_featurecov_cf1_eps_sweep_20260416"
)
OLD_PACKAGED_MANIFEST = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_20260402/exports/best9_cutoff_png_package_20260406/selection_manifest.csv"
)
NDLM_FEATURECOV_RERUN_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_ndlm_featurecov_rerun_20260420/runs"
)
OUTPUT_DIR = REPO_ROOT / "reports" / "ndlm_parity_audit"
CSV_OUT = OUTPUT_DIR / "label_mapping_check.csv"
MD_OUT = OUTPUT_DIR / "PHASE2_LABEL_MAPPING_SUMMARY.md"
RUN_ROOT_CANDIDATES = {
    "baseline_tt": Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/runs"),
    "ndlm_relaunch_20260411": Path(
        "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_20260411/runs"
    ),
}

CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]
MANUSCRIPT_LABELS = {
    "N-U-T1": {
        "model_variant": "ndlm_univar_keep",
        "model_id": "ndlm_univar_synth_keep",
        "transfer_mode": "keep",
    },
    "N-M-T0": {
        "model_variant": "ndlm_main_drop",
        "model_id": "ndlm_main_synth_drop",
        "transfer_mode": "drop",
    },
    "N-M-T1": {
        "model_variant": "ndlm_main_keep",
        "model_id": "ndlm_main_synth_keep",
        "transfer_mode": "keep",
    },
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_manuscript_rows(path: Path) -> dict[str, dict[str, float]]:
    lines = path.read_text().splitlines()
    out: dict[str, dict[str, float]] = {}
    for label in MANUSCRIPT_LABELS:
        candidates = [line for line in lines if line.startswith(f"{label} & ")]
        value_row = next(line for line in candidates if re.search(r"&\s*[0-9]", line))
        raw_values = [chunk.replace("\\\\", "").strip() for chunk in value_row.split("&")[1:6]]
        out[label] = {cutoff: float(value) for cutoff, value in zip(CUTOFFS, raw_values)}
    return out


def lineage_from_run_id(run_id: str) -> str:
    if not run_id:
        return "unknown"
    if "ndlm_tune_20260411" in run_id:
        return "ndlm_relaunch_20260411"
    if "_epsTT_" in run_id:
        return "baseline_tt"
    if "featurecov" in run_id:
        return "featurecov_cf1_eps_sweep"
    return "unknown"


def resolve_run_root(run_id: str, lineage: str) -> tuple[str, str]:
    if not run_id:
        return "", ""
    base = RUN_ROOT_CANDIDATES.get(lineage)
    if base is None:
        return "", ""
    run_root = base / run_id
    resolved_config = run_root / "resolved_config.yaml"
    return (
        str(run_root) if run_root.exists() else "",
        str(resolved_config) if resolved_config.exists() else "",
    )


def compare_report_records() -> dict[tuple[str, str], list[dict[str, object]]]:
    records: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for prov_path in sorted(FEATURECOV_ROOT.glob("reports/multimodel_*_compare/source_provenance.csv")):
        compare_dir = prov_path.parent
        parts = compare_dir.name.split("_")
        cutoff = parts[1]
        epsilon_label = parts[3]

        prov_rows = {row["model_id"]: row for row in read_csv(prov_path)}
        crps_rows = {row["model_id"]: row for row in read_csv(compare_dir / "crps_forecast_summary_all_models.csv")}

        for spec in MANUSCRIPT_LABELS.values():
            model_variant = spec["model_variant"]
            model_id = spec["model_id"]
            if model_id not in prov_rows or model_id not in crps_rows:
                continue
            prov_row = prov_rows[model_id]
            crps_row = crps_rows[model_id]
            selected_source_run = prov_row.get("selected_source_run", "") or prov_row.get("source_run", "")
            records[(model_variant, cutoff)].append(
                {
                    "compare_dir": str(compare_dir),
                    "epsilon_label": epsilon_label,
                    "mean_crps": float(crps_row["mean_crps"]),
                    "source_run": prov_row.get("source_run", ""),
                    "source_type": prov_row.get("source_type", ""),
                    "selected_source_run": selected_source_run,
                    "selected_source_lineage": lineage_from_run_id(selected_source_run),
                }
            )
    return records


def corrected_rerun_values() -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for cutoff in CUTOFFS:
        for model_variant in {spec["model_variant"] for spec in MANUSCRIPT_LABELS.values()}:
            run_id = f"multimodel_{cutoff}_v8_ndlm_featurecov_v1_{model_variant}"
            summary = (
                NDLM_FEATURECOV_RERUN_ROOT
                / run_id
                / "post"
                / "outputs"
                / run_id
                / "tables"
                / "crps_forecast_summary.csv"
            )
            if summary.exists():
                with summary.open(newline="") as handle:
                    row = next(csv.DictReader(handle))
                out[(model_variant, cutoff)] = float(row["mean_crps"])
    return out


def choose_current_record(
    model_variant: str,
    cutoff: str,
    records: dict[tuple[str, str], list[dict[str, object]]],
) -> dict[str, object]:
    candidates = records[(model_variant, cutoff)]
    if not candidates:
        raise RuntimeError(f"Missing compare-report provenance for {model_variant} @ {cutoff}")
    if model_variant == "ndlm_univar_keep":
        return sorted(candidates, key=lambda row: (str(row["epsilon_label"]), str(row["compare_dir"])))[0]
    return min(candidates, key=lambda row: float(row["mean_crps"]))


def rounded_match(a: float, b: float, digits: int = 4) -> bool:
    return round(a, digits) == round(b, digits)


def build_rows() -> list[dict[str, object]]:
    manuscript = read_manuscript_rows(CORRECTIONS_MAIN)
    best_long = {
        (row["model_variant"], row["cutoff"]): row
        for row in read_csv(
            FEATURECOV_ROOT / "reports" / "final_featurecov_cf1_eps_analysis" / "best_by_cutoff_long.csv"
        )
    }
    old_manifest = {
        (row["model_id"], row["cutoff"]): row
        for row in read_csv(OLD_PACKAGED_MANIFEST)
        if row["model_id"] in {spec["model_id"] for spec in MANUSCRIPT_LABELS.values()}
    }
    rerun_values = corrected_rerun_values()
    report_records = compare_report_records()

    rows: list[dict[str, object]] = []
    for manuscript_label, spec in MANUSCRIPT_LABELS.items():
        model_variant = spec["model_variant"]
        model_id = spec["model_id"]
        for cutoff in CUTOFFS:
            current_summary = best_long[(model_variant, cutoff)]
            chosen_record = choose_current_record(model_variant, cutoff, report_records)
            candidate_values = [
                float(row["mean_crps"]) for row in report_records[(model_variant, cutoff)]
            ]
            old_row = old_manifest.get((model_id, cutoff))
            manuscript_value = manuscript[manuscript_label][cutoff]
            final_summary_value = float(current_summary["forecast_window_crps"])
            current_compare_value = float(chosen_record["mean_crps"])
            corrected_rerun_value = rerun_values.get((model_variant, cutoff), math.nan)
            old_value = float(old_row["mean_crps"]) if old_row else math.nan

            rows.append(
                {
                    "manuscript_label": manuscript_label,
                    "cutoff": cutoff,
                    "model_variant": model_variant,
                    "model_id": model_id,
                    "expected_transfer_mode": spec["transfer_mode"],
                    "manuscript_he2_value": manuscript_value,
                    "current_final_summary_value": final_summary_value,
                    "current_selection_class": current_summary["class"],
                    "current_selection_basis": current_summary["selection_basis"],
                    "current_best_epsilon_label": current_summary["best_epsilon_label"],
                    "current_best_epsilon_value": current_summary["best_epsilon_value"],
                    "current_compare_dir": chosen_record["compare_dir"],
                    "current_compare_value": current_compare_value,
                    "corrected_rerun_value": corrected_rerun_value,
                    "current_selected_source_run": chosen_record["selected_source_run"],
                    "current_selected_source_lineage": chosen_record["selected_source_lineage"],
                    "current_selected_source_run_root": resolve_run_root(
                        str(chosen_record["selected_source_run"]),
                        str(chosen_record["selected_source_lineage"]),
                    )[0],
                    "current_selected_source_resolved_config": resolve_run_root(
                        str(chosen_record["selected_source_run"]),
                        str(chosen_record["selected_source_lineage"]),
                    )[1],
                    "current_compare_source_type": chosen_record["source_type"],
                    "current_compare_source_run": chosen_record["source_run"],
                    "compare_values_unique_count": len({round(value, 12) for value in candidate_values}),
                    "compare_values_min": min(candidate_values),
                    "compare_values_max": max(candidate_values),
                    "manuscript_matches_current_summary_4dp": rounded_match(
                        manuscript_value, final_summary_value
                    ),
                    "manuscript_matches_current_compare_4dp": rounded_match(
                        manuscript_value, current_compare_value
                    ),
                    "manuscript_matches_corrected_rerun_4dp": (
                        rounded_match(manuscript_value, corrected_rerun_value)
                        if not math.isnan(corrected_rerun_value)
                        else ""
                    ),
                    "old_packaged_best9_value": old_value if old_row else "",
                    "old_packaged_best9_source_run_dir": old_row["source_run_dir"] if old_row else "",
                    "old_packaged_matches_current_summary_4dp": (
                        rounded_match(final_summary_value, old_value) if old_row else ""
                    ),
                }
            )
    return rows


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def row(label: str, cutoff: str) -> dict[str, object]:
        return next(item for item in rows if item["manuscript_label"] == label and item["cutoff"] == cutoff)

    baseline_count = sum(1 for item in rows if item["current_selected_source_lineage"] == "baseline_tt")
    relaunch_count = sum(1 for item in rows if item["current_selected_source_lineage"] == "ndlm_relaunch_20260411")
    stale_old_count = sum(
        1
        for item in rows
        if item["old_packaged_best9_value"] != ""
        and not item["old_packaged_matches_current_summary_4dp"]
    )

    lines: list[str] = []
    lines.append("# Phase 2 NDLM Label Mapping and Provenance Summary")
    lines.append("")
    lines.append("Status: complete")
    lines.append("")
    lines.append("## Headline Findings")
    lines.append("")
    lines.append(
        "- This phase established the pre-rerun provenance chain behind the older NDLM manuscript rows: they aligned with the final featurecov summary in "
        "[best_by_cutoff_long.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
        "multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/final_featurecov_cf1_eps_analysis/"
        "best_by_cutoff_long.csv), not with the older packaged "
        "[selection_manifest.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
        "multimodel_v8_20260402/exports/best9_cutoff_png_package_20260406/selection_manifest.csv)."
    )
    lines.append(
        "- The current HE2 NDLM rows in the manuscript have since been replaced by the corrected NDLM featurecov rerun values; the provenance columns below are retained as historical context for why that rerun was needed."
    )
    lines.append(
        f"- Across the 15 NDLM HE2 cells, the current selected source lineage is `baseline_tt` in "
        f"{baseline_count} cells and `ndlm_relaunch_20260411` in {relaunch_count} cell."
    )
    lines.append(
        f"- The older packaged best9 manifest is stale for {stale_old_count} of the 15 NDLM HE2 cells."
    )
    lines.append("")
    lines.append("## Label Mapping")
    lines.append("")
    lines.append("| Manuscript label | Unified family | Model ID | Transfer mode | Current provenance role |")
    lines.append("| --- | --- | --- | --- | --- |")
    lines.append("| `N-U-T1` | `ndlm_univar_keep` | `ndlm_univar_synth_keep` | `keep` | fixed baseline carried forward in current featurecov summary |")
    lines.append("| `N-M-T0` | `ndlm_main_drop` | `ndlm_main_synth_drop` | `drop` | tuned current cf1 selection from current featurecov summary |")
    lines.append("| `N-M-T1` | `ndlm_main_keep` | `ndlm_main_synth_keep` | `keep` | tuned current cf1 selection from current featurecov summary |")
    lines.append("")
    lines.append("## Historical Provenance By Cutoff")
    lines.append("")
    lines.append("| Label | Cutoff | Current HE2 value | Historical source lineage | Historical selected source run | Historical compare dir |")
    lines.append("| --- | --- | ---: | --- | --- | --- |")
    for manuscript_label in MANUSCRIPT_LABELS:
        for cutoff in CUTOFFS:
            item = row(manuscript_label, cutoff)
            lines.append(
                f"| `{manuscript_label}` | `{cutoff}` | `{float(item['manuscript_he2_value']):.4f}` | "
                f"`{item['current_selected_source_lineage']}` | `{item['current_selected_source_run']}` | "
                f"`{Path(str(item['current_compare_dir'])).name}` |"
            )
    lines.append("")
    lines.append("## Important Provenance Interpretation")
    lines.append("")
    lines.append(
        "- Historically, `N-U-T1` did not come from the dedicated NDLM relaunch tree. It was a carried-forward baseline row, and that older value was validated against the current featurecov compare reports rather than the older packaged best9 manifest."
    )
    lines.append(
        "- Historically, `N-M-T0` resolved to featurecov summary selections whose underlying selected source run remained in the baseline TT lineage for all five cutoffs."
    )
    lines.append(
        "- Historically, `N-M-T1` resolved mostly to baseline TT lineage, except for cutoff `20210123`, where the selected underlying source run came from the dedicated `ndlm_tune_20260411_v1` relaunch."
    )
    lines.append("")
    lines.append("## Old Packaged Best9 Manifest Status")
    lines.append("")
    lines.append(
        "- The older packaged best9 export manifest should not be treated as the authoritative current source for the NDLM HE2 rows."
    )
    lines.append(
        "- It still matches some current cells, but it diverges materially for the multivariate NDLM rows and also diverges for `N-U-T1` at cutoffs `20211221` and `20220511`."
    )
    lines.append("")
    lines.append("## Historical Role In The Audit")
    lines.append("")
    lines.append(
        "- This phase provided the provenance baseline that justified the later corrected rerun. The current manuscript-facing NDLM rows should now be interpreted through the completed rerun documented in `ndlm_final_audit_summary.md`, not through the historical featurecov compare lineage captured here."
    )

    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    rows = build_rows()
    write_csv(rows, CSV_OUT)
    write_summary(rows, MD_OUT)
    print(f"wrote {CSV_OUT}")
    print(f"wrote {MD_OUT}")


if __name__ == "__main__":
    main()
