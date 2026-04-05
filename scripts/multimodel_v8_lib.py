#!/usr/bin/env python3
from __future__ import annotations

import copy
import os
import re
import shutil
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
INPUT_SOURCE_ROOT = Path(os.environ.get("MULTIMODEL_V8_INPUT_SOURCE_ROOT", ROOT))
DEFAULT_ARTIFACT_ROOT = ROOT / "repro"
DEFAULT_RUNS_DIR = DEFAULT_ARTIFACT_ROOT / "runs"
DEFAULT_REPORTS_DIR = DEFAULT_ARTIFACT_ROOT / "reports"
RUNS_DIR = DEFAULT_RUNS_DIR
REPORTS_DIR = DEFAULT_REPORTS_DIR
CONFIG_DIR = ROOT / "config" / "unified_runs"

CUTOFFS: list[tuple[str, str]] = [
    ("20210123", "2021-01-23"),
    ("20211112", "2021-11-12"),
    ("20211221", "2021-12-21"),
    ("20220511", "2022-05-11"),
    ("20221225", "2022-12-25"),
]
CUTOFF_TO_DATE = OrderedDict(CUTOFFS)
DATE_TO_CUTOFF = {v: k for k, v in CUTOFFS}
ORDINARY_CUTOFFS = [c for c, _ in CUTOFFS if c != "20221225"]
HEAVY_CUTOFF = "20221225"

FORECATS_BUNDLE_BY_CUTOFF: "OrderedDict[str, Path]" = OrderedDict([
    (
        "20210123",
        INPUT_SOURCE_ROOT / "data" / "forecats_inputs" / "site=11160500" / "cutoff_date=2021-01-23" /
        "run_id=20260305_single_retro_policy_pre1080_gapfix_r01" / "meta.yaml",
    ),
    (
        "20211112",
        INPUT_SOURCE_ROOT / "data" / "forecats_inputs" / "site=11160500" / "cutoff_date=2021-11-12" /
        "run_id=20260219_single_retro_policy_pre1080_r01" / "meta.yaml",
    ),
    (
        "20211221",
        INPUT_SOURCE_ROOT / "data" / "forecats_inputs" / "site=11160500" / "cutoff_date=2021-12-21" /
        "run_id=20260219_single_retro_policy_pre1080_r01" / "meta.yaml",
    ),
    (
        "20220511",
        INPUT_SOURCE_ROOT / "data" / "forecats_inputs" / "site=11160500" / "cutoff_date=2022-05-11" /
        "run_id=20260219_single_retro_policy_pre1080_r01" / "meta.yaml",
    ),
    (
        "20221225",
        INPUT_SOURCE_ROOT / "data" / "forecats_inputs" / "site=11160500" / "cutoff_date=2022-12-25" /
        "run_id=20260404_single_retro_policy_pre1080_gapfix_r01" / "meta.yaml",
    ),
])

FALLBACK_INPUTS = {
    "retros_path": INPUT_SOURCE_ROOT / "retros_2022-12-25.csv",
    "retros_storage_scale": "log1p_cms",
    "nws_forecast_path": INPUT_SOURCE_ROOT / "nws_forecast.csv",
    "nws_storage_scale": "raw_cms",
    "glofas_forecast_path": INPUT_SOURCE_ROOT / "weighted_time_series.csv",
    "glofas_storage_scale": "raw_cms",
}

AUTHORITATIVE_V7_BUNDLE_NAMES = [
    "multimodel_20210123_v7_compare_alfix_20260331",
    "multimodel_20211112_v7_compare_alfix_20260331",
    "multimodel_20211221_v7_compare_alfix_20260331",
    "multimodel_20220511_v7_compare_alfix_20260331",
    "multimodel_20221225_v7_compare_alfix_20260331",
]

EPSILON_LABEL_TO_VALUE: "OrderedDict[str, float | None]" = OrderedDict([
    ("epsTT", None),
    ("eps30", 30.0),
    ("eps90", 90.0),
    ("eps180", 180.0),
    ("eps360", 360.0),
])
NON_TT_EPSILON_LABELS = [label for label in EPSILON_LABEL_TO_VALUE if label != "epsTT"]

HISTORICAL_SUFFIX_TO_EPSILON: "OrderedDict[str, float | None]" = OrderedDict([
    ("", None),
    ("_v2", 30.0),
    ("_v3", 90.0),
    ("_v4", 30.0),
    ("_v5", 180.0),
    ("_v6", 360.0),
])

