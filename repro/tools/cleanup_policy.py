#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    import yaml  # type: ignore
except Exception as exc:
    print(
        f"ERROR: PyYAML is required for cleanup policy tooling (import yaml failed: {exc})",
        file=sys.stderr,
    )
    sys.exit(2)


SAFETY_WINDOW_HOURS_DEFAULT = 6
THIN_FILE_PATTERNS = (
    "fit/**/outputs/*.RData",
    "fit/**/outputs/*.rds",
    "fit/**/outputs/*.RDS",
)
THIN_CACHE_PATTERNS = (
    "fit/**/cache",
    "post/**/cache",
)
PROTECTION_MARKERS = (".canonical.keep", ".run_keep", ".protect_run")


@dataclass
class RunRecord:
    run_id: str
    path: str
    is_baseline: bool
    size_bytes: int
    finished_at_utc: Optional[str]
    validation_status: Optional[str]
    git_sha: Optional[str]
    profile: Optional[str]
    families_enabled: List[str]
    last_modified_utc: str
    manifest_exists: bool
    resolved_config_exists: bool
    is_unfinished: bool
    is_recently_modified: bool
    age_days: float
    protect_reasons: List[str] = field(default_factory=list)


@dataclass
class CleanupAction:
    run_id: str
    run_path: str
    is_baseline: bool
    action: str  # delete_run | thin_run
    reason: str
    estimated_reclaim_bytes: int
    targets: List[str] = field(default_factory=list)
    top_heavy_files: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CleanupPlan:
    mode: str
    options: Dict[str, Any]
    generated_at_utc: str
    runs_scanned: int
    actions: List[CleanupAction]
    protected_runs: List[RunRecord]
    estimated_reclaim_bytes: int
    canonical_ids_detected: List[str]
    protected_ids_detected: List[str]
    baseline_allowlist_detected: List[str]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def parse_iso_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "~"}:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def bytes_to_human(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(value)
    for unit in units:
        if val < 1024 or unit == units[-1]:
            return f"{val:.2f}{unit}"
        val /= 1024.0
    return f"{value}B"


def safe_read_yaml(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict):
        return data
    return None


def get_dir_size_bytes(path: Path) -> int:
    try:
        out = subprocess.check_output(["du", "-sb", str(path)], text=True)
        return int(out.strip().split()[0])
    except Exception:
        total = 0
        for child in path.rglob("*"):
            if child.is_file():
                try:
                    total += child.stat().st_size
                except OSError:
                    continue
        return total


def detect_profile(resolved_cfg: Optional[Dict[str, Any]]) -> Optional[str]:
    if not resolved_cfg:
        return None
    validation = resolved_cfg.get("validation")
    if not isinstance(validation, dict):
        return None
    prof = validation.get("profile")
    return str(prof) if prof is not None else None


def detect_families_enabled(resolved_cfg: Optional[Dict[str, Any]]) -> List[str]:
    if not resolved_cfg:
        return []
    models = resolved_cfg.get("models")
    if not isinstance(models, dict):
        return []
    families: List[Tuple[str, str]] = [
        ("exdqlm_multivar", "run_exdqlm_multivar"),
        ("exdqlm_univar", "run_exdqlm_univar"),
        ("ndlm_main", "run_ndlm_main"),
    ]
    out = [family for family, key in families if bool(models.get(key))]
    return out


def record_from_run_dir(run_dir: Path, is_baseline: bool, now: datetime, safety_window_hours: int) -> RunRecord:
    manifest_path = run_dir / "run_manifest.yaml"
    resolved_cfg_path = run_dir / "resolved_config.yaml"

    manifest = safe_read_yaml(manifest_path)
    resolved_cfg = safe_read_yaml(resolved_cfg_path)

    finished_at = None
    validation_status = None
    git_sha = None
    if manifest:
        timestamps = manifest.get("timestamps")
        if isinstance(timestamps, dict):
            finished_at = timestamps.get("finished_at_utc")
            if finished_at is not None:
                finished_at = str(finished_at)
        validation = manifest.get("validation")
        if isinstance(validation, dict):
            val_status = validation.get("status")
            validation_status = str(val_status) if val_status is not None else None
        git = manifest.get("git")
        if isinstance(git, dict):
            commit = git.get("commit")
            git_sha = str(commit) if commit is not None else None

    mtime = run_dir.stat().st_mtime
    last_modified_utc = isoformat_utc(mtime)
    age_hours = (now.timestamp() - mtime) / 3600.0

    finished_dt = parse_iso_dt(finished_at)
    is_unfinished = finished_dt is None
    is_recently_modified = age_hours < float(safety_window_hours)

    return RunRecord(
        run_id=run_dir.name,
        path=str(run_dir),
        is_baseline=is_baseline,
        size_bytes=get_dir_size_bytes(run_dir),
        finished_at_utc=finished_at,
        validation_status=validation_status,
        git_sha=git_sha,
        profile=detect_profile(resolved_cfg),
        families_enabled=detect_families_enabled(resolved_cfg),
        last_modified_utc=last_modified_utc,
        manifest_exists=manifest_path.exists(),
        resolved_config_exists=resolved_cfg_path.exists(),
        is_unfinished=is_unfinished,
        is_recently_modified=is_recently_modified,
        age_days=max((now.timestamp() - mtime) / 86400.0, 0.0),
    )


def collect_run_records(
    runs_dir: Path,
    baseline_dir: Path,
    include_baseline: bool,
    safety_window_hours: int,
) -> List[RunRecord]:
    now = utc_now()
    records: List[RunRecord] = []

    if runs_dir.exists():
        for child in sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.name):
            records.append(record_from_run_dir(child, is_baseline=False, now=now, safety_window_hours=safety_window_hours))

    if include_baseline and baseline_dir.exists():
        for child in sorted([p for p in baseline_dir.iterdir() if p.is_dir()], key=lambda p: p.name):
            records.append(record_from_run_dir(child, is_baseline=True, now=now, safety_window_hours=safety_window_hours))

    return records


