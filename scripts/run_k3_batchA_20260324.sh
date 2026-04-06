#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
BATCH_LOG="${REPO_ROOT}/repro/hardening_logs/J4_batch_monitor_${ts}.log"

CONFIGS=(
  "config/unified_runs/prod_phaseK3_batchA_20210123_l1_20260324.yaml"
  "config/unified_runs/prod_phaseK3_batchA_20210123_l2_20260324.yaml"
  "config/unified_runs/prod_phaseK3_batchA_20211112_l1_20260324.yaml"
  "config/unified_runs/prod_phaseK3_batchA_20211112_l2_20260324.yaml"
)

mkdir -p "$(dirname "${BATCH_LOG}")"

{
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "batch=batchA"
  echo "cutoffs=20210123 20211112"
  echo "configs=${CONFIGS[*]}"
  echo "runner=$(realpath "$0")"
} > "${BATCH_LOG}"

append_gate_block() {
  local cfg="$1"
  local run_id="$2"
  local lane="$3"
  local cutoff="$4"
  local launcher_log="$5"
  local expected_ndlm_mode="$6"

  Rscript --vanilla - "${REPO_ROOT}" "${run_id}" "${lane}" "${cutoff}" "${launcher_log}" "${expected_ndlm_mode}" "${BATCH_LOG}" <<'RS'
args <- commandArgs(trailingOnly = TRUE)
repo_root <- args[[1]]
run_id <- args[[2]]
lane <- args[[3]]
cutoff <- args[[4]]
launcher_log <- args[[5]]
expected_ndlm_mode <- args[[6]]
batch_log <- args[[7]]

suppressPackageStartupMessages(library(yaml))

run_root <- file.path(repo_root, "repro", "runs", run_id)
manifest_path <- file.path(run_root, "run_manifest.yaml")
crps_sum_path <- file.path(run_root, "post", "outputs", run_id, "tables", "crps_forecast_summary.csv")
crps_health_path <- file.path(run_root, "post", "outputs", run_id, "tables", "crps_input_health.csv")
crps_health_pt_path <- file.path(run_root, "post", "outputs", run_id, "tables", "crps_input_health_per_time.csv")
theory_path <- file.path(run_root, "fit", "ndlm_main", "logs", "ndlm_theory_summary.log")

required_ids <- switch(
  lane,
  l1 = c(
    "dqlm_univar_al_synth",
    "dqlm_multivar_al_synth_drop",
    "dqlm_multivar_al_synth_keep",
    "ndlm_main_synth_keep",
    "ndlm_univar_synth_keep"
  ),
  l2 = c(
    "exdqlm_univar_synth",
    "exdqlm_multivar_synth_drop",
    "exdqlm_multivar_synth_keep",
    "ndlm_main_synth_drop"
  ),
  stop(sprintf("unknown lane: %s", lane))
)

manifest <- read_yaml(manifest_path)
stage_pass <- all(vapply(c("fit", "post", "report"), function(s) identical(manifest$stages[[s]]$status, "pass"), logical(1)))

diag_paths <- sort(list.files(file.path(run_root, "fit", "diagnostics"), pattern = "_diagnostics\\.yaml$", recursive = TRUE, full.names = TRUE))
diag_statuses <- if (length(diag_paths)) {
  vapply(diag_paths, function(path) {
    x <- tryCatch(read_yaml(path), error = function(e) NULL)
    if (is.null(x) || is.null(x$status)) return(NA_character_)
    as.character(x$status)
  }, character(1))
} else {
  character(0)
}
diag_pass <- length(diag_paths) > 0L && all(diag_statuses == "pass")

crps_sum <- read.csv(crps_sum_path, stringsAsFactors = FALSE)
present_ids <- sort(unique(crps_sum$model_id))
missing_ids <- setdiff(required_ids, present_ids)
id_pass <- length(missing_ids) == 0L

crps_health <- read.csv(crps_health_path, stringsAsFactors = FALSE)
crps_health_pt <- read.csv(crps_health_pt_path, stringsAsFactors = FALSE)
health_fail_rows <- sum(tolower(trimws(crps_health$status)) == "fail")
health_fail_rows_pt <- sum(tolower(trimws(crps_health_pt$status)) == "fail")
health_pass <- health_fail_rows == 0L && health_fail_rows_pt == 0L

theory_lines <- readLines(theory_path, warn = FALSE)
mode_line <- sprintf("forecast_transfer_mode=%s", expected_ndlm_mode)
active_line <- if (identical(expected_ndlm_mode, "keep")) {
  "transfer_active_forecast_window=true"
} else {
  "transfer_active_forecast_window=false"
}
ndlm_mode_pass <- any(trimws(theory_lines) == mode_line) && any(trimws(theory_lines) == active_line)

rdata_count <- length(list.files(run_root, pattern = "\\.RData$", recursive = TRUE, full.names = TRUE))
cleanup_pass <- identical(rdata_count, 0L)

overall_pass <- stage_pass && diag_pass && id_pass && health_pass && ndlm_mode_pass && cleanup_pass

lines <- c(
  sprintf("=== run_id %s ===", run_id),
  sprintf("cutoff=%s", cutoff),
  sprintf("lane=%s", lane),
  sprintf("launcher_log=%s", launcher_log),
  sprintf("G1_stage_pass=%s", if (stage_pass) "pass" else "fail"),
  sprintf("G2_diag_pass=%s (n=%d)", if (diag_pass) "pass" else "fail", length(diag_paths)),
  sprintf("G3_required_model_ids=%s (missing=%s)", if (id_pass) "pass" else "fail", if (length(missing_ids)) paste(missing_ids, collapse = ",") else "<none>"),
  sprintf("G4_input_health=%s (fail_rows=%d, fail_rows_per_time=%d)", if (health_pass) "pass" else "fail", health_fail_rows, health_fail_rows_pt),
  sprintf("G5_ndlm_mode=%s (expected=%s)", if (ndlm_mode_pass) "pass" else "fail", expected_ndlm_mode),
  sprintf("G6_cleanup=%s (rdata_count=%d)", if (cleanup_pass) "pass" else "fail", rdata_count),
  sprintf("OVERALL=%s", if (overall_pass) "pass" else "fail"),
  sprintf("evidence_manifest=%s", manifest_path),
  sprintf("evidence_diag_dir=%s", file.path(run_root, "fit", "diagnostics")),
  sprintf("evidence_theory=%s", theory_path),
  sprintf("evidence_crps_summary=%s", crps_sum_path),
  sprintf("evidence_crps_health=%s", crps_health_path),
  sprintf("evidence_crps_health_per_time=%s", crps_health_pt_path)
)

write(lines, file = batch_log, append = TRUE)
if (!overall_pass) {
  quit(status = 1L)
}
RS
}

