disc_w_sampling_log <- function(msg) {
  log_enabled <- get0("DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES", ifnotfound = FALSE, inherits = TRUE)
  if (isTRUE(log_enabled)) {
    cat(sprintf("[sampling_contract] %s\n", msg))
    flush.console()
  }
}

disc_w_coerce_sampling_matrix <- function(x, nrow_expected = NA_integer_, ncol_expected = NA_integer_, label = "sm") {
  expected_nrow <- suppressWarnings(as.integer(nrow_expected))
  expected_ncol <- suppressWarnings(as.integer(ncol_expected))
  dims <- dim(x)
  coerced <- FALSE

  if (is.null(dims)) {
    if (!is.finite(expected_nrow) || !is.finite(expected_ncol)) {
      stop(sprintf("%s has no dim attribute and expected dims are unavailable", label), call. = FALSE)
    }
    expected_size <- as.integer(expected_nrow * expected_ncol)
    if (length(x) != expected_size) {
      stop(sprintf(
        "%s length mismatch: expected %d values for %dx%d matrix, got %d",
        label,
        expected_size,
        expected_nrow,
        expected_ncol,
        as.integer(length(x))
      ), call. = FALSE)
    }
    x <- matrix(as.numeric(x), nrow = expected_nrow, ncol = expected_ncol)
    coerced <- TRUE
  } else if (length(dims) != 2L) {
    stop(sprintf("%s must be 2D or vector-like; got dim length=%d", label, as.integer(length(dims))), call. = FALSE)
  } else {
    x <- as.matrix(x)
  }

  storage.mode(x) <- "double"
  if (is.finite(expected_nrow) && nrow(x) != expected_nrow) {
    stop(sprintf("%s row mismatch: expected=%d got=%d", label, expected_nrow, nrow(x)), call. = FALSE)
  }
  if (is.finite(expected_ncol) && ncol(x) != expected_ncol) {
    stop(sprintf("%s col mismatch: expected=%d got=%d", label, expected_ncol, ncol(x)), call. = FALSE)
  }
  if (any(!is.finite(x))) {
    stop(sprintf("%s contains non-finite values", label), call. = FALSE)
  }
  if (coerced) {
    disc_w_sampling_log(sprintf(
      "%s coerced to matrix with dims=%dx%d",
      label,
      as.integer(nrow(x)),
      as.integer(ncol(x))
    ))
  }
  x
}

