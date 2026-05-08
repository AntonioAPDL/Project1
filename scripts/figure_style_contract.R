`%||%` <- function(x, y) if (is.null(x) || length(x) == 0L) y else x

figure_flow_axis_label <- function(plot_scale) {
  if (is.null(plot_scale) || !nzchar(as.character(plot_scale))) {
    plot_scale <- "log_log1p_cms"
  }
  switch(
    as.character(plot_scale),
    raw_cms = expression(Water~Flow~(m^3/s)),
    log1p_cms = expression(Water~Flow~(log(1 + m^3/s))),
    log_log1p_cms = expression(Water~Flow~(log(log(1 + m^3/s)))),
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

figure_selected_run_nws_label <- function(selected_run_root, default_label = "NWS retrospective (selected-run window)") {
  if (is.null(selected_run_root) || !nzchar(as.character(selected_run_root))) {
    return(default_label)
  }
  retros_path <- file.path(as.character(selected_run_root), "inputs", "shared", "retros", "retros.csv")
  if (!file.exists(retros_path)) {
    return(default_label)
  }
  header <- tryCatch(utils::read.csv(retros_path, nrows = 0, check.names = FALSE), error = function(e) NULL)
  if (is.null(header)) {
    return(default_label)
  }
  nws_cols <- grep("^NWS", names(header), value = TRUE)
  if (length(nws_cols) == 0L) {
    return(default_label)
  }
  col <- nws_cols[[1L]]
  if (grepl("^NWS[0-9.]+$", col)) {
    version <- sub("^NWS", "", col)
    return(sprintf("NWS retrospective v%s (selected-run window)", version))
  }
  default_label
}

figure_default_retro_label <- function(source_id, meta = NULL, cutoff_date = NULL, selected_run_root = NULL) {
  sid <- tolower(as.character(source_id %||% ""))
  if (!nzchar(sid)) {
    return("")
  }

  if (identical(sid, "nws_synth_retro_ens_mean")) {
    chosen_sid <- figure_choose_cutoff_window_source_id(meta$config$inputs$retros$selection_policy$nws_by_cutoff_windows %||% list(), cutoff_date)
    chosen_label <- figure_nws_version_label(chosen_sid)
    if (nzchar(chosen_label)) {
      return(sprintf("%s (closest available)", chosen_label))
    }
    return("NWS retrospective (closest available)")
  }

  if (identical(sid, "nws_selected_window_retro")) {
    return(figure_selected_run_nws_label(selected_run_root))
  }

  if (identical(sid, "glofas_synth_retro_ens_mean")) {
    return("GloFAS retrospective (closest available)")
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
    glofas_hist_v21_htessel_cons = "GloFAS historical v2.1 (HTESSEL-LISFLOOD, consolidated)",
    glofas_hist_v31_lisflood_cons = "GloFAS historical v3.1 (LISFLOOD, consolidated)",
    glofas_hist_v40_lisflood_cons = "GloFAS historical v4.0 (LISFLOOD, consolidated)",
    glofas_legacy_reanalysis_v30 = "GloFAS legacy reanalysis v3.0",
    glofas_synth_retro_ens_mean = "GloFAS retrospective (closest available)",
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
  out <- setNames(rep(NA_character_, length(labels)), labels)

  fixed <- c(
    "GloFAS retrospective (baseline)" = "#E67E22",
    "GloFAS retrospective (closest available)" = "#AF601A",
    "GloFAS historical v2.1 (HTESSEL-LISFLOOD, consolidated)" = "#F5B041",
    "GloFAS historical v3.1 (LISFLOOD, consolidated)" = "#EB984E",
    "GloFAS historical v4.0 (LISFLOOD, consolidated)" = "#D35400",
    "GloFAS legacy reanalysis v3.0" = "#BA4A00",
    "NWS retrospective (baseline)" = palette[["nws"]],
    "NWS retrospective v1.2" = "#B7AADF",
    "NWS retrospective v1.2 (closest available)" = "#B7AADF",
    "NWS retrospective v2.0" = "#9A8CC9",
    "NWS retrospective v2.0 (baseline)" = "#A491D3",
    "NWS retrospective v2.0 (closest available)" = "#9A8CC9",
    "NWS retrospective v2.1" = "#7A68B5",
    "NWS retrospective v2.1 (baseline)" = "#8E79C6",
    "NWS retrospective v2.1 (closest available)" = "#7A68B5",
    "NWS retrospective v3.0" = "#5B4B9A",
    "NWS retrospective v3.0 (baseline)" = palette[["nws"]],
    "NWS retrospective v3.0 (selected-run window)" = "#5B4B9A",
    "NWS retrospective v3.0 (closest available)" = "#5B4B9A",
    "NWS retrospective v3.0 (legacy local csv)" = "#6C5BA8",
    "NWS retrospective v2.1 (legacy local csv)" = "#8A78C1",
    "NWS retrospective v3.0 (re-extracted point)" = "#5B4B9A",
    "NWS retrospective v2.1 (re-extracted point)" = "#7A68B5",
    "NWS retrospective v2.0 (re-extracted point)" = "#9A8CC9",
    "NWS retrospective (selected-run window)" = "#5B4B9A",
    "NWS retrospective (closest available)" = palette[["nws"]]
  )
  for (nm in names(fixed)) {
    if (nm %in% labels) {
      out[[nm]] <- fixed[[nm]]
    }
  }

  idx_na <- which(is.na(out))
  if (length(idx_na) > 0L) {
    for (i in idx_na) {
      lbl <- labels[[i]]
      if (grepl("^GloFAS", lbl)) {
        out[[lbl]] <- palette[["glofas"]]
      } else if (grepl("^NWS", lbl)) {
        out[[lbl]] <- palette[["nws"]]
      } else if (grepl("^USGS", lbl)) {
        out[[lbl]] <- palette[["usgs"]]
      } else {
        out[[lbl]] <- "#4d4d4d"
      }
    }
  }

  out
}

figure_retro_shape_map <- function(labels) {
  labels <- unique(as.character(labels))
  if (length(labels) == 0L) {
    return(setNames(integer(0), character(0)))
  }
  out <- setNames(rep(NA_integer_, length(labels)), labels)
  fixed <- c(
    "USGS observed" = 16,
    "GloFAS retrospective (baseline)" = 15,
    "GloFAS retrospective (closest available)" = 10,
    "GloFAS historical v2.1 (HTESSEL-LISFLOOD, consolidated)" = 17,
    "GloFAS historical v3.1 (LISFLOOD, consolidated)" = 18,
    "GloFAS historical v4.0 (LISFLOOD, consolidated)" = 0,
    "GloFAS legacy reanalysis v3.0" = 8,
    "NWS retrospective (baseline)" = 1,
    "NWS retrospective v1.2" = 3,
    "NWS retrospective v1.2 (closest available)" = 3,
    "NWS retrospective v2.0" = 4,
    "NWS retrospective v2.0 (baseline)" = 5,
    "NWS retrospective v2.0 (closest available)" = 4,
    "NWS retrospective v2.1" = 6,
    "NWS retrospective v2.1 (baseline)" = 2,
    "NWS retrospective v2.1 (closest available)" = 6,
    "NWS retrospective v3.0" = 7,
    "NWS retrospective v3.0 (baseline)" = 1,
    "NWS retrospective v3.0 (selected-run window)" = 7,
    "NWS retrospective v3.0 (closest available)" = 7,
    "NWS retrospective v3.0 (legacy local csv)" = 1,
    "NWS retrospective v2.1 (legacy local csv)" = 2,
    "NWS retrospective v3.0 (re-extracted point)" = 7,
    "NWS retrospective v2.1 (re-extracted point)" = 6,
    "NWS retrospective v2.0 (re-extracted point)" = 4,
    "NWS retrospective (selected-run window)" = 7,
    "NWS retrospective (closest available)" = 9
  )
  for (nm in names(fixed)) {
    if (nm %in% labels) {
      out[[nm]] <- fixed[[nm]]
    }
  }
  idx_na <- which(is.na(out))
  if (length(idx_na) > 0L) {
    fallback <- c(0:25)
    used <- unname(out[!is.na(out)])
    fallback <- fallback[!fallback %in% used]
    out[idx_na] <- fallback[seq_len(min(length(idx_na), length(fallback)))]
  }
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
