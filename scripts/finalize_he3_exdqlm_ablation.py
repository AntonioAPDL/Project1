#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from he3_exdqlm_ablation_lib import build_status_frame, write_status_markdown
from multimodel_v8_lib import ROOT, load_yaml


DEFAULT_MATRIX_DIR = (
    ROOT.parent
    / "project1_ucsc_phd_runtime"
    / "multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608"
    / "control"
    / "he3_exdqlm_ablation_authoritative_winners_v1"
)

SUMMARY_FILES = [
    "he3_ablation_long.csv",
    "he3_ablation_wide.csv",
    "he3_ablation_summary.md",
    "he3_table_rows.tex",
]

AUDIT_FILES = [
    "audit/he3_ablation_audit.csv",
    "audit/he3_ablation_lead_buckets.csv",
    "audit/he3_ablation_audit.md",
]

ARTICLE_FILES = [
    "tables/generated_tex/he3_ablation_crps_main_table.tex",
    "tables/generated_tex/he3_ablation_crps_body.tex",
    "artifacts/he3_exdqlm_ablation_authoritative/manifest.csv",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Wait for the authoritative HE3 ablation queue to finish, then verify or "
            "repair final summary/audit/article-sync outputs."
        )
    )
    parser.add_argument("--matrix-dir", type=Path, default=DEFAULT_MATRIX_DIR)
    parser.add_argument("--wait", action="store_true", help="Poll until all rows pass or a row fails.")
    parser.add_argument("--poll-seconds", type=int, default=120)
    parser.add_argument(
        "--timeout-minutes",
        type=float,
        default=0.0,
        help="Maximum wait time. Zero means no timeout when --wait is used.",
    )
    parser.add_argument("--force", action="store_true", help="Re-run summary/audit/sync even if outputs exist.")
    parser.add_argument("--no-sync", action="store_true", help="Skip article/corrections sync.")
    parser.add_argument(
        "--cleanup-rdata",
        action="store_true",
        help="After verified completion, remove launched-row .RData/.rdata/.rda files under the HE3 runtime root.",
    )
    parser.add_argument(
        "--ignore-active-controller",
        action="store_true",
        help="Run missing completion hooks even if the queue controller process is still alive.",
    )
    parser.add_argument("--status-json", type=Path, default=None)
    return parser.parse_args()


def load_metadata(matrix_dir: Path) -> dict[str, Any]:
    metadata_path = matrix_dir / "matrix_metadata.yaml"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing matrix metadata: {metadata_path}")
    metadata = load_yaml(metadata_path)
    if not isinstance(metadata, dict):
        raise TypeError(f"Matrix metadata is not a mapping: {metadata_path}")
    return metadata


def artifact_root_from_metadata(metadata: dict[str, Any]) -> Path:
    raw = metadata.get("artifact_root")
    if not raw:
        raise KeyError("matrix_metadata.yaml does not define artifact_root")
    return Path(str(raw)).resolve()


def report_dir_from_metadata(metadata: dict[str, Any]) -> Path:
    return artifact_root_from_metadata(metadata) / "reports" / "he3_exdqlm_ablation"


def refresh_status(matrix_dir: Path, artifact_root: Path) -> pd.DataFrame:
    plan_path = matrix_dir / "matrix_plan.csv"
    if not plan_path.exists():
        raise FileNotFoundError(f"Missing matrix plan: {plan_path}")
    plan = pd.read_csv(plan_path)
    status = build_status_frame(plan, artifact_root)
    status.to_csv(matrix_dir / "matrix_status.csv", index=False)
    write_status_markdown(status, matrix_dir / "matrix_status.md")
    return status


def status_counts(status: pd.DataFrame) -> dict[str, int]:
    return {str(k): int(v) for k, v in Counter(status["status"].astype(str)).items()}


