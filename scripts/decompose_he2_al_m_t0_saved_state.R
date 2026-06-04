#!/usr/bin/env Rscript

usage <- function() {
  cat(paste(
    "Usage:",
    "  Rscript scripts/decompose_he2_al_m_t0_saved_state.R --outdir DIR --case LABEL=RDATA [--case LABEL=RDATA ...]",
    sep = "\n"
  ), "\n")
}

args <- commandArgs(trailingOnly = TRUE)
cases <- character(0)
outdir <- ""
i <- 1L
while (i <= length(args)) {
  arg <- args[[i]]
  if (identical(arg, "--case")) {
    i <- i + 1L
    if (i > length(args)) stop("--case requires LABEL=RDATA", call. = FALSE)
    cases <- c(cases, args[[i]])
  } else if (identical(arg, "--outdir")) {
    i <- i + 1L
    if (i > length(args)) stop("--outdir requires DIR", call. = FALSE)
    outdir <- args[[i]]
  } else if (arg %in% c("--help", "-h")) {
    usage()
    quit(save = "no", status = 0)
  } else {
    stop(sprintf("unknown argument: %s", arg), call. = FALSE)
  }
  i <- i + 1L
}

if (!nzchar(outdir) || length(cases) < 1L) {
  usage()
  quit(save = "no", status = 2)
}

dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

safe_label <- function(x) {
  gsub("[^A-Za-z0-9_.=-]+", "_", x)
}

num_or_na <- function(x) {
  if (length(x) < 1L || !is.finite(x[[1L]])) return(NA_real_)
  as.numeric(x[[1L]])
}

summarize_numeric <- function(x, label) {
  vals <- suppressWarnings(as.numeric(x))
  finite <- vals[is.finite(vals)]
  q <- function(p) {
    if (length(finite) < 1L) return(NA_real_)
    as.numeric(stats::quantile(finite, probs = p, na.rm = TRUE, names = FALSE, type = 7))
  }
  data.frame(
    metric = label,
    n = length(vals),
    finite_n = length(finite),
    nonfinite_n = length(vals) - length(finite),
    min = if (length(finite)) min(finite) else NA_real_,
    p01 = q(0.01),
    p05 = q(0.05),
    p25 = q(0.25),
    median = q(0.50),
    mean = if (length(finite)) mean(finite) else NA_real_,
    p75 = q(0.75),
    p95 = q(0.95),
    p99 = q(0.99),
    max = if (length(finite)) max(finite) else NA_real_,
    max_abs = if (length(finite)) max(abs(finite)) else NA_real_,
    stringsAsFactors = FALSE
  )
}

write_rows <- function(path, rows) {
  if (length(rows) < 1L) {
    utils::write.csv(data.frame(), path, row.names = FALSE)
    return(invisible(NULL))
  }
  out <- do.call(rbind, rows)
  utils::write.csv(out, path, row.names = FALSE)
}

top_matrix_cells <- function(mat, label, top_k = 25L) {
  if (is.null(mat)) return(data.frame())
  arr <- as.matrix(mat)
  vals <- as.numeric(arr)
  if (length(vals) < 1L) return(data.frame())
  finite_idx <- which(is.finite(vals))
  if (length(finite_idx) < 1L) return(data.frame())
  ord <- finite_idx[order(abs(vals[finite_idx]), decreasing = TRUE)]
  ord <- ord[seq_len(min(length(ord), top_k))]
  rc <- arrayInd(ord, dim(arr))
  data.frame(
    metric = label,
    row = rc[, 1],
    col = rc[, 2],
    value = vals[ord],
    abs_value = abs(vals[ord]),
    stringsAsFactors = FALSE
  )
}

block_id <- function(row, n_rows) {
  if (row <= 7L) return("shared_quantile")
  if (row <= 14L) return("glofas_discrepancy")
  if (row <= 21L) return("nws_discrepancy")
  if (row == 22L) return("transfer_level")
  if (row > 22L) return("transfer_coefficients")
  sprintf("row_%d_of_%d", row, n_rows)
}

state_block_summary <- function(sm) {
  if (is.null(sm)) return(data.frame())
  mat <- as.matrix(sm)
  n_rows <- nrow(mat)
  rows <- lapply(seq_len(n_rows), function(r) {
    vals <- mat[r, ]
    finite <- vals[is.finite(vals)]
    data.frame(
      block = block_id(r, n_rows),
      row = r,
      n = length(vals),
      finite_n = length(finite),
      max_abs = if (length(finite)) max(abs(finite)) else NA_real_,
      mean_abs = if (length(finite)) mean(abs(finite)) else NA_real_,
      norm_sq = if (length(finite)) sum(finite^2) else NA_real_,
      stringsAsFactors = FALSE
    )
  })
  out <- do.call(rbind, rows)
  blocks <- split(out, out$block)
  do.call(rbind, lapply(names(blocks), function(block_name) {
    block_rows <- blocks[[block_name]]
    data.frame(
      block = block_name,
      row_count = nrow(block_rows),
      max_abs = if (all(!is.finite(block_rows$max_abs))) NA_real_ else max(block_rows$max_abs, na.rm = TRUE),
      mean_abs = if (all(!is.finite(block_rows$mean_abs))) NA_real_ else max(block_rows$mean_abs, na.rm = TRUE),
      norm_sq = if (all(!is.finite(block_rows$norm_sq))) NA_real_ else sum(block_rows$norm_sq, na.rm = TRUE),
      stringsAsFactors = FALSE
    )
  }))
}

