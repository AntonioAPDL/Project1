source(testthat::test_path("..", "..", "R", "environmetrics", "02_helpers_core.R"))

test_that("build_agg_discrep_quantile_df maps fitted overlays to rows 1/4/7", {
  q <- array(NA_real_, dim = c(7, 6, 3))
  for (r in 1:7) {
    for (t in 1:6) {
      q[r, t, 1] <- r + t + 0.3
      q[r, t, 2] <- r + t + 0.2
      q[r, t, 3] <- r + t + 0.1
    }
  }

  idx <- 2:5
  dates <- as.Date("2022-12-26") + 0:3
  df <- build_agg_discrep_quantile_df(q, idx = idx, dates = dates)

  expect_equal(sort(unique(df$Quantile)), c("50th", "5th", "95th"))
  expect_equal(nrow(df), 3L * length(idx))

  med_5 <- df$Median[df$Quantile == "5th"]
  med_50 <- df$Median[df$Quantile == "50th"]
  med_95 <- df$Median[df$Quantile == "95th"]

  expect_equal(med_5, q[1, idx, 2])
  expect_equal(med_50, q[4, idx, 2])
  expect_equal(med_95, q[7, idx, 2])

  expect_true(all(df$Lower <= df$Upper))
})

test_that("build_agg_discrep_quantile_df validates index and date contracts", {
  q <- array(1, dim = c(7, 4, 3))
  idx <- 1:3
  dates <- as.Date("2022-01-01") + 0:2

  expect_error(
    build_agg_discrep_quantile_df(q, idx = idx, dates = dates, quantile_rows = c(1, 8, 7)),
    "ROW_OOB"
  )

  expect_error(
    build_agg_discrep_quantile_df(q, idx = idx, dates = dates[1:2]),
    "DATE_LEN"
  )

  expect_error(
    build_agg_discrep_quantile_df(q, idx = c(1, 5), dates = dates[1:2]),
    "INDEX_OOB"
  )
})

test_that("resolve_agg_discrep_ylim keeps preferred limits when fitted coverage is adequate", {
  obs <- c(-0.2, 0.1, 0.3, -0.1)
  fitted_df <- data.frame(
    Lower = c(-0.4, -0.3, -0.2),
    Median = c(-0.1, 0.0, 0.1),
    Upper = c(0.2, 0.3, 0.4)
  )

  out <- resolve_agg_discrep_ylim(
    obs = obs,
    fitted_df = fitted_df,
    preferred_ylim = c(-1, 1),
    context = "test.pref"
  )

  expect_equal(out$mode, "preferred")
  expect_equal(out$ylim, c(-1, 1))
  expect_true(is.finite(out$preferred_inrange_share))
  expect_gte(out$preferred_inrange_share, 0.99)
})

test_that("resolve_agg_discrep_ylim expands limits when preferred range hides fitted series", {
  obs <- c(-0.2, 0.1, 0.3, -0.1)
  fitted_df <- data.frame(
    Lower = c(3.0, 3.1, 3.2),
    Median = c(3.3, 3.4, 3.5),
    Upper = c(3.6, 3.7, 3.8)
  )

  out <- resolve_agg_discrep_ylim(
    obs = obs,
    fitted_df = fitted_df,
    preferred_ylim = c(-1, 1),
    context = "test.expand"
  )

  expect_equal(out$mode, "expanded")
  expect_lt(out$preferred_inrange_share, 0.15)
  expect_lt(out$ylim[[1]], min(c(obs, fitted_df$Lower), na.rm = TRUE))
  expect_gt(out$ylim[[2]], max(c(obs, fitted_df$Upper), na.rm = TRUE))
})
