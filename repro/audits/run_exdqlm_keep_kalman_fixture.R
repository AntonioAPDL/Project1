#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
out_dir <- if (length(args) >= 1L) {
  args[[1L]]
} else {
  file.path("reports", "exdqlm_multivar_keep_kalman_fixture_20260520")
}
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

Sys.setenv(
  PKG_CXXFLAGS = "-I/data/muscat_data/jaguir26/libs/eigen -I/data/muscat_data/jaguir26/libs/boost/include -DEIGEN_DONT_VECTORIZE",
  PKG_LIBS = "-L/data/muscat_data/jaguir26/libs/lib64 -L/data/muscat_data/jaguir26/libs/boost/lib -llapack -lblas -lboost_random -lboost_system -fopenmp",
  LD_LIBRARY_PATH = "/data/muscat_data/jaguir26/libs/lib64:/data/muscat_data/jaguir26/libs/boost/lib:/lib64"
)

if (!requireNamespace("Rcpp", quietly = TRUE)) {
  stop("Rcpp is required for the Kalman fixture", call. = FALSE)
}

Rcpp::sourceCpp("DISC_kalman_synth_transfer_forecast.cpp")

sym <- function(M) 0.5 * (M + t(M))

regularize <- function(M, eps = 1e-15) {
  M <- sym(as.matrix(M))
  M + diag(eps, nrow(M))
}

safe_solve <- function(M) {
  solve(regularize(M, 1e-12))
}

head_tail_indices <- function(full_dim, core_dim, tail_dim) {
  if (core_dim + tail_dim > full_dim) stop("invalid head/tail dimensions", call. = FALSE)
  c(seq_len(core_dim), if (tail_dim > 0L) seq.int(full_dim - tail_dim + 1L, full_dim) else integer(0))
}

project_state_head_tail <- function(x, core_dim, tail_dim) {
  x[head_tail_indices(length(x), core_dim, tail_dim)]
}

project_cov_head_tail <- function(M, core_dim, tail_dim) {
  idx <- head_tail_indices(nrow(M), core_dim, tail_dim)
  M[idx, idx, drop = FALSE]
}

get_transition_slice <- function(x, step) {
  d <- dim(x)
  if (length(d) == 2L) return(as.matrix(x))
  if (length(d) != 3L) stop("transition must be a matrix or cube", call. = FALSE)
  use_step <- min(max(1L, as.integer(step)), d[[3L]])
  as.matrix(x[, , use_step, drop = TRUE])
}

expand_matrix <- function(product, num_mem) {
  product <- as.matrix(product)
  num_mem <- as.integer(num_mem)
  out <- matrix(0, nrow = sum(num_mem), ncol = sum(num_mem))
  row_start <- 1L
  for (i in seq_along(num_mem)) {
    col_start <- 1L
    for (j in seq_along(num_mem)) {
      out[
        row_start:(row_start + num_mem[[i]] - 1L),
        col_start:(col_start + num_mem[[j]] - 1L)
      ] <- product[[i, j]]
      col_start <- col_start + num_mem[[j]]
    }
    row_start <- row_start + num_mem[[i]]
  }
  out
}

expand_FF <- function(FF_slice, num_mem) {
  FF_slice <- as.matrix(FF_slice)
  num_mem <- as.integer(num_mem)
  out <- matrix(0, nrow = nrow(FF_slice), ncol = sum(num_mem))
  col_start <- 1L
  for (j in seq_along(num_mem)) {
    out[, col_start:(col_start + num_mem[[j]] - 1L)] <- FF_slice[, j, drop = FALSE]
    col_start <- col_start + num_mem[[j]]
  }
  out
}

repeat_vector <- function(x, num_mem) {
  rep(as.numeric(x), times = as.integer(num_mem))
}

