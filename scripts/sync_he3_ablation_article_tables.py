#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from multimodel_v8_lib import ROOT, load_yaml


CUTOFF_ORDER = ["20210123", "20211112", "20211221", "20220511", "20221225"]
CUTOFF_LABELS = {
    "20210123": "01/23/2021",
    "20211112": "11/12/2021",
    "20211221": "12/21/2021",
    "20220511": "05/11/2022",
    "20221225": "12/25/2022",
}
RUN_SLUG_MAP = {
    "20210123": "20210123_exal_m_t1",
    "20211112": "20211112_exal_m_t1",
    "20211221": "20211221_exal_m_t1",
    "20220511": "20220511_exal_m_t1",
    "20221225": "20221225_exal_m_t1",
}
VARIANT_ORDER = ["full", "noTrend", "noTF", "noH1", "noH2", "noH3"]
DISPLAY_LABEL = {
    "full": "exAL-M-T1 (full)",
    "noTrend": "exAL-M-T1-noTrend",
    "noTF": "exAL-M-noTF",
    "noH1": "exAL-M-T1-noH1",
    "noH2": "exAL-M-T1-noH2",
    "noH3": "exAL-M-T1-noH3",
}
RAW_MODEL_MAP = {
    "RAW-GLOFAS": "glofas_ensemble",
    "RAW-NWS": "nws_nwm_ensemble",
}
ARTICLE_TABLE_DIR = Path("tables") / "generated_tex"
ARTICLE_ARTIFACT_DIR = Path("artifacts") / "he3_exdqlm_ablation_authoritative"
TABLE_LABEL = "tab:he3_ablation_crps"
TABLE_NOTE = (
    "Generated from the authoritative HE3 exDQLM multivariate ablation matrix anchored to the "
    "20260601 exAL-M-T1 winner manifest; raw forecast references are copied from the article-side "
    "five-cutoff CRPS validation source freeze."
)
DISPLAY_DIGITS = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync completed HE3 ablation tables into the article repos.")
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--article-root", type=Path, default=ROOT / "Evironmetrics---REVISED-DOC-Corrected")
    parser.add_argument("--corrections-root", type=Path, default=ROOT.parent / "Corrections---Project-1")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fmt_value(value: float, bold: bool = False) -> str:
    rendered = f"{float(value):.{DISPLAY_DIGITS}f}"
    return rf"\textbf{{{rendered}}}" if bold else rendered


def load_he3_long(matrix_dir: Path) -> tuple[pd.DataFrame, Path, dict[str, Any]]:
    metadata = load_yaml(matrix_dir / "matrix_metadata.yaml")
    artifact_root = Path(str(metadata["artifact_root"])).resolve()
    report_dir = artifact_root / "reports" / "he3_exdqlm_ablation"
    long_path = report_dir / "he3_ablation_long.csv"
    if not long_path.exists():
        raise FileNotFoundError(f"Missing completed HE3 summary: {long_path}")
    df = pd.read_csv(long_path)
    if not (df["status"].astype(str) == "pass").all():
        bad = df[df["status"].astype(str) != "pass"][["cutoff", "variant", "status"]]
        raise RuntimeError(f"Cannot sync incomplete HE3 ablation table: {bad.to_dict(orient='records')}")
    return df, report_dir, metadata


def load_raw_values(article_root: Path) -> dict[str, dict[str, float]]:
    root = article_root / "artifacts" / "five_cutoff_crps_validation_sources"
    out: dict[str, dict[str, float]] = {label: {} for label in RAW_MODEL_MAP}
    for cutoff in CUTOFF_ORDER:
        rows = read_csv(root / RUN_SLUG_MAP[cutoff] / "crps_forecast_summary.csv")
        by_model = {row["model_id"]: row for row in rows}
        for label, model_id in RAW_MODEL_MAP.items():
            out[label][cutoff] = float(by_model[model_id]["mean_crps"])
    return out


