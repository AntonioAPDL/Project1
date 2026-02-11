unified_run_exdqlm_univar_theory <- function(q, seed, output_path, log_path = NULL) {
  q_num <- as.integer(round(as.numeric(q) * 100))
  constants <- univar_theory_constants(q_num = q_num, seed = seed)
  inputs <- univar_theory_load_inputs()
  fit_result <- univar_theory_run_cavi(inputs, constants)
  out_env <- univar_theory_pack_compat_outputs(fit_result, constants)

  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
  save(list = ls(out_env), file = output_path, envir = out_env)

  summary_lines <- c(
    sprintf("implementation_mode=theory_aligned"),
    sprintf("quantile=%0.2f", as.numeric(q)),
    sprintf("q_num=%d", q_num),
    sprintf("output_path=%s", output_path),
    sprintf("sigma=%.8f", fit_result$sigma),
    sprintf("gamma=%.8f", fit_result$gamma),
    sprintf("T=%d", inputs$T),
    sprintf("p0=%.6f", fit_result$p0)
  )
  if (!is.null(log_path) && nzchar(log_path)) {
    dir.create(dirname(log_path), recursive = TRUE, showWarnings = FALSE)
    writeLines(summary_lines, con = log_path)
  } else {
    writeLines(summary_lines)
  }

  invisible(
    list(
      quantile = as.numeric(q),
      q_num = q_num,
      output_path = output_path,
      sigma = fit_result$sigma,
      gamma = fit_result$gamma
    )
  )
}
