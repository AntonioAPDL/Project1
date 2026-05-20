#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(yaml)
  library(exdqlm)
  library(dlm)
})

args <- commandArgs(trailingOnly = TRUE)

get_arg <- function(flag, default = NULL) {
  idx <- match(flag, args)
  if (is.na(idx) || idx >= length(args)) {
    return(default)
  }
  args[[idx + 1L]]
}

config_path <- get_arg("--config")
source_run_root <- get_arg("--source-run-root")
report_dir <- get_arg("--report-dir")

if (is.null(config_path) || is.null(source_run_root) || is.null(report_dir)) {
  stop("Usage: audit_he2_exal_m_t1_dimension_contract.R --config <yaml> --source-run-root <run-root> --report-dir <dir>", call. = FALSE)
}

repo_root <- "/data/muscat_data/jaguir26/project1_ucsc_phd"
source(file.path(repo_root, "R", "unified", "config.R"))
source(file.path(repo_root, "R", "unified", "families", "shared_input_helpers.R"))
source(file.path(repo_root, "R", "unified", "families", "exdqlm_multivar_structure.R"))

cfg_raw <- yaml::read_yaml(config_path)
cfg <- unified_deep_merge(unified_config_defaults(), cfg_raw)
cfg <- unified_resolve_paths(cfg, repo_root = repo_root)
dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)

source_run_root <- normalizePath(source_run_root, mustWork = TRUE)
feature_csv <- file.path(source_run_root, "inputs", "shared", "covariates", "covariate_features.csv")
retros_csv <- file.path(source_run_root, "fit", "inputs", "retros_fit_adapter.csv")
cutoff_csv <- file.path(source_run_root, "post", "outputs", basename(source_run_root), "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv")

retros <- utils::read.csv(retros_csv, stringsAsFactors = FALSE)
cutoff_df <- utils::read.csv(cutoff_csv, stringsAsFactors = FALSE)
history_dates <- as.Date(retros$Date)
forecast_dates <- sort(unique(as.Date(cutoff_df$date)))

selected_features <- unified_resolve_transfer_feature_columns(cfg)
design <- family_shared_build_featurecov_design_matrices(
  history_df = data.frame(
    ppt = rep(NA_real_, length(history_dates)),
    soil = rep(NA_real_, length(history_dates)),
    Static_PCA = rep(NA_real_, length(history_dates))
  ),
  forecast_df = data.frame(
    ppt = rep(NA_real_, length(forecast_dates)),
    soil = rep(NA_real_, length(forecast_dates)),
    Static_PCA = rep(NA_real_, length(forecast_dates))
  ),
  history_dates = history_dates,
  forecast_dates = forecast_dates,
  feature_path = feature_csv,
  fill_value = 0,
  selected_feature_names = selected_features
)

Y <- t(as.matrix(retros[, c("USGS", "GloFAS", "NWS3.0")]))
s_yy <- stats::sd(Y, na.rm = TRUE)
m_yy <- mean(Y, na.rm = TRUE) + s_yy * stats::qnorm(0.5)
kk <- 0.5 * s_yy

structure_cfg <- unified_get(
  cfg,
  c("models", "exdqlm_multivar", "structure"),
  default = list(include_trend = TRUE, enabled_harmonic_indices = c(1L, 2L, 3L))
)
state_cfg <- unified_get(cfg, c("models", "exdqlm_multivar", "state_evolution"), default = list())
lam1 <- as.numeric(unified_get(cfg, c("fit", "exdqlm_multivar", "legacy", "lam1"), default = 1 - 1e-6))
lam2 <- as.numeric(unified_get(cfg, c("fit", "exdqlm_multivar", "legacy", "lam2"), default = 1 - 1e-6))

structure_model <- exdqlm_multivar_build_structure(
  m_yy = m_yy,
  kk = kk,
  df_t = as.numeric(state_cfg$df_t),
  df_s1 = as.numeric(state_cfg$df_s1),
  df_s2 = as.numeric(state_cfg$df_s2),
  df_s67 = as.numeric(state_cfg$df_s67),
  lam1 = lam1,
  lam2 = lam2,
  include_trend = isTRUE(structure_cfg$include_trend),
  enabled_harmonic_indices = structure_cfg$enabled_harmonic_indices
)

response_channels <- c("USGS", "GloFAS", "NWS3.0")
J <- length(response_channels) - 1L
p <- as.integer(structure_model$p)
px <- as.integer(ncol(design$X))
ppx <- as.integer(px + 1L)
total_state <- as.integer(p * (J + 1L) + ppx)
segment_state_dims <- vapply(seq_len(J), function(seg) as.integer(p * (J - seg + 2L) + ppx), integer(1))

