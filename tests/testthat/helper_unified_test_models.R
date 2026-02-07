make_toy_scalar_model <- function(TT, gg_vals = NULL, ff_vals = NULL, m0 = 0, C0 = 1) {
  stopifnot(TT >= 3)
  if (is.null(gg_vals)) gg_vals <- seq(0.8, 1.4, length.out = TT)
  if (is.null(ff_vals)) ff_vals <- rep(1, TT)
  stopifnot(length(gg_vals) == TT, length(ff_vals) == TT)

  list(
    m0 = matrix(m0, nrow = 1, ncol = 1),
    C0 = matrix(C0, nrow = 1, ncol = 1),
    FF = array(ff_vals, dim = c(1, 1, TT)),
    GG = array(gg_vals, dim = c(1, 1, TT))
  )
}

reference_dlm_df_scalar <- function(y, model, df, s.priors = list(l0 = 1, S0 = 10), use_buggy_index = FALSE) {
  y <- as.numeric(y)
  TT <- length(y)
  stopifnot(TT >= 2)

  l0 <- s.priors$l0
  S0 <- s.priors$S0
  gg <- as.numeric(model$GG[1, 1, ])
  ff <- as.numeric(model$FF[1, 1, ])
  m0 <- as.numeric(model$m0[1, 1])
  C0 <- as.numeric(model$C0[1, 1])

  df_factor <- (1 - df) / df

  a <- numeric(TT)
  P <- numeric(TT)
  W <- numeric(TT)
  R <- numeric(TT)
  f <- numeric(TT)
  Q <- numeric(TT)
  invQ <- numeric(TT)
  e <- numeric(TT)
  A <- numeric(TT)
  S <- numeric(TT)
  l <- numeric(TT)
  m <- numeric(TT)
  C <- numeric(TT)

  a[1] <- gg[1] * m0
  P[1] <- gg[1] * C0 * gg[1]
  W[1] <- df_factor * P[1]
  R[1] <- P[1] + W[1]
  f[1] <- ff[1] * a[1]
  Q[1] <- 1 + ff[1] * R[1] * ff[1]
  invQ[1] <- 1 / Q[1]
  e[1] <- y[1] - f[1]
  A[1] <- R[1] * ff[1] * invQ[1]
  l[1] <- l0 + 1
  S[1] <- l0 * S0 / l[1] + (e[1] * invQ[1] * e[1] / l[1])
  m[1] <- a[1] + A[1] * e[1]
  C[1] <- R[1] - A[1] * Q[1] * A[1]

  if (TT >= 2) {
    for (i in 2:TT) {
      a[i] <- gg[i] * m[i - 1]
      P[i] <- gg[i] * C[i - 1] * gg[i]
      W[i] <- df_factor * P[i]
      R[i] <- P[i] + W[i]
      f[i] <- ff[i] * a[i]
      Q[i] <- 1 + ff[i] * R[i] * ff[i]
      invQ[i] <- 1 / Q[i]
      e[i] <- y[i] - f[i]
      A[i] <- R[i] * ff[i] * invQ[i]
      l[i] <- l[i - 1] + 1
      S[i] <- l[i - 1] * S[i - 1] / l[i] + (e[i] * invQ[i] * e[i] / l[i])
      m[i] <- a[i] + A[i] * e[i]
      C[i] <- R[i] - A[i] * Q[i] * A[i]
    }
  }

  R[1] <- S0 * R[1]
  Q[1] <- S0 * Q[1]
  C[1] <- S[1] * C[1]
  if (TT >= 2) {
    for (i in 2:TT) {
      R[i] <- S[i - 1] * R[i]
      Q[i] <- S[i - 1] * Q[i]
      C[i] <- S[i] * C[i]
    }
  }

  sa <- numeric(TT)
  sR <- numeric(TT)
  sa[TT] <- m[TT]
  sR[TT] <- C[TT]

  if (TT >= 2) {
    for (k in seq_len(TT - 1)) {
      t_idx <- TT - k
      g_idx <- if (use_buggy_index) TT else (TT - k + 1)
      B <- C[t_idx] * gg[g_idx] / R[t_idx + 1]
      sa[t_idx] <- m[t_idx] + B * (sa[t_idx + 1] - a[t_idx + 1])
      sR[t_idx] <- C[t_idx] + B * (sR[t_idx + 1] - R[t_idx + 1]) * B
    }
  }

  for (k in seq_len(TT)) {
    t_idx <- TT - k + 1
    sR[t_idx] <- S[TT] * sR[t_idx] / S[t_idx]
  }

  list(
    fm = m,
    fC = C,
    m = sa,
    C = sR,
    s = S,
    n = l
  )
}