filter_update <- function(a, P, FF_slice, ex_f, ex_q, y_obs) {
  R <- regularize(P)
  f <- drop(t(FF_slice) %*% a) + as.numeric(ex_f)
  q <- sym(t(FF_slice) %*% R %*% FF_slice + ex_q)
  q_inv <- safe_solve(q)
  innov <- as.numeric(y_obs) - f
  list(
    m = drop(a + R %*% FF_slice %*% q_inv %*% innov),
    C = sym(R - R %*% FF_slice %*% q_inv %*% t(FF_slice) %*% t(R))
  )
}

reference_history_filter <- function(GG, m0, C0, ex_f, ex_q, FF, y, ex_df_mat, Ones, TT) {
  n <- length(m0)
  m <- matrix(0, n, TT)
  C <- array(0, c(n, n, TT))

  for (tt in seq_len(TT)) {
    if (tt == 1L) {
      a <- GG[, , tt] %*% m0
      P0 <- GG[, , tt] %*% C0 %*% t(GG[, , tt])
      R <- P0 + ex_df_mat * P0
    } else {
      a <- GG[, , tt] %*% m[, tt - 1L]
      P0 <- GG[, , tt] %*% C[, , tt - 1L] %*% t(GG[, , tt])
      R <- P0 * ex_df_mat + P0 * Ones
    }
    upd <- filter_update(
      a = drop(a),
      P = R,
      FF_slice = FF[, , tt],
      ex_f = ex_f[, tt],
      ex_q = ex_q[, , tt],
      y_obs = y[, tt]
    )
    m[, tt] <- upd$m
    C[, , tt] <- upd$C
  }
  list(fm = m, fC = C)
}

reference_forecast_filter <- function(hist, fixture) {
  p <- fixture$p
  J <- fixture$J
  ppx <- fixture$ppx
  k_ens <- fixture$k_ens
  num_mem <- fixture$num_mem
  TT <- fixture$TT

  m_ens <- vector("list", J)
  C_ens <- vector("list", J)

  for (j in J:1) {
    idx <- J - j + 1L
    state_dim <- p * (j + 1L) + ppx
    sub_num_mem <- num_mem[seq_len(j)]
    k_j <- if (j < J) k_ens[[j]] - k_ens[[j + 1L]] else k_ens[[j]]

    m_ens[[idx]] <- array(0, dim = c(state_dim, 1L, k_j))
    C_ens[[idx]] <- array(0, dim = c(state_dim, state_dim, k_j))

    for (kk in seq_len(k_j)) {
      G <- get_transition_slice(fixture$GG_list[[idx]], kk)
      W <- fixture$W_list[[idx]][, , kk, drop = TRUE]
      if (kk == 1L) {
        if (j == J) {
          prev_m <- project_state_head_tail(hist$fm[, TT], p * (j + 1L), ppx)
          prev_C <- project_cov_head_tail(hist$fC[, , TT], p * (j + 1L), ppx)
        } else {
          prev_idx <- idx - 1L
          prev_last <- dim(m_ens[[prev_idx]])[[3L]]
          prev_m <- project_state_head_tail(m_ens[[prev_idx]][, 1L, prev_last], p * (j + 1L), ppx)
          prev_C <- project_cov_head_tail(C_ens[[prev_idx]][, , prev_last], p * (j + 1L), ppx)
        }
      } else {
        prev_m <- m_ens[[idx]][, 1L, kk - 1L]
        prev_C <- C_ens[[idx]][, , kk - 1L]
      }

      a <- drop(G %*% prev_m)
      P <- G %*% prev_C %*% t(G) + W
      FF_slice <- fixture$FF_list[[idx]]
      f_base <- repeat_vector(drop(t(FF_slice) %*% a), sub_num_mem)
      q_base <- expand_matrix(t(FF_slice) %*% P %*% FF_slice, sub_num_mem)
      expanded_FF <- expand_FF(FF_slice, sub_num_mem)
      upd <- filter_update(
        a = a,
        P = P,
        FF_slice = expanded_FF,
        ex_f = fixture$ex_f_list[[idx]][, kk],
        ex_q = q_base * 0 + fixture$ex_q_list[[idx]][, , kk],
        y_obs = fixture$y_list[[idx]][, kk] - f_base + drop(t(expanded_FF) %*% a)
      )
      m_ens[[idx]][, 1L, kk] <- upd$m
      C_ens[[idx]][, , kk] <- upd$C
    }
  }

  list(fm_ens = m_ens, fC_ens = C_ens)
}

