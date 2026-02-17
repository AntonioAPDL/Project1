# unified/stages/stage_post.R

unified_stage_post <- function(cfg, run_root, repo_root, manifest) {
  run_root_abs <- normalizePath(run_root, mustWork = FALSE)
  repo_root_abs <- normalizePath(repo_root, mustWork = FALSE)
  run_id <- cfg$run$run_id
  post_use_fit_outputs_from_run <- isTRUE(unified_get(cfg, c("inputs", "post", "use_fit_outputs_from_run"), default = TRUE))
  post_source_run_id <- unified_get(cfg, c("inputs", "post", "source_run_id"), default = NULL)
  if (!is.null(post_source_run_id) && !is.character(post_source_run_id)) {
    post_source_run_id <- as.character(post_source_run_id)
  }
  post_source_run_root <- unified_get(cfg, c("inputs", "post", "source_run_root"), default = NULL)
  if (is.null(post_source_run_root) || !nzchar(post_source_run_root)) {
    post_source_run_root <- cfg$run$run_root
  }
  fit_outputs_root_abs <- run_root_abs
  if (post_use_fit_outputs_from_run &&
      !is.null(post_source_run_id) &&
      nzchar(post_source_run_id) &&
      !identical(post_source_run_id, run_id)) {
    fit_outputs_root_abs <- normalizePath(file.path(post_source_run_root, post_source_run_id), mustWork = FALSE)
    if (!dir.exists(fit_outputs_root_abs)) {
      stop(sprintf(
        "inputs.post.source_run_id requested but source run root is missing: %s",
        fit_outputs_root_abs
      ), call. = FALSE)
    }
  }
  post_root <- file.path(run_root, "post")
  post_inputs <- file.path(post_root, "inputs")
  post_logs <- file.path(post_root, "logs")
  post_cache_dir <- file.path(run_root_abs, "post", "cache")
  dir.create(post_root, recursive = TRUE, showWarnings = FALSE)
  dir.create(post_inputs, recursive = TRUE, showWarnings = FALSE)
  dir.create(post_logs, recursive = TRUE, showWarnings = FALSE)
  dir.create(post_cache_dir, recursive = TRUE, showWarnings = FALSE)

  shared_input_run_root <- run_root
  if (dir.exists(file.path(fit_outputs_root_abs, "inputs", "shared"))) {
    shared_input_run_root <- fit_outputs_root_abs
  }
  shared_paths <- unified_shared_input_paths(shared_input_run_root)
  use_shared_inputs <- isTRUE(cfg$stages$data_prep_shared) || dir.exists(shared_paths$root)
  if (use_shared_inputs) {
    shared_validation <- unified_validate_required_shared_inputs(
      run_root = shared_input_run_root,
      stage_name = "post",
      manifest = manifest,
      enabled_models = cfg$models
    )
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
    source_retros <- cfg$inputs$fit$retros_path
    source_nws <- cfg$inputs$fit$nws_forecast_path
    source_glofas <- cfg$inputs$fit$glofas_forecast_path
    source_retros_scale <- cfg$inputs$fit$retros_storage_scale
    source_nws_scale <- cfg$inputs$fit$nws_storage_scale
    source_glofas_scale <- cfg$inputs$fit$glofas_storage_scale
  }

  legacy_scale <- cfg$scale_contract$legacy_post_input_scale
  unified_assert_known_scale(legacy_scale, "scale_contract.legacy_post_input_scale")

  adapted_retros <- file.path(post_inputs, "retros_post_adapter.csv")
  adapted_nws <- file.path(post_inputs, "nws_post_adapter.csv")
  adapted_glofas <- file.path(post_inputs, "glofas_post_adapter.csv")

  unified_adapt_csv_scale(
    input_path = source_retros,
    output_path = adapted_retros,
    from_scale = source_retros_scale,
    to_scale = legacy_scale,
    positive_required = TRUE
  )
  manifest <- unified_manifest_add_scale_history(
    manifest,
    artifact = "post_input/retros",
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
    artifact = "post_input/nws_forecast",
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
    artifact = "post_input/glofas_forecast",
    from_scale = source_glofas_scale,
    to_scale = legacy_scale,
    transform = sprintf("adapter_%s_to_%s", source_glofas_scale, legacy_scale)
  )

  manifest <- unified_manifest_add_artifact(manifest, adapted_retros, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_nws, storage_scale = legacy_scale)
  manifest <- unified_manifest_add_artifact(manifest, adapted_glofas, storage_scale = legacy_scale)

  repro_mode <- cfg$run$repro_mode
  if (is.null(repro_mode) || !nzchar(repro_mode)) repro_mode <- "strict"
  repro_mode <- as.character(repro_mode)
  strict_repro <- identical(tolower(repro_mode), "strict")
  legacy_fallback_requested <- isTRUE(cfg$post$allow_legacy_root_fallback)
  if (legacy_fallback_requested) {
    warning(
      "post.allow_legacy_root_fallback is deprecated and should remain false; this compatibility path will be removed in a future cutover.",
      call. = FALSE
    )
  }
  allow_legacy_root_fallback <- legacy_fallback_requested && !strict_repro
  quantiles <- as.numeric(cfg$fit$quantiles)
  q_num <- as.integer(round(quantiles * 100))
  q_labels <- sprintf("%02d", q_num)

  resolve_manifest_paths <- function(patterns, family_name, fallback_rel_paths = NULL) {
    allowed_roots <- unique(c(run_root_abs, fit_outputs_root_abs))
    is_under_allowed_roots <- function(path) {
      abs_path <- path.expand(path)
      any(vapply(allowed_roots, function(root) {
        startsWith(abs_path, paste0(root, .Platform$file.sep)) || identical(abs_path, root)
      }, logical(1)))
    }

    paths <- vapply(patterns, function(pattern) {
      unified_first_artifact_path(manifest, pattern = pattern, must_exist = FALSE)
    }, character(1))
    names(paths) <- names(patterns)

    if (!is.null(fallback_rel_paths)) {
      for (nm in names(paths)) {
        rel <- fallback_rel_paths[[nm]]
        rel <- if (is.null(rel)) "" else as.character(rel)
        if (!nzchar(rel)) next
        candidate <- file.path(fit_outputs_root_abs, rel)
        if (!file.exists(candidate)) next

        if (!nzchar(paths[[nm]])) {
          paths[[nm]] <- candidate
          next
        }

        if (strict_repro && !is_under_allowed_roots(paths[[nm]])) {
          paths[[nm]] <- candidate
        }
      }
    }

    missing <- names(paths)[!nzchar(paths)]
    if (length(missing) > 0L) {
      msg <- sprintf(
        "post stage missing run-scoped %s artifacts for keys: %s",
        family_name,
        paste(missing, collapse = ", ")
      )
      if (strict_repro) {
        stop(msg, call. = FALSE)
      } else {
        warning(msg, call. = FALSE)
      }
    }
    existing <- paths[nzchar(paths)]
    if (length(existing) == 0L) {
      return(character(0))
    }
    unified_artifact_paths_to_absolute(existing, run_root = fit_outputs_root_abs, repo_root = repo_root_abs, must_exist = strict_repro)
  }

  disc_w_paths_abs <- character(0)
  if (isTRUE(cfg$models$run_exdqlm_multivar)) {
    patterns <- setNames(
      sprintf("fit/q=%s/outputs/DISC_variables_%d_exAL_synth_DISC\\.RData$", q_labels, q_num),
      q_labels
    )
    fallback_rel <- setNames(
      sprintf("fit/q=%s/outputs/DISC_variables_%d_exAL_synth_DISC.RData", q_labels, q_num),
      q_labels
    )
    disc_w_paths_abs <- resolve_manifest_paths(patterns, "DISC-W", fallback_rel_paths = fallback_rel)
  }

  univ_paths_abs <- character(0)
  if (isTRUE(cfg$models$run_exdqlm_univar)) {
    patterns <- setNames(
      sprintf("fit/exdqlm_univar/q=%s/outputs/variables_%s_exAL_synth_DISC_uni\\.RData$", q_labels, q_labels),
      q_labels
    )
    fallback_rel <- setNames(
      sprintf("fit/exdqlm_univar/q=%s/outputs/variables_%s_exAL_synth_DISC_uni.RData", q_labels, q_labels),
      q_labels
    )
    univ_paths_abs <- resolve_manifest_paths(patterns, "univariate", fallback_rel_paths = fallback_rel)
  }

  ndlm_path_abs <- ""
  if (isTRUE(cfg$models$run_ndlm_main)) {
    ndlm_rel <- unified_first_artifact_path(
      manifest,
      pattern = "fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC\\.RData$",
      must_exist = FALSE
    )

    ndlm_fallback <- file.path(fit_outputs_root_abs, "fit", "ndlm_main", "outputs", "DISC_variables_50_NDLM_synth_DISC.RData")
    ndlm_is_run_scoped <- function(path) {
      abs_path <- path.expand(path)
      startsWith(abs_path, paste0(run_root_abs, .Platform$file.sep)) ||
        identical(abs_path, run_root_abs) ||
        startsWith(abs_path, paste0(fit_outputs_root_abs, .Platform$file.sep)) ||
        identical(abs_path, fit_outputs_root_abs)
    }

    if (file.exists(ndlm_fallback)) {
      if (!nzchar(ndlm_rel) || (strict_repro && !ndlm_is_run_scoped(ndlm_rel))) {
        ndlm_rel <- ndlm_fallback
      }
    }

    if (!nzchar(ndlm_rel)) {
      msg <- "post stage missing run-scoped NDLM artifact"
      if (strict_repro) {
        stop(msg, call. = FALSE)
      } else {
        warning(msg, call. = FALSE)
      }
    } else {
      ndlm_path_abs <- unified_artifact_path_to_absolute(
        ndlm_rel,
        run_root = fit_outputs_root_abs,
        repo_root = repo_root_abs,
        must_exist = strict_repro
      )
    }
  }

  encode_env_list <- function(x) {
    x <- as.character(x)
    if (length(x) == 0L) return("")
    paste(x, collapse = ",")
  }

  sort_keep_na <- cfg$post$sort_keep_na
  if (is.null(sort_keep_na)) sort_keep_na <- TRUE
  export_tables <- cfg$post$export_tables
  if (is.null(export_tables)) export_tables <- TRUE
  table_formats <- cfg$post$table_formats
  if (is.null(table_formats) || length(table_formats) == 0L) {
    table_formats <- "csv"
  } else {
    table_formats <- tolower(as.character(table_formats))
    table_formats <- table_formats[nzchar(table_formats)]
    if (length(table_formats) == 0L) table_formats <- "csv"
  }
  env_overrides <- c(
    UNIFIED_RUN_ROOT = run_root_abs,
    UNIFIED_RUN_ID = run_id,
    UNIFIED_FIT_OUTPUTS_SOURCE_ROOT = fit_outputs_root_abs,
    UNIFIED_POST_CACHE_DIR = normalizePath(post_cache_dir, mustWork = FALSE),
    UNIFIED_REPRO_MODE = repro_mode,
    UNIFIED_REQUIRE_RUNSCOPED_POST = if (strict_repro) "TRUE" else "FALSE",
    UNIFIED_ALLOW_LEGACY_POST_FALLBACK = if (allow_legacy_root_fallback) "TRUE" else "FALSE",
    UNIFIED_MODEL_RUN_EXDQLM_MULTIVAR = if (isTRUE(cfg$models$run_exdqlm_multivar)) "TRUE" else "FALSE",
    UNIFIED_MODEL_RUN_EXDQLM_UNIVAR = if (isTRUE(cfg$models$run_exdqlm_univar)) "TRUE" else "FALSE",
    UNIFIED_MODEL_RUN_NDLM_MAIN = if (isTRUE(cfg$models$run_ndlm_main)) "TRUE" else "FALSE",
    UNIFIED_POST_SMOKE_FAST = if (isTRUE(cfg$post$smoke_fast)) "TRUE" else "FALSE",
    UNIFIED_FIT_QUANTILE_LABELS = encode_env_list(q_labels),
    UNIFIED_DISC_W_RDATA_PATHS = encode_env_list(disc_w_paths_abs),
    UNIFIED_UNIV_RDATA_PATHS = encode_env_list(univ_paths_abs),
    UNIFIED_NDLM_RDATA_PATH = ndlm_path_abs,
    RUN_ID = run_id,
    PROFILE = if (isTRUE(cfg$post$profile)) "TRUE" else "FALSE",
    PROFILE_DETAIL = if (isTRUE(cfg$post$profile_detail)) "TRUE" else "FALSE",
    UNIFIED_POST_FIGURES = if (isTRUE(cfg$post$figures)) "TRUE" else "FALSE",
    ENV_SORT_KEEP_NA = if (isTRUE(sort_keep_na)) "TRUE" else "FALSE",
    EXPORT_TABLES = if (isTRUE(export_tables)) "TRUE" else "FALSE",
    EXPORT_TABLE_FORMATS = paste(unique(table_formats), collapse = ","),
    ENV_PROJECT_ROOT = repo_root_abs,
    ENV_RETROS_PATH = normalizePath(adapted_retros, mustWork = FALSE),
    ENV_NWS_FORECAST_PATH = normalizePath(adapted_nws, mustWork = FALSE),
    ENV_GLOFAS_FORECAST_PATH = normalizePath(adapted_glofas, mustWork = FALSE)
  )

  log_path <- file.path(post_logs, "post_runner.log")
  env_kv <- sprintf("%s=%s", names(env_overrides), unname(env_overrides))
  cmd_out <- system2(
    "Rscript",
    c("--vanilla", file.path("scripts", "run_environmetrics_figures.R")),
    stdout = TRUE,
    stderr = TRUE,
    env = env_kv
  )
  writeLines(cmd_out, log_path, useBytes = TRUE)
  status <- attr(cmd_out, "status")
  if (!is.null(status) && status != 0) {
    stop(sprintf("post stage failed; see %s", log_path), call. = FALSE)
  }

  out_dir <- file.path(run_root, "post", "outputs", run_id)
  if (dir.exists(out_dir)) {
    generated <- list.files(out_dir, full.names = TRUE, recursive = TRUE)
    allowed_ext <- "\\.(png|pdf|csv|tsv|txt|json|yaml|yml|rds)$"
    out_dir_abs <- normalizePath(out_dir, mustWork = TRUE)
    out_dir_prefix <- paste0(out_dir_abs, .Platform$file.sep)
    for (f in generated) {
      if (file.info(f)$isdir) next
      if (!grepl(allowed_ext, f, ignore.case = TRUE)) next
      f_abs <- normalizePath(f, mustWork = FALSE)
      if (!startsWith(f_abs, out_dir_prefix) && !identical(f_abs, out_dir_abs)) next

      if (grepl("\\.png$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "image_png", analysis_scale = "n/a")
      } else if (grepl("\\.pdf$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "text_binary", analysis_scale = "n/a")
      } else if (grepl("\\.rds$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "model_state")
      } else if (grepl("\\.csv$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "table_csv", analysis_scale = "n/a")
      } else if (grepl("\\.tsv$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "table_tsv", analysis_scale = "n/a")
      } else if (grepl("\\.json$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "text_json", analysis_scale = "n/a")
      } else if (grepl("\\.(yaml|yml)$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "text_yaml", analysis_scale = "n/a")
      } else if (grepl("\\.txt$", f, ignore.case = TRUE)) {
        manifest <- unified_manifest_add_artifact(manifest, f, storage_scale = "text_plain", analysis_scale = "n/a")
      }
    }
  }

  list(manifest = manifest)
}
