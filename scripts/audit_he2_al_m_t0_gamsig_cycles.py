#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROGRESS_RE = re.compile(
    r"\[gamsig_progress\].*?"
    r"p0=(?P<p0>[-+0-9.eE]+).*?"
    r"iter=(?P<iter>\d+).*?"
    r"elbo=(?P<elbo>[-+0-9.eE]+|NA).*?"
    r"sigma_exp=(?P<sigma_exp>[-+0-9.eE]+|NA).*?"
    r"gamma_exp=(?P<gamma_exp>[-+0-9.eE]+|NA).*?"
    r"state_norm_sq=(?P<state_norm_sq>[-+0-9.eE]+|NA).*?"
    r"gamsig_update_iters=(?P<gamsig_update_iters>\d+).*?"
    r"frozen=(?P<frozen>true|false|TRUE|FALSE)"
)

POLICY_RE = re.compile(r"\[gamsig_policy\](?P<body>.*)")
PREFLIGHT_RE = re.compile(r"\[sampling_preflight\](?P<body>.*)")


@dataclass(frozen=True)
class ProgressRow:
    p0: float
    iteration: int
    elbo: float
    sigma_exp: float
    gamma_exp: float
    state_norm_sq: float
    gamsig_update_iters: int
    frozen: bool


def parse_float(value: str) -> float:
    try:
        out = float(value)
    except Exception:
        return math.nan
    return out if math.isfinite(out) else math.nan


