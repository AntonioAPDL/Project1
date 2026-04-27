#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from he3_exdqlm_ablation_lib import build_status_frame, crps_summary_path, cutoff_to_display, read_model_mean_crps
from multimodel_v8_lib import load_yaml

VARIANT_DISPLAY_ORDER = ["full", "noTrend", "noTF", "noH1", "noH2", "noH3"]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build HE3 CRPS summary tables from the ablation matrix.")
    ap.add_argument("--matrix-dir", required=True)
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--allow-partial", action="store_true")
    return ap.parse_args()


def render_markdown(wide: pd.DataFrame) -> str:
    lines = ["# HE3 exdqlm multivar ablation summary", ""]
    for cutoff, cutoff_df in wide.groupby("cutoff", sort=False):
        cutoff_display = cutoff_df["cutoff_display"].iloc[0]
        lines.extend([f"## Cutoff {cutoff_display}", ""])
        lines.append("| Variant | Label | Mean CRPS | Status | Best Epsilon |")
        lines.append("|---|---|---:|---|---|")
        for _, row in cutoff_df.iterrows():
            lines.append(
                f"| `{row['variant']}` | `{row['manuscript_label']}` | {row['mean_crps']:.6f} | "
                f"`{row['status']}` | `{row['best_epsilon_label']}` |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def render_latex_rows(wide: pd.DataFrame) -> str:
    lines: list[str] = []
    for cutoff, cutoff_df in wide.groupby("cutoff", sort=False):
        cutoff_display = cutoff_df["cutoff_display"].iloc[0]
        lines.append(rf"\multicolumn{{3}}{{l}}{{\textit{{Cutoff {cutoff_display}}}}} \\")
        for _, row in cutoff_df.iterrows():
            lines.append(
                f"{row['manuscript_label']} & {row['best_epsilon_label']} & {row['mean_crps']:.4f} \\\\"
            )
        lines.append(r"\midrule")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    matrix_dir = Path(args.matrix_dir).resolve()
    metadata = load_yaml(matrix_dir / "matrix_metadata.yaml")
    artifact_root = Path(metadata["artifact_root"]).resolve()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else artifact_root / "reports" / "he3_exdqlm_ablation"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = pd.read_csv(matrix_dir / "matrix_plan.csv")
    status = build_status_frame(plan, artifact_root)
    status.to_csv(matrix_dir / "matrix_status.csv", index=False)

    merged = plan.merge(
        status.loc[:, ["run_id", "variant", "status", "phase"]],
        on=["run_id", "variant"],
        how="left",
    )
    if not args.allow_partial and not (merged["status"] == "pass").all():
        incomplete = merged[merged["status"] != "pass"][["run_id", "variant", "status"]]
        raise SystemExit(
            "HE3 summary requires all rows to pass. Incomplete rows: "
            + ", ".join(f"{row.run_id}:{row.variant}:{row.status}" for row in incomplete.itertuples())
        )

    rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        run_dir = Path(str(row["source_run_dir"])) if row["launch_mode"] == "reuse_reference" else artifact_root / "runs" / str(row["run_id"])
        mean_crps = read_model_mean_crps(crps_summary_path(run_dir), str(row["target_model_id"]))
        rows.append(
            {
                "cutoff": str(row["cutoff"]),
                "cutoff_display": cutoff_to_display(str(row["cutoff"])),
                "variant": str(row["variant"]),
                "manuscript_label": str(row["manuscript_label"]),
                "best_epsilon_label": str(row["best_epsilon_label"]),
                "best_c_factor": float(row["best_c_factor"]),
                "target_model_id": str(row["target_model_id"]),
                "launch_mode": str(row["launch_mode"]),
                "resolved_run_id": str(row["source_run_id"]) if row["launch_mode"] == "reuse_reference" else str(row["run_id"]),
                "resolved_run_dir": str(run_dir),
                "mean_crps": float(mean_crps),
                "status": str(row["status"]),
            }
        )

    long_df = pd.DataFrame(rows)
    long_df["variant"] = pd.Categorical(long_df["variant"], VARIANT_DISPLAY_ORDER, ordered=True)
    long_df = long_df.sort_values(["cutoff", "variant"]).reset_index(drop=True)

    wide_df = long_df.copy()
    wide_df.to_csv(output_dir / "he3_ablation_long.csv", index=False)
    wide_df.to_csv(output_dir / "he3_ablation_wide.csv", index=False)
    (output_dir / "he3_ablation_summary.md").write_text(render_markdown(wide_df), encoding="utf-8")
    (output_dir / "he3_table_rows.tex").write_text(render_latex_rows(wide_df), encoding="utf-8")
    print(output_dir / "he3_ablation_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
