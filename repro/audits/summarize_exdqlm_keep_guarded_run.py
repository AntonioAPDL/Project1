#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


PROGRESS_RE = re.compile(r"\[gamsig_progress\].*?\bp0=(?P<p0>[0-9.]+)\s+(?P<body>.*)$")
FIELD_RE = re.compile(r"\b([A-Za-z0-9_.]+)=([^\s]+)")
EVENT_PATTERNS = (
    "gamsig_converged",
    "Sampling finished",
    "Variables saved",
    "post_save_objective",
    "[pseudodata_guard]",
    "Error",
    "Execution halted",
)


def q_label(path: Path) -> str:
    raw = path.name
    if raw.startswith("q="):
        return f"q{raw.split('=', 1)[1]}"
    return raw


def parse_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_progress(line: str) -> dict[str, str]:
    match = PROGRESS_RE.search(line)
    if not match:
        return {}
    fields = {key: value for key, value in FIELD_RE.findall(match.group("body"))}
    fields["p0"] = match.group("p0")
    return fields


def latest_matching(lines: list[str], patterns: tuple[str, ...]) -> str:
    for line in reversed(lines):
        if any(pattern in line for pattern in patterns):
            return line.rstrip("\n")
    return ""


def summarize_lane(lane_dir: Path) -> dict[str, object]:
    lane = q_label(lane_dir)
    log_path = lane_dir / "logs" / "fit.log"
    out_dir = lane_dir / "outputs"
    row: dict[str, object] = {
        "lane": lane,
        "log_path": str(log_path),
        "status": "missing_log",
        "latest_event": "",
        "iter": "",
        "elbo": "",
        "crit_elbo": "",
        "sigma_exp": "",
        "gamma_exp": "",
        "state_norm_sq": "",
        "gamsig_update_iters": "",
        "frozen": "",
        "output_rdata": "",
        "output_rdata_bytes": "",
        "log_mtime_utc": "",
    }
    if not log_path.exists():
        return row

    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    stat = log_path.stat()
    row["log_mtime_utc"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    row["latest_event"] = latest_matching(lines, EVENT_PATTERNS)

    progress = {}
    for line in reversed(lines):
        progress = parse_progress(line)
        if progress:
            break
    if progress:
        row["status"] = "running"
        for key in (
            "iter",
            "elbo",
            "crit_elbo",
            "sigma_exp",
            "gamma_exp",
            "state_norm_sq",
            "gamsig_update_iters",
            "frozen",
        ):
            row[key] = progress.get(key, "")
    if "Variables saved" in row["latest_event"]:
        row["status"] = "saved"
    if "Sampling finished" in row["latest_event"] and row["status"] != "saved":
        row["status"] = "sampling_finished"
    if "Error" in row["latest_event"] or "Execution halted" in row["latest_event"]:
        row["status"] = "error"

    rdata_paths = sorted(out_dir.glob("DISC_variables_*_exAL_synth_DISC.RData"))
    if rdata_paths:
        newest = max(rdata_paths, key=lambda path: path.stat().st_mtime)
        row["output_rdata"] = str(newest)
        row["output_rdata_bytes"] = newest.stat().st_size
        if row["status"] == "running":
            row["status"] = "output_written"
    return row


def count_guard_rows(guard_dir: Path | None) -> dict[str, object]:
    if guard_dir is None or not guard_dir.exists():
        return {"guard_file_count": 0, "guard_event_rows": 0, "guard_dir": str(guard_dir or "")}
    files = sorted(guard_dir.glob("*.csv"))
    rows = 0
    for path in files:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            line_count = sum(1 for _ in handle)
        rows += max(line_count - 1, 0)
    return {"guard_file_count": len(files), "guard_event_rows": rows, "guard_dir": str(guard_dir)}


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, object]], guard_summary: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# exDQLM keep guarded run status",
        "",
        f"Generated UTC: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        f"Guard event rows: `{guard_summary['guard_event_rows']}`",
        "",
        "| lane | status | iter | state_norm_sq | sigma_exp | gamma_exp | output bytes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {lane} | {status} | {iter} | {state_norm_sq} | {sigma_exp} | {gamma_exp} | {output_rdata_bytes} |".format(
                **{key: row.get(key, "") for key in (
                    "lane",
                    "status",
                    "iter",
                    "state_norm_sq",
                    "sigma_exp",
                    "gamma_exp",
                    "output_rdata_bytes",
                )}
            )
        )
    lines.append("")
    lines.append("Latest events:")
    for row in rows:
        lines.append(f"- `{row['lane']}`: {row.get('latest_event', '')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize an isolated guarded exDQLM keep run.")
    parser.add_argument("--run-root", type=Path, required=True, help="Resolved unified run root.")
    parser.add_argument("--guard-dir", type=Path, default=None, help="Pseudo-data guard event directory.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Optional report directory for CSV/JSON/Markdown.")
    args = parser.parse_args()

    keep_root = args.run_root / "fit" / "exdqlm_multivar" / "keep"
    lane_dirs = sorted(path for path in keep_root.glob("q=*") if path.is_dir())
    rows = [summarize_lane(path) for path in lane_dirs]
    guard_summary = count_guard_rows(args.guard_dir)
    payload = {
        "run_root": str(args.run_root),
        "keep_root": str(keep_root),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "guard_summary": guard_summary,
        "lanes": rows,
    }

    if args.out_dir is not None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        write_csv(rows, args.out_dir / "live_status.csv")
        (args.out_dir / "live_status.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        write_markdown(rows, guard_summary, args.out_dir / "LIVE_STATUS.md")

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
