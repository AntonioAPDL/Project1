#!/usr/bin/env bash
set -euo pipefail

root="/data/muscat_data/jaguir26/project1_ucsc_phd"
cd "$root"
out_dir="config/unified_runs"
mkdir -p "$out_dir"

PARAMETERS="/data/muscat_data/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt"
RETROS="/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20210123/inputs/shared/forecats_bundle/retros.csv"
NWS="/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20210123/inputs/shared/forecats_bundle/nws_forecast.csv"
GLOFAS="/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20210123/inputs/shared/forecats_bundle/glofas_forecast.csv"
ELI="/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_1_ELI.csv"
ONI="/data/muscat_data/jaguir26/projects/Project/Input/exAL/covariates/cov_2_ONI.csv"
PPT="/data/muscat_data/jaguir26/project1_ucsc_phd/prism_precipitation_santa_cruz_1987_2023.csv"
SOIL="/data/muscat_data/jaguir26/project1_ucsc_phd/soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv"
PCA="/data/muscat_data/jaguir26/project1_ucsc_phd/pca.csv"

write_common() {
  local run_id="$1"
  cat <<YAML
config_version: 1
run:
  run_id: ${run_id}
  run_root: repro/runs
  repro_mode: strict
  seed: 777
  overwrite: no
  auto_suffix_on_collision: yes
  dry_run: no
  git_require_clean: no
  threads:
    omp: 1
    openblas: 1
    mkl: 1
    veclib: 1
    numexpr: 1
    mc_cores: 1
stages:
  forecats: no
  data_prep_shared: yes
  fit: yes
  post: yes
  validate: no
  report: yes
site:
  usgs_site: '11160500'
  lat: 37.0443931
  lon: -122.072464
dates:
  cutoff_date: '2021-01-23'
  plot_start: '2021-01-05'
  plot_end: '2021-02-20'
  data_start: '2010-01-01'
inputs:
  fit:
    parameters_path: ${PARAMETERS}
    retros_path: ${RETROS}
    retros_storage_scale: log1p_cms
    nws_forecast_path: ${NWS}
    nws_storage_scale: raw_cms
    glofas_forecast_path: ${GLOFAS}
    glofas_storage_scale: raw_cms
    usgs_mode: live
    usgs_cache_path: ~
    covariates:
    - name: ELI
      path: ${ELI}
    - name: ONI
      path: ${ONI}
    - name: PPT
      path: ${PPT}
    - name: SOIL
      path: ${SOIL}
    - name: PCA
      path: ${PCA}
  post:
    use_fit_outputs_from_run: yes
  forecats:
    mode: use_existing
    pipeline_config_path: config/forecats_pipeline.template.yaml
    existing_bundle_path: ~
    snapshot:
      enabled: no
  shared:
    prefer_forecats_snapshot: no
post:
  figures: yes
  smoke_fast: no
  force_isolation_smoke_fast: no
  profile: no
  profile_detail: no
  allow_legacy_root_fallback: no
  sort_keep_na: yes
  export_tables: yes
  table_formats:
  - csv
  crps_input_health:
    enabled: yes
    fail_fast: yes
    min_finite_share: 1.0
    max_abs: 50.0
validation:
  profile: smoke
  canonical_run_id: __SELF__
  compare:
    mode: none
    numeric_abs_tol: 0.0
    numeric_rel_tol: 0.0
    pixel_max_abs_tol: 0.0
scale_contract:
  canonical_storage_scale: raw_cms
  legacy_fit_input_scale: log1p_cms
  legacy_post_input_scale: log1p_cms
  analysis_scale_fit_internal: log_log1p_cms
  analysis_scale_post_internal: log_log1p_cms
write_audit:
  enabled: yes
  enforce_from_stage: 4
  allowlist_outside_run_root: []
YAML
}

{
  write_common repair_r1_ndlm_main_drop_20210123_20260324
  cat <<'YAML'
models:
  run_exdqlm_multivar: no
  run_exdqlm_univar: no
  run_ndlm_main: yes
  run_ndlm_univar: no
  ndlm_main:
    implementation_mode: theory_aligned
    kalman_backend: cpp
    forecast_transfer_mode: drop
fit:
  quantiles: [0.50]
  parallel:
    mode: one_core_per_model
  warm_start:
    enabled: no
    mode: resume
  ndlm_main:
    gamma_sigma:
      min_total_iters: 50
      max_iter: 100
      convergence_tol: 1.0e-06
      convergence:
        elbo_tol: 1.0e-06
        elbo_rel_tol: 0.00025
  contract_checks:
    enabled: yes
    fail_fast: yes
    write_reports: yes
  diagnostics:
    enabled: yes
    fail_fast: yes
    write_reports: yes
    max_time_checks: 5000
    seed: 777
    psd_tol: -1.0e-08
YAML
} > "$out_dir/repair_r1_ndlm_main_drop_20210123_20260324.yaml"

