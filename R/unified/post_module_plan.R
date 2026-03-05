unified_post_select_modules <- function(
  post_figures,
  post_smoke_fast,
  model_run_exdqlm_multivar,
  model_run_exdqlm_univar,
  model_run_ndlm_main,
  core_modules
) {
  stopifnot(is.logical(post_figures), length(post_figures) == 1L)
  stopifnot(is.logical(post_smoke_fast), length(post_smoke_fast) == 1L)
  stopifnot(is.logical(model_run_exdqlm_multivar), length(model_run_exdqlm_multivar) == 1L)
  stopifnot(is.logical(model_run_exdqlm_univar), length(model_run_exdqlm_univar) == 1L)
  stopifnot(is.logical(model_run_ndlm_main), length(model_run_ndlm_main) == 1L)
  stopifnot(is.character(core_modules), length(core_modules) > 0L)

  if (!isTRUE(post_figures)) {
    return(core_modules)
  }

  ndlm_only_mode <- isTRUE(model_run_ndlm_main) &&
    !isTRUE(model_run_exdqlm_multivar) &&
    !isTRUE(model_run_exdqlm_univar)

  univar_only_mode <- isTRUE(model_run_exdqlm_univar) &&
    !isTRUE(model_run_exdqlm_multivar) &&
    !isTRUE(model_run_ndlm_main)

  multivar_only_mode <- isTRUE(model_run_exdqlm_multivar) &&
    !isTRUE(model_run_exdqlm_univar) &&
    !isTRUE(model_run_ndlm_main)

  if (isTRUE(post_smoke_fast)) {
    if (multivar_only_mode) {
      # Multivariate isolation lane: run DISC-only post figures without
      # requiring NDLM/univariate artifacts.
      return(c(core_modules, "10_data_inputs.R", "20_model_setup.R", "30_univariate_and_misc.R", "40_figures_multivar_only.R"))
    }
    return(c(core_modules, "10_data_inputs.R", "20_model_setup.R", "40_figures_smoke_fast.R"))
  }

  if (ndlm_only_mode) {
    # NDLM isolation lane: avoid exDQLM init/load codepaths entirely.
    return(c(core_modules, "10_data_inputs.R", "20_model_setup.R", "30_ndlm_only_init.R", "40_figures_smoke_fast.R"))
  }

  if (univar_only_mode) {
    # Univariate isolation lane: keep the univariate synthesis path, but avoid
    # full cross-family figure contracts that require NDLM/multiv objects.
    return(c(core_modules, "10_data_inputs.R", "20_model_setup.R", "30_univariate_and_misc.R", "40_figures_smoke_fast.R"))
  }

  if (multivar_only_mode) {
    # Multivariate isolation lane: generate DISC-only diagnostics/forecast plots
    # without touching NDLM-specific figure sections.
    return(c(core_modules, "10_data_inputs.R", "20_model_setup.R", "30_univariate_and_misc.R", "40_figures_multivar_only.R"))
  }

  c(core_modules, "10_data_inputs.R", "20_model_setup.R", "30_univariate_and_misc.R", "40_figures.R")
}
