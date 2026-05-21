#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) {
  stop(
    paste(
      "Usage:",
      "Rscript repro/audits/exdqlm_keep_runtime_stability_audit.R",
      "--out reports/exdqlm_keep_runtime_stability_<tag> FILE1.RData [FILE2.RData ...]"
    ),
    call. = FALSE
  )
}

out_dir <- file.path("reports", "exdqlm_keep_runtime_stability_audit_20260520")
if (length(args) >= 2L && identical(args[[1L]], "--out")) {
  out_dir <- args[[2L]]
  args <- args[-c(1L, 2L)]
}
if (length(args) < 1L) {
  stop("At least one .RData path is required", call. = FALSE)
}
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

safe_quantile <- function(x, prob) {
  x <- as.numeric(x)
  x <- x[is.finite(x)]
  if (!length(x)) return(NA_real_)
  as.numeric(stats::quantile(x, prob, names = FALSE, type = 8))
}

summarize_vec <- function(x, lane, object, quantity, source = NA_character_, block = NA_character_) {
  raw <- as.numeric(x)
  finite <- raw[is.finite(raw)]
  data.frame(
    lane = lane,
    object = object,
    quantity = quantity,
    source = source,
    block = block,
    n = length(raw),
    finite_n = length(finite),
    finite_frac = if (length(raw)) length(finite) / length(raw) else NA_real_,
    positive_frac = if (length(finite)) mean(finite > 0) else NA_real_,
    min = if (length(finite)) min(finite) else NA_real_,
    q01 = safe_quantile(finite, 0.01),
    q05 = safe_quantile(finite, 0.05),
    median = safe_quantile(finite, 0.50),
    q95 = safe_quantile(finite, 0.95),
    q99 = safe_quantile(finite, 0.99),
    max = if (length(finite)) max(finite) else NA_real_
  )
}

extract_cube_diagonal <- function(x) {
  d <- dim(x)
  if (is.null(d) || length(d) != 3L) return(NULL)
  if (d[[1L]] == d[[2L]]) {
    return(unlist(lapply(seq_len(d[[3L]]), function(i) diag(x[, , i, drop = TRUE])), use.names = FALSE))
  }
  if (d[[2L]] == d[[3L]]) {
    return(unlist(lapply(seq_len(d[[1L]]), function(i) diag(x[i, , , drop = TRUE])), use.names = FALSE))
  }
  NULL
}

plot_vector_trace <- function(x, out_png, main, ylab) {
  raw <- as.numeric(x)
  if (!length(raw) || !any(is.finite(raw))) return(invisible(FALSE))
  grDevices::png(out_png, width = 1400, height = 850)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::plot(
    seq_along(raw), raw, type = "l", lwd = 1.2,
    xlab = "index", ylab = ylab, main = main
  )
  invisible(TRUE)
}

find_first <- function(nms, pattern) {
  hit <- grep(pattern, nms, value = TRUE)
  if (length(hit)) hit[[1L]] else NA_character_
}

lane_from_path <- function(path) {
  base <- basename(path)
  m <- regexpr("DISC_variables_[0-9]+", base)
  if (m > 0) return(sub("DISC_variables_", "q", regmatches(base, m)))
  tools::file_path_sans_ext(base)
}

as_source_name <- function(i, baseline = FALSE) {
  if (baseline && i == 1L) return("target")
  if (baseline) return(sprintf("source_%d", i - 1L))
  sprintf("source_%d", i)
}

plot_matrix_rows <- function(M, out_png, main, ylab) {
  M <- as.matrix(M)
  if (!nrow(M) || !ncol(M) || any(!is.finite(range(M, na.rm = TRUE)))) return(invisible(FALSE))
  grDevices::png(out_png, width = 1400, height = 850)
  on.exit(grDevices::dev.off(), add = TRUE)
  graphics::matplot(t(M), type = "l", lty = 1, lwd = 1.2, xlab = "time/lead", ylab = ylab, main = main)
  graphics::legend("topright", legend = rownames(M) %||% paste0("row", seq_len(nrow(M))), col = seq_len(nrow(M)), lty = 1, cex = 0.8)
  invisible(TRUE)
}

`%||%` <- function(x, y) if (is.null(x)) y else x

all_summaries <- list()
state_norms <- list()
state_norm_totals <- list()
state_coords <- list()
manifest <- list()

