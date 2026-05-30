source(testthat::test_path("..", "..", "R", "unified", "config.R"))
source(testthat::test_path("..", "..", "R", "unified", "stages", "stage_report.R"))

test_that("stage report discovers exdqlm multivar quantiles after RData cleanup", {
  testthat::skip_if_not_installed("jsonlite")

  run_root <- tempfile("stage_report_quantiles_")
  dir.create(file.path(run_root, "fit", "exdqlm_multivar", "keep", "q=05", "logs"), recursive = TRUE)
  dir.create(file.path(run_root, "fit", "exdqlm_multivar", "keep", "q=20", "logs"), recursive = TRUE)
  dir.create(file.path(run_root, "fit", "exdqlm_multivar", "keep", "q=95", "logs"), recursive = TRUE)
  on.exit(unlink(run_root, recursive = TRUE, force = TRUE), add = TRUE)

  cfg <- unified_config_defaults()
  cfg$run$run_id <- "report_quantile_discovery"
  cfg$run$repro_mode <- "strict"
  cfg$run$seed <- 20221225L
  cfg$models$run_exdqlm_multivar <- TRUE
  cfg$models$exdqlm_multivar$forecast_transfer_mode <- "keep"
  cfg$fit$quantiles <- c(0.05, 0.20, 0.95)

  manifest <- list(
    inputs = list(),
    artifacts = list(),
    git = list(commit = "testcommit"),
    validation = list(status = "pass", compare_report_path = NULL),
    change_approval = list(status = "pending"),
    deterministic_climate = list(enabled = FALSE),
    rdata_cleanup = list(after_post = list(before = 3L, removed = 3L, remaining = 0L))
  )

  unified_stage_report(cfg, run_root = run_root, repo_root = getwd(), manifest = manifest)

  summary <- jsonlite::read_json(file.path(run_root, "report", "summary.json"), simplifyVector = TRUE)
  found <- summary$report$families$exdqlm_multivar$quantiles_found
  found_by_mode <- summary$report$families$exdqlm_multivar$quantiles_found_by_mode$keep
  testthat::expect_equal(as.integer(found), c(5L, 20L, 95L))
  testthat::expect_equal(as.integer(found_by_mode), c(5L, 20L, 95L))
  testthat::expect_equal(summary$rdata_cleanup$after_post$remaining, 0L)

  summary_md <- readLines(file.path(run_root, "report", "summary.md"), warn = FALSE)
  testthat::expect_true(any(grepl("families.exdqlm_multivar.quantiles_found: `5, 20, 95`", summary_md, fixed = TRUE)))
  testthat::expect_true(any(grepl("rdata_cleanup.after_post.remaining: `0`", summary_md, fixed = TRUE)))
})
