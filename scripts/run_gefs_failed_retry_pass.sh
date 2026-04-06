#!/usr/bin/env bash
set -euo pipefail

# Run a targeted, low-concurrency GEFS retry pass against failed file URLs,
# then reconcile the recovered rows into a new non-destructive output root.
#
# Usage:
#   ./scripts/run_gefs_failed_retry_pass.sh <BASE_MANIFEST_RUN_DIR> [RETRY_ID]
#
# Environment overrides:
#   DRY_RUN=1
#   BASE_OUT_SUBDIR=extract_gefs_full
#   RETRY_OUT_SUBDIR=extract_gefs_retry
#   RECONCILED_OUT_SUBDIR=extract_gefs_full_reconciled_<retry_id>
#   GEFS_RETRY_WORKERS=1
#   GEFS_RETRY_BATCH_SIZE=1
#   GEFS_RETRY_FILE_RETRIES=6
#   GEFS_RETRY_ERROR_SUBSTRING="503: Slow Down"

BASE_MANIFEST_RUN_DIR="${1:?BASE_MANIFEST_RUN_DIR is required}"
RETRY_ID="${2:-gefs_retry_$(date -u +%Y%m%dT%H%M%SZ)}"
DRY_RUN="${DRY_RUN:-0}"

ROOT="${PROJECT_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd}"
cd "$ROOT"

BASE_RUN_DIR="$(python3 - <<'PY' "$BASE_MANIFEST_RUN_DIR"
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"

BASE_OUT_SUBDIR="${BASE_OUT_SUBDIR:-extract_gefs_full}"
RETRY_OUT_SUBDIR="${RETRY_OUT_SUBDIR:-extract_gefs_retry}"
RECONCILED_OUT_SUBDIR="${RECONCILED_OUT_SUBDIR:-extract_gefs_full_reconciled_${RETRY_ID}}"
GEFS_RETRY_WORKERS="${GEFS_RETRY_WORKERS:-1}"
GEFS_RETRY_BATCH_SIZE="${GEFS_RETRY_BATCH_SIZE:-1}"
GEFS_RETRY_FILE_RETRIES="${GEFS_RETRY_FILE_RETRIES:-6}"
GEFS_RETRY_ERROR_SUBSTRING="${GEFS_RETRY_ERROR_SUBSTRING:-503: Slow Down}"

RETRY_RUN_DIR="${BASE_RUN_DIR}/retry_passes/${RETRY_ID}"
RETRY_LOG_DIR="${RETRY_RUN_DIR}/logs"
RETRY_CMD_DIR="${RETRY_RUN_DIR}/commands"
mkdir -p "$RETRY_LOG_DIR" "$RETRY_CMD_DIR"

if [[ "$BASE_OUT_SUBDIR" == "$RETRY_OUT_SUBDIR" || "$BASE_OUT_SUBDIR" == "$RECONCILED_OUT_SUBDIR" || "$RETRY_OUT_SUBDIR" == "$RECONCILED_OUT_SUBDIR" ]]; then
  echo "[FATAL] BASE_OUT_SUBDIR, RETRY_OUT_SUBDIR, and RECONCILED_OUT_SUBDIR must all be distinct." >&2
  exit 2
fi

if [[ ! -d "$BASE_RUN_DIR" ]]; then
  echo "[FATAL] Base manifest run dir does not exist: $BASE_RUN_DIR" >&2
  exit 2
fi

if [[ ! -f "$BASE_RUN_DIR/manifests/gefs_manifest.csv" ]]; then
  echo "[FATAL] Missing base GEFS manifest: $BASE_RUN_DIR/manifests/gefs_manifest.csv" >&2
  exit 2
fi

if [[ ! -f "$BASE_RUN_DIR/$BASE_OUT_SUBDIR/gefs/gefs_file_status.csv" ]]; then
  echo "[FATAL] Missing base GEFS status ledger: $BASE_RUN_DIR/$BASE_OUT_SUBDIR/gefs/gefs_file_status.csv" >&2
  exit 2
fi