def discover_canonical_run_ids(repo_root: Path) -> Set[str]:
    out: Set[str] = set()
    cfg_root = repo_root / "config" / "unified_runs"
    if not cfg_root.exists():
        return out
    for cfg_path in sorted(cfg_root.glob("*.yaml")):
        cfg = safe_read_yaml(cfg_path)
        if not cfg:
            continue
        validation = cfg.get("validation")
        if not isinstance(validation, dict):
            continue
        rid = validation.get("canonical_run_id")
        if rid is None:
            continue
        rid_s = str(rid).strip()
        if not rid_s or rid_s.lower() == "null" or rid_s == "__SELF__":
            continue
        out.add(rid_s)
    return out


def load_protected_config(path: Path) -> Tuple[Set[str], Dict[str, str], Set[str]]:
    if not path.exists():
        return set(), {}, set()
    data = safe_read_yaml(path) or {}

    protected: Set[str] = set()
    notes: Dict[str, str] = {}
    baseline_allowlist: Set[str] = set()

    ids = data.get("protected_run_ids")
    if isinstance(ids, list):
        for item in ids:
            if item is None:
                continue
            rid = str(item).strip()
            if rid:
                protected.add(rid)

    raw_notes = data.get("notes")
    if isinstance(raw_notes, dict):
        for k, v in raw_notes.items():
            rid = str(k).strip()
            if not rid:
                continue
            notes[rid] = str(v)

    raw_allow = data.get("baseline_delete_allowlist")
    if isinstance(raw_allow, list):
        for item in raw_allow:
            if item is None:
                continue
            rid = str(item).strip()
            if rid:
                baseline_allowlist.add(rid)

    return protected, notes, baseline_allowlist


def marker_reasons(run_path: Path) -> List[str]:
    reasons: List[str] = []
    for marker in PROTECTION_MARKERS:
        if (run_path / marker).exists():
            reasons.append(f"marker:{marker}")
    return reasons


def top_heavy_files(run_path: Path, limit: int = 5) -> List[Dict[str, Any]]:
    files: List[Tuple[int, str]] = []
    for root, _, names in os.walk(run_path):
        for name in names:
            p = Path(root) / name
            try:
                size = p.stat().st_size
            except OSError:
                continue
            files.append((size, str(p)))
    files.sort(key=lambda x: x[0], reverse=True)
    out = []
    for size, p in files[:limit]:
        out.append({"path": p, "size_bytes": size, "size_human": bytes_to_human(size)})
    return out


def thin_targets_for_run(run_path: Path) -> List[Path]:
    targets: Set[Path] = set()
    for pattern in THIN_FILE_PATTERNS:
        for p in run_path.glob(pattern):
            if p.is_file():
                targets.add(p)
    for pattern in THIN_CACHE_PATTERNS:
        for p in run_path.glob(pattern):
            if p.exists() and p.is_dir():
                targets.add(p)
    return sorted(targets, key=lambda x: str(x))


