#!/usr/bin/env Rscript
# Read-only audit of retained predictions against original saved scores.
# No fitting, forecast regeneration, or production diagnostic implementation.
# All audit outputs must go to a caller-specified NEW directory under /tmp.

args <- commandArgs(trailingOnly = TRUE)
if (!length(args)) stop("Both --project-root and --output-dir are required.")
if (length(args) %% 2L != 0L) stop("Arguments must be --name value pairs.")
allowed <- c("--project-root", "--output-dir")
keys <- args[seq.int(1L, length(args), by = 2L)]
if (!length(args) || any(!keys %in% allowed) || anyDuplicated(keys)) {
  stop("Usage: Rscript --vanilla no_refit_replay_audit.R --project-root PATH --output-dir /tmp/NEW_DIRECTORY")
}
opts <- setNames(args[seq.int(2L, length(args), by = 2L)], keys)
if (!all(allowed %in% names(opts))) stop("Both --project-root and --output-dir are required.")
project <- normalizePath(opts[["--project-root"]], mustWork = TRUE)
requested_output <- opts[["--output-dir"]]
if (file.exists(requested_output) || dir.exists(requested_output)) {
  stop("Output directory already exists; choose a fresh /tmp directory.")
}
parent <- normalizePath(dirname(requested_output), mustWork = TRUE)
tmp_root <- normalizePath("/tmp", mustWork = TRUE)
if (!(identical(parent, tmp_root) || startsWith(parent, paste0(tmp_root, "/")))) {
  stop("Audit output directory must be under /tmp.")
}
output <- file.path(parent, basename(requested_output))
if (!grepl("^[A-Za-z0-9_.-]+$", basename(output)) || basename(output) %in% c(".", "..")) {
  stop("Use a simple new directory name under /tmp.")
}
if (!requireNamespace("digest", quietly = TRUE) || !requireNamespace("jsonlite", quietly = TRUE)) {
  stop("Installed packages digest and jsonlite are required; this audit never installs packages.")
}
sha256 <- function(path) digest::digest(file = path, algo = "sha256")
assert <- function(condition, message) if (!isTRUE(condition)) stop(message, call. = FALSE)
read_csv <- function(path) utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)

article <- file.path(project, "Evironmetrics---REVISED-DOC-Corrected-2")
manifest_path <- file.path(article, "artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv")
truth_path <- file.path(article, "artifacts/comment2_revision/external_baselines/inputs/usgs_verification.csv")
scorer_path <- file.path(project, "R/environmetrics/02_helpers_core.R")
input_hashes <- c(publication_manifest = sha256(manifest_path), verification = sha256(truth_path), scorer = sha256(scorer_path))
m <- read_csv(manifest_path)
truth <- read_csv(truth_path)
assert(nrow(m) == 45L && !anyDuplicated(paste(m$cutoff, m$manuscript_label)), "Expected 45 unique publication cases.")
assert(nrow(truth) == 140L && !anyDuplicated(truth$date) && all(is.finite(truth$Y)), "Unexpected frozen verification schema.")

# Evaluate only the two existing pure scorer definitions, not the complete module.
scorer_env <- new.env(parent = baseenv())
definitions <- c("check_loss_fn", "post_crps_quantile_approx")
found <- character(0)
for (expression in parse(scorer_path)) {
  if (is.call(expression) && identical(expression[[1L]], as.name("<-")) &&
      is.symbol(expression[[2L]]) && as.character(expression[[2L]]) %in% definitions) {
    assert(is.call(expression[[3L]]) && identical(expression[[3L]][[1L]], as.name("function")), "Scorer entry is not a function definition.")
    eval(expression, scorer_env)
    found <- c(found, as.character(expression[[2L]]))
  }
}
assert(setequal(found, definitions) && length(found) == 2L, "Could not isolate the existing scorer definitions.")

