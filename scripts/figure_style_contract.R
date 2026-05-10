`%||%` <- function(x, y) if (is.null(x) || length(x) == 0L) y else x

figure_flow_axis_label <- function(plot_scale) {
  if (is.null(plot_scale) || !nzchar(as.character(plot_scale))) {
    plot_scale <- "log_log1p_cms"
  }
  switch(
    as.character(plot_scale),
    raw_cms = bquote(River~flow~"["*m^3~s^-1*"]"),
    log1p_cms = bquote(River~flow~"["*log(1 + x)*";"~~x~"in"~~m^3~s^-1*"]"),
    log_log1p_cms = bquote(River~flow~"["*log(log(1 + x))*";"~~x~"in"~~m^3~s^-1*"]"),
    as.character(plot_scale)
  )
}

figure_date_label_format <- function(dates) {
  if (length(dates) == 0L) {
    return("%Y-%m-%d")
  }
  date_vals <- as.Date(dates)
  span_days <- suppressWarnings(as.numeric(max(date_vals, na.rm = TRUE) - min(date_vals, na.rm = TRUE)))
  if (!is.finite(span_days)) {
    return("%Y-%m-%d")
  }
  if (span_days > 3650) {
    return("%Y")
  }
  if (span_days > 730) {
    return("%Y-%m")
  }
  "%Y-%m-%d"
}

figure_product_palette <- function() {
  c(
    usgs = "#238b45",
    glofas = "#E67E22",
    nws = "#756bb1",
    usgs_future = "#B22222"
  )
}

figure_transform_flow <- function(x_cms, plot_scale) {
  vals <- suppressWarnings(as.numeric(x_cms))
  out <- rep(NA_real_, length(vals))
  if (identical(plot_scale, "raw_cms")) {
    return(vals)
  }
  if (identical(plot_scale, "log1p_cms")) {
    ok <- !is.na(vals) & vals > -1
    out[ok] <- log(vals[ok] + 1)
    return(out)
  }
  if (identical(plot_scale, "log_log1p_cms")) {
    ok <- !is.na(vals) & vals >= 0
    out[ok] <- log(log(vals[ok] + 1))
    out[!is.finite(out)] <- NA_real_
    return(out)
  }
  stop(sprintf("Unknown plot scale: %s", plot_scale), call. = FALSE)
}

figure_flood_stage_df <- function(plot_scale = "log1p_cms") {
  flood_cfs <- c(15000, 6750)
  flood_cms <- flood_cfs * 0.028316846592
  data.frame(
    label = c("Major Flooding", "Minor Flooding"),
    y = figure_transform_flow(flood_cms, plot_scale),
    stringsAsFactors = FALSE
  )
}

figure_flood_label_df <- function(plot_scale = "log1p_cms", values = numeric()) {
  out <- figure_flood_stage_df(plot_scale = plot_scale)
  vals <- suppressWarnings(as.numeric(values))
  vals <- vals[is.finite(vals)]
  span <- suppressWarnings(diff(range(c(vals, out$y), na.rm = TRUE)))
  if (!is.finite(span) || span <= 0) {
    span <- 1
  }
  offset <- max(0.03 * span, 0.04)
  if (nrow(out) > 1L) {
    out$label_y <- out$y + c(offset, -offset)
  } else {
    out$label_y <- out$y
  }
  out
}

figure_flood_stage_style <- function() {
  list(
    line_color = "#6B7280",
    line_width = 0.65,
    line_type = "dashed",
    label_color = "#4A5568",
    label_size = 3.3,
    label_face = "italic"
  )
}

figure_covariate_facet_labels <- function() {
  c(
    Precipitation = "Precipitation~'['*mm*']'",
    Soil_Moisture = "Soil~moisture~'['*m^3~m^{-3}*']'",
    Climate_PC1 = "GDPC[1]"
  )
}

figure_choose_cutoff_window_source_id <- function(windows, cutoff_date) {
  if (!is.list(windows) || length(windows) == 0L) {
    return(NA_character_)
  }
  cutoff_use <- suppressWarnings(as.Date(cutoff_date))
  if (is.na(cutoff_use)) {
    return(NA_character_)
  }
  for (window in windows) {
    start <- suppressWarnings(as.Date(window$start %||% NA_character_))
    end <- suppressWarnings(as.Date(window$end %||% NA_character_))
    if (!is.na(start) && !is.na(end) && cutoff_use >= start && cutoff_use <= end) {
      return(tolower(as.character(window$source_id %||% NA_character_)))
    }
  }
  NA_character_
}

