# disc_w/05_save_state.R
#
# Save-state helpers for `DISC_Optimal_Synth_Ranges_W.r`.
# The workflow dynamically names many variables via `assign()` and then saves a
# subset into `DISC_variables_<...>.RData`. This module preserves those semantics
# without changing object creation or save ordering.

# disc_w_save_variables(var_names, filename, dir_path, env)
# Saves the objects listed in `var_names` (character vector) from `env`.
disc_w_save_variables <- function(var_names, filename, dir_path, env = parent.frame()) {
  file_path <- file.path(dir_path, filename)
  save_fun <- function(path) save(list = var_names, file = path, envir = env)
  if (exists("unified_safe_save", mode = "function", inherits = TRUE)) {
    unified_safe_save(
      save_fun = save_fun,
      final_path = file_path,
      context = sprintf("disc_w_save_variables[%s]", filename)
    )
  } else {
    save_fun(file_path)
  }
  cat("Variables saved to:", file_path, "\n")
  invisible(file_path)
}

# disc_w_save_state(p0, ending, disc_w_paths, env)
# Reproduces the original save-state block:
# - constructs dynamic names (suffix + ending)
# - assigns derived variables into `env`
# - saves the selected variables into `DISC_variables_<...>.RData`
disc_w_save_state <- function(p0, ending, disc_w_paths, env = parent.frame()) {
  result_suffix <- sprintf("%.0f", p0 * 100)

  ext.f_name <- paste0("ext.f_", result_suffix, ending)
  ext.q_name <- paste0("ext.q_", result_suffix, ending)
  ext.f_f_name <- paste0("ext.f_f_", result_suffix, ending)
  ext.q_f_name <- paste0("ext.q_f_", result_suffix, ending)

  samp.gamma_name <- paste0("samp.gamma_", result_suffix, ending)
  samp.sigma_name <- paste0("samp.sigma_", result_suffix, ending)

  samp.uts_name <- paste0("samp.uts_", result_suffix, ending)
  samp.sts_name <- paste0("samp.sts_", result_suffix, ending)
  samp.uts_ens_name <- paste0("samp.uts_ens_", result_suffix, ending)
  samp.sts_ens_name <- paste0("samp.sts_ens_", result_suffix, ending)

  samp.theta_name <- paste0("samp.theta_", result_suffix, ending)
  samp.theta_ens_name <- paste0("samp.theta_ens_", result_suffix, ending)

  new.uts.out_name <- paste0("new.uts.out_", result_suffix, ending)
  new.sts.out_name <- paste0("new.sts.out_", result_suffix, ending)
  new.uts.out_ens_name <- paste0("new.uts_ens.out_", result_suffix, ending)
  new.sts.out_ens_name <- paste0("new.sts_ens.out_", result_suffix, ending)

  new.gamsig.out_name <- paste0("new.gamsig.out_", result_suffix, ending)
  new.theta.out_name <- paste0("new.theta.out_", result_suffix, ending)
  new.theta.out_ens_name <- paste0("new.theta_ens.out_", result_suffix, ending)

  seq.gamma_name <- paste0("seq.gamma_", result_suffix, ending)
  seq.sigma_name <- paste0("seq.sigma_", result_suffix, ending)
  seq.elbo_name <- paste0("seq.elbo_", result_suffix, ending)
  seq.eigen_name <- paste0("seq.eigen", result_suffix, ending)

  delta_name <- paste0("delta_", result_suffix, ending)

  assign(delta_name, get("delta", envir = env), envir = env)

  assign(samp.gamma_name, get("samp.gamma", envir = env), envir = env)
  assign(samp.sigma_name, get("samp.sigma", envir = env), envir = env)

  assign(samp.uts_name, get("samp.uts", envir = env), envir = env)
  assign(samp.sts_name, get("samp.sts", envir = env), envir = env)
  assign(samp.uts_ens_name, get("samp.uts_ens", envir = env), envir = env)
  assign(samp.sts_ens_name, get("samp.sts_ens", envir = env), envir = env)

  assign(samp.theta_name, get("result_retro", envir = env), envir = env)
  assign(samp.theta_ens_name, get("result_forecast", envir = env), envir = env)

  assign(new.uts.out_name, get("new.uts.out", envir = env), envir = env)
  assign(new.sts.out_name, get("new.sts.out", envir = env), envir = env)
  assign(new.uts.out_ens_name, get("new.uts.out_f", envir = env), envir = env)
  assign(new.sts.out_ens_name, get("new.sts.out_f", envir = env), envir = env)

  assign(new.gamsig.out_name, get("new.gamsig.out", envir = env), envir = env)
  assign(new.theta.out_name, get("new.theta.out", envir = env), envir = env)

  assign(seq.gamma_name, get("seq.gamma", envir = env), envir = env)
  assign(seq.sigma_name, get("seq.sigma", envir = env), envir = env)
  assign(seq.elbo_name, get("seq.elbo", envir = env), envir = env)
  assign(seq.eigen_name, get("seq.eigen", envir = env), envir = env)

  assign(ext.f_name, get("FFF", envir = env), envir = env)
  assign(ext.q_name, get("QQQ", envir = env), envir = env)
  assign(ext.f_f_name, get("FFF_list", envir = env), envir = env)
  assign(ext.q_f_name, get("QQQ_list", envir = env), envir = env)

  vars_to_save <- c(
    samp.gamma_name, samp.sigma_name,
    samp.uts_name, samp.sts_name,
    samp.theta_name,
    samp.uts_ens_name, samp.sts_ens_name,
    samp.theta_ens_name,
    new.uts.out_name, new.sts.out_name,
    new.gamsig.out_name,
    new.theta.out_name,
    new.uts.out_ens_name, new.sts.out_ens_name,
    seq.gamma_name, seq.sigma_name,
    seq.elbo_name, delta_name,
    ext.f_name, ext.q_name,
    ext.f_f_name, ext.q_f_name,
    seq.eigen_name
  )

  disc_w_save_variables(
    vars_to_save,
    filename = paste0("DISC_variables_", result_suffix, ending, ".RData"),
    dir_path = disc_w_paths$output_dir,
    env = env
  )
}
