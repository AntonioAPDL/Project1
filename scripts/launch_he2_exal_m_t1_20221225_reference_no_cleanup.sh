#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG="$(cd "${REPO_ROOT}/.." && pwd)/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/control/generated_configs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml"
if [ ! -f "$CONFIG" ]; then
  echo "Missing generated config: $CONFIG" >&2
  echo "Build the package first with scripts/build_he2_exal_m_t1_20221225_reference_relaunch_package.py" >&2
  exit 1
fi
exec "${SCRIPT_DIR}/run_unified_without_cleanup.sh" --config "$CONFIG"
