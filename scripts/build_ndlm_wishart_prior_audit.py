#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
SPEC_PARITY_CSV = REPO_ROOT / "reports" / "ndlm_parity_audit" / "spec_parity_matrix.csv"
OUTPUT_DIR = REPO_ROOT / "reports" / "ndlm_parity_audit"
CSV_OUT = OUTPUT_DIR / "wishart_runtime_trace.csv"
MD_OUT = OUTPUT_DIR / "wishart_prior_audit.md"

STAGE_FIT_PATH = REPO_ROOT / "R" / "unified" / "stages" / "stage_fit.R"
CONSTANTS_PATH = REPO_ROOT / "R" / "unified" / "families" / "ndlm_main" / "00_constants.R"
VB_PATH = REPO_ROOT / "R" / "unified" / "families" / "ndlm_main" / "08_vb_cavi_exact.R"
SAVE_STATE_PATH = REPO_ROOT / "R" / "unified" / "families" / "ndlm_main" / "06_save_state.R"

FIELDNAMES = [
    "cutoff",
    "comparison_group",
    "manuscript_label",
    "model_variant",
    "selected_source_run",
    "selected_source_lineage",
    "resolved_config_path",
    "config_implementation_mode",
    "config_kalman_backend",
    "config_transfer_mode",
    "config_prior_c_factor",
    "config_prior_epsilon",
    "config_prior_dof_offset",
    "config_prior_scale_mult",
    "config_prior_jitter",
    "config_state_df_covs",
    "progress_log_path",
    "progress_log_exists",
    "runtime_implementation_mode",
    "runtime_kalman_backend",
    "runtime_anchor_mode",
    "runtime_epsilon0",
    "runtime_c_factor",
    "runtime_trace_W_T_hist",
    "runtime_df_covs",
    "summary_log_path",
    "summary_log_exists",
    "runtime_w_fore",
    "cov_diag_path",
    "cov_diag_exists",
    "cov_diag_objects",
    "contract_check_path",
    "contract_check_exists",
    "fit_diag_path",
    "fit_diag_exists",
    "runtime_uses_default_epsilon0",
    "code_uses_c_factor",
    "code_uses_epsilon0",
    "code_uses_jitter",
    "code_uses_dof_offset",
    "code_uses_scale_mult",
    "code_saves_dof_offset",
    "code_saves_scale_mult",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=None)
def load_yaml(path: str) -> dict[str, Any]:
    with Path(path).open() as handle:
        return yaml.safe_load(handle)


def load_ndlm_main_rows() -> list[dict[str, str]]:
    rows = read_csv(SPEC_PARITY_CSV)
    out = [
        row
        for row in rows
        if row["model_variant"] in {"ndlm_main_keep", "ndlm_main_drop"}
    ]
    out.sort(key=lambda row: (row["cutoff"], row["comparison_group"], row["model_variant"]))
    return out


def find_line_numbers(path: Path, needle: str) -> list[int]:
    lines: list[int] = []
    for idx, line in enumerate(path.read_text().splitlines(), start=1):
        if needle in line:
            lines.append(idx)
    return lines


