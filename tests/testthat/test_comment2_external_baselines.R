library(testthat)

workflow <- normalizePath(if (file.exists("scripts/build_comment2_external_baselines.R")) "." else "../..")
source(file.path(workflow, "scripts/build_comment2_external_baselines.R"), local = TRUE)
settings <- jsonlite::read_json(file.path(workflow, "config/comment2_external_baselines.json"),
                                simplifyVector = TRUE)$settings
scorer <- new.env(parent = globalenv())
sys.source(file.path(workflow, "R/environmetrics/02_helpers_core.R"), envir = scorer)

test_that("the unchanged publication scorer has the correct point-mass limit", {
  prediction <- matrix(c(.2, 1.1, 3), nrow = 2000, ncol = 3, byrow = TRUE)
  y <- c(.1, 1.1, 5)
  scored <- scorer$post_crps_quantile_approx(y, prediction)
  expect_equal(scored$crps, abs(y - c(.2, 1.1, 3)), tolerance = 1e-13)
  expect_identical(scored$method, "quantile_check_loss_sum")
  expect_identical(scored$tau_rule, "k_over_m_plus_1")
})

test_that("truncated-normal quantiles are stable and match the analytic CRPS integral", {
  p <- seq_len(20000) / 20001
  for (mu in c(-20, -1, 0, 2)) {
    quantiles <- c2_qtnorm(p, mu, .7)
    expect_true(all(is.finite(quantiles)))
    expect_true(all(quantiles >= 0))
    expect_true(all(diff(quantiles) >= 0))
    numeric_score <- scorer$post_crps_quantile_approx(1.2, matrix(quantiles, ncol = 1))$crps
    analytic <- c2_tn_crps(1.2, mu, .7)
    expect_equal(numeric_score, analytic, tolerance = 2e-4)
    if (mu >= -1) expect_equal(analytic,
      scoringRules::crps_tnorm(1.2, location = mu, scale = .7, lower = 0), tolerance = 1e-12)
  }
})

test_that("calendar climatology is circular and preserves the leap-day slot", {
  days <- c2_calendar_day(c("2019-02-28", "2020-02-29", "2019-03-01"))
  expect_identical(days, c(59L, 60L, 61L))
  expect_equal(c2_calendar_distance(c2_calendar_day("2020-12-31"),
                                   c2_calendar_day("2021-01-01")), 1)
})

test_that("training excludes unmatured outcomes and incompatible products", {
  history <- data.frame(date = c("2021-05-25", "2021-05-26", "2021-05-27", "2021-06-01"), Y = c(1, 2, 2.5, 3))
  features <- data.frame(issue_date = c("2021-05-24", "2021-05-26", "2021-05-31", "2021-06-01"),
    target_date = c("2021-05-25", "2021-05-27", "2021-06-02", "2021-06-02"),
    lead_day = c(1, 1, 2, 1), product_family = c("GloFAS-2.x", rep("GloFAS-3.x", 3)),
    ensemble_mean = 1, ensemble_variance = .1)
  # Two mature current-version records are valid; old-version, unmatured and
  # contemporaneous-issuance rows must never enter the training set.
  features <- rbind(features, data.frame(issue_date = "2021-05-31", target_date = "2021-06-01",
    lead_day = 1, product_family = "GloFAS-3.x", ensemble_mean = 2, ensemble_variance = .2))
  selected <- c2_training(history, features, "2021-06-01", settings)
  expect_identical(selected$issue_date, c("2021-05-26", "2021-05-31"))
  expect_identical(selected$observed, c(2.5, 3))
  future <- rbind(history, data.frame(date = "2021-06-02", Y = 1e8))
  expect_error(c2_training(future, features, "2021-06-01", settings), "post-origin")
  # Arbitrarily perturb future verification; the history made available to the
  # fit remains identical, rather than merely asserting a prose date convention.
  future$Y[future$date > "2021-06-01"] <- -1e20
  selected_after <- c2_training(future[future$date <= "2021-06-01", ], features,
                                 "2021-06-01", settings)
  expect_identical(selected, selected_after)
})

test_that("fit diagnostics fail closed on insufficient cases", {
  training <- data.frame(observed = rep(1, 10), ensemble_mean = rep(1, 10),
                         ensemble_variance = rep(.1, 10))
  expect_error(c2_emos_fit(training, settings), "Too few")
})

test_that("optimizer rejects mathematically invalid tail-score evaluations", {
  pathological <- c2_tn_crps(c(0, 1e-6), -20, exp(-9))
  expect_false(c2_valid_training_scores(pathological, 2))
  expect_false(c2_valid_training_scores(c(.2, Inf), 2))
  expect_false(c2_valid_training_scores(c(.2, NaN), 2))
  expect_false(c2_valid_training_scores(c(.2), 2))
  expect_true(c2_valid_training_scores(c(.2, .3), 2))
})

test_that("reported skill uses the ratio of aggregate scores", {
  frame <- data.frame(cutoff_date = rep(c("2021-01-01", "2022-01-01"), each = 2),
    model = "A", lead_day = rep(1:2, 2), crps = c(1, 3, 2, 6),
    climatology_crps = c(2, 2, 4, 8))
  result <- c2_aggregate(frame, 2)
  expect_equal(result$aggregate$crpss, 1 - 12 / 16)
  expect_false(isTRUE(all.equal(result$aggregate$crpss,
                               mean(1 - frame$crps/frame$climatology_crps))))
})

test_that("curated CSV round trips preserve binary doubles", {
  path <- tempfile(fileext = ".csv.gz")
  on.exit(unlink(path))
  original <- data.frame(value = c(pi, .Machine$double.eps, sqrt(2), 1e-17),
                         text = c("a", "b", "c", "d"))
  c2_write(original, path)
  expect_identical(c2_read(path)$value, original$value)
})

test_that("curated replay rejects corrupted inputs before computation", {
  path <- tempfile(); dir.create(path)
  on.exit(unlink(path, recursive = TRUE))
  writeLines("original input", file.path(path, "forecast_features.csv.gz"))
  index <- data.frame(file = "forecast_features.csv.gz",
                       sha256 = c2_hash(file.path(path, "forecast_features.csv.gz")))
  c2_write(index, file.path(path, "bundle_checksums.csv"))
  writeLines("altered input", file.path(path, "forecast_features.csv.gz"))
  expect_error(c2_load_bundle(path, settings), "checksum mismatch")
  index$file <- "../escape"
  c2_write(index, file.path(path, "bundle_checksums.csv"))
  expect_error(c2_load_bundle(path, settings), "Unsafe curated")
})