TARGET_MODELS = [
    {"model_id": "exdqlm_univar_synth", "model_variant": "exdqlm_univar", "transfer_mode": "", "baseline_lane": "l2", "epsilon_sensitive": False},
    {"model_id": "dqlm_univar_al_synth", "model_variant": "dqlm_univar_al", "transfer_mode": "", "baseline_lane": "l1", "epsilon_sensitive": False},
    {"model_id": "exdqlm_multivar_synth_drop", "model_variant": "exdqlm_multivar_drop", "transfer_mode": "drop", "baseline_lane": "l2", "epsilon_sensitive": True},
    {"model_id": "exdqlm_multivar_synth_keep", "model_variant": "exdqlm_multivar_keep", "transfer_mode": "keep", "baseline_lane": "l2", "epsilon_sensitive": True},
    {"model_id": "dqlm_multivar_al_synth_drop", "model_variant": "dqlm_multivar_al_drop", "transfer_mode": "drop", "baseline_lane": "l1", "epsilon_sensitive": True},
    {"model_id": "dqlm_multivar_al_synth_keep", "model_variant": "dqlm_multivar_al_keep", "transfer_mode": "keep", "baseline_lane": "l1", "epsilon_sensitive": True},
    {"model_id": "ndlm_main_synth_drop", "model_variant": "ndlm_main_drop", "transfer_mode": "drop", "baseline_lane": "l2", "epsilon_sensitive": False},
    {"model_id": "ndlm_main_synth_keep", "model_variant": "ndlm_main_keep", "transfer_mode": "keep", "baseline_lane": "l1", "epsilon_sensitive": False},
    {"model_id": "ndlm_univar_synth_keep", "model_variant": "ndlm_univar_keep", "transfer_mode": "keep", "baseline_lane": "l1", "epsilon_sensitive": False},
]
TARGET_MODEL_IDS = [row["model_id"] for row in TARGET_MODELS]
ENSEMBLE_IDS = {"glofas_ensemble", "nws_nwm_ensemble"}

INVARIANT_MODEL_IDS = {row["model_id"] for row in TARGET_MODELS if not row["epsilon_sensitive"]}
EPSILON_SENSITIVE_MODEL_IDS = {row["model_id"] for row in TARGET_MODELS if row["epsilon_sensitive"]}


@dataclass(frozen=True)
class LanePlan:
    cutoff: str
    epsilon_label: str
    epsilon_value: float | None
    lane: str
    run_scope: str
    run_id: str
    config_path: Path
    priority_group: int
    max_concurrent_class: str


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_artifact_root(artifact_root: str | Path | None = None) -> Path:
    raw = artifact_root or os.environ.get("MULTIMODEL_V8_ARTIFACT_ROOT")
    if raw is None or str(raw).strip() == "":
        return DEFAULT_ARTIFACT_ROOT
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def runs_dir(artifact_root: str | Path | None = None) -> Path:
    return resolve_artifact_root(artifact_root) / "runs"


def reports_dir(artifact_root: str | Path | None = None) -> Path:
    return resolve_artifact_root(artifact_root) / "reports"


def control_dir(artifact_root: str | Path | None = None) -> Path:
    return resolve_artifact_root(artifact_root) / "control"


def artifact_disk_free_gb(artifact_root: str | Path | None = None) -> float:
    probe = resolve_artifact_root(artifact_root)
    if not probe.exists():
        probe = probe.parent
    return round(shutil.disk_usage(probe).free / (1024 ** 3), 1)


