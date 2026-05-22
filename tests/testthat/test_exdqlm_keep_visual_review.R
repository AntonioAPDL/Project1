testthat::test_that("visual review script writes ELBO, theta.out, and exps plots", {
  script <- testthat::test_path(
    "..",
    "..",
    "repro",
    "audits",
    "exdqlm_keep_visual_review.R"
  )
  testthat::skip_if_not(file.exists(script))

  tmp <- tempfile("keep_visual_review_")
  run_root <- file.path(tmp, "run")
  keep_root <- file.path(run_root, "fit", "exdqlm_multivar", "keep")
  decomp_dir <- file.path(tmp, "decomp")
  out_dir <- file.path(tmp, "visual")
  dir.create(file.path(keep_root, "q=05", "outputs"), recursive = TRUE)
  dir.create(file.path(keep_root, "q=50", "outputs"), recursive = TRUE)
  dir.create(decomp_dir, recursive = TRUE)

  make_rdata <- function(path, q, offset) {
    seq_obj <- matrix(cumsum(c(-10, rep(0.1, 20))) + offset, nrow = 1)
    sm <- matrix(seq_len(11 * 12) / 100 + offset, nrow = 11, ncol = 12)
    exps <- matrix(rep(seq_len(15), each = 3) / 10 + offset, nrow = 3)
    theta <- list(sm = sm, exps = exps)
    assign(sprintf("seq.elbo_%s_exAL_synth_DISC", q), seq_obj)
    assign(sprintf("new.theta.out_%s_exAL_synth_DISC", q), theta)
    save(
      list = c(
        sprintf("seq.elbo_%s_exAL_synth_DISC", q),
        sprintf("new.theta.out_%s_exAL_synth_DISC", q)
      ),
      file = path
    )
  }
  make_rdata(file.path(keep_root, "q=05", "outputs", "DISC_variables_5_exAL_synth_DISC.RData"), "5", 0)
  make_rdata(file.path(keep_root, "q=50", "outputs", "DISC_variables_50_exAL_synth_DISC.RData"), "50", 1)

  utils::write.csv(
    data.frame(
      phase = "history",
      segment = 0,
      role = c("theta", "theta", "theta", "discrepancy", "discrepancy", "transfer_zeta"),
      source = c("target", "target", "target", "source_1", "source_2", "all"),
      index = c(1, 2, 3, 4, 7, 10)
    ),
    file.path(decomp_dir, "state_coordinate_map.csv"),
    row.names = FALSE
  )
  hist <- expand.grid(
    lane = c("q05", "q50"),
    time_index = seq_len(12),
    source = c("target", "source_1"),
    KEEP.OUT.ATTRS = FALSE,
    stringsAsFactors = FALSE
  )
  hist$phase <- "history"
  hist$segment <- 0
  hist$date <- as.Date("2020-01-01") + hist$time_index - 1L
  hist$observed_usgs <- hist$time_index / 10
  hist$target_exps <- hist$time_index / 11 + ifelse(hist$lane == "q50", 0.1, 0)
  hist$target_reconstructed <- hist$target_exps
  hist$target_error <- 0
  hist$mu_without_transfer <- 0
  hist$transfer_zeta <- 0
  hist$trend_agg <- 0
  hist$season_agg <- 0
  hist$exps <- hist$target_exps
  hist$reconstructed <- hist$target_exps
  hist$discrepancy <- 0
  hist$reconstruction_error <- 0
  utils::write.csv(hist, file.path(decomp_dir, "history_decomposition.csv"), row.names = FALSE)

  forecast <- hist[hist$source == "source_1", , drop = FALSE]
  forecast$phase <- "forecast"
  forecast$lead_index <- forecast$time_index
  utils::write.csv(forecast, file.path(decomp_dir, "forecast_decomposition.csv"), row.names = FALSE)

  result <- system2(
    "Rscript",
    c(
      "--vanilla", script,
      "--run-root", run_root,
      "--decomp-dir", decomp_dir,
      "--out", out_dir
    ),
    stdout = TRUE,
    stderr = TRUE
  )
  testthat::expect_equal(attr(result, "status") %||% 0L, 0L)
  testthat::expect_true(file.exists(file.path(out_dir, "README.md")))
  testthat::expect_true(file.exists(file.path(out_dir, "elbo_convergence_panel.png")))
  testthat::expect_true(file.exists(file.path(out_dir, "thetaout_state_norm_panel.png")))
  testthat::expect_true(file.exists(file.path(out_dir, "thetaout_selected_states_panel.png")))
  testthat::expect_true(file.exists(file.path(out_dir, "usgs_history_target_exps_last730.png")))
  testthat::expect_true(file.exists(file.path(out_dir, "elbo_summary.csv")))
})
