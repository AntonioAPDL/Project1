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

quantile_labels <- c("q05", "q20", "q35", "q50", "q65", "q80", "q95")
quantile_suffixes <- c("5", "20", "35", "50", "65", "80", "95")
palette <- c(
  q05 = "#9B1D20",
  q20 = "#C45D38",
  q35 = "#E38D2C",
  q50 = "#6A3D9A",
  q65 = "#2E86AB",
  q80 = "#1F9E89",
  q95 = "#006D2C"
)

extract_usgs_exps_row <- function(rdata_path, quant_suffix) {
  env <- new.env(parent = baseenv())
  on.exit({
    rm(list = ls(env, all.names = TRUE), envir = env)
    gc(verbose = FALSE)
  }, add = TRUE)
  load(rdata_path, envir = env)
  obj_name <- sprintf("new.theta.out_%s_exAL_synth_DISC", quant_suffix)
  if (!exists(obj_name, envir = env, inherits = FALSE)) {
    stop(sprintf("Missing object %s in %s", obj_name, rdata_path), call. = FALSE)
  }
  theta_obj <- get(obj_name, envir = env, inherits = FALSE)
  if (!is.list(theta_obj) || is.null(theta_obj$exps)) {
    stop(sprintf("%s lacks exps payload in %s", obj_name, rdata_path), call. = FALSE)
  }
  exps <- theta_obj$exps
  if (is.null(dim(exps)) || nrow(exps) < 1L) {
    stop(sprintf("%s$exps is not a valid matrix/array", obj_name), call. = FALSE)
  }
  as.numeric(exps[1L, ])
}

write_csv_det <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(df, path, row.names = FALSE)
}