for (path in args) {
  if (!file.exists(path)) {
    warning(sprintf("Skipping missing path: %s", path), call. = FALSE)
    next
  }
  lane <- lane_from_path(path)
  env <- new.env(parent = emptyenv())
  loaded <- load(path, envir = env)
  nms <- ls(env)
  manifest[[length(manifest) + 1L]] <- data.frame(
    lane = lane,
    path = normalizePath(path, mustWork = FALSE),
    object_count = length(nms),
    loaded_objects = paste(loaded, collapse = ";")
  )

  sts_name <- find_first(nms, "^new\\.sts\\.out_")
  uts_name <- find_first(nms, "^new\\.uts\\.out_")
  sts_f_name <- find_first(nms, "^new\\.sts_ens\\.out_")
  uts_f_name <- find_first(nms, "^new\\.uts_ens\\.out_")
  theta_name <- find_first(nms, "^new\\.theta\\.out_")
  gamsig_name <- find_first(nms, "^new\\.gamsig\\.out_")
  fff_name <- find_first(nms, "^ext\\.f_")
  qqq_name <- find_first(nms, "^ext\\.q_")
  fff_f_name <- find_first(nms, "^ext\\.f_f_")
  qqq_f_name <- find_first(nms, "^ext\\.q_f_")
  seq_elbo_name <- find_first(nms, "^seq\\.elbo_")
  seq_gamma_name <- find_first(nms, "^seq\\.gamma_")
  seq_sigma_name <- find_first(nms, "^seq\\.sigma_")

  add_summary <- function(x, object, quantity, source = NA_character_, block = NA_character_) {
    all_summaries[[length(all_summaries) + 1L]] <<- summarize_vec(x, lane, object, quantity, source, block)
  }

  if (!is.na(sts_name)) {
    sts <- get(sts_name, envir = env)
    for (field in intersect(c("E.sts", "E.sts2"), names(sts))) {
      M <- as.matrix(sts[[field]])
      for (i in seq_len(nrow(M))) add_summary(M[i, ], sts_name, field, as_source_name(i, baseline = TRUE), "history")
      rownames(M) <- vapply(seq_len(nrow(M)), as_source_name, character(1), baseline = TRUE)
      plot_matrix_rows(M, file.path(out_dir, sprintf("%s_%s_history.png", lane, field)), sprintf("%s %s history", lane, field), field)
    }
    if ("tot.entrop" %in% names(sts)) add_summary(sts$tot.entrop, sts_name, "tot.entrop", block = "history")
  }

  if (!is.na(uts_name)) {
    uts <- get(uts_name, envir = env)
    for (field in intersect(c("E.uts", "E.inv.uts"), names(uts))) {
      M <- as.matrix(uts[[field]])
      for (i in seq_len(nrow(M))) add_summary(M[i, ], uts_name, field, as_source_name(i, baseline = TRUE), "history")
      rownames(M) <- vapply(seq_len(nrow(M)), as_source_name, character(1), baseline = TRUE)
      plot_matrix_rows(M, file.path(out_dir, sprintf("%s_%s_history.png", lane, field)), sprintf("%s %s history", lane, field), field)
    }
    if ("E.log.uts" %in% names(uts)) add_summary(uts$E.log.uts, uts_name, "E.log.uts", block = "history")
    if ("tot.entrop" %in% names(uts)) add_summary(uts$tot.entrop, uts_name, "tot.entrop", block = "history")
  }

  if (!is.na(sts_f_name)) {
    sts_f <- get(sts_f_name, envir = env)
    for (field in intersect(c("E.sts", "E.sts2"), names(sts_f))) {
      for (i in seq_along(sts_f[[field]])) add_summary(sts_f[[field]][[i]], sts_f_name, field, as_source_name(i), "forecast")
    }
    if ("tot.entrop" %in% names(sts_f)) {
      for (i in seq_along(sts_f$tot.entrop)) add_summary(sts_f$tot.entrop[[i]], sts_f_name, "tot.entrop", as_source_name(i), "forecast")
    }
  }

  if (!is.na(uts_f_name)) {
    uts_f <- get(uts_f_name, envir = env)
    for (field in intersect(c("E.uts", "E.inv.uts", "E.log.uts"), names(uts_f))) {
      for (i in seq_along(uts_f[[field]])) add_summary(uts_f[[field]][[i]], uts_f_name, field, as_source_name(i), "forecast")
    }
    if ("tot.entrop" %in% names(uts_f)) {
      for (i in seq_along(uts_f$tot.entrop)) add_summary(uts_f$tot.entrop[[i]], uts_f_name, "tot.entrop", as_source_name(i), "forecast")
    }
  }

  if (!is.na(gamsig_name)) {
    gamsig <- get(gamsig_name, envir = env)
    for (field in intersect(c(
      "E.gam", "E.sigma", "E.inv.sigma", "E.c2.invb.absgam2.sigma",
      "E.c.invb.absgam", "E.invb.inv.sigma", "E.a.invb.inv.sigma",
      "E.log.sig.b", "E.log.sig"
    ), names(gamsig))) {
      add_summary(gamsig[[field]], gamsig_name, field, block = "gamsig")
    }
  }

  if (!is.na(fff_name)) {
    fff <- get(fff_name, envir = env)
    add_summary(fff, fff_name, "FFF", block = "history")
    plot_vector_trace(fff, file.path(out_dir, sprintf("%s_FFF_history.png", lane)), sprintf("%s FFF history", lane), "FFF")
  }
  if (!is.na(qqq_name)) {
    qqq <- get(qqq_name, envir = env)
    add_summary(qqq, qqq_name, "QQQ", block = "history_all_entries")
    qqq_diag <- extract_cube_diagonal(qqq)
    if (!is.null(qqq_diag)) {
      add_summary(qqq_diag, qqq_name, "QQQ_diag", block = "history_diagonal")
      plot_vector_trace(qqq_diag, file.path(out_dir, sprintf("%s_QQQ_diag_history.png", lane)), sprintf("%s QQQ diagonal history", lane), "QQQ diagonal")
    }
  }
  if (!is.na(fff_f_name)) {
    fff_f <- get(fff_f_name, envir = env)
    for (i in seq_along(fff_f)) add_summary(fff_f[[i]], fff_f_name, "FFF_forecast", as_source_name(i), "forecast_raw_source_list")
  }
  if (!is.na(qqq_f_name)) {
    qqq_f <- get(qqq_f_name, envir = env)
    for (i in seq_along(qqq_f)) {
      add_summary(qqq_f[[i]], qqq_f_name, "QQQ_forecast", as_source_name(i), "forecast_raw_source_list_all_entries")
      qqq_f_diag <- extract_cube_diagonal(qqq_f[[i]])
      if (!is.null(qqq_f_diag)) add_summary(qqq_f_diag, qqq_f_name, "QQQ_forecast_diag", as_source_name(i), "forecast_raw_source_list_diagonal")
    }
  }

  for (seq_name in c(seq_elbo_name, seq_gamma_name, seq_sigma_name)) {
    if (!is.na(seq_name)) add_summary(get(seq_name, envir = env), seq_name, seq_name, block = "trace")
  }

  if (!is.na(theta_name)) {
    theta <- get(theta_name, envir = env)
    if (!is.null(theta$sm)) {
      sm <- as.matrix(theta$sm)
      state_norms[[length(state_norms) + 1L]] <- data.frame(
        lane = lane,
        block = "history",
        time = seq_len(ncol(sm)),
        state_norm_sq = colSums(sm^2)
      )
      state_norm_totals[[length(state_norm_totals) + 1L]] <- data.frame(
        lane = lane,
        block = "history",
        n_state = nrow(sm),
        n_time = ncol(sm),
        finite_frac = mean(is.finite(sm)),
        total_state_norm_sq = sum(sm^2, na.rm = TRUE),
        max_time_state_norm_sq = max(colSums(sm^2), na.rm = TRUE),
        frobenius_norm = sqrt(sum(sm^2, na.rm = TRUE))
      )
      keep_rows <- seq_len(min(12L, nrow(sm)))
      state_coords[[length(state_coords) + 1L]] <- data.frame(
        lane = lane,
        block = "history",
        coordinate = rep(keep_rows, each = ncol(sm)),
        time = rep(seq_len(ncol(sm)), times = length(keep_rows)),
        value = as.vector(t(sm[keep_rows, , drop = FALSE]))
      )
    }
    if (!is.null(theta$sm_ens) && is.list(theta$sm_ens)) {
      for (i in seq_along(theta$sm_ens)) {
        sm <- as.matrix(theta$sm_ens[[i]])
        state_norms[[length(state_norms) + 1L]] <- data.frame(
          lane = lane,
          block = sprintf("forecast_%d", i),
          time = seq_len(ncol(sm)),
          state_norm_sq = colSums(sm^2)
        )
        state_norm_totals[[length(state_norm_totals) + 1L]] <- data.frame(
          lane = lane,
          block = sprintf("forecast_%d", i),
          n_state = nrow(sm),
          n_time = ncol(sm),
          finite_frac = mean(is.finite(sm)),
          total_state_norm_sq = sum(sm^2, na.rm = TRUE),
          max_time_state_norm_sq = max(colSums(sm^2), na.rm = TRUE),
          frobenius_norm = sqrt(sum(sm^2, na.rm = TRUE))
        )
        keep_rows <- seq_len(min(12L, nrow(sm)))
        state_coords[[length(state_coords) + 1L]] <- data.frame(
          lane = lane,
          block = sprintf("forecast_%d", i),
          coordinate = rep(keep_rows, each = ncol(sm)),
          time = rep(seq_len(ncol(sm)), times = length(keep_rows)),
          value = as.vector(t(sm[keep_rows, , drop = FALSE]))
        )
      }
    }
  }
}

