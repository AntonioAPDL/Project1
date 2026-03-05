#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
run_root <- if (length(args) >= 1L) args[[1L]] else "repro/runs/diag_ndlm_only_legacy_bridge_fit_20260226"
run_root <- normalizePath(run_root, mustWork = TRUE)

fit_root <- file.path(run_root, "fit")
out_dir <- file.path(fit_root, "diagnostics", "ndlm_main_legacy")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

rdata_candidates <- list.files(
  file.path(fit_root, "ndlm_main", "outputs"),
  pattern = "\\.RData$",
  full.names = TRUE
)
if (length(rdata_candidates) == 0L) {
  stop("No NDLM legacy .RData output found under fit/ndlm_main/outputs.", call. = FALSE)
}
rdata_path <- rdata_candidates[[1L]]

log_path <- file.path(fit_root, "ndlm_main", "logs", "ndlm_legacy.log")
if (!file.exists(log_path)) {
  stop("NDLM legacy log not found at fit/ndlm_main/logs/ndlm_legacy.log", call. = FALSE)
}

e <- new.env()
load(rdata_path, envir = e)
obj_names <- ls(e)

pick_one <- function(prefix) {
  hits <- obj_names[startsWith(obj_names, prefix)]
  if (length(hits) == 0L) return(NULL)
  hits[[1L]]
}

sigma_obj_name <- pick_one("seq.sigma_")
elbo_obj_name <- pick_one("seq.elbo_")
newtheta_obj_name <- pick_one("new.theta.out_")

if (is.null(sigma_obj_name) || is.null(elbo_obj_name) || is.null(newtheta_obj_name)) {
  stop("Missing required objects in NDLM output: seq.sigma_*, seq.elbo_*, new.theta.out_*.", call. = FALSE)
}

sigma_raw <- get(sigma_obj_name, envir = e)
elbo <- as.numeric(get(elbo_obj_name, envir = e))
new_theta <- get(newtheta_obj_name, envir = e)

if (is.null(dim(sigma_raw))) {
  sigma_mat <- matrix(as.numeric(sigma_raw), nrow = 1L)
} else {
  sigma_mat <- as.matrix(sigma_raw)
}
mode(sigma_mat) <- "numeric"
sigma_mat <- sigma_mat[is.finite(rowSums(sigma_mat)), , drop = FALSE]

if (ncol(sigma_mat) <= 1L && nrow(sigma_mat) > 1L) {
  sigma_mat <- t(sigma_mat)
}

n_iter <- max(length(elbo), ncol(sigma_mat))
iter_index <- seq_len(n_iter)

pad_to <- function(x, n) {
  if (length(x) >= n) return(x[seq_len(n)])
  c(x, rep(NA_real_, n - length(x)))
}

elbo <- pad_to(elbo, n_iter)
if (ncol(sigma_mat) < n_iter) {
  sigma_pad <- matrix(NA_real_, nrow = nrow(sigma_mat), ncol = n_iter)
  sigma_pad[, seq_len(ncol(sigma_mat))] <- sigma_mat
  sigma_mat <- sigma_pad
} else if (ncol(sigma_mat) > n_iter) {
  sigma_mat <- sigma_mat[, seq_len(n_iter), drop = FALSE]
}

scale_names <- rownames(sigma_mat)
if (is.null(scale_names) || any(!nzchar(scale_names))) {
  scale_names <- sprintf("scale_%02d", seq_len(nrow(sigma_mat)))
}
rownames(sigma_mat) <- scale_names

elbo_delta <- c(NA_real_, diff(elbo))
elbo_abs_delta <- abs(elbo_delta)

png(file.path(out_dir, "ndlm_legacy_elbo_trace.png"), width = 1400, height = 900, res = 130)
par(mar = c(4.5, 5, 3, 1))
plot(iter_index, elbo, type = "b", pch = 16, cex = 0.7, lwd = 2,
     xlab = "Iteration", ylab = "ELBO", main = "NDLM Legacy ELBO Trace")
grid(col = "grey85")
dev.off()

png(file.path(out_dir, "ndlm_legacy_elbo_delta_trace.png"), width = 1400, height = 900, res = 130)
par(mfrow = c(2, 1), mar = c(4, 5, 2.5, 1))
plot(iter_index, elbo_delta, type = "b", pch = 16, cex = 0.7, lwd = 2,
     xlab = "Iteration", ylab = expression(Delta * " ELBO"),
     main = "ELBO First Difference")
abline(h = 0, col = "grey40", lty = 2)
grid(col = "grey85")
plot(iter_index, elbo_abs_delta, type = "b", pch = 16, cex = 0.7, lwd = 2, log = "y",
     xlab = "Iteration", ylab = expression("|" * Delta * " ELBO|"),
     main = "Absolute ELBO Difference (log-scale)")
grid(col = "grey85")
dev.off()

png(file.path(out_dir, "ndlm_legacy_sigma_trace.png"), width = 1400, height = 900, res = 130)
par(mar = c(4.5, 5, 3, 1))
matplot(t(sigma_mat), type = "b", pch = 16, cex = 0.65, lwd = 2, lty = 1,
        xlab = "Iteration", ylab = expression(sigma^2),
        main = "NDLM Legacy Sigma Trace by Scale")