rows <- vector("list", nrow(m))
quantile_checks <- list()
for (i in seq_len(nrow(m))) {
  r <- m[i, ]
  root <- if (!is.na(r$artifact_run_root) && nzchar(r$artifact_run_root)) r$artifact_run_root else r$run_root
  files <- list.files(file.path(root, "post/cache"), full.names = TRUE)
  files <- files[grepl("(^synth_univar_forecast_log1p\\.rds$|synth_multivar_forecast_log1p\\.rds$|^y_reps_ndlm_log1p\\.rds$)", basename(files))]
  assert(length(files) == 1L, paste("Expected one compact prediction cache for", r$run_id))
  prediction_path <- files[[1L]]
  assert(file.info(prediction_path)$size < 500000, "Prediction file exceeds bounded audit size.")
  prediction_hash <- sha256(prediction_path)
  prediction <- readRDS(prediction_path)
  assert(is.matrix(prediction) && is.numeric(prediction) && nrow(prediction) > 1L &&
         ncol(prediction) == 28L && all(is.finite(prediction)), "Prediction matrix schema failed.")

  original_summary <- read_csv(r$score_source)
  selected_summary <- original_summary[abs(original_summary$mean_crps - r$crps_exact) < 1e-12, , drop = FALSE]
  assert(nrow(selected_summary) == 1L, "Could not uniquely identify the original score model.")
  score_path <- sub("crps_forecast_summary", "crps_forecast_per_time", r$score_source, fixed = TRUE)
  score_hash <- sha256(score_path)
  original_scores <- read_csv(score_path)
  original_scores <- original_scores[original_scores$model_id == selected_summary$model_id, , drop = FALSE]
  original_scores <- original_scores[order(original_scores$lead_day), , drop = FALSE]
  dates <- as.character(as.Date(as.character(r$cutoff), "%Y%m%d") + seq_len(28L))
  assert(nrow(original_scores) == 28L && all(original_scores$lead_day == seq_len(28L)) &&
         all(original_scores$forecast_date == dates), "Original lead/date identity failed.")
  observed <- truth$Y[match(dates, truth$date)]
  assert(length(observed) == 28L && all(is.finite(observed)), "Missing verification outcomes.")
  replay <- scorer_env$post_crps_quantile_approx(observed, prediction, context = "read_only_legacy_replay")
  error <- max(abs(replay$crps - original_scores$crps))
  assert(error <= 1e-12, paste("Original-score replay failed for", r$run_id))
  assert(identical(prediction_hash, sha256(prediction_path)) && identical(score_hash, sha256(score_path)), "Audit source changed during reading.")

  rows[[i]] <- list(cutoff = as.character(r$cutoff), model = r$manuscript_label,
    run_id = r$run_id, model_id = selected_summary$model_id,
    prediction_file = normalizePath(prediction_path), prediction_bytes = unname(file.info(prediction_path)$size),
    prediction_sha256 = prediction_hash, shape = unname(dim(prediction)),
    date_min = min(dates), date_max = max(dates), score_scale = selected_summary$score_scale,
    score_file = normalizePath(score_path), score_sha256 = score_hash,
    max_per_time_abs_error = error, mean_score_abs_error = abs(mean(replay$crps) - r$crps_exact),
    finite = all(is.finite(prediction)), minimum = min(prediction), maximum = max(prediction),
    negative_values = sum(prediction < 0), above_exp_limit = sum(prediction > log(.Machine$double.xmax)))

  if (r$manuscript_label == "exAL-M-T1") {
    exported_path <- file.path(article, "artifacts/five_cutoff_main_model_synthesis", paste0(r$cutoff, "_exal_m_t1"), "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv")
    exported <- read_csv(exported_path)
    exported <- exported[exported$segment == "forecast", ]
    assert(nrow(exported) == 28L && all(exported$date == dates), "Reference quantile dates do not match.")
    q <- apply(prediction, 2L, stats::quantile, probs = c(.05, .2, .35, .5, .65, .8, .95), type = 8L, names = FALSE)
    q_error <- max(abs(t(q) - as.matrix(exported[, c("q05", "q20", "q35", "q50", "q65", "q80", "q95")])))
    assert(q_error < 1e-12, "Saved reference quantile export does not match type-8 prediction quantiles.")
    quantile_checks[[length(quantile_checks) + 1L]] <- list(cutoff = as.character(r$cutoff), quantile_type = 8L,
      quantile_export = normalizePath(exported_path), quantile_export_sha256 = sha256(exported_path), max_abs_error = q_error)
  }
}

# Finite-example algebra checks only, not a new production scoring pipeline.
examples <- list(list(x = c(0, 2), y = 0), list(x = c(-1, -1, 3), y = 2),
                 list(x = c(4, 4, 4, 4), y = -2), list(x = c(-3, 0, 2, 9), y = 1))
algebra <- lapply(examples, function(z) {
  x <- sort(z$x); y <- z$y; n <- length(x); tau <- seq_len(n) / (n + 1)
  legacy <- 2 * mean((y - x) * (tau - as.numeric(y - x < 0)))
  D <- sum(abs(outer(x, x, "-"))) / 2
  ecdf <- mean(abs(x - y)) - D / n^2
  fair <- mean(abs(x - y)) - D / (n * (n - 1))
  list(x = x, y = y, legacy = legacy, ecdf = ecdf, fair = fair,
       legacy_identity_error = abs(legacy - ecdf - D / (n^2 * (n + 1))),
       fair_difference_error = abs(ecdf - fair - D / (n^2 * (n - 1))))
})
assert(all(vapply(algebra, function(z) z$legacy_identity_error < 1e-13 && z$fair_difference_error < 1e-13, logical(1))), "Finite CRPS identity checks failed.")
assert(identical(input_hashes, c(publication_manifest = sha256(manifest_path), verification = sha256(truth_path), scorer = sha256(scorer_path))), "Core audit inputs changed.")

result <- list(description = "Read-only forecast-cache authority and original-score identity audit; no fitting or new production metrics",
  invocation = commandArgs(), publication_manifest = normalizePath(manifest_path),
  publication_manifest_sha256 = input_hashes[["publication_manifest"]],
  scorer_sha256 = input_hashes[["scorer"]], verification_sha256 = input_hashes[["verification"]],
  n_runs = length(rows), n_forecast_cases = 28L * length(rows),
  prediction_bytes_total = sum(vapply(rows, function(z) z$prediction_bytes, numeric(1))),
  max_per_time_abs_error = max(vapply(rows, function(z) z$max_per_time_abs_error, numeric(1))),
  rows = rows, reference_quantile_checks = quantile_checks, finite_algebra_examples = algebra)
assert(dir.create(output, recursive = FALSE), "Could not create fresh audit output directory.")
jsonlite::write_json(result, file.path(output, "scoring_artifact_inventory.json"), pretty = TRUE, auto_unbox = TRUE, digits = 17L)
writeLines(capture.output(utils::sessionInfo()), file.path(output, "session_info.txt"))
cat(sprintf("Passed: %d runs, %d daily scores, max absolute difference %.17g; output %s\n", result$n_runs, result$n_forecast_cases, result$max_per_time_abs_error, output))
