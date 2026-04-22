repo_root <- normalizePath("/data/muscat_data/jaguir26/project1_ucsc_phd", mustWork = TRUE)
output_dir <- file.path(repo_root, "reports", "ndlm_reaudit_postcorrection")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

source(file.path(repo_root, "R", "environmetrics", "02_helpers_core.R"))
source(file.path(repo_root, "R", "unified", "families", "ndlm_main", "02_model_spec.R"))
source(file.path(repo_root, "R", "unified", "families", "exdqlm_univar", "02_model_spec.R"))

fmt_num <- function(x, digits = 6L) {
  if (!is.finite(x)) return("n/a")
  formatC(x, digits = digits, format = "f")
}

summarize_numeric_object <- function(name, obj, run_name) {
  vals <- as.numeric(obj)
  vals <- vals[is.finite(vals)]
  if (length(vals) < 1L) {
    return(data.frame(
      run_name = run_name,
      object_name = name,
      dim = if (is.null(dim(obj))) as.character(length(obj)) else paste(dim(obj), collapse = "x"),
      min = NA_real_,
      median = NA_real_,
      mean = NA_real_,
      q99 = NA_real_,
      q999 = NA_real_,
      max = NA_real_,
      stringsAsFactors = FALSE
    ))
  }
  data.frame(
    run_name = run_name,
    object_name = name,
    dim = if (is.null(dim(obj))) as.character(length(obj)) else paste(dim(obj), collapse = "x"),
    min = min(vals),
    median = stats::median(vals),
    mean = mean(vals),
    q99 = as.numeric(stats::quantile(vals, 0.99, names = FALSE)),
    q999 = as.numeric(stats::quantile(vals, 0.999, names = FALSE)),
    max = max(vals),
    stringsAsFactors = FALSE
  )
}

ndlm_runs_root <- file.path(
  "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime",
  "multimodel_v8_ndlm_featurecov_rerun_20260420",
  "runs"
)
run_dirs <- sort(list.dirs(ndlm_runs_root, full.names = TRUE, recursive = FALSE))
run_dirs <- run_dirs[!grepl("__failed_", basename(run_dirs), fixed = TRUE)]

cache_rows <- list()
for (run_dir in run_dirs) {
  run_name <- basename(run_dir)
  cache_dir <- file.path(run_dir, "post", "cache")
  for (nm in c("xbs_ndlm_mean_loglog1p.rds", "xbs_ndlm_log1p.rds", "y_reps_ndlm_loglog1p.rds", "y_reps_ndlm_log1p.rds")) {
    p <- file.path(cache_dir, nm)
    if (!file.exists(p)) next
    cache_rows[[length(cache_rows) + 1L]] <- summarize_numeric_object(nm, readRDS(p), run_name)
  }
}
cache_summary <- do.call(rbind, cache_rows)
utils::write.csv(
  cache_summary,
  file.path(output_dir, "ndlm_predictive_cache_summaries.csv"),
  row.names = FALSE
)

quantile_paths <- list(
  "multimodel_20211221_v8_eps1cf1_exdqlm_multivar_keep_featurecov_cf1" =
    file.path(
      "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime",
      "multimodel_v8_featurecov_cf1_eps_sweep_20260416",
      "runs",
      "multimodel_20211221_v8_eps1cf1_exdqlm_multivar_keep_featurecov_cf1",
      "post",
      "cache",
      "exdqlm_multivar_synth_keep__mode-keep__y_reps_f_new_smoke.rds"
    ),
  "multimodel_20211221_v8_eps1cf1_exdqlm_multivar_drop_featurecov_cf1" =
    file.path(
      "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime",
      "multimodel_v8_featurecov_cf1_eps_sweep_20260416",
      "runs",
      "multimodel_20211221_v8_eps1cf1_exdqlm_multivar_drop_featurecov_cf1",
      "post",
      "cache",
      "exdqlm_multivar_synth_drop__mode-drop__y_reps_f_new_smoke.rds"
    ),
  "multimodel_20221225_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1" =
    file.path(
      "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime",
      "multimodel_v8_featurecov_cf1_eps_sweep_20260416",
      "runs",
      "multimodel_20221225_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1",
      "post",
      "cache",
      "exdqlm_multivar_synth_keep__mode-keep__y_reps_f_new_smoke.rds"
    ),
  "multimodel_20221225_v8_eps1cf1_exdqlm_multivar_drop_featurecov_cf1" =
    file.path(
      "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime",
      "multimodel_v8_featurecov_cf1_eps_sweep_20260416",
      "runs",
      "multimodel_20221225_v8_eps1cf1_exdqlm_multivar_drop_featurecov_cf1",
      "post",
      "cache",
      "exdqlm_multivar_synth_drop__mode-drop__y_reps_f_new_smoke.rds"
    )
)
quant_rows <- list()
for (run_name in names(quantile_paths)) {
  p <- quantile_paths[[run_name]]
  if (!file.exists(p)) next
  quant_rows[[length(quant_rows) + 1L]] <- summarize_numeric_object("quantile_predictive_cube", readRDS(p), run_name)
}
quant_summary <- do.call(rbind, quant_rows)
utils::write.csv(
  quant_summary,
  file.path(output_dir, "ndlm_vs_quantile_predictive_scale.csv"),
  row.names = FALSE
)