figure_nws_version_label <- function(source_id) {
  sid <- tolower(as.character(source_id %||% ""))
  switch(
    sid,
    nws_retro_v12 = "NWS retrospective v1.2",
    nws_retro_v20 = "NWS retrospective v2.0",
    nws_retro_v21 = "NWS retrospective v2.1",
    nws_retro_v30 = "NWS retrospective v3.0",
    "NWS retrospective"
  )
}

figure_glofas_version_label <- function(source_id) {
  sid <- tolower(as.character(source_id %||% ""))
  switch(
    sid,
    glofas_hist_v21_htessel_cons = "GloFAS historical v2.1",
    glofas_hist_v31_lisflood_cons = "GloFAS historical v3.1",
    glofas_hist_v40_lisflood_cons = "GloFAS historical v4.0",
    glofas_legacy_reanalysis_v30 = "GloFAS legacy reanalysis v3.0",
    "GloFAS retrospective"
  )
}

figure_selected_run_nws_label <- function(selected_run_root, default_label = "NWS retrospective") {
  root <- as.character(selected_run_root %||% "")
  if (!nzchar(root)) {
    return(default_label)
  }
  cache <- get0(".figure_selected_run_nws_cache", envir = .GlobalEnv, inherits = FALSE)
  if (!is.environment(cache)) {
    cache <- new.env(parent = emptyenv())
    assign(".figure_selected_run_nws_cache", cache, envir = .GlobalEnv)
  }
  if (exists(root, envir = cache, inherits = FALSE)) {
    cached <- get(root, envir = cache, inherits = FALSE)
    return(as.character(cached %||% default_label))
  }

  retros_path <- file.path(root, "inputs", "shared", "retros", "retros.csv")
  if (!file.exists(retros_path)) {
    assign(root, default_label, envir = cache)
    return(default_label)
  }
  header <- tryCatch(utils::read.csv(retros_path, nrows = 0, check.names = FALSE), error = function(e) NULL)
  if (is.null(header)) {
    assign(root, default_label, envir = cache)
    return(default_label)
  }
  nws_cols <- grep("^NWS", names(header), value = TRUE)
  if (length(nws_cols) == 0L) {
    assign(root, default_label, envir = cache)
    return(default_label)
  }
  col <- nws_cols[[1L]]
  if (grepl("^NWS[0-9.]+$", col)) {
    version <- sub("^NWS", "", col)
    label <- sprintf("NWS retrospective v%s", version)
    assign(root, label, envir = cache)
    return(label)
  }
  assign(root, default_label, envir = cache)
  default_label
}

figure_default_retro_label <- function(source_id, meta = NULL, cutoff_date = NULL, selected_run_root = NULL) {
  sid <- tolower(as.character(source_id %||% ""))
  if (!nzchar(sid)) {
    return("")
  }
  selection_policy <- if (!is.null(meta)) meta$config$inputs$retros$selection_policy %||% list() else list()

  if (identical(sid, "nws_synth_retro_ens_mean")) {
    chosen_sid <- figure_choose_cutoff_window_source_id(selection_policy$nws_by_cutoff_windows %||% list(), cutoff_date)
    chosen_label <- figure_nws_version_label(chosen_sid)
    if (nzchar(chosen_label)) {
      return(chosen_label)
    }
    return(figure_selected_run_nws_label(selected_run_root, default_label = "NWS retrospective"))
  }

  if (identical(sid, "nws_selected_window_retro")) {
    return(figure_selected_run_nws_label(selected_run_root))
  }

  if (identical(sid, "glofas_synth_retro_ens_mean")) {
    chosen_sid <- figure_choose_cutoff_window_source_id(selection_policy$glofas_by_cutoff_windows %||% list(), cutoff_date)
    chosen_label <- figure_glofas_version_label(chosen_sid)
    if (nzchar(chosen_label)) {
      return(chosen_label)
    }
    return("GloFAS retrospective")
  }

  if (!is.null(meta)) {
    extras <- meta$config$inputs$retros$extra_sources %||% list()
    if (length(extras) > 0L) {
      for (row in extras) {
        row_sid <- tolower(as.character(row$source_id %||% ""))
        row_label <- as.character(row$source_label %||% "")
        if (identical(row_sid, sid) && nzchar(row_label)) {
          return(row_label)
        }
      }
    }
  }

  switch(
    sid,
    nws_retro_v12 = "NWS retrospective v1.2",
    nws_retro_v20 = "NWS retrospective v2.0",
    nws_retro_v21 = "NWS retrospective v2.1",
    nws_retro_v30 = "NWS retrospective v3.0",
    glofas_hist_v21_htessel_cons = "GloFAS historical v2.1",
    glofas_hist_v31_lisflood_cons = "GloFAS historical v3.1",
    glofas_hist_v40_lisflood_cons = "GloFAS historical v4.0",
    glofas_legacy_reanalysis_v30 = "GloFAS legacy reanalysis v3.0",
    glofas_synth_retro_ens_mean = "GloFAS retrospective",
    baseline_glofas = "GloFAS retrospective (baseline)",
    baseline_nws = "NWS retrospective (baseline)",
    sid
  )
}