grid(col = "grey85")
legend("topright", legend = scale_names, col = seq_len(nrow(sigma_mat)), lty = 1, lwd = 2, bty = "n")
dev.off()

png(file.path(out_dir, "ndlm_legacy_sigma_heatmap.png"), width = 1400, height = 900, res = 130)
par(mar = c(5, 6, 3, 2))
z <- sigma_mat
image(
  x = seq_len(ncol(z)),
  y = seq_len(nrow(z)),
  z = t(z[, ncol(z):1, drop = FALSE]),
  col = colorRampPalette(c("#f7fbff", "#6baed6", "#08306b"))(100),
  xlab = "Iteration",
  ylab = "Scale Index",
  main = "NDLM Legacy Sigma Heatmap",
  axes = FALSE
)
axis(1)
axis(2, at = seq_len(nrow(z)), labels = rev(scale_names), las = 2)
box()
dev.off()

sigma_min <- apply(sigma_mat, 2, function(x) if (all(!is.finite(x))) NA_real_ else min(x, na.rm = TRUE))
sigma_med <- apply(sigma_mat, 2, function(x) if (all(!is.finite(x))) NA_real_ else median(x, na.rm = TRUE))
sigma_max <- apply(sigma_mat, 2, function(x) if (all(!is.finite(x))) NA_real_ else max(x, na.rm = TRUE))

png(file.path(out_dir, "ndlm_legacy_sigma_range_trace.png"), width = 1400, height = 900, res = 130)
par(mar = c(4.5, 5, 3, 1))
plot(iter_index, sigma_med, type = "l", lwd = 3, col = "#1f78b4",
     ylim = range(c(sigma_min, sigma_max), na.rm = TRUE),
     xlab = "Iteration", ylab = expression(sigma^2),
     main = "Sigma Min / Median / Max Across Scales")
lines(iter_index, sigma_min, lwd = 2, lty = 2, col = "#33a02c")
lines(iter_index, sigma_max, lwd = 2, lty = 2, col = "#e31a1c")
grid(col = "grey85")
legend("topright", legend = c("median", "min", "max"),
       col = c("#1f78b4", "#33a02c", "#e31a1c"), lty = c(1, 2, 2), lwd = c(3, 2, 2), bty = "n")
dev.off()

std_err <- new_theta$standard_forecast_errors
if (!is.null(std_err)) {
  std_err <- as.matrix(std_err)
  mode(std_err) <- "numeric"
  err_scale_names <- rownames(std_err)
  if (is.null(err_scale_names) || any(!nzchar(err_scale_names))) {
    err_scale_names <- sprintf("scale_%02d", seq_len(nrow(std_err)))
  }

  png(file.path(out_dir, "ndlm_legacy_standard_forecast_error_density.png"), width = 1400, height = 900, res = 130)
  par(mar = c(4.5, 5, 3, 1))
  cols <- seq_len(nrow(std_err))
  x_rng <- range(std_err, finite = TRUE)
  y_max <- 0
  dens_list <- vector("list", nrow(std_err))
  for (i in seq_len(nrow(std_err))) {
    di <- density(std_err[i, is.finite(std_err[i, ])], na.rm = TRUE)
    dens_list[[i]] <- di
    y_max <- max(y_max, di$y, na.rm = TRUE)
  }
  plot(NA, xlim = x_rng, ylim = c(0, y_max * 1.05), xlab = "Standard Forecast Error",
       ylab = "Density", main = "Standard Forecast Error Density by Scale")
  grid(col = "grey85")
  for (i in seq_len(nrow(std_err))) {
    lines(dens_list[[i]], col = cols[i], lwd = 2)
  }
  legend("topright", legend = err_scale_names, col = cols, lty = 1, lwd = 2, bty = "n")
  dev.off()

  roll_mean_abs <- function(x, k = 100L) {
    n <- length(x)
    out <- rep(NA_real_, n)
    if (n == 0L) return(out)
    for (idx in seq_len(n)) {
      lo <- max(1L, idx - k + 1L)
      seg <- x[lo:idx]
      out[idx] <- mean(abs(seg), na.rm = TRUE)
    }
    out
  }

  png(file.path(out_dir, "ndlm_legacy_standard_forecast_error_rollabs.png"), width = 1400, height = 900, res = 130)
  par(mar = c(4.5, 5, 3, 1))
  t_idx <- seq_len(ncol(std_err))
  roll <- t(apply(std_err, 1, roll_mean_abs, k = 100L))
  matplot(t(roll), type = "l", lwd = 2, lty = 1, col = cols,
          xlab = "Time Index", ylab = "Rolling Mean |Std Error| (window=100)",
          main = "Standard Forecast Error Rolling Magnitude")
  grid(col = "grey85")
  legend("topright", legend = err_scale_names, col = cols, lty = 1, lwd = 2, bty = "n")
  dev.off()
}