def sum_existing_sizes(paths: Iterable[Path]) -> int:
    total = 0
    for p in paths:
        try:
            if p.is_file():
                total += p.stat().st_size
            elif p.is_dir():
                total += get_dir_size_bytes(p)
        except OSError:
            continue
    return total


def apply_base_protection(
    records: Sequence[RunRecord],
    include_baseline: bool,
    protected_ids: Set[str],
    canonical_ids: Set[str],
    baseline_allowlist: Set[str],
) -> None:
    for rec in records:
        reasons = rec.protect_reasons
        run_path = Path(rec.path)

        if rec.is_baseline and not include_baseline:
            reasons.append("baseline_default_protected")
        if rec.is_baseline and include_baseline and rec.run_id not in baseline_allowlist:
            reasons.append("baseline_not_in_allowlist")

        if rec.run_id in protected_ids:
            reasons.append("protected_runs_yaml")
        if rec.run_id in canonical_ids:
            reasons.append("canonical_config_reference")

        if rec.is_recently_modified:
            reasons.append("modified_within_safety_window")

        # Treat unfinished + recent as in-progress and always protected.
        if rec.is_unfinished and rec.is_recently_modified:
            reasons.append("in_progress_manifest")

        reasons.extend(marker_reasons(run_path))

        # de-dup while preserving order
        seen: Set[str] = set()
        dedup: List[str] = []
        for reason in reasons:
            if reason not in seen:
                dedup.append(reason)
                seen.add(reason)
        rec.protect_reasons = dedup


def apply_keep_last(records: Sequence[RunRecord], keep_last: int) -> None:
    if keep_last <= 0:
        return

    def sort_key(rec: RunRecord) -> Tuple[float, float, str]:
        finished_dt = parse_iso_dt(rec.finished_at_utc)
        finished_ts = finished_dt.timestamp() if finished_dt else -1.0
        mtime_ts = parse_iso_dt(rec.last_modified_utc).timestamp() if parse_iso_dt(rec.last_modified_utc) else -1.0
        return (finished_ts, mtime_ts, rec.run_id)

    completed_non_protected = [
        rec
        for rec in records
        if not rec.protect_reasons and not rec.is_unfinished
    ]
    completed_non_protected.sort(key=sort_key, reverse=True)

    for rec in completed_non_protected[:keep_last]:
        rec.protect_reasons.append("keep_last_completed")


def build_cleanup_plan(
    repo_root: Path,
    records: List[RunRecord],
    *,
    keep_last: int,
    older_than_days: int,
    thin_old: bool,
    thin_old_days: int,
    delete_failed: bool,
    include_baseline: bool,
    protected_config_path: Path,
) -> CleanupPlan:
    protected_ids, _, baseline_allowlist = load_protected_config(protected_config_path)
    canonical_ids = discover_canonical_run_ids(repo_root)

    apply_base_protection(
        records,
        include_baseline=include_baseline,
        protected_ids=protected_ids,
        canonical_ids=canonical_ids,
        baseline_allowlist=baseline_allowlist,
    )
    apply_keep_last(records, keep_last=keep_last)

    actions: List[CleanupAction] = []
    protected_runs: List[RunRecord] = []

    for rec in records:
        if rec.protect_reasons:
            protected_runs.append(rec)
            continue

        rec_age_ok = rec.age_days >= float(older_than_days)
        if rec.is_unfinished:
            if delete_failed and rec_age_ok and not rec.is_recently_modified:
                action = CleanupAction(
                    run_id=rec.run_id,
                    run_path=rec.path,
                    is_baseline=rec.is_baseline,
                    action="delete_run",
                    reason="delete_failed_unfinished",
                    estimated_reclaim_bytes=rec.size_bytes,
                    targets=[rec.path],
                    top_heavy_files=top_heavy_files(Path(rec.path)),
                )
                actions.append(action)
            continue

        if thin_old and rec.age_days >= float(thin_old_days):
            targets = thin_targets_for_run(Path(rec.path))
            reclaim = sum_existing_sizes(targets)
            if reclaim > 0:
                actions.append(
                    CleanupAction(
                        run_id=rec.run_id,
                        run_path=rec.path,
                        is_baseline=rec.is_baseline,
                        action="thin_run",
                        reason=f"thin_old_age>={thin_old_days}",
                        estimated_reclaim_bytes=reclaim,
                        targets=[str(t) for t in targets],
                        top_heavy_files=top_heavy_files(Path(rec.path)),
                    )
                )
            continue

        if rec_age_ok:
            actions.append(
                CleanupAction(
                    run_id=rec.run_id,
                    run_path=rec.path,
                    is_baseline=rec.is_baseline,
                    action="delete_run",
                    reason=f"age>={older_than_days}",
                    estimated_reclaim_bytes=rec.size_bytes,
                    targets=[rec.path],
                    top_heavy_files=top_heavy_files(Path(rec.path)),
                )
            )

    actions.sort(key=lambda a: (a.estimated_reclaim_bytes, a.run_id), reverse=True)

    return CleanupPlan(
        mode="dry-run",
        options={
            "keep_last": keep_last,
            "older_than_days": older_than_days,
            "thin_old": thin_old,
            "thin_old_days": thin_old_days,
            "delete_failed": delete_failed,
            "include_baseline": include_baseline,
            "protected_config_path": str(protected_config_path),
        },
        generated_at_utc=utc_now().isoformat(),
        runs_scanned=len(records),
        actions=actions,
        protected_runs=sorted(protected_runs, key=lambda r: r.run_id),
        estimated_reclaim_bytes=sum(a.estimated_reclaim_bytes for a in actions),
        canonical_ids_detected=sorted(canonical_ids),
        protected_ids_detected=sorted(protected_ids),
        baseline_allowlist_detected=sorted(baseline_allowlist),
    )


