# unified/stages/stage_fit.R

unified_normalize_fit_worker_result <- function(res, context_label = "fit stage worker") {
  required <- c("quantile", "output_path", "log_path", "status")
  if (is.list(res) && all(required %in% names(res))) {
    return(res)
  }

  res_preview <- tryCatch(paste(utils::head(as.character(res), 5L), collapse = " | "), error = function(e) "")
  if (!nzchar(res_preview)) {
    res_preview <- sprintf("<class=%s>", paste(class(res), collapse = "/"))
  }
  stop(
    sprintf("%s returned invalid result: %s", context_label, res_preview),
    call. = FALSE
  )
}

unified_stage_fit <- function(cfg, run_root, repo_root, manifest) {
  oldwd <- getwd()
  on.exit(setwd(oldwd), add = TRUE)
  setwd(repo_root)

  run_root_abs <- normalizePath(run_root, mustWork = FALSE)
  io_settings <- unified_get_run_io_settings(cfg)
  fit_root <- file.path(run_root, "fit")
  fit_inputs <- file.path(fit_root, "inputs")
  fit_logs_root <- file.path(fit_root, "logs")
  preflight_dir <- file.path(run_root, "preflight")
  fit_preflight_log <- file.path(fit_logs_root, "preflight.log")
  dir.create(fit_inputs, recursive = TRUE, showWarnings = FALSE)
  dir.create(fit_logs_root, recursive = TRUE, showWarnings = FALSE)
  dir.create(preflight_dir, recursive = TRUE, showWarnings = FALSE)

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
    default = "theory_aligned"
  )
  ndlm_impl_mode <- unified_get(
    cfg,
    c("models", "ndlm_main", "implementation_mode"),
    default = "theory_aligned"
  )
  if (isTRUE(cfg$models$run_exdqlm_univar) && identical(univar_impl_mode, "legacy_bridge")) {
    warning(
      "models.exdqlm_univar.implementation_mode=legacy_bridge is supported but deprecated; prefer theory_aligned.",
      call. = FALSE
    )
  }
  if (isTRUE(cfg$models$run_ndlm_main) && identical(ndlm_impl_mode, "legacy_bridge")) {
    warning(
      "models.ndlm_main.implementation_mode=legacy_bridge is supported but deprecated; prefer theory_aligned.",
      call. = FALSE
    )
  }
  contract_checks_enabled <- isTRUE(unified_get(cfg, c("fit", "contract_checks", "enabled"), default = FALSE))
  contract_checks_fail_fast <- isTRUE(unified_get(cfg, c("fit", "contract_checks", "fail_fast"), default = TRUE))
  contract_checks_write_reports <- isTRUE(unified_get(cfg, c("fit", "contract_checks", "write_reports"), default = TRUE))
  diagnostics_enabled <- isTRUE(unified_get(cfg, c("fit", "diagnostics", "enabled"), default = FALSE))
  diagnostics_fail_fast <- isTRUE(unified_get(cfg, c("fit", "diagnostics", "fail_fast"), default = TRUE))
  diagnostics_write_reports <- isTRUE(unified_get(cfg, c("fit", "diagnostics", "write_reports"), default = TRUE))
  diagnostics_settings <- list(
    max_time_checks = as.integer(unified_get(cfg, c("fit", "diagnostics", "max_time_checks"), default = 25L)),
    seed = as.integer(unified_get(cfg, c("fit", "diagnostics", "seed"), default = cfg$run$seed)),
    psd_tol = as.numeric(unified_get(cfg, c("fit", "diagnostics", "psd_tol"), default = -1e-10))
  )

  add_report_artifacts <- function(manifest, report_paths, role) {
    report_paths <- unlist(report_paths, use.names = FALSE)
    report_paths <- report_paths[nzchar(report_paths)]
    if (length(report_paths) > 0L) {
      for (rp in report_paths) {
        if (file.exists(rp)) {
          manifest <- unified_manifest_add_artifact(
            manifest,
            rp,
            storage_scale = "text",
            role = role
          )
        }
      }
    }
    manifest
  }

  run_preflight_check <- function(path, check_point, context, stage_label) {
    if (!isTRUE(io_settings$enabled)) {
      return(list(status = "disabled", report_path = NULL))
    }
    unified_run_io_preflight(
      path = path,
      io_settings = io_settings,
      check_point = check_point,
      context = context,
      report_dir = preflight_dir,
      stage_label = stage_label,
      log_path = fit_preflight_log
    )
  }

  add_preflight_artifact <- function(manifest, preflight_result) {
    rp <- preflight_result$report_path
    if (!is.null(rp) && nzchar(rp) && file.exists(rp)) {
      manifest <- unified_manifest_add_artifact(
        manifest,
        rp,
        storage_scale = "text",
        role = "preflight"
      )
    }
    manifest
  }

  fit_preflight <- run_preflight_check(
    path = fit_root,
    check_point = "fit_start",
    context = "stage_fit preflight",
    stage_label = "fit_start"
  )
  manifest <- add_preflight_artifact(manifest, fit_preflight)

  if (isTRUE(cfg$models$run_exdqlm_multivar)) {
    run_one_quantile <- function(q) {
      q_num <- as.integer(round(q * 100))
      q_label <- sprintf("%02d", q_num)
      q_root <- file.path(fit_root, sprintf("q=%s", q_label))
      q_outputs <- file.path(q_root, "outputs")
      q_logs <- file.path(q_root, "logs")
      dir.create(q_outputs, recursive = TRUE, showWarnings = FALSE)
      dir.create(q_logs, recursive = TRUE, showWarnings = FALSE)
      if (isTRUE(io_settings$enabled)) {
        run_preflight_check(
          path = q_outputs,
          check_point = "continue",
          context = sprintf("stage_fit quantile q=%s", q_label),
          stage_label = sprintf("fit_multivar_q%s", q_label)
        )
      }

      env_overrides <- c(
        DISC_BASE_SEED = as.character(cfg$run$seed),
        DISC_USE_PREV = if (isTRUE(cfg$fit$warm_start$enabled)) "TRUE" else "FALSE",
        DISC_W_OUTPUT_DIR = q_outputs,
        DISC_W_PARAMETERS_PATH = parameters_copy,
        DISC_W_RETROS_PATH = adapted_retros,
        DISC_W_NWS_PATH = adapted_nws,
        DISC_W_GLOFAS_PATH = adapted_glofas,
        DISC_GAMSIG_FREEZE_ITERS = as.character(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "warmup_freeze_iters"), default = 20L
        )),
        DISC_GAMSIG_FREEZE_TARGET = as.character(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "freeze_target"), default = "gamma_sigma"
        )),
        DISC_GAMSIG_GUARD_REFREEZE_ITERS = as.character(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "guard_refreeze_iters"), default = 10L
        )),
        DISC_GAMSIG_INIT_MODE = as.character(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "init", "mode"), default = "robust"
        )),
        DISC_GAMSIG_INIT_GAMMA = as.character(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "init", "gamma"), default = 0.0
        )),
        DISC_GAMSIG_INIT_SIGMA_FLOOR = as.character(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "init", "sigma_floor"), default = 1e-3
        )),
        DISC_GAMSIG_INIT_SIGMA_SCALE = as.character(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "init", "sigma_scale"), default = 1.0
        )),
        DISC_GAMSIG_OBJECTIVE_GUARD_ENABLED = if (isTRUE(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "objective_guard", "enabled"), default = TRUE
        ))) "TRUE" else "FALSE",
        DISC_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST = if (isTRUE(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "objective_guard", "fail_fast"), default = FALSE
        ))) "TRUE" else "FALSE",
        DISC_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES = if (isTRUE(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "objective_guard", "log_failures"), default = TRUE
        ))) "TRUE" else "FALSE",
        DISC_GAMSIG_OBJECTIVE_GUARD_MODE = as.character(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "objective_guard", "mode"), default = "adaptive_freeze"
        )),
        DISC_GAMSIG_OBJECTIVE_GUARD_PENALTY = as.character(unified_get(
          cfg, c("fit", "exdqlm_multivar", "gamma_sigma", "objective_guard", "penalty"), default = 1e12
        ))
      )
      env_kv <- sprintf("%s=%s", names(env_overrides), unname(env_overrides))

      log_path <- file.path(q_logs, "fit.log")
      cmd_status <- suppressWarnings(system2(
        "Rscript",
        c("--vanilla", file.path("scripts", "run_DISC_Optimal_Synth_Ranges_W.R"), as.character(q), as.character(cfg$run$seed)),
        stdout = log_path,
        stderr = log_path,
        env = env_kv
      ))
      if (!is.finite(cmd_status)) cmd_status <- 0L

      output_path <- file.path(q_outputs, sprintf("DISC_variables_%d_exAL_synth_DISC.RData", q_num))
      list(
        quantile = q,
        output_path = output_path,
        log_path = log_path,
        status = as.integer(cmd_status)
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

    for (res_raw in results) {
      res <- unified_normalize_fit_worker_result(res_raw, context_label = "fit stage parallel worker")
      if (!is.null(res$status) && res$status != 0) {
        stop(sprintf("fit stage failed for quantile %s; see %s", res$quantile, res$log_path), call. = FALSE)
      }
      file_size <- suppressWarnings(file.info(res$output_path)$size)
      if (!file.exists(res$output_path) || !is.finite(file_size) || file_size <= 0) {
        stop(
          sprintf("fit stage output missing or empty for quantile %s: %s", res$quantile, res$output_path),
          call. = FALSE
        )
      }
      manifest <- unified_manifest_add_artifact(
        manifest,
        res$output_path,
        storage_scale = "model_state",
        flow_domain = cfg$scale_contract$analysis_scale_fit_internal
      )
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
      if (isTRUE(io_settings$enabled)) {
        preflight_univar <- run_preflight_check(
          path = q_outputs,
          check_point = "continue",
          context = sprintf("stage_fit univar q=%s", q_lab),
          stage_label = sprintf("fit_univar_q%s", q_lab)
        )
        manifest <- add_preflight_artifact(manifest, preflight_univar)
      }
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
        UNIV_GAMSIG_FREEZE_ITERS = as.character(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "warmup_freeze_iters"), default = 20L
        )),
        UNIV_GAMSIG_FREEZE_TARGET = as.character(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "freeze_target"), default = "gamma_sigma"
        )),
        UNIV_GAMSIG_GUARD_REFREEZE_ITERS = as.character(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "guard_refreeze_iters"), default = 10L
        )),
        UNIV_GAMSIG_INIT_MODE = as.character(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "init", "mode"), default = "robust"
        )),
        UNIV_GAMSIG_INIT_GAMMA = as.character(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "init", "gamma"), default = 0.0
        )),
        UNIV_GAMSIG_INIT_SIGMA_FLOOR = as.character(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "init", "sigma_floor"), default = 1e-3
        )),
        UNIV_GAMSIG_INIT_SIGMA_SCALE = as.character(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "init", "sigma_scale"), default = 1.0
        )),
        UNIV_GAMSIG_OBJECTIVE_GUARD_ENABLED = if (isTRUE(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "objective_guard", "enabled"), default = TRUE
        ))) "TRUE" else "FALSE",
        UNIV_GAMSIG_OBJECTIVE_GUARD_FAIL_FAST = if (isTRUE(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "objective_guard", "fail_fast"), default = FALSE
        ))) "TRUE" else "FALSE",
        UNIV_GAMSIG_OBJECTIVE_GUARD_LOG_FAILURES = if (isTRUE(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "objective_guard", "log_failures"), default = TRUE
        ))) "TRUE" else "FALSE",
        UNIV_GAMSIG_OBJECTIVE_GUARD_MODE = as.character(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "objective_guard", "mode"), default = "adaptive_freeze"
        )),
        UNIV_GAMSIG_OBJECTIVE_GUARD_PENALTY = as.character(unified_get(
          cfg, c("fit", "exdqlm_univar", "gamma_sigma", "objective_guard", "penalty"), default = 1e12
        )),
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

      if (contract_checks_enabled && identical(univar_impl_mode, "theory_aligned")) {
        check_dir <- file.path(fit_root, "contract_checks", "exdqlm_univar", sprintf("q=%s", q_lab))
        check_result <- unified_contract_check_exdqlm_univar(
          rdata_path = output_path,
          q_num = q_num,
          report_dir = check_dir,
          write_reports = contract_checks_write_reports
        )
        manifest <- add_report_artifacts(manifest, check_result$report_paths, role = "contract_check")
        if (!identical(check_result$status, "pass")) {
          err_msg <- sprintf(
            "univariate contract check failed for q=%s: %s",
            q_lab,
            paste(check_result$errors, collapse = " | ")
          )
          if (contract_checks_fail_fast) {
            stop(err_msg, call. = FALSE)
          } else {
            warning(err_msg, call. = FALSE)
          }
        }
      }

      if (diagnostics_enabled && identical(univar_impl_mode, "theory_aligned")) {
        diag_dir <- file.path(fit_root, "diagnostics", "exdqlm_univar", sprintf("q=%s", q_lab))
        summary_log_path <- file.path(q_logs, "univar_theory_summary.log")
        diag_result <- unified_diag_exdqlm_univar_theory(
          rdata_path = output_path,
          q_num = q_num,
          report_dir = diag_dir,
          summary_log_path = summary_log_path,
          settings = diagnostics_settings,
          write_reports = diagnostics_write_reports
        )
        manifest <- add_report_artifacts(manifest, diag_result$report_paths, role = "diagnostics")
        if (!identical(diag_result$status, "pass")) {
          report_pointer <- unlist(diag_result$report_paths, use.names = FALSE)
          report_pointer <- report_pointer[nzchar(report_pointer)]
          pointer_msg <- if (length(report_pointer) > 0L) {
            sprintf(" (see %s)", report_pointer[[1]])
          } else {
            ""
          }
          err_msg <- sprintf(
            "univariate diagnostics failed for q=%s%s: %s",
            q_lab,
            pointer_msg,
            paste(diag_result$errors, collapse = " | ")
          )
          if (diagnostics_fail_fast) {
            stop(err_msg, call. = FALSE)
          } else {
            warning(err_msg, call. = FALSE)
          }
        }
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
    if (isTRUE(io_settings$enabled)) {
      ndlm_preflight <- run_preflight_check(
        path = ndlm_outputs,
        check_point = "continue",
        context = "stage_fit ndlm_main",
        stage_label = "fit_ndlm_main"
      )
      manifest <- add_preflight_artifact(manifest, ndlm_preflight)
    }

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

    if (contract_checks_enabled && identical(ndlm_impl_mode, "theory_aligned")) {
      check_dir <- file.path(fit_root, "contract_checks", "ndlm_main")
      summary_log_path <- file.path(ndlm_logs, "ndlm_theory_summary.log")
      check_result <- unified_contract_check_ndlm_main(
        rdata_path = output_path,
        report_dir = check_dir,
        summary_log_path = summary_log_path,
        write_reports = contract_checks_write_reports
      )
      manifest <- add_report_artifacts(manifest, check_result$report_paths, role = "contract_check")
      if (!identical(check_result$status, "pass")) {
        err_msg <- sprintf(
          "NDLM contract check failed: %s",
          paste(check_result$errors, collapse = " | ")
        )
        if (contract_checks_fail_fast) {
          stop(err_msg, call. = FALSE)
        } else {
          warning(err_msg, call. = FALSE)
        }
      }
    }

    if (diagnostics_enabled && identical(ndlm_impl_mode, "theory_aligned")) {
      diag_dir <- file.path(fit_root, "diagnostics", "ndlm_main")
      summary_log_path <- file.path(ndlm_logs, "ndlm_theory_summary.log")
      diag_result <- unified_diag_ndlm_main_theory(
        rdata_path = output_path,
        report_dir = diag_dir,
        summary_log_path = summary_log_path,
        settings = diagnostics_settings,
        write_reports = diagnostics_write_reports
      )
      manifest <- add_report_artifacts(manifest, diag_result$report_paths, role = "diagnostics")
      if (!identical(diag_result$status, "pass")) {
        report_pointer <- unlist(diag_result$report_paths, use.names = FALSE)
        report_pointer <- report_pointer[nzchar(report_pointer)]
        pointer_msg <- if (length(report_pointer) > 0L) {
          sprintf(" (see %s)", report_pointer[[1]])
        } else {
          ""
        }
        err_msg <- sprintf(
          "NDLM diagnostics failed%s: %s",
          pointer_msg,
          paste(diag_result$errors, collapse = " | ")
        )
        if (diagnostics_fail_fast) {
          stop(err_msg, call. = FALSE)
        } else {
          warning(err_msg, call. = FALSE)
        }
      }
    }
  }

  if (file.exists(fit_preflight_log)) {
    manifest <- unified_manifest_add_artifact(
      manifest,
      fit_preflight_log,
      storage_scale = "text",
      role = "preflight"
    )
  }
  if (isTRUE(io_settings$enabled) && dir.exists(preflight_dir)) {
    preflight_reports <- list.files(preflight_dir, pattern = "\\.json$", full.names = TRUE, recursive = FALSE)
    preflight_reports <- preflight_reports[file.exists(preflight_reports)]
    if (length(preflight_reports) > 0L) {
      existing_paths <- unlist(lapply(manifest$artifacts, function(x) {
        val <- x$path
        if (is.null(val)) "" else as.character(val)
      }), use.names = FALSE)
      for (rp in preflight_reports) {
        if (!(rp %in% existing_paths)) {
          manifest <- unified_manifest_add_artifact(
            manifest,
            rp,
            storage_scale = "text",
            role = "preflight"
          )
        }
      }
    }
  }

  list(manifest = manifest)
}