audited_files <- c(
  "R/environmetrics/10_data_inputs.R",
  "R/environmetrics/20_model_setup.R",
  "R/disc_w/03_covariates_standardize.R",
  "R/unified/families/shared_input_helpers.R",
  "R/unified/stages/stage_fit.R",
  "R/unified/stages/stage_post.R",
  "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r"
)
hardcoded_patterns <- c(
  "p\\s*=\\s*7\\b",
  "ppx\\s*=\\s*14\\b",
  "35\\s*x\\s*12995",
  "35\\s*by\\s*12995"
)

scan_rows <- list()
for (rel in audited_files) {
  text <- readLines(file.path(repo_root, rel), warn = FALSE)
  for (pat in hardcoded_patterns) {
    hit <- any(grepl(pat, text, perl = TRUE))
    scan_rows[[length(scan_rows) + 1L]] <- data.frame(
      file = rel,
      pattern = pat,
      found = hit,
      stringsAsFactors = FALSE
    )
  }
}
scan_df <- do.call(rbind, scan_rows)

summary <- list(
  config = normalizePath(config_path, mustWork = TRUE),
  source_run_root = source_run_root,
  selected_transfer_features = selected_features,
  include_trend = isTRUE(structure_cfg$include_trend),
  enabled_harmonic_indices = as.integer(unlist(structure_cfg$enabled_harmonic_indices, use.names = FALSE)),
  enabled_harmonic_count = length(structure_model$enabled_harmonics),
  p = p,
  px = px,
  ppx = ppx,
  J = J,
  total_state = total_state,
  segment_state_dims = as.integer(segment_state_dims),
  history_design_dim = c(nrow(design$X), ncol(design$X)),
  forecast_design_dim = c(nrow(design$X_f), ncol(design$X_f)),
  hardcoded_hits = subset(scan_df, found)
)

summary_json <- file.path(report_dir, "summary.json")
writeLines(jsonlite::toJSON(summary, pretty = TRUE, auto_unbox = TRUE), summary_json)
utils::write.csv(
  data.frame(
    key = c("p", "px", "ppx", "J", "total_state"),
    value = c(p, px, ppx, J, total_state)
  ),
  file.path(report_dir, "dimension_summary.csv"),
  row.names = FALSE
)
utils::write.csv(
  data.frame(segment = seq_along(segment_state_dims), state_dim = segment_state_dims),
  file.path(report_dir, "segment_state_dims.csv"),
  row.names = FALSE
)
utils::write.csv(
  data.frame(feature = selected_features),
  file.path(report_dir, "selected_transfer_features.csv"),
  row.names = FALSE
)
utils::write.csv(scan_df, file.path(report_dir, "hardcoded_dimension_scan.csv"), row.names = FALSE)

lines <- c(
  "# HE2 exAL-M-T1 Reduced-Spec Dimension Audit",
  "",
  sprintf("- config: `%s`", normalizePath(config_path, mustWork = TRUE)),
  sprintf("- source_run_root: `%s`", source_run_root),
  "",
  "## Requested structure",
  sprintf("- include_trend: `%s`", isTRUE(structure_cfg$include_trend)),
  sprintf("- enabled_harmonic_indices: `%s`", paste(as.integer(unlist(structure_cfg$enabled_harmonic_indices, use.names = FALSE)), collapse = ",")),
  sprintf("- selected_transfer_features: `%s`", paste(selected_features, collapse = ",")),
  "",
  "## Derived dimensions",
  sprintf("- p: `%d`", p),
  sprintf("- px: `%d`", px),
  sprintf("- ppx: `%d`", ppx),
  sprintf("- J: `%d`", J),
  sprintf("- total_state: `%d`", total_state),
  sprintf("- segment_state_dims: `%s`", paste(segment_state_dims, collapse = ",")),
  sprintf("- history_design_dim: `%d x %d`", nrow(design$X), ncol(design$X)),
  sprintf("- forecast_design_dim: `%d x %d`", nrow(design$X_f), ncol(design$X_f)),
  "",
  "## Hardcoded dimension scan",
  sprintf("- audited_files: `%d`", length(audited_files)),
  sprintf("- suspicious_hits: `%d`", sum(scan_df$found)),
  "",
  if (sum(scan_df$found) == 0L) "- No scanned files matched the targeted hardcoded-dimension patterns." else paste0("- Hits remain in: ", paste(unique(scan_df$file[scan_df$found]), collapse = ", "))
)
writeLines(lines, file.path(report_dir, "HE2_EXAL_M_T1_REDUCED_SPEC_DIMENSION_AUDIT_20260519.md"))

cat(jsonlite::toJSON(summary, pretty = TRUE, auto_unbox = TRUE))
