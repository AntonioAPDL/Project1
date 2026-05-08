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