def apply_cleanup_plan(plan: CleanupPlan, apply: bool) -> Dict[str, Any]:
    applied_actions: List[Dict[str, Any]] = []
    reclaimed = 0

    if not apply:
        return {"mode": "dry-run", "applied_actions": [], "reclaimed_bytes": 0}

    for action in plan.actions:
        action_record: Dict[str, Any] = asdict(action)
        action_record["removed"] = []

        if action.action == "delete_run":
            run_path = Path(action.run_path)
            if run_path.exists():
                action_record["removed"].append(str(run_path))
                shutil.rmtree(run_path)
        elif action.action == "thin_run":
            for target in action.targets:
                target_path = Path(target)
                if not target_path.exists():
                    continue
                action_record["removed"].append(str(target_path))
                if target_path.is_file() or target_path.is_symlink():
                    target_path.unlink()
                elif target_path.is_dir():
                    shutil.rmtree(target_path)
        else:
            continue

        reclaimed += action.estimated_reclaim_bytes
        applied_actions.append(action_record)

    return {"mode": "apply", "applied_actions": applied_actions, "reclaimed_bytes": reclaimed}


def format_plan_text(plan: CleanupPlan, apply_result: Dict[str, Any], *, apply: bool) -> str:
    lines: List[str] = []
    lines.append("cleanup_policy report")
    lines.append(f"generated_at_utc={plan.generated_at_utc}")
    lines.append(f"mode={'apply' if apply else 'dry-run'}")
    for k, v in plan.options.items():
        lines.append(f"option.{k}={v}")
    lines.append(f"runs_scanned={plan.runs_scanned}")
    lines.append(f"protected_runs={len(plan.protected_runs)}")
    lines.append(f"actions={len(plan.actions)}")
    lines.append(f"estimated_reclaim_bytes={plan.estimated_reclaim_bytes}")
    lines.append(f"estimated_reclaim_human={bytes_to_human(plan.estimated_reclaim_bytes)}")
    lines.append("")

    lines.append("detected.canonical_run_ids=" + (",".join(plan.canonical_ids_detected) if plan.canonical_ids_detected else ""))
    lines.append("detected.protected_run_ids=" + (",".join(plan.protected_ids_detected) if plan.protected_ids_detected else ""))
    lines.append("detected.baseline_delete_allowlist=" + (",".join(plan.baseline_allowlist_detected) if plan.baseline_allowlist_detected else ""))
    lines.append("")

    lines.append("planned_actions:")
    if not plan.actions:
        lines.append("  - none")
    for idx, action in enumerate(plan.actions, start=1):
        lines.append(
            f"  {idx}. {action.action} run_id={action.run_id} baseline={action.is_baseline} "
            f"reason={action.reason} reclaim={action.estimated_reclaim_bytes} ({bytes_to_human(action.estimated_reclaim_bytes)})"
        )
        for target in action.targets:
            lines.append(f"     target={target}")
        for heavy in action.top_heavy_files[:5]:
            lines.append(f"     heavy={heavy['size_human']} {heavy['path']}")

    lines.append("")
    lines.append("protected_runs:")
    if not plan.protected_runs:
        lines.append("  - none")
    for rec in plan.protected_runs:
        lines.append(
            f"  - {rec.run_id} baseline={rec.is_baseline} reasons={','.join(rec.protect_reasons)}"
        )

    lines.append("")
    lines.append(f"apply.reclaimed_bytes={apply_result.get('reclaimed_bytes', 0)}")
    lines.append(f"apply.reclaimed_human={bytes_to_human(int(apply_result.get('reclaimed_bytes', 0)))}")
    lines.append(f"apply.actions_applied={len(apply_result.get('applied_actions', []))}")

    return "\n".join(lines) + "\n"


