#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(gdpc))
suppressPackageStartupMessages(library(jsonlite))

parse_args <- function(args) {
  out <- list(
    input_csv = NULL,
    output_csv = NULL,
    output_alpha_csv = NULL,
    output_beta_csv = NULL,
    output_initial_f_csv = NULL,
    output_metadata_json = NULL,
    component_name = "GDPC1",
    k = 3L,
    tol = 1e-4,
    niter_max = 500L,
    crit = "LOO",
    anchor_index = NULL,
    require_convergence = TRUE
  )

  i <- 1L
  while (i <= length(args)) {
    arg <- args[[i]]
    if (arg == "--input-csv") {
      i <- i + 1L; out$input_csv <- args[[i]]
    } else if (arg == "--output-csv") {
      i <- i + 1L; out$output_csv <- args[[i]]
    } else if (arg == "--output-alpha-csv") {
      i <- i + 1L; out$output_alpha_csv <- args[[i]]
    } else if (arg == "--output-beta-csv") {
      i <- i + 1L; out$output_beta_csv <- args[[i]]
    } else if (arg == "--output-initial-f-csv") {
      i <- i + 1L; out$output_initial_f_csv <- args[[i]]
    } else if (arg == "--output-metadata-json") {
      i <- i + 1L; out$output_metadata_json <- args[[i]]
    } else if (arg == "--component-name") {
      i <- i + 1L; out$component_name <- args[[i]]
    } else if (arg == "--k") {
      i <- i + 1L; out$k <- as.integer(args[[i]])
    } else if (arg == "--tol") {
      i <- i + 1L; out$tol <- as.numeric(args[[i]])
    } else if (arg == "--niter-max") {
      i <- i + 1L; out$niter_max <- as.integer(args[[i]])
    } else if (arg == "--crit") {
      i <- i + 1L; out$crit <- args[[i]]
    } else if (arg == "--anchor-index") {
      i <- i + 1L; out$anchor_index <- args[[i]]
    } else if (arg == "--require-convergence") {
      i <- i + 1L; out$require_convergence <- tolower(args[[i]]) %in% c("1", "true", "t", "yes", "y")
    } else {
      stop(sprintf("Unknown argument: %s", arg), call. = FALSE)
    }
    i <- i + 1L
  }

  required <- c("input_csv", "output_csv", "output_alpha_csv", "output_beta_csv", "output_initial_f_csv", "output_metadata_json", "anchor_index")
  missing <- required[vapply(required, function(name) is.null(out[[name]]) || !nzchar(out[[name]]), logical(1))]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  out
}

ensure_parent <- function(path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
}

args <- parse_args(commandArgs(trailingOnly = TRUE))

df <- read.csv(args$input_csv, check.names = FALSE)
if (!("time" %in% names(df))) {
  stop("Expected 'time' column in standardized daily matrix.", call. = FALSE)
}
series_names <- setdiff(names(df), "time")
if (!(args$anchor_index %in% series_names)) {
  stop(sprintf("Anchor index '%s' not found in input matrix.", args$anchor_index), call. = FALSE)
}

time_values <- as.character(df$time)
X <- as.matrix(df[series_names])
storage.mode(X) <- "double"

t0 <- Sys.time()
fit <- gdpc(
  X,
  k = as.numeric(args$k),
  tol = as.numeric(args$tol),
  niter_max = as.numeric(args$niter_max),
  crit = args$crit
)
t1 <- Sys.time()

if (isTRUE(args$require_convergence) && !isTRUE(fit$conv)) {
  stop("gdpc() did not converge under the required convergence contract.", call. = FALSE)
}

factor_values <- as.numeric(fit$f)
anchor_series <- as.numeric(df[[args$anchor_index]])
anchor_corr_before <- suppressWarnings(cor(factor_values, anchor_series, use = "complete.obs"))
sign_flip <- is.finite(anchor_corr_before) && anchor_corr_before < 0

if (isTRUE(sign_flip)) {
  factor_values <- -factor_values
  fit$initial_f <- -fit$initial_f
  fit$beta <- -fit$beta
}

anchor_corr_after <- suppressWarnings(cor(factor_values, anchor_series, use = "complete.obs"))

factor_df <- data.frame(time = time_values, value = factor_values, stringsAsFactors = FALSE)
names(factor_df)[2] <- args$component_name

alpha_df <- data.frame(series = series_names, alpha = as.numeric(fit$alpha), stringsAsFactors = FALSE)

beta_df <- as.data.frame(fit$beta, stringsAsFactors = FALSE)
names(beta_df) <- paste0("lag_", 0:(ncol(beta_df) - 1L))
beta_df <- cbind(series = series_names, beta_df, stringsAsFactors = FALSE)

initial_offsets <- seq.int(from = -args$k + 1L, to = 0L, by = 1L)
initial_f_df <- data.frame(initial_offset = initial_offsets, value = as.numeric(fit$initial_f), stringsAsFactors = FALSE)

ensure_parent(args$output_csv)
ensure_parent(args$output_alpha_csv)
ensure_parent(args$output_beta_csv)
ensure_parent(args$output_initial_f_csv)
ensure_parent(args$output_metadata_json)

write.csv(factor_df, args$output_csv, row.names = FALSE, quote = TRUE)
write.csv(alpha_df, args$output_alpha_csv, row.names = FALSE, quote = TRUE)
write.csv(beta_df, args$output_beta_csv, row.names = FALSE, quote = TRUE)
write.csv(initial_f_df, args$output_initial_f_csv, row.names = FALSE, quote = TRUE)

metadata <- list(
  generated_at_utc = format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ"),
  input_csv = normalizePath(args$input_csv, winslash = "/", mustWork = FALSE),
  output_csv = normalizePath(args$output_csv, winslash = "/", mustWork = FALSE),
  component_name = args$component_name,
  rows = nrow(df),
  series_count = length(series_names),
  time_start = time_values[[1]],
  time_end = time_values[[length(time_values)]],
  gdpc = list(
    package_version = as.character(packageVersion("gdpc")),
    k = as.integer(args$k),
    tol = as.numeric(args$tol),
    niter_max = as.integer(args$niter_max),
    crit_name = args$crit,
    conv = isTRUE(fit$conv),
    niter = as.integer(fit$niter),
    mse = as.numeric(fit$mse),
    expart = as.numeric(fit$expart),
    criterion_value = as.numeric(fit$crit)
  ),
  sign_rule = list(
    method = "positive_correlation",
    anchor_index = args$anchor_index,
    anchor_correlation_before = as.numeric(anchor_corr_before),
    anchor_correlation_after = as.numeric(anchor_corr_after),
    sign_flipped = isTRUE(sign_flip)
  ),
  factor_summary = list(
    mean = as.numeric(mean(factor_values)),
    sd = as.numeric(sd(factor_values)),
    min = as.numeric(min(factor_values)),
    max = as.numeric(max(factor_values))
  ),
  runtime = list(
    elapsed_seconds = as.numeric(difftime(t1, t0, units = "secs"))
  )
)

writeLines(toJSON(metadata, pretty = TRUE, auto_unbox = TRUE), args$output_metadata_json)

cat(sprintf("Wrote %s\n", args$output_csv))
cat(sprintf("Wrote %s\n", args$output_metadata_json))