y <- c(0.3, 0.5, 0.2, 0.6, 0.4)
F_mat <- cbind(1, c(-0.2, 0.0, 0.1, 0.2, 0.3))
R_vec <- rep(0.15, length(y))
q_diag <- c(0.05, 0.02)
m0 <- c(0.1, -0.1)
C0 <- diag(c(0.5, 0.3), 2L)

ndlm_r <- ndlm_theory_kalman_smoother(
  y = y,
  H_mat = F_mat,
  R_vec = R_vec,
  q_diag = q_diag,
  m0 = m0,
  C0 = C0,
  df_mat = NULL,
  backend = "r"
)
ndlm_cpp <- ndlm_theory_kalman_smoother(
  y = y,
  H_mat = F_mat,
  R_vec = R_vec,
  q_diag = q_diag,
  m0 = m0,
  C0 = C0,
  df_mat = NULL,
  backend = "cpp"
)
univar_out <- univar_theory_kalman_smoother(
  y = y,
  F_mat = F_mat,
  R_vec = R_vec,
  q_diag = q_diag,
  m0 = m0,
  C0 = C0
)

kalman_checks <- data.frame(
  check = c(
    "ndlm_r_vs_univar_fitted_mean_max_abs_diff",
    "ndlm_r_vs_univar_fitted_var_max_abs_diff",
    "ndlm_r_vs_univar_smooth_mean_max_abs_diff",
    "ndlm_r_vs_univar_smooth_cov_max_abs_diff",
    "ndlm_r_vs_cpp_fitted_mean_max_abs_diff",
    "ndlm_r_vs_cpp_fitted_var_max_abs_diff",
    "ndlm_r_vs_cpp_smooth_mean_max_abs_diff",
    "ndlm_r_vs_cpp_smooth_cov_max_abs_diff"
  ),
  value = c(
    max(abs(ndlm_r$fitted_mean - univar_out$fitted_mean)),
    max(abs(ndlm_r$fitted_var - univar_out$fitted_var)),
    max(abs(ndlm_r$smooth_mean - univar_out$smooth_mean)),
    max(abs(ndlm_r$smooth_cov - univar_out$smooth_cov)),
    max(abs(ndlm_r$fitted_mean - ndlm_cpp$fitted_mean)),
    max(abs(ndlm_r$fitted_var - ndlm_cpp$fitted_var)),
    max(abs(ndlm_r$smooth_mean - ndlm_cpp$smooth_mean)),
    max(abs(ndlm_r$smooth_cov - ndlm_cpp$smooth_cov))
  ),
  stringsAsFactors = FALSE
)
utils::write.csv(
  kalman_checks,
  file.path(output_dir, "ndlm_kalman_congruence_checks.csv"),
  row.names = FALSE
)

