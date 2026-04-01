#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from multimodel_v8_lib import ENSEMBLE_IDS, EPSILON_SENSITIVE_MODEL_IDS, TARGET_MODELS, TARGET_MODEL_IDS, v8_compare_dir


@dataclass(frozen=True)
class LaneSpec:
    label: str
    run_id: str
    source_type: str

    @property
    def output_root(self) -> Path:
        return Path("repro/runs") / self.run_id / "post" / "outputs" / self.run_id


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _lane_tables(lane: LaneSpec) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    root = lane.output_root
    crps = _read_csv(root / "tables" / "crps_forecast_summary.csv")
    health = _read_csv(root / "tables" / "crps_input_health.csv")
    fig_path = root / "figure_manifest.csv"
    fig = _read_csv(fig_path) if fig_path.exists() else pd.DataFrame(columns=["model_id", "plot_type", "path", "source_run", "note"])

    for df in (crps, health, fig):
        if "source_lane" not in df.columns:
            df["source_lane"] = lane.label
        else:
            df["source_lane"] = lane.label
        if "source_run" not in df.columns:
            df["source_run"] = lane.run_id
        else:
            df["source_run"] = lane.run_id
        if "source_type" not in df.columns:
            df["source_type"] = lane.source_type
        else:
            df["source_type"] = lane.source_type
    return crps, health, fig


