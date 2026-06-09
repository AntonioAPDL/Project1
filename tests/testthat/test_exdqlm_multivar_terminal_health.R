source(testthat::test_path("..", "..", "R", "unified", "stages", "stage_fit.R"))

make_terminal_health_fixture <- function(path, transfer_level = 0, history_exps = 0, sm_ens_value = 0) {
  TT <- 10L
  HH <- 2L
  sm <- matrix(0, nrow = 34L, ncol = TT)
  sm[22L, ] <- transfer_level
  exps <- matrix(0, nrow = 3L, ncol = TT + HH)
  exps[, seq_len(TT)] <- history_exps
  exps[, (TT + 1L):(TT + HH)] <- 0.5
  theta <- list(
    sm = sm,
    sm_ens = list(matrix(sm_ens_value, nrow = 4L, ncol = HH)),
    exps = exps
  )
  gamsig <- list(E.sigma = matrix(0.1, nrow = 3L, ncol = TT))
  new.theta.out <- theta
  new.gamsig.out <- gamsig
  save(new.theta.out, new.gamsig.out, file = path)
  invisible(path)
}

testthat::test_that("terminal multivar health flags impossible saved history and transfer state", {
  rdata <- tempfile(fileext = ".RData")
  txt <- tempfile(fileext = ".txt")
  terminal_txt <- tempfile(fileext = ".txt")
  terminal_csv <- tempfile(fileext = ".csv")
  make_terminal_health_fixture(
    rdata,
    transfer_level = 200,
    history_exps = 500
  )

  out <- unified_multivar_fit_health_check(
    rdata_path = rdata,
    quantile = 0.35,
    transfer_mode = "drop",
    report_path = txt,
    terminal_report_path = terminal_txt,
    terminal_csv_path = terminal_csv,
    history_latent_limit = 25,
    state_norm_sq_per_T_limit = 1e4,
    transfer_level_limit = 25
  )

  testthat::expect_true(any(grepl("max_abs_history_exps", out$violations)))
  testthat::expect_true(any(grepl("state_norm_sq_per_T", out$violations)))
  testthat::expect_true(any(grepl("transfer_level_max_abs", out$violations)))
  testthat::expect_true(file.exists(terminal_txt))
  testthat::expect_true(file.exists(terminal_csv))
  rows <- utils::read.csv(terminal_csv, stringsAsFactors = FALSE)
  testthat::expect_true(any(rows$metric == "max_abs_history_exps" & rows$status == "warn"))
  testthat::expect_true(any(rows$metric == "max_abs_history_exps" & rows$severity == "warning"))
  testthat::expect_true(any(rows$metric == "transfer_level_max_abs" & rows$status == "fail"))
  terminal_lines <- readLines(terminal_txt)
  testthat::expect_true(any(grepl("^terminal_status=fail$", terminal_lines)))
  testthat::expect_true(any(grepl("^hard_violations=.*transfer_level_max_abs", terminal_lines)))
  testthat::expect_true(any(grepl("^warnings=max_abs_history_exps$", terminal_lines)))
})

testthat::test_that("terminal multivar health separates warning-only history magnitude from hard failures", {
  rdata <- tempfile(fileext = ".RData")
  terminal_txt <- tempfile(fileext = ".txt")
  terminal_csv <- tempfile(fileext = ".csv")
  make_terminal_health_fixture(
    rdata,
    transfer_level = 0,
    history_exps = 26
  )

  out <- unified_multivar_fit_health_check(
    rdata_path = rdata,
    quantile = 0.05,
    transfer_mode = "drop",
    terminal_report_path = terminal_txt,
    terminal_csv_path = terminal_csv,
    history_latent_limit = 25,
    state_norm_sq_per_T_limit = 1e4,
    transfer_level_limit = 25
  )

  testthat::expect_true(any(grepl("max_abs_history_exps", out$violations)))
  testthat::expect_equal(out$hard_violations, character(0))
  testthat::expect_equal(out$warning_violations, "max_abs_history_exps")
  rows <- utils::read.csv(terminal_csv, stringsAsFactors = FALSE)
  testthat::expect_true(any(rows$metric == "max_abs_history_exps" & rows$status == "warn"))
  testthat::expect_false(any(rows$status == "fail"))
  terminal_lines <- readLines(terminal_txt)
  testthat::expect_true(any(grepl("^terminal_status=warn$", terminal_lines)))
  testthat::expect_true(any(grepl("^hard_violations=$", terminal_lines)))
  testthat::expect_true(any(grepl("^warnings=max_abs_history_exps$", terminal_lines)))
})

testthat::test_that("terminal multivar health passes healthy final saved state", {
  rdata <- tempfile(fileext = ".RData")
  make_terminal_health_fixture(
    rdata,
    transfer_level = 2,
    history_exps = 1.5,
    sm_ens_value = 0.25
  )

  out <- unified_multivar_fit_health_check(
    rdata_path = rdata,
    quantile = 0.80,
    transfer_mode = "drop",
    history_latent_limit = 25,
    state_norm_sq_per_T_limit = 1e4,
    transfer_level_limit = 25
  )

  testthat::expect_equal(out$violations, character(0))
  testthat::expect_equal(out$hard_violations, character(0))
  testthat::expect_equal(out$warning_violations, character(0))
  testthat::expect_equal(out$finite_history_exps, 30L)
  testthat::expect_true(is.finite(out$state_norm_sq_per_T))
  testthat::expect_true(all(out$terminal_rows$status == "ok"))
})
