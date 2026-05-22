`%||%` <- function(x, y) if (is.null(x)) y else x

testthat::test_that("curated evidence bundle builds compact report from runtime CSVs", {
  script <- testthat::test_path(
    "..",
    "..",
    "repro",
    "audits",
    "exdqlm_keep_curated_evidence_bundle.R"
  )
  testthat::skip_if_not(file.exists(script))

  tmp <- tempfile("curated_bundle_fixture_")
  runtime_dir <- file.path(tmp, "runtime")
  out_dir <- file.path(tmp, "curated")
  guard_dir <- file.path(tmp, "guards")
  live_dir <- file.path(tmp, "live")
  dir.create(runtime_dir, recursive = TRUE)
  dir.create(guard_dir, recursive = TRUE)
  dir.create(live_dir, recursive = TRUE)

  lanes <- c("q5", "q50")
  state_norms <- do.call(rbind, lapply(lanes, function(lane) {
    data.frame(
      lane = lane,
      block = "history",
      time = 1:6,
      state_norm_sq = seq_len(6) * ifelse(lane == "q5", 1, 2)
    )
  }))
  utils::write.csv(state_norms, file.path(runtime_dir, "state_norms.csv"), row.names = FALSE)

  state_totals <- data.frame(
    lane = lanes,
    block = "history",
    n_state = 2,
    n_time = 6,
    finite_frac = 1,
    total_state_norm_sq = c(21, 42),
    max_time_state_norm_sq = c(6, 12),
    frobenius_norm = sqrt(c(21, 42))
  )
  utils::write.csv(state_totals, file.path(runtime_dir, "state_norm_totals.csv"), row.names = FALSE)

  coords <- do.call(rbind, lapply(lanes, function(lane) {
    expand.grid(
      lane = lane,
      block = "history",
      coordinate = as.character(1:2),
      time = 1:6,
      KEEP.OUT.ATTRS = FALSE,
      stringsAsFactors = FALSE
    )
  }))
  coords$value <- seq_len(nrow(coords)) / 100
  utils::write.csv(coords, file.path(runtime_dir, "selected_state_coordinates.csv"), row.names = FALSE)

  findings <- data.frame(
    lane = rep(lanes, each = 5),
    block = rep(c("history", "history", "history_diagonal", "gamsig", "gamsig"), times = 2),
    source = NA,
    quantity = rep(c("E.inv.uts", "FFF", "QQQ_diag", "E.sigma", "E.gam"), times = 2),
    metric = "distribution",
    finite_frac = 1,
    positive_frac = 1,
    min = c(1, -2, 0.1, 0.01, -0.2, 1, -3, 0.2, 0.02, -0.4),
    median = c(2, 0, 0.2, 0.02, 0.1, 3, 0, 0.3, 0.03, 0.2),
    q95 = c(3, 2, 0.3, 0.03, 0.2, 4, 3, 0.4, 0.04, 0.3),
    q99 = c(4, 3, 0.4, 0.04, 0.3, 5, 4, 0.5, 0.05, 0.4),
    max = c(5, 4, 0.5, 0.05, 0.4, 6, 5, 0.6, 0.06, 0.5)
  )
  utils::write.csv(findings, file.path(runtime_dir, "runtime_key_findings.csv"), row.names = FALSE)

  guard_csv <- file.path(guard_dir, "pseudodata_guard_events.csv")
  utils::write.csv(
    data.frame(
      p0 = 0.05,
      iter = 1001:1002,
      context = "live",
      quantity = "E_inv_uts",
      block = "history",
      n = 10,
      finite_n = 10,
      nonfinite_n = 0,
      positive_required = TRUE,
      nonpositive_n = 0,
      min = 1,
      max = c(6000, 7000),
      max_abs = c(6000, 7000),
      abs_cap = 5000,
      cap_exceed_n = 1,
      status = "cap_exceeded"
    ),
    guard_csv,
    row.names = FALSE
  )

  live_csv <- file.path(live_dir, "live_status.csv")
  utils::write.csv(
    data.frame(
      lane = lanes,
      status = "output_written",
      iter = c(3000, 1079),
      state_norm_sq = c(21, 42)
    ),
    live_csv,
    row.names = FALSE
  )

  result <- system2(
    "Rscript",
    c(
      "--vanilla", script,
      "--runtime-dir", runtime_dir,
      "--out", out_dir,
      "--guard-csv", guard_csv,
      "--live-status", live_csv
    ),
    stdout = TRUE,
    stderr = TRUE
  )
  testthat::expect_equal(attr(result, "status") %||% 0L, 0L)
  testthat::expect_true(file.exists(file.path(out_dir, "README.md")))
  testthat::expect_true(file.exists(file.path(out_dir, "state_norm_history_panel.png")))
  testthat::expect_true(file.exists(file.path(out_dir, "latent_pseudodata_extremes_panel.png")))
  testthat::expect_true(file.exists(file.path(out_dir, "q05_e_inv_u_guard_burst.png")))
  readme <- readLines(file.path(out_dir, "README.md"))
  testthat::expect_true(any(grepl("Peak `E_inv_uts`/`history`", readme, fixed = TRUE)))

  out_no_guard <- file.path(tmp, "curated_no_guard")
  result_no_guard <- system2(
    "Rscript",
    c(
      "--vanilla", script,
      "--runtime-dir", runtime_dir,
      "--out", out_no_guard,
      "--live-status", live_csv
    ),
    stdout = TRUE,
    stderr = TRUE
  )
  testthat::expect_equal(attr(result_no_guard, "status") %||% 0L, 0L)
  readme_no_guard <- readLines(file.path(out_no_guard, "README.md"))
  testthat::expect_true(any(grepl("No live guard rows were supplied or observed", readme_no_guard, fixed = TRUE)))
  testthat::expect_false(any(grepl("q05 still had a transient live", readme_no_guard, fixed = TRUE)))
})
