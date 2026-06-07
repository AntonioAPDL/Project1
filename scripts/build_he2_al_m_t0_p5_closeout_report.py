#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = (
    ROOT.parent
    / "project1_ucsc_phd_runtime"
    / "multimodel_v8_he2_dqlm_multivar_al_drop_p5_production_20260606"
)
DEFAULT_REPORT_DIR = ROOT / "reports" / "he2_al_m_t0_p5_production_closeout_20260606"
EXPECTED_CUTOFFS = ("20210123", "20211112", "20211221", "20220511", "20221225")
TARGET_MODEL_ID = "dqlm_multivar_al_synth_drop"
BASELINE_GLOFAS = "glofas_ensemble"
BASELINE_NWS = "nws_nwm_ensemble"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_id(cutoff: str) -> str:
    return f"multimodel_{cutoff}_v8_he2pubgdpc1r1_dqlm_multivar_al_drop"


def count_rdata(run_root: Path) -> tuple[int, int]:
    total = 0
    count = 0
    for pattern in ("*.RData", "*.rdata", "*.rda"):
        for path in run_root.rglob(pattern):
            if path.is_file():
                count += 1
                total += path.stat().st_size
    return count, total


def dir_size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def terminal_rows(run_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for q_dir in sorted((run_root / "fit").glob("q=*")):
        q = q_dir.name.split("=", 1)[1]
        path = q_dir / "outputs" / "multivar_terminal_state_health.csv"
        if not path.exists():
            rows.append({"q": q, "terminal_exists": "false"})
            continue
        csv_rows = read_csv(path)
        if not csv_rows:
            rows.append({"q": q, "terminal_exists": "true"})
            continue
        if {"metric", "value"}.issubset(csv_rows[0].keys()):
            row = {str(item.get("metric", "")): str(item.get("value", "")) for item in csv_rows}
            row["non_ok_count"] = str(sum(1 for item in csv_rows if str(item.get("status", "")).lower() != "ok"))
        else:
            row = dict(csv_rows[0])
        row["q"] = q
        row["terminal_exists"] = "true"
        rows.append(row)
    return rows


def load_crps_rows(path: Path, cutoff: str) -> list[dict[str, str]]:
    rows = read_csv(path)
    for row in rows:
        row["cutoff_compact"] = cutoff
    return rows


def crps_lookup(rows: list[dict[str, str]], model_id: str) -> str:
    for row in rows:
        if row.get("model_id") == model_id:
            return row.get("mean_crps", "")
    return ""


def fig_manifest_count(path: Path) -> int:
    if not path.exists():
        return 0
    return max(len(read_csv(path)), 0)


def validate_and_collect(artifact_root: Path) -> tuple[list[dict[str, object]], list[dict[str, str]], list[str]]:
    matrix_path = artifact_root / "control" / "publication_relaunch_matrix" / "matrix_status.csv"
    if not matrix_path.exists():
        raise FileNotFoundError(matrix_path)

    matrix_rows = read_csv(matrix_path)
    matrix_by_cutoff = {row.get("cutoff", ""): row for row in matrix_rows}

    summary_rows: list[dict[str, object]] = []
    all_crps_rows: list[dict[str, str]] = []
    failures: list[str] = []

    for cutoff in EXPECTED_CUTOFFS:
        rid = run_id(cutoff)
        run_root = artifact_root / "runs" / rid
        out_dir = run_root / "post" / "outputs" / rid
        crps_path = out_dir / "tables" / "crps_forecast_summary.csv"
        fig_manifest = out_dir / "publication_figure_manifest.csv"
        run_manifest = run_root / "run_manifest.yaml"
        row = matrix_by_cutoff.get(cutoff, {})
        terminals = terminal_rows(run_root)
        rdata_count, rdata_bytes = count_rdata(run_root)
        run_bytes = dir_size_bytes(run_root)

        if row.get("phase") != "report" or row.get("status") != "pass":
            failures.append(f"{cutoff}: matrix not report/pass")
        if not crps_path.exists():
            failures.append(f"{cutoff}: missing CRPS summary")
            crps_rows: list[dict[str, str]] = []
        else:
            crps_rows = load_crps_rows(crps_path, cutoff)
            all_crps_rows.extend(crps_rows)
        if not fig_manifest.exists():
            failures.append(f"{cutoff}: missing publication figure manifest")
        if not run_manifest.exists():
            failures.append(f"{cutoff}: missing run manifest")
        if len([r for r in terminals if r.get("terminal_exists") == "true"]) != 7:
            failures.append(f"{cutoff}: not all seven terminal health files exist")
        if rdata_count != 0:
            failures.append(f"{cutoff}: retained RData count is {rdata_count}")

        state_values = []
        terminal_failures = 0
        for term in terminals:
            value = term.get("state_norm_sq_per_T", "")
            try:
                if value != "":
                    state_values.append(float(value))
            except ValueError:
                pass
            try:
                terminal_failures += int(float(term.get("violation_n", term.get("non_ok_count", "0")) or "0"))
            except ValueError:
                terminal_failures += 0

        q65_state = ""
        for term in terminals:
            if term.get("q") == "65":
                q65_state = term.get("state_norm_sq_per_T", "")

        summary_rows.append(
            {
                "cutoff": cutoff,
                "run_id": rid,
                "matrix_phase": row.get("phase", ""),
                "matrix_status": row.get("status", ""),
                "finished_at": row.get("finished_at", ""),
                "terminal_health_files": len([r for r in terminals if r.get("terminal_exists") == "true"]),
                "terminal_violation_n": terminal_failures,
                "max_state_norm_sq_per_T": f"{max(state_values):.12g}" if state_values else "",
                "q65_state_norm_sq_per_T": q65_state,
                "crps_summary_exists": str(crps_path.exists()).lower(),
                "publication_figure_manifest_exists": str(fig_manifest.exists()).lower(),
                "publication_figure_manifest_rows": fig_manifest_count(fig_manifest),
                "run_manifest_exists": str(run_manifest.exists()).lower(),
                "rdata_count_after_post": rdata_count,
                "rdata_gb_after_post": f"{rdata_bytes / 1024**3:.6f}",
                "run_size_mb": f"{run_bytes / 1024**2:.3f}",
                "synth_mean_crps": crps_lookup(crps_rows, TARGET_MODEL_ID),
                "glofas_mean_crps": crps_lookup(crps_rows, BASELINE_GLOFAS),
                "nws_mean_crps": crps_lookup(crps_rows, BASELINE_NWS),
            }
        )

    return summary_rows, all_crps_rows, failures


def markdown_table(rows: list[list[object]], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def build_markdown(
    artifact_root: Path,
    report_dir: Path,
    summary_rows: list[dict[str, object]],
    all_crps_rows: list[dict[str, str]],
    failures: list[str],
) -> str:
    status = "PASS" if not failures else "FAIL"
    overview = [
        [
            r["cutoff"],
            r["matrix_status"],
            r["terminal_health_files"],
            r["max_state_norm_sq_per_T"],
            r["synth_mean_crps"],
            r["glofas_mean_crps"],
            r["nws_mean_crps"],
            r["publication_figure_manifest_rows"],
            r["rdata_count_after_post"],
        ]
        for r in summary_rows
    ]
    crps_rows = [
        [
            row.get("cutoff_compact", ""),
            row.get("model_id", ""),
            row.get("mean_crps", ""),
            row.get("n_valid", ""),
            row.get("score_scale", ""),
        ]
        for row in all_crps_rows
    ]
    lines = [
        "# HE2 AL-M-T0 P5 Production Closeout",
        "",
        f"- status: `{status}`",
        f"- generated_at_utc: `{now_utc()}`",
        f"- git_head: `{git_head()}`",
        f"- artifact_root: `{artifact_root}`",
        f"- report_dir: `{report_dir}`",
        "",
        "## Cutoff Summary",
        "",
        markdown_table(
            overview,
            [
                "Cutoff",
                "Status",
                "Terminal q",
                "Max State/T",
                "Synth CRPS",
                "GLOFAS CRPS",
                "NWS CRPS",
                "Fig Rows",
                "RData",
            ],
        ),
        "",
        "## CRPS Rows",
        "",
        markdown_table(crps_rows, ["Cutoff", "Model", "Mean CRPS", "n_valid", "Scale"]),
        "",
        "## Evidence Files",
        "",
        f"- closeout summary CSV: `{report_dir / 'p5_closeout_summary.csv'}`",
        f"- CRPS aggregate CSV: `{report_dir / 'p5_crps_forecast_summary_all_cutoffs.csv'}`",
        f"- validation status: `{report_dir / 'p5_closeout_validation_status.txt'}`",
        f"- matrix status: `{artifact_root / 'control' / 'publication_relaunch_matrix' / 'matrix_status.csv'}`",
        "",
    ]
    if failures:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {item}" for item in failures)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build closeout report for HE2 AL-M-T0 P5 production.")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--allow-failures", action="store_true")
    args = parser.parse_args()

    summary_rows, all_crps_rows, failures = validate_and_collect(args.artifact_root)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.report_dir / "p5_closeout_summary.csv", summary_rows)
    write_csv(
        args.report_dir / "p5_crps_forecast_summary_all_cutoffs.csv",
        all_crps_rows,
        fields=list(all_crps_rows[0].keys()) if all_crps_rows else [],
    )
    status_text = "PASS\n" if not failures else "FAIL\n" + "\n".join(failures) + "\n"
    write_text(args.report_dir / "p5_closeout_validation_status.txt", status_text)
    write_text(
        args.report_dir / "P5_PRODUCTION_CLOSEOUT.md",
        build_markdown(args.artifact_root, args.report_dir, summary_rows, all_crps_rows, failures),
    )
    print(f"status={'PASS' if not failures else 'FAIL'}")
    print(f"summary={args.report_dir / 'p5_closeout_summary.csv'}")
    print(f"crps={args.report_dir / 'p5_crps_forecast_summary_all_cutoffs.csv'}")
    print(f"markdown={args.report_dir / 'P5_PRODUCTION_CLOSEOUT.md'}")
    if failures and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
