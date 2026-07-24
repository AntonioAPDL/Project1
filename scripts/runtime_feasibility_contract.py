#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RUNTIME_MANIFEST_REL = "artifacts/runtime_benchmark/runtime_manifest.json"
RUNTIME_CONTRACT_REL = "docs/he1_runtime_feasibility_contract_20260615.md"
ARTICLE_RUNTIME_DOC_REL = "docs/runtime_benchmark_contract.md"

RUNTIME_SOURCE_ROOT = (
    "/data/jaguir26/local/src/exdqlm__wt__shared_fitforecast_v2_1p0p0/"
    "validation/fitforecast_v2/runs/"
    "20260515_exdqlm_dqlm_dynamic_fitforecast_v2_orchestrated_3500202605200353075941"
)
RUNTIME_INTERFACE_REL = "interfaces/exdqlm_dqlm_dynamic_fitforecast_v2_shared_interface.csv"

TOTAL_RUNTIME_COLUMNS = ["runtime_sec_total", "runtime_sec"]
MOSTLY_MISSING_DECOMPOSITION_COLUMNS = ["runtime_sec_fit", "runtime_sec_forecast"]

REQUIRED_RUNTIME_ARTICLE_CLAIMS = [
    "seven quantile-specific models used in the application to be fitted in parallel",
    "can be refit on operational time scales",
    "once observations, retrospective products, forecast products, and forecast covariates have been staged",
]

REQUIRED_RUNTIME_CORRECTIONS_CLAIMS = [
    "about two hours end-to-end",
    r"\texttt{runtime\_sec\_total}",
    r"\texttt{runtime\_sec}",
    "54 completed and 18 pending planned run units",
    "do not support a separate fitting/forecasting decomposition",
]

FORBIDDEN_RUNTIME_DECOMPOSITION_CLAIMS = [
    "100 minutes for fitting",
    "100 minutes for fit",
    "20 minutes for post-processing",
    "20 minutes for postprocessing",
    "runtime_sec_fit and runtime_sec_forecast were used",
]


@dataclass(frozen=True)
class RuntimeManifestCheck:
    item: str
    ok: bool
    detail: str


def _nested(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def check_runtime_manifest(data: dict[str, Any]) -> list[RuntimeManifestCheck]:
    source_root = _nested(data, "source", "source_root")
    interface_rel = _nested(data, "source", "interface_csv_relative_path")
    interface_rows = _nested(data, "interface_table", "row_count")
    interface_cols = _nested(data, "interface_table", "column_count")
    interface_status = _nested(data, "interface_table", "status_summary")
    total_columns = _nested(data, "interface_table", "practical_total_runtime_columns") or []
    missing_columns = _nested(data, "interface_table", "mostly_missing_decomposition_columns") or []
    planned = _nested(data, "planned_run_manifest", "planned_run_units")
    done = _nested(data, "planned_run_manifest", "done")
    pending = _nested(data, "planned_run_manifest", "pending")
    runtime_hours = _nested(data, "benchmark", "representative_end_to_end_runtime_hours_approx")
    core_count = _nested(data, "benchmark", "hardware", "core_count")
    memory_gib = _nested(data, "benchmark", "hardware", "memory_gib_approx")
    decomposition = _nested(data, "claims_policy", "report_fit_forecast_decomposition")
    scope = str(_nested(data, "claims_policy", "valid_scope") or "")

    return [
        RuntimeManifestCheck("schema_version", data.get("schema_version") == "he1_runtime_benchmark_v1", str(data.get("schema_version", ""))),
        RuntimeManifestCheck("source_root", source_root == RUNTIME_SOURCE_ROOT, str(source_root)),
        RuntimeManifestCheck("interface_csv_relative_path", interface_rel == RUNTIME_INTERFACE_REL, str(interface_rel)),
        RuntimeManifestCheck("interface_shape", interface_rows == 1620 and interface_cols == 127, f"{interface_rows} x {interface_cols}"),
        RuntimeManifestCheck("interface_status", interface_status == "all 1620 interface rows are done", str(interface_status)),
        RuntimeManifestCheck("total_runtime_columns", total_columns == TOTAL_RUNTIME_COLUMNS, str(total_columns)),
        RuntimeManifestCheck("decomposition_columns_marked_missing", missing_columns == MOSTLY_MISSING_DECOMPOSITION_COLUMNS, str(missing_columns)),
        RuntimeManifestCheck("planned_counts", planned == 72 and done == 54 and pending == 18, f"planned={planned}, done={done}, pending={pending}"),
        RuntimeManifestCheck("runtime_hours", runtime_hours == 2.0, str(runtime_hours)),
        RuntimeManifestCheck("hardware_context", core_count == 64 and memory_gib == 503, f"cores={core_count}, memory_gib={memory_gib}"),
        RuntimeManifestCheck("no_runtime_decomposition", decomposition is False, str(decomposition)),
        RuntimeManifestCheck("scope_completed_outputs", "completed measured validation outputs" in scope, scope),
    ]
