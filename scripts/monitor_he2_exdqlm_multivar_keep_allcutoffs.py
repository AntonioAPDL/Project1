#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522"
)
DEFAULT_MATRIX_DIR = DEFAULT_ARTIFACT_ROOT / "control" / "publication_relaunch_matrix"
DEFAULT_OUT_DIR = ROOT / "reports" / "he2_exdqlm_multivar_keep_allcutoffs_fullhistory_promotion_live_20260522"
DEFAULT_DATA_START = "1987-05-29"
DEFAULT_QUANTILES = ["05", "20", "35", "50", "65", "80", "95"]

PROGRESS_RE = re.compile(r"\[gamsig_progress\].*")
TOKEN_RE = re.compile(r"([A-Za-z0-9_]+)=([^ ]+)")
FATAL_RE = re.compile(r"(^Error\b|Execution halted|Traceback \(most recent call last\))")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compact_stamp(iso_utc: str) -> str:
    return iso_utc.replace("-", "").replace(":", "")


def parse_date(value: str) -> datetime:
    value = str(value).strip()
    if re.fullmatch(r"\d{8}", value):
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=timezone.utc)
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def history_length(cutoff: str, data_start: str = DEFAULT_DATA_START) -> int:
    start = parse_date(data_start)
    end = parse_date(cutoff)
    return int((end - start).days) + 1


