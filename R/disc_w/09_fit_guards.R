disc_w_numeric_mean_all_finite <- function(x, positive_required = FALSE) {
  values <- suppressWarnings(as.numeric(x))
  if (!length(values) || any(!is.finite(values))) {
    return(NA_real_)
  }
  if (isTRUE(positive_required) && any(values <= 0)) {
    return(NA_real_)
  }
  mean(values)
}

disc_w_state_norm_sq_all_finite <- function(x) {
  values <- suppressWarnings(as.numeric(x))
  if (!length(values) || any(!is.finite(values))) {
    return(NA_real_)
  }
  sum(values^2)
}

disc_w_scalar_finite_or_default <- function(x, default = NA_real_) {
  value <- suppressWarnings(as.numeric(x))
  if (length(value) != 1L || !is.finite(value)) {
    return(default)
  }
  value
}

disc_w_fit_guard_fmt_num <- function(x, digits = 8L) {
  value <- suppressWarnings(as.numeric(x)[1L])
  if (!is.finite(value)) {
    return("NA")
  }
  format(signif(value, digits = as.integer(digits)), trim = TRUE, scientific = FALSE)
}

disc_w_iteration_guard_decision <- function(
  elbo,
  state_norm_sq,
  sigma_exp,
  gamma_exp,
  theta_update,
  gamsig_frozen_now,
  state_guard_enabled,
  iter,
  state_guard_start_iter,
  prev_state_norm_sq,
  state_norm_abs_cap,
  state_norm_max_ratio
) {
  iter <- suppressWarnings(as.integer(iter)[1L])
  state_guard_start_iter <- suppressWarnings(as.integer(state_guard_start_iter)[1L])
  if (!is.finite(iter)) iter <- 0L
  if (!is.finite(state_guard_start_iter)) state_guard_start_iter <- 0L

  active_for_state_growth <- isTRUE(state_guard_enabled) &&
    iter >= state_guard_start_iter

  state_growth_ratio <- NA_real_
  prev_state_norm_sq <- suppressWarnings(as.numeric(prev_state_norm_sq)[1L])
  state_norm_sq <- suppressWarnings(as.numeric(state_norm_sq)[1L])
  if (isTRUE(active_for_state_growth) &&
      isTRUE(theta_update) &&
      !isTRUE(gamsig_frozen_now) &&
      is.finite(prev_state_norm_sq) &&
      prev_state_norm_sq > 0 &&
      is.finite(state_norm_sq)) {
    state_growth_ratio <- state_norm_sq / prev_state_norm_sq
  }

  if (!isTRUE(theta_update)) {
    return(list(
      reason = NULL,
      state_guard_active = active_for_state_growth,
      state_growth_ratio = state_growth_ratio,
      finite_guard = FALSE
    ))
  }

  core_values <- c(
    elbo = suppressWarnings(as.numeric(elbo)[1L]),
    state_norm_sq = state_norm_sq,
    sigma_exp = suppressWarnings(as.numeric(sigma_exp)[1L]),
    gamma_exp = suppressWarnings(as.numeric(gamma_exp)[1L])
  )
  bad_core <- names(core_values)[!is.finite(core_values)]
  if (length(bad_core)) {
    return(list(
      reason = paste0("non-finite ", paste(bad_core, collapse = ",")),
      state_guard_active = active_for_state_growth,
      state_growth_ratio = state_growth_ratio,
      finite_guard = TRUE
    ))
  }

  state_norm_abs_cap <- suppressWarnings(as.numeric(state_norm_abs_cap)[1L])
  state_norm_max_ratio <- suppressWarnings(as.numeric(state_norm_max_ratio)[1L])
  if (is.finite(state_norm_abs_cap) && state_norm_sq > state_norm_abs_cap) {
    return(list(
      reason = sprintf(
        "state_norm_sq=%s exceeds abs_cap=%s",
        disc_w_fit_guard_fmt_num(state_norm_sq),
        disc_w_fit_guard_fmt_num(state_norm_abs_cap)
      ),
      state_guard_active = active_for_state_growth,
      state_growth_ratio = state_growth_ratio,
      finite_guard = FALSE
    ))
  }

  if (isTRUE(active_for_state_growth) && !isTRUE(gamsig_frozen_now)) {
    if (is.finite(state_growth_ratio) &&
        is.finite(state_norm_max_ratio) &&
        state_growth_ratio > state_norm_max_ratio) {
      return(list(
        reason = sprintf(
          "state_growth_ratio=%s exceeds max_ratio=%s",
          disc_w_fit_guard_fmt_num(state_growth_ratio),
          disc_w_fit_guard_fmt_num(state_norm_max_ratio)
        ),
        state_guard_active = active_for_state_growth,
        state_growth_ratio = state_growth_ratio,
        finite_guard = FALSE
      ))
    }
  }

  list(
    reason = NULL,
    state_guard_active = active_for_state_growth,
    state_growth_ratio = state_growth_ratio,
    finite_guard = FALSE
  )
}

