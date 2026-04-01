#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any

import pandas as pd

from multimodel_v8_lib import (
    AUTHORITATIVE_V7_BUNDLE_NAMES,
    CONFIG_DIR,
    CUTOFF_TO_DATE,
    CUTOFFS,
    EPSILON_LABEL_TO_VALUE,
    FALLBACK_INPUTS,
    FORECATS_BUNDLE_BY_CUTOFF,
    HEAVY_CUTOFF,
    HISTORICAL_SUFFIX_TO_EPSILON,
    REPORTS_DIR,
    ROOT,
    RUNS_DIR,
    build_lane_plan_rows,
    deep_copy_dict,
    ensure_dir,
    load_yaml,
    matrix_report_dir,
    v7_template_config_path,
    v8_compare_dir,
    write_yaml,
)

V7_COMPARE_BUNDLES = [REPORTS_DIR / name for name in AUTHORITATIVE_V7_BUNDLE_NAMES]
V7_CROSS_CUTOFF = REPORTS_DIR / "multimodel_v7_compare_alfix_20260331"
V7_AUTHORITATIVE_PACKAGE = REPORTS_DIR / "multimodel_v7_authoritative_20260401"

LIGHTWEIGHT_REQUIRED_FILES = [
    "crps_forecast_summary_all_models.csv",
    "crps_input_health_all_models.csv",
    "model_coverage.csv",
    "figure_manifest.csv",
    "summary.md",
]


def _set_nested(cfg: dict[str, Any], path: list[str], value: Any) -> None:
    cur = cfg
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def _parse_cutoff_from_name(name: str) -> str | None:
    m = re.search(r"multimodel_(\d{8})", name)
    return m.group(1) if m else None


def _historical_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cutoff, _ in CUTOFFS:
        for suffix, epsilon in HISTORICAL_SUFFIX_TO_EPSILON.items():
            run_id = f"multimodel_{cutoff}{suffix}"
            path = RUNS_DIR / run_id
            role = "historical_canonical"
            reason = "Preserved pre-fix canonical epsilon lineage point."
            if suffix == "_v4":
                role = "historical_duplicate_eps30"
                reason = "Preserved duplicate historical eps=30 lineage point; not a unique v8 scientific cell."
            if not path.exists():
                reason = f"{reason} Path is not present in the current trimmed workspace snapshot, but the lineage point remains reserved and must not be overwritten."
            rows.append({
                "path": str(path),
                "cutoff": cutoff,
                "lineage_role": role,
                "epsilon_value": "TT" if epsilon is None else int(epsilon),
                "authoritative_for_current_use": "no",
                "must_preserve": "yes",
                "action": "keep",
                "reason": reason,
            })
    return rows


def _authoritative_v7_source_runs() -> set[str]:
    source_runs: set[str] = set()
    for bundle in V7_COMPARE_BUNDLES:
        cov_path = bundle / "model_coverage.csv"
        if not cov_path.exists():
            continue
        df = pd.read_csv(cov_path)
        if "source_run" in df.columns:
            source_runs.update(str(x) for x in df["source_run"].dropna().unique() if str(x).strip())
    return source_runs


