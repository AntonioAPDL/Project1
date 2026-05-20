#!/usr/bin/env Rscript

parse_args <- function(argv) {
  out <- list()
  i <- 1L
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (!startsWith(key, "--")) {
      i <- i + 1L
      next
    }
    key <- sub("^--", "", key)
    key <- gsub("-", "_", key, fixed = TRUE)
    if (i == length(argv) || startsWith(argv[[i + 1L]], "--")) {
      out[[key]] <- TRUE
      i <- i + 1L
    } else {
      out[[key]] <- argv[[i + 1L]]
      i <- i + 2L
    }
  }
  out
}

`%||%` <- function(x, y) {
  if (is.null(x) || identical(x, "") || (length(x) == 1L && is.na(x))) y else x
}

require_pkg <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(sprintf("Package '%s' is required.", pkg), call. = FALSE)
  }
}

write_csv_det <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(df, path, row.names = FALSE)
}

quantile_labels <- c("q05", "q20", "q35", "q50", "q65", "q80", "q95")
quantile_suffixes <- c("5", "20", "35", "50", "65", "80", "95")
quantile_probs <- c(0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95)
palette_quantiles <- c(
  q05 = "#9B1D20",
  q20 = "#C45D38",
  q35 = "#E38D2C",
  q50 = "#6A3D9A",
  q65 = "#2E86AB",
  q80 = "#1F9E89",
  q95 = "#006D2C"
)

palette_components <- c(
  "USGS fit input" = "#1B1B1B",
  "USGS exps" = "#7B3294",
  "USGS state-reconstructed" = "#1F78B4",
  "USGS without transfer" = "#2166AC",
  "Transfer zeta" = "#B2182B",
  "Trend aggregate" = "#4D4D4D",
  "Season aggregate" = "#E08214"
)

resolve_covariate_path_by_name <- function(cfg, name) {
  covs <- cfg$inputs$fit$covariates
  if (!is.list(covs) || length(covs) < 1L) {
    stop("Resolved config has no fit covariates block.", call. = FALSE)
  }
  idx <- vapply(
    covs,
    function(x) identical(as.character(x$name %||% ""), name),
    logical(1)
  )
  if (!any(idx)) {
    stop(sprintf("Could not resolve covariate path for %s", name), call. = FALSE)
  }
  as.character(covs[[which(idx)[1L]]]$path)
}

