#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

usage <- paste(
  "Usage:",
  "Rscript repro/audits/exdqlm_keep_curated_evidence_bundle.R",
  "--runtime-dir reports/.../runtime_stability",
  "--out reports/.../curated_evidence",
  "[--guard-csv reports/.../pseudodata_guard_events/pseudodata_guard_events.csv]",
  "[--live-status reports/.../live_monitor/live_status.csv]"
)

arg_value <- function(flag, default = NULL) {
  idx <- which(args == flag)
  if (!length(idx)) return(default)
  if (idx[[1L]] == length(args)) stop(sprintf("Missing value for %s\n%s", flag, usage), call. = FALSE)
  args[[idx[[1L]] + 1L]]
}

runtime_dir <- arg_value("--runtime-dir")
out_dir <- arg_value("--out")
guard_csv <- arg_value("--guard-csv")
live_status_csv <- arg_value("--live-status")

if (is.null(runtime_dir) || is.null(out_dir)) {
  stop(usage, call. = FALSE)
}
if (!dir.exists(runtime_dir)) {
  stop(sprintf("Runtime audit directory does not exist: %s", runtime_dir), call. = FALSE)
}
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

read_required_csv <- function(name) {
  path <- file.path(runtime_dir, name)
  if (!file.exists(path)) stop(sprintf("Required runtime audit CSV missing: %s", path), call. = FALSE)
  utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
}

as_num <- function(x) suppressWarnings(as.numeric(x))

lane_order <- function(x) {
  x <- as.character(x)
  q <- suppressWarnings(as.numeric(sub("^q", "", x)))
  x[order(q, x)]
}

open_png <- function(path, width = 1500, height = 950) {
  grDevices::png(path, width = width, height = height, res = 125)
}

save_state_norm_panel <- function(state_norms, out_png) {
  state_norms <- state_norms[state_norms$block == "history", , drop = FALSE]
  state_norms$state_norm_sq <- as_num(state_norms$state_norm_sq)
  state_norms$time <- as_num(state_norms$time)
  lanes <- lane_order(unique(state_norms$lane))
  open_png(out_png)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))
  for (lane in lanes) {
    row <- state_norms[state_norms$lane == lane, , drop = FALSE]
    graphics::plot(
      row$time, row$state_norm_sq,
      type = "l", lwd = 1.1, col = "#1f77b4",
      xlab = "time", ylab = "state norm sq",
      main = sprintf("%s history state norm", lane)
    )
  }
  invisible(TRUE)
}

save_state_coordinate_panel <- function(coords, out_png) {
  coords$coordinate <- as.character(coords$coordinate)
  coords <- coords[coords$block == "history" & coords$coordinate %in% c("1", "2", "3", "4"), , drop = FALSE]
  coords$time <- as_num(coords$time)
  coords$value <- as_num(coords$value)
  lanes <- lane_order(unique(coords$lane))
  open_png(out_png)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))
  for (lane in lanes) {
    row <- coords[coords$lane == lane, , drop = FALSE]
    split_rows <- split(row, row$coordinate)
    yrange <- range(row$value, finite = TRUE)
    graphics::plot(
      NA_real_, NA_real_, xlim = range(row$time, finite = TRUE), ylim = yrange,
      xlab = "time", ylab = "state value",
      main = sprintf("%s selected state coordinates", lane)
    )
    cols <- c("#1f77b4", "#d62728", "#2ca02c", "#9467bd")
    i <- 0L
    for (coord in names(split_rows)) {
      i <- i + 1L
      graphics::lines(split_rows[[coord]]$time, split_rows[[coord]]$value, col = cols[[((i - 1L) %% length(cols)) + 1L]], lwd = 1)
    }
    graphics::legend("topright", legend = names(split_rows), col = cols[seq_along(split_rows)], lty = 1, cex = 0.75, bty = "n")
  }
  invisible(TRUE)
}

max_by_lane_quantity <- function(findings, quantity, block_pattern = NULL) {
  row <- findings[findings$quantity == quantity, , drop = FALSE]
  if (!is.null(block_pattern)) {
    row <- row[grepl(block_pattern, row$block), , drop = FALSE]
  }
  if (!nrow(row)) return(data.frame())
  row$max <- as_num(row$max)
  row$min <- as_num(row$min)
  lanes <- lane_order(unique(row$lane))
  data.frame(
    lane = lanes,
    min = vapply(lanes, function(lane) min(row$min[row$lane == lane], na.rm = TRUE), numeric(1)),
    max = vapply(lanes, function(lane) max(row$max[row$lane == lane], na.rm = TRUE), numeric(1)),
    max_abs = vapply(lanes, function(lane) max(abs(c(row$min[row$lane == lane], row$max[row$lane == lane])), na.rm = TRUE), numeric(1))
  )
}