smoke_fit_rdata <- file.path(
  "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime",
  "multimodel_v8_ndlm_featurecov_rerun_20260420",
  "control",
  "prelaunch_validation_20260421T045415Z",
  "smoke_runs",
  "ndlm_main_keep",
  "smoke_ndlm_main_keep",
  "fit",
  "ndlm_main",
  "outputs",
  "DISC_variables_50_NDLM_synth_DISC.RData"
)
sigma_replay <- NULL
if (file.exists(smoke_fit_rdata)) {
  e <- new.env(parent = emptyenv())
  load(smoke_fit_rdata, envir = e)
  sigma_draws <- get("samp.sigma_50_NDLM_synth_DISC", envir = e)
  mean_draws <- as.matrix(get("new.theta.out_50_NDLM_synth_DISC", envir = e)$forecast_mean_draws_loglog1p)
  n_eff <- min(nrow(mean_draws), ncol(sigma_draws))
  sigma_flat <- as.numeric(sigma_draws)
  sigma_usgs <- as.numeric(sigma_draws["usgs", ])

  set.seed(777L)
  z_bug <- matrix(stats::rnorm(length(mean_draws[seq_len(n_eff), , drop = FALSE])), nrow = n_eff)
  pred_bug <- exp(mean_draws[seq_len(n_eff), , drop = FALSE] + sweep(z_bug, 1L, sqrt(sigma_flat[seq_len(n_eff)]), `*`))

  set.seed(777L)
  z_fix <- matrix(stats::rnorm(length(mean_draws[seq_len(n_eff), , drop = FALSE])), nrow = n_eff)
  pred_fix <- exp(mean_draws[seq_len(n_eff), , drop = FALSE] + sweep(z_fix, 1L, sqrt(sigma_usgs[seq_len(n_eff)]), `*`))

  sigma_replay <- data.frame(
    check = c(
      "sigma_row_mean_usgs",
      "sigma_row_mean_nws",
      "sigma_row_mean_glofas",
      "bug_predictive_q999_log1p",
      "bug_predictive_max_log1p",
      "fix_predictive_q999_log1p",
      "fix_predictive_max_log1p",
      "bug_over_fix_q999_ratio",
      "bug_over_fix_max_ratio"
    ),
    value = c(
      mean(as.numeric(sigma_draws["usgs", ])),
      mean(as.numeric(sigma_draws["nws", ])),
      mean(as.numeric(sigma_draws["glofas", ])),
      as.numeric(stats::quantile(as.numeric(pred_bug), 0.999, names = FALSE)),
      max(as.numeric(pred_bug)),
      as.numeric(stats::quantile(as.numeric(pred_fix), 0.999, names = FALSE)),
      max(as.numeric(pred_fix)),
      as.numeric(stats::quantile(as.numeric(pred_bug), 0.999, names = FALSE)) /
        max(as.numeric(stats::quantile(as.numeric(pred_fix), 0.999, names = FALSE)), 1e-12),
      max(as.numeric(pred_bug)) / max(max(as.numeric(pred_fix)), 1e-12)
    ),
    stringsAsFactors = FALSE
  )
  utils::write.csv(
    sigma_replay,
    file.path(output_dir, "ndlm_sigma_mixing_replay.csv"),
    row.names = FALSE
  )
}

md_lines <- c(
  "# NDLM Numeric Reaudit Checks",
  "",
  "## Kalman Congruence",
  "",
  sprintf(
    "- NDLM R vs univariate Gaussian backbone max fitted-mean diff: `%s`",
    fmt_num(kalman_checks$value[kalman_checks$check == "ndlm_r_vs_univar_fitted_mean_max_abs_diff"], digits = 10L)
  ),
  sprintf(
    "- NDLM R vs univariate Gaussian backbone max smooth-cov diff: `%s`",
    fmt_num(kalman_checks$value[kalman_checks$check == "ndlm_r_vs_univar_smooth_cov_max_abs_diff"], digits = 10L)
  ),
  sprintf(
    "- NDLM R vs NDLM cpp max smooth-cov diff: `%s`",
    fmt_num(kalman_checks$value[kalman_checks$check == "ndlm_r_vs_cpp_smooth_cov_max_abs_diff"], digits = 10L)
  ),
  "",
  "## Sigma-Mixing Replay",
  ""
)
if (!is.null(sigma_replay)) {
  md_lines <- c(
    md_lines,
    sprintf(
      "- Smoke-run sigma row means (`usgs`, `nws`, `glofas`): `%s`, `%s`, `%s`",
      fmt_num(sigma_replay$value[sigma_replay$check == "sigma_row_mean_usgs"]),
      fmt_num(sigma_replay$value[sigma_replay$check == "sigma_row_mean_nws"]),
      fmt_num(sigma_replay$value[sigma_replay$check == "sigma_row_mean_glofas"])
    ),
    sprintf(
      "- Pre-fix replay q99.9 / max: `%s` / `%s`",
      fmt_num(sigma_replay$value[sigma_replay$check == "bug_predictive_q999_log1p"]),
      fmt_num(sigma_replay$value[sigma_replay$check == "bug_predictive_max_log1p"])
    ),
    sprintf(
      "- USGS-only replay q99.9 / max: `%s` / `%s`",
      fmt_num(sigma_replay$value[sigma_replay$check == "fix_predictive_q999_log1p"]),
      fmt_num(sigma_replay$value[sigma_replay$check == "fix_predictive_max_log1p"])
    ),
    sprintf(
      "- Explosion ratio (bug over fix): q99.9=`%s`, max=`%s`",
      fmt_num(sigma_replay$value[sigma_replay$check == "bug_over_fix_q999_ratio"]),
      fmt_num(sigma_replay$value[sigma_replay$check == "bug_over_fix_max_ratio"])
    )
  )
} else {
  md_lines <- c(md_lines, "- Smoke-run fit artifact was unavailable, so the sigma-mixing replay could not be executed.")
}
writeLines(md_lines, file.path(output_dir, "ndlm_synthetic_harness_report.md"))
