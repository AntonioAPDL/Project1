disc_w_ens_spec <- function() {
  list(
    version = 1L,
    object = "disc_w_ensemble",
    axes = c("time", "member"),
    ordering = c("time", "member"),
    element_type = "numeric_matrix_like",
    container = "list_of_matrix_like",
    notes = c(
      "Canonical ensemble representation for DISC Wishart/ensemble workflow.",
      "Each ensemble j is matrix-like (matrix or data.frame of numeric columns) with rows = time/lead index, cols = member index.",
      "The list index j preserves the original ordering used by the script (e.g., 1=glofas, 2=nws)."
    )
  )
}

disc_w_validate_ensemble <- function(E, spec = disc_w_ens_spec(), strict = TRUE) {
  if (!isTRUE(strict)) {
    return(invisible(TRUE))
  }

  if (!is.list(spec) || !identical(spec$object, "disc_w_ensemble")) {
    stop("Invalid ensemble spec: expected spec$object == 'disc_w_ensemble'.", call. = FALSE)
  }

  if (!is.list(E) || !identical(E$type, "disc_w_ensemble")) {
    stop("Invalid ensemble object: expected list(type='disc_w_ensemble', ...).", call. = FALSE)
  }

  if (!is.list(E$data) || length(E$data) < 1) {
    stop("Ensemble E$data must be a non-empty list of matrix-like objects.", call. = FALSE)
  }

  J <- length(E$data)
  if (!is.numeric(E$J) || length(E$J) != 1 || as.integer(E$J) != J) {
    stop("Ensemble E$J must match length(E$data).", call. = FALSE)
  }

  if (!is.numeric(E$num_mem) || length(E$num_mem) != J) {
    stop("Ensemble E$num_mem must be numeric length J.", call. = FALSE)
  }
  if (!is.numeric(E$ranges) || length(E$ranges) != J) {
    stop("Ensemble E$ranges must be numeric length J.", call. = FALSE)
  }

  for (j in seq_len(J)) {
    mj <- E$data[[j]]
    if (!is.matrix(mj) && !is.data.frame(mj)) {
      stop(sprintf("Ensemble E$data[[%d]] must be matrix-like.", j), call. = FALSE)
    }
    if (is.data.frame(mj) && !all(vapply(mj, is.numeric, logical(1)))) {
      stop(sprintf("Ensemble E$data[[%d]] must have numeric columns.", j), call. = FALSE)
    }
    if (is.matrix(mj) && !is.numeric(mj)) {
      stop(sprintf("Ensemble E$data[[%d]] must be numeric.", j), call. = FALSE)
    }
    d <- dim(mj)
    if (length(d) != 2L || any(is.na(d)) || any(d < 0)) {
      stop(sprintf("Ensemble E$data[[%d]] has invalid dimensions.", j), call. = FALSE)
    }
    if (as.integer(E$ranges[j]) != d[1]) {
      stop(sprintf("Ensemble E$ranges[%d] must equal nrow(E$data[[%d]]).", j, j), call. = FALSE)
    }
    if (as.integer(E$num_mem[j]) != d[2]) {
      stop(sprintf("Ensemble E$num_mem[%d] must equal ncol(E$data[[%d]]).", j, j), call. = FALSE)
    }
  }

  invisible(TRUE)
}

disc_w_as_ensemble <- function(x, spec = disc_w_ens_spec(), strict = TRUE) {
  if (is.list(x) && identical(x$type, "disc_w_ensemble")) {
    disc_w_validate_ensemble(x, spec = spec, strict = strict)
    return(x)
  }

  if (is.matrix(x) || is.data.frame(x)) {
    x <- list(x)
  }

  if (!is.list(x) || length(x) < 1) {
    stop("Cannot convert to ensemble: expected a matrix-like object or list of matrix-like objects.", call. = FALSE)
  }

  J <- length(x)
  num_mem <- rep(NA_real_, J)
  ranges <- rep(NA_real_, J)
  for (j in seq_len(J)) {
    mj <- x[[j]]
    if (!is.matrix(mj) && !is.data.frame(mj)) {
      stop(sprintf("Cannot convert to ensemble: element %d is not matrix-like.", j), call. = FALSE)
    }
    if (is.data.frame(mj) && !all(vapply(mj, is.numeric, logical(1)))) {
      stop(sprintf("Cannot convert to ensemble: element %d must have numeric columns.", j), call. = FALSE)
    }
    if (is.matrix(mj) && !is.numeric(mj)) {
      stop(sprintf("Cannot convert to ensemble: element %d matrix is not numeric.", j), call. = FALSE)
    }
    num_mem[j] <- dim(mj)[2]
    ranges[j] <- dim(mj)[1]
  }

  E <- list(
    type = "disc_w_ensemble",
    spec_version = spec$version,
    data = x,
    J = J,
    num_mem = num_mem,
    ranges = ranges
  )

  disc_w_validate_ensemble(E, spec = spec, strict = strict)
  E
}
