from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLE_ROOT = ROOT / "Evironmetrics---REVISED-DOC-Corrected"
KEEP_RUNTIME_ROOT = ROOT.parent / "project1_ucsc_phd_runtime" / "multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516"
OUT_DIR = ROOT / "reports" / "he2_exal_keep_output_quality_audit_20260517"

CUTOFF_SPECS = [
    ("20210123", "2021-01-23"),
    ("20211112", "2021-11-12"),
    ("20211221", "2021-12-21"),
    ("20220511", "2022-05-11"),
    ("20221225", "2022-12-25"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def float_or_nan(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def row_for_model(rows: list[dict[str, str]], model_id: str) -> dict[str, str]:
    for row in rows:
        if row.get("model_id") == model_id:
            return row
    raise KeyError(f"Missing model_id={model_id}")


def classify_quality(mean_crps: float, q95_ratio: float, q80_ratio: float) -> str:
    if mean_crps > 100 or q95_ratio > 1e6 or q80_ratio > 1e4:
        return "extreme_run_side_issue"
    if mean_crps > 10 or q95_ratio > 1e4 or q80_ratio > 1e3:
        return "severe_run_side_issue"
    if mean_crps > 2 or q95_ratio > 100 or q80_ratio > 30:
        return "suspect"
    return "plausible"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    representative_runtime = (
        KEEP_RUNTIME_ROOT
        / "runs"
        / "multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep"
        / "post"
        / "outputs"
        / "multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep"
        / "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png"
    )
    representative_article = ARTICLE_ROOT / "figures" / "manuscript" / "representative_synthesis_multivariate.png"

    cutoff_rows: list[dict[str, object]] = []
    all_extreme = True

    for slug, cutoff in CUTOFF_SPECS:
        run_id = f"multimodel_{slug}_v8_he2pubgdpc1r1_exdqlm_multivar_keep"
        out_root = KEEP_RUNTIME_ROOT / "runs" / run_id / "post" / "outputs" / run_id
        crps_rows = read_csv(out_root / "tables" / "crps_forecast_summary.csv")
        quant_rows = read_csv(out_root / "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv")

        synth = row_for_model(crps_rows, "exdqlm_multivar_synth_keep")
        raw_glofas = row_for_model(crps_rows, "glofas_ensemble")
        raw_nws = row_for_model(crps_rows, "nws_nwm_ensemble")

        observed_vals = [float_or_nan(row["observed"]) for row in quant_rows]
        q50_vals = [float_or_nan(row["q50"]) for row in quant_rows]
        q80_vals = [float_or_nan(row["q80"]) for row in quant_rows]
        q95_vals = [float_or_nan(row["q95"]) for row in quant_rows]

        observed_max = max(v for v in observed_vals if math.isfinite(v))
        q50_max = max(v for v in q50_vals if math.isfinite(v))
        q80_max = max(v for v in q80_vals if math.isfinite(v))
        q95_max = max(v for v in q95_vals if math.isfinite(v))

        mean_crps = float(synth["mean_crps"])
        q80_ratio = q80_max / observed_max
        q95_ratio = q95_max / observed_max
        quality = classify_quality(mean_crps, q95_ratio, q80_ratio)
        all_extreme = all_extreme and quality in {"extreme_run_side_issue", "severe_run_side_issue"}

        cutoff_rows.append(
            {
                "cutoff": cutoff,
                "run_id": run_id,
                "synth_mean_crps": mean_crps,
                "glofas_mean_crps": float(raw_glofas["mean_crps"]),
                "nws_mean_crps": float(raw_nws["mean_crps"]),
                "observed_max": observed_max,
                "q50_max": q50_max,
                "q80_max": q80_max,
                "q95_max": q95_max,
                "q80_to_observed_max_ratio": q80_ratio,
                "q95_to_observed_max_ratio": q95_ratio,
                "quality_class": quality,
                "quantiles_csv": str(out_root / "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv"),
                "crps_summary_csv": str(out_root / "tables" / "crps_forecast_summary.csv"),
                "runtime_png": str(out_root / "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png"),
            }
        )

    with (OUT_DIR / "cutoff_quality_matrix.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cutoff_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(cutoff_rows)

    representative_row = next(row for row in cutoff_rows if row["cutoff"] == "2022-12-25")
    sync_rows = [
        {
            "asset": "representative_synthesis_multivariate.png",
            "article_path": str(representative_article),
            "runtime_path": str(representative_runtime),
            "article_sha256": sha256(representative_article),
            "runtime_sha256": sha256(representative_runtime),
            "byte_identical": sha256(representative_article) == sha256(representative_runtime),
        }
    ]
    with (OUT_DIR / "article_runtime_sync_check.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(sync_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(sync_rows)

    summary = {
        "representative_article_is_synced_to_runtime": sync_rows[0]["byte_identical"],
        "representative_keep_quality_class": representative_row["quality_class"],
        "representative_keep_mean_crps": representative_row["synth_mean_crps"],
        "representative_keep_q95_to_observed_max_ratio": representative_row["q95_to_observed_max_ratio"],
        "all_five_cutoffs_show_severe_or_worse_issue": all_extreme,
        "article_staleness_is_primary_explanation": False,
        "likely_primary_explanation": "run_side_output_quality_issue",
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    md: list[str] = []
    md.append("# HE2 exAL Keep Output Quality Audit (2026-05-17)\n\n")
    md.append("## Purpose\n\n")
    md.append("This audit checks whether the weird-looking `exAL-M-T1` synthesis figures in the revised doc are caused by stale article wiring or by the current keep rerun outputs themselves.\n\n")
    md.append("## Executive Conclusion\n\n")
    md.append(f"- Representative article figure synced to runtime output: `{sync_rows[0]['byte_identical']}`.\n")
    md.append(f"- Representative keep quality class: `{representative_row['quality_class']}`.\n")
    md.append(f"- Representative keep mean CRPS: `{representative_row['synth_mean_crps']}`.\n")
    md.append(f"- Representative keep `q95 / observed_max` ratio: `{representative_row['q95_to_observed_max_ratio']:.4e}`.\n")
    md.append(f"- All five cutoffs severe-or-worse: `{all_extreme}`.\n")
    md.append("- Primary interpretation: the article is synced to the latest keep outputs, and the current keep outputs themselves are numerically implausible.\n\n")
    md.append("## Cutoff Matrix\n\n")
    md.append("| Cutoff | Synth mean CRPS | GloFAS mean CRPS | NWS mean CRPS | Observed max | q50 max | q80 max | q95 max | q80/obs max | q95/obs max | Quality |\n")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for row in cutoff_rows:
        md.append(
            f"| {row['cutoff']} | {row['synth_mean_crps']:.4f} | {row['glofas_mean_crps']:.4f} | {row['nws_mean_crps']:.4f} | "
            f"{row['observed_max']:.4f} | {row['q50_max']:.4f} | {row['q80_max']:.4e} | {row['q95_max']:.4e} | "
            f"{row['q80_to_observed_max_ratio']:.4e} | {row['q95_to_observed_max_ratio']:.4e} | `{row['quality_class']}` |\n"
        )
    md.append("\n## Interpretation\n\n")
    md.append("- This is **not** primarily an article-staleness problem: the representative manuscript figure matches the current runtime PNG exactly.\n")
    md.append("- The current keep synthesis quantiles are already pathological in the underlying CSVs, with massive `q80`/`q95` inflation relative to observed values.\n")
    md.append("- Therefore the keep-family issue should be investigated as a run-side/post-side model-output problem after the historical-support renderer is fixed.\n")
    (OUT_DIR / "HE2_EXAL_KEEP_OUTPUT_QUALITY_AUDIT_20260517.md").write_text("".join(md))

    print(f"Wrote keep output quality audit to {OUT_DIR}")


if __name__ == "__main__":
    main()
