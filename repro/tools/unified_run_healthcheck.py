#!/usr/bin/env python3
"""One-shot health check + optional S3 output inventory for unified runs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


Q_TAGS = ("01", "05", "10", "50", "90", "95", "99")
ITER_PATTERNS = (
    re.compile(r"\biter(?:ation)?\b[^0-9]*([0-9]{1,6})", re.IGNORECASE),
    re.compile(r"\bvb\b[^0-9]*([0-9]{1,6})", re.IGNORECASE),
)
ERROR_PATTERNS = (
    re.compile(r"\berror\b", re.IGNORECASE),
    re.compile(r"execution halted", re.IGNORECASE),
    re.compile(r"\btraceback\b", re.IGNORECASE),
    re.compile(r"\bfatal\b", re.IGNORECASE),
    re.compile(r"\bfailed?\b", re.IGNORECASE),
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_lines(path: Path, max_lines: int = 1200) -> List[str]:
    if not path.exists():
        return []
    try:
        data = path.read_text(errors="replace").splitlines()
    except OSError:
        return []
    if len(data) <= max_lines:
        return data
    return data[-max_lines:]


def extract_last_iteration(lines: List[str]) -> int | None:
    last_iter = None
    for line in lines:
        for pat in ITER_PATTERNS:
            m = pat.search(line)
            if m:
                try:
                    last_iter = int(m.group(1))
                except ValueError:
                    continue
    return last_iter


def extract_error_signals(lines: List[str], max_hits: int = 6) -> List[str]:
    hits: List[str] = []
    for line in lines:
        if any(p.search(line) for p in ERROR_PATTERNS):
            hits.append(line.strip())
    return hits[-max_hits:]


def status_from_log(path: Path) -> Dict[str, object]:
    lines = read_lines(path)
    return {
        "path": str(path),
        "exists": path.exists(),
        "line_count": len(lines),
        "last_iteration": extract_last_iteration(lines),
        "error_signals": extract_error_signals(lines),
    }


def collect_family_progress(run_root: Path) -> Dict[str, object]:
    multiv = {
        f"q={q}": status_from_log(run_root / "fit" / f"q={q}" / "logs" / "fit.log")
        for q in Q_TAGS
    }
    univar = {
        f"q={q}": status_from_log(
            run_root
            / "fit"
            / "exdqlm_univar"
            / f"q={q}"
            / "logs"
            / "univar_theory.log"
        )
        for q in Q_TAGS
    }
    ndlm = status_from_log(run_root / "fit" / "ndlm_main" / "logs" / "ndlm_theory.log")
    return {"multiv": multiv, "univar": univar, "ndlm": ndlm}


def gather_stage_logs(manifest: Dict[str, object], run_root: Path) -> List[Tuple[str, Path]]:
    logs: List[Tuple[str, Path]] = []
    stages = manifest.get("stages") or {}
    if isinstance(stages, dict):
        for stage_name, payload in stages.items():
            if not isinstance(payload, dict):
                continue
            log_path = payload.get("log_path")
            if isinstance(log_path, str) and log_path.strip():
                logs.append((f"stage:{stage_name}", Path(log_path)))
    logs.append(("fit:ndlm", run_root / "fit" / "ndlm_main" / "logs" / "ndlm_theory.log"))
    for q in Q_TAGS:
        logs.append((f"fit:multiv:q={q}", run_root / "fit" / f"q={q}" / "logs" / "fit.log"))
        logs.append(
            (
                f"fit:univar:q={q}",
                run_root
                / "fit"
                / "exdqlm_univar"
                / f"q={q}"
                / "logs"
                / "univar_theory.log",
            )
        )
    seen = set()
    deduped: List[Tuple[str, Path]] = []
    for label, path in logs:
        key = (label, str(path))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((label, path))
    return deduped


def stage_summary(manifest: Dict[str, object]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    stages = manifest.get("stages") or {}
    if not isinstance(stages, dict):
        return out
    for stage_name, payload in stages.items():
        if isinstance(payload, dict):
            out[stage_name] = str(payload.get("status"))
        else:
            out[stage_name] = str(payload)
    return out


def run_closed_pass(manifest: Dict[str, object]) -> bool:
    timestamps = manifest.get("timestamps") or {}
    finished = timestamps.get("finished_at_utc") if isinstance(timestamps, dict) else None
    if not finished:
        return False
    stages = stage_summary(manifest)
    required = ("forecats", "data_prep_shared", "fit", "post", "validate", "report")
    return all(stages.get(s) == "pass" for s in required)


def run_failed(manifest: Dict[str, object]) -> bool:
    return any(v == "fail" for v in stage_summary(manifest).values())


def build_output_inventory(run_id: str, run_root: Path, output_dir: Path) -> Dict[str, object]:
    post_root = run_root / "post" / "outputs" / run_id
    inventory: Dict[str, object] = {
        "generated_at_utc": utc_now(),
        "run_id": run_id,
        "post_output_root": str(post_root),
        "post_output_exists": post_root.exists(),
    }
    if not post_root.exists():
        inventory["error"] = "post output root missing"
        return inventory

    all_files = [p for p in post_root.rglob("*") if p.is_file()]
    figure_ext = {".png", ".jpg", ".jpeg", ".pdf", ".svg"}
    table_ext = {".csv", ".tex", ".tsv", ".md"}
    figures = [p for p in all_files if p.suffix.lower() in figure_ext]
    tables = [p for p in all_files if p.suffix.lower() in table_ext]
    table_dir_files = [p for p in (post_root / "tables").rglob("*") if p.is_file()] if (post_root / "tables").exists() else []

    key_artifacts = {
        "post_artifacts_manifest.csv": post_root / "post_artifacts_manifest.csv",
        "post_artifacts_summary.json": post_root / "post_artifacts_summary.json",
        "All3_exal_DISC.png": post_root / "All3_exal_DISC.png",
        "All3_ndlm_DISC.png": post_root / "All3_ndlm_DISC.png",
        "All_ELBOS_DISC.png": post_root / "All_ELBOS_DISC.png",
        "posterior_samples.png": post_root / "posterior_samples.png",
        "posterior_samples_counter.png": post_root / "posterior_samples_counter.png",
        "tables/posterior_table_exports_manifest.csv": post_root / "tables" / "posterior_table_exports_manifest.csv",
    }
    key_presence = {k: v.exists() for k, v in key_artifacts.items()}

    inventory.update(
        {
            "counts": {
                "files_total": len(all_files),
                "figures_total": len(figures),
                "tables_total": len(tables),
                "tables_dir_total": len(table_dir_files),
            },
            "key_artifacts": key_presence,
            "key_synthesis_present": len([p for p in all_files if "synth" in p.name.lower()]),
            "key_agg_disc_present": len([p for p in all_files if p.name.startswith("Agg_disc_")]),
            "posterior_trace_like_present": len(
                [
                    p
                    for p in all_files
                    if ("elbo" in p.name.lower())
                    or ("posterior" in p.name.lower())
                    or ("conv" in p.name.lower())
                ]
            ),
            "missing_key_artifacts": [k for k, ok in key_presence.items() if not ok],
        }
    )

    (output_dir / "s3_output_inventory.json").write_text(json.dumps(inventory, indent=2))
    lines = [
        "# S3 Output Inventory",
        "",
        f"- generated_at_utc: `{inventory['generated_at_utc']}`",
        f"- run_id: `{run_id}`",
        f"- post_output_root: `{post_root}`",
        f"- post_output_exists: `{inventory['post_output_exists']}`",
        "",
        "## Counts",
        "",
        f"- files_total: `{inventory['counts']['files_total']}`",
        f"- figures_total: `{inventory['counts']['figures_total']}`",
        f"- tables_total: `{inventory['counts']['tables_total']}`",
        f"- tables_dir_total: `{inventory['counts']['tables_dir_total']}`",
        "",
        "## Key Artifacts",
        "",
    ]
    for key, ok in key_presence.items():
        lines.append(f"- {key}: `{'present' if ok else 'missing'}`")
    if inventory["missing_key_artifacts"]:
        lines.extend(
            [
                "",
                "## Missing Key Artifacts",
                "",
                *[f"- `{name}`" for name in inventory["missing_key_artifacts"]],
            ]
        )
    (output_dir / "s3_output_inventory.md").write_text("\n".join(lines) + "\n")
    return inventory


def write_failure_bundle(
    manifest: Dict[str, object], run_root: Path, output_dir: Path
) -> Dict[str, object]:
    rows = []
    for label, path in gather_stage_logs(manifest, run_root):
        info = status_from_log(path)
        if info["error_signals"]:
            rows.append(
                {
                    "source": label,
                    "log_path": info["path"],
                    "last_iteration": info["last_iteration"],
                    "error_signals": info["error_signals"],
                }
            )
    bundle = {
        "generated_at_utc": utc_now(),
        "run_id": manifest.get("run_id"),
        "summary": "Root-cause-first failure signatures captured; no broad fixes applied.",
        "fail_stage_statuses": {
            k: v for k, v in stage_summary(manifest).items() if v == "fail"
        },
        "error_sources": rows,
    }
    (output_dir / "failure_bundle.json").write_text(json.dumps(bundle, indent=2))
    md = [
        "# Failure Bundle",
        "",
        f"- generated_at_utc: `{bundle['generated_at_utc']}`",
        f"- run_id: `{bundle['run_id']}`",
        f"- summary: {bundle['summary']}",
        "",
        "## Failed Stages",
        "",
    ]
    fail_stages = bundle["fail_stage_statuses"]
    if fail_stages:
        md.extend([f"- `{k}`: `{v}`" for k, v in fail_stages.items()])
    else:
        md.append("- none")
    md.extend(["", "## Error Signatures", ""])
    if not rows:
        md.append("- none captured from scanned logs")
    else:
        for row in rows:
            md.append(f"- source `{row['source']}` ({row['log_path']})")
            md.append(f"  - last_iteration: `{row['last_iteration']}`")
            for sig in row["error_signals"]:
                md.append(f"  - signal: `{sig}`")
    (output_dir / "failure_bundle.md").write_text("\n".join(md) + "\n")
    return bundle


def write_status_md(report: Dict[str, object], out_path: Path) -> None:
    lines = [
        "# Unified Run Health Check",
        "",
        f"- generated_at_utc: `{report['generated_at_utc']}`",
        f"- run_id: `{report['run_id']}`",
        f"- run_root: `{report['run_root']}`",
        f"- manifest_path: `{report['manifest_path']}`",
        f"- finished_at_utc: `{report.get('finished_at_utc')}`",
        f"- run_closed_pass: `{report['run_closed_pass']}`",
        f"- run_failed: `{report['run_failed']}`",
        "",
        "## Stage Statuses",
        "",
    ]
    for stage, status in report["stages"].items():
        lines.append(f"- `{stage}`: `{status}`")
    lines.extend(["", "## Family Progress (last iteration / error count)", ""])
    for fam in ("multiv", "univar"):
        lines.append(f"### {fam}")
        for q, info in report["family_progress"][fam].items():
            lines.append(
                f"- `{q}`: iter=`{info['last_iteration']}` errors=`{len(info['error_signals'])}`"
            )
    nd = report["family_progress"]["ndlm"]
    lines.extend(
        [
            "",
            "### ndlm",
            f"- iter=`{nd['last_iteration']}` errors=`{len(nd['error_signals'])}`",
            "",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-root", default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--emit-s3-on-pass", action="store_true")
    args = parser.parse_args()

    run_root = (
        Path(args.run_root)
        if args.run_root
        else Path("repro") / "runs" / args.run_id
    )
    manifest_path = run_root / "run_manifest.yaml"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not manifest_path.exists():
        payload = {
            "generated_at_utc": utc_now(),
            "run_id": args.run_id,
            "run_root": str(run_root),
            "manifest_path": str(manifest_path),
            "error": "manifest_missing",
        }
        (output_dir / "status_report.json").write_text(json.dumps(payload, indent=2))
        (output_dir / "status_report.md").write_text(
            "# Unified Run Health Check\n\n- error: `manifest_missing`\n"
        )
        return 1

    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    stages = stage_summary(manifest)
    timestamps = manifest.get("timestamps") or {}
    finished_at = timestamps.get("finished_at_utc") if isinstance(timestamps, dict) else None

    report = {
        "generated_at_utc": utc_now(),
        "run_id": manifest.get("run_id", args.run_id),
        "run_root": str(run_root),
        "manifest_path": str(manifest_path),
        "finished_at_utc": finished_at,
        "stages": stages,
        "run_closed_pass": run_closed_pass(manifest),
        "run_failed": run_failed(manifest),
        "family_progress": collect_family_progress(run_root),
    }
    (output_dir / "status_report.json").write_text(json.dumps(report, indent=2))
    write_status_md(report, output_dir / "status_report.md")

    if report["run_closed_pass"] and args.emit_s3_on_pass:
        build_output_inventory(report["run_id"], run_root, output_dir)
    elif report["run_failed"]:
        write_failure_bundle(manifest, run_root, output_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