save_latent_pseudodata_panel <- function(findings, out_png) {
  e_inv <- max_by_lane_quantity(findings, "E.inv.uts")
  fff <- max_by_lane_quantity(findings, "FFF", "^history$")
  qqq <- max_by_lane_quantity(findings, "QQQ_diag")
  open_png(out_png)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mfrow = c(1, 3), mar = c(6, 4, 3, 1))
  if (nrow(e_inv)) {
    graphics::barplot(e_inv$max, names.arg = e_inv$lane, las = 2, col = "#4c78a8", ylab = "max", main = "saved max E[1/u]")
    graphics::abline(h = 5000, col = "#d62728", lty = 2)
  }
  if (nrow(fff)) {
    graphics::barplot(fff$max_abs, names.arg = fff$lane, las = 2, col = "#f58518", ylab = "max abs", main = "saved history |FFF|")
    graphics::abline(h = 1000, col = "#d62728", lty = 2)
  }
  if (nrow(qqq)) {
    graphics::barplot(qqq$max, names.arg = qqq$lane, las = 2, col = "#54a24b", ylab = "max diag", main = "saved history QQQ diag")
    graphics::abline(h = 10000, col = "#d62728", lty = 2)
  }
  invisible(TRUE)
}

save_sigma_gamma_panel <- function(findings, live_status, out_png) {
  sig <- max_by_lane_quantity(findings, "E.sigma")
  gam <- max_by_lane_quantity(findings, "E.gam")
  open_png(out_png)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mfrow = c(1, 3), mar = c(6, 4, 3, 1))
  if (nrow(sig)) graphics::barplot(sig$max, names.arg = sig$lane, las = 2, col = "#72b7b2", ylab = "max", main = "saved E[sigma]")
  if (nrow(gam)) graphics::barplot(gam$max_abs, names.arg = gam$lane, las = 2, col = "#e45756", ylab = "max abs", main = "saved |E[gamma]|")
  if (!is.null(live_status) && nrow(live_status)) {
    live_status$state_norm_sq <- as_num(live_status$state_norm_sq)
    graphics::barplot(
      live_status$state_norm_sq,
      names.arg = live_status$lane,
      las = 2, col = "#b279a2",
      ylab = "terminal state norm sq",
      main = "terminal fit log state norm"
    )
  }
  invisible(TRUE)
}

save_guard_panel <- function(guard, out_png) {
  guard$iter <- as_num(guard$iter)
  guard$max <- as_num(guard$max)
  guard$abs_cap <- as_num(guard$abs_cap)
  open_png(out_png, width = 1400, height = 850)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::par(mar = c(5, 5, 3, 2))
  graphics::plot(
    guard$iter, guard$max,
    type = "b", pch = 19, lwd = 1.2, col = "#d62728",
    xlab = "iteration", ylab = "guarded max",
    main = "q05 live guard burst: historical E[1/u]"
  )
  cap <- unique(guard$abs_cap[is.finite(guard$abs_cap)])
  if (length(cap)) graphics::abline(h = cap[[1L]], lty = 2, col = "#333333")
  invisible(TRUE)
}

copy_trace_pngs <- function() {
  trace_dir <- file.path(out_dir, "source_trace_pngs")
  dir.create(trace_dir, recursive = TRUE, showWarnings = FALSE)
  wanted <- list.files(
    runtime_dir,
    pattern = "(_E\\.inv\\.uts_history|_FFF_history|_QQQ_diag_history|_E\\.sts_history|_E\\.uts_history)\\.png$",
    full.names = TRUE
  )
  if (length(wanted)) {
    file.copy(wanted, file.path(trace_dir, basename(wanted)), overwrite = TRUE)
  }
  invisible(wanted)
}