prepare_rebuild_context <- function(run_root, repo_root, cfg) {
  cutoff_date <- as.Date(cfg$dates$cutoff_date)
  if (is.na(cutoff_date)) {
    stop("Resolved config cutoff_date is invalid.", call. = FALSE)
  }
  forecast_start_date <- cutoff_date + 1L
  scale_contract <- cfg$scale_contract %||% list()
  legacy_fit_scale <- as.character(scale_contract$legacy_fit_input_scale %||% "log1p_cms")
  analysis_fit_scale <- as.character(scale_contract$analysis_scale_fit_internal %||% legacy_fit_scale)
  legacy_post_scale <- as.character(scale_contract$legacy_post_input_scale %||% legacy_fit_scale)
  analysis_post_scale <- as.character(scale_contract$analysis_scale_post_internal %||% analysis_fit_scale)

  enabled_harmonics <- cfg$models$exdqlm_multivar$structure$enabled_harmonic_indices
  if (is.null(enabled_harmonics) || length(enabled_harmonics) < 1L) {
    enabled_harmonics <- c(1L, 2L, 3L)
  }
  include_trend <- cfg$models$exdqlm_multivar$structure$include_trend
  if (is.null(include_trend)) include_trend <- TRUE

  Sys.setenv(
    ENV_PROJECT_ROOT = repo_root,
    UNIFIED_RUN_ROOT = run_root,
    UNIFIED_CUTOFF_DATE = as.character(cutoff_date),
    UNIFIED_FORECAST_START_DATE = as.character(forecast_start_date),
    ENV_RETROS_PATH = file.path(run_root, "fit", "inputs", "retros_fit_adapter.csv"),
    ENV_GLOFAS_FORECAST_PATH = file.path(run_root, "fit", "inputs", "glofas_fit_adapter.csv"),
    ENV_NWS_FORECAST_PATH = file.path(run_root, "fit", "inputs", "nws_fit_adapter.csv"),
    UNIFIED_USGS_DAILY_CSV = as.character(cfg$inputs$fit$usgs_cache_path),
    ENV_PPT_PATH = resolve_covariate_path_by_name(cfg, "PPT"),
    ENV_SOIL_PATH = resolve_covariate_path_by_name(cfg, "SOIL"),
    ENV_PCA_PATH = resolve_covariate_path_by_name(cfg, "PCA"),
    UNIFIED_COVARIATE_FEATURES_CSV = file.path(run_root, "inputs", "shared", "covariates", "covariate_features.csv"),
    UNIFIED_LEGACY_FIT_INPUT_SCALE = legacy_fit_scale,
    UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL = analysis_fit_scale,
    UNIFIED_LEGACY_POST_INPUT_SCALE = legacy_post_scale,
    UNIFIED_ANALYSIS_SCALE_POST_INTERNAL = analysis_post_scale,
    DISC_W_INCLUDE_TREND = if (isTRUE(include_trend)) "TRUE" else "FALSE",
    DISC_W_ENABLED_HARMONIC_INDICES = paste(as.integer(enabled_harmonics), collapse = ","),
    UNIFIED_MULTIVAR_FORECAST_TRANSFER_MODE = as.character(cfg$models$exdqlm_multivar$forecast_transfer_mode %||% "keep")
  )

  suppressPackageStartupMessages({
    library(Matrix)
    library(readr)
    library(lubridate)
    library(truncnorm)
    library(dlm)
    library(exdqlm)
  })

  source(file.path(repo_root, "R", "unified", "utils_scale.R"))
  source(file.path(repo_root, "R", "unified", "families", "shared_input_helpers.R"))
  source(file.path(repo_root, "R", "environmetrics", "00_paths.R"))
  DATA_CBIND_RDS <<- tempfile(fileext = ".rds")
  DATA_CBIND_CSV <<- tempfile(fileext = ".csv")
  source(file.path(repo_root, "R", "environmetrics", "00_constants.R"))
  source(file.path(repo_root, "R", "environmetrics", "02_helpers_core.R"))
  source(file.path(repo_root, "R", "environmetrics", "10_data_inputs.R"))
  source(file.path(repo_root, "R", "environmetrics", "20_model_setup.R"))

  ff_base <- as.numeric(model_simp$FF[seq_len(p), 1L, 1L])
  enabled_harmonics_resolved <- if (exists("harm", inherits = TRUE)) as.numeric(harm) else numeric(0)
  trend_dim <- if (isTRUE(include_trend)) 1L else 0L
  season_start <- trend_dim + 1L
  season_end <- trend_dim + 2L * length(enabled_harmonics_resolved)
  season_idx <- if (season_start <= season_end) seq.int(season_start, season_end) else integer(0)
  trend_idx <- if (trend_dim > 0L) seq_len(trend_dim) else integer(0)

  list(
    cutoff_date = cutoff_date,
    hist_dates = as.Date(timestamps),
    observed_usgs = as.numeric(Y[1L, ]),
    TT = as.integer(TT),
    p = as.integer(p),
    J = as.integer(J),
    ppx = as.integer(ppx),
    ff_base = ff_base,
    trend_idx = trend_idx,
    season_idx = season_idx,
    core_hist_dim = as.integer(p * (J + 1L)),
    forecast_transfer_mode = as.character(cfg$models$exdqlm_multivar$forecast_transfer_mode %||% "keep")
  )
}

extract_quantile_state <- function(rdata_path, quant_suffix, TT_hist) {
  env <- new.env(parent = baseenv())
  on.exit({
    rm(list = ls(env, all.names = TRUE), envir = env)
    gc(verbose = FALSE)
  }, add = TRUE)
  load(rdata_path, envir = env)
  theta_name <- sprintf("new.theta.out_%s_exAL_synth_DISC", quant_suffix)
  if (!exists(theta_name, envir = env, inherits = FALSE)) {
    stop(sprintf("Missing %s in %s", theta_name, rdata_path), call. = FALSE)
  }
  theta_obj <- get(theta_name, envir = env, inherits = FALSE)
  exps <- as.matrix(theta_obj$exps)
  sm <- as.matrix(theta_obj$sm)
  if (nrow(exps) < 1L || ncol(exps) < TT_hist) {
    stop(sprintf("Invalid exps dimensions in %s", rdata_path), call. = FALSE)
  }
  if (ncol(sm) < TT_hist) {
    stop(sprintf("Invalid sm dimensions in %s", rdata_path), call. = FALSE)
  }
  list(
    exps_usgs = as.numeric(exps[1L, seq_len(TT_hist)]),
    sm = sm[, seq_len(TT_hist), drop = FALSE]
  )
}

