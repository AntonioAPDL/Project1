#!/usr/bin/env bash
set -euo pipefail

p0="${1:-0.5}"
seed="${2:-777}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

ts="$(date +%Y%m%d_%H%M%S)"
run_dir="repro/baseline_runs/${ts}_p0_${p0}_seed_${seed}"

mkdir -p "${run_dir}/run1" "${run_dir}/run2" "${run_dir}/inputs" "${run_dir}/meta"

{
  echo "TIMESTAMP: $(date -Is)"
  echo "REPO_ROOT: ${repo_root}"
  echo "P0: ${p0}"
  echo "SEED: ${seed}"
  echo "CMD: Rscript --vanilla scripts/run_DISC_Optimal_Synth_Ranges_W.R ${p0} ${seed}"
  echo "ENV: OMP_NUM_THREADS=${OMP_NUM_THREADS:-1} OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1} MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}"
  echo "GIT_HEAD: $(git rev-parse HEAD)"
  echo "GIT_BRANCH: $(git rev-parse --abbrev-ref HEAD)"
} | tee "${run_dir}/meta/command_and_env.txt" >/dev/null

git status -sb > "${run_dir}/meta/git_status.txt"
git log --oneline --decorate -n 30 > "${run_dir}/meta/git_log.txt"

# Inputs/outputs used by DISC_Optimal_Synth_Ranges_W.r (p0=0.5 baseline by default)
# (avoid python dependency)
p0_suffix="$(awk -v p0="${p0}" 'BEGIN { printf "%.0f", (p0 * 100.0) }')"
disc_rdata="DISC_variables_${p0_suffix}_exAL_synth_DISC.RData"
disc_rdata_path="${repo_root}/${disc_rdata}"

inputs=(
  "/data/muscat_data/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt"
  "/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv"
  "/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv"
  "${repo_root}/nws_forecast.csv"
  "${repo_root}/weighted_time_series.csv"
  "${repo_root}/prism_precipitation_santa_cruz_1987_2023.csv"
  "${repo_root}/soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv"
  "${repo_root}/pca.csv"
  "${repo_root}/retros_2022-12-25.csv"
  "${disc_rdata_path}"
)

printf "" > "${run_dir}/inputs/inputs.sha256"
for p in "${inputs[@]}"; do
  if [[ -e "$p" ]]; then
    sha256sum "$p" >> "${run_dir}/inputs/inputs.sha256"
  else
    echo "MISSING_INPUT: $p" >> "${run_dir}/inputs/inputs.sha256"
  fi
done

# Backup mutable input/output RData so both runs start from identical state.
cp --reflink=auto "${disc_rdata_path}" "${run_dir}/inputs/${disc_rdata}"

run_once () {
  local out_subdir="$1"
  local console_path="${run_dir}/${out_subdir}/console.txt"
  local sessinfo_path="${run_dir}/${out_subdir}/sessionInfo.txt"
  local outputs_path="${run_dir}/${out_subdir}/outputs.sha256"

  export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
  export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
  export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

  (
    set -x
    Rscript --vanilla repro/capture_sessionInfo_DISC_Optimal_Synth_Ranges_W.R "${sessinfo_path}"
    Rscript --vanilla scripts/run_DISC_Optimal_Synth_Ranges_W.R "${p0}" "${seed}"
  ) > "${console_path}" 2>&1

  printf "" > "${outputs_path}"
  if [[ -e "${disc_rdata_path}" ]]; then
    sha256sum "${disc_rdata_path}" >> "${outputs_path}"
  else
    echo "MISSING_OUTPUT: ${disc_rdata_path}" >> "${outputs_path}"
  fi
}

echo "== Stage 0 baseline: run 1 ==" | tee "${run_dir}/meta/progress.txt" >/dev/null
run_once "run1"

# Restore to exact initial state before run 2.
cp --reflink=auto "${run_dir}/inputs/${disc_rdata}" "${disc_rdata_path}"

echo "== Stage 0 baseline: run 2 ==" | tee -a "${run_dir}/meta/progress.txt" >/dev/null
run_once "run2"

echo "== Comparing outputs ==" | tee -a "${run_dir}/meta/progress.txt" >/dev/null
diff -u "${run_dir}/run1/outputs.sha256" "${run_dir}/run2/outputs.sha256" > "${run_dir}/meta/outputs_diff.txt" || true
diff -u "${run_dir}/run1/console.txt" "${run_dir}/run2/console.txt" > "${run_dir}/meta/console_diff.txt" || true

if [[ ! -s "${run_dir}/meta/outputs_diff.txt" ]]; then
  echo "PASS: outputs.sha256 identical" | tee -a "${run_dir}/meta/progress.txt" >/dev/null
else
  echo "FAIL: outputs.sha256 differ (see ${run_dir}/meta/outputs_diff.txt)" | tee -a "${run_dir}/meta/progress.txt" >/dev/null
  exit 2
fi

echo "DONE: ${run_dir}" | tee -a "${run_dir}/meta/progress.txt" >/dev/null