write_if_any <- function(rows, path) {
  if (length(rows)) {
    write.csv(do.call(rbind, rows), path, row.names = FALSE)
  } else {
    write.csv(data.frame(), path, row.names = FALSE)
  }
}

write_if_any(manifest, file.path(out_dir, "manifest.csv"))
write_if_any(all_summaries, file.path(out_dir, "object_summaries.csv"))
write_if_any(state_norms, file.path(out_dir, "state_norms.csv"))
write_if_any(state_norm_totals, file.path(out_dir, "state_norm_totals.csv"))
write_if_any(state_coords, file.path(out_dir, "selected_state_coordinates.csv"))

if (length(all_summaries) || length(state_norm_totals)) {
  key_rows <- list()
  if (length(all_summaries)) {
    summary_table <- do.call(rbind, all_summaries)
    keep_quantities <- c(
      "E.sts", "E.sts2", "E.uts", "E.inv.uts", "E.log.uts",
      "FFF", "QQQ_diag", "FFF_forecast", "QQQ_forecast_diag",
      "E.gam", "E.sigma", "E.inv.sigma"
    )
    summary_table <- summary_table[summary_table$quantity %in% keep_quantities, , drop = FALSE]
    if (nrow(summary_table)) {
      key_rows[[length(key_rows) + 1L]] <- data.frame(
        lane = summary_table$lane,
        block = summary_table$block,
        source = summary_table$source,
        quantity = summary_table$quantity,
        metric = "distribution",
        finite_frac = summary_table$finite_frac,
        positive_frac = summary_table$positive_frac,
        min = summary_table$min,
        median = summary_table$median,
        q95 = summary_table$q95,
        q99 = summary_table$q99,
        max = summary_table$max
      )
    }
  }
  if (length(state_norm_totals)) {
    norm_table <- do.call(rbind, state_norm_totals)
    key_rows[[length(key_rows) + 1L]] <- data.frame(
      lane = norm_table$lane,
      block = norm_table$block,
      source = NA_character_,
      quantity = "state_norm_sq",
      metric = "total",
      finite_frac = norm_table$finite_frac,
      positive_frac = NA_real_,
      min = norm_table$total_state_norm_sq,
      median = norm_table$total_state_norm_sq,
      q95 = norm_table$max_time_state_norm_sq,
      q99 = norm_table$max_time_state_norm_sq,
      max = norm_table$total_state_norm_sq
    )
  }
  write.csv(do.call(rbind, key_rows), file.path(out_dir, "runtime_key_findings.csv"), row.names = FALSE)
}

readme <- c(
  "# exDQLM keep runtime stability audit",
  "",
  "Generated by `repro/audits/exdqlm_keep_runtime_stability_audit.R`.",
  "",
  "Outputs:",
  "- `manifest.csv`: loaded `.RData` paths and object inventories.",
  "- `object_summaries.csv`: finite/positive fractions and quantiles for latent, sigma/gamma, pseudo-data, and trace objects.",
  "- `state_norms.csv`: state norm squared by lane/block/time.",
  "- `state_norm_totals.csv`: total squared state norms by lane/block, matching the full-matrix norm scale printed by fit logs.",
  "- `selected_state_coordinates.csv`: first selected state coordinates by lane/block/time.",
  "- `runtime_key_findings.csv`: compact high-signal subset used by the tracked runtime findings document.",
  "- `*.png`: lightweight history trace plots for matrix-shaped latent quantities and selected pseudo-data quantities when available.",
  "",
  "This script is read-only with respect to input `.RData` files and writes only to the requested report directory."
)
writeLines(readme, file.path(out_dir, "README.md"))

cat(sprintf("Runtime audit wrote: %s\n", normalizePath(out_dir, mustWork = FALSE)))
