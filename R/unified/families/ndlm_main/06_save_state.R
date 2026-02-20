ndlm_theory_pack_compat_outputs <- function(fit_result) {
  suffix <- "50_NDLM_synth_DISC"

  out_env <- new.env(parent = emptyenv())
  assign(sprintf("samp.sigma_%s", suffix), fit_result$samp_sigma, envir = out_env)
  assign(sprintf("samp.theta_%s", suffix), fit_result$samp_theta, envir = out_env)
  assign(sprintf("samp.theta_ens_%s", suffix), fit_result$samp_theta_ens, envir = out_env)
  assign(sprintf("new.theta.out_%s", suffix), fit_result$new_theta, envir = out_env)
  assign(sprintf("seq.sigma_%s", suffix), fit_result$seq_sigma, envir = out_env)
  assign(sprintf("seq.elbo_%s", suffix), ndlm_theory_elbo_trace(fit_result), envir = out_env)
  assign(sprintf("delta_%s", suffix), fit_result$delta, envir = out_env)

  assign(
    "ndlm_main_theory_state",
    list(
      sigma = fit_result$sigma,
      w_hist = fit_result$w_hist,
      w_fore = fit_result$w_fore,
      T = fit_result$T,
      K = fit_result$K,
      K_cap = fit_result$K_cap,
      nws_len = fit_result$nws_len,
      glofas_len = fit_result$glofas_len
    ),
    envir = out_env
  )

  out_env
}