def write_plan_logs(
    repo_root: Path,
    plan: CleanupPlan,
    apply_result: Dict[str, Any],
    *,
    apply: bool,
    log_dir: Optional[Path] = None,
) -> Tuple[Path, Path]:
    timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
    mode = "apply" if apply else "dryrun"

    if log_dir is None:
        log_dir = repo_root / "repro" / "cleanup_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    text_path = log_dir / f"{timestamp}_{mode}.log"
    json_path = log_dir / f"{timestamp}_{mode}.json"

    text_path.write_text(
        format_plan_text(plan, apply_result, apply=apply),
        encoding="utf-8",
    )

    payload = {
        "plan": {
            "mode": mode,
            "generated_at_utc": plan.generated_at_utc,
            "options": plan.options,
            "runs_scanned": plan.runs_scanned,
            "estimated_reclaim_bytes": plan.estimated_reclaim_bytes,
            "canonical_ids_detected": plan.canonical_ids_detected,
            "protected_ids_detected": plan.protected_ids_detected,
            "baseline_allowlist_detected": plan.baseline_allowlist_detected,
            "actions": [asdict(a) for a in plan.actions],
            "protected_runs": [asdict(r) for r in plan.protected_runs],
        },
        "apply": apply_result,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return text_path, json_path


def collect_inventory_rows(repo_root: Path, include_baseline: bool = True, safety_window_hours: int = SAFETY_WINDOW_HOURS_DEFAULT) -> List[RunRecord]:
    runs_dir = repo_root / "repro" / "runs"
    baseline_dir = repo_root / "repro" / "baseline_runs"
    return collect_run_records(
        runs_dir=runs_dir,
        baseline_dir=baseline_dir,
        include_baseline=include_baseline,
        safety_window_hours=safety_window_hours,
    )


def write_inventory(repo_root: Path, csv_path: Path, json_path: Path) -> Tuple[Path, Path]:
    rows = collect_inventory_rows(repo_root=repo_root, include_baseline=True)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "run_id",
                "path",
                "is_baseline",
                "size_bytes",
                "finished_at_utc",
                "validation_status",
                "git_sha",
                "profile",
                "families_enabled",
                "last_modified_utc",
                "manifest_exists",
                "resolved_config_exists",
                "is_unfinished",
                "is_recently_modified",
                "age_days",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.run_id,
                    row.path,
                    "true" if row.is_baseline else "false",
                    row.size_bytes,
                    row.finished_at_utc or "",
                    row.validation_status or "",
                    row.git_sha or "",
                    row.profile or "",
                    ";".join(row.families_enabled),
                    row.last_modified_utc,
                    "true" if row.manifest_exists else "false",
                    "true" if row.resolved_config_exists else "false",
                    "true" if row.is_unfinished else "false",
                    "true" if row.is_recently_modified else "false",
                    f"{row.age_days:.6f}",
                ]
            )

    payload = {
        "generated_at_utc": utc_now().isoformat(),
        "runs": [asdict(r) for r in rows],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return csv_path, json_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe retention + thinning cleanup workflow for repro runs")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--baseline-dir", type=Path, default=None)
    parser.add_argument("--protected-config", type=Path, default=None)
    parser.add_argument("--log-dir", type=Path, default=None)

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only (default)")
    mode.add_argument("--apply", action="store_true", help="Apply cleanup actions")

    parser.add_argument("--keep-last", type=int, default=15)
    parser.add_argument("--keep-last-success", type=int, default=None, help="Backward-compatible alias for --keep-last")
    parser.add_argument("--keep-recent", type=int, default=0, help="Backward-compatible no-op; retained for compatibility")
    parser.add_argument("--older-than-days", type=int, default=21)
    parser.add_argument("--thin-old", action="store_true")
    parser.add_argument("--thin-old-days", type=int, default=None)
    parser.add_argument("--delete-failed", action="store_true")
    parser.add_argument("--include-baseline", action="store_true")
    parser.add_argument("--include-baseline-runs", action="store_true", help="Backward-compatible alias for --include-baseline")
    parser.add_argument("--safety-window-hours", type=int, default=SAFETY_WINDOW_HOURS_DEFAULT)

    parser.add_argument("--inventory-only", action="store_true", help="Only generate run inventory files")
    parser.add_argument("--inventory-csv", type=Path, default=None)
    parser.add_argument("--inventory-json", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    repo_root = args.repo_root.resolve()
    runs_dir = (args.runs_dir or (repo_root / "repro" / "runs")).resolve()
    baseline_dir = (args.baseline_dir or (repo_root / "repro" / "baseline_runs")).resolve()
    protected_cfg = (args.protected_config or (repo_root / "repro" / "protected_runs.yaml")).resolve()
    log_dir = (args.log_dir or (repo_root / "repro" / "cleanup_logs")).resolve()

    if args.keep_last_success is not None:
        keep_last = args.keep_last_success
    else:
        keep_last = args.keep_last

    include_baseline = bool(args.include_baseline or args.include_baseline_runs)
    thin_old_days = args.thin_old_days if args.thin_old_days is not None else args.older_than_days

    if args.inventory_only:
        csv_path = (args.inventory_csv or (repo_root / "repro" / "run_inventory.csv")).resolve()
        json_path = (args.inventory_json or (repo_root / "repro" / "run_inventory.json")).resolve()
        out_csv, out_json = write_inventory(repo_root=repo_root, csv_path=csv_path, json_path=json_path)
        print(f"inventory_csv={out_csv}")
        print(f"inventory_json={out_json}")
        return 0

    if keep_last < 0 or args.older_than_days < 0 or thin_old_days < 0:
        print("ERROR: keep/age thresholds must be non-negative integers", file=sys.stderr)
        return 2

    if not runs_dir.exists():
        print(f"ERROR: runs directory not found: {runs_dir}", file=sys.stderr)
        return 1

    records = collect_run_records(
        runs_dir=runs_dir,
        baseline_dir=baseline_dir,
        include_baseline=include_baseline,
        safety_window_hours=args.safety_window_hours,
    )

    plan = build_cleanup_plan(
        repo_root=repo_root,
        records=records,
        keep_last=keep_last,
        older_than_days=args.older_than_days,
        thin_old=args.thin_old,
        thin_old_days=thin_old_days,
        delete_failed=args.delete_failed,
        include_baseline=include_baseline,
        protected_config_path=protected_cfg,
    )

    apply_mode = bool(args.apply)
    plan.mode = "apply" if apply_mode else "dry-run"

    apply_result = apply_cleanup_plan(plan, apply=apply_mode)
    text_log, json_log = write_plan_logs(
        repo_root=repo_root,
        plan=plan,
        apply_result=apply_result,
        apply=apply_mode,
        log_dir=log_dir,
    )

    print("cleanup_policy summary")
    print(f"mode={plan.mode}")
    print(f"runs_scanned={plan.runs_scanned}")
    print(f"protected_runs={len(plan.protected_runs)}")
    print(f"actions={len(plan.actions)}")
    print(f"estimated_reclaim_bytes={plan.estimated_reclaim_bytes}")
    print(f"estimated_reclaim_human={bytes_to_human(plan.estimated_reclaim_bytes)}")
    print(f"log_text={text_log}")
    print(f"log_json={json_log}")

    for idx, action in enumerate(plan.actions, start=1):
        print(
            f"plan[{idx}] action={action.action} run_id={action.run_id} "
            f"baseline={action.is_baseline} reason={action.reason} "
            f"reclaim={action.estimated_reclaim_bytes} ({bytes_to_human(action.estimated_reclaim_bytes)})"
        )

    if not apply_mode:
        print("Dry-run only. Re-run with --apply to execute the plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
