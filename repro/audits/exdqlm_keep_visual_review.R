#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

usage <- paste(
  "Usage:",
  "Rscript repro/audits/exdqlm_keep_visual_review.R",
  "--run-root /path/to/run",
  "--decomp-dir reports/.../decomposition",
  "--out reports/.../visual_review"
)

arg_value <- function(flag, default = NULL) {
  idx <- which(args == flag)
  if (!length(idx)) return(default)
  if (idx[[1L]] == length(args)) stop(sprintf("Missing value for %s\n%s", flag, usage), call. = FALSE)
  args[[idx[[1L]] + 1L]]
}

run_root <- arg_value("--run-root")
decomp_dir <- arg_value("--decomp-dir")
out_dir <- arg_value("--out")

if (is.null(run_root) || is.null(decomp_dir) || is.null(out_dir)) {
  stop(usage, call. = FALSE)
}
if (!dir.exists(run_root)) stop(sprintf("Run root does not exist: %s", run_root), call. = FALSE)
if (!dir.exists(decomp_dir)) stop(sprintf("Decomposition directory does not exist: %s", decomp_dir), call. = FALSE)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

as_num <- function(x) suppressWarnings(as.numeric(x))

lane_from_path <- function(path) {
  q <- sub(".*q=([0-9]+).*", "\\1", path)
  bad <- !grepl("^[0-9]+$", q)
  q[bad] <- sub(".*DISC_variables_([0-9]+)_.*", "\\1", basename(path[bad]))
  sprintf("q%02d", as.integer(q))
}

lane_order <- function(x) {
  x <- as.character(x)
  x[order(suppressWarnings(as.numeric(sub("^q", "", x))), x)]
}

open_png <- function(path, width = 1600, height = 1000) {
  grDevices::png(path, width = width, height = height, res = 130)
}

object_by_prefix <- function(env, prefix) {
  nm <- grep(sprintf("^%s", prefix), ls(env), value = TRUE)
  if (!length(nm)) stop(sprintf("No object with prefix `%s` in loaded RData", prefix), call. = FALSE)
  get(nm[[1L]], env)
}

role_label <- function(coord_map, idx) {
  row <- coord_map[coord_map$phase == "history" & coord_map$index == idx, , drop = FALSE]
  if (!nrow(row)) return(sprintf("state_%02d_unmapped", idx))
  paste(unique(sprintf("%s_%s", row$role, row$source)), collapse = "+")
}

rdata_paths <- list.files(
  file.path(run_root, "fit", "exdqlm_multivar", "keep"),
  pattern = "^DISC_variables_.*_exAL_synth_DISC\\.RData$",
  recursive = TRUE,
  full.names = TRUE
)
if (!length(rdata_paths)) {
  stop(sprintf("No DISC_variables RData files found below %s", run_root), call. = FALSE)
}
rdata_paths <- rdata_paths[order(lane_from_path(rdata_paths))]

coord_map_path <- file.path(decomp_dir, "state_coordinate_map.csv")
hist_path <- file.path(decomp_dir, "history_decomposition.csv")
forecast_path <- file.path(decomp_dir, "forecast_decomposition.csv")
if (!file.exists(coord_map_path)) stop(sprintf("Missing coordinate map: %s", coord_map_path), call. = FALSE)
if (!file.exists(hist_path)) stop(sprintf("Missing history decomposition: %s", hist_path), call. = FALSE)
coord_map <- utils::read.csv(coord_map_path, stringsAsFactors = FALSE, check.names = FALSE)
hist_decomp <- utils::read.csv(hist_path, stringsAsFactors = FALSE, check.names = FALSE)
forecast_decomp <- if (file.exists(forecast_path)) {
  utils::read.csv(forecast_path, stringsAsFactors = FALSE, check.names = FALSE)
} else {
  data.frame()
}

elbo_rows <- list()
state_norm_rows <- list()
state_coord_rows <- list()
exps_rows <- list()
manifest_rows <- list()