def parse_key_values(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in body.strip().split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def parse_progress_lines(lines: Iterable[str]) -> tuple[list[ProgressRow], dict[str, str], dict[str, str], int]:
    rows: list[ProgressRow] = []
    policy: dict[str, str] = {}
    preflight: dict[str, str] = {}
    state_guard_count = 0
    for line in lines:
        if "[gamsig_state_guard]" in line:
            state_guard_count += 1
        policy_match = POLICY_RE.search(line)
        if policy_match:
            policy = parse_key_values(policy_match.group("body"))
        preflight_match = PREFLIGHT_RE.search(line)
        if preflight_match:
            preflight = parse_key_values(preflight_match.group("body"))
        match = PROGRESS_RE.search(line)
        if not match:
            continue
        rows.append(
            ProgressRow(
                p0=parse_float(match.group("p0")),
                iteration=int(match.group("iter")),
                elbo=parse_float(match.group("elbo")),
                sigma_exp=parse_float(match.group("sigma_exp")),
                gamma_exp=parse_float(match.group("gamma_exp")),
                state_norm_sq=parse_float(match.group("state_norm_sq")),
                gamsig_update_iters=int(match.group("gamsig_update_iters")),
                frozen=match.group("frozen").lower() == "true",
            )
        )
    rows.sort(key=lambda row: row.iteration)
    return rows, policy, preflight, state_guard_count


def finite_positive(values: Iterable[float]) -> list[float]:
    return [float(v) for v in values if math.isfinite(float(v)) and float(v) > 0]


def ratio(values: Iterable[float]) -> float:
    vals = finite_positive(values)
    if len(vals) < 2:
        return math.nan
    return max(vals) / min(vals)


def alternating_transitions(values: list[float]) -> tuple[int, str]:
    vals = finite_positive(values)
    if len(vals) < len(values) or len(values) < 3:
        return 0, ""
    lo = min(values)
    hi = max(values)
    if not (math.isfinite(lo) and math.isfinite(hi) and hi > lo and lo > 0):
        return 0, ""
    threshold = math.sqrt(lo * hi)
    labels = ["H" if value >= threshold else "L" for value in values]
    transitions = sum(1 for left, right in zip(labels, labels[1:]) if left != right)
    return transitions, "".join(labels)


def classify_two_cycle(
    rows: list[ProgressRow],
    *,
    window: int = 10,
    min_window: int = 6,
    sigma_ratio_threshold: float = 10.0,
    state_ratio_threshold: float = 100.0,
    min_transition_fraction: float = 0.80,
) -> dict[str, str | int | float | bool]:
    if not rows:
        return {
            "two_cycle_suspect": False,
            "cycle_reason": "no_progress_rows",
            "window_n": 0,
        }
    tail = rows[-window:]
    if len(tail) < min_window:
        return {
            "two_cycle_suspect": False,
            "cycle_reason": "too_few_progress_rows",
            "window_n": len(tail),
        }
    sigma_values = [row.sigma_exp for row in tail]
    state_values = [row.state_norm_sq for row in tail]
    sigma_ratio = ratio(sigma_values)
    state_ratio = ratio(state_values)
    sigma_transitions, sigma_pattern = alternating_transitions(sigma_values)
    state_transitions, state_pattern = alternating_transitions(state_values)
    max_transitions = max(sigma_transitions, state_transitions)
    transition_fraction = max_transitions / max(1, len(tail) - 1)
    separated = (
        (math.isfinite(sigma_ratio) and sigma_ratio >= sigma_ratio_threshold)
        or (math.isfinite(state_ratio) and state_ratio >= state_ratio_threshold)
    )
    alternating = transition_fraction >= min_transition_fraction
    suspect = bool(separated and alternating)
    reason_parts: list[str] = []
    if separated:
        reason_parts.append("separated_regimes")
    if alternating:
        reason_parts.append("alternating_tail")
    if not reason_parts:
        reason_parts.append("stable_or_non_alternating_tail")
    return {
        "two_cycle_suspect": suspect,
        "cycle_reason": "+".join(reason_parts),
        "window_n": len(tail),
        "last_iter": tail[-1].iteration,
        "last_elbo": tail[-1].elbo,
        "last_sigma_exp": tail[-1].sigma_exp,
        "last_gamma_exp": tail[-1].gamma_exp,
        "last_state_norm_sq": tail[-1].state_norm_sq,
        "last_gamsig_update_iters": tail[-1].gamsig_update_iters,
        "last_frozen": tail[-1].frozen,
        "tail_sigma_min": min(finite_positive(sigma_values), default=math.nan),
        "tail_sigma_max": max(finite_positive(sigma_values), default=math.nan),
        "tail_sigma_ratio": sigma_ratio,
        "tail_state_min": min(finite_positive(state_values), default=math.nan),
        "tail_state_max": max(finite_positive(state_values), default=math.nan),
        "tail_state_ratio": state_ratio,
        "tail_sigma_transitions": sigma_transitions,
        "tail_state_transitions": state_transitions,
        "tail_transition_fraction": transition_fraction,
        "tail_sigma_pattern": sigma_pattern,
        "tail_state_pattern": state_pattern,
    }


def discover_logs(paths: Iterable[Path]) -> list[Path]:
    logs: list[Path] = []
    for path in paths:
        if path.is_file():
            logs.append(path)
            continue
        logs.extend(path.glob("**/fit.log"))
    return sorted(set(logs))


def summarize_log(path: Path) -> dict[str, str | int | float | bool]:
    rows, policy, preflight, state_guard_count = parse_progress_lines(path.read_text(errors="ignore").splitlines())
    summary = classify_two_cycle(rows)
    p0 = rows[-1].p0 if rows else parse_float(policy.get("p0", "nan"))
    run_id = ""
    parts = path.parts
    if "runs" in parts:
        idx = parts.index("runs")
        if idx + 1 < len(parts):
            run_id = parts[idx + 1]
    return {
        "run_id": run_id,
        "log_path": str(path),
        "q": "" if not math.isfinite(p0) else f"{p0:.2f}",
        "progress_rows": len(rows),
        "policy_likelihood_mode": policy.get("likelihood_mode", ""),
        "policy_freeze_target": policy.get("freeze_target", ""),
        "policy_state_guard": policy.get("state_guard", ""),
        "policy_state_guard_effective": policy.get("state_guard_effective_policy", ""),
        "policy_state_guard_disabled_reason": policy.get("state_guard_disabled_reason", ""),
        "policy_terminal_sampling_guard_mode": policy.get(
            "terminal_sampling_guard_mode",
            preflight.get("mode", ""),
        ),
        "preflight_guard_count": preflight.get("guard_count", ""),
        "observed_state_guard_count": state_guard_count,
        **summary,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# HE2 AL-M-T0 Gamma/Sigma Cycle Audit",
        "",
        "| run_id | q | rows | two-cycle | final iter | sigma | state norm sq | tail sigma ratio | tail state ratio | freeze | guard | log |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {run_id} | {q} | {progress_rows} | {two_cycle_suspect} | {last_iter} | "
            "{last_sigma_exp} | {last_state_norm_sq} | {tail_sigma_ratio} | "
            "{tail_state_ratio} | {policy_freeze_target} | {observed_state_guard_count} | `{log_path}` |".format(
                **{key: row.get(key, "") for key in row.keys()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit gamsig progress logs for terminal two-cycle behavior.")
    parser.add_argument("--path", type=Path, action="append", required=True, help="Run root or fit.log path.")
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--csv-name", default="gamsig_cycle_summary.csv")
    parser.add_argument("--md-name", default="GAMSIG_CYCLE_AUDIT.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logs = discover_logs(args.path)
    rows = [summarize_log(path) for path in logs]
    write_csv(args.report_dir / args.csv_name, rows)
    write_markdown(args.report_dir / args.md_name, rows)
    print(f"wrote {len(rows)} log summaries to {args.report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
