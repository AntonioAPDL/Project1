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
    key <- gsub("-", "_", sub("^--", "", key), fixed = TRUE)
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

as_int_vec <- function(x, default = integer(0)) {
  if (is.null(x) || !nzchar(as.character(x))) return(default)
  y <- suppressWarnings(as.integer(strsplit(as.character(x), ",", fixed = TRUE)[[1L]]))
  y[is.finite(y)]
}

as_num_vec <- function(x, default = numeric(0)) {
  if (is.null(x) || !nzchar(as.character(x))) return(default)
  y <- suppressWarnings(as.numeric(strsplit(as.character(x), ",", fixed = TRUE)[[1L]]))
  y[is.finite(y)]
}

write_csv_det <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(df, path, row.names = FALSE)
}

require_pkg <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    stop(sprintf("Package '%s' is required.", pkg), call. = FALSE)
  }
}

quantile_pct <- function(q) {
  if (grepl("^q", q)) return(as.integer(sub("^q0?", "", q)))
  val <- as.numeric(q)
  if (is.na(val)) stop(sprintf("Invalid quantile value: %s", q), call. = FALSE)
  as.integer(round(if (val <= 1) 100 * val else val))
}

quantile_lane <- function(q) sprintf("q%02d", quantile_pct(q))

quantile_suffix <- function(q) as.character(quantile_pct(q))

lane_from_path <- function(path) {
  base <- basename(path)
  m <- regexpr("DISC_variables_[0-9]+", base)
  if (m > 0) {
    pct <- as.integer(sub("DISC_variables_", "", regmatches(base, m)))
    return(sprintf("q%02d", pct))
  }
  tools::file_path_sans_ext(base)
}

resolve_covariate_path_by_name <- function(cfg, name) {
  covs <- cfg$inputs$fit$covariates
  if (!is.list(covs) || length(covs) < 1L) {
    stop("Resolved config has no fit covariates block.", call. = FALSE)
  }
  idx <- vapply(covs, function(x) identical(as.character(x$name %||% ""), name), logical(1))
  if (!any(idx)) stop(sprintf("Could not resolve covariate path for %s", name), call. = FALSE)
  as.character(covs[[which(idx)[1L]]]$path)
}

prepare_rebuild_context <- function(run_root, repo_root) {
  require_pkg("yaml")
  cfg <- yaml::read_yaml(file.path(run_root, "resolved_config.yaml"))
  cutoff_date <- as.Date(cfg$dates$cutoff_date)
  forecast_start_date <- cutoff_date + 1L
  scale_contract <- cfg$scale_contract %||% list()
  legacy_fit_scale <- as.character(scale_contract$legacy_fit_input_scale %||% "log1p_cms")
  analysis_fit_scale <- as.character(scale_contract$analysis_scale_fit_internal %||% legacy_fit_scale)
  legacy_post_scale <- as.character(scale_contract$legacy_post_input_scale %||% legacy_fit_scale)
  analysis_post_scale <- as.character(scale_contract$analysis_scale_post_internal %||% analysis_fit_scale)

  enabled_harmonics <- cfg$models$exdqlm_multivar$structure$enabled_harmonic_indices
  if (is.null(enabled_harmonics) || length(enabled_harmonics) < 1L) enabled_harmonics <- c(1L, 2L, 3L)
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
    source = "run_root",
    run_root = run_root,
    cutoff_date = cutoff_date,
    hist_dates = as.Date(timestamps),
    forecast_dates = seq.Date(cutoff_date + 1L, by = "day", length.out = k),
    observed_usgs = as.numeric(Y[1L, ]),
    TT = as.integer(TT),
    k = as.integer(k),
    p = as.integer(p),
    J = as.integer(J),
    ppx = as.integer(ppx),
    ff_base = ff_base,
    trend_idx = trend_idx,
    season_idx = season_idx,
    scale = analysis_fit_scale,
    forecast_transfer_mode = as.character(cfg$models$exdqlm_multivar$forecast_transfer_mode %||% "keep")
  )
}

