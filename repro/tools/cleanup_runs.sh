#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNS_DIR="${ROOT_DIR}/repro/runs"
KEEP_LAST=10
OLDER_THAN_DAYS=30
APPLY=0

usage() {
  cat <<'EOF'
Usage: repro/tools/cleanup_runs.sh [--dry-run] [--apply] [--keep-last N] [--older-than-days D] [--runs-dir PATH]

Defaults (safe):
  --dry-run           (default behavior; no deletions)
  --keep-last 10
  --older-than-days 30

Selection rule:
  Candidate run dir is selected when either:
    - run status is not PASS (finished_at_utc missing OR validation.status != pass), OR
    - run directory age is older than threshold days
  while preserving newest N run directories.
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
    --keep-last)
      KEEP_LAST="${2:-}"
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

if ! [[ "${KEEP_LAST}" =~ ^[0-9]+$ ]]; then
  echo "--keep-last must be a non-negative integer" >&2
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

mapfile -t RUN_DIRS < <(find "${RUNS_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -nr | awk '{print $2}')
if [[ ${#RUN_DIRS[@]} -eq 0 ]]; then
  echo "No run directories under ${RUNS_DIR}"
  exit 0
fi

declare -A KEEP_MAP=()
for ((i=0; i<${#RUN_DIRS[@]} && i<KEEP_LAST; i++)); do
  KEEP_MAP["${RUN_DIRS[$i]}"]=1
done

now_epoch="$(date +%s)"
total_bytes=0
candidates=()

status_of_dir() {
  local run_dir="$1"
  local manifest="${run_dir}/run_manifest.yaml"
  if [[ ! -f "${manifest}" ]]; then
    echo "missing_manifest"
    return
  fi
  python3 - "$manifest" <<'PY'
import sys, yaml
manifest_path = sys.argv[1]
try:
    with open(manifest_path) as f:
        data = yaml.safe_load(f) or {}
except Exception:
    print("manifest_parse_error")
    raise SystemExit(0)
ts = (data.get("timestamps") or {}).get("finished_at_utc")
v = (data.get("validation") or {}).get("status")
if ts and str(v).lower() == "pass":
    print("pass")
else:
    print("not_pass")
PY
}

for run_dir in "${RUN_DIRS[@]}"; do
  if [[ -n "${KEEP_MAP[${run_dir}]:-}" ]]; then
    continue
  fi
  status="$(status_of_dir "${run_dir}")"
  mtime="$(stat -c %Y "${run_dir}")"
  age_days=$(( (now_epoch - mtime) / 86400 ))
  choose=0
  if [[ "${status}" != "pass" ]]; then
    choose=1
  fi
  if [[ "${age_days}" -gt "${OLDER_THAN_DAYS}" ]]; then
    choose=1
  fi
  if [[ "${choose}" -eq 1 ]]; then
    bytes="$(du -sb "${run_dir}" | awk '{print $1}')"
    total_bytes=$((total_bytes + bytes))
    candidates+=("${run_dir}|${status}|${age_days}|${bytes}")
  fi
done

echo "cleanup_runs.sh summary"
echo "- runs_dir: ${RUNS_DIR}"
echo "- keep_last: ${KEEP_LAST}"
echo "- older_than_days: ${OLDER_THAN_DAYS}"
echo "- mode: $([[ ${APPLY} -eq 1 ]] && echo apply || echo dry-run)"
echo "- candidates: ${#candidates[@]}"
echo "- estimated_reclaim_bytes: ${total_bytes}"

if [[ ${#candidates[@]} -eq 0 ]]; then
  exit 0
fi

printf '%s\n' "candidate|status|age_days|bytes"
for row in "${candidates[@]}"; do
  printf '%s\n' "${row}"
done

if [[ "${APPLY}" -ne 1 ]]; then
  echo "Dry-run only. Re-run with --apply to delete candidate run directories."
  exit 0
fi

for row in "${candidates[@]}"; do
  run_dir="${row%%|*}"
  echo "Deleting ${run_dir}"
  rm -rf -- "${run_dir}"
done

echo "Cleanup complete."
