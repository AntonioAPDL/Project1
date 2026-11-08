library(testthat)

candidate_scripts <- c("scripts/build_no_refit_synthesis_diagnostics.R",
                       "../../scripts/build_no_refit_synthesis_diagnostics.R")
script_path <- candidate_scripts[file.exists(candidate_scripts)][1L]
stopifnot(!is.na(script_path))
helper_env <- new.env(parent = globalenv())
source(script_path, local = helper_env)

test_that("first extraction resolves workflow sources independently of the article checkout", {
  root <- tempfile("workflow_binding_")
  dir.create(file.path(root, "scripts"), recursive = TRUE)
  dir.create(file.path(root, "R/environmetrics"), recursive = TRUE)
  writeLines("# frozen source fixture", file.path(root, "R/environmetrics/02_helpers_core.R"))
  expected <- normalizePath(root)
  expect_identical(helper_env$n14_workflow_root(root, "/unrelated/article/scripts/export.R"), expected)
  expect_identical(helper_env$n14_workflow_root(script = file.path(root, "scripts/export.R")), expected)
  expect_error(helper_env$n14_workflow_root(), "requires --workflow-root")
  expect_error(helper_env$n14_workflow_root(tempdir()), "source root is unavailable")
  unlink(root, recursive = TRUE)
})

test_that("own predictive anchors use each fit's target and declared type7", {
  cube <- array(0, c(3L, 4L, 2L))
  cube[1L, , 1L] <- 0:3
  cube[2L, , 1L] <- 10:13
  cube[3L, , 1L] <- 20:23
  cube[, , 2L] <- cube[, , 1L] + 100
  before <- get0(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
  actual <- helper_env$n14_own_anchors(cube, c(.25, .5, .75))
  expect_equal(actual[, 1L], c(.75, 11.5, 22.25))
  expect_equal(actual[, 2L], c(100.75, 111.5, 122.25))
  expect_identical(get0(".Random.seed", envir = .GlobalEnv, inherits = FALSE), before)
  cube[2L, 1L, 1L] <- NA_real_
  expect_error(helper_env$n14_own_anchors(cube, c(.25, .5, .75)), "finite support")
})

test_that("isotonic anchors and crossing counts describe quantile curves", {
  anchors <- matrix(c(3, 1, 2, -2, 0, 4), nrow = 3L)
  adjusted <- helper_env$n14_isotonic(anchors, c(.25, .5, .75))
  expect_equal(adjusted[, 1L], c(2, 2, 2))
  expect_equal(adjusted[, 2L], c(-2, 0, 4))
  expect_equal(unname(helper_env$n14_crossings(anchors[, 1L])), c(1, -2))
  expect_equal(unname(helper_env$n14_crossings(adjusted[, 1L])), c(0, 0))
  expect_equal(unname(helper_env$n14_crossings(c(1, 1, 2))), c(0, 0))
})

test_that("quantile loss respects asymmetry and exact ties", {
  expect_equal(helper_env$n14_loss(c(2, 0, 1), c(1, 1, 1), c(.2, .2, .9)), c(.2, .8, 0))
  x <- c(-.2, 0, .3)
  observed <- .1
  expect_identical(observed < x, expm1(observed) < expm1(x))
  expect_lt(expm1(x[1L]), 0)
})

test_that("the final bundle preserves role/type and unsupported tails", {
  bundle <- Sys.getenv("NO_REFIT_SYNTHESIS_DIR", "")
  if (!nzchar(bundle)) {
    workflow <- normalizePath(file.path(dirname(script_path), ".."))
    binding <- jsonlite::read_json(file.path(workflow, "config/article_repository_binding.json"))
    article <- Sys.getenv(binding$root_override_environment, file.path(workflow, binding$active_article_directory))
    bundle <- file.path(article, "artifacts/no_refit_revision/synthesis_diagnostics")
  }
  skip_if(is.na(bundle) || !file.exists(file.path(bundle, "manifest.json")), "Bundle not supplied")
  inputs <- helper_env$n14_read(file.path(bundle, "inputs/anchors.csv"))
  expect_equal(nrow(inputs), 5880L)
  expect_equal(length(unique(inputs$representation_id)), 30L)
  expect_equal(sum(inputs$final_quantile_definition == "frozen_HE4_target_quantile"), 3920L)
  expect_equal(sum(inputs$final_quantile_definition == "new_sample_quantiles_type8"), 1960L)
  support <- helper_env$n14_read(file.path(bundle, "inputs/support.csv"))
  expect_equal(sum(as.numeric(support$final_prediction_negative_log_values) > 0), 10L)
  expect_true(all(as.integer(support$clipped_values) == 0L))
  cases <- helper_env$n14_read(file.path(bundle, "per_case.csv"))
  log_rows <- cases[cases$score_scale == "log1p_cms", , drop = FALSE]
  raw_rows <- cases[cases$score_scale == "discharge_cms", , drop = FALSE]
  expect_identical(log_rows$hit_strict, raw_rows$hit_strict)
  expect_identical(log_rows$hit_weak, raw_rows$hit_weak)
  expect_identical(log_rows$exact_tie, raw_rows$exact_tie)
  helper_env$n14_main(c("--output-dir", bundle, "--check"))
})