main <- function() {
  require_pkg("ggplot2")
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  run_root <- normalizePath(args$run_root %||% "", mustWork = TRUE)
  report_dir <- normalizePath(args$report_dir %||% "", mustWork = FALSE)
  last_n <- suppressWarnings(as.integer(args$last_n %||% 200L))
  if (!nzchar(report_dir)) {
    stop("Provide --report-dir", call. = FALSE)
  }
  if (!is.finite(last_n) || last_n <= 0L) {
    stop("--last-n must be a positive integer", call. = FALSE)
  }
  dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)

  retros_path <- file.path(run_root, "fit", "inputs", "retros_fit_adapter.csv")
  if (!file.exists(retros_path)) {
    stop(sprintf("Missing retros fit adapter: %s", retros_path), call. = FALSE)
  }
  retros_df <- utils::read.csv(retros_path, stringsAsFactors = FALSE, check.names = FALSE)
  if (!all(c("Date", "USGS", "GloFAS", "NWS3.0") %in% names(retros_df))) {
    stop("retros_fit_adapter.csv missing expected columns", call. = FALSE)
  }
  retros_df$Date <- as.Date(retros_df$Date)
  TT <- nrow(retros_df)
  idx <- seq.int(max(1L, TT - last_n + 1L), TT)
  window_tag <- sprintf("last%d", length(idx))

  out_df <- data.frame(
    date = retros_df$Date[idx],
    observed_usgs = as.numeric(retros_df$USGS[idx]),
    glofas_retro = as.numeric(retros_df$GloFAS[idx]),
    nws_retro = as.numeric(retros_df[["NWS3.0"]][idx]),
    stringsAsFactors = FALSE
  )

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
    message(sprintf("Extracting %s from %s", q_label, basename(rdata_path)))
    exps_row <- extract_usgs_exps_row(rdata_path, q_suffix)
    if (length(exps_row) < TT) {
      stop(sprintf("%s exps row shorter than retros length (%d < %d)", q_label, length(exps_row), TT), call. = FALSE)
    }
    out_df[[paste0("exps_", q_label)]] <- as.numeric(exps_row[idx])
  }

  csv_name <- sprintf("%s_newtheta_exps_usgs_row.csv", window_tag)
  write_csv_det(out_df, file.path(report_dir, csv_name))

  long_rows <- lapply(quantile_labels, function(q) {
    data.frame(
      date = out_df$date,
      quantile = q,
      value = out_df[[paste0("exps_", q)]],
      stringsAsFactors = FALSE
    )
  })
  long_df <- do.call(rbind, long_rows)
  long_df$quantile <- factor(long_df$quantile, levels = quantile_labels)

  p <- ggplot2::ggplot(out_df, ggplot2::aes(x = date)) +
    ggplot2::geom_line(
      ggplot2::aes(y = observed_usgs, color = "Observed USGS input"),
      linewidth = 1.10,
      lineend = "round"
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = glofas_retro, color = "GloFAS retros input"),
      linewidth = 0.90,
      alpha = 0.90,
      linetype = "longdash",
      lineend = "round"
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = nws_retro, color = "NWS retros input"),
      linewidth = 0.90,
      alpha = 0.90,
      linetype = "dotdash",
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
      values = c(
        "Observed USGS input" = "#238B45",
        "GloFAS retros input" = "#C95F02",
        "NWS retros input" = "#5E3C99",
        palette
      ),
      breaks = c("Observed USGS input", "GloFAS retros input", "NWS retros input", quantile_labels)
    ) +
    ggplot2::scale_x_date(
      date_breaks = if (length(idx) > 400L) "2 months" else if (length(idx) > 200L) "1 month" else "2 weeks",
      date_labels = if (length(idx) > 400L) "%Y-%m" else "%b %d"
    ) +
    ggplot2::labs(
      title = sprintf("Representative exAL-M-T1 %s historical fitted exps curves", window_tag),
      subtitle = "new.theta.out$exps[1, ] for each quantile row; USGS row only, before sampling",
      x = "Date",
      y = "log1p(cms)"
    ) +
    ggplot2::theme_minimal(base_size = 12) +
    ggplot2::theme(
      legend.position = "bottom",
      legend.box = "vertical",
      legend.title = ggplot2::element_blank(),
      axis.text.x = ggplot2::element_text(angle = 45, hjust = 1),
      panel.grid.minor = ggplot2::element_blank()
    )

  png_path <- file.path(report_dir, sprintf("%s_newtheta_exps_usgs_row_all_quantiles_log1p.png", window_tag))
  pdf_path <- file.path(report_dir, sprintf("%s_newtheta_exps_usgs_row_all_quantiles_log1p.pdf", window_tag))
  ggplot2::ggsave(png_path, p, width = 14, height = 8, dpi = 180)
  ggplot2::ggsave(pdf_path, p, width = 14, height = 8)

  summary_df <- data.frame(
    metric = c(
      "retros_rows",
      "window_n",
      sprintf("%s_start_date", window_tag),
      sprintf("%s_end_date", window_tag),
      "row_mapping_statement"
    ),
    value = c(
      as.character(TT),
      as.character(length(idx)),
      as.character(min(out_df$date)),
      as.character(max(out_df$date)),
      "row1_of_Y_and_new.theta.out$exps_is_USGS_based_on_10_data_inputs_order_USGS_GloFAS_NWS3.0"
    ),
    stringsAsFactors = FALSE
  )
  write_csv_det(summary_df, file.path(report_dir, "newtheta_exps_review_summary.csv"))

  readme <- c(
    "# exAL-M-T1 new.theta.out exps review",
    "",
    sprintf("- run root: `%s`", run_root),
    "- extracted object: `new.theta.out_<q>_exAL_synth_DISC$exps`",
    "- plotted row: `row 1`",
    "- row mapping basis: `R/environmetrics/10_data_inputs.R` builds `Y <- t(cbind(USGS, GloFAS, NWS3.0))`",
    "- interpretation: these are the fitted expected-value observation dynamics for the USGS row during the observational window, not posterior samples",
    "",
    "## Outputs",
    "",
    sprintf("- plot: `%s`", png_path),
    sprintf("- csv: `%s`", file.path(report_dir, csv_name)),
    sprintf("- summary: `%s`", file.path(report_dir, "newtheta_exps_review_summary.csv"))
  )
  writeLines(readme, con = file.path(report_dir, "README.md"))
}

main()
