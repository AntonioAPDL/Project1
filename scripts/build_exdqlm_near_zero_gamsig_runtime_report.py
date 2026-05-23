#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"([A-Za-z0-9_]+)=([^ ]+)")
FATAL_RE = re.compile(r"(^Error\b|Execution halted|Traceback \(most recent call last\))")
CLEANUP_RE = re.compile(r"Post-stage \.RData cleanup: before=(\d+) removed=(\d+) remaining=(\d+)")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def parse_tokens(line: str) -> dict[str, str]:
    return {key: value for key, value in TOKEN_RE.findall(line)}


def q_labels(raw: str) -> list[str]:
    out: list[str] = []
    for piece in re.split(r"[,| ]+", str(raw or "")):
        piece = piece.strip()
        if not piece:
            continue
        if re.fullmatch(r"\d+", piece):
            out.append(f"{int(piece):02d}")
            continue
        num = parse_number(piece)
        if num is not None:
            out.append(f"{int(round(100 * num)):02d}")
    return out


def scan_text(path: Path) -> dict[str, Any]:
    latest_progress: dict[str, str] = {}
    latest_policy: dict[str, str] = {}
    progress_count = 0
    near_zero_fallback_count = 0
    gamsig_guard_count = 0
    state_guard_count = 0
    pseudodata_guard_fail_count = 0
    sampling_preflight_count = 0
    posterior_sampling_count = 0
    fatal_error_count = 0
    tail: list[str] = []
    if not path.exists():
        return {
            "exists": False,
            "latest_progress": latest_progress,
            "latest_policy": latest_policy,
            "progress_count": 0,
            "near_zero_fallback_count": 0,
            "gamsig_guard_count": 0,
            "state_guard_count": 0,
            "pseudodata_guard_fail_count": 0,
            "sampling_preflight_count": 0,
            "posterior_sampling_count": 0,
            "fatal_error_count": 0,
            "tail": [],
        }
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if "[gamsig_policy]" in line:
                latest_policy = parse_tokens(line)
            if "[gamsig_progress]" in line:
                latest_progress = parse_tokens(line)
                progress_count += 1
            if "[gamsig_near_zero_fallback]" in line:
                near_zero_fallback_count += 1
            if "[gamsig_guard]" in line:
                gamsig_guard_count += 1
            if "[state_guard]" in line:
                state_guard_count += 1
            if "[pseudodata_guard_fail]" in line or "[pseudodata_guard_violation]" in line:
                pseudodata_guard_fail_count += 1
            if "sampling_preflight" in line:
                sampling_preflight_count += 1
            if "[sampling_phase]" in line and "posterior" in line:
                posterior_sampling_count += 1
            if FATAL_RE.search(line):
                fatal_error_count += 1
            tail.append(line)
            if len(tail) > 8:
                tail.pop(0)
    return {
        "exists": True,
        "latest_progress": latest_progress,
        "latest_policy": latest_policy,
        "progress_count": progress_count,
        "near_zero_fallback_count": near_zero_fallback_count,
        "gamsig_guard_count": gamsig_guard_count,
        "state_guard_count": state_guard_count,
        "pseudodata_guard_fail_count": pseudodata_guard_fail_count,
        "sampling_preflight_count": sampling_preflight_count,
        "posterior_sampling_count": posterior_sampling_count,
        "fatal_error_count": fatal_error_count,
        "tail": tail,
    }


def scan_cleanup(path: Path) -> dict[str, Any]:
    latest: dict[str, int] = {"before": 0, "removed": 0, "remaining": 0}
    if not path.is_file():
        return {"exists": False, "found": False, **latest}
    found = False
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = CLEANUP_RE.search(line)
            if match is None:
                continue
            found = True
            latest = {
                "before": int(match.group(1)),
                "removed": int(match.group(2)),
                "remaining": int(match.group(3)),
            }
    return {"exists": True, "found": found, **latest}


