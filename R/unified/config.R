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
      io = list(
        enabled = FALSE,
        min_free_gb = 20,
        min_free_gb_start = NULL,
        min_free_gb_continue = NULL,
        preflight_scope = "legacy",
        min_free_inodes_pct = 5
      ),
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
      data_prep_shared = FALSE,
      fit = TRUE,
      post = TRUE,
      validate = TRUE,
      report = TRUE
    ),
    models = list(
      run_exdqlm_multivar = TRUE,
      run_exdqlm_univar = FALSE,
      run_ndlm_main = FALSE,
      exdqlm_univar = list(
        implementation_mode = "legacy_bridge"
      ),
      ndlm_main = list(
        implementation_mode = "legacy_bridge"
      )
    ),
    site = list(
      usgs_site = "11160500",
      lat = 37.0443931,
      lon = -122.072464
    ),
    dates = list(
      cutoff_date = "2022-12-25",
      plot_start = "2022-12-07",
      plot_end = "2023-01-22",
      data_start = NULL
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
        usgs_cache_path = NULL,
        covariates = list()
      ),
      post = list(
        use_fit_outputs_from_run = TRUE
      ),
      forecats = list(
        mode = "use_existing",
        pipeline_config_path = "config/forecats_pipeline.template.yaml",
        existing_bundle_path = NULL,
        snapshot = list(
          enabled = NULL,
          dest_rel = "inputs/shared/forecats_bundle",
          copy_list = list()
        )
      ),
      shared = list(
        prefer_forecats_snapshot = TRUE
      ),
      shared_covariates = list() # legacy compatibility
    ),
    fit = list(
      quantiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95),
      warm_start = list(
        enabled = FALSE,
        source_run_id = NULL,
        mode = "resume"
      ),
      contract_checks = list(
        enabled = FALSE,
        fail_fast = TRUE,
        write_reports = TRUE
      ),
      diagnostics = list(
        enabled = FALSE,
        fail_fast = TRUE,
        write_reports = TRUE,
        max_time_checks = 25L,
        seed = 777L,
        psd_tol = -1e-10
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
      profile = "production",
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
  # YAML sequences (unnamed lists) are replaced as a whole.
  if (is.null(names(defaults)) || is.null(names(user))) {
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

  shared_covariates <- unified_get(cfg, c("inputs", "shared_covariates"), default = list())
  if (is.null(shared_covariates)) {
    shared_covariates <- list()
  }
  shared_covariates <- unlist(shared_covariates, use.names = FALSE)
  shared_covariates <- shared_covariates[nzchar(shared_covariates)]
  if (length(shared_covariates) > 0L) {
    shared_covariates <- vapply(shared_covariates, unified_resolve_path, character(1), repo_root = repo_root)
  }
  cfg <- unified_set(cfg, c("inputs", "shared_covariates"), as.list(shared_covariates))

  fit_covariates <- unified_get(cfg, c("inputs", "fit", "covariates"), default = list())
  if (is.null(fit_covariates)) fit_covariates <- list()
  if (length(fit_covariates) > 0L) {
    for (i in seq_along(fit_covariates)) {
      entry <- fit_covariates[[i]]
      if (!is.list(entry)) next
      cov_path <- entry$path
      if (is.null(cov_path) || !nzchar(cov_path)) next
      fit_covariates[[i]]$path <- unified_resolve_path(cov_path, repo_root)
    }
  }
  cfg <- unified_set(cfg, c("inputs", "fit", "covariates"), fit_covariates)

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

  io_enabled <- unified_get(cfg, c("run", "io", "enabled"), default = FALSE)
  if (!isTRUE(io_enabled) && !identical(io_enabled, FALSE)) {
    add_err("run.io.enabled must be boolean (true/false)")
  }
  io_min_free_gb <- suppressWarnings(as.numeric(unified_get(cfg, c("run", "io", "min_free_gb"), default = 20)))
  if (!is.finite(io_min_free_gb) || io_min_free_gb < 0) {
    add_err("run.io.min_free_gb must be numeric and >= 0")
  }
  read_optional_nonneg <- function(path) {
    raw <- unified_get(cfg, path, default = NULL)
    if (is.null(raw)) return(NA_real_)
    raw_chr <- as.character(raw)
    if (!nzchar(raw_chr) || tolower(raw_chr) %in% c("null", "na", "~")) return(NA_real_)
    val <- suppressWarnings(as.numeric(raw_chr))
    if (!is.finite(val) || val < 0) return(NaN)
    val
  }
  io_min_free_gb_start <- read_optional_nonneg(c("run", "io", "min_free_gb_start"))
  if (is.nan(io_min_free_gb_start)) {
    add_err("run.io.min_free_gb_start must be null or numeric >= 0")
  }
  io_min_free_gb_continue <- read_optional_nonneg(c("run", "io", "min_free_gb_continue"))
  if (is.nan(io_min_free_gb_continue)) {
    add_err("run.io.min_free_gb_continue must be null or numeric >= 0")
  }
  io_preflight_scope <- unified_get(cfg, c("run", "io", "preflight_scope"), default = "legacy")
  if (!(io_preflight_scope %in% c("legacy", "fit_start_and_continue", "fit_start_only"))) {
    add_err("run.io.preflight_scope must be one of: legacy, fit_start_and_continue, fit_start_only")
  }
  io_min_free_inodes_pct <- suppressWarnings(as.numeric(unified_get(cfg, c("run", "io", "min_free_inodes_pct"), default = 5)))
  if (!is.finite(io_min_free_inodes_pct) || io_min_free_inodes_pct < 0 || io_min_free_inodes_pct > 100) {
    add_err("run.io.min_free_inodes_pct must be numeric in [0, 100]")
  }

  post_export_tables <- unified_get(cfg, c("post", "export_tables"), default = TRUE)
  if (!isTRUE(post_export_tables) && !identical(post_export_tables, FALSE)) {
    add_err("post.export_tables must be boolean (true/false)")
  }

  run_exdqlm_multivar <- unified_get(cfg, c("models", "run_exdqlm_multivar"), default = TRUE)
  if (!isTRUE(run_exdqlm_multivar) && !identical(run_exdqlm_multivar, FALSE)) {
    add_err("models.run_exdqlm_multivar must be boolean (true/false)")
  }

  run_exdqlm_univar <- unified_get(cfg, c("models", "run_exdqlm_univar"), default = FALSE)
  if (!isTRUE(run_exdqlm_univar) && !identical(run_exdqlm_univar, FALSE)) {
    add_err("models.run_exdqlm_univar must be boolean (true/false)")
  }

  run_ndlm_main <- unified_get(cfg, c("models", "run_ndlm_main"), default = FALSE)
  if (!isTRUE(run_ndlm_main) && !identical(run_ndlm_main, FALSE)) {
    add_err("models.run_ndlm_main must be boolean (true/false)")
  }

  univar_mode <- unified_get(cfg, c("models", "exdqlm_univar", "implementation_mode"), default = "legacy_bridge")
  if (!(univar_mode %in% c("legacy_bridge", "theory_aligned"))) {
    add_err("models.exdqlm_univar.implementation_mode must be one of: legacy_bridge, theory_aligned")
  }

  ndlm_mode <- unified_get(cfg, c("models", "ndlm_main", "implementation_mode"), default = "legacy_bridge")
  if (!(ndlm_mode %in% c("legacy_bridge", "theory_aligned"))) {
    add_err("models.ndlm_main.implementation_mode must be one of: legacy_bridge, theory_aligned")
  }

  check_required_file <- function(path, key) {
    if (is.null(path) || !nzchar(path)) {
      add_err(sprintf("%s is required and must not be null", key))
    } else if (!file.exists(path)) {
      add_err(sprintf("%s does not exist: %s", key, path))
    }
  }

  fit_or_shared <- isTRUE(unified_get(cfg, c("stages", "fit"), FALSE)) ||
    isTRUE(unified_get(cfg, c("stages", "data_prep_shared"), FALSE))
  if (fit_or_shared) {
    check_required_file(unified_get(cfg, c("inputs", "fit", "parameters_path")), "inputs.fit.parameters_path")
    check_required_file(unified_get(cfg, c("inputs", "fit", "retros_path")), "inputs.fit.retros_path")
    check_required_file(unified_get(cfg, c("inputs", "fit", "nws_forecast_path")), "inputs.fit.nws_forecast_path")
    check_required_file(unified_get(cfg, c("inputs", "fit", "glofas_forecast_path")), "inputs.fit.glofas_forecast_path")
  }

  shared_covariates <- unified_get(cfg, c("inputs", "shared_covariates"), default = list())
  if (is.null(shared_covariates)) {
    shared_covariates <- list()
  }
  shared_covariates <- unlist(shared_covariates, use.names = FALSE)
  if (length(shared_covariates) > 0L) {
    for (i in seq_along(shared_covariates)) {
      cov_path <- as.character(shared_covariates[[i]])
      if (!nzchar(cov_path)) next
      check_required_file(cov_path, sprintf("inputs.shared_covariates[%d]", i))
    }
  }

  fit_covariates <- unified_get(cfg, c("inputs", "fit", "covariates"), default = list())
  if (is.null(fit_covariates)) fit_covariates <- list()
  for (i in seq_along(fit_covariates)) {
    entry <- fit_covariates[[i]]
    if (!is.list(entry)) {
      add_err(sprintf("inputs.fit.covariates[%d] must be a map with name/path", i))
      next
    }
    cov_name <- entry$name
    cov_path <- entry$path
    cov_name <- if (is.null(cov_name)) "" else as.character(cov_name)
    cov_path <- if (is.null(cov_path)) "" else as.character(cov_path)
    if (!nzchar(cov_name)) {
      add_err(sprintf("inputs.fit.covariates[%d].name is required", i))
    }
    check_required_file(cov_path, sprintf("inputs.fit.covariates[%d].path", i))
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

    snapshot_enabled <- unified_get(cfg, c("inputs", "forecats", "snapshot", "enabled"), NULL)
    if (!is.null(snapshot_enabled) && !isTRUE(snapshot_enabled) && !identical(snapshot_enabled, FALSE)) {
      add_err("inputs.forecats.snapshot.enabled must be boolean or null")
    }
    snapshot_dest <- unified_get(cfg, c("inputs", "forecats", "snapshot", "dest_rel"), "inputs/shared/forecats_bundle")
    if (is.null(snapshot_dest) || !is.character(snapshot_dest) || !nzchar(snapshot_dest)) {
      add_err("inputs.forecats.snapshot.dest_rel must be a non-empty string")
    }
    snapshot_copy_list <- unified_get(cfg, c("inputs", "forecats", "snapshot", "copy_list"), list())
    if (!is.null(snapshot_copy_list)) {
      snapshot_copy_list <- unlist(snapshot_copy_list, use.names = FALSE)
      if (length(snapshot_copy_list) > 0L && !all(nzchar(as.character(snapshot_copy_list)))) {
        add_err("inputs.forecats.snapshot.copy_list entries must be non-empty strings")
      }
    }
  }

  prefer_snapshot <- unified_get(cfg, c("inputs", "shared", "prefer_forecats_snapshot"), TRUE)
  if (!isTRUE(prefer_snapshot) && !identical(prefer_snapshot, FALSE)) {
    add_err("inputs.shared.prefer_forecats_snapshot must be boolean (true/false)")
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

  contract_checks_enabled <- unified_get(cfg, c("fit", "contract_checks", "enabled"), FALSE)
  if (!isTRUE(contract_checks_enabled) && !identical(contract_checks_enabled, FALSE)) {
    add_err("fit.contract_checks.enabled must be boolean (true/false)")
  }
  contract_checks_fail_fast <- unified_get(cfg, c("fit", "contract_checks", "fail_fast"), TRUE)
  if (!isTRUE(contract_checks_fail_fast) && !identical(contract_checks_fail_fast, FALSE)) {
    add_err("fit.contract_checks.fail_fast must be boolean (true/false)")
  }
  contract_checks_write_reports <- unified_get(cfg, c("fit", "contract_checks", "write_reports"), TRUE)
  if (!isTRUE(contract_checks_write_reports) && !identical(contract_checks_write_reports, FALSE)) {
    add_err("fit.contract_checks.write_reports must be boolean (true/false)")
  }

  diagnostics_enabled <- unified_get(cfg, c("fit", "diagnostics", "enabled"), FALSE)
  if (!isTRUE(diagnostics_enabled) && !identical(diagnostics_enabled, FALSE)) {
    add_err("fit.diagnostics.enabled must be boolean (true/false)")
  }
  diagnostics_fail_fast <- unified_get(cfg, c("fit", "diagnostics", "fail_fast"), TRUE)
  if (!isTRUE(diagnostics_fail_fast) && !identical(diagnostics_fail_fast, FALSE)) {
    add_err("fit.diagnostics.fail_fast must be boolean (true/false)")
  }
  diagnostics_write_reports <- unified_get(cfg, c("fit", "diagnostics", "write_reports"), TRUE)
  if (!isTRUE(diagnostics_write_reports) && !identical(diagnostics_write_reports, FALSE)) {
    add_err("fit.diagnostics.write_reports must be boolean (true/false)")
  }
  diagnostics_max_time_checks <- suppressWarnings(as.integer(unified_get(cfg, c("fit", "diagnostics", "max_time_checks"), 25L)))
  if (!is.finite(diagnostics_max_time_checks) || diagnostics_max_time_checks < 1L) {
    add_err("fit.diagnostics.max_time_checks must be an integer >= 1")
  }
  diagnostics_seed <- suppressWarnings(as.integer(unified_get(cfg, c("fit", "diagnostics", "seed"), 777L)))
  if (!is.finite(diagnostics_seed)) {
    add_err("fit.diagnostics.seed must be an integer")
  }
  diagnostics_psd_tol <- suppressWarnings(as.numeric(unified_get(cfg, c("fit", "diagnostics", "psd_tol"), -1e-10)))
  if (!is.finite(diagnostics_psd_tol)) {
    add_err("fit.diagnostics.psd_tol must be numeric and finite")
  }

  validation_profile <- unified_get(cfg, c("validation", "profile"), "production")
  if (!(validation_profile %in% c("production", "production_proof", "smoke"))) {
    add_err("validation.profile must be one of: production, production_proof, smoke")
  }

  data_start <- unified_get(cfg, c("dates", "data_start"), default = NULL)
  if (!is.null(data_start) && nzchar(as.character(data_start))) {
    parsed_data_start <- suppressWarnings(as.Date(as.character(data_start)))
    if (is.na(parsed_data_start)) {
      add_err("dates.data_start must be null or a valid date string (YYYY-MM-DD)")
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