compute_history_components <- function(state_payload, ctx) {
  sm <- state_payload$sm
  TT_hist <- ctx$TT
  p <- ctx$p
  J <- ctx$J
  ff_base <- ctx$ff_base
  core_hist_dim <- ctx$core_hist_dim
  theta_idx <- seq_len(p)
  delta_g_idx <- if (J >= 1L) seq.int(p + 1L, 2L * p) else integer(0)
  delta_n_idx <- if (J >= 2L) seq.int(2L * p + 1L, 3L * p) else integer(0)
  zeta_idx <- if (ctx$ppx > 0L) core_hist_dim + 1L else NA_integer_

  out <- data.frame(
    date = ctx$hist_dates,
    observed_usgs = ctx$observed_usgs,
    exps_usgs = state_payload$exps_usgs,
    mu_state_usgs = rep(NA_real_, TT_hist),
    mu_without_transfer = rep(NA_real_, TT_hist),
    transfer_zeta = rep(NA_real_, TT_hist),
    trend_agg = rep(NA_real_, TT_hist),
    season_agg = rep(NA_real_, TT_hist),
    agg_discrep_glofas = rep(NA_real_, TT_hist),
    agg_discrep_nws = rep(NA_real_, TT_hist),
    stringsAsFactors = FALSE
  )

  for (tt in seq_len(TT_hist)) {
    mt <- as.numeric(sm[, tt])
    if (length(mt) < max(theta_idx)) next
    base_no_transfer <- sum(ff_base * mt[theta_idx])
    zeta_mean <- if (is.finite(zeta_idx) && zeta_idx <= length(mt)) mt[zeta_idx] else 0
    trend_mean <- if (length(ctx$trend_idx) > 0L) {
      sum(ff_base[ctx$trend_idx] * mt[ctx$trend_idx])
    } else {
      NA_real_
    }
    season_mean <- if (length(ctx$season_idx) > 0L) {
      sum(ff_base[ctx$season_idx] * mt[ctx$season_idx])
    } else {
      0
    }
    disc_g_mean <- if (length(delta_g_idx) == p && max(delta_g_idx) <= length(mt)) {
      sum(ff_base * mt[delta_g_idx])
    } else {
      NA_real_
    }
    disc_n_mean <- if (length(delta_n_idx) == p && max(delta_n_idx) <= length(mt)) {
      sum(ff_base * mt[delta_n_idx])
    } else {
      NA_real_
    }

    out$mu_without_transfer[[tt]] <- base_no_transfer
    out$transfer_zeta[[tt]] <- zeta_mean
    out$trend_agg[[tt]] <- trend_mean
    out$season_agg[[tt]] <- season_mean
    out$mu_state_usgs[[tt]] <- base_no_transfer + zeta_mean
    out$agg_discrep_glofas[[tt]] <- disc_g_mean
    out$agg_discrep_nws[[tt]] <- disc_n_mean
  }

  out
}

plot_exps_window <- function(df, window_n, report_dir) {
  long_df <- do.call(
    rbind,
    lapply(quantile_labels, function(q) {
      data.frame(
        date = df$date,
        quantile = q,
        value = df[[paste0("exps_", q)]],
        stringsAsFactors = FALSE
      )
    })
  )
  long_df$quantile <- factor(long_df$quantile, levels = quantile_labels)
  break_str <- if (window_n >= 1500L) "4 months" else if (window_n >= 900L) "2 months" else "1 month"
  label_fmt <- if (window_n >= 1500L) "%Y-%m" else "%b %Y"

  p <- ggplot2::ggplot(df, ggplot2::aes(x = date)) +
    ggplot2::geom_line(
      ggplot2::aes(y = observed_usgs, color = "USGS fit input"),
      linewidth = 1.15,
      lineend = "round"
    ) +
    ggplot2::geom_line(
      data = long_df,
      mapping = ggplot2::aes(y = value, color = quantile, group = quantile),
      linewidth = 0.95,
      alpha = 0.95,
      lineend = "round"
    ) +
    ggplot2::scale_color_manual(
      values = c("USGS fit input" = "#1B1B1B", palette_quantiles),
      breaks = c("USGS fit input", quantile_labels)
    ) +
    ggplot2::scale_x_date(date_breaks = break_str, date_labels = label_fmt) +
    ggplot2::labs(
      title = sprintf("USGS new.theta.out$exps[1, ] over last %d observations", window_n),
      subtitle = "All 7 quantile rows against the exact USGS fit input",
      x = "Date",
      y = "log1p(cms)",
      color = NULL
    ) +
    ggplot2::theme_minimal(base_size = 12) +
    ggplot2::theme(
      legend.position = "bottom",
      legend.box = "vertical",
      axis.text.x = ggplot2::element_text(angle = 45, hjust = 1),
      panel.grid.minor = ggplot2::element_blank()
    )

  png_path <- file.path(report_dir, sprintf("last%d_usgs_exps_all_quantiles_log1p.png", window_n))
  pdf_path <- file.path(report_dir, sprintf("last%d_usgs_exps_all_quantiles_log1p.pdf", window_n))
  ggplot2::ggsave(png_path, p, width = 14, height = 8, dpi = 180)
  ggplot2::ggsave(pdf_path, p, width = 14, height = 8)
}