CMD_BUILD=(
  python3 scripts/build_gefs_failed_retry_bundle.py
  --base-manifest-run-dir "$BASE_RUN_DIR"
  --retry-run-dir "$RETRY_RUN_DIR"
  --base-out-subdir "$BASE_OUT_SUBDIR"
  --error-substring "$GEFS_RETRY_ERROR_SUBSTRING"
)
CMD_EXTRACT=(
  python3 scripts/extract_gefs_nwm_forecast_points.py
  --manifest-run-dir "$RETRY_RUN_DIR"
  --out-subdir "$RETRY_OUT_SUBDIR"
  --sources gefs
  --gefs-workers "$GEFS_RETRY_WORKERS"
  --batch-size "$GEFS_RETRY_BATCH_SIZE"
  --gefs-file-retries "$GEFS_RETRY_FILE_RETRIES"
)
CMD_RETRY_HEALTH=(
  python3 scripts/check_gefs_nwm_forecast_extract_health.py
  --manifest-run-dir "$RETRY_RUN_DIR"
  --mode full
  --sources gefs
  --gefs-out-subdir "$RETRY_OUT_SUBDIR"
  --out-json "$RETRY_RUN_DIR/health_checks/gefs_retry_health.json"
)
CMD_RECONCILE=(
  python3 scripts/reconcile_gefs_retry_outputs.py
  --base-manifest-run-dir "$BASE_RUN_DIR"
  --retry-run-dir "$RETRY_RUN_DIR"
  --base-out-subdir "$BASE_OUT_SUBDIR"
  --retry-out-subdir "$RETRY_OUT_SUBDIR"
  --reconciled-out-subdir "$RECONCILED_OUT_SUBDIR"
)
CMD_RECONCILED_HEALTH=(
  python3 scripts/check_gefs_nwm_forecast_extract_health.py
  --manifest-run-dir "$BASE_RUN_DIR"
  --mode full
  --sources gefs
  --gefs-out-subdir "$RECONCILED_OUT_SUBDIR"
  --out-json "$BASE_RUN_DIR/health_checks/gefs_reconciled_health_${RETRY_ID}.json"
)

PLAN_FILE="$RETRY_CMD_DIR/retry_pass_plan.sh"
{
  printf '#!/usr/bin/env bash\n'
  printf '# Auto-generated retry plan for %s\n' "$RETRY_ID"
  printf 'set -euo pipefail\n\n'
  printf '# Base manifest run dir\n'
  printf 'BASE_RUN_DIR=%q\n' "$BASE_RUN_DIR"
  printf 'RETRY_RUN_DIR=%q\n\n' "$RETRY_RUN_DIR"
  printf '# Step 1: Build retry bundle\n'
  printf '%q ' "${CMD_BUILD[@]}"; printf '\n\n'
  printf '# Step 2: Extract retry rows\n'
  printf '%q ' "${CMD_EXTRACT[@]}"; printf '\n\n'
  printf '# Step 3: Validate retry outputs\n'
  printf '%q ' "${CMD_RETRY_HEALTH[@]}"; printf '\n\n'
  printf '# Step 4: Reconcile non-destructively\n'
  printf '%q ' "${CMD_RECONCILE[@]}"; printf '\n\n'
  printf '# Step 5: Validate reconciled outputs\n'
  printf '%q ' "${CMD_RECONCILED_HEALTH[@]}"; printf '\n'
} > "$PLAN_FILE"
chmod +x "$PLAN_FILE"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY-RUN] wrote command plan: $PLAN_FILE"
  printf '[DRY-RUN] %q ' "${CMD_BUILD[@]}"; echo
  printf '[DRY-RUN] %q ' "${CMD_EXTRACT[@]}"; echo
  printf '[DRY-RUN] %q ' "${CMD_RETRY_HEALTH[@]}"; echo
  printf '[DRY-RUN] %q ' "${CMD_RECONCILE[@]}"; echo
  printf '[DRY-RUN] %q ' "${CMD_RECONCILED_HEALTH[@]}"; echo
  exit 0
fi

printf '[STEP] %q ' "${CMD_BUILD[@]}"; echo
"${CMD_BUILD[@]}" |& tee "$RETRY_LOG_DIR/build_retry_bundle.log"

printf '[STEP] %q ' "${CMD_EXTRACT[@]}"; echo
"${CMD_EXTRACT[@]}" |& tee "$RETRY_LOG_DIR/extract_retry.log"

printf '[STEP] %q ' "${CMD_RETRY_HEALTH[@]}"; echo
"${CMD_RETRY_HEALTH[@]}" |& tee "$RETRY_LOG_DIR/retry_health.log"

printf '[STEP] %q ' "${CMD_RECONCILE[@]}"; echo
"${CMD_RECONCILE[@]}" |& tee "$RETRY_LOG_DIR/reconcile.log"

printf '[STEP] %q ' "${CMD_RECONCILED_HEALTH[@]}"; echo
"${CMD_RECONCILED_HEALTH[@]}" |& tee "$RETRY_LOG_DIR/reconciled_health.log"

echo "[OK] command_plan=${PLAN_FILE}"
echo "[OK] retry_run_dir=${RETRY_RUN_DIR}"
echo "[OK] reconciled_out_subdir=${RECONCILED_OUT_SUBDIR}"
