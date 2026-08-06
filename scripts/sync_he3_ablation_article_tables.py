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
HE3_LONG_RAW_ROW_ORDER = ["RAW-GLOFAS"]
HE3_SHORT_RAW_ROW_ORDER = ["RAW-GLOFAS", "RAW-NWS"]
HE3_LONG_HORIZON_DAYS = 28
HE3_NWS_COMMON_HORIZON_DAYS = 8
ARTICLE_TABLE_DIR = Path("tables") / "generated_tex"
ARTICLE_ARTIFACT_DIR = Path("artifacts") / "he3_exdqlm_ablation_authoritative"
TABLE_LABEL = "tab:he3_ablation_crps"
NWS_HORIZON_TABLE_LABEL = "tab:he3_ablation_crps_nws_horizon"
TABLE_NOTE = (
    "Generated from the authoritative HE3 exDQLM multivariate ablation matrix anchored to the "
    "20260601 exAL-M-T1 winner manifest; raw forecast references are recomputed from the "
    "article-side five-cutoff per-time CRPS validation source freeze."
)
DISPLAY_DIGITS = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync completed HE3 ablation tables into the article repos.")
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--article-root", type=Path, default=ROOT / "Evironmetrics---REVISED-DOC-Corrected-2")
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


def mean_crps_for_leads(
    rows: pd.DataFrame,
    *,
    model_key: str,
    model_value: str,
    horizon_days: int,
    source_path: Path,
) -> float:
    selected = rows[
        rows[model_key].astype(str).eq(str(model_value))
        & rows["lead_day"].astype(int).between(1, horizon_days)
    ].copy()
    leads = sorted(selected["lead_day"].astype(int).tolist())
    expected = list(range(1, horizon_days + 1))
    if leads != expected:
        raise RuntimeError(
            f"Expected leads {expected} for {model_key}={model_value} in {source_path}; got {leads}"
        )
    return float(selected.sort_values("lead_day")["crps"].astype(float).mean())


def load_raw_values(
    article_root: Path,
    *,
    horizon_days: int,
    raw_row_order: list[str],
    table_label: str,
) -> tuple[dict[str, dict[str, float]], list[dict[str, str]]]:
    root = article_root / "artifacts" / "five_cutoff_crps_validation_sources"
    out: dict[str, dict[str, float]] = {label: {} for label in raw_row_order}
    source_rows: list[dict[str, str]] = []
    for cutoff in CUTOFF_ORDER:
        per_time_path = root / RUN_SLUG_MAP[cutoff] / "crps_forecast_per_time.csv"
        rows = pd.read_csv(per_time_path)
        for label in raw_row_order:
            model_id = RAW_MODEL_MAP[label]
            value = mean_crps_for_leads(
                rows,
                model_key="model_id",
                model_value=model_id,
                horizon_days=horizon_days,
                source_path=per_time_path,
            )
            out[label][cutoff] = value
            source_rows.append(
                {
                    "table_label": table_label,
                    "row_label": label,
                    "cutoff": cutoff,
                    "horizon_days": str(horizon_days),
                    "source_class": "raw_forecast_product",
                    "source_path": str(per_time_path.relative_to(article_root)),
                    "model_selector": f"model_id={model_id}",
                    "mean_crps": f"{value:.17g}",
                }
            )
    return out, source_rows


def build_value_grid(
    he3: pd.DataFrame,
    raw_values: dict[str, dict[str, float]],
    *,
    horizon_days: int,
    table_label: str,
) -> tuple[dict[str, dict[str, float]], list[dict[str, str]]]:
    grid: dict[str, dict[str, float]] = {}
    source_rows: list[dict[str, str]] = []
    for variant in VARIANT_ORDER:
        subset = he3[he3["variant"].astype(str).eq(variant)]
        if len(subset) != len(CUTOFF_ORDER):
            raise RuntimeError(f"Expected {len(CUTOFF_ORDER)} rows for HE3 variant={variant}, found {len(subset)}")
        grid[variant] = {}
        for _, row in subset.iterrows():
            cutoff = str(row["cutoff"]).zfill(8)
            per_time_path = (
                Path(str(row["resolved_run_dir"]))
                / "post"
                / "outputs"
                / str(row["resolved_run_id"])
                / "tables"
                / "crps_forecast_per_time.csv"
            )
            crps_rows = pd.read_csv(per_time_path)
            value = mean_crps_for_leads(
                crps_rows,
                model_key="model_id",
                model_value=str(row["target_model_id"]),
                horizon_days=horizon_days,
                source_path=per_time_path,
            )
            grid[variant][cutoff] = value
            source_rows.append(
                {
                    "table_label": table_label,
                    "row_label": DISPLAY_LABEL[variant],
                    "cutoff": cutoff,
                    "horizon_days": str(horizon_days),
                    "source_class": "he3_authoritative_ablation",
                    "source_path": str(per_time_path),
                    "model_selector": f"model_id={row['target_model_id']}",
                    "mean_crps": f"{value:.17g}",
                }
            )
    for raw_label, values in raw_values.items():
        grid[raw_label] = values
    return grid, source_rows