disc_w_assert_finite_square_matrix <- function(M, label = "matrix") {
  M <- as.matrix(M)
  storage.mode(M) <- "double"
  if (!is.matrix(M) || nrow(M) < 1L || ncol(M) < 1L || nrow(M) != ncol(M)) {
    stop(sprintf("%s must be a non-empty square matrix", label), call. = FALSE)
  }
  bad_n <- sum(!is.finite(M))
  if (bad_n > 0L) {
    stop(
      sprintf(
        "%s contains non-finite entries before SPD projection (n=%d dim=%dx%d)",
        label,
        as.integer(bad_n),
        as.integer(nrow(M)),
        as.integer(ncol(M))
      ),
      call. = FALSE
    )
  }
  M
}

disc_w_guard_backoff_step_scale <- function(
  current_scale,
  backoff_factor,
  min_scale,
  enabled = TRUE
) {
  current_scale <- suppressWarnings(as.numeric(current_scale)[1L])
  backoff_factor <- suppressWarnings(as.numeric(backoff_factor)[1L])
  min_scale <- suppressWarnings(as.numeric(min_scale)[1L])

  if (!is.finite(current_scale) || current_scale <= 0 || current_scale > 1) {
    current_scale <- 1
  }
  if (!is.finite(backoff_factor) || backoff_factor <= 0 || backoff_factor >= 1) {
    backoff_factor <- 0.2
  }
  if (!is.finite(min_scale) || min_scale <= 0 || min_scale >= 1) {
    min_scale <- 0.05
  }
  if (!isTRUE(enabled)) {
    return(current_scale)
  }
  max(min_scale, current_scale * backoff_factor)
}

disc_w_guard_scaled_hold_iters <- function(
  base_iters,
  step_scale,
  min_iters = 1L,
  enabled = TRUE
) {
  base_iters <- suppressWarnings(as.integer(base_iters)[1L])
  step_scale <- suppressWarnings(as.numeric(step_scale)[1L])
  min_iters <- suppressWarnings(as.integer(min_iters)[1L])

  if (!is.finite(base_iters) || base_iters <= 0L) {
    return(0L)
  }
  if (!is.finite(min_iters) || min_iters < 0L) {
    min_iters <- 1L
  }
  if (!is.finite(step_scale) || step_scale <= 0 || step_scale > 1) {
    step_scale <- 1
  }
  if (!isTRUE(enabled)) {
    return(as.integer(base_iters))
  }
  as.integer(max(min_iters, ceiling(base_iters * step_scale)))
}

disc_w_effective_step_cap <- function(base_cap, step_scale) {
  base_cap <- suppressWarnings(as.numeric(base_cap)[1L])
  step_scale <- suppressWarnings(as.numeric(step_scale)[1L])
  if (!is.finite(base_cap) || base_cap <= 0) {
    return(NA_real_)
  }
  if (!is.finite(step_scale) || step_scale <= 0 || step_scale > 1) {
    step_scale <- 1
  }
  base_cap * step_scale
}

