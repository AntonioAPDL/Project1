#!/usr/bin/env bash
set -euo pipefail

CAMPAIGN_ROOT="${1:?CAMPAIGN_ROOT is required}"
PRODUCT_ID="${2:?PRODUCT_ID is required}"
SESSION_NAME="${3:-${PRODUCT_ID}_$(date -u +%Y%m%dT%H%M%SZ)}"
DRY_RUN="${DRY_RUN:-0}"
ROOT="${PROJECT_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd}"

cd "$ROOT"
CMD_DIR="$CAMPAIGN_ROOT/commands"
LOG_DIR="$CAMPAIGN_ROOT/logs"
STATUS_DIR="$CAMPAIGN_ROOT/status"
mkdir -p "$CMD_DIR" "$LOG_DIR" "$STATUS_DIR"

COMMAND_PATH="$CMD_DIR/${PRODUCT_ID}_parallel_run.sh"
STDOUT_LOG="$LOG_DIR/${PRODUCT_ID}_parallel_stdout.log"
SESSION_FILE="$STATUS_DIR/parallel_sessions.txt"

cat > "$COMMAND_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
bash scripts/run_glofas_historical_product_campaign.sh "$PRODUCT_ID" "$CAMPAIGN_ROOT"
EOF
chmod +x "$COMMAND_PATH"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY-RUN] staged $COMMAND_PATH"
  echo "[DRY-RUN] session name: $SESSION_NAME"
  exit 0
fi

tmux new-session -d -s "$SESSION_NAME" "bash \"$COMMAND_PATH\" |& tee \"$STDOUT_LOG\""
echo "$SESSION_NAME" >> "$SESSION_FILE"
echo "[OK] launched $SESSION_NAME"
echo "[OK] command path: $COMMAND_PATH"
echo "[OK] stdout log: $STDOUT_LOG"
