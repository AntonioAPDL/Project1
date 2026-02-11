# unified/stages/stage_fit.R

unified_stage_fit <- function(cfg, run_root, repo_root, manifest) {
  oldwd <- getwd()
  on.exit(setwd(oldwd), add = TRUE)
  setwd(repo_root)

  run_root_abs <- normalizePath(run_root, mustWork = FALSE)
  fit_root <- file.path(run_root, "fit")
  fit_inputs <- file.path(fit_root, "inputs")
  dir.create(fit_inputs, recursive = TRUE, showWarnings = FALSE)

  shared_paths <- unified_shared_input_paths(run_root)
  use_shared_inputs <- isTRUE(cfg$stages$data_prep_shared) || dir.exists(shared_paths$root)
  if (use_shared_inputs) {
    shared_validation <- unified_validate_required_shared_inputs(
      run_root = run_root,
      stage_name = "fit",
      manifest = manifest,
      enabled_models = cfg$models
    )
    source_parameters <- shared_validation$paths$parameters
    source_retros <- shared_validation$paths$retros
    source_nws <- shared_validation$paths$nws
    source_glofas <- shared_validation$paths$glofas
    source_retros_scale <- shared_validation$scales$retros
    if (is.null(source_retros_scale) || !nzchar(source_retros_scale)) {
      source_retros_scale <- cfg$inputs$fit$retros_storage_scale
    }
    source_nws_scale <- shared_validation$scales$nws
    if (is.null(source_nws_scale) || !nzchar(source_nws_scale)) {
      source_nws_scale <- cfg$inputs$fit$nws_storage_scale
    }
    source_glofas_scale <- shared_validation$scales$glofas
    if (is.null(source_glofas_scale) || !nzchar(source_glofas_scale)) {
      source_glofas_scale <- cfg$inputs$fit$glofas_storage_scale
    }
  } else {
    source_parameters <- cfg$inputs$fit$parameters_path
    source_retros <- cfg$inputs$fit$retros_path
    source_nws <- cfg$inputs$fit$nws_forecast_path
    source_glofas <- cfg$inputs$fit$glofas_forecast_path
    source_retros_scale <- cfg$inputs$fit$retros_storage_scale
    source_nws_scale <- cfg$inputs$fit$nws_storage_scale
    source_glofas_scale <- cfg$inputs$fit$glofas_storage_scale
  }

  legacy_scale <- cfg$scale_contract$legacy_fit_input_scale
  unified_assert_known_scale(legacy_scale, "scale_contract.legacy_fit_input_scale")

  parameters_copy <- file.path(fit_inputs, basename(source_parameters))
  file.copy(source_parameters, parameters_copy, overwrite = TRUE)

  adapted_retros <- file.path(fit_inputs, "retros_fit_adapter.csv")
  adapted_nws <- file.path(fit_inputs, "nws_fit_adapter.csv")
  adapted_glofas <- file.path(fit_inputs, "glofas_fit_adapter.csv")

  unified_adapt_csv_scale(
    input_path = source_retros,
    output_path = adapted_retros,
    from_scale = source_retros_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "fit_input/retros",
    from_scale = source_retros_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", source_retros_scale, legacy_scale)
  )

  unified_adapt_csv_scale(
    input_path = source_nws,
    output_path = adapted_nws,
    from_scale = source_nws_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "fit_input/nws_forecast",
    from_scale = source_nws_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", source_nws_scale, legacy_scale)
  )

  unified_adapt_csv_scale(
    input_path = source_glofas,
    output_path = adapted_glofas,
    from_scale = source_glofas_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "fit_input/glofas_forecast",
    from_scale = source_glofas_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", source_glofas_scale, legacy_scale)
  )

  manifest <- unified_manifest_add_artifact(manifest, adapted_retros, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_nws, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_glofas, storage_scale = legacy_scale)

  shared_cov_paths <- list(
    eli = "",
    oni = "",
    ppt = "",
    soil = "",
    pca = ""
  )
  if (use_shared_inputs) {
    sanitize_cov_tag <- function(x) {
      tag <- gsub("[^A-Za-z0-9]+", "_", as.character(x))
      tag <- gsub("^_+|_+$", "", tag)
      if (!nzchar(tag)) "cov" else tag
    }
    fit_covariates <- cfg$inputs$fit$covariates
    if (is.null(fit_covariates)) fit_covariates <- list()
    if (length(fit_covariates) > 0L) {
      for (i in seq_along(fit_covariates)) {
        entry <- fit_covariates[[i]]
        if (!is.list(entry)) next
        cov_name <- if (is.null(entry$name)) "" else as.character(entry$name)
        if (!nzchar(cov_name)) next
        cov_path <- file.path(shared_paths$covariates_dir, sprintf("cov_%02d_%s.csv", i, sanitize_cov_tag(cov_name)))
        if (!file.exists(cov_path)) next
        key <- tolower(cov_name)
        if (grepl("eli", key, fixed = TRUE)) shared_cov_paths$eli <- cov_path
        if (grepl("oni", key, fixed = TRUE)) shared_cov_paths$oni <- cov_path
        if (grepl("ppt", key, fixed = TRUE) || grepl("precip", key, fixed = TRUE)) shared_cov_paths$ppt <- cov_path
        if (grepl("soil", key, fixed = TRUE)) shared_cov_paths$soil <- cov_path
        if (grepl("pca", key, fixed = TRUE)) shared_cov_paths$pca <- cov_path
      }
    }
  }

  quantiles <- as.numeric(cfg$fit$quantiles)
  univar_impl_mode <- unified_get(
    cfg,
    c("models", "exdqlm_univar", "implementation_mode"),
    default = "legacy_bridge"
  )
  ndlm_impl_mode <- unified_get(
    cfg,
    c("models", "ndlm_main", "implementation_mode"),
    default = "legacy_bridge"
  )

  if (isTRUE(cfg$models$run_exdqlm_multivar)) {
    run_one_quantile <- function(q) {
      q_num <- as.integer(round(q * 100))
      q_label <- sprintf("%02d", q_num)
      q_root <- file.path(fit_root, sprintf("q=%s", q_label))
      q_outputs <- file.path(q_root, "outputs")
      q_logs <- file.path(q_root, "logs")
      dir.create(q_outputs, recursive = TRUE, showWarnings = FALSE)
      dir.create(q_logs, recursive = TRUE, showWarnings = FALSE)

      env_overrides <- c(
        DISC_BASE_SEED = as.character(cfg$run$seed),
        DISC_USE_PREV = if (isTRUE(cfg$fit$warm_start$enabled)) "TRUE" else "FALSE",
        DISC_W_OUTPUT_DIR = q_outputs,
        DISC_W_PARAMETERS_PATH = parameters_copy,
        DISC_W_RETROS_PATH = adapted_retros,
        DISC_W_NWS_PATH = adapted_nws,
        DISC_W_GLOFAS_PATH = adapted_glofas
      )
      env_kv <- sprintf("%s=%s", names(env_overrides), unname(env_overrides))

      log_path <- file.path(q_logs, "fit.log")
      cmd_out <- system2(
        "Rscript",
        c("--vanilla", file.path("scripts", "run_DISC_Optimal_Synth_Ranges_W.R"), as.character(q), as.character(cfg$run$seed)),
        stdout = TRUE,
        stderr = TRUE,
        env = env_kv
      )
      writeLines(cmd_out, log_path, useBytes = TRUE)

      output_path <- file.path(q_outputs, sprintf("DISC_variables_%d_exAL_synth_DISC.RData", q_num))
      list(
        quantile = q,
        output_path = output_path,
        log_path = log_path,
        status = attr(cmd_out, "status")
      )
    }

    workers <- suppressWarnings(as.integer(cfg$run$threads$mc_cores))
    if (!is.finite(workers) || workers < 1) workers <- 1L
    workers <- min(workers, length(quantiles))

    results <- if (workers > 1 && .Platform$OS.type != "windows") {
      parallel::mclapply(quantiles, run_one_quantile, mc.cores = workers)
    } else {
      lapply(quantiles, run_one_quantile)
    }

    for (res in results) {
      if (!is.null(res$status) && res$status != 0) {
        stop(sprintf("fit stage failed for quantile %s; see %s", res$quantile, res$log_path), call. = FALSE)
      }
      if (file.exists(res$output_path)) {
        manifest <- unified_manifest_add_artifact(
          manifest,
          res$output_path,
          storage_scale = "model_state",
          flow_domain = cfg$scale_contract$analysis_scale_fit_internal
        )
      }
    }
  }

  if (isTRUE(cfg$models$run_exdqlm_univar)) {
    if (!use_shared_inputs) {
      stop(
        "legacy univariate bridge requires run-scoped shared inputs. Enable stages.data_prep_shared and provide shared bundle inputs.",
        call. = FALSE
      )
    }
    required_cov_keys <- c("eli", "oni", "ppt", "soil", "pca")
    missing_cov <- required_cov_keys[!nzchar(unlist(shared_cov_paths[required_cov_keys], use.names = FALSE))]
    if (length(missing_cov) > 0L) {
      stop(
        sprintf(
          "legacy univariate bridge missing shared covariates in run bundle: %s",
          paste(missing_cov, collapse = ", ")
        ),
        call. = FALSE
      )
    }
    univar_script <- if (identical(univar_impl_mode, "theory_aligned")) {
      file.path(repo_root, "scripts", "run_exdqlm_univar.R")
    } else {
      file.path(repo_root, "OptimalModelSLexAL.r")
    }
    if (!file.exists(univar_script)) {
      stop(
        sprintf("univariate script not found for implementation_mode=%s: %s", univar_impl_mode, univar_script),
        call. = FALSE
      )
    }

    for (q in quantiles) {
      q_num <- as.integer(round(q * 100))
      q_lab <- sprintf("%02d", q_num)

      q_root <- file.path(fit_root, "exdqlm_univar", sprintf("q=%s", q_lab))
      q_outputs <- file.path(q_root, "outputs")
      q_logs <- file.path(q_root, "logs")
      dir.create(q_outputs, recursive = TRUE, showWarnings = FALSE)
      dir.create(q_logs, recursive = TRUE, showWarnings = FALSE)

      output_path <- file.path(q_outputs, sprintf("variables_%s_exAL_synth_DISC_uni.RData", q_lab))
      log_name <- if (identical(univar_impl_mode, "theory_aligned")) "univar_theory.log" else "univar_legacy.log"
      log_path <- file.path(q_logs, log_name)
      env_overrides <- c(
        UNIFIED_UNIV_RDATA_OUT = output_path,
        UNIV_RUN_ROOT = run_root_abs,
        UNIV_OUT_DIR = q_outputs,
        UNIV_SHARED_INPUT_ROOT = shared_paths$root,
        UNIV_PARAMETERS_TXT = source_parameters,
        UNIV_RETROS_CSV = source_retros,
        UNIV_NWS_FORECAST_CSV = source_nws,
        UNIV_GLOFAS_FORECAST_CSV = source_glofas,
        UNIV_COVARIATES_DIR = shared_paths$covariates_dir,
        UNIV_COV1_ELI_CSV = shared_cov_paths$eli,
        UNIV_COV2_ONI_CSV = shared_cov_paths$oni,
        UNIV_PPT_CSV = shared_cov_paths$ppt,
        UNIV_SOIL_CSV = shared_cov_paths$soil,
        UNIV_PCA_CSV = shared_cov_paths$pca,
        UNIV_USE_PREV = if (isTRUE(cfg$fit$warm_start$enabled)) "TRUE" else "FALSE",
        UNIV_PREV_RDATA = output_path,
        UNIV_THEORY_SUMMARY_LOG = file.path(q_logs, "univar_theory_summary.log")
      )
      env_kv <- sprintf("%s=%s", names(env_overrides), unname(env_overrides))

      script_args <- if (identical(univar_impl_mode, "theory_aligned")) {
        c("--vanilla", univar_script, as.character(q), as.character(cfg$run$seed))
      } else {
        c("--vanilla", univar_script, as.character(q))
      }
      cmd_out <- system2(
        "Rscript",
        script_args,
        stdout = TRUE,
        stderr = TRUE,
        env = env_kv
      )
      writeLines(cmd_out, log_path, useBytes = TRUE)
      status <- attr(cmd_out, "status")
      if (!is.null(status) && status != 0) {
        stop(
          sprintf(
            "univariate fit failed for quantile %s (implementation_mode=%s); see %s",
            q,
            univar_impl_mode,
            log_path
          ),
          call. = FALSE
        )
      }
      if (!file.exists(output_path)) {
        stop(
          sprintf(
            "univariate output missing for quantile %s (implementation_mode=%s): %s",
            q,
            univar_impl_mode,
            output_path
          ),
          call. = FALSE
        )
      }

      manifest <- unified_manifest_add_artifact(
        manifest,
        output_path,
        storage_scale = "model_state",
        flow_domain = cfg$scale_contract$analysis_scale_fit_internal
      )
      if (file.exists(log_path)) {
        manifest <- unified_manifest_add_artifact(manifest, log_path, storage_scale = "text")
      }
    }
  }

  if (isTRUE(cfg$models$run_ndlm_main)) {
    if (!use_shared_inputs) {
      stop(
        "legacy NDLM bridge requires run-scoped shared inputs. Enable stages.data_prep_shared and provide shared bundle inputs.",
        call. = FALSE
      )
    }
    required_cov_keys <- c("eli", "oni", "ppt", "soil", "pca")
    missing_cov <- required_cov_keys[!nzchar(unlist(shared_cov_paths[required_cov_keys], use.names = FALSE))]
    if (length(missing_cov) > 0L) {
      stop(
        sprintf(
          "legacy NDLM bridge missing shared covariates in run bundle: %s",
          paste(missing_cov, collapse = ", ")
        ),
        call. = FALSE
      )
    }
    ndlm_script <- if (identical(ndlm_impl_mode, "theory_aligned")) {
      file.path(repo_root, "scripts", "run_ndlm_main.R")
    } else {
      file.path(repo_root, "DISC_Optimal_Synth_Ranges_NDLM.r")
    }
    if (!file.exists(ndlm_script)) {
      stop(
        sprintf("NDLM script not found for implementation_mode=%s: %s", ndlm_impl_mode, ndlm_script),
        call. = FALSE
      )
    }

    ndlm_root <- file.path(fit_root, "ndlm_main")
    ndlm_outputs <- file.path(ndlm_root, "outputs")
    ndlm_logs <- file.path(ndlm_root, "logs")
    dir.create(ndlm_outputs, recursive = TRUE, showWarnings = FALSE)
    dir.create(ndlm_logs, recursive = TRUE, showWarnings = FALSE)

    output_path <- file.path(ndlm_outputs, "DISC_variables_50_NDLM_synth_DISC.RData")
    log_name <- if (identical(ndlm_impl_mode, "theory_aligned")) "ndlm_theory.log" else "ndlm_legacy.log"
    log_path <- file.path(ndlm_logs, log_name)
    env_overrides <- c(
      UNIFIED_NDLM_RDATA_OUT = output_path,
      NDLM_RUN_ROOT = run_root_abs,
      NDLM_OUT_DIR = ndlm_outputs,
      NDLM_SHARED_INPUT_ROOT = shared_paths$root,
      NDLM_PARAMETERS_TXT = source_parameters,
      NDLM_RETROS_CSV = source_retros,
      NDLM_NWS_FORECAST_CSV = source_nws,
      NDLM_GLOFAS_FORECAST_CSV = source_glofas,
      NDLM_COVARIATES_DIR = shared_paths$covariates_dir,
      NDLM_COV1_ELI_CSV = shared_cov_paths$eli,
      NDLM_COV2_ONI_CSV = shared_cov_paths$oni,
      NDLM_PPT_CSV = shared_cov_paths$ppt,
      NDLM_SOIL_CSV = shared_cov_paths$soil,
      NDLM_PCA_CSV = shared_cov_paths$pca,
      NDLM_USE_PREV = if (isTRUE(cfg$fit$warm_start$enabled)) "TRUE" else "FALSE",
      NDLM_PREV_RDATA = output_path,
      NDLM_THEORY_SUMMARY_LOG = file.path(ndlm_logs, "ndlm_theory_summary.log")
    )
    env_kv <- sprintf("%s=%s", names(env_overrides), unname(env_overrides))

    script_args <- if (identical(ndlm_impl_mode, "theory_aligned")) {
      c("--vanilla", ndlm_script, as.character(cfg$run$seed))
    } else {
      c("--vanilla", ndlm_script)
    }
    cmd_out <- system2(
      "Rscript",
      script_args,
      stdout = TRUE,
      stderr = TRUE,
      env = env_kv
    )
    writeLines(cmd_out, log_path, useBytes = TRUE)
    status <- attr(cmd_out, "status")
    if (!is.null(status) && status != 0) {
      stop(
        sprintf("NDLM fit failed (implementation_mode=%s); see %s", ndlm_impl_mode, log_path),
        call. = FALSE
      )
    }
    if (!file.exists(output_path)) {
      stop(
        sprintf("NDLM output missing (implementation_mode=%s): %s", ndlm_impl_mode, output_path),
        call. = FALSE
      )
    }

    manifest <- unified_manifest_add_artifact(
      manifest,
      output_path,
      storage_scale = "model_state",
      flow_domain = cfg$scale_contract$analysis_scale_fit_internal
    )
    if (file.exists(log_path)) {
      manifest <- unified_manifest_add_artifact(manifest, log_path, storage_scale = "text")
    }
  }

  list(manifest = manifest)
}