reference_forecast_smoother <- function(fore, fixture) {
  p <- fixture$p
  J <- fixture$J
  ppx <- fixture$ppx
  k_ens <- fixture$k_ens

  sm_ens <- fore$fm_ens
  sC_ens <- fore$fC_ens

  k_seed <- if (J > 1L) k_ens[[1L]] - k_ens[[2L]] else k_ens[[1L]]
  sm_ens[[J]][, 1L, k_seed] <- fore$fm_ens[[J]][, 1L, k_seed]
  sC_ens[[J]][, , k_seed] <- fore$fC_ens[[J]][, , k_seed]

  for (j0 in 0:(J - 1L)) {
    k_j <- if (j0 == (J - 1L)) k_ens[[j0 + 1L]] else k_ens[[j0 + 1L]] - k_ens[[j0 + 2L]]
    idx <- J - j0
    state_dim_cur <- p * (j0 + 2L) + ppx

    if (idx < J) {
      state_dim_next <- p * (j0 + 1L) + ppx
      G <- get_transition_slice(fixture$GG_list[[idx + 1L]], k_j + 1L)
      W <- fixture$W_list[[idx + 1L]][, , k_j + 1L, drop = TRUE]
      prev_m <- project_state_head_tail(fore$fm_ens[[idx]][, 1L, k_j], p * (j0 + 1L), ppx)
      prev_C <- project_cov_head_tail(fore$fC_ens[[idx]][, , k_j], p * (j0 + 1L), ppx)
      a <- drop(G %*% prev_m)
      P <- G %*% prev_C %*% t(G)
      R <- regularize(W + P)
      R_inv <- safe_solve(R)
      cols <- head_tail_indices(state_dim_cur, p * (j0 + 1L), ppx)
      sB <- fore$fC_ens[[idx]][, , k_j] %*% diag(state_dim_cur)[, cols, drop = FALSE] %*% t(G) %*% R_inv
      sm_next <- sm_ens[[idx + 1L]][, 1L, 1L]
      sC_next <- sC_ens[[idx + 1L]][, , 1L]
      sm_ens[[idx]][, 1L, k_j] <- fore$fm_ens[[idx]][, 1L, k_j] + drop(sB %*% (sm_next - a))
      sC_ens[[idx]][, , k_j] <- sym(fore$fC_ens[[idx]][, , k_j] + sB %*% (sC_next - R) %*% t(sB))
    }

    if (k_j > 1L) {
      for (kk in seq.int(k_j - 1L, 1L)) {
        G <- get_transition_slice(fixture$GG_list[[idx]], kk + 1L)
        W <- fixture$W_list[[idx]][, , kk + 1L, drop = TRUE]
        a <- drop(G %*% fore$fm_ens[[idx]][, 1L, kk])
        P <- G %*% fore$fC_ens[[idx]][, , kk] %*% t(G)
        R <- regularize(W + P)
        sB <- fore$fC_ens[[idx]][, , kk] %*% t(G) %*% safe_solve(R)
        sm_ens[[idx]][, 1L, kk] <- fore$fm_ens[[idx]][, 1L, kk] +
          drop(sB %*% (sm_ens[[idx]][, 1L, kk + 1L] - a))
        sC_ens[[idx]][, , kk] <- sym(fore$fC_ens[[idx]][, , kk] +
          sB %*% (sC_ens[[idx]][, , kk + 1L] - R) %*% t(sB))
      }
    }
  }

  list(sm_ens = sm_ens, sC_ens = sC_ens)
}

