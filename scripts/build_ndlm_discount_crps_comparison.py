#!/usr/bin/env python3
"""Build a cutoff-by-cutoff NDLM discount-spec CRPS comparison.

This script compares the distinct NDLM discount regimes we have actually run
historically against the current HE-table NDLM rows from the postfix rerun.
It also benchmarks the current postfix NDLM rows against the current overall
HE2 winner at each cutoff as rendered in Corrections---Project-1/main.tex.

Important scope note:
    The historical baseline TT regime and the current postfix regime differ in
    more than discount factors alone (input contract and forecasting protocol
    also changed). This report therefore provides the empirical historical CRPS
    comparison we have available now, but it is not a pure controlled
    discount-only sweep.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import yaml


PROJECT_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
RUNTIME_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")
CORRECTIONS_TEX = Path("/data/muscat_data/jaguir26/Corrections---Project-1/main.tex")
OUTPUT_DIR = PROJECT_ROOT / "reports" / "ndlm_discount_comparison"

MODEL_VARIANT_TO_HE_LABEL = {
    "ndlm_univar_keep": "N-U-T1",
    "ndlm_main_drop": "N-M-T0",
    "ndlm_main_keep": "N-M-T1",
}

MODEL_VARIANT_TO_CONFIG_KEY = {
    "ndlm_univar_keep": "ndlm_univar",
    "ndlm_main_drop": "ndlm_main",
    "ndlm_main_keep": "ndlm_main",
}

CUTOFF_ORDER = [
    "2021-01-23",
    "2021-11-12",
    "2021-12-21",
    "2022-05-11",
    "2022-12-25",
]

CAMPAIGNS = {
    "baseline_20260402": {
        "root": RUNTIME_ROOT / "multimodel_v8_20260402",
        "report_glob": "multimodel_*_v8_epsTT_compare/crps_forecast_summary_all_models.csv",
        "status": "historical_baseline",
        "use_for_discount_comparison": True,
        "display_name": "Baseline TT regime",
    },
    "ndlm_tune_20260411": {
        "root": RUNTIME_ROOT / "multimodel_v8_ndlm_20260411",
        "report_glob": "**/crps_forecast_summary_all_models.csv",
        "status": "historical_tuned_pre_postfix",
        "use_for_discount_comparison": False,
        "display_name": "Tuned regime (pre-postfix)",
    },
    "featurecov_rerun_20260420": {
        "root": RUNTIME_ROOT / "multimodel_v8_ndlm_featurecov_rerun_20260420",
        "report_glob": "**/crps_forecast_summary_all_models.csv",
        "status": "featurecov_pre_postfix",
        "use_for_discount_comparison": False,
        "display_name": "Featurecov rerun (pre-postfix)",
    },
    "postfix_20260421": {
        "root": RUNTIME_ROOT / "multimodel_v8_ndlm_featurecov_rerun_postfix_20260421",
        "report_glob": "**/crps_forecast_summary_all_models.csv",
        "status": "current_he_row",
        "use_for_discount_comparison": True,
        "display_name": "Current postfix HE row",
    },
}


@dataclass(frozen=True)
class DiscountSpec:
    label: str
    df_t: float
    df_s1: float
    df_s2: float
    df_s67: float
    df_discrep: Optional[float]
    lambd: float
    df_trans: float
    df_covs: float

    def signature(self) -> str:
        discrep = "na" if self.df_discrep is None or math.isnan(self.df_discrep) else f"{self.df_discrep:.8f}"
        return (
            f"df_t={self.df_t:.8f}|df_s1={self.df_s1:.8f}|df_s2={self.df_s2:.8f}|"
            f"df_s67={self.df_s67:.8f}|df_discrep={discrep}|lambda={self.lambd:.8f}|"
            f"df_trans={self.df_trans:.8f}|df_covs={self.df_covs:.8f}"
        )


def parse_he2_table(tex_path: Path) -> pd.DataFrame:
    text = tex_path.read_text()
    marker = r"\noindent\textbf{Table HE2-A.}"
    start = text.find(marker)
    if start == -1:
        raise RuntimeError("Could not find Table HE2-A in corrections main.tex")
    end = text.find("This comparison addresses", start)
    if end == -1:
        raise RuntimeError("Could not find the end of the HE2 table section")
    block = text[start:end]

    rows: List[Dict[str, object]] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.endswith(r"\\"):
            continue
        if "&" not in line:
            continue
        if line.startswith(r"\multicolumn") or line.startswith("Model label"):
            continue
        parts = [part.strip() for part in line[:-2].split("&")]
        if len(parts) != 6:
            continue
        label = parts[0]
        values = parts[1:]
        cleaned = []
        for value in values:
            value = re.sub(r"\\textbf\{([^}]*)\}", r"\1", value)
            value = value.replace("$", "").strip()
            cleaned.append(float(value))
        row = {"label": label}
        for cutoff, value in zip(CUTOFF_ORDER, cleaned):
            row[cutoff] = value
        rows.append(row)

    if not rows:
        raise RuntimeError("Parsed zero HE2 rows from corrections main.tex")

    return pd.DataFrame(rows)


def resolve_run_config(source_run: str, preferred_root: Path) -> Path:
    direct = preferred_root / "runs" / source_run / "resolved_config.yaml"
    if direct.exists():
        return direct
    candidates = list(RUNTIME_ROOT.glob(f"*/runs/{source_run}/resolved_config.yaml"))
    if candidates:
        return candidates[0]
    raise FileNotFoundError(f"Could not resolve config for source run {source_run}")


def classify_discount_spec(model_variant: str, state: Dict[str, float]) -> DiscountSpec:
    df_s1 = float(state["df_s1"])
    baseline_like = abs(df_s1 - 0.9999) < 1e-12
    label = "baseline_tt_regime" if baseline_like else "tuned_postfix_regime"
    return DiscountSpec(
        label=label,
        df_t=float(state["df_t"]),
        df_s1=float(state["df_s1"]),
        df_s2=float(state["df_s2"]),
        df_s67=float(state["df_s67"]),
        df_discrep=float(state["df_discrep"]) if "df_discrep" in state else math.nan,
        lambd=float(state["lambda"]),
        df_trans=float(state["df_trans"]),
        df_covs=float(state["df_covs"]),
    )


def collect_campaign_rows() -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for campaign_name, meta in CAMPAIGNS.items():
        root = meta["root"]
        for compare_csv in sorted((root / "reports").glob(meta["report_glob"])):
            df = pd.read_csv(compare_csv)
            subset = df[df["model_variant"].isin(MODEL_VARIANT_TO_HE_LABEL)].copy()
            for _, record in subset.iterrows():
                source_run = record["source_run"]
                config_path = resolve_run_config(source_run, root)
                cfg = yaml.safe_load(config_path.read_text()) or {}
                config_key = MODEL_VARIANT_TO_CONFIG_KEY[str(record["model_variant"])]
                state = ((cfg.get("models") or {}).get(config_key) or {}).get("state_evolution") or {}
                spec = classify_discount_spec(str(record["model_variant"]), state)
                rows.append(
                    {
                        "campaign": campaign_name,
                        "campaign_display": meta["display_name"],
                        "campaign_status": meta["status"],
                        "use_for_discount_comparison": meta["use_for_discount_comparison"],
                        "cutoff": str(record["cutoff_date"]),
                        "model_variant": str(record["model_variant"]),
                        "he_label": MODEL_VARIANT_TO_HE_LABEL[str(record["model_variant"])],
                        "mean_crps": float(record["mean_crps"]),
                        "source_run": source_run,
                        "compare_csv": str(compare_csv),
                        "config_path": str(config_path),
                        "discount_label": spec.label,
                        "discount_signature": spec.signature(),
                        "df_t": spec.df_t,
                        "df_s1": spec.df_s1,
                        "df_s2": spec.df_s2,
                        "df_s67": spec.df_s67,
                        "df_discrep": spec.df_discrep,
                        "lambda": spec.lambd,
                        "df_trans": spec.df_trans,
                        "df_covs": spec.df_covs,
                    }
                )

    result = pd.DataFrame(rows)
    if result.empty:
        raise RuntimeError("No NDLM campaign rows were collected")
    return result.sort_values(["model_variant", "cutoff", "campaign"])


def build_he_winner_table(he2_df: pd.DataFrame) -> pd.DataFrame:
    winner_rows: List[Dict[str, object]] = []
    for cutoff in CUTOFF_ORDER:
        subset = he2_df[["label", cutoff]].copy()
        best_idx = subset[cutoff].idxmin()
        winner_rows.append(
            {
                "cutoff": cutoff,
                "he_best_label": subset.loc[best_idx, "label"],
                "he_best_crps": float(subset.loc[best_idx, cutoff]),
            }
        )
    return pd.DataFrame(winner_rows)


def build_current_vs_baseline(rows_df: pd.DataFrame, winner_df: pd.DataFrame) -> pd.DataFrame:
    baseline = rows_df[
        (rows_df["campaign"] == "baseline_20260402")
        & (rows_df["use_for_discount_comparison"])
    ][["cutoff", "model_variant", "mean_crps", "discount_label", "discount_signature"]].rename(
        columns={
            "mean_crps": "baseline_crps",
            "discount_label": "baseline_discount_label",
            "discount_signature": "baseline_discount_signature",
        }
    )

    current = rows_df[
        (rows_df["campaign"] == "postfix_20260421")
        & (rows_df["use_for_discount_comparison"])
    ][["cutoff", "model_variant", "he_label", "mean_crps", "discount_label", "discount_signature"]].rename(
        columns={
            "mean_crps": "current_postfix_crps",
            "discount_label": "current_discount_label",
            "discount_signature": "current_discount_signature",
        }
    )

    merged = current.merge(baseline, on=["cutoff", "model_variant"], how="left")
    merged = merged.merge(winner_df, on="cutoff", how="left")
    merged["delta_postfix_minus_baseline"] = merged["current_postfix_crps"] - merged["baseline_crps"]
    merged["pct_change_vs_baseline"] = (
        merged["delta_postfix_minus_baseline"] / merged["baseline_crps"] * 100.0
    )
    merged["gap_to_he_best"] = merged["current_postfix_crps"] - merged["he_best_crps"]
    merged["current_is_best_vs_baseline"] = merged["current_postfix_crps"] <= merged["baseline_crps"]
    return merged.sort_values(["model_variant", "cutoff"])


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def format_float(value: object, digits: int = 4) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{float(value):.{digits}f}"


def build_summary_markdown(
    rows_df: pd.DataFrame,
    winners_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
) -> str:
    lines: List[str] = []
    lines.append("# NDLM Discount-Spec CRPS Comparison\n")
    lines.append(
        "This report compares the distinct NDLM discount-factor regimes we have actually run "
        "historically against the current postfix NDLM rows that are now in Table HE2-A."
    )
    lines.append("")
    lines.append("## Main Takeaways")
    lines.append("")

    def wins_text(model_variant: str) -> str:
        subset = comparison_df[comparison_df["model_variant"] == model_variant]
        wins = int(subset["current_is_best_vs_baseline"].sum())
        total = len(subset)
        return f"{MODEL_VARIANT_TO_HE_LABEL[model_variant]}: current postfix beats baseline at {wins}/{total} cutoffs."

    for model_variant in ["ndlm_main_keep", "ndlm_main_drop", "ndlm_univar_keep"]:
        lines.append(f"- {wins_text(model_variant)}")
    lines.append(
        "- The only meaningful distinct NDLM discount regimes we currently have are the old baseline TT regime "
        "and the tuned/postfix regime now used in the HE table."
    )
    lines.append(
        "- The intermediate `ndlm_tune_20260411` and `featurecov_rerun_20260420` campaigns reuse the tuned discount regime; "
        "they are included in the audit CSVs, but not used as separate discount-spec competitors."
    )
    lines.append(
        "- This is not a pure discount-only experiment, because the baseline TT campaign also differs in inputs/protocol from the current postfix featurecov rerun."
    )
    lines.append("")

    lines.append("## Distinct Discount Regimes")
    lines.append("")
    regime_df = (
        rows_df[
            rows_df["campaign"].isin(["baseline_20260402", "postfix_20260421"])
        ][
            [
                "campaign_display",
                "model_variant",
                "discount_label",
                "df_t",
                "df_s1",
                "df_s2",
                "df_s67",
                "df_discrep",
                "lambda",
                "df_trans",
                "df_covs",
            ]
        ]
        .drop_duplicates()
        .sort_values(["model_variant", "campaign_display"])
    )
    lines.append(
        "| Campaign | Model | Regime | df_t | df_s1 | df_s2 | df_s67 | df_discrep | lambda | df_trans | df_covs |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, row in regime_df.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["campaign_display"]),
                    str(row["model_variant"]),
                    str(row["discount_label"]),
                    format_float(row["df_t"], 8),
                    format_float(row["df_s1"], 8),
                    format_float(row["df_s2"], 8),
                    format_float(row["df_s67"], 8),
                    format_float(row["df_discrep"], 8),
                    format_float(row["lambda"], 8),
                    format_float(row["df_trans"], 8),
                    format_float(row["df_covs"], 8),
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append("## Current HE Winner By Cutoff")
    lines.append("")
    lines.append("| Cutoff | Current HE Winner | Mean CRPS |")
    lines.append("|---|---|---:|")
    for _, row in winners_df.sort_values("cutoff").iterrows():
        lines.append(f"| {row['cutoff']} | {row['he_best_label']} | {format_float(row['he_best_crps'])} |")
    lines.append("")

    for model_variant in ["ndlm_main_keep", "ndlm_main_drop", "ndlm_univar_keep"]:
        he_label = MODEL_VARIANT_TO_HE_LABEL[model_variant]
        lines.append(f"## {he_label}")
        lines.append("")
        lines.append(
            "| Cutoff | Baseline TT CRPS | Current Postfix CRPS | Delta (postfix-baseline) | Current HE Winner | Winner CRPS | Gap To HE Winner |"
        )
        lines.append("|---|---:|---:|---:|---|---:|---:|")
        subset = comparison_df[comparison_df["model_variant"] == model_variant].sort_values("cutoff")
        for _, row in subset.iterrows():
            lines.append(
                f"| {row['cutoff']} | {format_float(row['baseline_crps'])} | {format_float(row['current_postfix_crps'])} | "
                f"{format_float(row['delta_postfix_minus_baseline'])} | {row['he_best_label']} | {format_float(row['he_best_crps'])} | "
                f"{format_float(row['gap_to_he_best'])} |"
            )
        lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The current postfix HE rows are the right manuscript-facing reference, because they use the corrected post predictive-generation path. "
        "Empirically, the tuned/postfix NDLM main keep regime (`N-M-T1`) is better than the historical baseline TT regime at all five cutoffs, "
        "while `N-M-T0` and `N-U-T1` improve at three of five cutoffs."
    )
    lines.append("")
    lines.append(
        "Because the baseline TT campaign and the current postfix campaign also differ in input contract and protocol, this comparison should be read "
        "as a historical empirical benchmark rather than a pure controlled discount-factor sweep. A strict discount-only answer would still require "
        "rerunning the old baseline discount regime under the same current postfix featurecov contract."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    he2_df = parse_he2_table(CORRECTIONS_TEX)
    winners_df = build_he_winner_table(he2_df)
    rows_df = collect_campaign_rows()
    comparison_df = build_current_vs_baseline(rows_df, winners_df)

    write_csv(rows_df, OUTPUT_DIR / "ndlm_discount_crps_history_long.csv")
    write_csv(winners_df, OUTPUT_DIR / "he2_current_winners.csv")
    write_csv(comparison_df, OUTPUT_DIR / "ndlm_discount_vs_current_he_optimal.csv")

    summary = build_summary_markdown(rows_df, winners_df, comparison_df)
    (OUTPUT_DIR / "ndlm_discount_comparison_summary.md").write_text(summary)

    print(f"Wrote {OUTPUT_DIR / 'ndlm_discount_crps_history_long.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'he2_current_winners.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'ndlm_discount_vs_current_he_optimal.csv'}")
    print(f"Wrote {OUTPUT_DIR / 'ndlm_discount_comparison_summary.md'}")


if __name__ == "__main__":
    main()
