#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" != "--config" ] || [ -z "${2:-}" ]; then
  echo "Usage: scripts/run_unified_without_cleanup.sh --config <config.yaml>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

LOCAL_LD_LIBRARY_PATH="/data/muscat_data/jaguir26/libs/lib64:/data/muscat_data/jaguir26/libs/boost/lib:/lib64"
export LD_LIBRARY_PATH="${LOCAL_LD_LIBRARY_PATH}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
export CLEANUP_RDATA_AFTER_POST=0

cd "${REPO_ROOT}"
exec Rscript --vanilla scripts/unified_run.R "$@"
