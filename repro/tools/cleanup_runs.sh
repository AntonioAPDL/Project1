#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNS_DIR="${ROOT_DIR}/repro/runs"
BASELINE_DIR="${ROOT_DIR}/repro/baseline_runs"
KEEP_LAST_SUCCESS=10
KEEP_RECENT=8
OLDER_THAN_DAYS=30
APPLY=0
INCLUDE_BASELINE_RUNS=0
REPORT_FILE=""
MARKER_FILES=".canonical.keep,.run_keep,.protect_run"

usage() {
  cat <<'EOF'
Usage: repro/tools/cleanup_runs.sh [--dry-run] [--apply]
                                [--keep-last-success N] [--keep-recent N]
                                [--older-than-days D] [--runs-dir PATH]
                                [--include-baseline-runs] [--baseline-dir PATH]
                                [--report-file PATH]

Defaults (safe):
  --dry-run           (default behavior; no deletions)
  --keep-last-success 10
  --keep-recent 8
  --older-than-days 30

Selection rule:
  Candidate run dir is selected only when it is NOT protected and:
    - status is not PASS, OR
    - age is older than threshold days

Protection rules (deterministic):
  - most recent N directories by mtime (keep-recent)
  - last N PASS runs by mtime (keep-last-success)
  - run_id referenced by any config/* canonical_run_id (except "__SELF__")
  - marker file present in run dir: .canonical.keep / .run_keep / .protect_run

Baseline safety:
  - baseline runs are NEVER touched unless --include-baseline-runs is set.

Output:
  - prints sorted deletion plan with sizes
  - writes a timestamped cleanup report file (or --report-file path)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      APPLY=0
      shift
      ;;
    --apply)
      APPLY=1
      shift
      ;;
    --keep-last-success)
      KEEP_LAST_SUCCESS="${2:-}"
      shift 2
      ;;
    --keep-recent)
      KEEP_RECENT="${2:-}"
      shift 2
      ;;
    --older-than-days)
      OLDER_THAN_DAYS="${2:-}"
      shift 2
      ;;
    --runs-dir)
      RUNS_DIR="${2:-}"
      shift 2
      ;;
    --include-baseline-runs)
      INCLUDE_BASELINE_RUNS=1
      shift
      ;;
    --baseline-dir)
      BASELINE_DIR="${2:-}"
      shift 2
      ;;
    --report-file)
      REPORT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "${KEEP_LAST_SUCCESS}" =~ ^[0-9]+$ ]]; then
  echo "--keep-last-success must be a non-negative integer" >&2
  exit 2
fi
if ! [[ "${KEEP_RECENT}" =~ ^[0-9]+$ ]]; then
  echo "--keep-recent must be a non-negative integer" >&2
  exit 2
fi
if ! [[ "${OLDER_THAN_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "--older-than-days must be a non-negative integer" >&2
  exit 2
fi

if [[ ! -d "${RUNS_DIR}" ]]; then
  echo "Runs directory not found: ${RUNS_DIR}" >&2
  exit 1
fi

timestamp="$(date -u +%Y%m%d_%H%M%S)"
if [[ -z "${REPORT_FILE}" ]]; then
  REPORT_DIR="${ROOT_DIR}/repro/reports/cleanup_runs"
  mkdir -p "${REPORT_DIR}"
  REPORT_FILE="${REPORT_DIR}/cleanup_${timestamp}.log"
else
  mkdir -p "$(dirname "${REPORT_FILE}")"
fi

python3 - "${ROOT_DIR}" "${RUNS_DIR}" "${BASELINE_DIR}" "${KEEP_LAST_SUCCESS}" "${KEEP_RECENT}" "${OLDER_THAN_DAYS}" "${APPLY}" "${INCLUDE_BASELINE_RUNS}" "${REPORT_FILE}" "${MARKER_FILES}" <<'PY'
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Set

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"ERROR: PyYAML is required for cleanup policy resolution (import yaml failed: {exc})", file=sys.stderr)
    sys.exit(2)

root_dir = pathlib.Path(sys.argv[1]).resolve()
runs_dir = pathlib.Path(sys.argv[2]).resolve()
baseline_dir = pathlib.Path(sys.argv[3]).resolve()
keep_last_success = int(sys.argv[4])
keep_recent = int(sys.argv[5])
older_than_days = int(sys.argv[6])
apply_mode = bool(int(sys.argv[7]))
include_baseline_runs = bool(int(sys.argv[8]))
report_file = pathlib.Path(sys.argv[9]).resolve()
marker_files = [x.strip() for x in sys.argv[10].split(",") if x.strip()]

now = dt.datetime.now(dt.timezone.utc).timestamp()


def bytes_to_human(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(n)
    for u in units:
        if val < 1024 or u == units[-1]:
            return f"{val:.2f}{u}"
        val /= 1024
    return f"{n}B"


def dir_size_bytes(path: pathlib.Path) -> int:
    try:
        out = subprocess.check_output(["du", "-sb", str(path)], text=True).strip()
        return int(out.split()[0])
    except Exception:
        total = 0
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
        return total


def read_manifest_status(run_dir: pathlib.Path) -> str:
    manifest = run_dir / "run_manifest.yaml"
    if not manifest.exists():
        return "missing_manifest"
    try:
        data = yaml.safe_load(manifest.read_text()) or {}
    except Exception:
        return "manifest_parse_error"
    ts = ((data.get("timestamps") or {}).get("finished_at_utc"))
    v = ((data.get("validation") or {}).get("status"))
    if ts and str(v).lower() == "pass":
        return "pass"
    return "not_pass"


def referenced_canonical_run_ids() -> Set[str]:
    out: Set[str] = set()
    cfg_dir = root_dir / "config"
    for y in cfg_dir.rglob("*.yaml"):
        try:
            data = yaml.safe_load(y.read_text()) or {}
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        val = ((data.get("validation") or {}).get("canonical_run_id"))
        if val is None:
            continue
        val_s = str(val).strip()
        if not val_s or val_s.lower() == "null" or val_s == "__SELF__":
            continue
        out.add(val_s)
    return out


@dataclass(order=True)
class Entry:
    sort_key: float
    path: pathlib.Path = field(compare=False)
    run_id: str = field(compare=False)
    kind: str = field(compare=False)
    status: str = field(compare=False)
    age_days: int = field(compare=False)
    mtime: float = field(compare=False)
    size_bytes: int = field(compare=False)
    protected_reasons: List[str] = field(default_factory=list, compare=False)
    select_reasons: List[str] = field(default_factory=list, compare=False)


def marker_hits(path: pathlib.Path) -> List[str]:
    hits = []
    for m in marker_files:
        if (path / m).exists():
            hits.append(m)
    return hits


def collect_entries(base: pathlib.Path, kind: str) -> List[Entry]:
    if not base.exists():
        return []
    entries: List[Entry] = []
    for p in sorted([x for x in base.iterdir() if x.is_dir()]):
        st = p.stat()
        mtime = st.st_mtime
        age_days = int((now - mtime) // 86400)
        status = read_manifest_status(p) if kind == "runs" else "baseline"
        entries.append(
            Entry(
                sort_key=-mtime,
                path=p,
                run_id=p.name,
                kind=kind,
                status=status,
                age_days=age_days,
                mtime=mtime,
                size_bytes=dir_size_bytes(p),
            )
        )
    return entries


entries = collect_entries(runs_dir, "runs")
if include_baseline_runs:
    entries.extend(collect_entries(baseline_dir, "baseline_runs"))

entries.sort()  # newest first due negative mtime key

canonical_ids = referenced_canonical_run_ids()
recent_ids = {e.run_id for e in entries[:keep_recent]}
pass_entries = [e for e in entries if e.kind == "runs" and e.status == "pass"]
pass_entries.sort(key=lambda e: e.mtime, reverse=True)
last_success_ids = {e.run_id for e in pass_entries[:keep_last_success]}

for e in entries:
    if e.run_id in canonical_ids:
        e.protected_reasons.append("canonical_config_reference")
    hits = marker_hits(e.path)
    if hits:
        e.protected_reasons.append(f"marker:{','.join(hits)}")
    if e.run_id in recent_ids:
        e.protected_reasons.append("keep_recent")
    if e.run_id in last_success_ids:
        e.protected_reasons.append("keep_last_success")

candidates: List[Entry] = []
for e in entries:
    if e.protected_reasons:
        continue
    if e.kind == "baseline_runs":
        if e.age_days > older_than_days:
            e.select_reasons.append("age")
            candidates.append(e)
        continue
    if e.status != "pass":
        e.select_reasons.append("status")
    if e.age_days > older_than_days:
        e.select_reasons.append("age")
    if e.select_reasons:
        candidates.append(e)

candidates.sort(key=lambda e: (-e.size_bytes, str(e.path)))
estimated_reclaim = sum(e.size_bytes for e in candidates)

lines: List[str] = []
lines.append("cleanup_runs.sh policy report")
lines.append(f"generated_utc={dt.datetime.now(dt.timezone.utc).isoformat()}")
lines.append(f"runs_dir={runs_dir}")
lines.append(f"baseline_dir={baseline_dir}")
lines.append(f"include_baseline_runs={include_baseline_runs}")
lines.append(f"keep_recent={keep_recent}")
lines.append(f"keep_last_success={keep_last_success}")
lines.append(f"older_than_days={older_than_days}")
lines.append(f"mode={'apply' if apply_mode else 'dry-run'}")
lines.append(f"canonical_ids_detected={len(canonical_ids)}")
lines.append(f"entries_scanned={len(entries)}")
lines.append(f"candidates={len(candidates)}")
lines.append(f"estimated_reclaim_bytes={estimated_reclaim}")
lines.append(f"estimated_reclaim_human={bytes_to_human(estimated_reclaim)}")
lines.append("")
if canonical_ids:
    lines.append("canonical_ids:")
    for rid in sorted(canonical_ids):
        lines.append(f"  - {rid}")
    lines.append("")

lines.append("deletion_plan_sorted=size_desc,path")
lines.append("kind|run_id|status|age_days|size_bytes|size_human|reasons|path")
for e in candidates:
    lines.append(
        "|".join(
            [
                e.kind,
                e.run_id,
                e.status,
                str(e.age_days),
                str(e.size_bytes),
                bytes_to_human(e.size_bytes),
                ",".join(e.select_reasons) if e.select_reasons else "-",
                str(e.path),
            ]
        )
    )

if apply_mode:
    lines.append("")
    lines.append("apply_actions:")
    for e in candidates:
        lines.append(f"  - delete {e.path}")
        shutil.rmtree(e.path, ignore_errors=False)
    lines.append("apply_status=complete")
else:
    lines.append("")
    lines.append("apply_status=not_requested")

report_file.parent.mkdir(parents=True, exist_ok=True)
report_file.write_text("\n".join(lines) + "\n")

for l in lines[:20]:
    print(l)
print("...")
print(f"report_file={report_file}")
print(f"estimated_reclaim_human={bytes_to_human(estimated_reclaim)}")
print(f"candidates={len(candidates)}")
if not apply_mode:
    print("Dry-run only. Re-run with --apply to delete listed candidates.")
PY