prepare_manual_context <- function(args, first_rdata) {
  p <- as.integer(args$p %||% NA_integer_)
  J <- as.integer(args$J %||% NA_integer_)
  ppx <- as.integer(args$ppx %||% NA_integer_)
  ff_base <- as_num_vec(args$ff_base)
  if (!is.finite(p) || !is.finite(J) || !is.finite(ppx) || length(ff_base) != p) {
    stop("Manual mode requires --p, --J, --ppx, and --ff-base with length p.", call. = FALSE)
  }
  env <- new.env(parent = emptyenv())
  load(first_rdata, envir = env)
  theta_name <- grep("^new\\.theta\\.out_", ls(env), value = TRUE)[[1L]]
  theta <- get(theta_name, envir = env)
  TT <- ncol(theta$sm)
  h <- max(0L, ncol(theta$exps) - TT)
  start_date <- as.Date(args$start_date %||% "2000-01-01")
  forecast_start <- start_date + TT
  list(
    source = "manual",
    run_root = NA_character_,
    cutoff_date = start_date + TT - 1L,
    hist_dates = seq.Date(start_date, by = "day", length.out = TT),
    forecast_dates = seq.Date(forecast_start, by = "day", length.out = h),
    observed_usgs = rep(NA_real_, TT),
    TT = TT,
    k = h,
    p = p,
    J = J,
    ppx = ppx,
    ff_base = ff_base,
    trend_idx = as_int_vec(args$trend_idx, integer(0)),
    season_idx = as_int_vec(args$season_idx, integer(0)),
    scale = as.character(args$scale %||% "fixture_scale"),
    forecast_transfer_mode = "keep"
  )
}

resolve_rdata_paths <- function(args, ctx) {
  if (!is.null(args$rdata) && nzchar(as.character(args$rdata))) {
    paths <- strsplit(as.character(args$rdata), ",", fixed = TRUE)[[1L]]
    paths <- normalizePath(trimws(paths), mustWork = TRUE)
    names(paths) <- vapply(paths, lane_from_path, character(1))
    return(paths)
  }

  run_root <- normalizePath(args$run_root %||% "", mustWork = TRUE)
  q_raw <- strsplit(as.character(args$quantiles %||% "0.05,0.35,0.5,0.95"), ",", fixed = TRUE)[[1L]]
  paths <- vapply(q_raw, function(q) {
    file.path(
      run_root,
      "fit", "exdqlm_multivar", "keep",
      sprintf("q=%02d", quantile_pct(q)),
      "outputs",
      sprintf("DISC_variables_%s_exAL_synth_DISC.RData", quantile_suffix(q))
    )
  }, character(1))
  names(paths) <- vapply(q_raw, quantile_lane, character(1))
  missing <- paths[!file.exists(paths)]
  if (length(missing)) {
    stop(sprintf("Missing RData paths: %s", paste(missing, collapse = "; ")), call. = FALSE)
  }
  normalized <- normalizePath(paths, mustWork = TRUE)
  names(normalized) <- names(paths)
  normalized
}

extract_theta <- function(path) {
  env <- new.env(parent = emptyenv())
  on.exit({
    rm(list = ls(env, all.names = TRUE), envir = env)
    gc(verbose = FALSE)
  }, add = TRUE)
  loaded <- load(path, envir = env)
  theta_name <- grep("^new\\.theta\\.out_", loaded, value = TRUE)
  if (length(theta_name) != 1L) {
    stop(sprintf("Expected exactly one new.theta.out object in %s", path), call. = FALSE)
  }
  theta <- get(theta_name, envir = env)
  list(
    theta_name = theta_name,
    exps = as.matrix(theta$exps),
    sm = as.matrix(theta$sm),
    sC = theta$sC,
    sm_ens = theta$sm_ens,
    sC_ens = theta$sC_ens
  )
}

component_indices <- function(ctx, active_sources = ctx$J) {
  p <- ctx$p
  core_dim <- p * (active_sources + 1L)
  list(
    theta = seq_len(p),
    deltas = lapply(seq_len(active_sources), function(src) seq.int(src * p + 1L, (src + 1L) * p)),
    zeta = if (ctx$ppx > 0L) core_dim + 1L else NA_integer_,
    core_dim = core_dim,
    state_dim = core_dim + ctx$ppx
  )
}

weighted_sum <- function(w, x, idx) {
  if (!length(idx) || max(idx) > length(x)) return(NA_real_)
  sum(w[seq_along(idx)] * x[idx])
}