def build_value_grid(he3: pd.DataFrame, raw_values: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    grid: dict[str, dict[str, float]] = {}
    for variant in VARIANT_ORDER:
        subset = he3[he3["variant"].astype(str).eq(variant)]
        if len(subset) != len(CUTOFF_ORDER):
            raise RuntimeError(f"Expected {len(CUTOFF_ORDER)} rows for HE3 variant={variant}, found {len(subset)}")
        grid[variant] = {
            str(row["cutoff"]).zfill(8): float(row["mean_crps"])
            for _, row in subset.iterrows()
        }
    for raw_label, values in raw_values.items():
        grid[raw_label] = values
    return grid


def render_model_row(label: str, values: dict[str, float], best_by_cutoff: dict[str, float] | None = None) -> str:
    parts = [label]
    for cutoff in CUTOFF_ORDER:
        value = float(values[cutoff])
        bold = best_by_cutoff is not None and abs(value - float(best_by_cutoff[cutoff])) < 1e-12
        parts.append(fmt_value(value, bold=bold))
    return " & ".join(parts) + r" \\"


def render_body_lines(grid: dict[str, dict[str, float]]) -> list[str]:
    ablation_best = {
        cutoff: min(float(grid[variant][cutoff]) for variant in VARIANT_ORDER)
        for cutoff in CUTOFF_ORDER
    }
    lines = [
        *(render_model_row(DISPLAY_LABEL[variant], grid[variant], ablation_best) for variant in VARIANT_ORDER),
        r"\addlinespace[2pt]",
        r"\multicolumn{6}{l}{\textit{Raw forecast products (reference only)}} \\",
        *(render_model_row(raw_label, grid[raw_label]) for raw_label in RAW_MODEL_MAP),
    ]
    return lines


def render_main_table(body_lines: list[str]) -> str:
    return "\n".join(
        [
            r"\begin{table*}[htbp]",
            r"\centering",
            r"\renewcommand{\arraystretch}{1.08}",
            r"\begin{threeparttable}",
            r"\caption{Targeted ablation of the selected \texttt{exAL-M-T1} specification. Entries are mean forecast-window CRPS; lower values are better, and bold marks the best ablation-row value within each cutoff.}",
            rf"\label{{{TABLE_LABEL}}}",
            r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} >{\ttfamily}l r r r r r}",
            r"\toprule",
            r"Ablation model & 01/23/2021 & 11/12/2021 & 12/21/2021 & 05/11/2022 & 12/25/2022 \\",
            r"\midrule",
            *body_lines,
            r"\bottomrule",
            r"\end{tabular*}",
            r"\begin{tablenotes}",
            r"\item \textit{Note:} Each ablation inherits the cutoff-specific winning \texttt{exAL-M-T1} input bundle, preprocessing, likelihood, and selected winner hyperparameters, changing only the named structural component. \texttt{noH3} removes the third retained seasonal harmonic pair, where the third harmonic is the noninteger frequency \(1/6.8068493\).",
            r"\end{tablenotes}",
            r"\end{threeparttable}",
            r"\end{table*}",
            "",
        ]
    )


def render_corrections_block(body_lines: list[str]) -> str:
    return "\n".join(
        [
            r"\begin{center}",
            r"\scriptsize",
            r"\setlength{\tabcolsep}{4pt}",
            r"\begin{tabular}{>{\ttfamily}l c c c c c}",
            r"\toprule",
            r"Ablation model & 01/23/2021 & 11/12/2021 & 12/21/2021 & 05/11/2022 & 12/25/2022 \\",
            r"\midrule",
            *body_lines,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{center}",
        ]
    )