for (path in rdata_paths) {
  lane <- lane_from_path(path)
  env <- new.env(parent = emptyenv())
  load(path, envir = env)
  seq_elbo <- as_num(object_by_prefix(env, "seq.elbo"))
  seq_elbo <- seq_elbo[is.finite(seq_elbo)]
  elbo_rows[[lane]] <- data.frame(
    lane = lane,
    iter = seq_along(seq_elbo) - 1L,
    elbo = seq_elbo
  )

  theta <- object_by_prefix(env, "new.theta.out")
  sm <- theta$sm
  exps <- theta$exps
  if (!is.matrix(sm)) stop(sprintf("new.theta.out$sm is not a matrix for %s", lane), call. = FALSE)
  if (!is.matrix(exps)) stop(sprintf("new.theta.out$exps is not a matrix for %s", lane), call. = FALSE)

  state_norm_rows[[lane]] <- data.frame(
    lane = lane,
    time_index = seq_len(ncol(sm)),
    state_norm_sq = colSums(sm^2)
  )

  selected <- unique(c(1L, 2L, 3L, 4L, 7L, 10L, nrow(sm)))
  selected <- selected[selected >= 1L & selected <= nrow(sm)]
  state_coord_rows[[lane]] <- do.call(rbind, lapply(selected, function(idx) {
    data.frame(
      lane = lane,
      time_index = seq_len(ncol(sm)),
      coordinate = idx,
      role = role_label(coord_map, idx),
      value = as_num(sm[idx, ])
    )
  }))

  exps_rows[[lane]] <- data.frame(
    lane = lane,
    row = rep(seq_len(nrow(exps)), each = ncol(exps)),
    time_index = rep(seq_len(ncol(exps)), times = nrow(exps)),
    exps = as.vector(t(exps))
  )

  manifest_rows[[lane]] <- data.frame(
    lane = lane,
    rdata_path = normalizePath(path, mustWork = FALSE),
    n_elbo = length(seq_elbo),
    n_state = nrow(sm),
    n_history_time = ncol(sm),
    n_exps_row = nrow(exps),
    n_exps_time = ncol(exps)
  )
}

elbo <- do.call(rbind, elbo_rows)
state_norm <- do.call(rbind, state_norm_rows)
state_coords <- do.call(rbind, state_coord_rows)
theta_exps <- do.call(rbind, exps_rows)
manifest <- do.call(rbind, manifest_rows)

utils::write.csv(manifest, file.path(out_dir, "manifest.csv"), row.names = FALSE)
utils::write.csv(elbo, file.path(out_dir, "elbo_trace.csv"), row.names = FALSE)
utils::write.csv(state_norm, file.path(out_dir, "thetaout_state_norm.csv"), row.names = FALSE)
utils::write.csv(state_coords, file.path(out_dir, "thetaout_selected_states.csv"), row.names = FALSE)
utils::write.csv(theta_exps, file.path(out_dir, "thetaout_exps_long.csv"), row.names = FALSE)

elbo_summary <- do.call(rbind, lapply(split(elbo, elbo$lane), function(row) {
  tail_delta <- if (nrow(row) > 1L) tail(row$elbo, 1L) - row$elbo[[max(1L, nrow(row) - 100L)]] else NA_real_
  data.frame(
    lane = row$lane[[1L]],
    n_iter_saved = nrow(row),
    first_elbo = row$elbo[[1L]],
    final_elbo = tail(row$elbo, 1L),
    max_abs_step_last_100 = if (nrow(row) > 1L) max(abs(diff(tail(row$elbo, min(101L, nrow(row))))), na.rm = TRUE) else NA_real_,
    delta_last_100 = tail_delta
  )
}))
utils::write.csv(elbo_summary, file.path(out_dir, "elbo_summary.csv"), row.names = FALSE)

state_summary <- do.call(rbind, lapply(split(state_norm, state_norm$lane), function(row) {
  data.frame(
    lane = row$lane[[1L]],
    max_state_norm_sq = max(row$state_norm_sq, na.rm = TRUE),
    final_state_norm_sq = tail(row$state_norm_sq, 1L),
    median_state_norm_sq = stats::median(row$state_norm_sq, na.rm = TRUE)
  )
}))
utils::write.csv(state_summary, file.path(out_dir, "thetaout_state_summary.csv"), row.names = FALSE)

target_hist <- hist_decomp[hist_decomp$source == "target", , drop = FALSE]
target_hist$date <- as.Date(target_hist$date)
target_hist$observed_usgs <- as_num(target_hist$observed_usgs)
target_hist$target_exps <- as_num(target_hist$target_exps)
utils::write.csv(target_hist, file.path(out_dir, "usgs_history_target_exps.csv"), row.names = FALSE)

target_summary <- do.call(rbind, lapply(split(target_hist, target_hist$lane), function(row) {
  err <- row$target_exps - row$observed_usgs
  data.frame(
    lane = row$lane[[1L]],
    n = nrow(row),
    median_abs_error_log1p = stats::median(abs(err), na.rm = TRUE),
    q95_abs_error_log1p = as.numeric(stats::quantile(abs(err), 0.95, na.rm = TRUE, names = FALSE)),
    max_abs_error_log1p = max(abs(err), na.rm = TRUE)
  )
}))
utils::write.csv(target_summary, file.path(out_dir, "usgs_history_target_exps_summary.csv"), row.names = FALSE)

