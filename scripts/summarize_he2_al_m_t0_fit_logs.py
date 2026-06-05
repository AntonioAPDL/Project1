#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable

try:
    from audit_he2_al_m_t0_gamsig_cycles import discover_logs, summarize_log
except ModuleNotFoundError:  # pragma: no cover - used when imported as scripts.*
    from scripts.audit_he2_al_m_t0_gamsig_cycles import discover_logs, summarize_log


CUTOFF_RE = re.compile(r"multimodel_(?P<cutoff>\d{8})_")
ERROR_RE = re.compile(r"(Error:|Execution halted|stopped before required gamma/sigma updates)")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def cutoff_from_run_id(run_id: str) -> str:
    match = CUTOFF_RE.search(run_id)
    return match.group("cutoff") if match else ""


def terminal_health_for_log(log_path: Path) -> dict[str, str]:
    q_root = log_path.parent.parent
    path = q_root / "outputs" / "multivar_terminal_state_health.csv"
    if not path.exists():
        return {
            "terminal_health_exists": "false",
            "terminal_violation_n": "",
            "state_norm_sq_per_T": "",
        }
    try:
        rows = read_csv(path)
    except Exception:
        return {
            "terminal_health_exists": "unreadable",
            "terminal_violation_n": "",
            "state_norm_sq_per_T": "",
        }
    violations = sum(1 for row in rows if row.get("status", "") not in ("", "ok"))
    by_metric = {row.get("metric", ""): row for row in rows}
    return {
        "terminal_health_exists": "true",
        "terminal_violation_n": str(violations),
        "state_norm_sq_per_T": by_metric.get("state_norm_sq_per_T", {}).get("value", ""),
    }


def error_tail(log_path: Path) -> str:
    try:
        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return ""
    errors = [line.strip() for line in lines[-400:] if ERROR_RE.search(line)]
    return errors[-1][:180] if errors else ""


def summarize(paths: Iterable[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for log_path in discover_logs(paths):
        cycle = summarize_log(log_path)
        run_id = str(cycle.get("run_id", ""))
        rows.append(
            {
                "cutoff": cutoff_from_run_id(run_id),
                "q": cycle.get("q", ""),
                "iter": cycle.get("last_iter", ""),
                "upd": cycle.get("last_gamsig_update_iters", ""),
                "sigma": cycle.get("last_sigma_exp", ""),
                "gamma": cycle.get("last_gamma_exp", ""),
                "state_norm_sq": cycle.get("last_state_norm_sq", ""),
                "guards": cycle.get("observed_state_guard_count", ""),
                "frozen": cycle.get("last_frozen", ""),
                "two_cycle": cycle.get("two_cycle_suspect", ""),
                "preflight_guard_count": cycle.get("preflight_guard_count", ""),
                **terminal_health_for_log(log_path),
                "error": error_tail(log_path),
                "run_id": run_id,
                "log_path": str(log_path),
            }
        )
    return sorted(rows, key=lambda row: (str(row.get("cutoff", "")), str(row.get("q", ""))))


def write_markdown(path: Path, rows: list[dict[str, object]], title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title}",
        "",
        "| cutoff | q | iter | upd | sigma | gamma | state norm sq | state/T | guards | frozen | two-cycle | term fail | error |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---|",
    ]
    for row in rows:
        err = "yes" if str(row.get("error", "")).strip() else "no"
        lines.append(
            f"| {row.get('cutoff', '')} | {row.get('q', '')} | {row.get('iter', '')} | "
            f"{row.get('upd', '')} | {row.get('sigma', '')} | {row.get('gamma', '')} | "
            f"{row.get('state_norm_sq', '')} | {row.get('state_norm_sq_per_T', '')} | "
            f"{row.get('guards', '')} | {row.get('frozen', '')} | {row.get('two_cycle', '')} | "
            f"{row.get('terminal_violation_n', '')} | {err} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize HE2 AL-M-T0 fit logs into a compact health table.")
    parser.add_argument("--path", type=Path, action="append", required=True, help="Run root, artifact root, or fit.log path.")
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--csv-name", default="fit_log_summary.csv")
    parser.add_argument("--md-name", default="FIT_LOG_SUMMARY.md")
    parser.add_argument("--title", default="HE2 AL-M-T0 Fit-Log Summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = summarize([path.resolve() for path in args.path])
    write_csv(args.report_dir / args.csv_name, rows)
    write_markdown(args.report_dir / args.md_name, rows, args.title)
    print(f"wrote {len(rows)} fit-log summaries to {args.report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