compute_history <- function(theta, lane, ctx) {
  idx <- component_indices(ctx, active_sources = ctx$J)
  TT <- min(ctx$TT, ncol(theta$sm), ncol(theta$exps))
  rows <- vector("list", TT)
  for (tt in seq_len(TT)) {
    mt <- as.numeric(theta$sm[, tt])
    base <- weighted_sum(ctx$ff_base, mt, idx$theta)
    zeta <- if (is.finite(idx$zeta) && idx$zeta <= length(mt)) mt[[idx$zeta]] else 0
    trend <- weighted_sum(ctx$ff_base, mt, ctx$trend_idx)
    season <- weighted_sum(ctx$ff_base, mt, ctx$season_idx)
    disc_vals <- vapply(idx$deltas, function(didx) weighted_sum(ctx$ff_base, mt, didx), numeric(1))
    source_recon <- base + disc_vals + zeta
    rows[[tt]] <- data.frame(
      lane = lane,
      phase = "history",
      segment = 0L,
      time_index = tt,
      date = as.character(ctx$hist_dates[[tt]]),
      observed_usgs = ctx$observed_usgs[[tt]],
      target_exps = theta$exps[1L, tt],
      target_reconstructed = base + zeta,
      target_error = theta$exps[1L, tt] - (base + zeta),
      mu_without_transfer = base,
      transfer_zeta = zeta,
      trend_agg = trend,
      season_agg = season,
      source = c("target", sprintf("source_%d", seq_along(source_recon))),
      exps = c(theta$exps[1L, tt], theta$exps[seq_along(source_recon) + 1L, tt]),
      reconstructed = c(base + zeta, source_recon),
      discrepancy = c(0, disc_vals),
      reconstruction_error = c(theta$exps[1L, tt] - (base + zeta), theta$exps[seq_along(source_recon) + 1L, tt] - source_recon),
      stringsAsFactors = FALSE
    )
  }
  do.call(rbind, rows)
}

compute_forecast <- function(theta, lane, ctx) {
  if (!is.list(theta$sm_ens) || !length(theta$sm_ens)) return(data.frame())
  rows <- list()
  TT <- ctx$TT
  col_offset <- TT
  for (seg in seq_along(theta$sm_ens)) {
    sm_seg <- as.matrix(theta$sm_ens[[seg]])
    h <- ncol(sm_seg)
    active_sources <- ctx$J - seg + 1L
    idx <- component_indices(ctx, active_sources = active_sources)
    if (h < 1L || active_sources < 1L) next
    for (hh in seq_len(h)) {
      mt <- as.numeric(sm_seg[, hh])
      base <- weighted_sum(ctx$ff_base, mt, idx$theta)
      zeta <- if (is.finite(idx$zeta) && idx$zeta <= length(mt)) mt[[idx$zeta]] else 0
      trend <- weighted_sum(ctx$ff_base, mt, ctx$trend_idx)
      season <- weighted_sum(ctx$ff_base, mt, ctx$season_idx)
      disc_vals <- vapply(idx$deltas, function(didx) weighted_sum(ctx$ff_base, mt, didx), numeric(1))
      source_recon <- base + disc_vals + zeta
      global_col <- col_offset + hh
      exps_vals <- if (global_col <= ncol(theta$exps)) theta$exps[seq_along(source_recon) + 1L, global_col] else rep(NA_real_, length(source_recon))
      rows[[length(rows) + 1L]] <- data.frame(
        lane = lane,
        phase = "forecast",
        segment = seg,
        time_index = global_col,
        lead_index = global_col - TT,
        date = if ((global_col - TT) <= length(ctx$forecast_dates)) as.character(ctx$forecast_dates[[global_col - TT]]) else NA_character_,
        mu_without_transfer = base,
        transfer_zeta = zeta,
        trend_agg = trend,
        season_agg = season,
        source = sprintf("source_%d", seq_along(source_recon)),
        exps = exps_vals,
        reconstructed = source_recon,
        discrepancy = disc_vals,
        reconstruction_error = exps_vals - source_recon,
        stringsAsFactors = FALSE
      )
    }
    col_offset <- col_offset + h
  }
  if (length(rows)) do.call(rbind, rows) else data.frame()
}