find_object <- function(object_names, pattern) {
  hits <- object_names[grepl(pattern, object_names, ignore.case = TRUE)]
  if (length(hits) < 1L) return("")
  hits[[1L]]
}

summarize_named_numeric_fields <- function(obj, prefix, wanted = NULL) {
  if (!is.list(obj)) return(list())
  names_obj <- names(obj)
  if (is.null(names_obj)) return(list())
  rows <- list()
  for (nm in names_obj) {
    value <- obj[[nm]]
    if (!is.null(wanted) && !grepl(wanted, nm, ignore.case = TRUE)) next
    if (is.numeric(value) || is.array(value) || is.matrix(value)) {
      rows[[length(rows) + 1L]] <- summarize_numeric(value, paste(prefix, nm, sep = "."))
    }
  }
  rows
}

compute_pseudodata_summary <- function(gamsig, sts, uts, label) {
  rows <- list()
  if (!is.list(gamsig) || !is.list(sts) || !is.list(uts)) return(rows)
  required <- c("E.c.invb.absgam", "E.a.invb.inv.sigma", "E.invb.inv.sigma")
  if (!all(required %in% names(gamsig)) || !("E.sts" %in% names(sts)) || !("E.inv.uts" %in% names(uts))) {
    return(rows)
  }
  align_to <- function(x, target) {
    x <- as.matrix(x)
    target_dim <- dim(as.matrix(target))
    if (identical(dim(x), target_dim)) return(x)
    if (length(dim(x)) == 2L && identical(dim(t(x)), target_dim)) return(t(x))
    if (nrow(x) == target_dim[[1L]] && ncol(x) == 1L) {
      return(matrix(rep(x[, 1L], target_dim[[2L]]), nrow = target_dim[[1L]], ncol = target_dim[[2L]]))
    }
    if (nrow(x) == 1L && ncol(x) == target_dim[[2L]]) {
      return(matrix(rep(x[1L, ], each = target_dim[[1L]]), nrow = target_dim[[1L]], ncol = target_dim[[2L]]))
    }
    NULL
  }
  target <- as.matrix(uts$E.inv.uts)
  e_inv_uts <- align_to(uts$E.inv.uts, target)
  base <- align_to(gamsig$E.invb.inv.sigma, target)
  e_sts <- align_to(sts$E.sts, target)
  e_c <- align_to(gamsig$E.c.invb.absgam, target)
  e_a <- align_to(gamsig$E.a.invb.inv.sigma, target)
  if (is.null(base) || is.null(e_sts) || is.null(e_inv_uts) || is.null(e_c) || is.null(e_a)) {
    rows[[length(rows) + 1L]] <- data.frame(
      metric = paste(label, "shape_status", sep = "."),
      n = NA_integer_,
      finite_n = NA_integer_,
      nonfinite_n = NA_integer_,
      min = NA_real_,
      p01 = NA_real_,
      p05 = NA_real_,
      p25 = NA_real_,
      median = NA_real_,
      mean = NA_real_,
      p75 = NA_real_,
      p95 = NA_real_,
      p99 = NA_real_,
      max = NA_real_,
      max_abs = NA_real_,
      note = sprintf(
        "cannot_align target=%s base=%s sts=%s inv_uts=%s c=%s a=%s",
        paste(dim(target), collapse = "x"),
        paste(dim(as.matrix(gamsig$E.invb.inv.sigma)), collapse = "x"),
        paste(dim(as.matrix(sts$E.sts)), collapse = "x"),
        paste(dim(as.matrix(uts$E.inv.uts)), collapse = "x"),
        paste(dim(as.matrix(gamsig$E.c.invb.absgam)), collapse = "x"),
        paste(dim(as.matrix(gamsig$E.a.invb.inv.sigma)), collapse = "x")
      ),
      stringsAsFactors = FALSE
    )
    return(rows)
  }
  denom <- suppressWarnings(base * e_inv_uts)
  fff <- suppressWarnings((e_c * e_sts + e_a / e_inv_uts) / base)
  qqq <- suppressWarnings(1 / denom)
  rows[[length(rows) + 1L]] <- summarize_numeric(fff, paste(label, "FFF_history", sep = "."))
  rows[[length(rows) + 1L]] <- summarize_numeric(qqq, paste(label, "QQQ_history_diag", sep = "."))
  rows
}

case_records <- list()

