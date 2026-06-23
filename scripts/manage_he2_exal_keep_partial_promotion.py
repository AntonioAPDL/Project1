#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import signal
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")
SCREEN_ROOT = RUNTIME_ROOT / "multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619"
MATRIX_DIR = SCREEN_ROOT / "control" / "publication_relaunch_matrix"
AUTHORITY_YAML = ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml"
REPORT_ROOT = ROOT / "reports" / "he2_exal_keep_partial_screen_promotion_20260623"
PROMOTION_CUTOFFS = {"20211221", "20220511", "20221225"}
SCREEN_TOKEN = "overnight_screen_20260619"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def read_mean_crps(run_id: str) -> tuple[float, Path]:
    summary_path = SCREEN_ROOT / "runs" / run_id / "post" / "outputs" / run_id / "tables" / "crps_forecast_summary.csv"
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    rows = read_csv(summary_path)
    for row in rows:
        if row.get("model_id") in {"exdqlm_multivar_synth_keep", "exdqlm_multivar_keep"}:
            return float(row["mean_crps"]), summary_path
        if row.get("model_variant") in {"exdqlm_multivar_synth_keep", "exdqlm_multivar_keep"}:
            return float(row["mean_crps"]), summary_path
    if rows and rows[0].get("mean_crps"):
        return float(rows[0]["mean_crps"]), summary_path
    raise ValueError(f"Could not identify mean CRPS row in {summary_path}")


def authority_by_cutoff() -> dict[str, dict[str, Any]]:
    payload = load_yaml(AUTHORITY_YAML)
    return {str(row["cutoff"]): row for row in payload.get("winners", [])}


def compute_screen_summary() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    status_path = MATRIX_DIR / "matrix_status.csv"
    rows = read_csv(status_path)
    auth = authority_by_cutoff()
    best_by_cutoff: dict[str, dict[str, Any]] = {}
    crps_rows: list[dict[str, Any]] = []

    for row in rows:
        if row.get("status") != "pass":
            continue
        mean_crps, source_path = read_mean_crps(row["run_id"])
        record: dict[str, Any] = {
            **row,
            "mean_crps": mean_crps,
            "crps_source": str(source_path),
        }
        crps_rows.append(record)
        cutoff = str(row["cutoff"])
        if cutoff not in best_by_cutoff or mean_crps < float(best_by_cutoff[cutoff]["mean_crps"]):
            best_by_cutoff[cutoff] = record

    promotion_rows: list[dict[str, Any]] = []
    for cutoff in sorted(auth):
        authority = auth[cutoff]
        best = best_by_cutoff.get(cutoff)
        if best is None:
            promotion_rows.append(
                {
                    "cutoff": cutoff,
                    "authority_run_id": authority["run_id"],
                    "authority_mean_crps": float(authority["mean_crps"]),
                    "best_screen_run_id": "",
                    "best_screen_spec": "",
                    "best_screen_mean_crps": "",
                    "delta_vs_authority": "",
                    "promote": "False",
                    "reason": "no_completed_screening_row",
                }
            )
            continue
        delta = float(best["mean_crps"]) - float(authority["mean_crps"])
        promote = cutoff in PROMOTION_CUTOFFS and delta < 0
        reason = "screen_crps_improves_authority" if promote else "best_completed_screening_row_not_better_than_authority"
        promotion_rows.append(
            {
                "cutoff": cutoff,
                "authority_run_id": authority["run_id"],
                "authority_mean_crps": float(authority["mean_crps"]),
                "best_screen_run_id": best["run_id"],
                "best_screen_spec": best["epsilon"],
                "best_screen_mean_crps": float(best["mean_crps"]),
                "delta_vs_authority": delta,
                "promote": str(promote),
                "reason": reason,
            }
        )

    metadata = {
        "generated_at_utc": utc_now(),
        "screen_root": str(SCREEN_ROOT),
        "matrix_dir": str(MATRIX_DIR),
        "status_counts": dict(Counter(row.get("status", "") for row in rows)),
        "passed_rows_with_crps": len(crps_rows),
        "promoted_cutoffs": sorted(row["cutoff"] for row in promotion_rows if row["promote"] == "True"),
        "partial_screen_final": False,
        "partial_screen_note": "The grid remains exploratory until every matrix row is terminal and a later full-screen authority overlay is produced.",
    }
    return crps_rows, promotion_rows, metadata


