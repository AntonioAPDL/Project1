#!/usr/bin/env bash
set -euo pipefail

RECOVERY_RUN_ROOT="${1:?RECOVERY_RUN_ROOT is required}"
LAUNCH_ID="${2:-glofas_operational_parallel_$(date -u +%Y%m%dT%H%M%SZ)}"
NUM_SPLITS="${3:-6}"
DRY_RUN="${DRY_RUN:-0}"
ROOT="${PROJECT_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd}"

cd "$ROOT"
RUN_ROOT="$(python3 - <<'PY' "$RECOVERY_RUN_ROOT"
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"

CAMPAIGN_ROOT="$RUN_ROOT/family=glofas_operational_forecasts/full_runs/$LAUNCH_ID"
PLAN_ROOT="$CAMPAIGN_ROOT/plans"
DOWNLOAD_ROOT="$CAMPAIGN_ROOT/outputs/download_root"
EXTRACT_ROOT="$CAMPAIGN_ROOT/outputs/forecast_cache/glofas"
MANIFEST_DIR="$CAMPAIGN_ROOT/manifests"
LOG_DIR="$CAMPAIGN_ROOT/logs"
CMD_DIR="$CAMPAIGN_ROOT/commands"
STATUS_DIR="$CAMPAIGN_ROOT/status"
HEALTH_DIR="$CAMPAIGN_ROOT/health_checks"
mkdir -p "$PLAN_ROOT" "$DOWNLOAD_ROOT" "$EXTRACT_ROOT" "$MANIFEST_DIR" "$LOG_DIR" "$CMD_DIR" "$STATUS_DIR" "$HEALTH_DIR"

PLAN_CMD="$CMD_DIR/build_split_plan.sh"
cat > "$PLAN_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
python3 scripts/build_glofas_operational_split_plan.py \
  --out-dir "$PLAN_ROOT" \
  --num-splits "$NUM_SPLITS"
EOF
chmod +x "$PLAN_CMD"

bash "$PLAN_CMD" > "$LOG_DIR/build_split_plan.log"

SESSION_FILE="$STATUS_DIR/tmux_sessions.txt"
: > "$SESSION_FILE"

SUMMARY_CSV="$PLAN_ROOT/split_summary.csv"
if [[ ! -f "$SUMMARY_CSV" ]]; then
  echo "[ERR] missing split summary: $SUMMARY_CSV" >&2
  exit 1
fi

while IFS=, read -r split_id issue_count first_issue_date last_issue_date interval_count intervals_compact; do
  if [[ "$split_id" == "split_id" ]]; then
    continue
  fi
  split_cmd="$CMD_DIR/${split_id}_download.sh"
  split_manifest="$MANIFEST_DIR/${split_id}_download_manifest.csv"
  split_log="$LOG_DIR/${split_id}_download_internal.log"
  split_intervals="$PLAN_ROOT/splits/${split_id}_intervals.csv"
  cat > "$split_cmd" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
python3 glofas_operational_mediumrange_download_point.py \
  --run \
  --intervals-file "$split_intervals" \
  --out-root "$DOWNLOAD_ROOT" \
  --manifest-path "$split_manifest" \
  --log-path "$split_log" \
  --lat 37.0443931 \
  --lon -122.072464 \
  --verbose
EOF
  chmod +x "$split_cmd"
done < "$SUMMARY_CSV"

EXTRACT_CMD="$CMD_DIR/run_extract_all.sh"
cat > "$EXTRACT_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
python3 scripts/forecats_extract_glofas_batch.py \
  --grib-root "$DOWNLOAD_ROOT/grib" \
  --dates-file "$PLAN_ROOT/all_issue_dates.txt" \
  --out-root "$EXTRACT_ROOT" \
  --lat 37.0443931 \
  --lon -122.072464 \
  --var dis24 \
  --control-dtype cf \
  --perturbed-dtype pf \
  --cell-policy nearest_valid \
  --shift-days 1 \
  --post-days 28 \
  --verbose
EOF
chmod +x "$EXTRACT_CMD"

HEALTH_CMD="$CMD_DIR/check_parallel_health.sh"
cat > "$HEALTH_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
python3 scripts/check_glofas_operational_parallel_health.py \
  --campaign-root "$CAMPAIGN_ROOT" \
  --out-json "$HEALTH_DIR/parallel_download_health.json"
EOF
chmod +x "$HEALTH_CMD"

python3 - <<'PY' "$CAMPAIGN_ROOT/launch_manifest.json" "$RUN_ROOT" "$CAMPAIGN_ROOT" "$PLAN_ROOT" "$DOWNLOAD_ROOT" "$EXTRACT_ROOT" "$NUM_SPLITS"
import json
import sys
payload = {
    "recovery_run_root": sys.argv[2],
    "campaign_root": sys.argv[3],
    "plan_root": sys.argv[4],
    "download_root": sys.argv[5],
    "extract_root": sys.argv[6],
    "num_splits": int(sys.argv[7]),
    "notes": [
        "This launcher stages only the parallel download sessions.",
        "Use commands/run_extract_all.sh after the split downloads finish.",
        "Use commands/check_parallel_health.sh anytime for a manifest-based health snapshot.",
    ],
}
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
PY

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY-RUN] staged $CAMPAIGN_ROOT"
  cat "$SUMMARY_CSV"
  exit 0
fi

launch_tmux() {
  local session_name="$1"
  local command_path="$2"
  local stdout_log="$3"
  tmux new-session -d -s "$session_name" "bash \"$command_path\" |& tee \"$stdout_log\""
  echo "$session_name" >> "$SESSION_FILE"
  echo "[OK] launched $session_name"
}

while IFS=, read -r split_id issue_count first_issue_date last_issue_date interval_count intervals_compact; do
  if [[ "$split_id" == "split_id" ]]; then
    continue
  fi
  session_name="${split_id}_${LAUNCH_ID}"
  launch_tmux "$session_name" "$CMD_DIR/${split_id}_download.sh" "$LOG_DIR/${split_id}_stdout.log"
done < "$SUMMARY_CSV"

bash "$HEALTH_CMD" |& tee "$LOG_DIR/parallel_health_initial.log" || true

echo "[OK] launched operational split sessions"
echo "[OK] campaign root: $CAMPAIGN_ROOT"
echo "[OK] session list: $SESSION_FILE"
echo "[OK] follow-on extract command: $EXTRACT_CMD"
