#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(yaml))

args <- commandArgs(trailingOnly = TRUE)
repo_root <- normalizePath(
  if (length(args) >= 1L) args[[1]] else "/data/muscat_data/jaguir26/project1_ucsc_phd",
  mustWork = TRUE
)

run_ids <- c(
  "prod_phaseK3_batchA_20210123_l1_fix1_20260324",
  "prod_phaseK3_batchA_20210123_l2_20260324",
  "prod_phaseK3_batchA_20211112_l1_20260324",
  "prod_phaseK3_batchA_20211112_l2_20260324",
  "prod_phaseK3_batchB_20211221_l1_20260324",
  "prod_phaseK3_batchB_20211221_l2_20260324",
  "prod_phaseK3_batchB_20220511_l1_20260324",
  "prod_phaseK3_batchB_20220511_l2_20260324",
  "prod_phaseK3_batchC_20221225_l1_20260324",
  "prod_phaseK3_batchC_20221225_l2_20260324"
)

required_model_ids <- c(
  "dqlm_univar_al_synth",
  "dqlm_multivar_al_synth_drop",
  "dqlm_multivar_al_synth_keep",
  "ndlm_main_synth_keep",
  "ndlm_univar_synth_keep",
  "exdqlm_univar_synth",
  "exdqlm_multivar_synth_drop",
  "exdqlm_multivar_synth_keep",
  "ndlm_main_synth_drop"
)

run_root_for <- function(run_id) file.path(repo_root, "repro", "runs", run_id)
table_path_for <- function(run_id, name) {
  file.path(run_root_for(run_id), "post", "outputs", run_id, "tables", name)
}

read_manifest <- function(run_id) {
  path <- file.path(run_root_for(run_id), "run_manifest.yaml")
  if (!file.exists(path)) stop(sprintf("missing manifest for run_id=%s", run_id), call. = FALSE)
  read_yaml(path)
}

read_table_or_stop <- function(run_id, table_name) {
  path <- table_path_for(run_id, table_name)
  if (!file.exists(path)) stop(sprintf("missing table %s for run_id=%s", table_name, run_id), call. = FALSE)
  utils::read.csv(path, stringsAsFactors = FALSE)
}

union_rbind <- function(dfs) {
  cols <- unique(unlist(lapply(dfs, names), use.names = FALSE))
  padded <- lapply(dfs, function(df) {
    missing <- setdiff(cols, names(df))
    for (nm in missing) df[[nm]] <- NA
    df[, cols, drop = FALSE]
  })
  out <- do.call(rbind, padded)
  out[!duplicated(out), , drop = FALSE]
}

summaries <- list()
per_time <- list()
health <- list()
health_pt <- list()
coverage_rows <- list()

for (run_id in run_ids) {
  manifest <- read_manifest(run_id)
  cutoff <- gsub("-", "", manifest$run_id |> sub(".*_(\\d{8})_l[12]_.*", "\\1", x = _))
  if (!grepl("^\\d{8}$", cutoff)) {
    cutoff <- gsub("-", "", manifest$inputs[[1]]$path |> basename())
  }
  lane <- sub(".*_(l[12])_.*", "\\1", run_id)

  sum_df <- read_table_or_stop(run_id, "crps_forecast_summary.csv")
  sum_df$run_id <- run_id
  sum_df$cutoff <- cutoff
  sum_df$lane <- lane
  summaries[[run_id]] <- sum_df

  pt_df <- read_table_or_stop(run_id, "crps_forecast_per_time.csv")
  pt_df$run_id <- run_id
  pt_df$cutoff <- cutoff
  pt_df$lane <- lane
  per_time[[run_id]] <- pt_df

  h_df <- read_table_or_stop(run_id, "crps_input_health.csv")
  h_df$run_id <- run_id
  h_df$cutoff <- cutoff
  h_df$lane <- lane
  health[[run_id]] <- h_df

  hpt_df <- read_table_or_stop(run_id, "crps_input_health_per_time.csv")
  hpt_df$run_id <- run_id
  hpt_df$cutoff <- cutoff
  hpt_df$lane <- lane
  health_pt[[run_id]] <- hpt_df

  present <- sort(unique(sum_df$model_id))
  missing <- setdiff(required_model_ids, present)
  coverage_rows[[run_id]] <- data.frame(
    run_id = run_id,
    cutoff = cutoff,
    lane = lane,
    required_model_ids_pass = length(missing) == 0L,
    missing_model_ids = if (length(missing)) paste(missing, collapse = ",") else "",
    stringsAsFactors = FALSE
  )
}

summary_merged <- union_rbind(summaries)
per_time_merged <- union_rbind(per_time)
health_merged <- union_rbind(health)
health_pt_merged <- union_rbind(health_pt)
coverage_report <- do.call(rbind, coverage_rows)

health_fail_rows <- sum(tolower(trimws(health_merged$status)) == "fail")
health_fail_rows_pt <- sum(tolower(trimws(health_pt_merged$status)) == "fail")
overall_models_present <- sort(unique(summary_merged$model_id))
overall_missing <- setdiff(required_model_ids, overall_models_present)

timestamp <- format(Sys.time(), "%Y%m%dT%H%M%SZ", tz = "UTC")
out_dir <- file.path(repo_root, "exports", "benchmark_crps")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

summary_path <- file.path(out_dir, sprintf("crps_summary_merged_%s.csv", timestamp))
per_time_path <- file.path(out_dir, sprintf("crps_per_time_merged_%s.csv", timestamp))
health_path <- file.path(out_dir, sprintf("crps_input_health_merged_%s.csv", timestamp))
health_pt_path <- file.path(out_dir, sprintf("crps_input_health_per_time_merged_%s.csv", timestamp))
coverage_path <- file.path(out_dir, sprintf("coverage_report_%s.csv", timestamp))
manifest_path <- file.path(out_dir, sprintf("merge_manifest_%s.yaml", timestamp))

write.csv(summary_merged, summary_path, row.names = FALSE)
write.csv(per_time_merged, per_time_path, row.names = FALSE)
write.csv(health_merged, health_path, row.names = FALSE)
write.csv(health_pt_merged, health_pt_path, row.names = FALSE)
write.csv(coverage_report, coverage_path, row.names = FALSE)

write_yaml(list(
  timestamp_utc = timestamp,
  run_ids = run_ids,
  required_model_ids = required_model_ids,
  overall_required_model_ids_pass = length(overall_missing) == 0L,
  overall_missing_model_ids = overall_missing,
  crps_input_health_fail_rows = health_fail_rows,
  crps_input_health_fail_rows_per_time = health_fail_rows_pt,
  outputs = list(
    summary = summary_path,
    per_time = per_time_path,
    health = health_path,
    health_per_time = health_pt_path,
    coverage = coverage_path
  )
), manifest_path)

cat(summary_path, "\n", sep = "")
cat(per_time_path, "\n", sep = "")
cat(health_path, "\n", sep = "")
cat(health_pt_path, "\n", sep = "")
cat(coverage_path, "\n", sep = "")
cat(manifest_path, "\n", sep = "")
