#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-repro/runs}"
MODE="${2:---dry-run}" # --dry-run (default) | --apply
KEEP_CSV="${KEEP_RUN_IDS:-}"

if [[ ! -d "${ROOT}" ]]; then
  echo "ERROR: run root not found: ${ROOT}" >&2
  exit 1
fi

FAILED_DIR="${ROOT}/_failed"
mkdir -p "${FAILED_DIR}"

IFS=',' read -r -a KEEP_IDS <<< "${KEEP_CSV}"

should_keep() {
  local rid="$1"
  local k
  for k in "${KEEP_IDS[@]:-}"; do
    [[ -z "${k}" ]] && continue
    if [[ "${rid}" == "${k}" ]]; then
      return 0
    fi
  done
  return 1
}

is_failed_run() {
  local run_dir="$1"
  local run_id="$2"

  if [[ -f "${run_dir}/COMPLETION_REPORT.md" ]]; then
    return 1
  fi
  if [[ -f "${run_dir}/FAILURE_REPORT.md" ]]; then
    return 0
  fi

  if [[ -f "${run_dir}/run_manifest.yaml" ]]; then
    local status
    status="$(python3 - "${run_dir}/run_manifest.yaml" <<'PY'
import sys
from pathlib import Path
try:
    import yaml
except Exception:
    print("unknown")
    raise SystemExit(0)
p = Path(sys.argv[1])
try:
    d = yaml.safe_load(p.read_text()) or {}
    status = ((d.get("validation") or {}).get("status"))
    print(status if status is not None else "unknown")
except Exception:
    print("unknown")
PY
)"
    if [[ "${status}" != "pass" ]]; then
      return 0
    fi
  fi

  return 1
}

echo "Cleanup mode: ${MODE}"
echo "Root: ${ROOT}"
echo "Keep IDs: ${KEEP_CSV:-<none>}"

moved=0
scanned=0

for run_dir in "${ROOT}"/heavy_* "${ROOT}"/20*; do
  [[ -d "${run_dir}" ]] || continue
  run_id="$(basename "${run_dir}")"
  ((scanned+=1))

  if should_keep "${run_id}"; then
    echo "KEEP (explicit): ${run_id}"
    continue
  fi
  if [[ "${run_id}" == "_failed" || "${run_id}" == "_keep" ]]; then
    continue
  fi

  if is_failed_run "${run_dir}" "${run_id}"; then
    target="${FAILED_DIR}/${run_id}"
    if [[ "${MODE}" == "--apply" ]]; then
      if [[ -e "${target}" ]]; then
        echo "SKIP (target exists): ${target}"
      else
        mv "${run_dir}" "${target}"
        echo "MOVED: ${run_id} -> ${target}"
        ((moved+=1))
      fi
    else
      echo "WOULD_MOVE: ${run_id} -> ${target}"
    fi
  else
    echo "KEEP (pass/unknown-safe): ${run_id}"
  fi
done

echo "Scanned runs: ${scanned}"
if [[ "${MODE}" == "--apply" ]]; then
  echo "Moved runs: ${moved}"
else
  echo "Moved runs: 0 (dry-run)"
fi