state_norms <- read_required_csv("state_norms.csv")
state_totals <- read_required_csv("state_norm_totals.csv")
coords <- read_required_csv("selected_state_coordinates.csv")
findings <- read_required_csv("runtime_key_findings.csv")
live_status <- NULL
if (!is.null(live_status_csv) && file.exists(live_status_csv)) {
  live_status <- utils::read.csv(live_status_csv, stringsAsFactors = FALSE, check.names = FALSE)
}
guard <- NULL
if (!is.null(guard_csv) && file.exists(guard_csv)) {
  guard <- utils::read.csv(guard_csv, stringsAsFactors = FALSE, check.names = FALSE)
}

save_state_norm_panel(state_norms, file.path(out_dir, "state_norm_history_panel.png"))
save_state_coordinate_panel(coords, file.path(out_dir, "selected_state_coordinates_panel.png"))
save_latent_pseudodata_panel(findings, file.path(out_dir, "latent_pseudodata_extremes_panel.png"))
save_sigma_gamma_panel(findings, live_status, file.path(out_dir, "sigma_gamma_state_summary_panel.png"))
copied <- copy_trace_pngs()
if (!is.null(guard) && nrow(guard)) {
  save_guard_panel(guard, file.path(out_dir, "q05_e_inv_u_guard_burst.png"))
}

utils::write.csv(state_totals, file.path(out_dir, "state_norm_totals.csv"), row.names = FALSE)
utils::write.csv(findings, file.path(out_dir, "runtime_key_findings.csv"), row.names = FALSE)
if (!is.null(guard)) utils::write.csv(guard, file.path(out_dir, "pseudodata_guard_events.csv"), row.names = FALSE)
if (!is.null(live_status)) utils::write.csv(live_status, file.path(out_dir, "live_status.csv"), row.names = FALSE)

guard_summary <- "No guard CSV was supplied or no guard rows were present."
guard_interpretation <- c(
  "The supplied saved outputs are visually summarized for review. No live guard rows were supplied or observed,",
  "so this bundle does not show a live pseudo-data/latent guard burst."
)
if (!is.null(guard) && nrow(guard)) {
  peak_i <- which.max(as_num(guard$max))
  guard_summary <- sprintf(
    "Guard CSV contains %d rows. Peak `%s`/`%s` at iteration %s was max=%s with cap=%s.",
    nrow(guard),
    guard$quantity[[peak_i]],
    guard$block[[peak_i]],
    guard$iter[[peak_i]],
    guard$max[[peak_i]],
    guard$abs_cap[[peak_i]]
  )
  guard_interpretation <- c(
    "The saved outputs are visually stable in terminal summaries, but the supplied live guard CSV contains",
    "guard rows. Treat this as evidence requiring causal ablation or guard-policy review before promotion."
  )
}

readme <- c(
  "# exDQLM keep curated evidence bundle",
  "",
  "Generated by `repro/audits/exdqlm_keep_curated_evidence_bundle.R`.",
  "",
  "This is a compact review bundle from existing guarded-run outputs. It does not refit the model and does not prove",
  "which repair was causal. Use it to inspect the repaired run before ablations.",
  "",
  "## Inputs",
  "",
  sprintf("- runtime audit directory: `%s`", normalizePath(runtime_dir, mustWork = FALSE)),
  sprintf("- guard CSV: `%s`", ifelse(is.null(guard_csv), "", normalizePath(guard_csv, mustWork = FALSE))),
  sprintf("- live status CSV: `%s`", ifelse(is.null(live_status_csv), "", normalizePath(live_status_csv, mustWork = FALSE))),
  "",
  "## Outputs",
  "",
  "- `state_norm_history_panel.png`: history state norm by lane.",
  "- `latent_pseudodata_extremes_panel.png`: saved-output maxima for `E[1/u]`, `FFF`, and `QQQ_diag`.",
  "- `sigma_gamma_state_summary_panel.png`: saved sigma/gamma summary and terminal state norm when live status is supplied.",
  "- `selected_state_coordinates_panel.png`: first selected historical state coordinates by lane.",
  "- `q05_e_inv_u_guard_burst.png`: live guard burst plot when guard rows are supplied.",
  "- `source_trace_pngs/`: selected source trace PNGs copied from the runtime audit.",
  "- CSV copies of the compact evidence tables used by these plots.",
  "",
  "## Guard Summary",
  "",
  guard_summary,
  "",
  "## Interpretation",
  "",
  guard_interpretation
)
writeLines(readme, file.path(out_dir, "README.md"))

cat(sprintf("Curated evidence bundle wrote: %s\n", normalizePath(out_dir, mustWork = FALSE)))
cat(sprintf("Copied %d source trace PNGs\n", length(copied)))