def _dedupe_baselines(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "model_id" not in df.columns:
        return df
    non_ensemble = df.loc[~df["model_id"].isin(ENSEMBLE_IDS)].copy()
    ensemble = df.loc[df["model_id"].isin(ENSEMBLE_IDS)].copy()
    if not ensemble.empty:
        ensemble = ensemble.drop_duplicates(subset=["model_id"], keep="first")
    out = pd.concat([non_ensemble, ensemble], ignore_index=True)
    return out


def _build_source_map(cutoff: str, epsilon: str, baseline_l1: LaneSpec, baseline_l2: LaneSpec, mv_l1: LaneSpec | None, mv_l2: LaneSpec | None) -> pd.DataFrame:
    rows = []
    for spec in TARGET_MODELS:
        model_id = spec["model_id"]
        baseline_lane = spec["baseline_lane"]
        epsilon_sensitive = model_id in EPSILON_SENSITIVE_MODEL_IDS
        if epsilon_sensitive and epsilon != "epsTT":
            lane = mv_l1 if baseline_lane == "l1" else mv_l2
            if lane is None:
                raise ValueError(f"Missing epsilon-specific lane for {model_id} in {cutoff}/{epsilon}")
            source_type = "epsilon_specific_mv"
        else:
            lane = baseline_l1 if baseline_lane == "l1" else baseline_l2
            source_type = "baseline_tt"
        rows.append({
            "cutoff": cutoff,
            "epsilon": epsilon,
            "model_id": model_id,
            "source_run": lane.run_id,
            "source_lane": lane.label,
            "source_type": source_type,
        })
    return pd.DataFrame(rows)


def _select_rows(df: pd.DataFrame, source_map: pd.DataFrame, include_ensembles: bool = False) -> pd.DataFrame:
    frames = []
    for _, row in source_map.iterrows():
        subset = df.loc[(df["model_id"] == row["model_id"]) & (df["source_run"] == row["source_run"])].copy()
        if subset.empty:
            continue
        frames.append(subset)
    if include_ensembles and "model_id" in df.columns:
        ensemble = df.loc[df["model_id"].isin(ENSEMBLE_IDS)].copy()
        if not ensemble.empty:
            ensemble = ensemble.drop_duplicates(subset=["model_id"], keep="first")
            frames.append(ensemble)
    if not frames:
        return pd.DataFrame(columns=df.columns)
    out = pd.concat(frames, ignore_index=True)
    return out


def _coverage_note(model_id: str, health_row: pd.Series | None) -> str:
    if health_row is None:
        return ""
    status = str(health_row.get("status", "")).strip()
    max_abs = health_row.get("max_abs_observed")
    try:
        max_abs_val = float(max_abs)
    except Exception:
        max_abs_val = None
    if status and status.lower() != "pass":
        return f"input-health status={status}"
    if model_id == "ndlm_main_synth_keep" and max_abs_val is not None and max_abs_val > 100:
        return "Larger predictive scale than exdqlm lanes but input-health status=pass."
    return ""


def _build_coverage(crps: pd.DataFrame, health: pd.DataFrame) -> pd.DataFrame:
    crps_by_id = {row["model_id"]: row for _, row in crps.iterrows() if row["model_id"] in TARGET_MODEL_IDS}
    health_by_id = {row["model_id"]: row for _, row in health.iterrows() if row["model_id"] in TARGET_MODEL_IDS}
    rows = []
    for spec in TARGET_MODELS:
        model_id = spec["model_id"]
        crps_row = crps_by_id.get(model_id)
        exported = crps_row is not None
        rows.append({
            "model_id": model_id,
            "model_variant": spec["model_variant"],
            "transfer_mode": spec["transfer_mode"] if spec["transfer_mode"] else pd.NA,
            "source_lane": crps_row.get("source_lane") if exported else pd.NA,
            "source_run": crps_row.get("source_run") if exported else pd.NA,
            "source_type": crps_row.get("source_type") if exported else pd.NA,
            "export_status": "exported" if exported else "missing",
            "caveat": _coverage_note(model_id, health_by_id.get(model_id)),
        })
    return pd.DataFrame(rows)


def _write_summary(outdir: Path, cutoff: str, epsilon: str, source_map: pd.DataFrame, crps: pd.DataFrame, coverage: pd.DataFrame) -> None:
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        f"# multimodel_{cutoff}_v8_{epsilon} compare bundle",
        "",
        f"- Generated: {timestamp}",
        f"- Cutoff: `{cutoff}`",
        f"- Epsilon cell: `{epsilon}`",
        f"- Exported target models: {int((coverage['export_status'] == 'exported').sum())}/9",
        "- Source composition is explicit in `source_provenance.csv`.",
        "",
        "## Provenance",
    ]
    for _, row in source_map.sort_values(["source_type", "source_lane", "model_id"]).iterrows():
        lines.append(
            f"- `{row['model_id']}` <- `{row['source_run']}` ({row['source_lane']}, {row['source_type']})"
        )
    lines.extend(["", "## CRPS ranking", ""])
    rank_df = crps.loc[crps["model_id"].isin(TARGET_MODEL_IDS)].sort_values(["mean_crps", "median_crps", "model_id"])
    for _, row in rank_df.iterrows():
        lines.append(
            f"- `{row['model_id']}`: mean_crps={float(row['mean_crps']):.6f}, median_crps={float(row['median_crps']):.6f}, "
            f"source_run=`{row['source_run']}`, source_type=`{row['source_type']}`"
        )
    caveats = [c for c in coverage["caveat"].fillna("") if str(c).strip()]
    lines.extend(["", "## Residual caveats"])
    if caveats:
        for note in caveats:
            lines.append(f"- {note}")
    else:
        lines.append("- None.")
    (outdir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_bundle(cutoff: str, epsilon: str, baseline_l1: LaneSpec, baseline_l2: LaneSpec, outdir: Path, mv_l1: LaneSpec | None = None, mv_l2: LaneSpec | None = None) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    lane_specs = [baseline_l1, baseline_l2] + ([mv_l1] if mv_l1 else []) + ([mv_l2] if mv_l2 else [])
    lane_specs = [lane for lane in lane_specs if lane is not None]
    crps_frames = []
    health_frames = []
    fig_frames = []
    for lane in lane_specs:
        crps, health, fig = _lane_tables(lane)
        crps_frames.append(crps)
        health_frames.append(health)
        fig_frames.append(fig)

    all_crps = pd.concat(crps_frames, ignore_index=True)
    all_health = pd.concat(health_frames, ignore_index=True)
    all_fig = pd.concat(fig_frames, ignore_index=True) if fig_frames else pd.DataFrame(columns=["model_id", "plot_type", "path", "source_run", "note", "source_lane", "source_type"])

    source_map = _build_source_map(cutoff, epsilon, baseline_l1, baseline_l2, mv_l1, mv_l2)
    crps = _select_rows(all_crps, source_map, include_ensembles=True)
    health = _select_rows(all_health, source_map, include_ensembles=True)
    figures = _select_rows(all_fig, source_map, include_ensembles=False)

    crps = _dedupe_baselines(crps).sort_values(["mean_crps", "median_crps", "model_id"], ascending=[True, True, True]).reset_index(drop=True)
    health = _dedupe_baselines(health).sort_values(["model_id", "source_lane"], ascending=[True, True]).reset_index(drop=True)
    if not figures.empty:
        figures = figures.sort_values(["model_id", "plot_type", "path"], ascending=[True, True, True]).reset_index(drop=True)

    coverage = _build_coverage(crps, health)
    missing = coverage.loc[coverage["export_status"] != "exported", "model_id"].tolist()
    if missing:
        raise RuntimeError(f"Missing target model rows in compare bundle for {cutoff}/{epsilon}: {missing}")

    crps.to_csv(outdir / "crps_forecast_summary_all_models.csv", index=False)
    health.to_csv(outdir / "crps_input_health_all_models.csv", index=False)
    coverage.to_csv(outdir / "model_coverage.csv", index=False)
    figures.to_csv(outdir / "figure_manifest.csv", index=False)
    source_map.to_csv(outdir / "source_provenance.csv", index=False)
    _write_summary(outdir, cutoff, epsilon, source_map, crps, coverage)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build v8 compare bundle with explicit per-model provenance.")
    ap.add_argument("--cutoff", required=True)
    ap.add_argument("--epsilon", required=True, choices=["epsTT", "eps30", "eps90", "eps180", "eps360"])
    ap.add_argument("--baseline-l1-run", required=True)
    ap.add_argument("--baseline-l2-run", required=True)
    ap.add_argument("--outdir", required=False)
    ap.add_argument("--mv-l1-run")
    ap.add_argument("--mv-l2-run")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir) if args.outdir else v8_compare_dir(args.cutoff, args.epsilon)
    build_bundle(
        cutoff=args.cutoff,
        epsilon=args.epsilon,
        baseline_l1=LaneSpec(label=f"v8_epsTT_l1", run_id=args.baseline_l1_run, source_type="baseline_tt"),
        baseline_l2=LaneSpec(label=f"v8_epsTT_l2", run_id=args.baseline_l2_run, source_type="baseline_tt"),
        mv_l1=LaneSpec(label=f"v8_{args.epsilon}_l1_mv", run_id=args.mv_l1_run, source_type="epsilon_specific_mv") if args.mv_l1_run else None,
        mv_l2=LaneSpec(label=f"v8_{args.epsilon}_l2_mv", run_id=args.mv_l2_run, source_type="epsilon_specific_mv") if args.mv_l2_run else None,
        outdir=outdir,
    )


if __name__ == "__main__":
    main()