reference_history_smoother <- function(hist, fore_smooth, fixture) {
  p <- fixture$p
  J <- fixture$J
  ppx <- fixture$ppx
  TT <- fixture$TT
  full_core <- p * (J + 1L)
  full_dim <- full_core + ppx

  sm <- hist$fm
  sC <- hist$fC

  G_bridge <- get_transition_slice(fixture$GG_list[[1L]], 1L)
  W_bridge <- fixture$W_list[[1L]][, , 1L, drop = TRUE]
  prev_m <- project_state_head_tail(hist$fm[, TT], full_core, ppx)
  prev_C <- project_cov_head_tail(hist$fC[, , TT], full_core, ppx)
  a <- drop(G_bridge %*% prev_m)
  P <- G_bridge %*% prev_C %*% t(G_bridge)
  R <- regularize(W_bridge + P)
  idx_bridge <- head_tail_indices(full_dim, full_core, ppx)
  sB <- hist$fC[, , TT] %*% diag(full_dim)[, idx_bridge, drop = FALSE] %*% t(G_bridge) %*% safe_solve(R)
  sm[, TT] <- hist$fm[, TT] + drop(sB %*% (fore_smooth$sm_ens[[1L]][, 1L, 1L] - a))
  sC[, , TT] <- sym(hist$fC[, , TT] + sB %*% (fore_smooth$sC_ens[[1L]][, , 1L] - R) %*% t(sB))

  if (TT > 1L) {
    for (tt in seq.int(TT - 1L, 1L)) {
      G <- fixture$GG[, , tt + 1L]
      a <- drop(G %*% hist$fm[, tt])
      P <- G %*% hist$fC[, , tt] %*% t(G)
      R <- regularize(P * fixture$ex_df_mat + P * fixture$Ones)
      sB <- hist$fC[, , tt] %*% t(G) %*% safe_solve(R)
      sm[, tt] <- hist$fm[, tt] + drop(sB %*% (sm[, tt + 1L] - a))
      sC[, , tt] <- sym(hist$fC[, , tt] + sB %*% (sC[, , tt + 1L] - R) %*% t(sB))
    }
  }

  list(sm = sm, sC = sC)
}

make_spd_cube <- function(diag_values, n_slices, offdiag = 0) {
  n <- length(diag_values)
  out <- array(0, dim = c(n, n, n_slices))
  for (i in seq_len(n_slices)) {
    M <- diag(diag_values + i * 0.01, n)
    if (offdiag != 0 && n > 1L) {
      M[upper.tri(M)] <- offdiag
      M[lower.tri(M)] <- offdiag
    }
    out[, , i] <- regularize(M, 1e-8)
  }
  out
}