def iso_mtime(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def format_float(value: Any, digits: int = 6) -> str:
    num = parse_number(value)
    if num is None:
        return ""
    return f"{num:.{digits}g}"


def parse_progress(line: str) -> dict[str, str]:
    return {key: value for key, value in TOKEN_RE.findall(line)}


def parse_quantiles(raw: str | None) -> list[str]:
    if raw is None or not str(raw).strip():
        return list(DEFAULT_QUANTILES)
    pieces = [p.strip() for p in re.split(r"[|, ]+", str(raw)) if p.strip()]
    out: list[str] = []
    for piece in pieces:
        if re.fullmatch(r"\d+", piece):
            out.append(f"{int(piece):02d}")
            continue
        num = parse_number(piece)
        if num is None:
            continue
        if 0 < num < 1:
            out.append(f"{int(round(100 * num)):02d}")
        else:
            out.append(f"{int(round(num)):02d}")
    return sorted(set(out), key=lambda x: int(x)) or list(DEFAULT_QUANTILES)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_yaml_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def read_matrix_plan(matrix_dir: Path) -> list[dict[str, str]]:
    rows = read_csv_rows(matrix_dir / "matrix_plan.csv")
    for row in rows:
        if "cutoff" in row:
            row["cutoff"] = str(row["cutoff"]).zfill(8)
    rows.sort(key=lambda r: (r.get("order_index", ""), r.get("cutoff", ""), r.get("lane", "")))
    return rows


def read_status_by_run_id(matrix_dir: Path) -> dict[str, dict[str, str]]:
    rows = read_csv_rows(matrix_dir / "matrix_status.csv")
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        run_id = str(row.get("run_id", "")).strip()
        if run_id:
            out[run_id] = row
    return out


def scan_log(path: Path) -> dict[str, Any]:
    latest_progress: dict[str, str] = {}
    latest_sampling_phase = ""
    gamsig_guard_count = 0
    gamsig_rollback_count = 0
    latent_parameter_guard_count = 0
    state_guard_count = 0
    pseudodata_guard_event_count = 0
    pseudodata_guard_fail_count = 0
    near_zero_fallback_log_count = 0
    fatal_error_count = 0
    tail: list[str] = []

    if not path.exists():
        return {
            "exists": False,
            "latest_progress": latest_progress,
            "latest_sampling_phase": latest_sampling_phase,
            "gamsig_guard_count": 0,
            "gamsig_rollback_count": 0,
            "latent_parameter_guard_count": 0,
            "state_guard_count": 0,
            "pseudodata_guard_event_count": 0,
            "pseudodata_guard_fail_count": 0,
            "near_zero_fallback_log_count": 0,
            "fatal_error_count": 0,
            "tail": [],
        }

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if PROGRESS_RE.search(line):
                latest_progress = parse_progress(line)
            if line.startswith("[sampling_phase]"):
                latest_sampling_phase = line
            if "[gamsig_guard]" in line:
                gamsig_guard_count += 1
            if "[gamsig_rollback]" in line:
                gamsig_rollback_count += 1
            if "[latent_parameter_guard]" in line:
                latent_parameter_guard_count += 1
            if "[state_guard]" in line:
                state_guard_count += 1
            if "[pseudodata_guard]" in line and "policy" not in line:
                pseudodata_guard_event_count += 1
            if ("[pseudodata_guard_fail]" in line) or ("[pseudodata_guard_violation]" in line):
                pseudodata_guard_fail_count += 1
            if "[gamsig_near_zero_fallback]" in line:
                near_zero_fallback_log_count += 1
            if FATAL_RE.search(line):
                fatal_error_count += 1
            tail.append(line)
            if len(tail) > 8:
                tail.pop(0)

    return {
        "exists": True,
        "latest_progress": latest_progress,
        "latest_sampling_phase": latest_sampling_phase,
        "gamsig_guard_count": gamsig_guard_count,
        "gamsig_rollback_count": gamsig_rollback_count,
        "latent_parameter_guard_count": latent_parameter_guard_count,
        "state_guard_count": state_guard_count,
        "pseudodata_guard_event_count": pseudodata_guard_event_count,
        "pseudodata_guard_fail_count": pseudodata_guard_fail_count,
        "near_zero_fallback_log_count": near_zero_fallback_log_count,
        "fatal_error_count": fatal_error_count,
        "tail": tail,
    }


def run_cleanup_snapshot(
    artifact_root: Path,
    run_id: str,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if run_id in cache:
        return cache[run_id]

    run_root = artifact_root / "runs" / run_id
    manifest = load_yaml_optional(run_root / "run_manifest.yaml")
    cleanup_after_post = ((manifest.get("rdata_cleanup") or {}).get("after_post") or {})
    fit_root = run_root / "fit" / "exdqlm_multivar" / "keep"
    if fit_root.exists():
        run_rdata_count = (
            len(list(fit_root.glob("q=*/outputs/*.RData")))
            + len(list(fit_root.glob("q=*/outputs/*.rda")))
        )
    else:
        run_rdata_count = 0

    snapshot = {
        "run_root": run_root,
        "cleanup_before": cleanup_after_post.get("before", ""),
        "cleanup_removed": cleanup_after_post.get("removed", ""),
        "cleanup_remaining": cleanup_after_post.get("remaining", ""),
        "run_rdata_count": run_rdata_count,
    }
    cache[run_id] = snapshot
    return snapshot


def lane_snapshot(
    artifact_root: Path,
    run_row: dict[str, str],
    matrix_status: dict[str, str],
    q_label: str,
    data_start: str,
    run_cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    run_id = run_row["run_id"]
    cutoff = str(run_row["cutoff"]).zfill(8)
    q_int = int(q_label)
    if run_cache is None:
        run_cache = {}
    cleanup = run_cleanup_snapshot(artifact_root, run_id, run_cache)
    run_root = cleanup["run_root"]
    cleanup_before = cleanup["cleanup_before"]
    cleanup_removed = cleanup["cleanup_removed"]
    cleanup_remaining = cleanup["cleanup_remaining"]
    run_rdata_count = cleanup["run_rdata_count"]
    q_root = run_root / "fit" / "exdqlm_multivar" / "keep" / f"q={q_label}"
    log_path = q_root / "logs" / "fit.log"
    sampling_diag_path = q_root / "logs" / "sampling_diagnostics.log"
    rdata_path = q_root / "outputs" / f"DISC_variables_{q_int}_exAL_synth_DISC.RData"
    health_path = q_root / "outputs" / "multivar_forecast_health.txt"
    scan = scan_log(log_path)
    sampling_scan = scan_log(sampling_diag_path)
    latest = scan["latest_progress"] if isinstance(scan["latest_progress"], dict) else {}
    hist_len = history_length(cutoff, data_start=data_start)
    state_norm_sq = parse_number(latest.get("state_norm_sq"))
    state_norm_sq_per_history_day = state_norm_sq / hist_len if state_norm_sq is not None and hist_len > 0 else None
    sqrt_state_norm_over_history_len = (
        math.sqrt(state_norm_sq) / hist_len
        if state_norm_sq is not None and state_norm_sq >= 0 and hist_len > 0
        else None
    )
    progress_near_zero_count = parse_number(latest.get("near_zero_fallback_count"))
    near_zero_fallback_count = max(
        int(scan["near_zero_fallback_log_count"]),
        int(progress_near_zero_count) if progress_near_zero_count is not None else 0,
    )
    stage = matrix_status.get("phase", "not_started")
    status = matrix_status.get("status", "not_started")
    if rdata_path.exists():
        output_state = "rdata_present"
    elif status == "pass" and str(cleanup_remaining) == "0":
        output_state = "post_cleaned"
    elif status == "pass":
        output_state = "post_cleaned_or_absent"
    elif log_path.exists():
        output_state = "fit_or_post_pending"
    else:
        output_state = "missing"
    pseudodata_total = int(scan["pseudodata_guard_event_count"]) + int(scan["pseudodata_guard_fail_count"])
    if int(scan["fatal_error_count"]) > 0:
        failure_layer = "fatal"
    elif int(scan["pseudodata_guard_fail_count"]) > 0:
        failure_layer = "pseudodata"
    elif int(scan["gamsig_rollback_count"]) > 0:
        failure_layer = "gamma_sigma_guarded"
    elif int(scan["latent_parameter_guard_count"]) > 0:
        failure_layer = "latent_boundary"
    elif status == "pass":
        failure_layer = "none"
    else:
        failure_layer = "pending"

    return {
        "cutoff": cutoff,
        "grid_spec_id": str(run_row.get("grid_spec_id", run_row.get("epsilon", ""))),
        "epsilon_label": str(run_row.get("epsilon", "")),
        "q": f"q{q_label}",
        "run_id": run_id,
        "stage": stage,
        "status": status,
        "fit_log_exists": log_path.exists(),
        "fit_log_mtime_utc": iso_mtime(log_path),
        "iter": latest.get("iter", ""),
        "updates": latest.get("gamsig_update_iters", ""),
        "elbo": latest.get("elbo", ""),
        "d_elbo": latest.get("crit_elbo", ""),
        "sigma_exp": latest.get("sigma_exp", ""),
        "gamma_exp": latest.get("gamma_exp", ""),
        "state_norm_sq": latest.get("state_norm_sq", ""),
        "history_len_to_cutoff": hist_len,
        "state_norm_sq_per_history_day": "" if state_norm_sq_per_history_day is None else f"{state_norm_sq_per_history_day:.12g}",
        "sqrt_state_norm_over_history_len": (
            "" if sqrt_state_norm_over_history_len is None else f"{sqrt_state_norm_over_history_len:.12g}"
        ),
        "frozen": latest.get("frozen", ""),
        "guard_count": int(scan["gamsig_guard_count"]) + int(scan["state_guard_count"]) + int(scan["gamsig_rollback_count"]),
        "gamsig_guard_count": int(scan["gamsig_guard_count"]),
        "gamsig_rollback_count": int(scan["gamsig_rollback_count"]),
        "latent_parameter_guard_count": int(scan["latent_parameter_guard_count"]),
        "state_guard_count": int(scan["state_guard_count"]),
        "pseudodata_guard_event_count": int(scan["pseudodata_guard_event_count"]),
        "pseudodata_guard_fail_count": int(scan["pseudodata_guard_fail_count"]),
        "pseudodata_guard_total_count": pseudodata_total,
        "near_zero_fallback_count": near_zero_fallback_count,
        "near_zero_fallback_log_count": int(scan["near_zero_fallback_log_count"]),
        "fatal_error_count": int(scan["fatal_error_count"]),
        "rdata_exists": rdata_path.exists(),
        "forecast_health_exists": health_path.exists(),
        "sampling_diag_exists": sampling_diag_path.exists(),
        "latest_sampling_phase": sampling_scan["latest_sampling_phase"] or scan["latest_sampling_phase"],
        "output_state": output_state,
        "failure_layer": failure_layer,
        "run_rdata_count": run_rdata_count,
        "rdata_cleanup_after_post_before": cleanup_before,
        "rdata_cleanup_after_post_removed": cleanup_removed,
        "rdata_cleanup_after_post_remaining": cleanup_remaining,
        "fit_log_path": str(log_path),
    }


def build_snapshot_rows(artifact_root: Path, matrix_dir: Path, data_start: str) -> list[dict[str, Any]]:
    matrix_plan = read_matrix_plan(matrix_dir)
    status_by_run_id = read_status_by_run_id(matrix_dir)
    rows: list[dict[str, Any]] = []
    run_cache: dict[str, dict[str, Any]] = {}
    for run_row in matrix_plan:
        run_id = run_row.get("run_id", "")
        if not run_id:
            continue
        q_labels = parse_quantiles(run_row.get("active_quantiles"))
        matrix_status = status_by_run_id.get(run_id, {})
        for q_label in q_labels:
            rows.append(lane_snapshot(
                artifact_root,
                run_row,
                matrix_status,
                q_label,
                data_start=data_start,
                run_cache=run_cache,
            ))
    rows.sort(key=lambda r: (str(r["cutoff"]), str(r.get("grid_spec_id", "")), int(str(r["q"]).replace("q", ""))))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], append: bool = False) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]], audited_at: str, artifact_root: Path, matrix_dir: Path) -> None:
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[str(row.get("status", ""))] = status_counts.get(str(row.get("status", "")), 0) + 1
    counts = ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items())) or "none"
    lines = [
        "# Live exDQLM Multivar Keep All-Cutoff Monitor",
        "",
        f"- audited_at_utc: `{audited_at}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- lane_status_counts: `{counts}`",
        "",
        "| cutoff | spec | q | stage/status | iter | upd | ELBO | sigma | gamma | sqrt(state)/T | state/T | roll | latent | pseudo | fatal | output | layer |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {cutoff} | {grid_spec_id} | {q} | {stage}/{status} | {iter} | {updates} | {elbo} | "
            "{sigma_exp} | {gamma_exp} | {sqrt_state_norm_over_history_len} | {state_norm_sq_per_history_day} | {gamsig_rollback_count} | "
            "{latent_parameter_guard_count} | {pseudodata_guard_total_count} | {fatal_error_count} | "
            "{output_state} | {failure_layer} |".format(**row)
        )
    lines.append("")
    lines.append("`sqrt(state)/T` is `sqrt(state_norm_sq)` divided by the history length through the cutoff date.")
    lines.append("`state/T` is `state_norm_sq` divided by the history length through the cutoff date, retained for backward comparison.")
    lines.append("`roll`, `latent`, and `pseudo` count gamma/sigma rollbacks, latent-parameter guards, and pseudo-data guard events.")
    lines.append("This monitor is read-only: it parses logs/manifests and writes report files only.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def matrix_terminal(matrix_dir: Path) -> bool:
    rows = read_csv_rows(matrix_dir / "matrix_status.csv")
    if not rows:
        return False
    statuses = {str(row.get("status", "")).lower() for row in rows}
    return bool(statuses) and statuses.issubset({"pass", "fail"})


def refresh_matrix_status(matrix_dir: Path, artifact_root: Path) -> None:
    subprocess.run(
        [
            "python3",
            "scripts/check_multimodel_v8_matrix_health.py",
            "--matrix-dir",
            str(matrix_dir),
            "--artifact-root",
            str(artifact_root),
        ],
        cwd=ROOT,
        check=True,
    )


def snapshot(args: argparse.Namespace) -> Path:
    artifact_root = Path(args.artifact_root).resolve()
    matrix_dir = Path(args.matrix_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    if args.refresh_matrix:
        refresh_matrix_status(matrix_dir, artifact_root)
    audited_at = utc_now()
    rows = build_snapshot_rows(artifact_root, matrix_dir, data_start=args.data_start)
    rows_with_time = [dict(audited_at_utc=audited_at, **row) for row in rows]
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "live_status_latest.csv", rows_with_time, append=False)
    write_csv(out_dir / "live_status_history.csv", rows_with_time, append=True)
    write_markdown(out_dir / "LIVE_STATUS.md", rows, audited_at=audited_at, artifact_root=artifact_root, matrix_dir=matrix_dir)
    snapshot_dir = out_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "audited_at_utc": audited_at,
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "rows": rows,
    }
    (snapshot_dir / f"summary_{compact_stamp(audited_at)}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_dir / "LIVE_STATUS.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only all-cutoff live monitor for HE2 exDQLM multivar keep.")
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--matrix-dir", default=str(DEFAULT_MATRIX_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--data-start", default=DEFAULT_DATA_START)
    parser.add_argument("--interval", type=float, default=300.0)
    parser.add_argument("--max-snapshots", type=int, default=288)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--refresh-matrix", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    count = 0
    while True:
        latest = snapshot(args)
        print(f"{utc_now()} wrote {latest}", flush=True)
        count += 1
        if args.once:
            return 0
        if matrix_terminal(Path(args.matrix_dir)):
            return 0
        if count >= args.max_snapshots:
            return 0
        time.sleep(max(float(args.interval), 1.0))


if __name__ == "__main__":
    raise SystemExit(main())