plot_component_window <- function(df, q_label, window_n, report_dir) {
  level_df <- data.frame(
    date = rep(df$date, 4L),
    panel = "Level terms",
    series = factor(
      rep(c("USGS fit input", "USGS exps", "USGS state-reconstructed", "USGS without transfer"), each = nrow(df)),
      levels = c("USGS fit input", "USGS exps", "USGS state-reconstructed", "USGS without transfer")
    ),
    value = c(df$observed_usgs, df$exps_usgs, df$mu_state_usgs, df$mu_without_transfer),
    stringsAsFactors = FALSE
  )
  component_df <- data.frame(
    date = rep(df$date, 3L),
    panel = "Component terms",
    series = factor(
      rep(c("Transfer zeta", "Trend aggregate", "Season aggregate"), each = nrow(df)),
      levels = c("Transfer zeta", "Trend aggregate", "Season aggregate")
    ),
    value = c(df$transfer_zeta, df$trend_agg, df$season_agg),
    stringsAsFactors = FALSE
  )
  long_df <- rbind(level_df, component_df)
  break_str <- if (window_n >= 1500L) "4 months" else if (window_n >= 900L) "2 months" else "1 month"
  label_fmt <- if (window_n >= 1500L) "%Y-%m" else "%b %Y"

  p <- ggplot2::ggplot(long_df, ggplot2::aes(x = date, y = value, color = series)) +
    ggplot2::geom_line(linewidth = 0.95, alpha = 0.96, na.rm = TRUE, lineend = "round") +
    ggplot2::facet_wrap(~panel, ncol = 1L, scales = "free_y") +
    ggplot2::scale_color_manual(values = palette_components) +
    ggplot2::scale_x_date(date_breaks = break_str, date_labels = label_fmt) +
    ggplot2::labs(
      title = sprintf("%s historical USGS state decomposition over last %d observations", q_label, window_n),
      subtitle = "USGS exps from new.theta.out with historical state-derived components against the exact USGS fit input",
      x = "Date",
      y = "log1p(cms) / component scale",
      color = NULL
    ) +
    ggplot2::theme_minimal(base_size = 12) +
    ggplot2::theme(
      legend.position = "bottom",
      legend.box = "vertical",
      axis.text.x = ggplot2::element_text(angle = 45, hjust = 1),
      panel.grid.minor = ggplot2::element_blank()
    )

  png_path <- file.path(report_dir, sprintf("last%d_%s_usgs_exps_components_log1p.png", window_n, q_label))
  pdf_path <- file.path(report_dir, sprintf("last%d_%s_usgs_exps_components_log1p.pdf", window_n, q_label))
  ggplot2::ggsave(png_path, p, width = 14, height = 10, dpi = 180)
  ggplot2::ggsave(pdf_path, p, width = 14, height = 10)
}