open_png(file.path(out_dir, "elbo_convergence_panel.png"))
graphics::par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))
for (lane in lane_order(unique(elbo$lane))) {
  row <- elbo[elbo$lane == lane, , drop = FALSE]
  graphics::plot(row$iter, row$elbo, type = "l", lwd = 1.1, col = "#1f77b4",
    xlab = "iteration", ylab = "ELBO", main = sprintf("%s ELBO", lane))
  if (nrow(row) > 200L) {
    usr <- graphics::par("usr")
    graphics::rect(max(row$iter) - 200, usr[[3L]], max(row$iter), usr[[4L]], col = grDevices::adjustcolor("#f58518", 0.12), border = NA)
    graphics::lines(row$iter, row$elbo, lwd = 1.1, col = "#1f77b4")
  }
}
grDevices::dev.off()

open_png(file.path(out_dir, "elbo_tail_step_panel.png"))
graphics::par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))
for (lane in lane_order(unique(elbo$lane))) {
  row <- elbo[elbo$lane == lane, , drop = FALSE]
  row <- tail(row, min(250L, nrow(row)))
  step <- c(NA_real_, abs(diff(row$elbo)))
  graphics::plot(row$iter, step, type = "l", lwd = 1.1, col = "#d62728",
    xlab = "iteration", ylab = "|ELBO step|", main = sprintf("%s tail ELBO step", lane))
}
grDevices::dev.off()

open_png(file.path(out_dir, "thetaout_state_norm_panel.png"))
graphics::par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))
for (lane in lane_order(unique(state_norm$lane))) {
  row <- state_norm[state_norm$lane == lane, , drop = FALSE]
  graphics::plot(row$time_index, row$state_norm_sq, type = "l", lwd = 1.1, col = "#4c78a8",
    xlab = "history time index", ylab = "sum sm^2", main = sprintf("%s theta.out state norm", lane))
}
grDevices::dev.off()

open_png(file.path(out_dir, "thetaout_selected_states_panel.png"), width = 1800, height = 1200)
graphics::par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))
cols <- c("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#17becf")
for (lane in lane_order(unique(state_coords$lane))) {
  row <- state_coords[state_coords$lane == lane, , drop = FALSE]
  roles <- unique(row$role)
  yr <- range(row$value, finite = TRUE)
  graphics::plot(NA, NA, xlim = range(row$time_index), ylim = yr,
    xlab = "history time index", ylab = "sm coordinate", main = sprintf("%s selected theta.out states", lane))
  for (i in seq_along(roles)) {
    rr <- row[row$role == roles[[i]], , drop = FALSE]
    graphics::lines(rr$time_index, rr$value, col = cols[[((i - 1L) %% length(cols)) + 1L]], lwd = 0.9)
  }
  graphics::legend("topleft", legend = roles, col = cols[seq_along(roles)], lty = 1, cex = 0.55, bty = "n")
}
grDevices::dev.off()

open_png(file.path(out_dir, "usgs_history_target_exps_last730.png"), width = 1800, height = 1100)
last_date <- max(target_hist$date, na.rm = TRUE)
plot_hist <- target_hist[target_hist$date >= last_date - 729, , drop = FALSE]
obs <- plot_hist[!duplicated(plot_hist$date), c("date", "observed_usgs")]
graphics::plot(obs$date, obs$observed_usgs, type = "l", lwd = 1.2, col = "#111111",
  xlab = "date", ylab = "log1p cms", main = "USGS observed and theta.out target exps, last 730 history days")
for (lane in lane_order(unique(plot_hist$lane))) {
  rr <- plot_hist[plot_hist$lane == lane, , drop = FALSE]
  graphics::lines(rr$date, rr$target_exps, lwd = 1, col = cols[[match(lane, lane_order(unique(plot_hist$lane)))]])
}
graphics::legend("topleft", legend = c("observed_usgs", lane_order(unique(plot_hist$lane))),
  col = c("#111111", cols[seq_along(lane_order(unique(plot_hist$lane)))]), lty = 1, lwd = c(1.2, rep(1, length(unique(plot_hist$lane)))), cex = 0.75, bty = "n")
grDevices::dev.off()