figure_retro_color_map <- function(labels) {
  labels <- unique(as.character(labels))
  if (length(labels) == 0L) {
    return(setNames(character(0), character(0)))
  }
  palette <- figure_product_palette()
  out <- setNames(rep("#4d4d4d", length(labels)), labels)
  out[grepl("^GloFAS", labels)] <- palette[["glofas"]]
  out[grepl("^NWS", labels)] <- palette[["nws"]]
  out[grepl("^USGS", labels)] <- palette[["usgs"]]
  out
}

figure_retro_shape_map <- function(labels) {
  labels <- unique(as.character(labels))
  if (length(labels) == 0L) {
    return(setNames(integer(0), character(0)))
  }
  out <- setNames(rep(8L, length(labels)), labels)
  out[grepl("^USGS", labels)] <- 16L
  out[grepl("^GloFAS", labels)] <- 15L
  out[grepl("^NWS", labels)] <- 17L
  out
}

theme_manuscript_standard <- function(
  base_size = 14,
  title_size = 16,
  subtitle_size = NULL,
  legend_position = "none",
  axis_text_size = 11,
  axis_text_y_size = axis_text_size,
  x_angle = 0,
  x_hjust = if (x_angle == 0) 0.5 else 1,
  x_vjust = if (x_angle == 0) 0.5 else 1,
  strip_text_size = NULL,
  major_grid_x = NULL,
  major_grid_y = NULL,
  plot_margin = NULL
) {
  th <- theme_minimal(base_size = base_size) +
    theme(
      plot.title = element_text(size = title_size, face = "bold", hjust = 0.5, margin = margin(b = 8)),
      axis.title = element_text(face = "bold"),
      axis.text = element_text(size = axis_text_size),
      axis.text.y = element_text(size = axis_text_y_size),
      axis.text.x = element_text(size = axis_text_size, angle = x_angle, hjust = x_hjust, vjust = x_vjust),
      panel.grid.minor = element_blank(),
      legend.position = legend_position
    )

  if (!is.null(subtitle_size)) {
    th <- th + theme(
      plot.subtitle = element_text(size = subtitle_size, face = "italic", hjust = 0.5)
    )
  }

  if (!is.null(strip_text_size)) {
    th <- th + theme(
      strip.text = element_text(face = "bold", size = strip_text_size, color = "black"),
      strip.background = element_blank()
    )
  }

  if (!is.null(major_grid_x)) {
    th <- th + theme(
      panel.grid.major.x = if (isTRUE(major_grid_x)) {
        element_line(linewidth = 0.3, color = "#e5e5e5")
      } else {
        element_blank()
      }
    )
  }

  if (!is.null(major_grid_y)) {
    th <- th + theme(
      panel.grid.major.y = if (isTRUE(major_grid_y)) {
        element_line(linewidth = 0.4, color = "#e5e5e5")
      } else {
        element_blank()
      }
    )
  }

  if (!is.null(plot_margin)) {
    th <- th + theme(plot.margin = plot_margin)
  }

  th
}