if (!is.null(new_theta$sm)) {
  sm <- as.matrix(new_theta$sm)
  mode(sm) <- "numeric"
  state_norm <- apply(sm, 2, function(v) sqrt(sum(v^2, na.rm = TRUE)))
  png(file.path(out_dir, "ndlm_legacy_state_l2_norm_trace.png"), width = 1400, height = 900, res = 130)
  par(mar = c(4.5, 5, 3, 1))
  plot(seq_along(state_norm), state_norm, type = "l", lwd = 2,
       xlab = "Time Index", ylab = "L2 norm of sm[,t]",
       main = "State Magnitude Trace")
  grid(col = "grey85")
  dev.off()
}

log_lines <- readLines(log_path, warn = FALSE)
progress_lines <- grep("\\[gamsig_progress\\]", log_lines, value = TRUE)
parse_progress <- function(lines) {
  if (length(lines) == 0L) return(NULL)
  pattern <- ".*iter=([0-9]+)\\s+elbo=([-0-9.eE]+)\\s+crit_elbo=([-0-9.eE]+)\\s+sigma_exp=([-0-9.eE]+)\\s+gamma_exp=([-0-9.eE]+)\\s+state_norm_sq=([-0-9.eE]+).*"
  m <- regexec(pattern, lines, perl = TRUE)
  mm <- regmatches(lines, m)
  mm <- mm[lengths(mm) == 7L]
  if (length(mm) == 0L) return(NULL)
  mat <- do.call(rbind, mm)
  data.frame(
    iter = as.numeric(mat[, 2]),
    elbo = as.numeric(mat[, 3]),
    crit_elbo = as.numeric(mat[, 4]),
    sigma_exp = as.numeric(mat[, 5]),
    gamma_exp = as.numeric(mat[, 6]),
    state_norm_sq = as.numeric(mat[, 7])
  )
}

progress_df <- parse_progress(progress_lines)
if (!is.null(progress_df) && nrow(progress_df) > 0L) {
  png(file.path(out_dir, "ndlm_legacy_vb_progress_from_log.png"), width = 1400, height = 1200, res = 130)
  par(mfrow = c(3, 1), mar = c(4, 5, 2.5, 1))
  plot(progress_df$iter, progress_df$crit_elbo, type = "b", pch = 16, cex = 0.7, lwd = 2, log = "y",
       xlab = "Iteration", ylab = "crit_elbo (log)", main = "VB Criterion Trace (from log)")
  grid(col = "grey85")
  matplot(progress_df$iter, cbind(progress_df$sigma_exp, progress_df$gamma_exp), type = "b",
          pch = 16, cex = 0.7, lwd = 2, lty = 1, xlab = "Iteration", ylab = "Expectation",
          main = "sigma_exp and gamma_exp (from log)")
  legend("topright", legend = c("sigma_exp", "gamma_exp"), col = 1:2, lty = 1, lwd = 2, bty = "n")
  grid(col = "grey85")
  plot(progress_df$iter, progress_df$state_norm_sq, type = "b", pch = 16, cex = 0.7, lwd = 2,
       xlab = "Iteration", ylab = "state_norm_sq", main = "State Norm Squared (from log)")
  grid(col = "grey85")
  dev.off()
  utils::write.csv(progress_df, file.path(out_dir, "ndlm_legacy_vb_progress_from_log.csv"), row.names = FALSE)
}

summary_df <- data.frame(
  metric = c(
    "n_iterations",
    "elbo_start",
    "elbo_end",
    "elbo_delta_last",
    "elbo_abs_delta_last",
    "sigma_global_min",
    "sigma_global_max",
    "sigma_global_sd",
    "sigma_n_scales"
  ),
  value = c(
    n_iter,
    elbo[1],
    elbo[n_iter],
    elbo_delta[n_iter],
    elbo_abs_delta[n_iter],
    suppressWarnings(min(sigma_mat, na.rm = TRUE)),
    suppressWarnings(max(sigma_mat, na.rm = TRUE)),
    stats::sd(as.numeric(sigma_mat), na.rm = TRUE),
    nrow(sigma_mat)
  )
)

utils::write.csv(summary_df, file.path(out_dir, "ndlm_legacy_trace_summary.csv"), row.names = FALSE)

manifest <- data.frame(
  artifact = c(
    "ndlm_legacy_elbo_trace.png",
    "ndlm_legacy_elbo_delta_trace.png",
    "ndlm_legacy_sigma_trace.png",
    "ndlm_legacy_sigma_heatmap.png",
    "ndlm_legacy_sigma_range_trace.png",
    "ndlm_legacy_standard_forecast_error_density.png",
    "ndlm_legacy_standard_forecast_error_rollabs.png",
    "ndlm_legacy_state_l2_norm_trace.png",
    "ndlm_legacy_vb_progress_from_log.png",
    "ndlm_legacy_vb_progress_from_log.csv",
    "ndlm_legacy_trace_summary.csv"
  )
)
manifest$path <- file.path(out_dir, manifest$artifact)
manifest$exists <- file.exists(manifest$path)
utils::write.csv(manifest, file.path(out_dir, "ndlm_legacy_diagnostics_manifest.csv"), row.names = FALSE)

cat(sprintf("Diagnostics written to: %s\n", out_dir))