def write_article_outputs(
    article_root: Path,
    report_dir: Path,
    grid: dict[str, dict[str, float]],
    body_lines: list[str],
    main_table: str,
) -> None:
    table_dir = article_root / ARTICLE_TABLE_DIR
    table_dir.mkdir(parents=True, exist_ok=True)
    (table_dir / "he3_ablation_crps_body.tex").write_text("\n".join(body_lines) + "\n", encoding="utf-8")
    (table_dir / "he3_ablation_crps_main_table.tex").write_text(main_table, encoding="utf-8")

    artifact_dir = article_root / ARTICLE_ARTIFACT_DIR
    artifact_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    for name in [
        "he3_ablation_long.csv",
        "he3_ablation_wide.csv",
        "he3_ablation_summary.md",
        "he3_table_rows.tex",
        "audit/he3_ablation_audit.csv",
        "audit/he3_ablation_lead_buckets.csv",
        "audit/he3_ablation_audit.md",
        "audit/he3_ablation_runtime_input_detail.csv",
        "audit/he3_ablation_runtime_input_detail.md",
    ]:
        src = report_dir / name
        if not src.exists():
            continue
        dst = artifact_dir / name.replace("/", "__")
        shutil.copy2(src, dst)
        copied.append({"source": str(src), "artifact": str(dst.relative_to(article_root))})
    (artifact_dir / "README.md").write_text(
        "# HE3 exDQLM Ablation Authoritative Artifact\n\n"
        "This bundle is copied from the workflow-side authoritative HE3 ablation campaign after all rows pass.\n",
        encoding="utf-8",
    )
    pd.DataFrame(copied).to_csv(artifact_dir / "manifest.csv", index=False)

    manifest_csv = table_dir / "manifest.csv"
    rows = read_csv(manifest_csv) if manifest_csv.exists() else []
    rows = [row for row in rows if row.get("table_label") != TABLE_LABEL]
    for label in [DISPLAY_LABEL[v] for v in VARIANT_ORDER] + list(RAW_MODEL_MAP):
        rows.append(
            {
                "table_label": TABLE_LABEL,
                "row_label": label,
                "source_class": "he3_authoritative_ablation",
                "source_note": TABLE_NOTE,
            }
        )
    with manifest_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["table_label", "row_label", "source_class", "source_note"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    manifest_json = article_root / "MANUSCRIPT_ASSET_MANIFEST.json"
    if manifest_json.exists():
        payload = json.loads(manifest_json.read_text(encoding="utf-8"))
        payload.setdefault("tables", {})[TABLE_LABEL] = {
            "label": TABLE_LABEL,
            "role": "Selected-model ablation CRPS table",
            "table_tex_path": str(ARTICLE_TABLE_DIR / "he3_ablation_crps_main_table.tex"),
            "source_class": "he3_authoritative_ablation",
            "sources": {
                "he3_ablation_long_csv": str(ARTICLE_ARTIFACT_DIR / "he3_ablation_long.csv"),
                "he3_ablation_audit_csv": str(ARTICLE_ARTIFACT_DIR / "audit__he3_ablation_audit.csv"),
                "he3_runtime_input_detail_csv": str(
                    ARTICLE_ARTIFACT_DIR / "audit__he3_ablation_runtime_input_detail.csv"
                ),
                "five_run_source_root": "artifacts/five_cutoff_crps_validation_sources",
            },
            "note": TABLE_NOTE,
        }
        manifest_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    wiley = article_root / "wileyNJD-APA.tex"
    if wiley.exists():
        text = wiley.read_text(encoding="utf-8")
        input_line = r"\input{tables/generated_tex/he3_ablation_crps_main_table.tex}"
        if input_line not in text:
            marker = r"\section{INTERPRETATION OF THE SELECTED SPECIFICATION}"
            section = "\n".join(
                [
                    "",
                    r"\subsection{Ablation of the Selected Specification}",
                    r"\label{subsec:he3ablation}",
                    "",
                    r"To isolate which structural components contribute most to the selected multivariate specification, we rerun the cutoff-specific \texttt{exAL-M-T1} winners after removing one component at a time while preserving the same rolling-origin cutoffs, input bundles, preprocessing, likelihood, and winner hyperparameters.",
                    "",
                    input_line,
                    "",
                ]
            )
            if marker not in text:
                raise RuntimeError(f"Could not insert HE3 ablation subsection; missing marker {marker}")
            text = text.replace(marker, section + marker, 1)
            wiley.write_text(text, encoding="utf-8")


def write_corrections_outputs(corrections_root: Path, corrections_block: str) -> None:
    table_dir = corrections_root / "tables" / "generated_tex"
    table_dir.mkdir(parents=True, exist_ok=True)
    response_table = table_dir / "he3_ablation_crps_response_table.tex"
    response_table.write_text(corrections_block + "\n", encoding="utf-8")

    tex_path = corrections_root / "main.tex"
    if not tex_path.exists():
        return
    text = tex_path.read_text(encoding="utf-8")
    input_line = r"\input{tables/generated_tex/he3_ablation_crps_response_table.tex}"
    if input_line in text:
        return
    pattern = re.compile(
        r"\\begin\{center\}\s*\\scriptsize\s*\\setlength\{\\tabcolsep\}\{4pt\}\s*"
        r"\\begin\{tabular\}\{>\{\\ttfamily\}l c c c c c\}.*?"
        r"\\end\{tabular\}\s*\\end\{center\}",
        re.DOTALL,
    )
    new_text, n = pattern.subn(lambda _match: corrections_block, text, count=1)
    if n != 1:
        raise RuntimeError(f"Could not replace HE3 ablation table in {tex_path}")
    tex_path.write_text(new_text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    he3, report_dir, _metadata = load_he3_long(args.matrix_dir.resolve())
    raw_values = load_raw_values(args.article_root.resolve())
    grid = build_value_grid(he3, raw_values)
    body_lines = render_body_lines(grid)
    main_table = render_main_table(body_lines)
    corrections_block = render_corrections_block(body_lines)
    write_article_outputs(args.article_root.resolve(), report_dir, grid, body_lines, main_table)
    write_corrections_outputs(args.corrections_root.resolve(), corrections_block)
    print(args.article_root.resolve() / ARTICLE_TABLE_DIR / "he3_ablation_crps_main_table.tex")
    print(args.corrections_root.resolve() / "tables" / "generated_tex" / "he3_ablation_crps_response_table.tex")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