wide <- reshape(
  target_hist[, c("date", "observed_usgs", "lane", "target_exps")],
  idvar = c("date", "observed_usgs"),
  timevar = "lane",
  direction = "wide"
)
wide <- wide[order(wide$date), , drop = FALSE]
wide_last <- wide[wide$date >= last_date - 729, , drop = FALSE]
q05_col <- grep("target_exps\\.q05$", names(wide_last), value = TRUE)
q50_col <- grep("target_exps\\.q50$", names(wide_last), value = TRUE)
q95_col <- grep("target_exps\\.q95$", names(wide_last), value = TRUE)
if (length(q05_col) && length(q50_col) && length(q95_col)) {
  open_png(file.path(out_dir, "usgs_history_q05_q50_q95_band_last730.png"), width = 1800, height = 1100)
  yr <- range(c(wide_last$observed_usgs, wide_last[[q05_col]], wide_last[[q50_col]], wide_last[[q95_col]]), finite = TRUE)
  graphics::plot(wide_last$date, wide_last$observed_usgs, type = "n", ylim = yr,
    xlab = "date", ylab = "log1p cms", main = "USGS observed vs theta.out q05/q50/q95 target exps")
  graphics::polygon(
    c(wide_last$date, rev(wide_last$date)),
    c(wide_last[[q05_col]], rev(wide_last[[q95_col]])),
    col = grDevices::adjustcolor("#4c78a8", 0.18),
    border = NA
  )
  graphics::lines(wide_last$date, wide_last$observed_usgs, col = "#111111", lwd = 1.2)
  graphics::lines(wide_last$date, wide_last[[q50_col]], col = "#d62728", lwd = 1.1)
  graphics::lines(wide_last$date, wide_last[[q05_col]], col = "#4c78a8", lwd = 0.8, lty = 2)
  graphics::lines(wide_last$date, wide_last[[q95_col]], col = "#4c78a8", lwd = 0.8, lty = 2)
  graphics::legend("topleft", legend = c("observed_usgs", "q50 target exps", "q05-q95 target exps band"),
    col = c("#111111", "#d62728", "#4c78a8"), lty = c(1, 1, 2), lwd = c(1.2, 1.1, 0.8), cex = 0.8, bty = "n")
  grDevices::dev.off()
}

if (nrow(forecast_decomp)) {
  forecast_decomp$date <- as.Date(forecast_decomp$date)
  forecast_decomp$exps <- as_num(forecast_decomp$exps)
  utils::write.csv(forecast_decomp, file.path(out_dir, "forecast_source_exps.csv"), row.names = FALSE)
  open_png(file.path(out_dir, "forecast_source_exps_by_lane.png"), width = 1700, height = 1100)
  graphics::par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))
  for (lane in lane_order(unique(forecast_decomp$lane))) {
    row <- forecast_decomp[forecast_decomp$lane == lane, , drop = FALSE]
    yr <- range(row$exps, finite = TRUE)
    graphics::plot(NA, NA, xlim = range(row$lead_index, finite = TRUE), ylim = yr,
      xlab = "lead index", ylab = "forecast source exps", main = sprintf("%s retained forecast exps", lane))
    for (src in unique(row$source)) {
      rr <- row[row$source == src, , drop = FALSE]
      graphics::lines(rr$lead_index, rr$exps, type = "b", pch = 19, cex = 0.45,
        col = if (src == "source_1") "#1f77b4" else "#ff7f0e", lwd = 1)
    }
    graphics::legend("topleft", legend = unique(row$source),
      col = ifelse(unique(row$source) == "source_1", "#1f77b4", "#ff7f0e"), lty = 1, pch = 19, cex = 0.75, bty = "n")
  }
  grDevices::dev.off()
}

readme <- c(
  "# exDQLM keep visual review",
  "",
  "Generated by `repro/audits/exdqlm_keep_visual_review.R`.",
  "",
  sprintf("- run root: `%s`", normalizePath(run_root, mustWork = FALSE)),
  sprintf("- decomposition directory: `%s`", normalizePath(decomp_dir, mustWork = FALSE)),
  "",
  "## Main Plots",
  "",
  "- `elbo_convergence_panel.png`: full saved ELBO traces by q-lane.",
  "- `elbo_tail_step_panel.png`: absolute ELBO step size over the final saved iterations.",
  "- `thetaout_state_norm_panel.png`: `sum(new.theta.out$sm^2)` over history time by q-lane.",
  "- `thetaout_selected_states_panel.png`: selected `new.theta.out$sm` coordinates labelled by the decomposition state map.",
  "- `usgs_history_target_exps_last730.png`: observed USGS and `new.theta.out$exps` target rows for the last 730 history days.",
  "- `usgs_history_q05_q50_q95_band_last730.png`: q05/q50/q95 target-exps band against observed USGS.",
  "- `forecast_source_exps_by_lane.png`: retained-source forecast `exps` by lead, when forecast decomposition is available.",
  "",
  "## CSV Outputs",
  "",
  "- `elbo_summary.csv`",
  "- `thetaout_state_summary.csv`",
  "- `usgs_history_target_exps_summary.csv`",
  "- long-form plot inputs for ELBO, state norms, selected states, and `theta.out$exps`.",
  "",
  "All values are on the active internal analysis scale of the decomposition report."
)
writeLines(readme, file.path(out_dir, "README.md"))

cat(sprintf("Visual review wrote: %s\n", normalizePath(out_dir, mustWork = FALSE)))
