#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <config-yaml>" >&2
  exit 1
fi

CONFIG_PATH="$1"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
R440_ROOT="${R440_ROOT:-${REPO_ROOT}/repro/runtime/r-4.4.0/install}"
R440_BIN="${R440_ROOT}/bin/Rscript"
R440_R_HOME="${R440_ROOT}/lib64/R"

if [[ ! -x "${R440_BIN}" ]]; then
  echo "Missing R 4.4.0 runtime: ${R440_BIN}" >&2
  echo "Build it first with scripts/bootstrap_r440_runtime.sh" >&2
  exit 1
fi

export R_LIBS="/home/jaguir26/R/x86_64-redhat-linux-gnu-library/4.4"
export R_LIBS_USER=""
export R_LIBS_SITE=""
export R_HOME="${R440_R_HOME}"
export PATH="${R440_ROOT}/bin:${PATH}"
export ENVIRONMETRICS_LIBS_ONLY="1"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

cd "${REPO_ROOT}"
"${R440_BIN}" --vanilla scripts/unified_run.R --config "${CONFIG_PATH}"
