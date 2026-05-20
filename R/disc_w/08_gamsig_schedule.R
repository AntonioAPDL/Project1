# disc_w/08_gamsig_schedule.R
#
# Helpers for optional gamma/sigma state refresh scheduling. These are pure
# functions so the scheduling policy can be tested independently of the
# monolithic legacy fit loop.

disc_w_normalize_state_refresh_schedule <- function(
  enabled = FALSE,
  start_iter = 11L,
  end_iter = 200L,
  hold_iters = 10L,
  refresh_iters = 1L
) {
  if (!isTRUE(enabled) && !identical(enabled, FALSE)) {
    stop("state_refresh_schedule.enabled must be boolean", call. = FALSE)
  }

  out <- list(
    enabled = isTRUE(enabled),
    start_iter = suppressWarnings(as.integer(start_iter)),
    end_iter = suppressWarnings(as.integer(end_iter)),
    hold_iters = suppressWarnings(as.integer(hold_iters)),
    refresh_iters = suppressWarnings(as.integer(refresh_iters))
  )

  if (!out$enabled) {
    return(out)
  }

  if (!is.finite(out$start_iter) || out$start_iter < 1L) {
    stop("state_refresh_schedule.start_iter must be an integer >= 1", call. = FALSE)
  }
  if (!is.finite(out$end_iter) || out$end_iter < out$start_iter) {
    stop("state_refresh_schedule.end_iter must be an integer >= start_iter", call. = FALSE)
  }
  if (!is.finite(out$hold_iters) || out$hold_iters < 1L) {
    stop("state_refresh_schedule.hold_iters must be an integer >= 1", call. = FALSE)
  }
  if (!is.finite(out$refresh_iters) || out$refresh_iters < 1L) {
    stop("state_refresh_schedule.refresh_iters must be an integer >= 1", call. = FALSE)
  }

  out
}

disc_w_state_refresh_phase <- function(iter_candidate, schedule) {
  if (!is.list(schedule)) {
    stop("schedule must be a list", call. = FALSE)
  }

  enabled <- isTRUE(schedule$enabled)
  iter_candidate <- suppressWarnings(as.integer(iter_candidate))
  if (!enabled || !is.finite(iter_candidate) || iter_candidate < 1L) {
    return(list(active = FALSE, hold = FALSE, refresh = FALSE, position = NA_integer_))
  }

  start_iter <- suppressWarnings(as.integer(schedule$start_iter))
  end_iter <- suppressWarnings(as.integer(schedule$end_iter))
  hold_iters <- suppressWarnings(as.integer(schedule$hold_iters))
  refresh_iters <- suppressWarnings(as.integer(schedule$refresh_iters))
  cycle_len <- suppressWarnings(as.integer(hold_iters + refresh_iters))

  if (!is.finite(start_iter) || !is.finite(end_iter) || !is.finite(hold_iters) ||
      !is.finite(refresh_iters) || !is.finite(cycle_len) || cycle_len < 1L) {
    stop("schedule is not normalized", call. = FALSE)
  }

  if (iter_candidate < start_iter || iter_candidate > end_iter) {
    return(list(active = FALSE, hold = FALSE, refresh = FALSE, position = NA_integer_))
  }

  offset <- as.integer(iter_candidate - start_iter)
  position <- as.integer(offset %% cycle_len)
  hold_now <- position < hold_iters

  list(
    active = TRUE,
    hold = hold_now,
    refresh = !hold_now,
    position = position
  )
}
