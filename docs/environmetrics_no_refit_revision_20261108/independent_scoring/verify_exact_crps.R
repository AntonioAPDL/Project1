#!/usr/bin/env Rscript
# Independent verification: no production helpers are sourced or called.
# Reads frozen forecast inputs and compares published derived score outputs.
# No fitting, optimization, random draws, or input writes.
args <- commandArgs(trailingOnly = TRUE)
if (!length(args) || length(args) %% 2L) stop("Use --bundle-root PATH --output-dir NEW_DIRECTORY")
keys <- args[seq.int(1L, length(args), by = 2L)]
if (anyDuplicated(keys) || !setequal(keys, c("--bundle-root", "--output-dir"))) stop("Unexpected CLI arguments")
opt <- setNames(args[seq.int(2L, length(args), by = 2L)], keys)
root <- normalizePath(opt[["--bundle-root"]], mustWork = TRUE)
output <- opt[["--output-dir"]]
if (file.exists(output) || !dir.exists(dirname(output))) stop("Choose a new output directory with an existing parent")
for (p in c("jsonlite", "digest", "scoringRules")) if (!requireNamespace(p, quietly = TRUE)) stop(paste("Required installed package:", p))
Sys.setenv(OPENBLAS_NUM_THREADS = "1", OMP_NUM_THREADS = "1", MKL_NUM_THREADS = "1")
assert <- function(ok, message) if (!isTRUE(ok)) stop(message, call. = FALSE)
sha <- function(path) digest::digest(file = path, algo = "sha256")
read_csv <- function(path) utils::read.csv(path, check.names = FALSE, stringsAsFactors = FALSE)
safe <- function(rel) {
  assert(length(rel) == 1L && !grepl("^/|(^|/)\\.\\.(/|$)", rel), "Unsafe snapshot path")
  path <- normalizePath(file.path(root, rel), mustWork = TRUE)
  assert(startsWith(path, paste0(root, "/")), "Snapshot escapes bundle")
  path
}
close_check <- function(a, b, scale) {
  atol <- if (scale == "log1p_cms") 1e-12 else 1e-10
  error <- abs(a - b)
  size <- pmax(abs(a), abs(b))
  limit <- atol + 1e-12 * size
  relative <- ifelse(size == 0, 0, error / size)
  assert(all(is.finite(a)) && all(is.finite(b)) && all(error <= limit), paste("Independent score disagreement on", scale))
  data.frame(absolute_error = error, relative_error = relative, tolerance = limit,
             tolerance_fraction = error / limit)
}
manifest_path <- file.path(root, "inputs/manifest.json")
manifest <- jsonlite::fromJSON(manifest_path, simplifyVector = FALSE)
snapshot_paths <- vapply(manifest$files, function(z) safe(z$input_snapshot_relpath), character(1))
expected_hashes <- vapply(manifest$files, `[[`, character(1), "sha256")
before <- vapply(snapshot_paths, sha, character(1))
assert(identical(unname(before), unname(expected_hashes)), "Frozen input hash mismatch")
result_path <- file.path(root, "results/scores_per_case.csv")
fixed_paths <- c(snapshot_paths, manifest_path, result_path)
fixed_before <- vapply(fixed_paths, sha, character(1))
registry <- read_csv(safe(manifest$representations))
truth <- read_csv(safe(manifest$observations))
scores <- read_csv(result_path)
score_keys <- paste(scores$representation_id, scores$target_date, scores$score_scale, sep = "|")
assert(nrow(registry) == 70L && nrow(scores) == 3720L && !anyDuplicated(score_keys), "Wrong score/representation counts")
random_before_exists <- exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
random_before <- if (random_before_exists) digest::digest(get(".Random.seed", envir = .GlobalEnv), algo = "sha256") else NULL
clock <- proc.time()
checks <- list(); pairwise <- list()
for (i in seq_len(nrow(registry))) {
  r <- registry[i, ]
  dates <- as.character(as.Date(r$origin_date) + seq_len(r$available_leads))
  path <- safe(r$input_snapshot_relpath)
  # These readers intentionally do not call the production reader.
  if (r$reader_kind == "matrix_rds") {
    matrix_log <- readRDS(path)
  } else if (r$reader_kind == "raw_csv") {
    raw <- read_csv(path)
    assert(identical(raw$target_date, dates), "Raw verification date mismatch")
    matrix_log <- t(log1p(as.matrix(raw[, grepl("^member_", names(raw)), drop = FALSE])))
  } else {
    assert(r$reader_kind == "external_list_rds", "Unexpected frozen representation reader")
    object <- readRDS(path)
    assert(identical(object$dates, dates), "External verification date mismatch")
    matrix_log <- object$predictions[[r$object_key]]
  }
  assert(is.matrix(matrix_log) && identical(dim(matrix_log), as.integer(c(r$n_values_nominal, r$available_leads))) &&
           all(is.finite(matrix_log)), "Frozen prediction shape/finite check failed")
  index <- match(dates, truth$date)
  assert(!anyNA(index), "Missing original frozen target")
  eligible <- !r$model_id %in% c("CLIM-SEASONAL", "EMOS-GLOFAS", "PERSISTENCE")
  for (scale in c("log1p_cms", "discharge_cms")) {
    values <- if (scale == "discharge_cms") expm1(matrix_log) else matrix_log
    observed <- if (scale == "discharge_cms") truth$discharge_cms[index] else truth$Y[index]
    assert(all(is.finite(values)) && all(is.finite(observed)), "Nonfinite independent input")
    match_index <- match(paste(r$representation_id, dates, scale, sep = "|"), score_keys)
    assert(!anyNA(match_index), "Derived case identity missing")
    target <- scores[match_index, ]
    assert(identical(as.integer(target$lead_day), seq_len(r$available_leads)), "Derived lead identity mismatch")
    # scoringRules EDF uses the exact empirical-distribution CRPS, implemented
    # via midpoint empirical quantile weights. This differs independently from
    # the production pairwise sorted-spread calculation.
    reference <- as.numeric(scoringRules::crps_sample(y = observed, dat = t(values), method = "edf", show_messages = FALSE))
    error <- close_check(target$exact_ecdf_crps, reference, scale)
    checks[[length(checks) + 1L]] <- data.frame(model_id = r$model_id, representation_id = r$representation_id,
      origin_date = r$origin_date, lead_day = seq_len(r$available_leads), target_date = dates,
      score_scale = scale, production_score = target$exact_ecdf_crps, independent_score = reference,
      error, stringsAsFactors = FALSE)
    assert(identical(is.na(target$iid_adjusted_crps), rep(!eligible, nrow(target))), "Adjusted-score applicability differs")
    # Prespecified real-data subset: first origin, lead1, every eligible method,
    # both scales (22 cases). Quadratic pair matrices are bounded to one lead
    # and occur only in this independent verification, never in production.
    if (eligible && r$origin_date == "2021-01-23") {
      x <- values[, 1L]; y <- observed[[1L]]; n <- length(x)
      direct <- mean(abs(x - y)) - sum(abs(outer(x, x, `-`))) / (2 * n * (n - 1))
      e <- close_check(target$iid_adjusted_crps[[1L]], direct, scale)
      pairwise[[length(pairwise) + 1L]] <- data.frame(model_id = r$model_id, origin_date = r$origin_date,
        lead_day = 1L, score_scale = scale, n_values = n,
        production_score = target$iid_adjusted_crps[[1L]], independent_pairwise_score = direct, e, stringsAsFactors = FALSE)
    }
  }
}
all_checks <- do.call(rbind, checks)
all_pairs <- do.call(rbind, pairwise)
assert(nrow(all_checks) == 3720L && nrow(all_pairs) == 22L, "Independent case count mismatch")
after <- vapply(fixed_paths, sha, character(1))
assert(identical(fixed_before, after), "Input/result changed during independent audit")
assert(identical(random_before_exists, exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)), "Audit changed RNG state")
if (random_before_exists) assert(identical(random_before, digest::digest(get(".Random.seed", envir = .GlobalEnv), algo = "sha256")), "Audit consumed random values")
summary_errors <- function(d) {
  lapply(split(d, d$score_scale), function(z) list(cases = nrow(z),
    max_absolute_error = max(z$absolute_error), max_relative_error = max(z$relative_error),
    max_tolerance_fraction = max(z$tolerance_fraction)))
}
edf <- get("crps_edf", asNamespace("scoringRules"))
script_path <- normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)), mustWork = TRUE)
report <- list(status = "PASSED", script_sha256 = sha(script_path),
  package = list(name = "scoringRules", version = as.character(utils::packageVersion("scoringRules")), method = "edf",
    public_arguments = names(formals(scoringRules::crps_sample)),
    namespace_function = "crps_edf", implementation_body_sha256 = digest::digest(body(edf), algo = "sha256"),
    implementation_description = "Exact EDF CRPS through sorted values and midpoint quantile weights (i-.5)/m; no kernel smoothing"),
  exact_ecdf_cases = 3720L, ecdf_errors = summary_errors(all_checks),
  direct_adjusted_pairwise_cases = 22L, adjusted_errors = summary_errors(all_pairs),
  tolerances = list(log1p_cms = list(absolute = 1e-12, relative = 1e-12), discharge_cms = list(absolute = 1e-10, relative = 1e-12),
    criterion = "abs(a-b)<=atol+rtol*max(abs(a),abs(b))"),
  frozen_files_checked = length(fixed_paths), changed_files = 0L,
  input_hashes_unchanged = TRUE, random_state_unchanged = TRUE,
  no_fit_or_forecast_generation = TRUE, production_helpers_called = FALSE,
  input_manifest_sha256 = sha(manifest_path), derived_score_file_sha256 = sha(result_path),
  elapsed_seconds = unname((proc.time() - clock)[["elapsed"]]))
assert(dir.create(output), "Cannot create independent audit output directory")
jsonlite::write_json(report, file.path(output, "report.json"), pretty = TRUE, auto_unbox = TRUE, digits = 17L)
write_csv <- function(d, path) {
  for (k in names(d)) if (is.double(d[[k]])) d[[k]] <- sprintf("%.17g", d[[k]])
  utils::write.csv(d, path, row.names = FALSE)
}
write_csv(all_checks, file.path(output, "all_case_crosschecks.csv"))
write_csv(all_pairs, file.path(output, "direct_pairwise_crosschecks.csv"))
write_csv(data.frame(path = fixed_paths, sha256_before = unname(fixed_before), sha256_after = unname(after)), file.path(output, "unchanged_input_hashes.csv"))
writeLines(capture.output(utils::sessionInfo()), file.path(output, "session_info.txt"))
cat(jsonlite::toJSON(report, pretty = TRUE, auto_unbox = TRUE, digits = 17L), "\n")