build_fixture <- function() {
  p <- 1L
  J <- 2L
  ppx <- 1L
  TT <- 3L
  k_ens <- c(5, 2)
  num_mem <- c(2, 1)
  full_dim <- p * (J + 1L) + ppx

  GG <- array(0, c(full_dim, full_dim, TT))
  for (tt in seq_len(TT)) {
    GG[, , tt] <- matrix(c(
      1.00, 0.04, 0.02, 0.00,
      0.00, 0.92, 0.01, 0.00,
      0.00, 0.02, 0.89, 0.00,
      0.03, 0.00, 0.00, 0.95
    ), nrow = full_dim, byrow = TRUE)
    GG[, , tt] <- GG[, , tt] + diag(0.002 * tt, full_dim)
  }

  FF <- array(0, c(full_dim, J + 1L, TT))
  for (tt in seq_len(TT)) {
    FF[, , tt] <- matrix(c(
      1.0, 0.9, 1.1,
      0.0, 1.0, 0.1,
      0.0, 0.2, 1.0,
      1.0, 1.0, 1.0
    ), nrow = full_dim, byrow = FALSE)
    FF[1L, , tt] <- FF[1L, , tt] + 0.01 * tt
  }

  list(
    p = p,
    J = J,
    ppx = ppx,
    TT = TT,
    k = max(k_ens),
    dM = 0L,
    k_ens = k_ens,
    num_mem = num_mem,
    GG = GG,
    m0 = c(0.10, -0.05, 0.08, 0.02),
    C0 = diag(c(0.7, 0.5, 0.45, 0.35)),
    ex_f = matrix(c(0.02, -0.01, 0.03, 0.00, 0.02, -0.02, 0.01, 0.00, 0.02), nrow = J + 1L),
    ex_q = make_spd_cube(c(0.35, 0.40, 0.45), TT, offdiag = 0.015),
    FF = FF,
    y = matrix(c(0.8, 0.6, 0.7, 0.9, 0.65, 0.72, 0.95, 0.66, 0.75), nrow = J + 1L),
    ex_df_mat = diag(c(0.06, 0.05, 0.05, 0.04)),
    ex_df_mat_k = diag(c(0.04, 0.04, 0.04, 0.03)),
    Ones = matrix(1, full_dim, full_dim),
    GG_list = list(
      array(c(
        0.98, 0.03, 0.02, 0.00,
        0.00, 0.91, 0.01, 0.00,
        0.00, 0.01, 0.88, 0.00,
        0.02, 0.00, 0.00, 0.96,
        0.99, 0.04, 0.01, 0.00,
        0.00, 0.90, 0.02, 0.00,
        0.00, 0.02, 0.87, 0.00,
        0.03, 0.00, 0.00, 0.95
      ), dim = c(full_dim, full_dim, 2L)),
      array(c(
        0.97, 0.05, 0.00,
        0.00, 0.90, 0.00,
        0.02, 0.00, 0.94,
        0.98, 0.04, 0.00,
        0.00, 0.89, 0.00,
        0.03, 0.00, 0.93,
        0.99, 0.03, 0.00,
        0.00, 0.88, 0.00,
        0.04, 0.00, 0.92
      ), dim = c(3L, 3L, 3L))
    ),
    FF_list = list(
      matrix(c(1, 1, 0, 1, 1, 0, 1, 1), nrow = full_dim, ncol = 2L),
      matrix(c(1, 1, 1), nrow = 3L, ncol = 1L)
    ),
    ex_f_list = list(
      matrix(c(0.02, -0.01, 0.00, 0.01, -0.02, 0.03), nrow = sum(num_mem), ncol = 2L),
      matrix(c(0.01, -0.02, 0.00, 0.01, -0.01, 0.02), nrow = num_mem[[1L]], ncol = 3L)
    ),
    ex_q_list = list(
      make_spd_cube(c(0.25, 0.27, 0.30), 2L, offdiag = 0.01),
      make_spd_cube(c(0.22, 0.24), 3L, offdiag = 0.008)
    ),
    ex_df_mat_list = array(0, c(full_dim, full_dim, 2L)),
    ex_df_mat_k_list = array(0, c(full_dim, full_dim, 1L)),
    y_list = list(
      matrix(c(1.1, 1.0, 0.9, 1.2, 1.05, 0.95), nrow = sum(num_mem), ncol = 2L),
      matrix(c(1.25, 1.1, 1.28, 1.12, 1.30, 1.15), nrow = num_mem[[1L]], ncol = 3L)
    ),
    Ones_ens = matrix(1, full_dim, full_dim),
    W_list = list(
      make_spd_cube(c(0.12, 0.10, 0.09, 0.08), 2L, offdiag = 0.004),
      make_spd_cube(c(0.11, 0.09, 0.07), 3L, offdiag = 0.003)
    ),
    forecast_cov_epsilon = 1e-6
  )
}

max_abs_diff_list <- function(a, b) {
  max(vapply(seq_along(a), function(i) max(abs(a[[i]] - b[[i]])), numeric(1)))
}

max_slice_asymmetry <- function(x) {
  d <- dim(x)
  if (length(d) == 2L) {
    return(max(abs(x - t(x))))
  }
  if (length(d) == 3L) {
    return(max(vapply(seq_len(d[[3L]]), function(i) max(abs(x[, , i] - t(x[, , i]))), numeric(1))))
  }
  stop("expected matrix or 3D array for symmetry check", call. = FALSE)
}

