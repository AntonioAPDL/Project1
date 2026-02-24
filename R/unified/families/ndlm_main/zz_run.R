unified_run_ndlm_main_theory <- function(seed, output_path, log_path = NULL) {
  constants <- ndlm_theory_constants(seed = seed)
  inputs <- ndlm_theory_load_inputs(horizon_cap = constants$forecast_horizon_cap)
  fit_result <- ndlm_theory_fit(inputs = inputs, constants = constants)
  out_env <- ndlm_theory_pack_compat_outputs(fit_result)

  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
  save(list = ls(out_env), file = output_path, envir = out_env)

  summary_lines <- c(
    "implementation_mode=theory_aligned",
    sprintf("kalman_backend=%s", constants$kalman_backend),
    sprintf("output_path=%s", output_path),
    sprintf("max_iter=%d", fit_result$max_iter),
    sprintf("min_total_iters=%d", constants$min_total_iters),
    sprintf("converged=%s", if (isTRUE(fit_result$converged)) "true" else "false"),
    sprintf("iterations_completed=%d", fit_result$iterations_completed),
    sprintf("convergence_reason=%s", fit_result$convergence_reason),
    sprintf("elbo_tol=%s", as.character(fit_result$convergence_metrics[["elbo_tol"]])),
    sprintf("elbo_rel_tol=%s", as.character(fit_result$convergence_metrics[["elbo_rel_tol"]])),
    sprintf("crit_elbo=%s", as.character(fit_result$convergence_metrics[["crit_elbo"]])),
    sprintf("crit_elbo_rel=%s", as.character(fit_result$convergence_metrics[["crit_elbo_rel"]])),
    sprintf("sigma=%.8f", fit_result$sigma),
    sprintf("w_hist=%.8f", fit_result$w_hist),
    sprintf("w_fore=%.8f", fit_result$w_fore),
    sprintf("T=%d", fit_result$T),
    sprintf("K=%d", fit_result$K),
    sprintf("K_overlap=%d", fit_result$K_overlap),
    sprintf("K_max=%d", fit_result$K_max),
    sprintf("K_vec.nws=%d", fit_result$K_vec[["nws"]]),
    sprintf("K_vec.glofas=%d", fit_result$K_vec[["glofas"]]),
    sprintf("segment_lengths=[%d,%d]", fit_result$segment_lengths[["overlap"]], fit_result$segment_lengths[["extension"]]),
    sprintf("extension_source=%s", fit_result$extension_source),
    sprintf("bridge_source=%s", fit_result$bridge_source),
    sprintf("K_cap=%d", fit_result$K_cap),
    sprintf("nws_len=%d", fit_result$nws_len),
    sprintf("glofas_len=%d", fit_result$glofas_len)
  )
  if (!is.null(log_path) && nzchar(log_path)) {
    dir.create(dirname(log_path), recursive = TRUE, showWarnings = FALSE)
    writeLines(summary_lines, con = log_path)
  } else {
    writeLines(summary_lines)
  }

  invisible(
    list(
      output_path = output_path,
      sigma = fit_result$sigma,
      w_hist = fit_result$w_hist,
      w_fore = fit_result$w_fore,
      kalman_backend = constants$kalman_backend
    )
  )
}
