#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

TARGET_MODELS: List[Dict[str, str]] = [
    {"model_id": "exdqlm_univar_synth", "lane_expected": "v7_l2", "model_variant": "exdqlm_univar", "transfer_mode": ""},
    {"model_id": "dqlm_univar_al_synth", "lane_expected": "v7_l1", "model_variant": "dqlm_univar_al", "transfer_mode": ""},
    {"model_id": "exdqlm_multivar_synth_drop", "lane_expected": "v7_l2", "model_variant": "exdqlm_multivar_drop", "transfer_mode": "drop"},
    {"model_id": "exdqlm_multivar_synth_keep", "lane_expected": "v7_l2", "model_variant": "exdqlm_multivar_keep", "transfer_mode": "keep"},
    {"model_id": "dqlm_multivar_al_synth_drop", "lane_expected": "v7_l1", "model_variant": "dqlm_multivar_al_drop", "transfer_mode": "drop"},
    {"model_id": "dqlm_multivar_al_synth_keep", "lane_expected": "v7_l1", "model_variant": "dqlm_multivar_al_keep", "transfer_mode": "keep"},
    {"model_id": "ndlm_main_synth_drop", "lane_expected": "v7_l2", "model_variant": "ndlm_main_drop", "transfer_mode": "drop"},
    {"model_id": "ndlm_main_synth_keep", "lane_expected": "v7_l1", "model_variant": "ndlm_main_keep", "transfer_mode": "keep"},
    {"model_id": "ndlm_univar_synth_keep", "lane_expected": "v7_l1", "model_variant": "ndlm_univar_keep", "transfer_mode": "keep"},
]

ENSEMBLE_IDS = {"glofas_ensemble", "nws_nwm_ensemble"}


@dataclass
class LaneSpec:
    label: str
    run_id: str

    @property
    def output_root(self) -> Path:
        return Path("repro/runs") / self.run_id / "post" / "outputs" / self.run_id


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _lane_tables(lane: LaneSpec) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    root = lane.output_root
    crps = _read_csv(root / "tables" / "crps_forecast_summary.csv")
    health = _read_csv(root / "tables" / "crps_input_health.csv")
    fig = _read_csv(root / "figure_manifest.csv") if (root / "figure_manifest.csv").exists() else pd.DataFrame(columns=["model_id", "plot_type", "path", "source_run", "note"])

    for df in [crps, health, fig]:
        if "source_lane" not in df.columns:
            df["source_lane"] = lane.label
        else:
            df["source_lane"] = lane.label
        if "source_run" not in df.columns:
            df["source_run"] = lane.run_id
    return crps, health, fig