disc_w_coerce_sampling_cube <- function(x, n_expected = NA_integer_, TT_expected = NA_integer_, label = "sC") {
  expected_n <- suppressWarnings(as.integer(n_expected))
  expected_TT <- suppressWarnings(as.integer(TT_expected))
  dims <- dim(x)
  coerced <- FALSE

  if (is.null(dims)) {
    if (!is.finite(expected_n) || !is.finite(expected_TT)) {
      stop(sprintf("%s has no dim attribute and expected dims are unavailable", label), call. = FALSE)
    }
    expected_size <- as.integer(expected_n * expected_n * expected_TT)
    if (length(x) != expected_size) {
      stop(sprintf(
        "%s length mismatch: expected %d values for %dx%dx%d cube, got %d",
        label,
        expected_size,
        expected_n,
        expected_n,
        expected_TT,
        as.integer(length(x))
      ), call. = FALSE)
    }
    x <- array(as.numeric(x), dim = c(expected_n, expected_n, expected_TT))
    coerced <- TRUE
  } else if (length(dims) == 2L) {
    if (!is.finite(expected_n)) {
      expected_n <- suppressWarnings(as.integer(dims[[1L]]))
    }
    if (!is.finite(expected_TT)) {
      expected_TT <- 1L
    }
    if (dims[[1L]] != dims[[2L]]) {
      stop(sprintf("%s 2D fallback requires square matrix; got %dx%d", label, dims[[1L]], dims[[2L]]), call. = FALSE)
    }
    if (is.finite(expected_n) && dims[[1L]] != expected_n) {
      stop(sprintf("%s row mismatch in 2D fallback: expected=%d got=%d", label, expected_n, dims[[1L]]), call. = FALSE)
    }
    if (expected_TT != 1L) {
      stop(sprintf("%s 2D fallback only valid for TT=1; got TT=%d", label, expected_TT), call. = FALSE)
    }
    x <- array(as.numeric(x), dim = c(dims[[1L]], dims[[2L]], 1L))
    coerced <- TRUE
  } else if (length(dims) != 3L) {
    stop(sprintf("%s must be 3D or vector-like; got dim length=%d", label, as.integer(length(dims))), call. = FALSE)
  } else {
    x <- as.array(x)
  }

  storage.mode(x) <- "double"
  dims <- dim(x)
  if (dims[[1L]] != dims[[2L]]) {
    stop(sprintf("%s must be square in the first two dims; got %dx%d", label, dims[[1L]], dims[[2L]]), call. = FALSE)
  }
  if (is.finite(expected_n) && dims[[1L]] != expected_n) {
    stop(sprintf("%s dim-1 mismatch: expected=%d got=%d", label, expected_n, dims[[1L]]), call. = FALSE)
  }
  if (is.finite(expected_TT) && dims[[3L]] != expected_TT) {
    stop(sprintf("%s dim-3 mismatch: expected=%d got=%d", label, expected_TT, dims[[3L]]), call. = FALSE)
  }
  if (any(!is.finite(x))) {
    stop(sprintf("%s contains non-finite values", label), call. = FALSE)
  }
  if (coerced) {
    disc_w_sampling_log(sprintf(
      "%s coerced to cube with dims=%dx%dx%d",
      label,
      as.integer(dims[[1L]]),
      as.integer(dims[[2L]]),
      as.integer(dims[[3L]])
    ))
  }
  x
}

disc_w_prepare_sampling_state <- function(sm, sC, TT_expected = NA_integer_, n_expected = NA_integer_, label = "sampling_state") {
  dims_sm <- dim(sm)
  dims_sC <- dim(sC)
  inferred_TT <- suppressWarnings(as.integer(TT_expected))
  inferred_n <- suppressWarnings(as.integer(n_expected))

  if (!is.finite(inferred_TT)) {
    if (!is.null(dims_sm) && length(dims_sm) >= 2L) {
      inferred_TT <- suppressWarnings(as.integer(dims_sm[[2L]]))
    } else if (!is.null(dims_sC) && length(dims_sC) >= 3L) {
      inferred_TT <- suppressWarnings(as.integer(dims_sC[[3L]]))
    }
  }
  if (!is.finite(inferred_n)) {
    if (!is.null(dims_sm) && length(dims_sm) >= 1L) {
      inferred_n <- suppressWarnings(as.integer(dims_sm[[1L]]))
    } else if (!is.null(dims_sC) && length(dims_sC) >= 2L) {
      inferred_n <- suppressWarnings(as.integer(dims_sC[[1L]]))
    } else if (is.finite(inferred_TT) && inferred_TT > 0L && is.null(dims_sm)) {
      inferred_n <- suppressWarnings(as.integer(length(sm) / inferred_TT))
    }
  }

  if (!is.finite(inferred_n) || inferred_n <= 0L) {
    stop(sprintf("%s: unable to infer positive state dimension", label), call. = FALSE)
  }
  if (!is.finite(inferred_TT) || inferred_TT <= 0L) {
    stop(sprintf("%s: unable to infer positive horizon length", label), call. = FALSE)
  }

  sm_matrix <- disc_w_coerce_sampling_matrix(
    sm,
    nrow_expected = inferred_n,
    ncol_expected = inferred_TT,
    label = sprintf("%s$sm", label)
  )
  sC_cube <- disc_w_coerce_sampling_cube(
    sC,
    n_expected = inferred_n,
    TT_expected = inferred_TT,
    label = sprintf("%s$sC", label)
  )

  list(
    sm = sm_matrix,
    sC = sC_cube,
    n = as.integer(inferred_n),
    TT = as.integer(inferred_TT)
  )
}
