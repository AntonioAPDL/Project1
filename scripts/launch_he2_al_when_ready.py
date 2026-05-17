#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CAMPAIGNS = {
    "keep": {
        "template": ROOT / "config" / "he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.template.yaml",
        "batch": ROOT / "config" / "he2_relaunch_batches" / "dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.yaml",
        "summary": ROOT
        / "runtime"
        / "placeholder",
    },
    "drop": {
        "template": ROOT / "config" / "he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml",
        "batch": ROOT / "config" / "he2_relaunch_batches" / "dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.yaml",
        "summary": ROOT
        / "runtime"
        / "placeholder",
    },
    "univar": {
        "template": ROOT / "config" / "he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml",
        "batch": ROOT / "config" / "he2_relaunch_batches" / "dqlm_univar_al_all_cutoffs_sharedspec_20260517.yaml",
        "summary": ROOT
        / "runtime"
        / "placeholder",
    },
}

CAMPAIGNS["keep"]["summary"] = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517/"
    "control/prelaunch_validation_exact_final_batch_20260517/prelaunch_validation_summary.json"
)
CAMPAIGNS["drop"]["summary"] = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517/"
    "control/prelaunch_validation_exact_final_batch_20260517/prelaunch_validation_summary.json"
)
CAMPAIGNS["univar"]["summary"] = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_dqlm_univar_al_all_cutoffs_sharedspec_20260517/"
    "control/prelaunch_validation_exact_final_batch_20260517/prelaunch_validation_summary.json"
)

STATUS_DIR = ROOT / "reports" / "he2_al_shared_relaunch_plan_20260517"
STATUS_JSON = STATUS_DIR / "auto_launch_status.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Wait for AL validation summaries, then launch the AL relaunch controllers."
    )
    ap.add_argument("--poll-seconds", type=int, default=30)
    ap.add_argument("--timeout-seconds", type=int, default=8 * 60 * 60)
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args(argv)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validation_status(summary: dict) -> tuple[bool, str]:
    smoke_runs = summary.get("smoke_runs", [])
    bad = [item for item in smoke_runs if item.get("status") not in {"passed", "skipped"}]
    if bad:
        label = ", ".join(
            f"{item.get('scope')}:{item.get('family')}:{item.get('cutoff')}={item.get('status')}"
            for item in bad
        )
        return False, f"failing smoke statuses: {label}"
    checks = summary.get("checks", {})
    smoke_meta = checks.get("smoke_runs", {})
    count = smoke_meta.get("count")
    passed = smoke_meta.get("passed", 0)
    skipped = smoke_meta.get("skipped", 0)
    if count is not None and passed + skipped != count:
        return False, f"smoke count mismatch: passed={passed} skipped={skipped} count={count}"
    return True, "passed"


def write_status(payload: dict) -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def launch_campaign(name: str, template: Path, batch: Path, dry_run: bool) -> str:
    cmd = [
        "python3",
        "scripts/launch_he2_bayesian_publication_relaunch.py",
        "--template",
        str(template),
        "--batch-file",
        str(batch),
        "--skip-validate",
        "--reset-state",
    ]
    if dry_run:
        return "DRY_RUN"
    proc = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    return proc.stdout.strip().splitlines()[-1]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    deadline = time.time() + args.timeout_seconds
    launched: dict[str, str] = {}
    while True:
        statuses = {}
        ready = True
        for name, meta in CAMPAIGNS.items():
            summary_path = meta["summary"]
            if not summary_path.exists():
                statuses[name] = {"summary": str(summary_path), "state": "pending"}
                ready = False
                continue
            summary = load_json(summary_path)
            ok, detail = validation_status(summary)
            statuses[name] = {
                "summary": str(summary_path),
                "state": "passed" if ok else "failed",
                "detail": detail,
            }
            if not ok:
                write_status({"state": "validation_failed", "campaigns": statuses})
                return 1
        if ready:
            subprocess.run(
                ["python3", "scripts/build_he2_al_shared_relaunch_validation_status.py"],
                cwd=ROOT,
                check=True,
            )
            subprocess.run(
                ["python3", "scripts/build_he2_al_shared_relaunch_plan.py"],
                cwd=ROOT,
                check=True,
            )
            for name, meta in CAMPAIGNS.items():
                launched[name] = launch_campaign(
                    name=name,
                    template=meta["template"],
                    batch=meta["batch"],
                    dry_run=args.dry_run,
                )
            write_status(
                {
                    "state": "launched" if not args.dry_run else "dry_run_ready",
                    "campaigns": statuses,
                    "controllers": launched,
                }
            )
            return 0
        if time.time() >= deadline:
            write_status({"state": "timeout", "campaigns": statuses})
            return 2
        write_status({"state": "waiting", "campaigns": statuses})
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
