#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ggplot2)
})

get_script_path <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- args[grepl("^--file=", args)]
  if (length(file_arg) == 0L) {
    stop("Unable to determine script path from commandArgs().")
  }
  normalizePath(sub("^--file=", "", file_arg[1]), winslash = "/", mustWork = TRUE)
}

parse_args <- function(args, defaults) {
  out <- defaults
  for (arg in args) {
    if (!startsWith(arg, "--")) next
    parts <- strsplit(sub("^--", "", arg), "=", fixed = TRUE)[[1]]
    if (length(parts) != 2L) {
      stop(sprintf("Expected --key=value format, got: %s", arg), call. = FALSE)
    }
    out[[parts[1]]] <- parts[2]
  }
  out
}

discover_run_root <- function(explicit_root, candidate_roots) {
  if (!is.null(explicit_root) && nzchar(explicit_root)) {
    if (!dir.exists(explicit_root)) {
      stop(sprintf("Run root does not exist: %s", explicit_root), call. = FALSE)
    }
    return(normalizePath(explicit_root, winslash = "/", mustWork = TRUE))
  }

  existing <- candidate_roots[dir.exists(candidate_roots)]
  if (length(existing) == 0L) {
    stop(
      paste(
        "Could not find a canonical run root. Checked:",
        paste(candidate_roots, collapse = "\n  - "),
        sep = "\n  - "
      ),
      call. = FALSE
    )
  }

  normalizePath(existing[1], winslash = "/", mustWork = TRUE)
}

discover_config_path <- function(run_root, explicit_config = NULL) {
  if (!is.null(explicit_config) && nzchar(explicit_config)) {
    if (!file.exists(explicit_config)) {
      stop(sprintf("Config file does not exist: %s", explicit_config), call. = FALSE)
    }
    return(normalizePath(explicit_config, winslash = "/", mustWork = TRUE))
  }

  config_path <- file.path(run_root, "resolved_config.yaml")
  if (!file.exists(config_path)) {
    stop(sprintf("Could not find resolved_config.yaml under run root: %s", run_root), call. = FALSE)
  }

  normalizePath(config_path, winslash = "/", mustWork = TRUE)
}

read_config <- function(config_path) {
  if (!requireNamespace("yaml", quietly = TRUE)) {
    stop("Package 'yaml' is required to read the unified run config.", call. = FALSE)
  }
  yaml::read_yaml(config_path)
}

pick_covariate_path <- function(run_root, filename, fallback = NULL) {
  candidate <- file.path(run_root, "inputs", "shared", "covariates", filename)
  if (file.exists(candidate)) {
    return(normalizePath(candidate, winslash = "/", mustWork = TRUE))
  }
  if (!is.null(fallback) && nzchar(fallback) && file.exists(fallback)) {
    return(normalizePath(fallback, winslash = "/", mustWork = TRUE))
  }
  stop(sprintf("Could not locate covariate file: %s", filename), call. = FALSE)
}

find_date_col <- function(df, label) {
  nm <- names(df)
  candidates <- nm[grepl("date|time", tolower(nm))]
  if (length(nm) > 0L) {
    candidates <- unique(c(candidates, nm[[1L]]))
  }
  for (cand in candidates) {
    vals <- suppressWarnings(as.Date(df[[cand]]))
    good <- sum(!is.na(vals))
    if (good >= max(1L, floor(0.8 * length(vals)))) {
      return(cand)
    }
  }
  stop(sprintf("Could not identify a date column for %s.", label), call. = FALSE)
}

find_value_col <- function(df, date_col, preferred = character(0), label) {
  for (cand in preferred) {
    if (!(cand %in% names(df))) next
    vals <- suppressWarnings(as.numeric(df[[cand]]))
    if (sum(is.finite(vals)) >= max(1L, floor(0.8 * length(vals)))) {
      return(cand)
    }
  }

  numeric_cols <- setdiff(
    names(df)[vapply(df, function(x) {
      vals <- suppressWarnings(as.numeric(x))
      sum(is.finite(vals)) >= max(1L, floor(0.8 * length(vals)))
    }, logical(1))],
    date_col
  )

  if (length(numeric_cols) == 0L) {
    stop(sprintf("Could not identify a numeric value column for %s.", label), call. = FALSE)
  }
  numeric_cols[[1L]]
}

read_series <- function(path, label, preferred_value_cols = character(0)) {
  df <- read.csv(path, check.names = FALSE, stringsAsFactors = FALSE)
  date_col <- find_date_col(df, label)
  value_col <- find_value_col(df, date_col, preferred_value_cols, label)

  out <- data.frame(
    date = as.Date(df[[date_col]]),
    value = suppressWarnings(as.numeric(df[[value_col]])),
    stringsAsFactors = FALSE
  )
  out <- out[!is.na(out$date) & is.finite(out$value), , drop = FALSE]
  out <- stats::aggregate(value ~ date, data = out, FUN = mean)
  out <- out[order(out$date), , drop = FALSE]

  if (nrow(out) == 0L) {
    stop(sprintf("No valid dated rows found for %s: %s", label, path), call. = FALSE)
  }

  out
}