def write_screen_report(out_dir: Path) -> None:
    crps_rows, promotion_rows, metadata = compute_screen_summary()
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "screen_passed_crps_rows.csv", crps_rows)
    write_csv(out_dir / "promotion_decisions.csv", promotion_rows)
    (out_dir / "promotion_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# HE2 exAL-M-T1 Partial-Screen Promotion Checkpoint",
        "",
        f"- generated_at_utc: `{metadata['generated_at_utc']}`",
        f"- screen_root: `{metadata['screen_root']}`",
        f"- status_counts: `{metadata['status_counts']}`",
        f"- promoted_cutoffs: `{metadata['promoted_cutoffs']}`",
        f"- partial_screen_final: `{metadata['partial_screen_final']}`",
        "",
        "| Cutoff | Authority CRPS | Best Completed Screen Spec | Best Screen CRPS | Delta | Promote | Reason |",
        "|---|---:|---|---:|---:|---|---|",
    ]
    for row in promotion_rows:
        best_crps = "" if row["best_screen_mean_crps"] == "" else f"{float(row['best_screen_mean_crps']):.5f}"
        delta = "" if row["delta_vs_authority"] == "" else f"{float(row['delta_vs_authority']):.5f}"
        lines.append(
            f"| `{row['cutoff']}` | {float(row['authority_mean_crps']):.5f} | "
            f"`{row['best_screen_spec']}` | {best_crps} | {delta} | `{row['promote']}` | `{row['reason']}` |"
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def checkpoint_inputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("matrix_plan.csv", "matrix_status.csv", "queue.log"):
        src = MATRIX_DIR / name
        if src.exists():
            shutil.copy2(src, out_dir / name)
    write_screen_report(out_dir)


def active_screen_processes() -> list[dict[str, str]]:
    proc = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True, text=True, check=True)
    rows: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or SCREEN_TOKEN not in line:
            continue
        if "manage_he2_exal_keep_partial_promotion.py" in line:
            continue
        match = re.match(r"^(\d+)\s+(.*)$", line)
        if match:
            rows.append({"pid": match.group(1), "command": match.group(2)})
    return rows


def pause_screen(*, apply: bool, checkpoint_dir: Path) -> None:
    checkpoint_inputs(checkpoint_dir)
    procs = active_screen_processes()
    write_csv(checkpoint_dir / "screen_processes_before_pause.csv", procs, fieldnames=["pid", "command"])
    if not apply:
        print(f"dry_run=true checkpoint_dir={checkpoint_dir}")
        print(f"matched_processes={len(procs)}")
        for row in procs:
            print(f"{row['pid']} {row['command']}")
        return
    for row in procs:
        os.kill(int(row["pid"]), signal.SIGTERM)
    print(f"sent_sigterm={len(procs)} checkpoint_dir={checkpoint_dir}")


def validate_expected_promotion() -> int:
    _crps_rows, promotion_rows, _metadata = compute_screen_summary()
    actual = {row["cutoff"] for row in promotion_rows if row["promote"] == "True"}
    if actual != PROMOTION_CUTOFFS:
        print(f"Unexpected promotion cutoffs: {sorted(actual)} != {sorted(PROMOTION_CUTOFFS)}")
        return 1
    bad = [row for row in promotion_rows if row["cutoff"] not in PROMOTION_CUTOFFS and row["promote"] == "True"]
    if bad:
        print(f"Unexpected non-target promotions: {bad}")
        return 1
    print("partial promotion decision is valid")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Checkpoint, pause, and validate the HE2 exAL-M-T1 partial-screen promotion handoff."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="Write a checkpoint report from current screening outputs.")
    status.add_argument("--out-dir", type=Path, default=REPORT_ROOT)
    checkpoint = sub.add_parser("checkpoint", help="Copy current matrix/queue evidence into a report directory.")
    checkpoint.add_argument("--out-dir", type=Path, default=REPORT_ROOT / "screen_checkpoint")
    pause = sub.add_parser("pause", help="Checkpoint and optionally SIGTERM only matching screening processes.")
    pause.add_argument("--checkpoint-dir", type=Path, default=REPORT_ROOT / "screen_checkpoint")
    pause.add_argument("--apply", action="store_true", help="Actually send SIGTERM after checkpointing.")
    sub.add_parser("validate-promotion", help="Fail unless the expected three cutoff promotions are the only improvements.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "status":
        write_screen_report(args.out_dir.resolve())
        print(args.out_dir.resolve())
        return 0
    if args.command == "checkpoint":
        checkpoint_inputs(args.out_dir.resolve())
        print(args.out_dir.resolve())
        return 0
    if args.command == "pause":
        pause_screen(apply=bool(args.apply), checkpoint_dir=args.checkpoint_dir.resolve())
        return 0
    if args.command == "validate-promotion":
        return validate_expected_promotion()
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
