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

args <- parse_args(commandArgs(trailingOnly = TRUE))
project_root <- normalizePath(getwd(), mustWork = FALSE)
helper_path <- file.path(project_root, "R", "unified", "post_publication_figures.R")
if (!file.exists(helper_path)) {
  stop(sprintf("Missing helper file: %s", helper_path), call. = FALSE)
}
source(helper_path)

runs_root <- args$runs_root %||% ""
run_dir <- args$run_dir %||% ""
style_config <- args$style_config %||% file.path(project_root, "config", "post_publication_figures.yaml")
rewrite_canonical <- !identical(as.character(args$rewrite_canonical %||% "TRUE"), "FALSE")
export_pdf <- !identical(as.character(args$export_pdf %||% "TRUE"), "FALSE")
fail_fast <- !identical(as.character(args$fail_fast %||% "TRUE"), "FALSE")

if (!nzchar(runs_root) && !nzchar(run_dir)) {
  stop("Provide --runs-root or --run-dir", call. = FALSE)
}

manifests <- character(0)
if (nzchar(run_dir)) {
  manifests <- file.path(normalizePath(run_dir, mustWork = TRUE), "figure_manifest.csv")
} else {
  runs_root <- normalizePath(runs_root, mustWork = TRUE)
  manifests <- list.files(runs_root, pattern = "^figure_manifest\\.csv$", recursive = TRUE, full.names = TRUE)
}
manifests <- manifests[file.exists(manifests)]
if (length(manifests) == 0L) {
  stop("No figure_manifest.csv files found.", call. = FALSE)
}

cat(sprintf("FOUND manifests=%d\n", length(manifests)))
results <- vector("list", length(manifests))
for (i in seq_along(manifests)) {
  manifest_path <- manifests[[i]]
  outputs_dir <- dirname(manifest_path)
  run_id <- basename(outputs_dir)
  cat(sprintf("[%d/%d] %s\n", i, length(manifests), outputs_dir))
  results[[i]] <- tryCatch(
    unified_render_publication_figures(
      outputs_dir = outputs_dir,
      run_id = run_id,
      project_root = project_root,
      enabled = TRUE,
      rewrite_canonical_png = rewrite_canonical,
      export_pdf = export_pdf,
      fail_fast = fail_fast,
      style_config_path = style_config
    ),
    error = function(e) {
      if (isTRUE(fail_fast)) stop(e)
      list(status = FALSE, rendered = 0L, skipped = 0L, failures = conditionMessage(e), outputs_dir = outputs_dir)
    }
  )
}

rendered <- sum(vapply(results, function(x) as.integer(x$rendered %||% 0L), integer(1)))
skipped <- sum(vapply(results, function(x) as.integer(x$skipped %||% 0L), integer(1)))
fails <- unlist(lapply(results, function(x) x$failures %||% character(0)), use.names = FALSE)
cat(sprintf("DONE rendered=%d skipped=%d failures=%d\n", rendered, skipped, length(fails)))
if (length(fails) > 0L) {
  cat(paste(fails, collapse = "\n"), "\n")
  quit(status = 1L)
}