build_history_df <- function(ppt_df, soil_df, pca_df, retros_df, cutoff_date) {
  merged <- Reduce(function(x, y) merge(x, y, by = "date"), list(
    stats::setNames(ppt_df, c("date", "ppt")),
    stats::setNames(soil_df, c("date", "soil")),
    stats::setNames(pca_df, c("date", "pca")),
    stats::setNames(retros_df["date"], "date")
  ))

  merged <- merged[merged$date <= cutoff_date, , drop = FALSE]
  merged <- merged[order(merged$date), , drop = FALSE]

  if (nrow(merged) == 0L) {
    stop("No overlapping historical dates were found across covariates and retros.", call. = FALSE)
  }

  sds <- c(
    ppt = stats::sd(merged$ppt),
    soil = stats::sd(merged$soil),
    pca = stats::sd(merged$pca)
  )
  if (any(!is.finite(sds)) || any(sds <= 0)) {
    stop("Historical covariate standard deviations must be finite and positive.", call. = FALSE)
  }

  data.frame(
    date = rep(merged$date, 3L),
    series_id = rep(c("ppt", "soil", "pca"), each = nrow(merged)),
    series_label = rep(
      c(
        "PRISM precipitation (scaled)",
        "ERA5 soil moisture (scaled)",
        "Climate-index PC1 (scaled)"
      ),
      each = nrow(merged)
    ),
    source_label = rep(
      c("PRISM", "ERA5", "PCA"),
      each = nrow(merged)
    ),
    color = rep(c("#5B1A72", "#1F8A89", "#D4B000"), each = nrow(merged)),
    raw_value = c(merged$ppt, merged$soil, merged$pca),
    scaled_value = c(
      merged$ppt / sds[["ppt"]],
      merged$soil / sds[["soil"]],
      merged$pca / sds[["pca"]]
    ),
    stringsAsFactors = FALSE
  )
}

save_plot_png <- function(plot_obj, path, width, height, dpi) {
  if (requireNamespace("ragg", quietly = TRUE)) {
    ragg::agg_png(
      filename = path,
      width = width,
      height = height,
      units = "in",
      res = dpi,
      scaling = 1,
      background = "white"
    )
    on.exit(grDevices::dev.off(), add = TRUE)
    print(plot_obj)
  } else {
    ggsave(
      filename = path,
      plot = plot_obj,
      width = width,
      height = height,
      units = "in",
      dpi = dpi,
      bg = "white"
    )
  }
}

