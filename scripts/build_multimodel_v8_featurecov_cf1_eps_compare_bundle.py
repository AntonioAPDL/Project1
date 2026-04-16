#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from multimodel_v8_lib import ENSEMBLE_IDS, TARGET_MODEL_IDS, runs_dir

SWEEP_MODEL_IDS = {
    "exdqlm_multivar_synth_keep",
    "exdqlm_multivar_synth_drop",
    "dqlm_multivar_al_synth_keep",
    "dqlm_multivar_al_synth_drop",
    "ndlm_main_synth_keep",
    "ndlm_main_synth_drop",
}


def _read_csv(path: Path, required: bool = True) -> pd.DataFrame:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return pd.DataFrame()
    return pd.read_csv(path)


def _replace_rows(df: pd.DataFrame, new_rows: pd.DataFrame, key: str = "model_id") -> pd.DataFrame:
    if df.empty:
        return new_rows.copy()
    if new_rows.empty:
        return df.copy()
    ids = {str(x) for x in new_rows[key].dropna().astype(str).tolist()}
    kept = df.loc[~df[key].astype(str).isin(ids)].copy()
    return pd.concat([kept, new_rows], ignore_index=True)


def _dedupe_ensembles(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "model_id" not in df.columns:
        return df
    ensemble = df.loc[df["model_id"].isin(ENSEMBLE_IDS)].drop_duplicates(subset=["model_id"], keep="first")
    non_ensemble = df.loc[~df["model_id"].isin(ENSEMBLE_IDS)]
    return pd.concat([non_ensemble, ensemble], ignore_index=True)


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _resolve_output_root(row: pd.Series, artifact_root: str | Path | None = None) -> tuple[Path, str, str]:
    if _boolish(row.get("reused", False)) and str(row.get("reuse_source_run_root", "")).strip():
        source_run_root = Path(str(row["reuse_source_run_root"]))
        source_run_id = str(row.get("reuse_source_run_id", "")).strip() or str(row["run_id"])
        return source_run_root / "post" / "outputs" / source_run_id, source_run_id, "reused_external_pass"
    run_id = str(row["run_id"])
    return runs_dir(artifact_root) / run_id / "post" / "outputs" / run_id, run_id, "launched_local_run"


def _load_row_tables(row: pd.Series, artifact_root: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    model_id = str(row["model_id"])
    output_root, physical_source_run, execution_origin = _resolve_output_root(row, artifact_root)
    crps = _read_csv(output_root / "tables" / "crps_forecast_summary.csv")
    health = _read_csv(output_root / "tables" / "crps_input_health.csv")
    fig = _read_csv(output_root / "figure_manifest.csv", required=False)

    crps = crps.loc[crps["model_id"] == model_id].copy()
    health = health.loc[health["model_id"] == model_id].copy()
    fig = fig.loc[fig["model_id"] == model_id].copy() if not fig.empty and "model_id" in fig.columns else pd.DataFrame(columns=["model_id", "plot_type", "path"])
    if crps.empty or health.empty:
        raise RuntimeError(f"Missing sweep rows for model_id={model_id} in output root {output_root}")

    logical_run_id = str(row["run_id"])
    family_id = str(row["family_id"])
    for df in (crps, health, fig):
        if df.empty:
            continue
        df["source_run"] = logical_run_id
        df["source_lane"] = family_id
        df["source_type"] = "featurecov_cf1_eps_sweep"
        df["execution_origin"] = execution_origin
        df["physical_source_run"] = physical_source_run
    return crps, health, fig


def _build_coverage(authoritative_coverage: pd.DataFrame, source_map: pd.DataFrame, replaced_ids: set[str]) -> pd.DataFrame:
    rows = authoritative_coverage.loc[~authoritative_coverage["model_id"].astype(str).isin(replaced_ids)].copy()
    repl_rows = []
    for _, row in source_map.iterrows():
        repl_rows.append(
            {
                "model_id": row["model_id"],
                "model_variant": row.get("family_id", row["model_id"]),
                "transfer_mode": row.get("transfer_mode", pd.NA),
                "source_lane": row["source_lane"],
                "source_run": row["source_run"],
                "source_type": row["source_type"],
                "export_status": "exported",
                "caveat": "reused compatible prior run" if _boolish(row.get("reused", False)) else "",
            }
        )
    out = pd.concat([rows, pd.DataFrame(repl_rows)], ignore_index=True)
    if not out.empty:
        out = out.loc[out["model_id"].isin(TARGET_MODEL_IDS)].copy()
        out = out.sort_values(["model_id", "source_type", "source_run"], kind="stable").reset_index(drop=True)
    return out


def _write_summary(outdir: Path, cutoff: str, epsilon_label: str, authoritative_compare_dir: Path, source_map: pd.DataFrame, crps: pd.DataFrame) -> None:
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        f"# multimodel_{cutoff}_v8_{epsilon_label} compare bundle",
        "",
        f"- Generated: {timestamp}",
        f"- Cutoff: `{cutoff}`",
        f"- Epsilon label: `{epsilon_label}`",
        f"- Authoritative compare source: `{authoritative_compare_dir}`",
        "- Raw ensemble rows and unswept univariate rows are preserved from the authoritative compare source.",
        "- Swept rows are replaced from the featurecov cf1 epsilon relaunch runs listed below.",
        "",
        "## Replaced swept rows",
    ]
    for _, row in source_map.sort_values(["family_id", "model_id"]).iterrows():
        suffix = f", reused_from=`{row['reuse_source_run_id']}`" if _boolish(row.get("reused", False)) else ""
        lines.append(
            f"- `{row['model_id']}` <- `{row['source_run']}` ({row['family_id']}, c_factor=`{row['target_c_factor']}`, epsilon=`{row['target_epsilon']}`{suffix})"
        )
    lines.extend(["", "## CRPS ranking", ""])
    rank_df = crps.loc[crps["model_id"].isin(TARGET_MODEL_IDS)].sort_values(["mean_crps", "median_crps", "model_id"])
    for _, row in rank_df.iterrows():
        lines.append(
            f"- `{row['model_id']}`: mean_crps={float(row['mean_crps']):.6f}, median_crps={float(row['median_crps']):.6f}, source_type=`{row.get('source_type', '')}`"
        )
    (outdir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_bundle(cutoff: str, epsilon_label: str, matrix_dir: Path, outdir: Path, artifact_root: str | Path | None = None) -> None:
    plan = pd.read_csv(matrix_dir / "matrix_plan.csv")
    cell_plan = plan.loc[(plan["cutoff"].astype(str) == str(cutoff)) & (plan["epsilon"].astype(str) == str(epsilon_label))].copy()
    if cell_plan.empty:
        raise RuntimeError(f"No matrix plan rows found for cutoff={cutoff} epsilon={epsilon_label}")

    authoritative_dirs = cell_plan["authoritative_compare_dir"].dropna().astype(str).unique().tolist()
    if len(authoritative_dirs) != 1:
        raise RuntimeError(f"Expected exactly one authoritative compare dir for cutoff={cutoff} epsilon={epsilon_label}; got {authoritative_dirs}")
    authoritative_compare_dir = Path(authoritative_dirs[0])
    if not authoritative_compare_dir.exists():
        raise FileNotFoundError(authoritative_compare_dir)

    auth_crps = _read_csv(authoritative_compare_dir / "crps_forecast_summary_all_models.csv")
    auth_health = _read_csv(authoritative_compare_dir / "crps_input_health_all_models.csv")
    auth_coverage = _read_csv(authoritative_compare_dir / "model_coverage.csv")
    auth_source = _read_csv(authoritative_compare_dir / "source_provenance.csv")
    auth_fig = _read_csv(authoritative_compare_dir / "figure_manifest.csv", required=False)

    source_rows = []
    crps_frames = []
    health_frames = []
    fig_frames = []
    for _, row in cell_plan.sort_values(["family_id", "run_id"]).iterrows():
        model_id = str(row["model_id"])
        crps, health, fig = _load_row_tables(row, artifact_root)
        crps_frames.append(crps)
        health_frames.append(health)
        if not fig.empty:
            fig_frames.append(fig)
        source_rows.append(
            {
                "cutoff": cutoff,
                "epsilon": epsilon_label,
                "model_id": model_id,
                "source_run": str(row["run_id"]),
                "source_lane": str(row["family_id"]),
                "source_type": "featurecov_cf1_eps_sweep",
                "family_id": str(row["family_id"]),
                "transfer_mode": row.get("transfer_mode", ""),
                "selected_source_run": row.get("selected_source_run", ""),
                "selected_c_factor": row.get("selected_c_factor", ""),
                "selected_epsilon": row.get("selected_epsilon", ""),
                "target_c_factor": row.get("target_c_factor", ""),
                "target_epsilon": row.get("target_epsilon", ""),
                "reused": row.get("reused", False),
                "reuse_source_run_id": row.get("reuse_source_run_id", ""),
            }
        )

    source_map = pd.DataFrame(source_rows)
    replaced_ids = set(source_map["model_id"].astype(str).tolist())
    if replaced_ids != SWEEP_MODEL_IDS:
        missing = sorted(SWEEP_MODEL_IDS.difference(replaced_ids))
        extra = sorted(replaced_ids.difference(SWEEP_MODEL_IDS))
        raise RuntimeError(f"Unexpected swept model set for cutoff={cutoff} epsilon={epsilon_label}; missing={missing}, extra={extra}")

    new_crps = pd.concat(crps_frames, ignore_index=True)
    new_health = pd.concat(health_frames, ignore_index=True)
    new_fig = pd.concat(fig_frames, ignore_index=True) if fig_frames else pd.DataFrame(columns=auth_fig.columns if not auth_fig.empty else ["model_id", "plot_type", "path", "source_run", "source_lane", "source_type"])

    final_crps = _replace_rows(auth_crps, new_crps)
    final_crps = _dedupe_ensembles(final_crps).sort_values(["mean_crps", "median_crps", "model_id"], kind="stable").reset_index(drop=True)
    final_health = _replace_rows(auth_health, new_health).sort_values(["model_id", "source_type", "source_run"], kind="stable").reset_index(drop=True)
    final_source = _replace_rows(auth_source, source_map).sort_values(["model_id", "source_type", "source_run"], kind="stable").reset_index(drop=True)
    final_coverage = _build_coverage(auth_coverage, source_map, replaced_ids)
    if "cutoff" in final_source.columns:
        final_source["cutoff"] = str(cutoff)
    if "epsilon" in final_source.columns:
        final_source["epsilon"] = str(epsilon_label)

    if auth_fig.empty:
        final_fig = new_fig.copy()
    else:
        final_fig = _replace_rows(auth_fig, new_fig).sort_values(["model_id", "plot_type", "path"], kind="stable").reset_index(drop=True)

    outdir.mkdir(parents=True, exist_ok=True)
    final_crps.to_csv(outdir / "crps_forecast_summary_all_models.csv", index=False)
    final_health.to_csv(outdir / "crps_input_health_all_models.csv", index=False)
    final_coverage.to_csv(outdir / "model_coverage.csv", index=False)
    final_fig.to_csv(outdir / "figure_manifest.csv", index=False)
    final_source.to_csv(outdir / "source_provenance.csv", index=False)
    _write_summary(outdir, cutoff, epsilon_label, authoritative_compare_dir, source_map, final_crps)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build a featurecov cf1 epsilon compare bundle by merging swept rows into an authoritative compare bundle.")
    ap.add_argument("--cutoff", required=True)
    ap.add_argument("--epsilon", required=True)
    ap.add_argument("--matrix-dir", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--artifact-root")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    build_bundle(
        cutoff=args.cutoff,
        epsilon_label=args.epsilon,
        matrix_dir=Path(args.matrix_dir),
        outdir=Path(args.outdir),
        artifact_root=args.artifact_root,
    )


if __name__ == "__main__":
    main()