for (case_arg in cases) {
  eq_pos <- regexpr("=", case_arg, fixed = TRUE)[[1L]]
  if (!is.finite(eq_pos) || eq_pos < 2L || eq_pos >= nchar(case_arg)) {
    stop(sprintf("invalid --case value: %s", case_arg), call. = FALSE)
  }
  parts <- c(substr(case_arg, 1L, eq_pos - 1L), substr(case_arg, eq_pos + 1L, nchar(case_arg)))
  label <- safe_label(parts[[1L]])
  rdata_path <- normalizePath(parts[[2L]], mustWork = TRUE)
  case_dir <- file.path(outdir, label)
  dir.create(case_dir, recursive = TRUE, showWarnings = FALSE)

  message(sprintf("[decompose] loading %s", rdata_path))
  object_names <- load(rdata_path)
  theta_name <- find_object(object_names, "theta\\.out")
  gamsig_name <- find_object(object_names, "gamsig")
  uts_name <- find_object(object_names, "uts\\.out([^_f]|_|$)|uts\\.out")
  sts_name <- find_object(object_names, "sts\\.out([^_f]|_|$)|sts\\.out")

  theta <- if (nzchar(theta_name)) get(theta_name) else NULL
  gamsig <- if (nzchar(gamsig_name)) get(gamsig_name) else NULL
  uts <- if (nzchar(uts_name)) get(uts_name) else NULL
  sts <- if (nzchar(sts_name)) get(sts_name) else NULL

  theta_rows <- list()
  top_rows <- list()
  if (is.list(theta)) {
    if (!is.null(theta$exps)) {
      theta_rows[[length(theta_rows) + 1L]] <- summarize_numeric(theta$exps, "theta.exps")
      top <- top_matrix_cells(theta$exps, "theta.exps", top_k = 50L)
      if (nrow(top)) top_rows[[length(top_rows) + 1L]] <- top
    }
    if (!is.null(theta$sm)) {
      theta_rows[[length(theta_rows) + 1L]] <- summarize_numeric(theta$sm, "theta.sm")
      top <- top_matrix_cells(theta$sm, "theta.sm", top_k = 50L)
      if (nrow(top)) top_rows[[length(top_rows) + 1L]] <- top
      utils::write.csv(state_block_summary(theta$sm), file.path(case_dir, "state_block_summary.csv"), row.names = FALSE)
    }
    if (!is.null(theta$sC)) {
      theta_rows[[length(theta_rows) + 1L]] <- summarize_numeric(theta$sC, "theta.sC")
    }
  }
  write_rows(file.path(case_dir, "theta_numeric_summary.csv"), theta_rows)
  write_rows(file.path(case_dir, "theta_top_coordinates.csv"), top_rows)

  gamsig_rows <- summarize_named_numeric_fields(gamsig, "gamsig", wanted = "sigma|sig|gam|theta|invb")
  write_rows(file.path(case_dir, "gamsig_numeric_summary.csv"), gamsig_rows)

  uts_rows <- summarize_named_numeric_fields(uts, "uts", wanted = "uts|inv|log|lambda|psi|chi|entrop")
  write_rows(file.path(case_dir, "uts_numeric_summary.csv"), uts_rows)

  sts_rows <- summarize_named_numeric_fields(sts, "sts", wanted = "sts|sig|mu|entrop")
  write_rows(file.path(case_dir, "sts_numeric_summary.csv"), sts_rows)

  pseudo_rows <- compute_pseudodata_summary(gamsig, sts, uts, "pseudodata")
  write_rows(file.path(case_dir, "pseudodata_numeric_summary.csv"), pseudo_rows)

  case_records[[length(case_records) + 1L]] <- data.frame(
    label = label,
    rdata_path = rdata_path,
    loaded_objects = paste(object_names, collapse = ";"),
    theta_object = theta_name,
    gamsig_object = gamsig_name,
    uts_object = uts_name,
    sts_object = sts_name,
    output_dir = normalizePath(case_dir, mustWork = FALSE),
    stringsAsFactors = FALSE
  )

  rm(list = object_names)
  rm(theta, gamsig, uts, sts)
  gc()
}

manifest <- do.call(rbind, case_records)
utils::write.csv(manifest, file.path(outdir, "saved_state_decomposition_manifest.csv"), row.names = FALSE)

readme <- c(
  "# HE2 AL-M-T0 Saved-State Decomposition",
  "",
  "This report was generated one retained RData file at a time.",
  "",
  "Files per case:",
  "",
  "- `theta_numeric_summary.csv`",
  "- `theta_top_coordinates.csv`",
  "- `state_block_summary.csv`",
  "- `gamsig_numeric_summary.csv`",
  "- `uts_numeric_summary.csv`",
  "- `sts_numeric_summary.csv`",
  "- `pseudodata_numeric_summary.csv`",
  "",
  "The script does not modify retained runs."
)
writeLines(readme, file.path(outdir, "README.md"))
message(sprintf("[decompose] wrote %d case summaries to %s", nrow(manifest), outdir))