def _dedupe_baselines(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "model_id" not in df.columns:
        return df
    non_ensemble = df.loc[~df["model_id"].isin(ENSEMBLE_IDS)].copy()
    ensemble = df.loc[df["model_id"].isin(ENSEMBLE_IDS)].copy()
    if not ensemble.empty:
        ensemble = ensemble.drop_duplicates(subset=["model_id"], keep="first")
    return pd.concat([non_ensemble, ensemble], ignore_index=True)


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
    if model_id == "dqlm_univar_al_synth" and max_abs_val is not None and max_abs_val > 100:
        return "High max_abs_observed in input-health but status=pass."
    if model_id == "ndlm_main_synth_keep" and max_abs_val is not None and max_abs_val > 100:
        return "Larger predictive scale than exdqlm lanes but input-health status=pass."
    return ""


def _build_coverage(crps: pd.DataFrame, health: pd.DataFrame) -> pd.DataFrame:
    crps_by_id = {row["model_id"]: row for _, row in crps.iterrows()}
    health_by_id = {row["model_id"]: row for _, row in health.iterrows()}
    rows = []
    for spec in TARGET_MODELS:
        model_id = spec["model_id"]
        crps_row = crps_by_id.get(model_id)
        exported = crps_row is not None
        rows.append({
            "model_id": model_id,
            "lane_expected": spec["lane_expected"],
            "model_variant": spec["model_variant"],
            "transfer_mode": spec["transfer_mode"] if spec["transfer_mode"] else pd.NA,
            "source_lane": crps_row.get("source_lane") if exported else pd.NA,
            "source_run": crps_row.get("source_run") if exported else pd.NA,
            "export_status": "exported" if exported else "missing",
            "caveat": _coverage_note(model_id, health_by_id.get(model_id)),
        })
    return pd.DataFrame(rows)


def _distinctness_note(crps: pd.DataFrame, prefix: str) -> str:
    drop_id = f"{prefix}_drop"
    keep_id = f"{prefix}_keep"
    rows = crps.set_index("model_id")
    if drop_id not in rows.index or keep_id not in rows.index:
        return f"{prefix}: unavailable"
    d = rows.loc[drop_id]
    k = rows.loc[keep_id]
    d_mean = float(d["mean_crps"])
    k_mean = float(k["mean_crps"])
    if abs(d_mean - k_mean) < 1e-12:
        return f"{prefix}: drop/keep still identical in aggregate"
    return f"{prefix}: drop mean_crps={d_mean:.6f}, keep mean_crps={k_mean:.6f}"


def _write_summary(outdir: Path, cutoff: str, lane_specs: List[LaneSpec], crps: pd.DataFrame, health: pd.DataFrame, coverage: pd.DataFrame, figures: pd.DataFrame) -> None:
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    target_exported = int((coverage["export_status"] == "exported").sum())
    lines: List[str] = []
    lines.append(f"# multimodel_{cutoff}_v7 comparison-ready summary")
    lines.append("")
    lines.append(f"- Generated: {timestamp}")
    for lane in lane_specs:
        lines.append(f"- {lane.label} source run: `{lane.run_id}`")
    lines.append("- Aggregate built from CRPS/input-health/figure exports in the accepted lane outputs.")
    lines.append("")
    lines.append("## Coverage")
    lines.append(f"- Exported target models: {target_exported}/9")
    lines.append("- Shared ensemble baselines included once in aggregate tables: `glofas_ensemble`, `nws_nwm_ensemble`.")
    lines.append(f"- Figure manifest rows: {len(figures)}")
    lines.append("")
    lines.append("## Distinctness audit")
    lines.append(f"- {_distinctness_note(crps, 'dqlm_multivar_al_synth')}")
    lines.append(f"- {_distinctness_note(crps, 'exdqlm_multivar_synth')}")
    lines.append("")
    lines.append("## CRPS ranking")
    lines.append("")
    crps_rank = crps.sort_values(["mean_crps", "median_crps", "model_id"], ascending=[True, True, True])
    for _, row in crps_rank.iterrows():
        transfer = row.get("transfer_mode")
        transfer_suffix = f", {transfer}" if pd.notna(transfer) and str(transfer).strip() else ""
        lines.append(
            f"- `{row['model_id']}` (`{row.get('model_variant', '')}`{transfer_suffix}): "
            f"mean_crps={float(row['mean_crps']):.6f}, median_crps={float(row['median_crps']):.6f}, "
            f"n_valid={int(row['n_valid'])}, source_run=`{row.get('source_run', '')}`"
        )
    lines.append("")
    lines.append("## Residual caveats")
    caveats = [c for c in coverage["caveat"].fillna("").tolist() if str(c).strip()]
    if caveats:
        for note in caveats:
            lines.append(f"- {note}")
    else:
        lines.append("- None.")
    lines.append("- Figures were produced in smoke-fast tables-first mode with model-id-specific filenames, not via the heavy legacy figure stack.")
    (outdir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_bundle(cutoff: str, lane1: LaneSpec, lane2: LaneSpec, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    lane1_crps, lane1_health, lane1_fig = _lane_tables(lane1)
    lane2_crps, lane2_health, lane2_fig = _lane_tables(lane2)

    crps = _dedupe_baselines(pd.concat([lane1_crps, lane2_crps], ignore_index=True))
    health = _dedupe_baselines(pd.concat([lane1_health, lane2_health], ignore_index=True))
    figures = pd.concat([lane1_fig.assign(lane=lane1.label), lane2_fig.assign(lane=lane2.label)], ignore_index=True)

    crps = crps.sort_values(["mean_crps", "median_crps", "model_id"], ascending=[True, True, True]).reset_index(drop=True)
    health = health.sort_values(["model_id", "source_lane"], ascending=[True, True]).reset_index(drop=True)
    figures = figures.sort_values(["model_id", "plot_type", "lane"], ascending=[True, True, True]).reset_index(drop=True)

    coverage = _build_coverage(crps, health)

    crps.to_csv(outdir / "crps_forecast_summary_all_models.csv", index=False)
    health.to_csv(outdir / "crps_input_health_all_models.csv", index=False)
    coverage.to_csv(outdir / "model_coverage.csv", index=False)
    figures.to_csv(outdir / "figure_manifest.csv", index=False)
    _write_summary(outdir, cutoff, [lane1, lane2], crps, health, coverage, figures)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build aggregate multimodel compare bundle from two v7 lane runs.")
    ap.add_argument("--cutoff", required=True)
    ap.add_argument("--lane1-run", required=True)
    ap.add_argument("--lane2-run", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--lane1-label", default="v7_l1")
    ap.add_argument("--lane2-label", default="v7_l2")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    build_bundle(
        cutoff=args.cutoff,
        lane1=LaneSpec(label=args.lane1_label, run_id=args.lane1_run),
        lane2=LaneSpec(label=args.lane2_label, run_id=args.lane2_run),
        outdir=Path(args.outdir),
    )


if __name__ == "__main__":
    main()
