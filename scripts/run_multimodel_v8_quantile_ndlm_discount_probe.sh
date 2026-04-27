#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CONFIG="${MULTIMODEL_V8_QUANTILE_NDLM_DISCOUNT_PROBE_CONFIG:-$ROOT/config/multimodel_v8_quantile_ndlm_discount_probe_20260422.template.yaml}"
LAUNCH=0
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG="$2"
      shift 2
      ;;
    --launch)
      LAUNCH=1
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

BUILD_OUTPUT="$({ python3 scripts/build_multimodel_v8_quantile_ndlm_discount_probe_matrix_configs.py --config "$CONFIG" "${EXTRA_ARGS[@]}"; } 2>&1)"
printf '%s\n' "$BUILD_OUTPUT"

MATRIX_DIR="$(printf '%s\n' "$BUILD_OUTPUT" | awk -F= '/^matrix_dir=/{print $2}' | tail -n 1)"
if [[ -z "$MATRIX_DIR" ]]; then
  echo "Failed to resolve matrix_dir from builder output." >&2
  exit 1
fi

if [[ "$LAUNCH" -ne 1 ]]; then
  cat <<EOF2

Corrected quantile NDLM-discount probe scaffolding is ready.
No queue was launched.
Matrix dir: $MATRIX_DIR
To launch later, run:
  bash scripts/run_multimodel_v8_quantile_ndlm_discount_probe.sh --config "$CONFIG" --launch
EOF2
  exit 0
fi

LAUNCH_ENV="$MATRIX_DIR/launch_settings.env"
if [[ ! -f "$LAUNCH_ENV" ]]; then
  echo "Missing launch settings: $LAUNCH_ENV" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$LAUNCH_ENV"

QUEUE_ARGS=(
  --matrix-dir "$MATRIX_DIR"
  --artifact-root "$ARTIFACT_ROOT"
  --ordinary-max-concurrent "$ORDINARY_MAX_CONCURRENT"
  --pause-free-gb "$PAUSE_FREE_GB"
  --launch-free-gb "$LAUNCH_FREE_GB"
  --heavy-free-gb "$HEAVY_FREE_GB"
  --heavy-cutoff-max-concurrent "$HEAVY_CUTOFF_MAX_CONCURRENT"
  --poll-seconds "$POLL_SECONDS"
)

if [[ "${HEAVY_CUTOFF_BLOCKS_ORDINARY:-1}" == "0" ]]; then
  QUEUE_ARGS+=(--no-heavy-cutoff-blocks-ordinary)
fi

bash scripts/run_multimodel_v8_queue.sh "${QUEUE_ARGS[@]}"
