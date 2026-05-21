#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

out_dir <- file.path("reports", "exdqlm_transform_regression_forensics_20260521")
base_ref <- "44e2d60^"
target_ref <- "44e2d60"

while (length(args) > 0L) {
  key <- args[[1L]]
  if (key == "--out" && length(args) >= 2L) {
    out_dir <- args[[2L]]
    args <- args[-c(1L, 2L)]
  } else if (key == "--base" && length(args) >= 2L) {
    base_ref <- args[[2L]]
    args <- args[-c(1L, 2L)]
  } else if (key == "--target" && length(args) >= 2L) {
    target_ref <- args[[2L]]
    args <- args[-c(1L, 2L)]
  } else {
    stop(sprintf("Unknown or incomplete argument: %s", key), call. = FALSE)
  }
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

git_lines <- function(...) {
  out <- system2("git", c(...), stdout = TRUE, stderr = TRUE)
  status <- attr(out, "status")
  if (!is.null(status) && !identical(status, 0L)) {
    stop(sprintf("git command failed: git %s\n%s", paste(c(...), collapse = " "), paste(out, collapse = "\n")), call. = FALSE)
  }
  out
}

read_ref_file <- function(ref, path) {
  out <- system2("git", c("show", sprintf("%s:%s", ref, path)), stdout = TRUE, stderr = TRUE)
  status <- attr(out, "status")
  if (!is.null(status) && !identical(status, 0L)) return(character())
  out
}

find_pattern_rows <- function(lines, pattern, ref_label, path, description) {
  hits <- grep(pattern, lines, perl = TRUE)
  if (!length(hits)) {
    return(data.frame(
      ref = ref_label,
      file = path,
      line = NA_integer_,
      description = description,
      pattern = pattern,
      text = NA_character_
    ))
  }
  do.call(rbind, lapply(hits, function(i) {
    data.frame(
      ref = ref_label,
      file = path,
      line = as.integer(i),
      description = description,
      pattern = pattern,
      text = lines[[i]]
    )
  }))
}

watched_sites <- data.frame(
  file = c(
    "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r",
    "DISC_Optimal_Synth_Ranges_W_transfer_forecast.r",
    "R/disc_w/03_covariates_standardize.R",
    "R/unified/config.R",
    "R/unified/config.R",
    "R/unified/stages/stage_fit.R",
    "R/unified/stages/stage_post.R"
  ),
  pattern = c(
    "nws_forecast\\[,-1\\]\\s*<-\\s*log\\(",
    "glofas_forecast\\[,-1\\]\\s*<-\\s*log\\(",
    "^\\s*Y\\s*<-\\s*log\\(Y\\)",
    "analysis_scale_fit_internal\\s*=\\s*\"[^\"]+\"",
    "analysis_scale_post_internal\\s*=\\s*\"[^\"]+\"",
    "positive_required\\s*=\\s*(TRUE|FALSE)",
    "positive_required\\s*=\\s*(TRUE|FALSE)"
  ),
  description = c(
    "runner NWS forecast second log",
    "runner GloFAS forecast second log",
    "retrospective matrix second log",
    "fit analysis internal scale default",
    "post analysis internal scale default",
    "fit adapter positive guard",
    "post adapter positive guard"
  ),
  stringsAsFactors = FALSE
)

refs <- c(base_ref, target_ref, "HEAD")
manifest_rows <- list()
for (ref in refs) {
  for (i in seq_len(nrow(watched_sites))) {
    path <- watched_sites$file[[i]]
    lines <- if (identical(ref, "HEAD")) {
      if (file.exists(path)) readLines(path, warn = FALSE) else character()
    } else {
      read_ref_file(ref, path)
    }
    manifest_rows[[length(manifest_rows) + 1L]] <- find_pattern_rows(
      lines = lines,
      pattern = watched_sites$pattern[[i]],
      ref_label = ref,
      path = path,
      description = watched_sites$description[[i]]
    )
  }
}
transform_manifest <- do.call(rbind, manifest_rows)
write.csv(transform_manifest, file.path(out_dir, "transform_diff_manifest.csv"), row.names = FALSE)

current_config <- readLines("R/unified/config.R", warn = FALSE)
scale_patterns <- c(
  canonical_storage_scale = "canonical_storage_scale\\s*=\\s*\"[^\"]+\"",
  legacy_fit_input_scale = "legacy_fit_input_scale\\s*=\\s*\"[^\"]+\"",
  legacy_post_input_scale = "legacy_post_input_scale\\s*=\\s*\"[^\"]+\"",
  analysis_scale_fit_internal = "analysis_scale_fit_internal\\s*=\\s*\"[^\"]+\"",
  analysis_scale_post_internal = "analysis_scale_post_internal\\s*=\\s*\"[^\"]+\""
)
scale_contract <- do.call(rbind, lapply(names(scale_patterns), function(key) {
  hits <- grep(scale_patterns[[key]], current_config, perl = TRUE)
  value <- if (length(hits)) sub(".*\"([^\"]+)\".*", "\\1", current_config[[hits[[1L]]]]) else NA_character_
  data.frame(key = key, value = value, line = if (length(hits)) hits[[1L]] else NA_integer_)
}))
write.csv(scale_contract, file.path(out_dir, "active_scale_contract.csv"), row.names = FALSE)

raw_values <- c(0, 1e-6, 0.001, 0.1, 1, 10, 100, 1000, 10000)
near_zero <- data.frame(
  raw_cms = raw_values,
  log1p_cms = log1p(raw_values),
  log_log1p_cms = suppressWarnings(log(log1p(raw_values)))
)
near_zero$log1p_finite <- is.finite(near_zero$log1p_cms)
near_zero$log_log1p_finite <- is.finite(near_zero$log_log1p_cms)
near_zero$interpretation <- ifelse(
  near_zero$raw_cms == 0,
  "log_log1p undefined at exact zero",
  ifelse(near_zero$raw_cms < 0.1, "log_log1p finite but extreme negative", "finite comparator")
)
write.csv(near_zero, file.path(out_dir, "near_zero_scale_behavior.csv"), row.names = FALSE)

positive_values <- raw_values[raw_values > 0]
scale_magnitude <- data.frame(
  raw_cms = positive_values,
  log1p_cms = log1p(positive_values),
  log_log1p_cms = log(log1p(positive_values))
)
scale_magnitude$ratio_log1p_to_abs_loglog1p <- scale_magnitude$log1p_cms / abs(scale_magnitude$log_log1p_cms)
write.csv(scale_magnitude, file.path(out_dir, "scale_magnitude_comparison.csv"), row.names = FALSE)

commit_summary <- data.frame(
  ref = c(base_ref, target_ref, "HEAD"),
  commit = vapply(c(base_ref, target_ref, "HEAD"), function(ref) git_lines("rev-parse", ref)[[1L]], character(1)),
  subject = vapply(c(base_ref, target_ref, "HEAD"), function(ref) git_lines("show", "-s", "--format=%s", ref)[[1L]], character(1))
)
write.csv(commit_summary, file.path(out_dir, "commit_summary.csv"), row.names = FALSE)

readme <- c(
  "# exDQLM transform regression forensics",
  "",
  "Generated by `repro/audits/exdqlm_transform_regression_forensics.R`.",
  "",
  "This report treats `log1p_cms` as the active repair target. The old",
  "`log_log1p_cms` behavior is included only as a diagnostic comparator.",
  "",
  "## Inputs",
  "",
  sprintf("- base ref: `%s`", base_ref),
  sprintf("- target ref: `%s`", target_ref),
  "- current ref: `HEAD`",
  "",
  "## Files",
  "",
  "- `commit_summary.csv`: commit ids and subjects for refs.",
  "- `transform_diff_manifest.csv`: watched transform and guard sites across refs.",
  "- `active_scale_contract.csv`: current scale-contract defaults.",
  "- `near_zero_scale_behavior.csv`: zero and near-zero scale behavior.",
  "- `scale_magnitude_comparison.csv`: positive-flow scale compression comparison.",
  "",
  "## Interpretation",
  "",
  "`log(log1p(cms))` is undefined at exact zero and very negative near zero.",
  "That is why this report must not be read as recommending a transform revert.",
  "The purpose is to quantify what changed and to guide `log1p_cms` stabilization."
)
writeLines(readme, file.path(out_dir, "README.md"))

cat(sprintf("Transform forensics written to %s\n", normalizePath(out_dir, mustWork = FALSE)))
