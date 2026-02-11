unified_run_ndlm_main_theory <- function(seed, output_path, log_path = NULL) {
  constants <- ndlm_theory_constants(seed = seed)
  inputs <- ndlm_theory_load_inputs()
  fit_result <- ndlm_theory_fit(inputs = inputs, constants = constants)
  out_env <- ndlm_theory_pack_compat_outputs(fit_result)

  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
  save(list = ls(out_env), file = output_path, envir = out_env)

  summary_lines <- c(
    "implementation_mode=theory_aligned",
    sprintf("output_path=%s", output_path),
    sprintf("sigma=%.8f", fit_result$sigma),
    sprintf("w_hist=%.8f", fit_result$w_hist),
    sprintf("w_fore=%.8f", fit_result$w_fore),
    sprintf("T=%d", fit_result$T),
    sprintf("K=%d", fit_result$K)
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
      w_fore = fit_result$w_fore
    )
  )
}
