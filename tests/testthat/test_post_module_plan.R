post_module_plan_path <- testthat::test_path("..", "..", "R", "unified", "post_module_plan.R")

testthat::test_that("post module plan selects univar-only safe modules", {
  source(post_module_plan_path, local = TRUE)

  core <- c("00_paths.R", "00_setup.R")
  mods <- unified_post_select_modules(
    post_figures = TRUE,
    post_smoke_fast = FALSE,
    model_run_exdqlm_multivar = FALSE,
    model_run_exdqlm_univar = TRUE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE,
    core_modules = core
  )

  testthat::expect_true("30_univariate_and_misc.R" %in% mods)
  testthat::expect_false("40_figures_smoke_fast.R" %in% mods)
  testthat::expect_true("40_figures_univar_only.R" %in% mods)
  testthat::expect_false("40_figures.R" %in% mods)
})

testthat::test_that("post module plan keeps ndlm-only isolation branch", {
  source(post_module_plan_path, local = TRUE)

  core <- c("00_paths.R", "00_setup.R")
  mods <- unified_post_select_modules(
    post_figures = TRUE,
    post_smoke_fast = FALSE,
    model_run_exdqlm_multivar = FALSE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = TRUE,
    model_run_ndlm_univar = FALSE,
    core_modules = core
  )

  testthat::expect_true("30_ndlm_only_init.R" %in% mods)
  testthat::expect_true("40_figures_ndlm_only.R" %in% mods)
  testthat::expect_false("40_figures.R" %in% mods)
})

testthat::test_that("post module plan keeps full figures for mixed/all-family mode", {
  source(post_module_plan_path, local = TRUE)

  core <- c("00_paths.R", "00_setup.R")
  mods <- unified_post_select_modules(
    post_figures = TRUE,
    post_smoke_fast = FALSE,
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = TRUE,
    model_run_ndlm_main = TRUE,
    model_run_ndlm_univar = FALSE,
    core_modules = core
  )

  testthat::expect_true("30_univariate_and_misc.R" %in% mods)
  testthat::expect_true("40_figures.R" %in% mods)
  testthat::expect_false("40_figures_smoke_fast.R" %in% mods)
})

testthat::test_that("post module plan keeps lightweight synthesis init for mixed smoke-fast mode", {
  source(post_module_plan_path, local = TRUE)

  core <- c("00_paths.R", "00_setup.R")
  mods <- unified_post_select_modules(
    post_figures = TRUE,
    post_smoke_fast = TRUE,
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = TRUE,
    model_run_ndlm_main = TRUE,
    model_run_ndlm_univar = TRUE,
    core_modules = core
  )

  testthat::expect_true("30_univariate_and_misc.R" %in% mods)
  testthat::expect_true("40_figures_smoke_fast.R" %in% mods)
  testthat::expect_false("40_figures.R" %in% mods)
})

testthat::test_that("post module plan uses smoke-fast exporter for multivar-only comparison lanes", {
  source(post_module_plan_path, local = TRUE)

  core <- c("00_paths.R", "00_setup.R")
  mods <- unified_post_select_modules(
    post_figures = TRUE,
    post_smoke_fast = TRUE,
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE,
    core_modules = core
  )

  testthat::expect_true("30_univariate_and_misc.R" %in% mods)
  testthat::expect_true("40_figures_smoke_fast.R" %in% mods)
  testthat::expect_false("40_figures_multivar_only.R" %in% mods)
})

testthat::test_that("post module plan can append q50 multivar components to smoke-fast lanes", {
  source(post_module_plan_path, local = TRUE)

  core <- c("00_paths.R", "00_setup.R")
  mods <- unified_post_select_modules(
    post_figures = TRUE,
    post_smoke_fast = TRUE,
    model_run_exdqlm_multivar = TRUE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = FALSE,
    core_modules = core,
    multivar_component_diagnostics = TRUE
  )

  testthat::expect_true("40_figures_smoke_fast.R" %in% mods)
  testthat::expect_true("40_figures_multivar_only.R" %in% mods)
  testthat::expect_equal(sum(mods == "40_figures_multivar_only.R"), 1L)
})

testthat::test_that("post module plan treats ndlm_univar-only as ndlm isolation lane", {
  source(post_module_plan_path, local = TRUE)

  core <- c("00_paths.R", "00_setup.R")
  mods <- unified_post_select_modules(
    post_figures = TRUE,
    post_smoke_fast = FALSE,
    model_run_exdqlm_multivar = FALSE,
    model_run_exdqlm_univar = FALSE,
    model_run_ndlm_main = FALSE,
    model_run_ndlm_univar = TRUE,
    core_modules = core
  )

  testthat::expect_true("30_ndlm_only_init.R" %in% mods)
  testthat::expect_true("40_figures_ndlm_only.R" %in% mods)
  testthat::expect_false("40_figures.R" %in% mods)
})