disc_w_reanchor_gamsig_to_gamma <- function(
  gamsig_out,
  gamma,
  p0,
  L,
  U,
  A_fn,
  B_fn,
  C_fn,
  source_indices = NULL,
  sigma_floor = 1e-12,
  status = "gamma_reanchored"
) {
  if (!is.list(gamsig_out)) {
    stop("gamsig_out must be a list", call. = FALSE)
  }
  required <- c(
    "E.gam",
    "E.sigma",
    "E.inv.sigma",
    "E.c2.invb.absgam2.sigma",
    "E.c.invb.absgam",
    "E.c.a.invb.absgam",
    "E.a2.invb.inv.sigma",
    "E.invb.inv.sigma",
    "E.a.invb.inv.sigma",
    "E.log.sig.b",
    "E.log.sig",
    "E.prior.sig.gam",
    "entrop"
  )
  missing <- required[!vapply(required, function(nm) !is.null(gamsig_out[[nm]]), logical(1))]
  if (length(missing)) {
    stop(sprintf("gamsig_out is missing required fields: %s", paste(missing, collapse = ",")), call. = FALSE)
  }
  if (!is.function(A_fn) || !is.function(B_fn) || !is.function(C_fn)) {
    stop("A_fn, B_fn, and C_fn must be functions", call. = FALSE)
  }

  gamma <- suppressWarnings(as.numeric(gamma)[1L])
  p0 <- suppressWarnings(as.numeric(p0)[1L])
  L <- suppressWarnings(as.numeric(L)[1L])
  U <- suppressWarnings(as.numeric(U)[1L])
  sigma_floor <- suppressWarnings(as.numeric(sigma_floor)[1L])
  if (!is.finite(gamma) || !is.finite(p0) || !is.finite(L) || !is.finite(U) || L >= U) {
    stop("gamma, p0, L, and U must be finite with L < U", call. = FALSE)
  }
  if (!is.finite(sigma_floor) || sigma_floor <= 0) {
    sigma_floor <- 1e-12
  }
  gamma <- pmin(pmax(gamma, L + 1e-12), U - 1e-12)

  sigma_mat <- as.matrix(gamsig_out$E.sigma)
  n_sources <- nrow(sigma_mat)
  if (!is.finite(n_sources) || n_sources < 1L) {
    stop("gamsig_out$E.sigma must have at least one source row", call. = FALSE)
  }
  if (is.null(source_indices)) {
    source_indices <- seq_len(n_sources)
  } else {
    source_indices <- suppressWarnings(as.integer(source_indices))
    if (!length(source_indices) ||
        any(!is.finite(source_indices)) ||
        any(source_indices < 1L) ||
        any(source_indices > n_sources)) {
      stop("source_indices must refer to valid gamsig source rows", call. = FALSE)
    }
  }

  a <- suppressWarnings(as.numeric(A_fn(p0, gamma))[1L])
  b <- suppressWarnings(as.numeric(B_fn(p0, gamma))[1L])
  c <- suppressWarnings(as.numeric(C_fn(p0, gamma))[1L])
  if (!is.finite(a) || !is.finite(b) || b <= 0 || !is.finite(c)) {
    stop("gamma anchor produced non-finite A/B/C moments", call. = FALSE)
  }

  out <- gamsig_out
  for (idx in source_indices) {
    sigma <- suppressWarnings(as.numeric(out$E.sigma[idx, ]))
    sigma[!is.finite(sigma) | sigma <= sigma_floor] <- sigma_floor

    out$E.gam[idx, ] <- gamma
    out$E.sigma[idx, ] <- sigma
    out$E.inv.sigma[idx, ] <- 1 / sigma
    out$E.c2.invb.absgam2.sigma[idx, ] <- c^2 * sigma * abs(gamma)^2 / b
    out$E.c.invb.absgam[idx, ] <- c * abs(gamma) / b
    out$E.c.a.invb.absgam[idx, ] <- c * abs(gamma) * a / b
    out$E.a2.invb.inv.sigma[idx, ] <- a^2 / (sigma * b)
    out$E.invb.inv.sigma[idx, ] <- 1 / (sigma * b)
    out$E.a.invb.inv.sigma[idx, ] <- a / (sigma * b)
    out$E.log.sig.b[idx, ] <- log(sigma * b)
    out$E.log.sig[idx, ] <- log(sigma)
    out$E.prior.sig.gam[idx, ] <- 0
    out$entrop[idx, ] <- 0
  }

  values <- suppressWarnings(as.numeric(unlist(out[required], use.names = FALSE)))
  if (!length(values) || any(!is.finite(values))) {
    stop(sprintf("%s produced non-finite gamma/sigma moments", status), call. = FALSE)
  }
  if (any(suppressWarnings(as.numeric(out$E.sigma[source_indices, ])) <= 0)) {
    stop(sprintf("%s produced non-positive sigma", status), call. = FALSE)
  }

  out$state_guard_reanchored <- TRUE
  out$state_guard_reanchor_status <- as.character(status)[1L]
  out$state_guard_reanchor_gamma <- gamma
  out
}