def load_yaml(path: Path, retries: int = 5, delay_seconds: float = 0.2) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            if not isinstance(data, dict):
                raise ValueError(f"YAML root is not a mapping: {path}")
            return data
        except (yaml.YAMLError, ValueError) as err:
            last_err = err
            if attempt == retries - 1:
                break
            time.sleep(delay_seconds)
    assert last_err is not None
    raise last_err


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, default_flow_style=False)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def deep_copy_dict(data: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(data)


def v7_template_config_path(cutoff: str, lane: str) -> Path:
    if lane not in {"l1", "l2"}:
        raise ValueError(f"Unsupported template lane: {lane}")
    return CONFIG_DIR / f"multimodel_{cutoff}_v7_{lane}.yaml"


def v8_run_id(cutoff: str, epsilon_label: str, lane: str) -> str:
    if lane not in {"l1", "l2", "l1_mv", "l2_mv"}:
        raise ValueError(f"Unsupported v8 lane: {lane}")
    suffix = lane
    return f"multimodel_{cutoff}_v8_{epsilon_label}_{suffix}"


def v8_config_path(cutoff: str, epsilon_label: str, lane: str) -> Path:
    return CONFIG_DIR / f"{v8_run_id(cutoff, epsilon_label, lane)}.yaml"


def v8_compare_dir(cutoff: str, epsilon_label: str, artifact_root: str | Path | None = None) -> Path:
    return reports_dir(artifact_root) / f"multimodel_{cutoff}_v8_{epsilon_label}_compare"


def matrix_report_dir(date_tag: str, artifact_root: str | Path | None = None) -> Path:
    return reports_dir(artifact_root) / f"multimodel_v8_matrix_{date_tag}"


def lane_label_for_bundle(epsilon_label: str, lane: str) -> str:
    return f"v8_{epsilon_label}_{lane}"


def latest_mtime(paths: Iterable[Path]) -> str:
    mtimes = [p.stat().st_mtime for p in paths if p.exists()]
    if not mtimes:
        return ""
    import datetime as _dt
    return _dt.datetime.utcfromtimestamp(max(mtimes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_epsilon_spec_list(specs: Iterable[str] | None = None) -> "OrderedDict[str, float | None]":
    if not specs:
        return OrderedDict(EPSILON_LABEL_TO_VALUE)
    out: "OrderedDict[str, float | None]" = OrderedDict()
    for raw_spec in specs:
        spec = str(raw_spec).strip()
        if not spec:
            continue
        if "=" in spec:
            label, raw_value = spec.split("=", 1)
            label = label.strip()
            raw_value = raw_value.strip()
            if raw_value.lower() in {"tt", "none", "null"}:
                value = None
            else:
                value = float(raw_value)
            out[label] = value
            continue
        if spec in EPSILON_LABEL_TO_VALUE:
            out[spec] = EPSILON_LABEL_TO_VALUE[spec]
            continue
        match = re.fullmatch(r"eps(\d+(?:\.\d+)?)", spec)
        if match:
            out[spec] = float(match.group(1))
            continue
        raise ValueError(f"Unsupported epsilon spec: {raw_spec}")
    return out


def build_lane_plan_rows(
    cutoffs: Iterable[str] | None = None,
    epsilon_map: "OrderedDict[str, float | None] | None" = None,
    include_tt: bool = True,
) -> list[LanePlan]:
    cutoff_list = [str(c) for c in (cutoffs or [cutoff for cutoff, _ in CUTOFFS])]
    epsilon_map = OrderedDict(epsilon_map or EPSILON_LABEL_TO_VALUE)
    non_tt_labels = [label for label in epsilon_map if label != "epsTT"]
    rows: list[LanePlan] = []
    order = 0
    # Ordinary TT full baselines first.
    for cutoff in [c for c in cutoff_list if c != HEAVY_CUTOFF]:
        if include_tt and "epsTT" in epsilon_map:
            for lane in ("l1", "l2"):
                order += 1
                rows.append(LanePlan(
                    cutoff=cutoff,
                    epsilon_label="epsTT",
                    epsilon_value=None,
                    lane=lane,
                    run_scope="full_tt",
                    run_id=v8_run_id(cutoff, "epsTT", lane),
                    config_path=v8_config_path(cutoff, "epsTT", lane),
                    priority_group=1,
                    max_concurrent_class="ordinary",
                ))
    # Ordinary epsilon-specific multivar reruns.
    for cutoff in [c for c in cutoff_list if c != HEAVY_CUTOFF]:
        for eps_label in non_tt_labels:
            for lane in ("l1_mv", "l2_mv"):
                order += 1
                rows.append(LanePlan(
                    cutoff=cutoff,
                    epsilon_label=eps_label,
                    epsilon_value=epsilon_map[eps_label],
                    lane=lane,
                    run_scope="multivar_only",
                    run_id=v8_run_id(cutoff, eps_label, lane),
                    config_path=v8_config_path(cutoff, eps_label, lane),
                    priority_group=2,
                    max_concurrent_class="ordinary",
                ))
    # Heavy cutoff TT alone.
    if HEAVY_CUTOFF in cutoff_list and include_tt and "epsTT" in epsilon_map:
        for lane in ("l1", "l2"):
            order += 1
            rows.append(LanePlan(
                cutoff=HEAVY_CUTOFF,
                epsilon_label="epsTT",
                epsilon_value=None,
                lane=lane,
                run_scope="full_tt",
                run_id=v8_run_id(HEAVY_CUTOFF, "epsTT", lane),
                config_path=v8_config_path(HEAVY_CUTOFF, "epsTT", lane),
                priority_group=3,
                max_concurrent_class="heavy",
            ))
    # Heavy cutoff epsilon-specific lanes one at a time.
    if HEAVY_CUTOFF in cutoff_list:
        for eps_label in non_tt_labels:
            for lane in ("l1_mv", "l2_mv"):
                order += 1
                rows.append(LanePlan(
                    cutoff=HEAVY_CUTOFF,
                    epsilon_label=eps_label,
                    epsilon_value=epsilon_map[eps_label],
                    lane=lane,
                    run_scope="multivar_only",
                    run_id=v8_run_id(HEAVY_CUTOFF, eps_label, lane),
                    config_path=v8_config_path(HEAVY_CUTOFF, eps_label, lane),
                    priority_group=4,
                    max_concurrent_class="heavy",
                ))
    return rows


def pilot_lane_plan_rows() -> list[LanePlan]:
    cutoff = "20211112"
    return [
        LanePlan(cutoff, "epsTT", None, "l1", "full_tt", v8_run_id(cutoff, "epsTT", "l1"), v8_config_path(cutoff, "epsTT", "l1"), 1, "ordinary"),
        LanePlan(cutoff, "epsTT", None, "l2", "full_tt", v8_run_id(cutoff, "epsTT", "l2"), v8_config_path(cutoff, "epsTT", "l2"), 1, "ordinary"),
        LanePlan(cutoff, "eps30", 30.0, "l1_mv", "multivar_only", v8_run_id(cutoff, "eps30", "l1_mv"), v8_config_path(cutoff, "eps30", "l1_mv"), 2, "ordinary"),
        LanePlan(cutoff, "eps30", 30.0, "l2_mv", "multivar_only", v8_run_id(cutoff, "eps30", "l2_mv"), v8_config_path(cutoff, "eps30", "l2_mv"), 2, "ordinary"),
    ]