def controller_active(matrix_dir: Path) -> bool:
    proc = subprocess.run(
        ["ps", "-eo", "pid=,command="],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    matrix_token = str(matrix_dir)
    for line in proc.stdout.splitlines():
        if "scripts/run_he3_exdqlm_ablation_queue.py" in line and matrix_token in line:
            return True
    return False


def files_exist(base: Path, rel_paths: list[str]) -> bool:
    return all((base / rel_path).exists() for rel_path in rel_paths)


def article_sync_enabled(metadata: dict[str, Any], no_sync: bool) -> bool:
    if no_sync:
        return False
    sync_cfg = metadata.get("article_sync", {})
    return isinstance(sync_cfg, dict) and bool(sync_cfg.get("enabled", False))


def run_cmd(cmd: list[str], log: list[str]) -> None:
    log.append(f"[{utc_now()}] RUN {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def ensure_summary(matrix_dir: Path, report_dir: Path, force: bool, log: list[str]) -> None:
    if force or not files_exist(report_dir, SUMMARY_FILES):
        run_cmd(
            [
                "python3",
                "scripts/build_he3_exdqlm_ablation_summary.py",
                "--matrix-dir",
                str(matrix_dir),
            ],
            log,
        )
    else:
        log.append(f"[{utc_now()}] summary outputs already present")


def ensure_audit(matrix_dir: Path, report_dir: Path, force: bool, log: list[str]) -> None:
    if force or not files_exist(report_dir, AUDIT_FILES):
        run_cmd(
            [
                "python3",
                "scripts/audit_he3_exdqlm_ablation.py",
                "--matrix-dir",
                str(matrix_dir),
            ],
            log,
        )
    else:
        log.append(f"[{utc_now()}] audit outputs already present")


def ensure_article_sync(matrix_dir: Path, metadata: dict[str, Any], force: bool, log: list[str]) -> None:
    sync_cfg = metadata.get("article_sync", {})
    article_root = Path(str(sync_cfg.get("article_root", ROOT / "Evironmetrics---REVISED-DOC-2"))).resolve()
    corrections_root = Path(str(sync_cfg.get("corrections_root", ROOT.parent / "Corrections---Project-1"))).resolve()
    if force or not files_exist(article_root, ARTICLE_FILES):
        cmd = [
            "python3",
            "scripts/sync_he3_ablation_article_tables.py",
            "--matrix-dir",
            str(matrix_dir),
            "--article-root",
            str(article_root),
            "--corrections-root",
            str(corrections_root),
        ]
        run_cmd(cmd, log)
    else:
        log.append(f"[{utc_now()}] article sync outputs already present")


def verify_summary(report_dir: Path) -> dict[str, Any]:
    long_path = report_dir / "he3_ablation_long.csv"
    if not long_path.exists():
        raise FileNotFoundError(f"Missing HE3 summary long table: {long_path}")
    df = pd.read_csv(long_path)
    if len(df) != 30:
        raise RuntimeError(f"Expected 30 HE3 long-table rows, found {len(df)}")
    if not (df["status"].astype(str) == "pass").all():
        bad = df[df["status"].astype(str) != "pass"][["cutoff", "variant", "status"]]
        raise RuntimeError(f"HE3 long table has non-pass rows: {bad.to_dict(orient='records')}")
    variant_counts = df["variant"].astype(str).value_counts().to_dict()
    return {
        "he3_long_rows": int(len(df)),
        "variant_counts": {str(k): int(v) for k, v in variant_counts.items()},
    }


def verify_audit(report_dir: Path) -> dict[str, Any]:
    audit_path = report_dir / "audit" / "he3_ablation_audit.csv"
    lead_path = report_dir / "audit" / "he3_ablation_lead_buckets.csv"
    if not audit_path.exists():
        raise FileNotFoundError(f"Missing HE3 audit table: {audit_path}")
    if not lead_path.exists():
        raise FileNotFoundError(f"Missing HE3 lead-bucket table: {lead_path}")
    audit = pd.read_csv(audit_path)
    if len(audit) != 25:
        raise RuntimeError(f"Expected 25 launched-row audit rows, found {len(audit)}")
    if "overall_ok" in audit.columns:
        ok_values = audit["overall_ok"].map(lambda x: str(x).strip().lower() in {"true", "1", "yes"})
        if not ok_values.all():
            bad = audit[~ok_values]
            raise RuntimeError(f"HE3 audit has non-ok rows: {bad.to_dict(orient='records')}")
    lead = pd.read_csv(lead_path)
    return {"audit_rows": int(len(audit)), "lead_bucket_rows": int(len(lead))}


def verify_article_sync(metadata: dict[str, Any]) -> dict[str, Any]:
    sync_cfg = metadata.get("article_sync", {})
    article_root = Path(str(sync_cfg.get("article_root", ROOT / "Evironmetrics---REVISED-DOC-2"))).resolve()
    corrections_root = Path(str(sync_cfg.get("corrections_root", ROOT.parent / "Corrections---Project-1"))).resolve()
    missing = [str(article_root / rel_path) for rel_path in ARTICLE_FILES if not (article_root / rel_path).exists()]
    if missing:
        raise FileNotFoundError(f"Missing article sync outputs: {missing}")
    table_text = (article_root / ARTICLE_FILES[0]).read_text(encoding="utf-8")
    if "exAL-M-T1-noH3" not in table_text or "RAW-GLOFAS" not in table_text:
        raise RuntimeError("Article HE3 table does not contain expected ablation/raw rows.")
    manifest_path = article_root / "MANUSCRIPT_ASSET_MANIFEST.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if "tab:he3_ablation_crps" not in manifest.get("tables", {}):
            raise RuntimeError("Article manifest is missing tab:he3_ablation_crps.")
    corrections_path = corrections_root / "main.tex"
    if corrections_path.exists():
        corrections_text = corrections_path.read_text(encoding="utf-8")
        if "RAW-GLOFAS" not in corrections_text or "exAL-M-T1-noH3" not in corrections_text:
            raise RuntimeError("Corrections HE3 table does not contain expected rows.")
    return {"article_root": str(article_root), "corrections_root": str(corrections_root)}


def cleanup_launched_rdata(matrix_dir: Path, artifact_root: Path) -> dict[str, Any]:
    plan = pd.read_csv(matrix_dir / "matrix_plan.csv")
    launched = plan[plan["launch_mode"].astype(str) == "launch"]["run_id"].astype(str).tolist()
    candidates: list[Path] = []
    for run_id in launched:
        run_dir = artifact_root / "runs" / run_id
        for pattern in ("**/*.RData", "**/*.rdata", "**/*.rda"):
            candidates.extend(run_dir.glob(pattern))
    unique = sorted({p for p in candidates if p.exists()})
    bytes_before = sum(p.stat().st_size for p in unique)
    removed = 0
    for path in unique:
        path.unlink()
        removed += 1
    remaining = []
    for run_id in launched:
        run_dir = artifact_root / "runs" / run_id
        for pattern in ("**/*.RData", "**/*.rdata", "**/*.rda"):
            remaining.extend(run_dir.glob(pattern))
    return {
        "rdata_candidates": len(unique),
        "rdata_removed": removed,
        "rdata_bytes_removed": bytes_before,
        "rdata_remaining": len({p for p in remaining if p.exists()}),
    }


def write_finish_report(
    matrix_dir: Path,
    report_dir: Path,
    payload: dict[str, Any],
    status_json: Path | None,
) -> Path:
    finish_dir = report_dir / "finish_gate"
    finish_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = status_json.resolve() if status_json else finish_dir / f"he3_finish_gate_{stamp}.json"
    md_path = finish_dir / f"he3_finish_gate_{stamp}.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# HE3 Ablation Finish Gate",
        "",
        f"- timestamp_utc: `{payload['timestamp_utc']}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- status_counts: `{payload['status_counts']}`",
        f"- completed: `{payload['completed']}`",
        f"- summary: `{payload.get('summary', {})}`",
        f"- audit: `{payload.get('audit', {})}`",
        f"- article_sync: `{payload.get('article_sync', {})}`",
        f"- cleanup: `{payload.get('cleanup', {})}`",
        "",
        "## Actions",
        "",
    ]
    for entry in payload.get("actions", []):
        lines.append(f"- {entry}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


def main() -> int:
    args = parse_args()
    matrix_dir = args.matrix_dir.resolve()
    metadata = load_metadata(matrix_dir)
    artifact_root = artifact_root_from_metadata(metadata)
    report_dir = report_dir_from_metadata(metadata)
    start = time.monotonic()
    actions: list[str] = []

    while True:
        status = refresh_status(matrix_dir, artifact_root)
        counts = status_counts(status)
        actions.append(f"[{utc_now()}] status {counts}")
        if any(status["status"].astype(str) == "fail"):
            payload = {
                "timestamp_utc": utc_now(),
                "completed": False,
                "status_counts": counts,
                "actions": actions,
                "reason": "one_or_more_rows_failed",
            }
            write_finish_report(matrix_dir, report_dir, payload, args.status_json)
            return 1
        if (status["status"].astype(str) == "pass").all():
            break
        if not args.wait:
            payload = {
                "timestamp_utc": utc_now(),
                "completed": False,
                "status_counts": counts,
                "actions": actions,
                "reason": "queue_incomplete",
            }
            write_finish_report(matrix_dir, report_dir, payload, args.status_json)
            return 2
        if args.timeout_minutes > 0 and (time.monotonic() - start) > args.timeout_minutes * 60:
            payload = {
                "timestamp_utc": utc_now(),
                "completed": False,
                "status_counts": counts,
                "actions": actions,
                "reason": "timeout",
            }
            write_finish_report(matrix_dir, report_dir, payload, args.status_json)
            return 3
        time.sleep(max(5, int(args.poll_seconds)))

    if not args.ignore_active_controller and controller_active(matrix_dir):
        while controller_active(matrix_dir):
            if files_exist(report_dir, SUMMARY_FILES + AUDIT_FILES) and (
                not article_sync_enabled(metadata, args.no_sync)
                or files_exist(
                    Path(str(metadata.get("article_sync", {}).get("article_root", ROOT / "Evironmetrics---REVISED-DOC-2"))),
                    ARTICLE_FILES,
                )
            ):
                break
            actions.append(f"[{utc_now()}] all rows pass; waiting for active controller completion hooks")
            time.sleep(max(5, int(args.poll_seconds)))

    ensure_summary(matrix_dir, report_dir, args.force, actions)
    summary_payload = verify_summary(report_dir)
    ensure_audit(matrix_dir, report_dir, args.force, actions)
    audit_payload = verify_audit(report_dir)

    article_payload: dict[str, Any] = {"enabled": False}
    if article_sync_enabled(metadata, args.no_sync):
        ensure_article_sync(matrix_dir, metadata, args.force, actions)
        article_payload = {"enabled": True, **verify_article_sync(metadata)}

    cleanup_payload: dict[str, Any] = {"enabled": False}
    if args.cleanup_rdata:
        cleanup_payload = {"enabled": True, **cleanup_launched_rdata(matrix_dir, artifact_root)}

    final_status = refresh_status(matrix_dir, artifact_root)
    payload = {
        "timestamp_utc": utc_now(),
        "completed": True,
        "status_counts": status_counts(final_status),
        "summary": summary_payload,
        "audit": audit_payload,
        "article_sync": article_payload,
        "cleanup": cleanup_payload,
        "actions": actions,
    }
    report_path = write_finish_report(matrix_dir, report_dir, payload, args.status_json)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
