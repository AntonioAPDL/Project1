source(testthat::test_path("..", "..", "R", "disc_w", "08_gamsig_schedule.R"))

test_that("disc_w_normalize_state_refresh_schedule validates enabled schedule", {
  sched <- disc_w_normalize_state_refresh_schedule(
    enabled = TRUE,
    start_iter = 11L,
    end_iter = 200L,
    hold_iters = 10L,
    refresh_iters = 1L
  )

  expect_true(sched$enabled)
  expect_equal(sched$start_iter, 11L)
  expect_equal(sched$end_iter, 200L)
  expect_equal(sched$hold_iters, 10L)
  expect_equal(sched$refresh_iters, 1L)
})

test_that("disc_w_state_refresh_phase cycles hold and refresh correctly", {
  sched <- disc_w_normalize_state_refresh_schedule(
    enabled = TRUE,
    start_iter = 11L,
    end_iter = 200L,
    hold_iters = 10L,
    refresh_iters = 1L
  )

  expect_false(disc_w_state_refresh_phase(10L, sched)$active)
  expect_true(disc_w_state_refresh_phase(11L, sched)$hold)
  expect_true(disc_w_state_refresh_phase(20L, sched)$hold)
  expect_true(disc_w_state_refresh_phase(21L, sched)$refresh)
  expect_true(disc_w_state_refresh_phase(22L, sched)$hold)
  expect_true(disc_w_state_refresh_phase(32L, sched)$refresh)
  expect_false(disc_w_state_refresh_phase(201L, sched)$active)
})

test_that("disc_w_normalize_state_refresh_schedule rejects invalid values", {
  expect_error(
    disc_w_normalize_state_refresh_schedule(
      enabled = TRUE,
      start_iter = 0L,
      end_iter = 200L,
      hold_iters = 10L,
      refresh_iters = 1L
    ),
    "start_iter"
  )
  expect_error(
    disc_w_normalize_state_refresh_schedule(
      enabled = TRUE,
      start_iter = 11L,
      end_iter = 10L,
      hold_iters = 10L,
      refresh_iters = 1L
    ),
    "end_iter"
  )
})