min_slice_eigen <- function(x) {
  d <- dim(x)
  if (length(d) == 2L) {
    return(min(eigen(sym(x), symmetric = TRUE, only.values = TRUE)$values))
  }
  if (length(d) == 3L) {
    return(min(vapply(seq_len(d[[3L]]), function(i) {
      min(eigen(sym(x[, , i]), symmetric = TRUE, only.values = TRUE)$values)
    }, numeric(1))))
  }
  stop("expected matrix or 3D array for eigen check", call. = FALSE)
}

fixture <- build_fixture()

cpp <- DISC_update_theta_synth_cpp_W(
  fixture$GG,
  fixture$m0,
  fixture$C0,
  fixture$ex_f,
  fixture$ex_q,
  fixture$FF,
  fixture$y,
  fixture$ex_df_mat,
  fixture$ex_df_mat_k,
  fixture$Ones,
  fixture$p,
  fixture$J,
  fixture$ppx,
  fixture$TT,
  fixture$k,
  fixture$dM,
  fixture$GG_list,
  fixture$FF_list,
  fixture$ex_f_list,
  fixture$ex_q_list,
  fixture$ex_df_mat_list,
  fixture$ex_df_mat_k_list,
  fixture$y_list,
  fixture$k_ens,
  fixture$Ones_ens,
  sum(fixture$num_mem),
  fixture$num_mem,
  fixture$W_list,
  fixture$forecast_cov_epsilon
)

ref_hist <- reference_history_filter(
  fixture$GG,
  fixture$m0,
  fixture$C0,
  fixture$ex_f,
  fixture$ex_q,
  fixture$FF,
  fixture$y,
  fixture$ex_df_mat,
  fixture$Ones,
  fixture$TT
)
ref_fore <- reference_forecast_filter(ref_hist, fixture)
ref_fore_smooth <- reference_forecast_smoother(ref_fore, fixture)
ref_hist_smooth <- reference_history_smoother(ref_hist, ref_fore_smooth, fixture)

coerce_like <- function(x, template) {
  if (!is.null(dim(x))) return(x)
  array(as.numeric(x), dim = dim(template))
}

cpp$fm_ens <- Map(coerce_like, cpp$fm_ens, ref_fore$fm_ens)
cpp$fC_ens <- Map(coerce_like, cpp$fC_ens, ref_fore$fC_ens)
cpp$sm_ens <- Map(coerce_like, cpp$sm_ens, ref_fore_smooth$sm_ens)
cpp$sC_ens <- Map(coerce_like, cpp$sC_ens, ref_fore_smooth$sC_ens)

checks <- data.frame(
  check = c(
    "historical_filtered_mean_max_abs_diff",
    "historical_filtered_cov_max_abs_diff",
    "historical_smoothed_mean_max_abs_diff",
    "historical_smoothed_cov_max_abs_diff",
    "forecast_filtered_mean_max_abs_diff",
    "forecast_filtered_cov_max_abs_diff",
    "forecast_smoothed_mean_max_abs_diff",
    "forecast_smoothed_cov_max_abs_diff",
    "historical_filtered_cov_symmetry_cpp",
    "historical_smoothed_cov_symmetry_cpp",
    "forecast_filtered_cov_symmetry_cpp",
    "forecast_smoothed_cov_symmetry_cpp",
    "historical_filtered_cov_min_eigen_cpp",
    "historical_smoothed_cov_min_eigen_cpp",
    "forecast_filtered_cov_min_eigen_cpp",
    "forecast_smoothed_cov_min_eigen_cpp",
    "ragged_segment_count",
    "retained_transfer_dim",
    "first_segment_state_dim",
    "second_segment_state_dim",
    "first_segment_horizon",
    "second_segment_horizon"
  ),
  value = c(
    max(abs(cpp$fm - ref_hist$fm)),
    max(abs(cpp$fC - ref_hist$fC)),
    max(abs(cpp$sm - ref_hist_smooth$sm)),
    max(abs(cpp$sC - ref_hist_smooth$sC)),
    max_abs_diff_list(cpp$fm_ens, ref_fore$fm_ens),
    max_abs_diff_list(cpp$fC_ens, ref_fore$fC_ens),
    max_abs_diff_list(cpp$sm_ens, ref_fore_smooth$sm_ens),
    max_abs_diff_list(cpp$sC_ens, ref_fore_smooth$sC_ens),
    max_slice_asymmetry(cpp$fC),
    max_slice_asymmetry(cpp$sC),
    max(vapply(cpp$fC_ens, max_slice_asymmetry, numeric(1))),
    max(vapply(cpp$sC_ens, max_slice_asymmetry, numeric(1))),
    min_slice_eigen(cpp$fC),
    min_slice_eigen(cpp$sC),
    min(vapply(cpp$fC_ens, min_slice_eigen, numeric(1))),
    min(vapply(cpp$sC_ens, min_slice_eigen, numeric(1))),
    length(cpp$sm_ens),
    fixture$ppx,
    dim(cpp$sm_ens[[1L]])[[1L]],
    dim(cpp$sm_ens[[2L]])[[1L]],
    dim(cpp$sm_ens[[1L]])[[3L]],
    dim(cpp$sm_ens[[2L]])[[3L]]
  ),
  tolerance = c(
    rep(1e-8, 8L),
    rep(1e-10, 4L),
    rep(-1e-8, 4L),
    2, 1, 4, 3, 2, 3
  ),
  stringsAsFactors = FALSE
)
checks$pass <- c(
  checks$value[seq_len(12L)] <= checks$tolerance[seq_len(12L)],
  checks$value[13:16] >= checks$tolerance[13:16],
  checks$value[17:22] == checks$tolerance[17:22]
)