{
  write_common repair_r1_ndlm_main_keep_20210123_20260324
  cat <<'YAML'
models:
  run_exdqlm_multivar: no
  run_exdqlm_univar: no
  run_ndlm_main: yes
  run_ndlm_univar: no
  ndlm_main:
    implementation_mode: theory_aligned
    kalman_backend: cpp
    forecast_transfer_mode: keep
fit:
  quantiles: [0.50]
  parallel:
    mode: one_core_per_model
  warm_start:
    enabled: no
    mode: resume
  ndlm_main:
    gamma_sigma:
      min_total_iters: 50
      max_iter: 100
      convergence_tol: 1.0e-06
      convergence:
        elbo_tol: 1.0e-06
        elbo_rel_tol: 0.00025
  contract_checks:
    enabled: yes
    fail_fast: yes
    write_reports: yes
  diagnostics:
    enabled: yes
    fail_fast: yes
    write_reports: yes
    max_time_checks: 5000
    seed: 777
    psd_tol: -1.0e-08
YAML
} > "$out_dir/repair_r1_ndlm_main_keep_20210123_20260324.yaml"

{
  write_common repair_r1_ndlm_univar_keep_20210123_20260324
  cat <<'YAML'
models:
  run_exdqlm_multivar: no
  run_exdqlm_univar: no
  run_ndlm_main: no
  run_ndlm_univar: yes
  ndlm_univar:
    implementation_mode: theory_aligned_closed_form
    kalman_backend: cpp
    forecast_transfer_mode: keep
    horizon_cap: 90
    posterior_draws: 64
    prior:
      n0: 20
      S0: 1
fit:
  quantiles: [0.50]
  parallel:
    mode: one_core_per_model
  warm_start:
    enabled: no
    mode: resume
  contract_checks:
    enabled: yes
    fail_fast: yes
    write_reports: yes
  diagnostics:
    enabled: yes
    fail_fast: yes
    write_reports: yes
    max_time_checks: 5000
    seed: 777
    psd_tol: -1.0e-08
YAML
} > "$out_dir/repair_r1_ndlm_univar_keep_20210123_20260324.yaml"

{
  write_common repair_r1_univar_exal_triage_20210123_20260324
  cat <<'YAML'
models:
  run_exdqlm_multivar: no
  run_exdqlm_univar: yes
  run_ndlm_main: no
  run_ndlm_univar: no
  exdqlm_univar:
    implementation_mode: legacy_bridge
    likelihood_mode: exal
fit:
  quantiles: [0.05, 0.50, 0.95]
  parallel:
    mode: one_core_per_model
  warm_start:
    enabled: no
    mode: resume
  contract_checks:
    enabled: yes
    fail_fast: yes
    write_reports: yes
  diagnostics:
    enabled: yes
    fail_fast: yes
    write_reports: yes
    max_time_checks: 5000
    seed: 777
    psd_tol: -1.0e-08
YAML
} > "$out_dir/repair_r1_univar_exal_triage_20210123_20260324.yaml"

{
  write_common repair_r1_univar_al_triage_20210123_20260324
  cat <<'YAML'
models:
  run_exdqlm_multivar: no
  run_exdqlm_univar: yes
  run_ndlm_main: no
  run_ndlm_univar: no
  exdqlm_univar:
    implementation_mode: legacy_bridge
    likelihood_mode: al
fit:
  quantiles: [0.05, 0.50, 0.95]
  parallel:
    mode: one_core_per_model
  warm_start:
    enabled: no
    mode: resume
  contract_checks:
    enabled: yes
    fail_fast: yes
    write_reports: yes
  diagnostics:
    enabled: yes
    fail_fast: yes
    write_reports: yes
    max_time_checks: 5000
    seed: 777
    psd_tol: -1.0e-08
YAML
} > "$out_dir/repair_r1_univar_al_triage_20210123_20260324.yaml"

echo "REPAIR_CONFIGS_WRITTEN $out_dir"
