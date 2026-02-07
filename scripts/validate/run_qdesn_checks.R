#!/usr/bin/env Rscript

source(file.path("R", "environmetrics", "qdesn_validation_math.R"))

run_check <- function(name, fn) {
  started <- Sys.time()
  ok <- TRUE
  msg <- "PASS"

  tryCatch(
    {
      fn()
    },
    error = function(e) {
      ok <<- FALSE
      msg <<- conditionMessage(e)
    }
  )

  elapsed <- as.numeric(difftime(Sys.time(), started, units = "secs"))
  list(name = name, status = if (ok) "PASS" else "FAIL", message = msg, seconds = elapsed)
}

check_dim1_reduction <- function() {
  set.seed(1001)
  p0 <- 0.35

  for (i in 1:50) {
    h_t <- rnorm(1)
    alpha_t <- rnorm(1)
    sigma <- runif(1, 0.2, 2.0)
    L <- qdesn_L_fn(p0)
    U <- qdesn_U_fn(p0)
    gamma <- runif(1, L * 0.75, U * 0.75)
    if (abs(gamma) < 0.05) gamma <- 0.05
    s_t <- runif(1, 0.01, 4.0)
    v_t <- runif(1, 0.01, 4.0)

    mu_uni <- qdesn_mu_univariate(h_t, alpha_t, sigma, gamma, s_t, v_t, p0)
    mu_multi <- qdesn_mu_multivariate(
      H_t = matrix(h_t, nrow = 1, ncol = 1),
      alpha_t = matrix(alpha_t, nrow = 1, ncol = 1),
      sigma = sigma,
      gamma = gamma,
      s_t = s_t,
      v_t = v_t,
      p0 = p0
    )

    if (abs(mu_uni - mu_multi) > 1e-12) {
      stop(sprintf("dimension-1 reduction mismatch at replicate %d", i))
    }
  }
}

check_finite_chi <- function() {
  set.seed(1002)
  d <- 64

  y <- rnorm(d)
  exps <- rnorm(d)
  exps2 <- exps^2 + rexp(d, 2)
  sts <- rexp(d, 1) + 0.01
  sts2 <- sts^2 + runif(d, 0, 0.2)

  chi <- qdesn_update_uts_chi(
    y = y,
    exps = exps,
    exps2 = exps2,
    sts = sts,
    sts2 = sts2,
    invb_inv_sigma = runif(d, 0.05, 2.0),
    c_invb_absgam = runif(d, -1, 1),
    c2_invb_absgam2_sigma = runif(d, 0.01, 2.0)
  )

  if (!all(is.finite(chi))) stop("non-finite chi detected")
  if (!all(chi > 0)) stop("chi contains non-positive values after clamp")
}

check_fd_gradient <- function() {
  set.seed(1003)
  p0 <- 0.5

  n <- 16
  y <- rnorm(n)
  exps <- rnorm(n)
  exps2 <- exps^2 + rexp(n, 2)
  sts <- rexp(n, 1) + 0.01
  sts2 <- sts^2 + runif(n, 0, 0.15)
  uts <- rexp(n, 1) + 0.05
  inv_uts <- 1 / (uts + runif(n, 0.1, 0.5))
  prior_g <- c(0, 1, 5)
  prior_s <- c(2, 1)

  f <- function(theta) {
    qdesn_dq_transf_no_climate(
      theta_s = theta[1],
      theta_g = theta[2],
      y = y,
      exps = exps,
      exps2 = exps2,
      sts = sts,
      sts2 = sts2,
      uts = uts,
      inv_uts = inv_uts,
      prior_g = prior_g,
      prior_s = prior_s,
      p0 = p0
    )
  }

  theta <- c(log(1.2), -0.35)
  g_h <- qdesn_central_diff(f, theta, h = 1e-5)
  g_h2 <- qdesn_central_diff(f, theta, h = 5e-6)

  if (!all(is.finite(g_h)) || !all(is.finite(g_h2))) {
    stop("non-finite finite-difference gradient")
  }

  if (max(abs(g_h - g_h2)) > 1e-4) {
    stop("finite-difference gradient unstable under step halving")
  }
}

checks <- list(
  run_check("dim1_reduction", check_dim1_reduction),
  run_check("finite_chi", check_finite_chi),
  run_check("fd_gradient", check_fd_gradient)
)

out_path <- file.path("logs", "validation", "qdesn_checks.tsv")

dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)

out_df <- data.frame(
  check = vapply(checks, `[[`, character(1), "name"),
  status = vapply(checks, `[[`, character(1), "status"),
  seconds = signif(vapply(checks, `[[`, numeric(1), "seconds"), 4),
  message = vapply(checks, `[[`, character(1), "message"),
  stringsAsFactors = FALSE
)

write.table(out_df, file = out_path, sep = "\t", row.names = FALSE, quote = TRUE)

cat("QDESN_CHECK_SUMMARY\n")
for (i in seq_len(nrow(out_df))) {
  cat(sprintf("- %s: %s (%ss)\n", out_df$check[i], out_df$status[i], out_df$seconds[i]))
}
cat(sprintf("\nWrote: %s\n", out_path))

if (any(out_df$status != "PASS")) {
  quit(status = 1)
}
