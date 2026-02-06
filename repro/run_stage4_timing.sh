#!/usr/bin/env bash
set -euo pipefail

p0="${1:-0.5}"
seed="${2:-777}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

ts="$(date +%Y%m%d_%H%M%S)"
run_dir="repro/perf/${ts}_p0_${p0}_seed_${seed}"

mkdir -p "${run_dir}"

{
  echo "TIMESTAMP: $(date -Is)"
  echo "REPO_ROOT: ${repo_root}"
  echo "P0: ${p0}"
  echo "SEED: ${seed}"
  echo "GIT_HEAD: $(git rev-parse HEAD)"
  echo "GIT_BRANCH: $(git rev-parse --abbrev-ref HEAD)"
} > "${run_dir}/git_rev.txt"

# Restore the locked initial state before running, because the workflow mutates
# DISC_variables_*.RData in-place.
p0_suffix="$(awk -v p0="${p0}" 'BEGIN { printf "%.0f", (p0 * 100.0) }')"
disc_rdata="DISC_variables_${p0_suffix}_exAL_synth_DISC.RData"
disc_rdata_path="${repo_root}/${disc_rdata}"

locked_inputs_dir="repro/baseline_runs/20260204_174008_p0_0.5_seed_777/inputs"
locked_rdata_path="${locked_inputs_dir}/${disc_rdata}"

if [[ ! -f "${locked_rdata_path}" ]]; then
  {
    echo "ERROR: locked baseline input not found for p0=${p0}"
    echo "Expected: ${locked_rdata_path}"
    echo "Hint: Stage 0 locked baseline is recorded for p0=0.5 only."
  } >&2
  exit 1
fi

cp --reflink=auto "${locked_rdata_path}" "${disc_rdata_path}"

# Time a single deterministic run.
/usr/bin/time -v -o "${run_dir}/time_v.txt" \
  Rscript --vanilla scripts/run_DISC_Optimal_Synth_Ranges_W.R "${p0}" "${seed}" \
  > "${run_dir}/console.txt" 2>&1

if [[ -f "${disc_rdata_path}" ]]; then
  sha256sum "${disc_rdata_path}" > "${run_dir}/sha256.txt"
else
  echo "MISSING_OUTPUT: ${disc_rdata_path}" > "${run_dir}/sha256.txt"
  exit 2
fi

echo "DONE: ${run_dir}"
