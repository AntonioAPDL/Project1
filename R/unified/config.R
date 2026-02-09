# unified/config.R

unified_scale_enum <- c("raw_cms", "log_cms", "log1p_cms", "log_log_cms", "log_log1p_cms")

unified_config_defaults <- function() {
  list(
    config_version = 1L,
    run = list(
      run_id = NULL,
      run_root = "repro/runs",
      repro_mode = "strict",
      seed = 777L,
      overwrite = FALSE,
      dry_run = FALSE,
      git_require_clean = FALSE,
      threads = list(
        omp = 1L,
        openblas = 1L,
        mkl = 1L,
        veclib = 1L,
        numexpr = 1L,
        mc_cores = 1L
      )
    ),
    stages = list(
      forecats = TRUE,
      fit = TRUE,
      post = TRUE,
      validate = TRUE,
      report = TRUE
    ),
    site = list(
      usgs_site = "11160500",
      lat = 37.0443931,
      lon = -122.072464
    ),
    dates = list(
      cutoff_date = "2022-12-25",
      plot_start = "2022-12-07",
      plot_end = "2023-01-22"
    ),
    inputs = list(
      fit = list(
        parameters_path = NULL,
        retros_path = NULL,
        retros_storage_scale = "log1p_cms",
        nws_forecast_path = NULL,
        nws_storage_scale = "log1p_cms",
        glofas_forecast_path = NULL,
        glofas_storage_scale = "log1p_cms",
        usgs_mode = "live",
        usgs_cache_path = NULL
      ),
      post = list(
        use_fit_outputs_from_run = TRUE
      ),
      forecats = list(
        mode = "use_existing",
        pipeline_config_path = "config/forecats_pipeline.template.yaml",
        existing_bundle_path = NULL
      )
    ),
    fit = list(
      quantiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95),
      warm_start = list(
        enabled = FALSE,
        source_run_id = NULL,
        mode = "resume"
      )
    ),
    post = list(
      figures = TRUE,
      profile = FALSE,
      profile_detail = FALSE,
      sort_keep_na = TRUE,
      export_tables = TRUE
    ),
    validation = list(
      canonical_run_id = NULL,
      compare = list(
        mode = "both",
        numeric_abs_tol = 0,
        numeric_rel_tol = 0,
        pixel_max_abs_tol = 0
      )
    ),
    scale_contract = list(
      canonical_storage_scale = "raw_cms",
      legacy_fit_input_scale = "log1p_cms",
      legacy_post_input_scale = "log1p_cms",
      analysis_scale_fit_internal = "log_log1p_cms",
      analysis_scale_post_internal = "log_log1p_cms"
    ),
    write_audit = list(
      enabled = TRUE,
      enforce_from_stage = 4L,
      allowlist_outside_run_root = list()
    )
  )
}

unified_deep_merge <- function(defaults, user) {
  if (is.null(user)) {
    return(defaults)
  }
  if (!is.list(defaults) || !is.list(user)) {
    return(user)
  }

  out <- defaults
  all_names <- union(names(defaults), names(user))
  for (nm in all_names) {
    has_default <- nm %in% names(defaults)
    has_user <- nm %in% names(user)
    if (has_default && has_user) {
      out[[nm]] <- unified_deep_merge(defaults[[nm]], user[[nm]])
    } else if (has_user) {
      out[[nm]] <- user[[nm]]
    }
  }
  out
}

unified_get <- function(x, path, default = NULL) {
  cur <- x
  for (p in path) {
    if (!is.list(cur) || !(p %in% names(cur))) {
      return(default)
    }
    cur <- cur[[p]]
  }
  cur
}

unified_set <- function(x, path, value) {
  if (length(path) == 1) {
    x[[path[[1]]]] <- value
    return(x)
  }
  head <- path[[1]]
  if (is.null(x[[head]]) || !is.list(x[[head]])) {
    x[[head]] <- list()
  }
  x[[head]] <- unified_set(x[[head]], path[-1], value)
  x
}

unified_is_abs <- function(path) {
  grepl("^(/|[A-Za-z]:[/\\\\])", path)
}

unified_resolve_path <- function(path, repo_root) {
  if (is.null(path) || !nzchar(path)) return(NULL)
  if (unified_is_abs(path)) {
    return(normalizePath(path, mustWork = FALSE))
  }
  normalizePath(file.path(repo_root, path), mustWork = FALSE)
}

