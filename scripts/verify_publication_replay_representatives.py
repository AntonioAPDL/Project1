#!/usr/bin/env python3
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_CSV = REPO_ROOT / "reports" / "publication_replay" / "publication_replay_matrix.csv"
OUT_DIR = REPO_ROOT / "reports" / "publication_replay"
OUT_CSV = OUT_DIR / "representative_replay_verification.csv"
OUT_MD = OUT_DIR / "representative_replay_verification.md"
R440_RUN_ROOT = REPO_ROOT / "repro" / "runs" / "paper_exalm_t1_r440_q20_keep_20221225_20260506"
CRPS_TOLERANCE = Decimal("1e-12")


def load_matrix() -> list[dict[str, str]]:
    with MATRIX_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if row["representative_lineage_row"] == "True"]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def truthy(value: str) -> bool:
    return value == "True"


def model_id_for_row(row: dict[str, str]) -> str:
    family = row["family"]
    mapping = {
        "ndlm_main_keep": "ndlm_main_synth_keep",
        "ndlm_main_drop": "ndlm_main_synth_drop",
        "ndlm_univar_keep": "ndlm_univar_synth_keep",
        "dqlm_univar_al": "dqlm_univar_al_synth",
        "exdqlm_univar": "exdqlm_univar_synth",
        "dqlm_multivar_al_keep": "dqlm_multivar_al_synth_keep",
        "dqlm_multivar_al_drop": "dqlm_multivar_al_synth_drop",
        "exdqlm_multivar_keep": "exdqlm_multivar_synth_keep",
        "exdqlm_multivar_drop": "exdqlm_multivar_synth_drop",
    }
    return mapping[family]


def close_decimal_equal(left: str, right: str, tolerance: Decimal = CRPS_TOLERANCE) -> bool:
    return abs(Decimal(left) - Decimal(right)) <= tolerance


def check_source_provenance(row: dict[str, str]) -> tuple[bool, str]:
    path = Path(row["source_provenance_path"])
    provenance_rows = read_csv_rows(path)
    expected_model_id = model_id_for_row(row)
    matches = [r for r in provenance_rows if r.get("model_id") == expected_model_id]
    if not matches:
        return False, f"missing model_id={expected_model_id}"
    if row["manuscript_label"] == "exAL-M-T1" and row["cutoff"] == "20221225":
        selected = matches[0].get("selected_source_run", "")
        if selected != row["replaced_source_run_id"]:
            return False, f"selected_source_run={selected} expected={row['replaced_source_run_id']}"
    return True, expected_model_id


def check_score_source(row: dict[str, str]) -> tuple[bool, str]:
    score_rows = read_csv_rows(Path(row["score_source"]))
    expected_model_id = model_id_for_row(row)
    matches = [r for r in score_rows if r.get("model_id") == expected_model_id]
    if not matches:
        return False, f"missing model_id={expected_model_id}"
    actual = matches[0]["mean_crps"]
    expected = row["crps_exact"]
    if not close_decimal_equal(actual, expected):
        return False, f"mean_crps={actual} expected={expected}"
    return True, actual


def check_required_artifacts(row: dict[str, str]) -> tuple[bool, str]:
    required_flags = [
        "artifact_run_manifest_exists",
        "artifact_report_summary_exists",
        "artifact_inputs_shared_exists",
        "compare_bundle_exists",
        "source_provenance_exists",
        "score_source_exists",
        "crps_forecast_per_time_exists",
        "posterior_table_exports_manifest_exists",
        "posterior_table_exports_readme_exists",
    ]
    missing = [flag for flag in required_flags if not truthy(row[flag])]
    if missing:
        return False, ",".join(missing)
    return True, "required artifacts present"


def check_r440_replay() -> tuple[bool, str]:
    manifest = R440_RUN_ROOT / "run_manifest.yaml"
    if not manifest.exists():
        return False, "missing run_manifest.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    fit_status = data["stages"]["fit"]["status"]
    shared_status = data["stages"]["data_prep_shared"]["status"]
    env_files = [
        R440_RUN_ROOT / "env" / "R_sessionInfo.txt",
        R440_RUN_ROOT / "env" / "R_installed_packages.csv",
        R440_RUN_ROOT / "env" / "renviron_snapshot.txt",
        R440_RUN_ROOT / "env" / "threads_snapshot.txt",
    ]
    missing = [str(path.relative_to(R440_RUN_ROOT)) for path in env_files if not path.exists()]
    if fit_status != "pass" or shared_status != "pass":
        return False, f"fit={fit_status} shared={shared_status}"
    if missing:
        return False, f"missing env files: {', '.join(missing)}"
    return True, "authoritative R 4.4 q=0.20 keep replay present"


def write_csv(rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_md(rows: Iterable[dict[str, str]]) -> None:
    rows = list(rows)
    lines = [
        "# Representative Replay Verification",
        "",
        "This report checks one representative publication row per replay lineage.",
        "",
        "| Cutoff | Label | Campaign lineage | Score match | Source provenance | Required artifacts | Exact-row R440 replay | Overall |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['cutoff_display']} | `{row['manuscript_label']}` | `{row['campaign_lineage']}` | "
            f"{row['score_match']} | {row['source_provenance_match']} | {row['required_artifacts_ok']} | "
            f"{row['r440_exact_replay_ok']} | {row['overall_status']} |"
        )
    lines.extend(
        [
            "",
            f"CSV: `{OUT_CSV}`",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = load_matrix()
    out_rows: list[dict[str, str]] = []
    r440_ok, r440_note = check_r440_replay()

    for row in rows:
        score_ok, score_note = check_score_source(row)
        prov_ok, prov_note = check_source_provenance(row)
        req_ok, req_note = check_required_artifacts(row)

        exact_row = row["cutoff"] == "20221225" and row["manuscript_label"] == "exAL-M-T1"
        overall = score_ok and prov_ok and req_ok and (r440_ok if exact_row else True)

        out_rows.append(
            {
                "cutoff": row["cutoff"],
                "cutoff_display": row["cutoff_display"],
                "manuscript_label": row["manuscript_label"],
                "campaign_lineage": row["campaign_lineage"],
                "run_id": row["run_id"],
                "score_match": "PASS" if score_ok else "FAIL",
                "score_note": score_note,
                "source_provenance_match": "PASS" if prov_ok else "FAIL",
                "source_provenance_note": prov_note,
                "required_artifacts_ok": "PASS" if req_ok else "FAIL",
                "required_artifacts_note": req_note,
                "r440_exact_replay_ok": ("PASS" if r440_ok else "FAIL") if exact_row else "N/A",
                "r440_exact_replay_note": r440_note if exact_row else "",
                "overall_status": "PASS" if overall else "FAIL",
            }
        )

    write_csv(out_rows)
    write_md(out_rows)
    print(OUT_CSV)
    print(OUT_MD)


if __name__ == "__main__":
    main()
