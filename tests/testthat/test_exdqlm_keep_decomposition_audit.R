`%||%` <- function(x, y) if (is.null(x)) y else x

testthat::test_that("decomposition audit reconstructs synthetic keep history and ragged forecast segments", {
  script <- testthat::test_path(
    "..",
    "..",
    "repro",
    "audits",
    "exdqlm_keep_decomposition_audit.R"
  )
  testthat::skip_if_not(file.exists(script))

  tmp <- tempdir()
  rdata_path <- file.path(tmp, "DISC_variables_50_exAL_synth_DISC.RData")
  out_dir <- file.path(tmp, "decomposition_audit")

  p <- 2L
  J <- 2L
  ppx <- 1L
  TT <- 4L
  ff <- c(1, 0.5)
  sm <- matrix(0, nrow = p * (J + 1L) + ppx, ncol = TT)
  exps <- matrix(NA_real_, nrow = J + 1L, ncol = TT + 4L)

  for (tt in seq_len(TT)) {
    sm[, tt] <- c(
      10 + tt, 2,
      0.1 * tt, 0.2,
      -0.05 * tt, 0.1,
      0.3
    )
    base <- sum(ff * sm[1:2, tt])
    disc1 <- sum(ff * sm[3:4, tt])
    disc2 <- sum(ff * sm[5:6, tt])
    exps[, tt] <- c(base + 0.3, base + disc1 + 0.3, base + disc2 + 0.3)
  }

  sm_seg1 <- matrix(0, nrow = 7L, ncol = 2L)
  sm_seg2 <- matrix(0, nrow = 5L, ncol = 2L)
  for (hh in seq_len(2L)) {
    sm_seg1[, hh] <- c(20 + hh, 3, 0.2 * hh, 0.4, -0.1 * hh, 0.2, 0.5)
    base <- sum(ff * sm_seg1[1:2, hh])
    disc1 <- sum(ff * sm_seg1[3:4, hh])
    disc2 <- sum(ff * sm_seg1[5:6, hh])
    exps[2:3, TT + hh] <- c(base + disc1 + 0.5, base + disc2 + 0.5)

    sm_seg2[, hh] <- c(30 + hh, 4, 0.3 * hh, 0.6, 0.7)
    base2 <- sum(ff * sm_seg2[1:2, hh])
    disc1b <- sum(ff * sm_seg2[3:4, hh])
    exps[2, TT + 2L + hh] <- base2 + disc1b + 0.7
  }

  env <- new.env(parent = emptyenv())
  env$new.theta.out_50_exAL_synth_DISC <- list(
    exps = exps,
    sm = sm,
    sC = array(0, dim = c(nrow(sm), nrow(sm), TT)),
    sm_ens = list(sm_seg1, sm_seg2),
    sC_ens = list(
      array(0, dim = c(nrow(sm_seg1), nrow(sm_seg1), ncol(sm_seg1))),
      array(0, dim = c(nrow(sm_seg2), nrow(sm_seg2), ncol(sm_seg2)))
    )
  )
  save(list = ls(env), file = rdata_path, envir = env)

  result <- system2(
    "Rscript",
    c(
      "--vanilla",
      script,
      "--rdata", rdata_path,
      "--out", out_dir,
      "--p", as.character(p),
      "--J", as.character(J),
      "--ppx", as.character(ppx),
      "--ff-base", paste(ff, collapse = ","),
      "--trend-idx", "1",
      "--season-idx", "2",
      "--start-date", "2020-01-01"
    ),
    stdout = TRUE,
    stderr = TRUE
  )
  testthat::expect_equal(attr(result, "status") %||% 0L, 0L)

  recon <- read.csv(file.path(out_dir, "reconstruction_summary.csv"))
  finite_recon <- recon[is.finite(recon$max_abs_reconstruction_error), , drop = FALSE]
  testthat::expect_true(nrow(finite_recon) > 0L)
  testthat::expect_lt(max(finite_recon$max_abs_reconstruction_error), 1e-10)

  state_map <- read.csv(file.path(out_dir, "state_coordinate_map.csv"))
  testthat::expect_true(any(state_map$phase == "forecast" & state_map$role == "transfer_zeta"))
  testthat::expect_true(any(state_map$phase == "history" & state_map$role == "discrepancy"))
  testthat::expect_true(file.exists(file.path(out_dir, "q50_history_components.png")))
})