def lane_row(
    artifact_root: Path,
    plan_row: dict[str, str],
    status_by_run: dict[str, dict[str, str]],
    q: str,
    allow_post_cleaned_rdata: bool,
) -> dict[str, Any]:
    run_id = plan_row["run_id"]
    run_root = Path(plan_row.get("run_root") or artifact_root / "runs" / run_id)
    q_root = run_root / "fit" / "exdqlm_multivar" / "keep" / f"q={int(q):02d}"
    fit_log = q_root / "logs" / "fit.log"
    sampling_log = q_root / "logs" / "sampling_diagnostics.log"
    q_int = int(q)
    rdata = q_root / "outputs" / f"DISC_variables_{q_int}_exAL_synth_DISC.RData"
    health = q_root / "outputs" / "multivar_forecast_health.txt"
    scan = scan_text(fit_log)
    sampling = scan_text(sampling_log)
    latest = scan["latest_progress"]
    policy = scan["latest_policy"]
    status = status_by_run.get(run_id, {})
    cleanup = scan_cleanup(Path(status.get("log_path", "")))
    updates = parse_number(latest.get("gamsig_update_iters"))
    min_updates = parse_number(latest.get("min_update_iters"))
    iter_value = parse_number(latest.get("iter"))
    rdata_available_for_gate = bool(rdata.exists())
    if (
        not rdata_available_for_gate
        and allow_post_cleaned_rdata
        and status.get("status") == "pass"
        and bool(cleanup["found"])
        and int(cleanup["before"]) > 0
        and int(cleanup["removed"]) > 0
        and int(cleanup["remaining"]) == 0
    ):
        rdata_available_for_gate = True
    if rdata.exists():
        rdata_contract = "present"
    elif rdata_available_for_gate:
        rdata_contract = "post_cleaned"
    else:
        rdata_contract = "missing"
    pass_gate = (
        status.get("status") == "pass"
        and rdata_available_for_gate
        and updates is not None
        and min_updates is not None
        and updates >= min_updates
        and int(scan["pseudodata_guard_fail_count"]) == 0
        and int(scan["state_guard_count"]) == 0
        and int(scan["fatal_error_count"]) == 0
    )
    return {
        "package": plan_row.get("package", ""),
        "role": plan_row.get("role", ""),
        "cutoff": plan_row.get("cutoff", ""),
        "q": f"q{int(q):02d}",
        "run_id": run_id,
        "runner_status": status.get("status", ""),
        "runner_phase": status.get("phase", ""),
        "returncode": status.get("returncode", ""),
        "iter": "" if iter_value is None else int(iter_value),
        "gamsig_update_iters": "" if updates is None else int(updates),
        "min_update_iters": "" if min_updates is None else int(min_updates),
        "elbo": latest.get("elbo", ""),
        "crit_elbo": latest.get("crit_elbo", ""),
        "sigma_exp": latest.get("sigma_exp", ""),
        "gamma_exp": latest.get("gamma_exp", ""),
        "state_norm_sq": latest.get("state_norm_sq", ""),
        "near_zero_fallback_count": max(
            int(scan["near_zero_fallback_count"]),
            int(parse_number(latest.get("near_zero_fallback_count")) or 0),
        ),
        "gamsig_guard_count": int(scan["gamsig_guard_count"]),
        "state_guard_count": int(scan["state_guard_count"]),
        "pseudodata_guard_fail_count": int(scan["pseudodata_guard_fail_count"]),
        "fatal_error_count": int(scan["fatal_error_count"]),
        "sampling_preflight_count": int(scan["sampling_preflight_count"]) + int(sampling["sampling_preflight_count"]),
        "posterior_sampling_count": int(scan["posterior_sampling_count"]) + int(sampling["posterior_sampling_count"]),
        "near_zero_fallback_enabled": policy.get("near_zero_fallback_enabled", ""),
        "near_zero_fallback_mode": policy.get("near_zero_fallback_mode", ""),
        "near_zero_gamma_anchor": policy.get("near_zero_gamma_anchor", ""),
        "rdata_exists": rdata.exists(),
        "rdata_contract": rdata_contract,
        "cleanup_log_found": cleanup["found"],
        "cleanup_rdata_before": cleanup["before"],
        "cleanup_rdata_removed": cleanup["removed"],
        "cleanup_rdata_remaining": cleanup["remaining"],
        "forecast_health_exists": health.exists(),
        "pass_gate": pass_gate,
        "fit_log_path": str(fit_log),
        "sampling_log_path": str(sampling_log),
    }


def build_rows(artifact_root: Path, matrix_dir: Path, allow_post_cleaned_rdata: bool = False) -> list[dict[str, Any]]:
    plan_rows = read_csv_rows(matrix_dir / "matrix_plan.csv")
    status_rows = read_csv_rows(matrix_dir / "matrix_status.csv")
    status_by_run = {row.get("run_id", ""): row for row in status_rows if row.get("run_id")}
    rows: list[dict[str, Any]] = []
    for plan_row in plan_rows:
        labels = q_labels(plan_row.get("active_quantiles", ""))
        for q in labels:
            rows.append(lane_row(artifact_root, plan_row, status_by_run, q, allow_post_cleaned_rdata))
    rows.sort(key=lambda row: (str(row["cutoff"]), int(str(row["q"]).replace("q", ""))))
    return rows


def write_readme(path: Path, artifact_root: Path, matrix_dir: Path, rows: list[dict[str, Any]], audited_at: str) -> None:
    passed = sum(1 for row in rows if row["pass_gate"])
    lines = [
        "# exDQLM Near-Zero Gamma/Sigma Runtime Report",
        "",
        f"- audited_at_utc: `{audited_at}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- lanes_passed: `{passed}/{len(rows)}`",
        "",
        "| cutoff | q | role | status | iter | updates | ELBO | sigma | gamma | near0 | gguard | sguard | pseudo | fatal | rdata | gate |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {cutoff} | {q} | {role} | {runner_status} | {iter} | {gamsig_update_iters}/{min_update_iters} | "
            "{elbo} | {sigma_exp} | {gamma_exp} | {near_zero_fallback_count} | {gamsig_guard_count} | "
            "{state_guard_count} | {pseudodata_guard_fail_count} | {fatal_error_count} | {rdata_contract} | "
            "{pass_gate} |".format(**row)
        )
    lines.extend([
        "",
        "Gate definition: runner pass, `.RData` present or verified post-stage `.RData` cleanup when the report is run",
        "with `--allow-post-cleaned-rdata`, terminal gamma/sigma updates meet the configured minimum, no pseudo-data",
        "guard failures, no state-guard events, and no fatal log errors. This is a runtime gate, not a scientific",
        "publication decision.",
        "",
        "Files:",
        "",
        "- `runtime_lane_summary.csv`: parsed lane-level evidence.",
        "- `README.md`: this summary.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a runtime report for near-zero gamma/sigma smoke or repair runs.")
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--allow-post-cleaned-rdata",
        action="store_true",
        help="Accept absent lane .RData only when the unified runner logged successful post-stage cleanup.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_root = args.artifact_root.resolve()
    matrix_dir = args.matrix_dir.resolve()
    out_dir = args.out_dir.resolve()
    rows = build_rows(artifact_root, matrix_dir, allow_post_cleaned_rdata=args.allow_post_cleaned_rdata)
    audited_at = utc_now()
    write_csv(out_dir / "runtime_lane_summary.csv", rows)
    write_readme(out_dir / "README.md", artifact_root, matrix_dir, rows, audited_at)
    print(out_dir / "README.md")
    return 0 if rows and all(row["pass_gate"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