main <- function() {
  require_pkg("ggplot2")
  require_pkg("yaml")

  args <- parse_args(commandArgs(trailingOnly = TRUE))
  repo_root <- normalizePath(args$repo_root %||% getwd(), mustWork = TRUE)
  run_root <- normalizePath(args$run_root %||% "", mustWork = TRUE)
  report_dir <- normalizePath(args$report_dir %||% "", mustWork = FALSE)
  windows_raw <- as.character(args$windows %||% "2000,1000,500")
  window_sizes <- suppressWarnings(as.integer(strsplit(windows_raw, ",", fixed = TRUE)[[1L]]))
  window_sizes <- unique(window_sizes[is.finite(window_sizes) & window_sizes > 0L])
  if (!nzchar(report_dir)) {
    stop("Provide --report-dir", call. = FALSE)
  }
  if (length(window_sizes) < 1L) {
    stop("No valid window sizes provided.", call. = FALSE)
  }
  dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)

  cfg <- yaml::read_yaml(file.path(run_root, "resolved_config.yaml"))
  ctx <- prepare_rebuild_context(run_root = run_root, repo_root = repo_root, cfg = cfg)

  exps_all_df <- data.frame(
    date = ctx$hist_dates,
    observed_usgs = ctx$observed_usgs,
    stringsAsFactors = FALSE
  )

  component_store <- list()
  manifest_rows <- list()

  for (k in seq_along(quantile_labels)) {
    q_label <- quantile_labels[[k]]
    q_suffix <- quantile_suffixes[[k]]
    rdata_path <- file.path(
      run_root,
      "fit", "exdqlm_multivar", "keep",
      sprintf("q=%s", sub("^q", "", q_label)),
      "outputs",
      sprintf("DISC_variables_%s_exAL_synth_DISC.RData", q_suffix)
    )
    message(sprintf("Loading retained state for %s", q_label))
    state_payload <- extract_quantile_state(rdata_path = rdata_path, quant_suffix = q_suffix, TT_hist = ctx$TT)
    exps_all_df[[paste0("exps_", q_label)]] <- state_payload$exps_usgs
    component_store[[q_label]] <- compute_history_components(state_payload, ctx)
    manifest_rows[[length(manifest_rows) + 1L]] <- data.frame(
      quantile = q_label,
      rdata_path = rdata_path,
      exps_length = length(state_payload$exps_usgs),
      sm_rows = nrow(state_payload$sm),
      sm_cols = ncol(state_payload$sm),
      stringsAsFactors = FALSE
    )
    rm(state_payload)
    invisible(gc(verbose = FALSE))
  }

  write_csv_det(exps_all_df, file.path(report_dir, "all_history_usgs_exps_quantiles_full.csv"))
  write_csv_det(do.call(rbind, manifest_rows), file.path(report_dir, "retained_state_manifest.csv"))

  summary_rows <- list()

  for (window_n in window_sizes) {
    idx <- seq.int(max(1L, ctx$TT - window_n + 1L), ctx$TT)
    window_df <- exps_all_df[idx, , drop = FALSE]
    plot_exps_window(window_df, window_n = length(idx), report_dir = report_dir)
    write_csv_det(
      window_df,
      file.path(report_dir, sprintf("last%d_usgs_exps_all_quantiles_log1p.csv", length(idx)))
    )

    for (q_label in quantile_labels) {
      comp_df <- component_store[[q_label]][idx, , drop = FALSE]
      plot_component_window(comp_df, q_label = q_label, window_n = length(idx), report_dir = report_dir)
      write_csv_det(
        comp_df,
        file.path(report_dir, sprintf("last%d_%s_usgs_exps_components_log1p.csv", length(idx), q_label))
      )
    }

    summary_rows[[length(summary_rows) + 1L]] <- data.frame(
      window_n = length(idx),
      start_date = as.character(min(window_df$date)),
      end_date = as.character(max(window_df$date)),
      stringsAsFactors = FALSE
    )
  }

  write_csv_det(do.call(rbind, summary_rows), file.path(report_dir, "window_summary.csv"))

  readme <- c(
    "# Retained exAL-M-T1 USGS exps + component review",
    "",
    sprintf("- run root: `%s`", run_root),
    "- source objects: retained `new.theta.out_<q>_exAL_synth_DISC` from all 7 quantile `.RData` files",
    "- total USGS fitted curve: `new.theta.out$exps[1, ]`",
    "- comparison target: exact historical `USGS` fit input from the retained run context",
    "- component plots: historical state-mean decomposition using the rebuilt shared model context (`trend`, `season`, `transfer zeta`, `mu_without_transfer`, and state-reconstructed USGS)",
    "",
    "## Windows",
    sprintf("- %s", paste(window_sizes, collapse = ", ")),
    "",
    "## Main outputs",
    "- one all-quantile `exps` plot for each requested window",
    "- one per-quantile component plot for each requested window",
    "- CSV exports for each plot window",
    "- retained state manifest and window summary"
  )
  writeLines(readme, con = file.path(report_dir, "README.md"))
}

main()