state_map <- function(ctx) {
  rows <- list()
  hist <- component_indices(ctx, active_sources = ctx$J)
  rows[[1L]] <- data.frame(phase = "history", segment = 0L, role = "theta", source = "target", index = hist$theta)
  for (src in seq_along(hist$deltas)) {
    rows[[length(rows) + 1L]] <- data.frame(phase = "history", segment = 0L, role = "discrepancy", source = sprintf("source_%d", src), index = hist$deltas[[src]])
  }
  if (is.finite(hist$zeta)) {
    rows[[length(rows) + 1L]] <- data.frame(phase = "history", segment = 0L, role = "transfer_zeta", source = "all", index = hist$zeta)
  }
  for (seg in seq_len(ctx$J)) {
    active_sources <- ctx$J - seg + 1L
    idx <- component_indices(ctx, active_sources = active_sources)
    rows[[length(rows) + 1L]] <- data.frame(phase = "forecast", segment = seg, role = "theta", source = "target", index = idx$theta)
    for (src in seq_along(idx$deltas)) {
      rows[[length(rows) + 1L]] <- data.frame(phase = "forecast", segment = seg, role = "discrepancy", source = sprintf("source_%d", src), index = idx$deltas[[src]])
    }
    if (is.finite(idx$zeta)) {
      rows[[length(rows) + 1L]] <- data.frame(phase = "forecast", segment = seg, role = "transfer_zeta", source = "all", index = idx$zeta)
    }
  }
  do.call(rbind, rows)
}

summarize_reconstruction <- function(history_df, forecast_df) {
  all_df <- rbind(
    history_df[, intersect(names(history_df), c("lane", "phase", "segment", "source", "reconstruction_error", "mu_without_transfer", "transfer_zeta", "trend_agg", "season_agg", "discrepancy"))],
    forecast_df[, intersect(names(forecast_df), c("lane", "phase", "segment", "source", "reconstruction_error", "mu_without_transfer", "transfer_zeta", "trend_agg", "season_agg", "discrepancy"))]
  )
  if (!nrow(all_df)) return(data.frame())
  groups <- unique(all_df[, c("lane", "phase", "segment", "source"), drop = FALSE])
  rows <- vector("list", nrow(groups))
  for (i in seq_len(nrow(groups))) {
    g <- groups[i, , drop = FALSE]
    idx <- all_df$lane == g$lane & all_df$phase == g$phase & all_df$segment == g$segment & all_df$source == g$source
    x <- all_df[idx, , drop = FALSE]
    err <- as.numeric(x$reconstruction_error)
    rows[[i]] <- data.frame(
      lane = g$lane,
      phase = g$phase,
      segment = g$segment,
      source = g$source,
      n = length(err),
      finite_error_frac = mean(is.finite(err)),
      max_abs_reconstruction_error = if (any(is.finite(err))) max(abs(err), na.rm = TRUE) else NA_real_,
      median_abs_transfer_zeta = stats::median(abs(x$transfer_zeta), na.rm = TRUE),
      median_abs_mu_without_transfer = stats::median(abs(x$mu_without_transfer), na.rm = TRUE),
      median_abs_discrepancy = stats::median(abs(x$discrepancy), na.rm = TRUE),
      stringsAsFactors = FALSE
    )
  }
  do.call(rbind, rows)
}

plot_history_components <- function(history_df, out_dir, window_n) {
  lanes <- unique(history_df$lane)
  for (lane in lanes) {
    df <- history_df[history_df$lane == lane & history_df$source == "target", , drop = FALSE]
    if (!nrow(df)) next
    keep <- tail(seq_len(nrow(df)), min(window_n, nrow(df)))
    df <- df[keep, , drop = FALSE]
    png(file.path(out_dir, sprintf("%s_history_components.png", lane)), width = 1400, height = 850)
    on.exit(dev.off(), add = TRUE)
    x <- seq_len(nrow(df))
    yr <- range(c(df$target_exps, df$target_reconstructed, df$mu_without_transfer, df$transfer_zeta, df$trend_agg, df$season_agg), na.rm = TRUE)
    plot(x, df$target_exps, type = "l", lwd = 2, col = "black", ylim = yr, xlab = "window index", ylab = "state scale", main = sprintf("%s history decomposition", lane))
    lines(x, df$target_reconstructed, col = "#1f78b4", lwd = 1.5)
    lines(x, df$mu_without_transfer, col = "#33a02c", lwd = 1.2)
    lines(x, df$transfer_zeta, col = "#e31a1c", lwd = 1.2)
    lines(x, df$trend_agg, col = "#6a3d9a", lwd = 1.1)
    lines(x, df$season_agg, col = "#ff7f00", lwd = 1.1)
    legend("topleft", legend = c("exps target", "reconstructed", "without transfer", "zeta", "trend", "season"), col = c("black", "#1f78b4", "#33a02c", "#e31a1c", "#6a3d9a", "#ff7f00"), lty = 1, lwd = c(2, 1.5, rep(1.2, 4)), cex = 0.8)
  }
}