unified_resolve_paths <- function(cfg, repo_root) {
  path_keys <- list(
    c("run", "run_root"),
    c("inputs", "fit", "parameters_path"),
    c("inputs", "fit", "retros_path"),
    c("inputs", "fit", "nws_forecast_path"),
    c("inputs", "fit", "glofas_forecast_path"),
    c("inputs", "fit", "usgs_cache_path"),
    c("inputs", "forecats", "pipeline_config_path"),
    c("inputs", "forecats", "existing_bundle_path")
  )

  for (key in path_keys) {
    val <- unified_get(cfg, key, default = NULL)
    resolved <- unified_resolve_path(val, repo_root)
    cfg <- unified_set(cfg, key, resolved)
  }

  cfg
}

unified_validate_config <- function(cfg) {
  errs <- character(0)

  add_err <- function(msg) {
    errs <<- c(errs, msg)
  }

  if (is.null(cfg$config_version) || !is.numeric(cfg$config_version)) {
    add_err("config_version must be numeric/integer")
  }

  repro_mode <- unified_get(cfg, c("run", "repro_mode"), default = NULL)
  if (!(repro_mode %in% c("strict", "fast"))) {
    add_err("run.repro_mode must be one of: strict, fast")
  }

  post_export_tables <- unified_get(cfg, c("post", "export_tables"), default = TRUE)
  if (!isTRUE(post_export_tables) && !identical(post_export_tables, FALSE)) {
    add_err("post.export_tables must be boolean (true/false)")
  }

  check_required_file <- function(path, key) {
    if (is.null(path) || !nzchar(path)) {
      add_err(sprintf("%s is required and must not be null", key))
    } else if (!file.exists(path)) {
      add_err(sprintf("%s does not exist: %s", key, path))
    }
  }

  if (isTRUE(unified_get(cfg, c("stages", "fit"), FALSE))) {
    check_required_file(unified_get(cfg, c("inputs", "fit", "parameters_path")), "inputs.fit.parameters_path")
    check_required_file(unified_get(cfg, c("inputs", "fit", "retros_path")), "inputs.fit.retros_path")
    check_required_file(unified_get(cfg, c("inputs", "fit", "nws_forecast_path")), "inputs.fit.nws_forecast_path")
    check_required_file(unified_get(cfg, c("inputs", "fit", "glofas_forecast_path")), "inputs.fit.glofas_forecast_path")
  }

  if (identical(unified_get(cfg, c("inputs", "fit", "usgs_mode"), "live"), "cache")) {
    check_required_file(unified_get(cfg, c("inputs", "fit", "usgs_cache_path")), "inputs.fit.usgs_cache_path")
  }

  if (isTRUE(unified_get(cfg, c("stages", "forecats"), FALSE))) {
    forecats_mode <- unified_get(cfg, c("inputs", "forecats", "mode"), "use_existing")
    if (identical(forecats_mode, "build")) {
      check_required_file(unified_get(cfg, c("inputs", "forecats", "pipeline_config_path")), "inputs.forecats.pipeline_config_path")
    }
    if (identical(forecats_mode, "use_existing")) {
      check_required_file(unified_get(cfg, c("inputs", "forecats", "existing_bundle_path")), "inputs.forecats.existing_bundle_path")
    }
  }

  scale_keys <- list(
    c("inputs", "fit", "retros_storage_scale"),
    c("inputs", "fit", "nws_storage_scale"),
    c("inputs", "fit", "glofas_storage_scale"),
    c("scale_contract", "canonical_storage_scale"),
    c("scale_contract", "legacy_fit_input_scale"),
    c("scale_contract", "legacy_post_input_scale"),
    c("scale_contract", "analysis_scale_fit_internal"),
    c("scale_contract", "analysis_scale_post_internal")
  )
  for (k in scale_keys) {
    val <- unified_get(cfg, k, NULL)
    key <- paste(k, collapse = ".")
    if (!(val %in% unified_scale_enum)) {
      add_err(sprintf("%s must be one of [%s]", key, paste(unified_scale_enum, collapse = ", ")))
    }
  }

  errs
}

unified_load_config <- function(config_path, repo_root = normalizePath(getwd(), mustWork = TRUE)) {
  if (!file.exists(config_path)) {
    stop("Config file does not exist: ", config_path)
  }
  if (!requireNamespace("yaml", quietly = TRUE)) {
    stop("Package 'yaml' is required to load unified config")
  }

  cfg_raw <- yaml::read_yaml(config_path)
  cfg <- unified_deep_merge(unified_config_defaults(), cfg_raw)
  cfg <- unified_resolve_paths(cfg, repo_root)

  errs <- unified_validate_config(cfg)
  if (length(errs) > 0) {
    stop(paste(c("Config validation failed:", paste0("- ", errs)), collapse = "\n"), call. = FALSE)
  }

  cfg
}
