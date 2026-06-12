#!/usr/bin/env bash
set -euo pipefail

ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
ARTICLE_ROOT="$ROOT/Evironmetrics---REVISED-DOC-Corrected"
WORKFLOW_ROOT="$ROOT"
KEEP_RUNTIME_ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516"
UNIVAR_RUNTIME_ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516"
SUPPORT_RUN_ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_historical_support_replay_20260517/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep_historical_support_replay"
RUN_PID="${1:-}"
OUT_DIR="$ROOT/reports/current_model_output_support_contract_audit_20260517"
STATUS_JSON="$OUT_DIR/background_refresh_status.json"

mkdir -p "$OUT_DIR"

log() {
  printf '[%s] %s\n' "$(date -Is)" "$*"
}

write_status() {
  python3 - "$STATUS_JSON" "$1" "$2" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
state = sys.argv[2]
message = sys.argv[3]
payload = {
    "state": state,
    "message": message,
}
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

fit_paths=(
  "$SUPPORT_RUN_ROOT/fit/exdqlm_multivar/keep/q=05/outputs/DISC_variables_5_exAL_synth_DISC.RData"
  "$SUPPORT_RUN_ROOT/fit/exdqlm_multivar/keep/q=20/outputs/DISC_variables_20_exAL_synth_DISC.RData"
  "$SUPPORT_RUN_ROOT/fit/exdqlm_multivar/keep/q=35/outputs/DISC_variables_35_exAL_synth_DISC.RData"
  "$SUPPORT_RUN_ROOT/fit/exdqlm_multivar/keep/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData"
  "$SUPPORT_RUN_ROOT/fit/exdqlm_multivar/keep/q=65/outputs/DISC_variables_65_exAL_synth_DISC.RData"
  "$SUPPORT_RUN_ROOT/fit/exdqlm_multivar/keep/q=80/outputs/DISC_variables_80_exAL_synth_DISC.RData"
  "$SUPPORT_RUN_ROOT/fit/exdqlm_multivar/keep/q=95/outputs/DISC_variables_95_exAL_synth_DISC.RData"
)

all_fit_paths_present() {
  local path
  for path in "${fit_paths[@]}"; do
    [[ -f "$path" ]] || return 1
  done
  return 0
}

write_status "waiting" "Waiting for historical-support replay artifacts."
log "Waiting for historical-support replay artifacts."

if [[ -n "$RUN_PID" ]]; then
  while kill -0 "$RUN_PID" >/dev/null 2>&1; do
    sleep 30
  done
else
  until all_fit_paths_present; do
    sleep 30
  done
fi

if ! all_fit_paths_present; then
  write_status "failed" "Replay ended without all retained multivariate fit artifacts."
  log "Replay ended without all retained multivariate fit artifacts."
  exit 1
fi

write_status "refreshing" "Replay artifacts are present; refreshing article assets."
log "Replay artifacts are present; refreshing article assets."

python3 "$ARTICLE_ROOT/scripts/refresh_all_generated_assets.py" \
  --article-root "$ARTICLE_ROOT" \
  --workflow-root "$WORKFLOW_ROOT" \
  --runtime-root "$KEEP_RUNTIME_ROOT" \
  --multivar-support-run-root "$SUPPORT_RUN_ROOT" \
  --univar-runtime-root "$UNIVAR_RUNTIME_ROOT" \
  --strict-current-model-support

python3 "$WORKFLOW_ROOT/scripts/audit_current_model_output_support_contract.py"

write_status "completed" "Historical-support refresh and audits completed successfully."
log "Historical-support refresh and audits completed successfully."