def render_model_row(label: str, values: dict[str, float], best_by_cutoff: dict[str, float] | None = None) -> str:
    parts = [label]
    for cutoff in CUTOFF_ORDER:
        value = float(values[cutoff])
        bold = best_by_cutoff is not None and abs(value - float(best_by_cutoff[cutoff])) < 1e-12
        parts.append(fmt_value(value, bold=bold))
    return " & ".join(parts) + r" \\"


def render_body_lines(grid: dict[str, dict[str, float]], *, raw_row_order: list[str]) -> list[str]:
    ablation_best = {
        cutoff: min(float(grid[variant][cutoff]) for variant in VARIANT_ORDER)
        for cutoff in CUTOFF_ORDER
    }
    lines = [
        *(render_model_row(DISPLAY_LABEL[variant], grid[variant], ablation_best) for variant in VARIANT_ORDER),
        r"\addlinespace[2pt]",
        r"\multicolumn{6}{l}{\textit{Raw forecast products (reference only)}} \\",
        *(render_model_row(raw_label, grid[raw_label]) for raw_label in raw_row_order),
    ]
    return lines


def render_main_table(
    body_lines: list[str],
    *,
    table_label: str,
    caption: str,
    note: str | None = None,
) -> str:
    lines = [
        r"\begin{table*}[htbp]",
        r"\centering",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\begin{threeparttable}",
        rf"\caption{{{caption}}}",
        rf"\label{{{table_label}}}",
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} >{\ttfamily}l r r r r r}",
        r"\toprule",
        r"Ablation model & 01/23/2021 & 11/12/2021 & 12/21/2021 & 05/11/2022 & 12/25/2022 \\",
        r"\midrule",
        *body_lines,
        r"\bottomrule",
        r"\end{tabular*}",
    ]
    if note:
        lines.extend(
            [
                r"\begin{tablenotes}",
                rf"\item \textit{{Note:}} {note}",
                r"\end{tablenotes}",
            ]
        )
    lines.extend(
        [
            r"\end{threeparttable}",
            r"\end{table*}",
            "",
        ]
    )
    return "\n".join(lines)


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
    long_body_lines: list[str],
    long_main_table: str,
    nws_body_lines: list[str],
    nws_main_table: str,
    horizon_source_rows: list[dict[str, str]],
) -> None:
    table_dir = article_root / ARTICLE_TABLE_DIR
    table_dir.mkdir(parents=True, exist_ok=True)
    (table_dir / "he3_ablation_crps_body.tex").write_text("\n".join(long_body_lines) + "\n", encoding="utf-8")
    (table_dir / "he3_ablation_crps_main_table.tex").write_text(long_main_table, encoding="utf-8")
    (table_dir / "he3_ablation_crps_nws_horizon_body.tex").write_text(
        "\n".join(nws_body_lines) + "\n",
        encoding="utf-8",
    )
    (table_dir / "he3_ablation_crps_nws_horizon_table.tex").write_text(nws_main_table, encoding="utf-8")
    pd.DataFrame(horizon_source_rows).to_csv(table_dir / "he3_ablation_crps_horizon_summary.csv", index=False)

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
    rows = [row for row in rows if row.get("table_label") not in {TABLE_LABEL, NWS_HORIZON_TABLE_LABEL}]
    for table_label, raw_order in (
        (TABLE_LABEL, HE3_LONG_RAW_ROW_ORDER),
        (NWS_HORIZON_TABLE_LABEL, HE3_SHORT_RAW_ROW_ORDER),
    ):
        for label in [DISPLAY_LABEL[v] for v in VARIANT_ORDER] + raw_order:
            rows.append(
                {
                    "table_label": table_label,
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

    build_metadata_json = table_dir / "build_metadata.json"
    if build_metadata_json.exists():
        build_metadata = json.loads(build_metadata_json.read_text(encoding="utf-8"))
        outputs = build_metadata.setdefault("outputs", {})
        outputs["tab:he3_ablation_crps_body"] = str(ARTICLE_TABLE_DIR / "he3_ablation_crps_body.tex")
        outputs["tab:he3_ablation_crps_block"] = str(ARTICLE_TABLE_DIR / "he3_ablation_crps_main_table.tex")
        outputs["tab:he3_ablation_crps_nws_horizon_body"] = str(
            ARTICLE_TABLE_DIR / "he3_ablation_crps_nws_horizon_body.tex"
        )
        outputs["tab:he3_ablation_crps_nws_horizon_block"] = str(
            ARTICLE_TABLE_DIR / "he3_ablation_crps_nws_horizon_table.tex"
        )
        outputs["tab:he3_ablation_crps_horizon_summary"] = str(
            ARTICLE_TABLE_DIR / "he3_ablation_crps_horizon_summary.csv"
        )
        build_metadata_json.write_text(json.dumps(build_metadata, indent=2) + "\n", encoding="utf-8")

    manifest_json = article_root / "MANUSCRIPT_ASSET_MANIFEST.json"
    if manifest_json.exists():
        payload = json.loads(manifest_json.read_text(encoding="utf-8"))
        payload.setdefault("tables", {})[TABLE_LABEL] = {
            "label": TABLE_LABEL,
            "role": "Selected-model 28-day ablation CRPS table",
            "table_tex_path": str(ARTICLE_TABLE_DIR / "he3_ablation_crps_main_table.tex"),
            "source_class": "he3_authoritative_ablation",
            "sources": {
                "he3_ablation_long_csv": str(ARTICLE_ARTIFACT_DIR / "he3_ablation_long.csv"),
                "he3_ablation_audit_csv": str(ARTICLE_ARTIFACT_DIR / "audit__he3_ablation_audit.csv"),
                "he3_runtime_input_detail_csv": str(
                    ARTICLE_ARTIFACT_DIR / "audit__he3_ablation_runtime_input_detail.csv"
                ),
                "five_run_source_root": "artifacts/five_cutoff_crps_validation_sources",
                "he3_ablation_horizon_summary_csv": str(ARTICLE_TABLE_DIR / "he3_ablation_crps_horizon_summary.csv"),
            },
            "note": (
                "Generated from the authoritative HE3 exDQLM multivariate ablation matrix anchored to "
                "the 20260601 exAL-M-T1 winner manifest. This 28-day table includes RAW-GLOFAS as "
                "the horizon-compatible raw reference and omits RAW-NWS because NWS has eight valid "
                "daily leads for these origins."
            ),
        }
        payload.setdefault("tables", {})[NWS_HORIZON_TABLE_LABEL] = {
            "label": NWS_HORIZON_TABLE_LABEL,
            "role": "Selected-model common eight-day NWS-horizon ablation CRPS table",
            "table_tex_path": str(ARTICLE_TABLE_DIR / "he3_ablation_crps_nws_horizon_table.tex"),
            "source_class": "he3_authoritative_ablation",
            "sources": {
                "he3_ablation_long_csv": str(ARTICLE_ARTIFACT_DIR / "he3_ablation_long.csv"),
                "he3_ablation_audit_csv": str(ARTICLE_ARTIFACT_DIR / "audit__he3_ablation_audit.csv"),
                "he3_runtime_input_detail_csv": str(
                    ARTICLE_ARTIFACT_DIR / "audit__he3_ablation_runtime_input_detail.csv"
                ),
                "five_run_source_root": "artifacts/five_cutoff_crps_validation_sources",
                "he3_ablation_horizon_summary_csv": str(ARTICLE_TABLE_DIR / "he3_ablation_crps_horizon_summary.csv"),
            },
            "note": (
                "Generated from the same authoritative HE3 ablation sources as the 28-day table, but "
                "every row is restricted to leads 1--8 so RAW-NWS, RAW-GLOFAS, the full model, and "
                "the ablation variants are compared on a common horizon."
            ),
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


def write_corrections_outputs(corrections_root: Path, corrections_block: str, nws_corrections_block: str) -> None:
    table_dir = corrections_root / "tables" / "generated_tex"
    table_dir.mkdir(parents=True, exist_ok=True)
    response_table = table_dir / "he3_ablation_crps_response_table.tex"
    response_table.write_text(corrections_block + "\n", encoding="utf-8")
    response_nws_table = table_dir / "he3_ablation_crps_nws_horizon_response_table.tex"
    response_nws_table.write_text(nws_corrections_block + "\n", encoding="utf-8")

    tex_path = corrections_root / "main.tex"
    if not tex_path.exists():
        return
    text = tex_path.read_text(encoding="utf-8")
    input_line = r"\input{tables/generated_tex/he3_ablation_crps_response_table.tex}"
    nws_input_line = r"\input{tables/generated_tex/he3_ablation_crps_nws_horizon_response_table.tex}"
    if input_line in text:
        if nws_input_line not in text:
            text = text.replace(input_line, input_line + "\n\n" + nws_input_line, 1)
            tex_path.write_text(text, encoding="utf-8")
        return
    pattern = re.compile(
        r"\\begin\{center\}\s*\\scriptsize\s*\\setlength\{\\tabcolsep\}\{4pt\}\s*"
        r"\\begin\{tabular\}\{>\{\\ttfamily\}l c c c c c\}.*?"
        r"\\end\{tabular\}\s*\\end\{center\}",
        re.DOTALL,
    )
    input_block = input_line + "\n\n" + nws_input_line
    new_text, n = pattern.subn(lambda _match: input_block, text, count=1)
    if n != 1:
        raise RuntimeError(f"Could not replace HE3 ablation table in {tex_path}")
    tex_path.write_text(new_text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    he3, report_dir, _metadata = load_he3_long(args.matrix_dir.resolve())
    long_raw_values, long_raw_source_rows = load_raw_values(
        args.article_root.resolve(),
        horizon_days=HE3_LONG_HORIZON_DAYS,
        raw_row_order=HE3_LONG_RAW_ROW_ORDER,
        table_label=TABLE_LABEL,
    )
    long_grid, long_source_rows = build_value_grid(
        he3,
        long_raw_values,
        horizon_days=HE3_LONG_HORIZON_DAYS,
        table_label=TABLE_LABEL,
    )
    long_body_lines = render_body_lines(long_grid, raw_row_order=HE3_LONG_RAW_ROW_ORDER)
    long_main_table = render_main_table(
        long_body_lines,
        table_label=TABLE_LABEL,
        caption=(
            r"Targeted 28-day ablation of the selected \texttt{exAL-M-T1} specification. "
            r"Entries are mean forecast-window CRPS; lower values are better, and bold marks "
            r"the best ablation-row value within each cutoff."
        ),
        note=r"The \texttt{noH3} row removes the retained noninteger seasonal harmonic with frequency \(1/6.8068493\).",
    )

    nws_raw_values, nws_raw_source_rows = load_raw_values(
        args.article_root.resolve(),
        horizon_days=HE3_NWS_COMMON_HORIZON_DAYS,
        raw_row_order=HE3_SHORT_RAW_ROW_ORDER,
        table_label=NWS_HORIZON_TABLE_LABEL,
    )
    nws_grid, nws_source_rows = build_value_grid(
        he3,
        nws_raw_values,
        horizon_days=HE3_NWS_COMMON_HORIZON_DAYS,
        table_label=NWS_HORIZON_TABLE_LABEL,
    )
    nws_body_lines = render_body_lines(nws_grid, raw_row_order=HE3_SHORT_RAW_ROW_ORDER)
    nws_main_table = render_main_table(
        nws_body_lines,
        table_label=NWS_HORIZON_TABLE_LABEL,
        caption=(
            r"Targeted ablation CRPS over the common eight-day NWS forecast horizon. "
            r"Lower values are better, and bold marks the best ablation-row value within each cutoff."
        ),
        note=r"This table restricts every row to forecast leads 1--8, the common daily horizon available for the NWS comparison.",
    )
    horizon_source_rows = long_raw_source_rows + long_source_rows + nws_raw_source_rows + nws_source_rows
    corrections_block = render_corrections_block(long_body_lines)
    nws_corrections_block = render_corrections_block(nws_body_lines)
    write_article_outputs(
        args.article_root.resolve(),
        report_dir,
        long_body_lines,
        long_main_table,
        nws_body_lines,
        nws_main_table,
        horizon_source_rows,
    )
    write_corrections_outputs(args.corrections_root.resolve(), corrections_block, nws_corrections_block)
    print(args.article_root.resolve() / ARTICLE_TABLE_DIR / "he3_ablation_crps_main_table.tex")
    print(args.article_root.resolve() / ARTICLE_TABLE_DIR / "he3_ablation_crps_nws_horizon_table.tex")
    print(args.corrections_root.resolve() / "tables" / "generated_tex" / "he3_ablation_crps_response_table.tex")
    print(args.corrections_root.resolve() / "tables" / "generated_tex" / "he3_ablation_crps_nws_horizon_response_table.tex")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