main <- function() {
  script_path <- get_script_path()
  repo_root <- normalizePath(file.path(dirname(script_path), ".."), winslash = "/", mustWork = TRUE)

  args <- parse_args(
    commandArgs(trailingOnly = TRUE),
    defaults = list(
      run_root = NULL,
      config = NULL,
      output_dir = file.path(repo_root, "exports", "transfer_covariates_history_20260310")
    )
  )

  candidate_roots <- c(
    file.path(repo_root, "repro", "runs", "prod_canonical_parallel_mc3_diag_20260217_194948"),
    file.path(
      repo_root,
      "repro", "quarantine", "cleanup_runs", "20260218T201412Z",
      "prod_canonical_parallel_mc3_diag_20260217_194948"
    )
  )

  run_root <- discover_run_root(args$run_root, candidate_roots)
  config_path <- discover_config_path(run_root, args$config)
  cfg <- read_config(config_path)

  cutoff_date <- as.Date(cfg$dates$cutoff_date)
  if (is.na(cutoff_date)) {
    stop("Could not parse dates.cutoff_date from the unified config.", call. = FALSE)
  }

  fit_covariates <- cfg$inputs$fit$covariates
  fit_cov_map <- list()
  if (!is.null(fit_covariates) && length(fit_covariates) > 0L) {
    for (entry in fit_covariates) {
      if (!is.list(entry) || is.null(entry$name) || is.null(entry$path)) next
      fit_cov_map[[toupper(as.character(entry$name))]] <- as.character(entry$path)
    }
  }

  ppt_path <- pick_covariate_path(run_root, "cov_03_PPT.csv", fit_cov_map[["PPT"]])
  soil_path <- pick_covariate_path(run_root, "cov_04_SOIL.csv", fit_cov_map[["SOIL"]])
  pca_path <- pick_covariate_path(run_root, "cov_05_PCA.csv", fit_cov_map[["PCA"]])

  retros_candidates <- c(
    file.path(run_root, "inputs", "shared", "retros", "retros.csv"),
    if (!is.null(cfg$inputs$fit$retros_path)) as.character(cfg$inputs$fit$retros_path) else character(0)
  )
  retros_candidates <- retros_candidates[nzchar(retros_candidates)]
  retros_existing <- retros_candidates[file.exists(retros_candidates)]
  if (length(retros_existing) == 0L) {
    stop("Could not locate a retros CSV for historical alignment.", call. = FALSE)
  }
  retros_path <- normalizePath(retros_existing[[1L]], winslash = "/", mustWork = TRUE)

  output_dir <- normalizePath(args$output_dir, winslash = "/", mustWork = FALSE)
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  ppt_df <- read_series(ppt_path, "PPT", preferred_value_cols = c("PRCP_mm", "ppt"))
  soil_df <- read_series(soil_path, "SOIL", preferred_value_cols = c("Daily_Avg_Soil_Moisture", "soil"))
  pca_df <- read_series(pca_path, "PCA", preferred_value_cols = c("Static_PCA", "Component_1"))
  retros_df <- read_series(retros_path, "retros", preferred_value_cols = c("USGS", "GloFAS", "NWS3.0"))

  plot_df <- build_history_df(ppt_df, soil_df, pca_df, retros_df, cutoff_date)
  plot_df$series_label <- factor(
    plot_df$series_label,
    levels = c(
      "PRISM precipitation (scaled)",
      "ERA5 soil moisture (scaled)",
      "Climate-index PC1 (scaled)"
    )
  )

  date_min <- min(plot_df$date)
  date_max <- max(plot_df$date)
  display_max <- cutoff_date + 120

  plot_obj <- ggplot(plot_df, aes(x = date, y = scaled_value)) +
    geom_line(aes(color = color), linewidth = 0.42, lineend = "round", show.legend = FALSE) +
    geom_vline(
      xintercept = cutoff_date,
      color = "#C53030",
      linewidth = 0.45,
      linetype = "22"
    ) +
    facet_wrap(~series_label, ncol = 1, scales = "free_y") +
    scale_color_identity() +
    scale_x_date(
      limits = c(date_min, display_max),
      date_breaks = "5 years",
      date_minor_breaks = "1 year",
      date_labels = "%Y",
      expand = expansion(mult = c(0.002, 0.002))
    ) +
    labs(
      title = "Historical Transfer Covariates",
      subtitle = paste0(
        "Unified canonical run inputs through ",
        format(cutoff_date),
        ". Historical covariates aligned to the retrospective fit window."
      ),
      x = "Date",
      y = "Scaled input",
      caption = paste0(
        "San Lorenzo River (11160500). Scaling matches fit inputs: divide each historical series by its pre-cutoff SD, without centering.\n",
        "Sources: PRISM precipitation, ERA5 soil moisture, and the run-scoped PCA covariate. Red dashed line marks the forecast cutoff."
      )
    ) +
    theme_minimal(base_size = 13) +
    theme(
      plot.title = element_text(face = "bold", size = 18, color = "#1F2933"),
      plot.subtitle = element_text(size = 11.5, color = "#4A5568"),
      plot.caption = element_text(size = 9, color = "#5F6C7B", hjust = 0),
      strip.text = element_text(face = "bold", size = 13, color = "#1F2933"),
      strip.background = element_rect(fill = "#F3F0E8", color = NA),
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_line(color = "#D9DEE7", linewidth = 0.35),
      panel.grid.major.y = element_line(color = "#EEF2F7", linewidth = 0.30),
      panel.spacing = grid::unit(0.9, "lines"),
      axis.title = element_text(face = "bold", color = "#243B53"),
      axis.text = element_text(color = "#334E68"),
      plot.margin = margin(t = 14, r = 22, b = 14, l = 12)
    )

  png_path <- file.path(output_dir, "transfer_covariates_history_3x1.png")
  pdf_path <- file.path(output_dir, "transfer_covariates_history_3x1.pdf")
  csv_path <- file.path(output_dir, "transfer_covariates_history_3x1.csv")
  meta_path <- file.path(output_dir, "transfer_covariates_history_metadata.txt")

  export_width <- 14
  export_height <- 15
  export_dpi <- 600

  save_plot_png(plot_obj, png_path, width = export_width, height = export_height, dpi = export_dpi)
  ggsave(
    pdf_path,
    plot = plot_obj,
    device = grDevices::cairo_pdf,
    width = export_width,
    height = export_height,
    units = "in",
    bg = "white"
  )
  write.csv(plot_df, csv_path, row.names = FALSE)

  metadata <- c(
    sprintf("generated_at=%s", format(Sys.time(), tz = "UTC", usetz = TRUE)),
    sprintf("run_root=%s", run_root),
    sprintf("config_path=%s", config_path),
    sprintf("cutoff_date=%s", format(cutoff_date)),
    sprintf("date_min=%s", format(date_min)),
    sprintf("date_max=%s", format(date_max)),
    sprintf("rows_plotted=%d", nrow(plot_df)),
    sprintf("ppt_path=%s", ppt_path),
    sprintf("soil_path=%s", soil_path),
    sprintf("pca_path=%s", pca_path),
    sprintf("retros_path=%s", retros_path),
    "scaling=historical_sd_only_no_centering",
    sprintf("png=%s", png_path),
    sprintf("pdf=%s", pdf_path),
    sprintf("csv=%s", csv_path),
    sprintf("export_width_in=%d", export_width),
    sprintf("export_height_in=%d", export_height),
    sprintf("export_dpi=%d", export_dpi)
  )
  writeLines(metadata, meta_path)

  message(sprintf("Wrote figure: %s", png_path))
  message(sprintf("Wrote figure: %s", pdf_path))
  message(sprintf("Wrote data:   %s", csv_path))
  message(sprintf("Wrote meta:   %s", meta_path))
}

main()