segment_table <- data.frame(
  segment = c("both_sources", "source1_only"),
  active_sources = c(2L, 1L),
  state_dim = c(dim(cpp$sm_ens[[1L]])[[1L]], dim(cpp$sm_ens[[2L]])[[1L]]),
  horizon = c(dim(cpp$sm_ens[[1L]])[[3L]], dim(cpp$sm_ens[[2L]])[[3L]]),
  transfer_dim = fixture$ppx,
  obs_members = c(sum(fixture$num_mem), fixture$num_mem[[1L]])
)

write.csv(checks, file.path(out_dir, "kalman_fixture_checks.csv"), row.names = FALSE)
write.csv(segment_table, file.path(out_dir, "kalman_fixture_segments.csv"), row.names = FALSE)
saveRDS(
  list(
    fixture = fixture,
    cpp = cpp,
    reference = list(
      history_filter = ref_hist,
      forecast_filter = ref_fore,
      forecast_smoother = ref_fore_smooth,
      history_smoother = ref_hist_smooth
    ),
    checks = checks,
    segments = segment_table
  ),
  file.path(out_dir, "kalman_fixture_payload.rds")
)

readme <- c(
  "# exDQLM keep ragged Kalman fixture",
  "",
  "Generated by `repro/audits/run_exdqlm_keep_kalman_fixture.R`.",
  "",
  "This deterministic fixture exercises the active compiled `DISC_update_theta_synth_cpp_W` path with:",
  "",
  "- `J = 2` forecast sources,",
  "- retained transfer dimension `ppx = 1`,",
  "- ragged forecast horizons `k_ens = c(5, 2)`, which create a both-source segment followed by a source-1-only segment,",
  "- time-varying forecast transition cubes,",
  "- compiled-vs-reference checks for historical and forecast filtered and smoothed means/covariances.",
  "",
  "## Segment Table",
  "",
  paste(capture.output(print(segment_table)), collapse = "\n"),
  "",
  "## Checks",
  "",
  paste(capture.output(print(checks)), collapse = "\n")
)
writeLines(readme, file.path(out_dir, "README.md"))

if (!all(checks$pass)) {
  stop(sprintf(
    "Kalman fixture failed; see %s",
    normalizePath(file.path(out_dir, "kalman_fixture_checks.csv"), mustWork = FALSE)
  ), call. = FALSE)
}

cat(sprintf("Kalman fixture PASS: %s\n", normalizePath(out_dir, mustWork = FALSE)))
