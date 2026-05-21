`%||%` <- function(x, y) if (is.null(x)) y else x

testthat::test_that("runtime stability audit reports E log u totals and per-time values separately", {
  script <- testthat::test_path(
    "..",
    "..",
    "repro",
    "audits",
    "exdqlm_keep_runtime_stability_audit.R"
  )
  testthat::skip_if_not(file.exists(script))

  tmp <- tempdir()
  rdata_path <- file.path(tmp, "DISC_variables_50_exAL_synth_DISC.RData")
  out_dir <- file.path(tmp, "runtime_audit")

  env <- new.env(parent = emptyenv())
  env$new.uts.out_50_exAL_synth_DISC <- list(
    E.uts = matrix(1, nrow = 2, ncol = 3),
    E.inv.uts = matrix(2, nrow = 2, ncol = 3),
    E.log.uts = matrix(c(-3, 6), nrow = 2),
    tot.entrop = matrix(c(1, 2), nrow = 2)
  )
  env$new.uts_ens.out_50_exAL_synth_DISC <- list(
    E.uts = list(matrix(1, nrow = 4, ncol = 2)),
    E.inv.uts = list(matrix(2, nrow = 4, ncol = 2)),
    E.log.uts = list(matrix(c(8, 12), nrow = 1)),
    tot.entrop = list(matrix(c(3, 4), nrow = 1))
  )
  save(list = ls(env), file = rdata_path, envir = env)

  result <- system2(
    "Rscript",
    c("--vanilla", script, "--out", out_dir, rdata_path),
    stdout = TRUE,
    stderr = TRUE
  )
  testthat::expect_equal(attr(result, "status") %||% 0L, 0L)

  object_summaries <- read.csv(file.path(out_dir, "object_summaries.csv"))
  testthat::expect_true("E.log.uts_total" %in% object_summaries$quantity)
  testthat::expect_true("E.log.uts_per_time" %in% object_summaries$quantity)
  testthat::expect_false("E.log.uts" %in% object_summaries$quantity)

  per_time <- object_summaries[object_summaries$quantity == "E.log.uts_per_time", ]
  testthat::expect_true(any(per_time$block == "history" & per_time$min == -1 & per_time$max == 2))
  testthat::expect_true(any(per_time$block == "forecast" & per_time$min == 2 & per_time$max == 3))

  key_findings <- read.csv(file.path(out_dir, "runtime_key_findings.csv"))
  testthat::expect_equal(unique(key_findings$lane), "q50")
  testthat::expect_true("E.log.uts_per_time" %in% key_findings$quantity)
  testthat::expect_false("E.log.uts_total" %in% key_findings$quantity)
})