main <- function() {
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  out_dir <- normalizePath(args$out %||% file.path("reports", "exdqlm_keep_decomposition_audit"), mustWork = FALSE)
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  repo_root <- normalizePath(args$repo_root %||% getwd(), mustWork = TRUE)

  if (!is.null(args$run_root) && nzchar(as.character(args$run_root))) {
    ctx <- prepare_rebuild_context(normalizePath(args$run_root, mustWork = TRUE), repo_root)
  } else {
    rdata_first <- strsplit(as.character(args$rdata %||% ""), ",", fixed = TRUE)[[1L]][[1L]]
    ctx <- prepare_manual_context(args, normalizePath(rdata_first, mustWork = TRUE))
  }

  rdata_paths <- resolve_rdata_paths(args, ctx)
  manifest <- data.frame(lane = names(rdata_paths), path = unname(rdata_paths), stringsAsFactors = FALSE)

  history_rows <- list()
  forecast_rows <- list()
  for (lane in names(rdata_paths)) {
    theta <- extract_theta(rdata_paths[[lane]])
    history_rows[[lane]] <- compute_history(theta, lane, ctx)
    forecast_rows[[lane]] <- compute_forecast(theta, lane, ctx)
  }
  history_df <- do.call(rbind, history_rows)
  forecast_df <- do.call(rbind, forecast_rows)
  recon <- summarize_reconstruction(history_df, forecast_df)

  write_csv_det(manifest, file.path(out_dir, "manifest.csv"))
  write_csv_det(state_map(ctx), file.path(out_dir, "state_coordinate_map.csv"))
  write_csv_det(history_df, file.path(out_dir, "history_decomposition.csv"))
  write_csv_det(forecast_df, file.path(out_dir, "forecast_decomposition.csv"))
  write_csv_det(recon, file.path(out_dir, "reconstruction_summary.csv"))

  window_n <- as.integer(args$window %||% 500L)
  if (!is.finite(window_n) || window_n <= 0L) window_n <- 500L
  plot_history_components(history_df, out_dir, window_n)

  readme <- c(
    "# exDQLM keep decomposition audit",
    "",
    "Generated by `repro/audits/exdqlm_keep_decomposition_audit.R`.",
    "",
    sprintf("- context source: `%s`", ctx$source),
    sprintf("- run root: `%s`", ctx$run_root %||% ""),
    sprintf("- scale: `%s`", ctx$scale),
    sprintf("- dimensions: `p=%d`, `J=%d`, `ppx=%d`, `TT=%d`, `k=%d`", ctx$p, ctx$J, ctx$ppx, ctx$TT, ctx$k),
    "",
    "Outputs:",
    "",
    "- `state_coordinate_map.csv`: state roles used by the decomposition.",
    "- `history_decomposition.csv`: target/source reconstruction with trend, season, discrepancy, and transfer zeta.",
    "- `forecast_decomposition.csv`: retained-source forecast reconstruction by ragged segment.",
    "- `reconstruction_summary.csv`: max absolute reconstruction errors and component magnitude summaries.",
    "- `q*_history_components.png`: compact target decomposition windows.",
    "",
    "The primary pass criterion is that `max_abs_reconstruction_error` is near numerical tolerance for the rows whose corresponding `new.theta.out$exps` values are populated."
  )
  writeLines(readme, file.path(out_dir, "README.md"))

  bad <- recon[is.finite(recon$max_abs_reconstruction_error) & recon$max_abs_reconstruction_error > 1e-6, , drop = FALSE]
  if (nrow(bad)) {
    warning(sprintf("Reconstruction errors above tolerance in %d groups; see reconstruction_summary.csv", nrow(bad)), call. = FALSE)
  }

  cat(sprintf("Decomposition audit wrote: %s\n", normalizePath(out_dir, mustWork = FALSE)))
}

main()