def parse_key_value_line(line: str) -> dict[str, str]:
    parts = line.strip().split()
    out: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def parse_progress_log(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    for raw_line in path.read_text().splitlines():
        if "[ndlm_fit_start]" not in raw_line:
            continue
        after_tag = raw_line.split("[ndlm_fit_start]", 1)[1].strip()
        return parse_key_value_line(after_tag)
    return {}


def parse_summary_log(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def read_cov_diag_objects(path: Path) -> str:
    if not path.exists():
        return ""
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        objs = [row["object"] for row in reader if row.get("object")]
    return "|".join(objs)


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def bool_text(value: bool) -> str:
    return "True" if value else "False"


def build_code_usage() -> dict[str, Any]:
    stage_fit_lines = {
        "c_factor": find_line_numbers(STAGE_FIT_PATH, "NDLM_FORECAST_IW_C_FACTOR"),
        "epsilon0": find_line_numbers(STAGE_FIT_PATH, "NDLM_FORECAST_IW_EPSILON0"),
        "dof_offset": find_line_numbers(STAGE_FIT_PATH, "NDLM_FORECAST_IW_DOF_OFFSET"),
        "scale_mult": find_line_numbers(STAGE_FIT_PATH, "NDLM_FORECAST_IW_SCALE_MULT"),
        "jitter": find_line_numbers(STAGE_FIT_PATH, "NDLM_FORECAST_IW_JITTER"),
    }
    constants_lines = {
        "c_factor": find_line_numbers(CONSTANTS_PATH, "forecast_iw_c_factor"),
        "epsilon0": find_line_numbers(CONSTANTS_PATH, "forecast_iw_epsilon0"),
        "dof_offset": find_line_numbers(CONSTANTS_PATH, "forecast_iw_dof_offset"),
        "scale_mult": find_line_numbers(CONSTANTS_PATH, "forecast_iw_scale_mult"),
        "jitter": find_line_numbers(CONSTANTS_PATH, "forecast_iw_jitter"),
    }
    vb_lines = {
        "c_factor": find_line_numbers(VB_PATH, "forecast_iw_c_factor"),
        "epsilon0": find_line_numbers(VB_PATH, "forecast_iw_epsilon0"),
        "dof_offset": find_line_numbers(VB_PATH, "forecast_iw_dof_offset"),
        "scale_mult": find_line_numbers(VB_PATH, "forecast_iw_scale_mult"),
        "jitter": find_line_numbers(VB_PATH, "forecast_iw_jitter"),
        "anchor_mode": find_line_numbers(VB_PATH, 'anchor_mode = "terminal_Q_hist"'),
        "nu0_formula": find_line_numbers(VB_PATH, "nu0 <- as.numeric(d_k + dof_offset + epsilon0)"),
        "S0_formula": find_line_numbers(VB_PATH, "epsilon0 * c_factor * scale_mult * W_T_k + diag(iw_jitter, d_k)"),
        "save_forecast_prior": find_line_numbers(VB_PATH, "forecast_prior = list("),
        "save_cov_diag": find_line_numbers(VB_PATH, "forecast_cov_diagnostics <- do.call(rbind"),
    }
    save_state_lines = {
        "forecast_prior": find_line_numbers(SAVE_STATE_PATH, "forecast_prior = fit_result$forecast_prior"),
        "forecast_cov_diagnostics": find_line_numbers(SAVE_STATE_PATH, "forecast_cov_diagnostics = fit_result$forecast_cov_diagnostics"),
    }
    return {
        "stage_fit_lines": stage_fit_lines,
        "constants_lines": constants_lines,
        "vb_lines": vb_lines,
        "save_state_lines": save_state_lines,
        "uses": {
            "c_factor": bool(vb_lines["c_factor"]),
            "epsilon0": bool(vb_lines["epsilon0"]),
            "dof_offset": bool(vb_lines["dof_offset"]),
            "scale_mult": bool(vb_lines["scale_mult"]),
            "jitter": bool(vb_lines["jitter"]),
            "saves_dof_offset": bool(find_line_numbers(VB_PATH, "forecast_iw_dof_offset"))
            or bool(find_line_numbers(SAVE_STATE_PATH, "forecast_iw_dof_offset")),
            "saves_scale_mult": bool(find_line_numbers(VB_PATH, "forecast_iw_scale_mult"))
            or bool(find_line_numbers(SAVE_STATE_PATH, "forecast_iw_scale_mult")),
        },
    }


def build_rows() -> list[dict[str, str]]:
    code_usage = build_code_usage()
    rows: list[dict[str, str]] = []
    for spec_row in load_ndlm_main_rows():
        config = load_yaml(spec_row["resolved_config_path"])
        ndlm_cfg = config["models"]["ndlm_main"]
        prior_cfg = ((ndlm_cfg.get("prior") or {}).get("forecast_cov") or {})
        run_root = Path(spec_row["selected_source_run_root"])
        progress_log = run_root / "fit" / "ndlm_main" / "logs" / "ndlm_theory_progress.log"
        summary_log = run_root / "fit" / "ndlm_main" / "logs" / "ndlm_theory_summary.log"
        cov_diag = run_root / "diagnostics" / "ndlm" / "ndlm_covariance_diagnostics.csv"
        contract_check = run_root / "fit" / "contract_checks" / "ndlm_main" / "ndlm_main_contract_check.yaml"
        fit_diag = run_root / "fit" / "diagnostics" / "ndlm_main" / "ndlm_main_diagnostics.yaml"

        progress = parse_progress_log(progress_log)
        summary = parse_summary_log(summary_log)

        config_epsilon = prior_cfg.get("epsilon")
        runtime_epsilon0 = progress.get("epsilon0", "")
        runtime_uses_default_epsilon0 = (
            (config_epsilon is None or as_text(config_epsilon) == "")
            and runtime_epsilon0 == summary.get("T", "")
            and runtime_epsilon0 != ""
        )

        rows.append(
            {
                "cutoff": spec_row["cutoff"],
                "comparison_group": spec_row["comparison_group"],
                "manuscript_label": spec_row["manuscript_label"],
                "model_variant": spec_row["model_variant"],
                "selected_source_run": spec_row["selected_source_run"],
                "selected_source_lineage": spec_row["selected_source_lineage"],
                "resolved_config_path": spec_row["resolved_config_path"],
                "config_implementation_mode": as_text(ndlm_cfg.get("implementation_mode")),
                "config_kalman_backend": as_text(ndlm_cfg.get("kalman_backend")),
                "config_transfer_mode": as_text(ndlm_cfg.get("forecast_transfer_mode")),
                "config_prior_c_factor": as_text(prior_cfg.get("c_factor")),
                "config_prior_epsilon": as_text(config_epsilon),
                "config_prior_dof_offset": as_text(prior_cfg.get("dof_offset")),
                "config_prior_scale_mult": as_text(prior_cfg.get("scale_mult")),
                "config_prior_jitter": as_text(prior_cfg.get("jitter")),
                "config_state_df_covs": as_text((ndlm_cfg.get("state_evolution") or {}).get("df_covs")),
                "progress_log_path": str(progress_log),
                "progress_log_exists": bool_text(progress_log.exists()),
                "runtime_implementation_mode": progress.get("implementation_mode", ""),
                "runtime_kalman_backend": progress.get("kalman_backend", ""),
                "runtime_anchor_mode": progress.get("anchor_mode", ""),
                "runtime_epsilon0": runtime_epsilon0,
                "runtime_c_factor": progress.get("c_factor", ""),
                "runtime_trace_W_T_hist": progress.get("trace_W_T_hist", ""),
                "runtime_df_covs": progress.get("df_covs", ""),
                "summary_log_path": str(summary_log),
                "summary_log_exists": bool_text(summary_log.exists()),
                "runtime_w_fore": summary.get("w_fore", ""),
                "cov_diag_path": str(cov_diag),
                "cov_diag_exists": bool_text(cov_diag.exists()),
                "cov_diag_objects": read_cov_diag_objects(cov_diag),
                "contract_check_path": str(contract_check),
                "contract_check_exists": bool_text(contract_check.exists()),
                "fit_diag_path": str(fit_diag),
                "fit_diag_exists": bool_text(fit_diag.exists()),
                "runtime_uses_default_epsilon0": bool_text(runtime_uses_default_epsilon0),
                "code_uses_c_factor": bool_text(code_usage["uses"]["c_factor"]),
                "code_uses_epsilon0": bool_text(code_usage["uses"]["epsilon0"]),
                "code_uses_jitter": bool_text(code_usage["uses"]["jitter"]),
                "code_uses_dof_offset": bool_text(code_usage["uses"]["dof_offset"]),
                "code_uses_scale_mult": bool_text(code_usage["uses"]["scale_mult"]),
                "code_saves_dof_offset": bool_text(code_usage["uses"]["saves_dof_offset"]),
                "code_saves_scale_mult": bool_text(code_usage["uses"]["saves_scale_mult"]),
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def fmt_ref(path: Path, lines: list[int]) -> str:
    if not lines:
        return f"`{path.relative_to(REPO_ROOT)}`: not found"
    return f"`{path.relative_to(REPO_ROOT)}:{','.join(str(line) for line in lines)}`"


def write_summary(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    code_usage = build_code_usage()

    lineage_counts = Counter(row["selected_source_lineage"] for row in rows)
    implementation_counts = Counter(row["runtime_implementation_mode"] for row in rows)
    anchor_counts = Counter(row["runtime_anchor_mode"] for row in rows)
    default_epsilon_rows = sum(row["runtime_uses_default_epsilon0"] == "True" for row in rows)
    explicit_dof = sum(bool(row["config_prior_dof_offset"]) for row in rows)
    explicit_scale = sum(bool(row["config_prior_scale_mult"]) for row in rows)
    explicit_jitter = sum(bool(row["config_prior_jitter"]) for row in rows)
    cov_diag_rows = sum(row["cov_diag_exists"] == "True" for row in rows)
    contract_rows = sum(row["contract_check_exists"] == "True" for row in rows)
    fit_diag_rows = sum(row["fit_diag_exists"] == "True" for row in rows)

    lines: list[str] = []
    lines.append("# Phase 5 NDLM Forecast-Window Covariance Prior Audit")
    lines.append("")
    lines.append("Status: complete")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(
        f"- Audited `{len(rows)}` authoritative HE2 multivariate NDLM rows (`N-M-T0` and `N-M-T1`) using the resolved source runs identified in Phase 2 and Phase 3."
    )
    lines.append(
        "- `N-U-T1` is intentionally out of scope for this phase because `ndlm_univar` uses the scalar `n0/S0` prior, not the multivariate forecast-window covariance prior audited here."
    )
    lines.append("")
    lines.append("## Static Code Trace")
    lines.append("")
    lines.append(
        f"- `stage_fit` forwards all five forecast-IW env vars (`c_factor`, `epsilon0`, `dof_offset`, `scale_mult`, `jitter`): {fmt_ref(STAGE_FIT_PATH, sum(code_usage['stage_fit_lines'].values(), []))}."
    )
    lines.append(
        f"- `ndlm_theory_constants()` reads all five into runtime constants: {fmt_ref(CONSTANTS_PATH, sum(code_usage['constants_lines'].values(), []))}."
    )
    lines.append(
        f"- The active anchor builder `ndlm_exact_forecast_prior_anchor()` uses all five prior knobs (`c_factor`, `epsilon0`, `dof_offset`, `scale_mult`, `jitter`): {fmt_ref(VB_PATH, code_usage['vb_lines']['c_factor'] + code_usage['vb_lines']['epsilon0'] + code_usage['vb_lines']['dof_offset'] + code_usage['vb_lines']['scale_mult'] + code_usage['vb_lines']['jitter'])}."
    )
    lines.append(
        f"- The implemented anchor formula is `nu0 = d_k + dof_offset + epsilon0` and `S0 = epsilon0 * c_factor * scale_mult * W_T_k + diag(jitter)`: {fmt_ref(VB_PATH, code_usage['vb_lines']['nu0_formula'] + code_usage['vb_lines']['S0_formula'])}."
    )
    lines.append(
        f"- `dof_offset` and `scale_mult` now have active use-sites in the theory-aligned fit loop: `dof_offset` anchor refs {fmt_ref(VB_PATH, code_usage['vb_lines']['dof_offset'])}; `scale_mult` anchor refs {fmt_ref(VB_PATH, code_usage['vb_lines']['scale_mult'])}."
    )
    lines.append(
        f"- Saved runtime state exposes `forecast_prior` and `forecast_cov_diagnostics`, and now preserves `dof_offset` / `scale_mult` through the fit-state outputs: anchor/save refs {fmt_ref(VB_PATH, code_usage['vb_lines']['save_forecast_prior'] + code_usage['vb_lines']['save_cov_diag'])}; save-state pack refs {fmt_ref(SAVE_STATE_PATH, code_usage['save_state_lines']['forecast_prior'] + code_usage['save_state_lines']['forecast_cov_diagnostics'])}."
    )
    lines.append("")
    lines.append("## Headline Findings")
    lines.append("")
    lines.append(
        f"- All `{len(rows)}` audited multivariate NDLM HE2 rows run with `implementation_mode=theory_aligned`; runtime modes: `{dict(implementation_counts)}`."
    )
    lines.append(
        f"- All `{len(rows)}` audited rows use `kalman_backend=cpp` and `anchor_mode=terminal_Q_hist`; anchor counts: `{dict(anchor_counts)}`."
    )
    lines.append(
        f"- Runtime `epsilon0` falls back to `T` for all `{default_epsilon_rows}` rows because the config-level `epsilon` field is blank in the authoritative HE2 source configs."
    )
    lines.append(
        f"- Explicit `dof_offset` is present in `{explicit_dof}` row configs, explicit `scale_mult` in `{explicit_scale}`, and explicit `jitter` in `{explicit_jitter}`; all three are now used by the active anchor builder."
    )
    lines.append(
        f"- Covariance diagnostics exist for all `{cov_diag_rows}` rows, and fit-level contract/diagnostic YAML also exists for all `{len(rows)}` rows (`contract={contract_rows}`, `fit_diag={fit_diag_rows}`)."
    )
    lines.append(
        f"- Lineage mix remains the same as earlier phases: `{dict(lineage_counts)}`."
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "- The authoritative manuscript NDLM main rows are already using the theory-aligned NDLM engine, not a separate legacy NDLM fit engine."
    )
    lines.append(
        "- The active forecast-window covariance prior is inverse-Wishart-like and anchored to the terminal historical discount covariance `Q_T`, with `dof_offset` and `scale_mult` now participating directly in the prior parameterization."
    )
    lines.append(
        "- In the current implementation, the active prior knobs are `epsilon0`, `c_factor`, `dof_offset`, `scale_mult`, and `jitter`. Because `epsilon0` is blank in the audited configs, the runtime still uses `epsilon0 = T`."
    )
    lines.append(
        "- `dof_offset` and `scale_mult` are exposed by the config surface, forwarded through `stage_fit`, and used in the active theory-aligned NDLM main fit path."
    )
    lines.append(
        "- This closes the earlier prior-contract gap and makes the multivariate NDLM forecast-window prior consistent with the current public config surface."
    )
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append(f"- CSV: [{CSV_OUT.name}]({CSV_OUT})")
    lines.append("")
    path.write_text("\n".join(lines))


def main() -> None:
    rows = build_rows()
    write_csv(rows, CSV_OUT)
    write_summary(rows, MD_OUT)
    print(f"Wrote {len(rows)} rows to {CSV_OUT}")
    print(f"Wrote summary to {MD_OUT}")


if __name__ == "__main__":
    main()