def _report_rows(source_runs: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle in V7_COMPARE_BUNDLES:
        cutoff = _parse_cutoff_from_name(bundle.name) or "all"
        reason = "Corrected authoritative v7 compare bundle; preserved source of truth for current use."
        if not bundle.exists():
            reason = f"{reason} Bundle directory is not present in the current trimmed workspace snapshot."
        rows.append({
            "path": str(bundle),
            "cutoff": cutoff,
            "lineage_role": "v7_authoritative_compare_bundle",
            "epsilon_value": "TT",
            "authoritative_for_current_use": "yes",
            "must_preserve": "yes",
            "action": "keep",
            "reason": reason,
        })
    for path, role, reason in [
        (V7_CROSS_CUTOFF, "v7_authoritative_cross_cutoff", "Corrected authoritative cross-cutoff rankings for v7."),
        (V7_AUTHORITATIVE_PACKAGE, "v7_authoritative_handoff", "Packaged authoritative v7 handoff."),
    ]:
        if not path.exists():
            reason = f"{reason} Directory is not present in the current trimmed workspace snapshot."
        rows.append({
            "path": str(path),
            "cutoff": "all",
            "lineage_role": role,
            "epsilon_value": "TT",
            "authoritative_for_current_use": "yes",
            "must_preserve": "yes",
            "action": "keep",
            "reason": reason,
        })
    for run_id in sorted(source_runs):
        cutoff = _parse_cutoff_from_name(run_id) or "all"
        rows.append({
            "path": str(RUNS_DIR / run_id),
            "cutoff": cutoff,
            "lineage_role": "v7_authoritative_source_run",
            "epsilon_value": "TT",
            "authoritative_for_current_use": "yes",
            "must_preserve": "yes",
            "action": "keep",
            "reason": "Authoritative corrected v7 source run referenced directly by compare bundles.",
        })
    return rows


def _helper_run_rows(source_runs: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    historical_ids = {f"multimodel_{cutoff}{suffix}" for cutoff, _ in CUTOFFS for suffix in HISTORICAL_SUFFIX_TO_EPSILON}
    if not RUNS_DIR.exists():
        return rows
    for path in sorted(RUNS_DIR.iterdir()):
        if not path.is_dir():
            continue
        name = path.name
        if name in historical_ids or name in source_runs:
            continue
        cutoff = _parse_cutoff_from_name(name) or "all"
        role = None
        action = "delete_later"
        must_preserve = "no"
        reason = "Superseded helper run; keep only if needed for historical debugging."
        if name.startswith("proof_"):
            role = "proof_helper_run"
            reason = "Historical proof run; superseded by corrected v7 and planned v8 lineage."
        elif name.startswith("repair_"):
            role = "repair_helper_run"
            reason = "Historical repair run; superseded by corrected v7 and planned v8 lineage."
        elif name.startswith("control_"):
            role = "control_helper_run"
            reason = "Control/debug helper run; not authoritative for current use."
        elif name.startswith("decision_"):
            role = "accepted_decision_evidence"
            action = "keep"
            must_preserve = "yes"
            reason = "Accepted decision evidence referenced in trackers/docs; preserve for traceability."
        elif "_v7_" in name:
            role = "superseded_v7_helper_run"
            reason = "Superseded v7 helper/postreplay/rerun root; not authoritative once corrected bundles are preserved."
        elif name.startswith("multimodel_"):
            role = "other_multimodel_helper_run"
            reason = "Multimodel helper root outside preserved historical/v7 authoritative set."
        if role is None:
            continue
        rows.append({
            "path": str(path),
            "cutoff": cutoff,
            "lineage_role": role,
            "epsilon_value": "",
            "authoritative_for_current_use": "no",
            "must_preserve": must_preserve,
            "action": action,
            "reason": reason,
        })
    return rows


def build_lineage_and_retention(matrix_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    source_runs = _authoritative_v7_source_runs()
    rows = _historical_rows() + _report_rows(source_runs) + _helper_run_rows(source_runs)
    df = pd.DataFrame(rows).sort_values(["cutoff", "lineage_role", "path"], na_position="last").reset_index(drop=True)
    retention = df.copy()
    ensure_dir(matrix_dir)
    df.to_csv(matrix_dir / "lineage_map.csv", index=False)
    retention.to_csv(matrix_dir / "retention_plan.csv", index=False)
    return df, retention


def build_v8_config(template_cfg: dict[str, Any], run_id: str, epsilon_label: str, epsilon_value: float | None, lane: str, cutoff: str) -> dict[str, Any]:
    cfg = deep_copy_dict(template_cfg)
    _set_nested(cfg, ["run", "run_id"], run_id)
    _set_nested(cfg, ["run", "run_root"], "repro/runs")
    _set_nested(cfg, ["run", "overwrite"], False)
    _set_nested(cfg, ["run", "auto_suffix_on_collision"], False)
    _set_nested(cfg, ["run", "dry_run"], False)
    _set_nested(cfg, ["run", "git_require_clean"], False)

    _set_nested(cfg, ["stages", "forecats"], True)
    _set_nested(cfg, ["stages", "data_prep_shared"], True)
    _set_nested(cfg, ["stages", "fit"], True)
    _set_nested(cfg, ["stages", "post"], True)
    _set_nested(cfg, ["stages", "validate"], True)
    _set_nested(cfg, ["stages", "report"], True)

    _set_nested(cfg, ["post", "figures"], True)
    _set_nested(cfg, ["post", "smoke_fast"], True)
    _set_nested(cfg, ["post", "force_isolation_smoke_fast"], True)
    _set_nested(cfg, ["post", "export_tables"], True)

    _set_nested(cfg, ["inputs", "forecats", "mode"], "use_existing")
    _set_nested(cfg, ["inputs", "forecats", "pipeline_config_path"], "config/forecats_pipeline.template.yaml")
    _set_nested(cfg, ["inputs", "forecats", "existing_bundle_path"], str(FORECATS_BUNDLE_BY_CUTOFF[cutoff]))
    _set_nested(cfg, ["inputs", "forecats", "snapshot", "enabled"], True)
    _set_nested(cfg, ["inputs", "forecats", "snapshot", "dest_rel"], "inputs/shared/forecats_bundle")
    _set_nested(cfg, ["inputs", "shared", "prefer_forecats_snapshot"], True)

    _set_nested(cfg, ["inputs", "fit", "retros_path"], str(FALLBACK_INPUTS["retros_path"]))
    _set_nested(cfg, ["inputs", "fit", "retros_storage_scale"], FALLBACK_INPUTS["retros_storage_scale"])
    _set_nested(cfg, ["inputs", "fit", "nws_forecast_path"], str(FALLBACK_INPUTS["nws_forecast_path"]))
    _set_nested(cfg, ["inputs", "fit", "nws_storage_scale"], FALLBACK_INPUTS["nws_storage_scale"])
    _set_nested(cfg, ["inputs", "fit", "glofas_forecast_path"], str(FALLBACK_INPUTS["glofas_forecast_path"]))
    _set_nested(cfg, ["inputs", "fit", "glofas_storage_scale"], FALLBACK_INPUTS["glofas_storage_scale"])

    _set_nested(cfg, ["fit", "exdqlm_multivar", "legacy", "forecast_cov", "epsilon"], epsilon_value)

    if lane.endswith("_mv"):
        _set_nested(cfg, ["models", "run_exdqlm_multivar"], True)
        _set_nested(cfg, ["models", "run_exdqlm_univar"], False)
        _set_nested(cfg, ["models", "run_ndlm_main"], False)
        _set_nested(cfg, ["models", "run_ndlm_univar"], False)
    else:
        if lane == "l1":
            _set_nested(cfg, ["models", "run_exdqlm_multivar"], True)
            _set_nested(cfg, ["models", "run_exdqlm_univar"], True)
            _set_nested(cfg, ["models", "run_ndlm_main"], True)
            _set_nested(cfg, ["models", "run_ndlm_univar"], True)
        elif lane == "l2":
            _set_nested(cfg, ["models", "run_exdqlm_multivar"], True)
            _set_nested(cfg, ["models", "run_exdqlm_univar"], True)
            _set_nested(cfg, ["models", "run_ndlm_main"], True)
            _set_nested(cfg, ["models", "run_ndlm_univar"], False)

    cfg["debug_v8_matrix"] = {
        "cutoff": cutoff,
        "epsilon_label": epsilon_label,
        "epsilon_value": epsilon_value,
        "run_scope": "multivar_only" if lane.endswith("_mv") else "full_tt",
        "template_source": str(v7_template_config_path(cutoff, "l1" if lane.startswith("l1") else "l2")),
        "forecats_bundle_path": str(FORECATS_BUNDLE_BY_CUTOFF[cutoff]),
        "shared_input_contract": "run_local_snapshot_from_stable_forecats_bundle",
        "historical_mapping_note": "Preserved historical mapping: base=TT/null, v2=30, v3=90, v4=30 duplicate, v5=180, v6=360.",
        "compare_bundle_outdir": str(v8_compare_dir(cutoff, epsilon_label)),
    }
    return cfg


def write_matrix_plan(matrix_dir: Path) -> pd.DataFrame:
    rows = []
    for order_index, plan in enumerate(build_lane_plan_rows(), start=1):
        rows.append({
            "order_index": order_index,
            "cutoff": plan.cutoff,
            "epsilon": plan.epsilon_label,
            "epsilon_value": "TT" if plan.epsilon_value is None else int(plan.epsilon_value),
            "lane": plan.lane,
            "run_scope": plan.run_scope,
            "run_id": plan.run_id,
            "config_path": str(plan.config_path),
            "compare_outdir": str(v8_compare_dir(plan.cutoff, plan.epsilon_label)),
            "priority_group": plan.priority_group,
            "max_concurrent_class": plan.max_concurrent_class,
        })
    df = pd.DataFrame(rows)
    df.to_csv(matrix_dir / "matrix_plan.csv", index=False)
    return df


def build_dependency_table(config_paths: list[Path], matrix_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cfg_path in config_paths:
        cfg = load_yaml(cfg_path)
        dep_specs = [
            (
                "forecats_existing_bundle",
                cfg.get("inputs", {}).get("forecats", {}).get("existing_bundle_path", ""),
                "yes",
                "Stable provider bundle used to synthesize run-local shared snapshots; replaces missing historical repro/runs input roots.",
            ),
            (
                "fit_fallback_retros",
                cfg.get("inputs", {}).get("fit", {}).get("retros_path", ""),
                "no",
                "Fallback schema-valid retros path. Normal v8 execution should consume the run-local snapshot built from the forecats bundle instead.",
            ),
            (
                "fit_fallback_nws_forecast",
                cfg.get("inputs", {}).get("fit", {}).get("nws_forecast_path", ""),
                "no",
                "Fallback schema-valid NWS path. Normal v8 execution should consume the run-local snapshot built from the forecats bundle instead.",
            ),
            (
                "fit_fallback_glofas_forecast",
                cfg.get("inputs", {}).get("fit", {}).get("glofas_forecast_path", ""),
                "no",
                "Fallback schema-valid GloFAS path. Normal v8 execution should consume the run-local snapshot built from the forecats bundle instead.",
            ),
        ]
        for dep_type, dep_path, preserve_required, note in dep_specs:
            dep_path = str(dep_path or "")
            rows.append({
                "consumer_config": str(cfg_path),
                "dependency_path": dep_path,
                "dependency_type": dep_type,
                "preserve_required": preserve_required,
                "note": note if dep_path else "missing dependency path",
            })
    df = pd.DataFrame(rows).sort_values(["consumer_config", "dependency_type"]).reset_index(drop=True)
    df.to_csv(matrix_dir / "dependency_preservation.csv", index=False)
    return df


def generate_configs(matrix_dir: Path) -> list[Path]:
    generated: list[Path] = []
    for cutoff, _date in CUTOFFS:
        for base_lane in ("l1", "l2"):
            template = load_yaml(v7_template_config_path(cutoff, base_lane))
            for epsilon_label, epsilon_value in EPSILON_LABEL_TO_VALUE.items():
                lanes = [base_lane] if epsilon_label == "epsTT" else [f"{base_lane}_mv"]
                for lane in lanes:
                    run_id = f"multimodel_{cutoff}_v8_{epsilon_label}_{lane}"
                    out_path = CONFIG_DIR / f"{run_id}.yaml"
                    cfg = build_v8_config(template, run_id, epsilon_label, epsilon_value, lane, cutoff)
                    write_yaml(out_path, cfg)
                    generated.append(out_path)
    return generated


def write_placeholder_markdown(path: Path, title: str, body: str) -> None:
    path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build corrected v8 multimodel matrix configs and planning artifacts.")
    ap.add_argument("--date-tag", default="20260401")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    matrix_dir = ensure_dir(matrix_report_dir(args.date_tag))
    ensure_dir(RUNS_DIR)
    ensure_dir(REPORTS_DIR)

    lineage_df, retention_df = build_lineage_and_retention(matrix_dir)
    generated = generate_configs(matrix_dir)
    dep_df = build_dependency_table(generated, matrix_dir)
    plan_df = write_matrix_plan(matrix_dir)

    status_path = matrix_dir / "matrix_status.csv"
    if not status_path.exists():
        with status_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "cutoff", "epsilon", "lane", "run_id", "phase", "status", "started_at", "finished_at",
                "manifest_path", "latest_log_mtime", "disk_free_gb", "note"
            ])
    write_placeholder_markdown(
        matrix_dir / "pilot_summary.md",
        "v8 pilot summary",
        "Pending pilot execution. This file will be updated after the 20211112 epsTT/eps30 pilot closes."
    )
    write_placeholder_markdown(
        matrix_dir / "final_matrix_summary.md",
        "v8 matrix summary",
        "Queue not complete yet. This file is a placeholder until the v8 matrix controller finishes."
    )
    (matrix_dir / "queue.log").touch()

    print(f"matrix_dir={matrix_dir}")
    print(f"generated_configs={len(generated)}")
    print(f"lineage_rows={len(lineage_df)}")
    print(f"retention_rows={len(retention_df)}")
    print(f"dependency_rows={len(dep_df)}")
    print(f"plan_rows={len(plan_df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