for cfg in "${CONFIGS[@]}"; do
  run_id="$(Rscript --vanilla -e "suppressPackageStartupMessages(library(yaml)); cat(read_yaml('${cfg}')\$run\$run_id)")"
  cutoff="$(Rscript --vanilla -e "suppressPackageStartupMessages(library(yaml)); x<-read_yaml('${cfg}'); cat(gsub('-', '', x\$dates\$cutoff_date))")"
  lane="$(basename "${cfg}" .yaml | awk -F'_' '{print $(NF-1)}')"
  expected_ndlm_mode="$(Rscript --vanilla -e "suppressPackageStartupMessages(library(yaml)); cat(read_yaml('${cfg}')\$models\$ndlm_main\$forecast_transfer_mode)")"
  launcher_log="${REPO_ROOT}/repro/hardening_logs/${run_id}.launcher.log"

  {
    echo "=== START run_id ${run_id} ==="
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "config=${cfg}"
    echo "cutoff=${cutoff}"
    echo "lane=${lane}"
  } >> "${BATCH_LOG}"

  if ! "${REPO_ROOT}/scripts/run_unified_with_cleanup.sh" --config "${cfg}" > "${launcher_log}" 2>&1; then
    {
      echo "RUN_EXIT=fail"
      echo "launcher_log=${launcher_log}"
    } >> "${BATCH_LOG}"
    exit 1
  fi

  echo "RUN_EXIT=pass" >> "${BATCH_LOG}"
  append_gate_block "${cfg}" "${run_id}" "${lane}" "${cutoff}" "${launcher_log}" "${expected_ndlm_mode}"
done

{
  echo "=== BATCH COMPLETE ==="
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "${BATCH_LOG}"

echo "${BATCH_LOG}"
