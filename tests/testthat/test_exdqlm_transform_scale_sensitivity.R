source(testthat::test_path("..", "..", "R", "disc_w", "11_latent_pseudodata_audit_helpers.R"))

testthat::test_that("scale sensitivity fixture records zero and near-zero behavior", {
  fixture <- disc_w_audit_scale_sensitivity_fixture(
    raw_y = c(0, 1e-6, 0.001, 0.1, 1, 10, 100),
    raw_exps = c(0, 1e-6, 0.001, 0.11, 0.9, 9, 90)
  )

  log1p_rows <- fixture[fixture$scale == "log1p_cms", ]
  loglog_rows <- fixture[fixture$scale == "log_log1p_cms", ]

  testthat::expect_true(all(log1p_rows$valid_scaled))
  testthat::expect_false(loglog_rows$valid_scaled[loglog_rows$raw_y == 0])
  testthat::expect_true(all(loglog_rows$valid_scaled[loglog_rows$raw_y > 0]))
  testthat::expect_true(all(is.finite(log1p_rows$E_inv_uts)))
  testthat::expect_true(all(log1p_rows$pseudo_variance > 0))
})

testthat::test_that("log1p scale expands high-flow residuals relative to log-log comparator", {
  fixture <- disc_w_audit_scale_sensitivity_fixture(
    raw_y = c(10, 100, 1000),
    raw_exps = c(8, 80, 800)
  )

  wide <- merge(
    fixture[fixture$scale == "log1p_cms", c("raw_y", "residual2", "E_inv_uts", "pseudo_offset")],
    fixture[fixture$scale == "log_log1p_cms", c("raw_y", "residual2", "E_inv_uts", "pseudo_offset")],
    by = "raw_y",
    suffixes = c("_log1p", "_loglog1p")
  )

  testthat::expect_true(all(wide$residual2_log1p > wide$residual2_loglog1p))
  testthat::expect_true(all(is.finite(wide$E_inv_uts_log1p)))
  testthat::expect_true(all(is.finite(wide$E_inv_uts_loglog1p)))
  testthat::expect_true(all(is.finite(wide$pseudo_offset_log1p)))
  testthat::expect_true(all(is.finite(wide$pseudo_offset_loglog1p)))
})
