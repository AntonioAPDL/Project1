# unified/config.R

unified_scale_enum <- c("raw_cms", "log_cms", "log1p_cms", "log_log_cms", "log_log1p_cms")

unified_resolve_source_run_dir <- function(source_run_root, source_run_id, fallback_run_root = NULL) {
  source_run_id <- if (is.null(source_run_id)) "" else as.character(source_run_id[[1L]])
  if (!nzchar(source_run_id)) {
    return(NULL)
  }

  root <- source_run_root
  if (is.null(root) || !nzchar(as.character(root))) {
    root <- fallback_run_root
  }
  if (is.null(root) || !nzchar(as.character(root))) {
    return(NULL)
  }

  root <- normalizePath(path.expand(as.character(root[[1L]])), mustWork = FALSE)
  if (identical(basename(root), source_run_id)) {
    return(root)
  }
  normalizePath(file.path(root, source_run_id), mustWork = FALSE)
}

unified_config_defaults <- function() {
  list(
    config_version = 1L,
    run = list(
      run_id = NULL,
      run_root = "repro/runs",
      repro_mode = "strict",
      seed = 777L,
      overwrite = FALSE,
      auto_suffix_on_collision = FALSE,
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
      run_ndlm_univar = FALSE,
      exdqlm_multivar = list(
        implementation_mode = "legacy_bridge",
        likelihood_mode = "exal",
        forecast_transfer_mode = "drop",
        forecast_transfer_modes = NULL,
        state_evolution = list(
          df_t = 0.99999999,
          df_s1 = 0.9999,
          df_s2 = 0.9999,
          df_s67 = 0.9999,
          df_discrep = 0.999,
          lambda = 0.97,
          df_trans = 0.9999999,
          df_covs = 0.99999
        )
      ),
      exdqlm_univar = list(
        implementation_mode = "legacy_bridge",
        likelihood_mode = "exal",
        state_evolution = list(
          df_t = 0.99999999,
          df_s1 = 0.9999,
          df_s2 = 0.9999,
          df_s67 = 0.9999,
          lambda = 0.97,
          df_trans = 0.9999999,
          df_covs = 0.99999
        )
      ),
      ndlm_main = list(
        implementation_mode = "theory_aligned",
        kalman_backend = "cpp",
        forecast_transfer_mode = "keep",
        state_evolution = list(
          df_t = 0.99999999,
          df_s1 = 0.9999,
          df_s2 = 0.9999,
          df_s67 = 0.9999,
          df_discrep = 0.999,
          lambda = 0.97,
          df_trans = 0.9999999,
          df_covs = 0.9999
        ),
        stabilization = list(
          cov_eig_floor = 1e-8,
          cov_eig_cap = 1e8,
          cov_diag_jitter = 1e-10,
          sigma_upper_cap = 1e12,
          sigma_update_damping = 1.0,
          latent_var_cap_mult = 1e4,
          latent_var_cap_abs = 1e8
        )
      ),
      ndlm_univar = list(
        implementation_mode = "theory_aligned_closed_form",
        kalman_backend = "cpp",
        forecast_transfer_mode = "keep",
        horizon_cap = 1080L,
        posterior_draws = 64L,
        prior = list(
          n0 = 20,
          S0 = 1
        ),
        state_evolution = list(
          df_t = 0.99999999,
          df_s1 = 0.9999,
          df_s2 = 0.9999,
          df_s67 = 0.9999,
          lambda = 0.97,
          df_trans = 0.9999999,
          df_covs = 0.99999
        ),
        stabilization = list(
          cov_eig_floor = 1e-8,
          cov_eig_cap = 1e8,
          cov_diag_jitter = 1e-10
        )
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
        nws_storage_scale = "raw_cms",
        glofas_forecast_path = NULL,
        glofas_storage_scale = "raw_cms",
        usgs_mode = "live",
        usgs_cache_path = NULL,
        covariates = list()
      ),
      post = list(
        use_fit_outputs_from_run = TRUE,
        source_run_id = NULL,
        source_run_root = NULL
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
        prefer_forecats_snapshot = TRUE,
        exact_source_snapshot_root = NULL
      ),
      deterministic_climate = list(
        enabled = FALSE,
        handoff_root = NULL,
        horizon_days = NULL,
        require_full_horizon = TRUE,
        precip = list(
          enabled = TRUE,
          source = "gefs_apcp",
          reduction = "mean",
          dry_day_threshold_mm = 0,
          noisy_blend = list(
            enabled = FALSE,
            noise_sd = 15,
            noise_seed = 20260415L,
            noise_distribution = "normal",
            floor_at_zero = TRUE
          ),
          observed_blend = list(
            enabled = FALSE,
            observed_weight = 0.9,
            observed_zero_stay_prob = NULL,
            observed_zero_stay_seed = 20260415L
          )
        ),
        soil = list(
          enabled = TRUE,
          source = "nwm_soilsat_top",
          reduction = "mean",
          noisy_blend = list(
            enabled = FALSE,
            noise_sd = 0.01,
            noise_seed = 20260415L,
            noise_distribution = "normal",
            floor_at_zero = FALSE
          ),
          observed_blend = list(
            enabled = FALSE,
            observed_weight = 0.9,
            observed_zero_stay_prob = NULL,
            observed_zero_stay_seed = 20260415L
          )
        )
      ),
      covariate_features = list(
        enabled = FALSE,
        output_filename = "covariate_features.csv",
        lag_orders = c(1L, 2L, 3L),
        include_squares = TRUE,
        include_interaction = TRUE
      ),
      shared_covariates = list() # legacy compatibility
    ),
    fit = list(
      quantiles = c(0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95),
      parallel = list(
        mode = "one_core_per_model",
        workers = NULL
      ),
      warm_start = list(
        enabled = FALSE,
        source_run_id = NULL,
        mode = "resume"
      ),
      exdqlm_multivar = list(
        gamma_sigma = list(
          warmup_freeze_iters = 5L,
          min_update_iters = 50L,
          min_total_iters = 50L,
          max_iter = 100L,
          convergence_tol = 1e-6,
          convergence = list(
            elbo_tol = 1e-6,
            state_norm_sq_tol = 1e-6,
            sigma_exp_tol = 1e-6,
            gamma_exp_tol = 1e-6
          ),
          freeze_target = "gamma_sigma",
          guard_refreeze_iters = 10L,
          init = list(
            mode = "robust",
            gamma = 0.0,
            sigma_floor = 1e-3,
            sigma_scale = 1.0
          ),
          objective_guard = list(
            enabled = TRUE,
            fail_fast = FALSE,
            log_failures = TRUE,
            mode = "adaptive_freeze",
            penalty = 1e12
          ),
          transfer_compare_fast = list(
            enabled = FALSE,
            warmup_freeze_iters = 5L,
            min_update_iters = 15L,
            min_total_iters = 20L,
            max_iter = 20L
          )
        ),
        forecast_health = list(
          enabled = TRUE,
          fail_fast = TRUE,
          write_reports = TRUE,
          latent_limit = 650,
          sigma_limit = 100,
          state_limit = 1000
        ),
        legacy = list(
          lam1 = 1 - 1e-6,
          lam2 = 1 - 1e-6,
          n_samp = 2000L,
          sims_enabled = TRUE,
          use_covariates = TRUE
        )
      ),
      exdqlm_univar = list(
        gamma_sigma = list(
          warmup_freeze_iters = 5L,
          min_update_iters = 50L,
          min_total_iters = 50L,
          max_iter = 100L,
          convergence_tol = 1e-6,
          convergence = list(
            elbo_tol = 1e-6,
            state_norm_sq_tol = 1e-6,
            sigma_exp_tol = 1e-6,
            gamma_exp_tol = 1e-6
          ),
          freeze_target = "gamma_sigma",
          guard_refreeze_iters = 10L,
          init = list(
            mode = "robust",
            gamma = 0.0,
            sigma_floor = 1e-3,
            sigma_scale = 1.0
          ),
          objective_guard = list(
            enabled = TRUE,
            fail_fast = FALSE,
            log_failures = TRUE,
            mode = "adaptive_freeze",
            penalty = 1e12
          )
        ),
        legacy = list(
          lam1 = 1 - 1e-16,
          lam2 = 1 - 1e-16,
          n_samp = 2000L,
          sims_enabled = TRUE,
          use_covariates = TRUE
        )
      ),
      ndlm_main = list(
        gamma_sigma = list(
          min_total_iters = 50L,
          max_iter = 100L,
          convergence_tol = 1e-6,
          convergence = list(
            elbo_tol = 1e-6,
            elbo_rel_tol = 2.5e-4
          )
        ),
        legacy = list(
          lam1 = 1 - 1e-6,
          lam2 = 0.9,
          n_samp = 2000L,
          sims_enabled = TRUE,
          use_covariates = TRUE
        )
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
        psd_tol = -1e-10,
        full_slice_psd = FALSE,
        psd_warn_tol = -1e-10,
        psd_fail_tol = -1e-10
      )
    ),
    post = list(
      figures = TRUE,
      profile = FALSE,
      profile_detail = FALSE,
      sort_keep_na = TRUE,
      export_tables = TRUE,
      allow_legacy_root_fallback = FALSE,
      crps_input_health = list(
        enabled = TRUE,
        fail_fast = FALSE,
        min_finite_share = 1,
        max_abs = NA_real_
      )
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

unified_normalize_likelihood_mode <- function(mode, default = "exal") {
  raw <- as.character(mode)
  if (!length(raw) || is.na(raw[[1L]]) || !nzchar(raw[[1L]])) {
    raw <- default
  } else {
    raw <- raw[[1L]]
  }
  raw <- tolower(trimws(raw))
  if (!(raw %in% c("exal", "al"))) {
    raw <- tolower(trimws(as.character(default)[[1L]]))
    if (!(raw %in% c("exal", "al"))) {
      raw <- "exal"
    }
  }
  raw
}

unified_resolve_univar_likelihood_mode <- function(cfg, default = "exal") {
  unified_normalize_likelihood_mode(
    unified_get(cfg, c("models", "exdqlm_univar", "likelihood_mode"), default = default),
    default = default
  )
}

unified_resolve_multivar_likelihood_mode <- function(cfg, default = "exal") {
  unified_normalize_likelihood_mode(
    unified_get(cfg, c("models", "exdqlm_multivar", "likelihood_mode"), default = default),
    default = default
  )
}

unified_resolve_ndlm_forecast_transfer_mode <- function(cfg, default = "keep") {
  mode <- as.character(unified_get(
    cfg,
    c("models", "ndlm_main", "forecast_transfer_mode"),
    default = default
  ))
  if (!length(mode) || is.na(mode[[1L]]) || !nzchar(mode[[1L]])) {
    mode <- default
  } else {
    mode <- mode[[1L]]
  }
  mode <- tolower(trimws(mode))
  if (!(mode %in% c("drop", "keep"))) {
    mode <- default
  }
  mode
}

unified_resolve_ndlm_univar_forecast_transfer_mode <- function(cfg, default = "keep") {
  mode <- as.character(unified_get(
    cfg,
    c("models", "ndlm_univar", "forecast_transfer_mode"),
    default = default
  ))
  if (!length(mode) || is.na(mode[[1L]]) || !nzchar(mode[[1L]])) {
    mode <- default
  } else {
    mode <- mode[[1L]]
  }
  mode <- tolower(trimws(mode))
  if (!(mode %in% c("drop", "keep"))) {
    mode <- default
  }
  mode
}

unified_resolve_multivar_transfer_modes <- function(cfg, default_mode = "drop") {
  single_mode <- as.character(unified_get(
    cfg,
    c("models", "exdqlm_multivar", "forecast_transfer_mode"),
    default = default_mode
  ))
  if (!length(single_mode) || is.na(single_mode[[1]]) || !nzchar(single_mode[[1]])) {
    single_mode <- default_mode
  } else {
    single_mode <- single_mode[[1]]
  }
  single_mode <- tolower(trimws(single_mode))
  if (!(single_mode %in% c("drop", "keep"))) {
    single_mode <- default_mode
  }

  raw_modes <- unified_get(
    cfg,
    c("models", "exdqlm_multivar", "forecast_transfer_modes"),
    default = NULL
  )
  if (is.null(raw_modes)) {
    return(single_mode)
  }

  mode_vec <- unlist(raw_modes, use.names = FALSE)
  mode_vec <- tolower(trimws(as.character(mode_vec)))
  mode_vec <- mode_vec[nzchar(mode_vec) & !is.na(mode_vec)]
  mode_vec <- unique(mode_vec)
  mode_vec <- mode_vec[mode_vec %in% c("drop", "keep")]

  if (length(mode_vec) == 0L) {
    return(single_mode)
  }
  mode_vec
}

unified_resolve_multivar_primary_transfer_mode <- function(cfg, modes = NULL, default_mode = "drop") {
  if (is.null(modes) || length(modes) == 0L) {
    modes <- unified_resolve_multivar_transfer_modes(cfg, default_mode = default_mode)
  }
  modes <- tolower(trimws(as.character(modes)))
  modes <- modes[nzchar(modes) & !is.na(modes)]
  if (length(modes) == 0L) {
    return(default_mode)
  }
  modes <- unique(modes)

  preferred <- as.character(unified_get(
    cfg,
    c("models", "exdqlm_multivar", "forecast_transfer_mode"),
    default = default_mode
  ))
  if (!length(preferred) || is.na(preferred[[1]]) || !nzchar(preferred[[1]])) {
    preferred <- default_mode
  } else {
    preferred <- preferred[[1]]
  }
  preferred <- tolower(trimws(preferred))
  if (preferred %in% modes) {
    return(preferred)
  }
  modes[[1]]
}

unified_resolve_exdqlm_multivar_legacy_output_suffix <- function(cfg, default = "DISC") {
  use_covariates <- isTRUE(unified_get(
    cfg,
    c("fit", "exdqlm_multivar", "legacy", "use_covariates"),
    default = identical(toupper(default), "DISC")
  ))
  if (isTRUE(use_covariates)) {
    "DISC"
  } else {
    "simp"
  }
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
    c("inputs", "post", "source_run_root"),
    c("inputs", "forecats", "pipeline_config_path"),
    c("inputs", "forecats", "existing_bundle_path"),
    c("inputs", "deterministic_climate", "handoff_root")
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
  run_threads_mc_cores <- suppressWarnings(as.integer(unified_get(cfg, c("run", "threads", "mc_cores"), default = 1L)))
  if (!is.finite(run_threads_mc_cores) || run_threads_mc_cores < 1L) {
    add_err("run.threads.mc_cores must be an integer >= 1")
  }
  fit_parallel_mode <- as.character(unified_get(cfg, c("fit", "parallel", "mode"), default = "one_core_per_model"))
  fit_parallel_mode <- if (length(fit_parallel_mode) > 0L) fit_parallel_mode[[1]] else "one_core_per_model"
  fit_parallel_mode <- gsub("[^A-Za-z0-9]+", "_", tolower(fit_parallel_mode))
  if (!(fit_parallel_mode %in% c("by_family", "global_models", "one_core_per_model"))) {
    add_err("fit.parallel.mode must be one of: one_core_per_model, global_models, by_family")
  }
  fit_parallel_workers_raw <- unified_get(cfg, c("fit", "parallel", "workers"), default = NULL)
  if (!is.null(fit_parallel_workers_raw)) {
    fit_parallel_workers_chr <- as.character(fit_parallel_workers_raw)[[1]]
    if (!is.na(fit_parallel_workers_chr) && nzchar(fit_parallel_workers_chr)) {
      fit_parallel_workers <- suppressWarnings(as.integer(fit_parallel_workers_chr))
      if (!is.finite(fit_parallel_workers) || fit_parallel_workers < 1L) {
        add_err("fit.parallel.workers must be null or an integer >= 1")
      }
    }
  }

  post_export_tables <- unified_get(cfg, c("post", "export_tables"), default = TRUE)
  if (!isTRUE(post_export_tables) && !identical(post_export_tables, FALSE)) {
    add_err("post.export_tables must be boolean (true/false)")
  }
  post_use_fit_outputs_from_run <- unified_get(cfg, c("inputs", "post", "use_fit_outputs_from_run"), default = TRUE)
  if (!isTRUE(post_use_fit_outputs_from_run) && !identical(post_use_fit_outputs_from_run, FALSE)) {
    add_err("inputs.post.use_fit_outputs_from_run must be boolean (true/false)")
  }
  post_source_run_id <- unified_get(cfg, c("inputs", "post", "source_run_id"), default = NULL)
  if (!is.null(post_source_run_id) && !is.character(post_source_run_id)) {
    post_source_run_id <- as.character(post_source_run_id)
  }
  post_source_run_root <- unified_get(cfg, c("inputs", "post", "source_run_root"), default = NULL)
  if (!is.null(post_source_run_root) && !nzchar(post_source_run_root)) {
    post_source_run_root <- NULL
  }
  if (isTRUE(unified_get(cfg, c("stages", "post"), FALSE)) &&
      isTRUE(post_use_fit_outputs_from_run) &&
      !is.null(post_source_run_id) &&
      nzchar(post_source_run_id)) {
    source_run_dir <- unified_resolve_source_run_dir(
      source_run_root = post_source_run_root,
      source_run_id = post_source_run_id,
      fallback_run_root = unified_get(cfg, c("run", "run_root"), default = NULL)
    )
    if (is.null(source_run_dir) || !dir.exists(source_run_dir)) {
      add_err(sprintf(
        "inputs.post.source_run_id is set but source run directory does not exist: %s",
        if (is.null(source_run_dir)) "<null>" else source_run_dir
      ))
    }
  }
  post_allow_legacy_root_fallback <- unified_get(cfg, c("post", "allow_legacy_root_fallback"), default = FALSE)
  if (!isTRUE(post_allow_legacy_root_fallback) && !identical(post_allow_legacy_root_fallback, FALSE)) {
    add_err("post.allow_legacy_root_fallback must be boolean (true/false)")
  }
  post_crps_health_enabled <- unified_get(cfg, c("post", "crps_input_health", "enabled"), default = TRUE)
  if (!isTRUE(post_crps_health_enabled) && !identical(post_crps_health_enabled, FALSE)) {
    add_err("post.crps_input_health.enabled must be boolean (true/false)")
  }
  post_crps_health_fail_fast <- unified_get(cfg, c("post", "crps_input_health", "fail_fast"), default = FALSE)
  if (!isTRUE(post_crps_health_fail_fast) && !identical(post_crps_health_fail_fast, FALSE)) {
    add_err("post.crps_input_health.fail_fast must be boolean (true/false)")
  }
  post_crps_health_min_finite_share <- suppressWarnings(as.numeric(unified_get(
    cfg, c("post", "crps_input_health", "min_finite_share"), default = 1
  )))
  if (!is.finite(post_crps_health_min_finite_share) ||
      post_crps_health_min_finite_share < 0 || post_crps_health_min_finite_share > 1) {
    add_err("post.crps_input_health.min_finite_share must be numeric in [0, 1]")
  }
  post_crps_health_max_abs <- suppressWarnings(as.numeric(unified_get(
    cfg, c("post", "crps_input_health", "max_abs"), default = NA_real_
  )))
  if (!is.na(post_crps_health_max_abs) && (!is.finite(post_crps_health_max_abs) || post_crps_health_max_abs <= 0)) {
    add_err("post.crps_input_health.max_abs must be null/NA or numeric > 0")
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
  run_ndlm_univar <- unified_get(cfg, c("models", "run_ndlm_univar"), default = FALSE)
  if (!isTRUE(run_ndlm_univar) && !identical(run_ndlm_univar, FALSE)) {
    add_err("models.run_ndlm_univar must be boolean (true/false)")
  }
  read_mode_scalar <- function(path, default) {
    raw <- as.character(unified_get(cfg, path, default = default))
    if (!length(raw) || is.na(raw[[1L]]) || !nzchar(raw[[1L]])) {
      return(tolower(trimws(as.character(default)[[1L]])))
    }
    tolower(trimws(raw[[1L]]))
  }

  univar_mode <- unified_get(cfg, c("models", "exdqlm_univar", "implementation_mode"), default = "legacy_bridge")
  if (!(univar_mode %in% c("legacy_bridge", "theory_aligned"))) {
    add_err("models.exdqlm_univar.implementation_mode must be one of: legacy_bridge, theory_aligned")
  }
  univar_likelihood_mode <- read_mode_scalar(c("models", "exdqlm_univar", "likelihood_mode"), "exal")
  if (!(univar_likelihood_mode %in% c("exal", "al"))) {
    add_err("models.exdqlm_univar.likelihood_mode must be one of: exal, al")
  }

  ndlm_mode <- unified_get(cfg, c("models", "ndlm_main", "implementation_mode"), default = "theory_aligned")
  if (!(ndlm_mode %in% c("legacy_bridge", "theory_aligned"))) {
    add_err("models.ndlm_main.implementation_mode must be one of: legacy_bridge, theory_aligned")
  }
  ndlm_univar_mode <- unified_get(
    cfg,
    c("models", "ndlm_univar", "implementation_mode"),
    default = "theory_aligned_closed_form"
  )
  if (!(ndlm_univar_mode %in% c("theory_aligned_closed_form", "theory_aligned"))) {
    add_err("models.ndlm_univar.implementation_mode must be one of: theory_aligned_closed_form, theory_aligned")
  }
  multivar_likelihood_mode <- read_mode_scalar(c("models", "exdqlm_multivar", "likelihood_mode"), "exal")
  if (!(multivar_likelihood_mode %in% c("exal", "al"))) {
    add_err("models.exdqlm_multivar.likelihood_mode must be one of: exal, al")
  }
  multivar_forecast_transfer_mode <- unified_get(
    cfg,
    c("models", "exdqlm_multivar", "forecast_transfer_mode"),
    default = "drop"
  )
  if (!(multivar_forecast_transfer_mode %in% c("drop", "keep"))) {
    add_err("models.exdqlm_multivar.forecast_transfer_mode must be one of: drop, keep")
  }
  multivar_forecast_transfer_modes <- unified_get(
    cfg,
    c("models", "exdqlm_multivar", "forecast_transfer_modes"),
    default = NULL
  )
  if (!is.null(multivar_forecast_transfer_modes)) {
    mode_vec <- unlist(multivar_forecast_transfer_modes, use.names = FALSE)
    mode_vec <- tolower(trimws(as.character(mode_vec)))
    mode_vec <- mode_vec[nzchar(mode_vec) & !is.na(mode_vec)]
    if (length(mode_vec) == 0L) {
      add_err("models.exdqlm_multivar.forecast_transfer_modes must be null or a non-empty list of modes")
    } else {
      invalid_modes <- unique(mode_vec[!(mode_vec %in% c("drop", "keep"))])
      if (length(invalid_modes) > 0L) {
        add_err(sprintf(
          "models.exdqlm_multivar.forecast_transfer_modes has invalid values: %s (allowed: drop, keep)",
          paste(invalid_modes, collapse = ", ")
        ))
      }
    }
  }
  ndlm_kalman_backend <- unified_get(cfg, c("models", "ndlm_main", "kalman_backend"), default = "cpp")
  if (!(ndlm_kalman_backend %in% c("r", "cpp"))) {
    add_err("models.ndlm_main.kalman_backend must be one of: r, cpp")
  }
  ndlm_univar_kalman_backend <- unified_get(cfg, c("models", "ndlm_univar", "kalman_backend"), default = "cpp")
  if (!(ndlm_univar_kalman_backend %in% c("r", "cpp"))) {
    add_err("models.ndlm_univar.kalman_backend must be one of: r, cpp")
  }
  ndlm_forecast_transfer_mode <- read_mode_scalar(c("models", "ndlm_main", "forecast_transfer_mode"), "keep")
  if (!(ndlm_forecast_transfer_mode %in% c("drop", "keep"))) {
    add_err("models.ndlm_main.forecast_transfer_mode must be one of: drop, keep")
  }
  ndlm_univar_forecast_transfer_mode <- read_mode_scalar(c("models", "ndlm_univar", "forecast_transfer_mode"), "keep")
  if (!(ndlm_univar_forecast_transfer_mode %in% c("drop", "keep"))) {
    add_err("models.ndlm_univar.forecast_transfer_mode must be one of: drop, keep")
  }
  multivar_prob_keys <- c("df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs")
  for (nm in multivar_prob_keys) {
    val <- suppressWarnings(as.numeric(unified_get(cfg, c("models", "exdqlm_multivar", "state_evolution", nm), default = NA_real_)))
    if (!is.finite(val) || val <= 0 || val >= 1) {
      add_err(sprintf("models.exdqlm_multivar.state_evolution.%s must be numeric in (0,1)", nm))
    }
  }
  ndlm_prob_keys <- c("df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs")
  for (nm in ndlm_prob_keys) {
    val <- suppressWarnings(as.numeric(unified_get(cfg, c("models", "ndlm_main", "state_evolution", nm), default = NA_real_)))
    if (!is.finite(val) || val <= 0 || val >= 1) {
      add_err(sprintf("models.ndlm_main.state_evolution.%s must be numeric in (0,1)", nm))
    }
  }
  ndlm_forecast_cov_c_factor <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_main", "prior", "forecast_cov", "c_factor"),
    default = 1.0
  )))
  if (!is.finite(ndlm_forecast_cov_c_factor) || ndlm_forecast_cov_c_factor <= 0) {
    add_err("models.ndlm_main.prior.forecast_cov.c_factor must be numeric > 0")
  }
  ndlm_forecast_cov_epsilon <- unified_get(
    cfg,
    c("models", "ndlm_main", "prior", "forecast_cov", "epsilon"),
    default = NULL
  )
  if (!is.null(ndlm_forecast_cov_epsilon)) {
    ndlm_forecast_cov_epsilon <- suppressWarnings(as.numeric(ndlm_forecast_cov_epsilon))
    if (!is.finite(ndlm_forecast_cov_epsilon) || ndlm_forecast_cov_epsilon <= 0) {
      add_err("models.ndlm_main.prior.forecast_cov.epsilon must be null or numeric > 0")
    }
  }
  ndlm_univar_prob_keys <- c("df_t", "df_s1", "df_s2", "df_s67", "lambda", "df_trans", "df_covs")
  for (nm in ndlm_univar_prob_keys) {
    val <- suppressWarnings(as.numeric(unified_get(cfg, c("models", "ndlm_univar", "state_evolution", nm), default = NA_real_)))
    if (!is.finite(val) || val <= 0 || val >= 1) {
      add_err(sprintf("models.ndlm_univar.state_evolution.%s must be numeric in (0,1)", nm))
    }
  }
  ndlm_cov_floor <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_main", "stabilization", "cov_eig_floor"),
    default = 1e-8
  )))
  if (!is.finite(ndlm_cov_floor) || ndlm_cov_floor <= 0) {
    add_err("models.ndlm_main.stabilization.cov_eig_floor must be numeric > 0")
  }
  ndlm_cov_cap <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_main", "stabilization", "cov_eig_cap"),
    default = 1e8
  )))
  if (!is.finite(ndlm_cov_cap) || ndlm_cov_cap <= 0) {
    add_err("models.ndlm_main.stabilization.cov_eig_cap must be numeric > 0")
  } else if (is.finite(ndlm_cov_floor) && ndlm_cov_cap <= ndlm_cov_floor) {
    add_err("models.ndlm_main.stabilization.cov_eig_cap must be greater than cov_eig_floor")
  }
  ndlm_cov_jitter <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_main", "stabilization", "cov_diag_jitter"),
    default = 1e-10
  )))
  if (!is.finite(ndlm_cov_jitter) || ndlm_cov_jitter < 0) {
    add_err("models.ndlm_main.stabilization.cov_diag_jitter must be numeric >= 0")
  }
  ndlm_sigma_cap <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_main", "stabilization", "sigma_upper_cap"),
    default = 1e12
  )))
  if (!is.finite(ndlm_sigma_cap) || ndlm_sigma_cap <= 0) {
    add_err("models.ndlm_main.stabilization.sigma_upper_cap must be numeric > 0")
  }
  ndlm_sigma_damping <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_main", "stabilization", "sigma_update_damping"),
    default = 1.0
  )))
  if (!is.finite(ndlm_sigma_damping) || ndlm_sigma_damping < 0 || ndlm_sigma_damping > 1) {
    add_err("models.ndlm_main.stabilization.sigma_update_damping must be numeric in [0,1]")
  }
  ndlm_latent_mult <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_main", "stabilization", "latent_var_cap_mult"),
    default = 1e4
  )))
  if (!is.finite(ndlm_latent_mult) || ndlm_latent_mult <= 0) {
    add_err("models.ndlm_main.stabilization.latent_var_cap_mult must be numeric > 0")
  }
  ndlm_latent_abs <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_main", "stabilization", "latent_var_cap_abs"),
    default = 1e8
  )))
  if (!is.finite(ndlm_latent_abs) || ndlm_latent_abs <= 0) {
    add_err("models.ndlm_main.stabilization.latent_var_cap_abs must be numeric > 0")
  }

  ndlm_univar_horizon_cap <- suppressWarnings(as.integer(unified_get(
    cfg,
    c("models", "ndlm_univar", "horizon_cap"),
    default = 1080L
  )))
  if (!is.finite(ndlm_univar_horizon_cap) || ndlm_univar_horizon_cap < 1L) {
    add_err("models.ndlm_univar.horizon_cap must be an integer >= 1")
  }
  ndlm_univar_draws <- suppressWarnings(as.integer(unified_get(
    cfg,
    c("models", "ndlm_univar", "posterior_draws"),
    default = 64L
  )))
  if (!is.finite(ndlm_univar_draws) || ndlm_univar_draws < 1L) {
    add_err("models.ndlm_univar.posterior_draws must be an integer >= 1")
  }
  ndlm_univar_n0 <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_univar", "prior", "n0"),
    default = 20
  )))
  if (!is.finite(ndlm_univar_n0) || ndlm_univar_n0 <= 0) {
    add_err("models.ndlm_univar.prior.n0 must be numeric > 0")
  }
  ndlm_univar_S0 <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_univar", "prior", "S0"),
    default = 1
  )))
  if (!is.finite(ndlm_univar_S0) || ndlm_univar_S0 <= 0) {
    add_err("models.ndlm_univar.prior.S0 must be numeric > 0")
  }
  ndlm_univar_cov_floor <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_univar", "stabilization", "cov_eig_floor"),
    default = 1e-8
  )))
  if (!is.finite(ndlm_univar_cov_floor) || ndlm_univar_cov_floor <= 0) {
    add_err("models.ndlm_univar.stabilization.cov_eig_floor must be numeric > 0")
  }
  ndlm_univar_cov_cap <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_univar", "stabilization", "cov_eig_cap"),
    default = 1e8
  )))
  if (!is.finite(ndlm_univar_cov_cap) || ndlm_univar_cov_cap <= 0) {
    add_err("models.ndlm_univar.stabilization.cov_eig_cap must be numeric > 0")
  } else if (is.finite(ndlm_univar_cov_floor) && ndlm_univar_cov_cap <= ndlm_univar_cov_floor) {
    add_err("models.ndlm_univar.stabilization.cov_eig_cap must be greater than cov_eig_floor")
  }
  ndlm_univar_cov_jitter <- suppressWarnings(as.numeric(unified_get(
    cfg,
    c("models", "ndlm_univar", "stabilization", "cov_diag_jitter"),
    default = 1e-10
  )))
  if (!is.finite(ndlm_univar_cov_jitter) || ndlm_univar_cov_jitter < 0) {
    add_err("models.ndlm_univar.stabilization.cov_diag_jitter must be numeric >= 0")
  }

  univar_prob_keys <- c("df_t", "df_s1", "df_s2", "df_s67", "lambda", "df_trans", "df_covs")
  for (nm in univar_prob_keys) {
    val <- suppressWarnings(as.numeric(unified_get(cfg, c("models", "exdqlm_univar", "state_evolution", nm), default = NA_real_)))
    if (!is.finite(val) || val <= 0 || val >= 1) {
      add_err(sprintf("models.exdqlm_univar.state_evolution.%s must be numeric in (0,1)", nm))
    }
  }

  validate_prob_01 <- function(path, label) {
    val <- suppressWarnings(as.numeric(unified_get(cfg, path, default = NA_real_)))
    if (!is.finite(val) || val <= 0 || val > 1) {
      add_err(sprintf("%s must be numeric in (0,1]", label))
    }
  }
  validate_int_min <- function(path, label, min_value = 1L) {
    val <- suppressWarnings(as.integer(unified_get(cfg, path, default = NA_integer_)))
    if (!is.finite(val) || val < as.integer(min_value)) {
      add_err(sprintf("%s must be an integer >= %d", label, as.integer(min_value)))
    }
  }
  validate_real_min <- function(path, label, min_value = 0) {
    val <- suppressWarnings(as.numeric(unified_get(cfg, path, default = NA_real_)))
    if (!is.finite(val) || val < as.numeric(min_value)) {
      add_err(sprintf("%s must be numeric >= %s", label, format(as.numeric(min_value), digits = 10)))
    }
  }
  validate_bool <- function(path, label) {
    val <- unified_get(cfg, path, default = NULL)
    if (!isTRUE(val) && !identical(val, FALSE)) {
      add_err(sprintf("%s must be boolean (true/false)", label))
    }
  }

  validate_prob_01(c("fit", "exdqlm_univar", "legacy", "lam1"), "fit.exdqlm_univar.legacy.lam1")
  validate_prob_01(c("fit", "exdqlm_univar", "legacy", "lam2"), "fit.exdqlm_univar.legacy.lam2")
  validate_int_min(c("fit", "exdqlm_univar", "legacy", "n_samp"), "fit.exdqlm_univar.legacy.n_samp", min_value = 1L)
  validate_bool(c("fit", "exdqlm_univar", "legacy", "sims_enabled"), "fit.exdqlm_univar.legacy.sims_enabled")
  validate_bool(c("fit", "exdqlm_univar", "legacy", "use_covariates"), "fit.exdqlm_univar.legacy.use_covariates")

  validate_prob_01(c("fit", "exdqlm_multivar", "legacy", "lam1"), "fit.exdqlm_multivar.legacy.lam1")
  validate_prob_01(c("fit", "exdqlm_multivar", "legacy", "lam2"), "fit.exdqlm_multivar.legacy.lam2")
  validate_int_min(c("fit", "exdqlm_multivar", "legacy", "n_samp"), "fit.exdqlm_multivar.legacy.n_samp", min_value = 1L)
  validate_bool(c("fit", "exdqlm_multivar", "legacy", "sims_enabled"), "fit.exdqlm_multivar.legacy.sims_enabled")
  validate_bool(c("fit", "exdqlm_multivar", "legacy", "use_covariates"), "fit.exdqlm_multivar.legacy.use_covariates")
  validate_bool(c("fit", "exdqlm_multivar", "forecast_health", "enabled"), "fit.exdqlm_multivar.forecast_health.enabled")
  validate_bool(c("fit", "exdqlm_multivar", "forecast_health", "fail_fast"), "fit.exdqlm_multivar.forecast_health.fail_fast")
  validate_bool(c("fit", "exdqlm_multivar", "forecast_health", "write_reports"), "fit.exdqlm_multivar.forecast_health.write_reports")
  validate_real_min(c("fit", "exdqlm_multivar", "forecast_health", "latent_limit"), "fit.exdqlm_multivar.forecast_health.latent_limit", min_value = 1e-6)
  validate_real_min(c("fit", "exdqlm_multivar", "forecast_health", "sigma_limit"), "fit.exdqlm_multivar.forecast_health.sigma_limit", min_value = 1e-6)
  validate_real_min(c("fit", "exdqlm_multivar", "forecast_health", "state_limit"), "fit.exdqlm_multivar.forecast_health.state_limit", min_value = 1e-6)

  validate_prob_01(c("fit", "ndlm_main", "legacy", "lam1"), "fit.ndlm_main.legacy.lam1")
  validate_prob_01(c("fit", "ndlm_main", "legacy", "lam2"), "fit.ndlm_main.legacy.lam2")
  validate_int_min(c("fit", "ndlm_main", "legacy", "n_samp"), "fit.ndlm_main.legacy.n_samp", min_value = 1L)
  validate_bool(c("fit", "ndlm_main", "legacy", "sims_enabled"), "fit.ndlm_main.legacy.sims_enabled")
  validate_bool(c("fit", "ndlm_main", "legacy", "use_covariates"), "fit.ndlm_main.legacy.use_covariates")

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

  detclim_enabled <- unified_get(cfg, c("inputs", "deterministic_climate", "enabled"), default = FALSE)
  if (!isTRUE(detclim_enabled) && !identical(detclim_enabled, FALSE)) {
    add_err("inputs.deterministic_climate.enabled must be boolean (true/false)")
  }
  if (isTRUE(detclim_enabled)) {
    handoff_root <- unified_get(cfg, c("inputs", "deterministic_climate", "handoff_root"), default = NULL)
    if (is.null(handoff_root) || !nzchar(as.character(handoff_root))) {
      add_err("inputs.deterministic_climate.handoff_root is required when deterministic_climate.enabled=true")
    } else if (!dir.exists(as.character(handoff_root))) {
      add_err(sprintf("inputs.deterministic_climate.handoff_root does not exist: %s", as.character(handoff_root)))
    }
    horizon_days <- unified_get(cfg, c("inputs", "deterministic_climate", "horizon_days"), default = NULL)
    if (!is.null(horizon_days)) {
      horizon_days_num <- suppressWarnings(as.integer(horizon_days))
      if (!is.finite(horizon_days_num) || horizon_days_num < 1L) {
        add_err("inputs.deterministic_climate.horizon_days must be null or an integer >= 1")
      }
    }
    require_full_horizon <- unified_get(cfg, c("inputs", "deterministic_climate", "require_full_horizon"), default = TRUE)
    if (!isTRUE(require_full_horizon) && !identical(require_full_horizon, FALSE)) {
      add_err("inputs.deterministic_climate.require_full_horizon must be boolean (true/false)")
    }
    for (series_name in c("precip", "soil")) {
      series_enabled <- unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "enabled"),
        default = TRUE
      )
      if (!isTRUE(series_enabled) && !identical(series_enabled, FALSE)) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.enabled must be boolean (true/false)",
          series_name
        ))
      }
      reduction <- tolower(as.character(unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "reduction"),
        default = "mean"
      ))[[1L]])
      reduction_ok <- tryCatch({
        detclim_parse_reduction_spec(reduction)
        TRUE
      }, error = function(e) FALSE)
      if (!isTRUE(reduction_ok)) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.reduction must be one of: mean, median, max, or a quantile like q85 / q0.85",
          series_name
        ))
      }
      source <- tolower(as.character(unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "source"),
        default = if (identical(series_name, "precip")) "gefs_apcp" else "nwm_soilsat_top"
      ))[[1L]])
      valid_sources <- if (identical(series_name, "precip")) c("gefs_apcp") else c("nwm_soilsat_top", "gefs_soilw_0_0.1m")
      if (!(source %in% valid_sources)) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.source must be one of: %s",
          series_name
          ,
          paste(valid_sources, collapse = ", ")
        ))
      }
      noisy_blend_enabled <- unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "noisy_blend", "enabled"),
        default = FALSE
      )
      if (!is.logical(noisy_blend_enabled) || length(noisy_blend_enabled) != 1L || is.na(noisy_blend_enabled)) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.noisy_blend.enabled must be boolean (true/false)",
          series_name
        ))
      }
      noisy_blend_sd <- suppressWarnings(as.numeric(unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "noisy_blend", "noise_sd"),
        default = if (identical(series_name, "precip")) 15 else 0.01
      )))
      if (!is.finite(noisy_blend_sd) || noisy_blend_sd < 0) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.noisy_blend.noise_sd must be numeric >= 0",
          series_name
        ))
      }
      noisy_blend_seed <- suppressWarnings(as.integer(unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "noisy_blend", "noise_seed"),
        default = 20260415L
      )))
      if (!is.finite(noisy_blend_seed)) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.noisy_blend.noise_seed must be an integer",
          series_name
        ))
      }
      noisy_blend_floor <- unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "noisy_blend", "floor_at_zero"),
        default = identical(series_name, "precip")
      )
      if (!is.logical(noisy_blend_floor) || length(noisy_blend_floor) != 1L || is.na(noisy_blend_floor)) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.noisy_blend.floor_at_zero must be boolean (true/false)",
          series_name
        ))
      }
      noisy_blend_distribution <- tolower(as.character(unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "noisy_blend", "noise_distribution"),
        default = "normal"
      ))[[1L]])
      if (!(noisy_blend_distribution %in% c("normal", "abs_normal"))) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.noisy_blend.noise_distribution must be one of: normal, abs_normal",
          series_name
        ))
      }
      observed_blend_enabled <- unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "observed_blend", "enabled"),
        default = FALSE
      )
      if (!is.logical(observed_blend_enabled) || length(observed_blend_enabled) != 1L || is.na(observed_blend_enabled)) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.observed_blend.enabled must be boolean (true/false)",
          series_name
        ))
      }
      observed_weight <- suppressWarnings(as.numeric(unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "observed_blend", "observed_weight"),
        default = 0.9
      )))
      if (!is.finite(observed_weight) || observed_weight < 0 || observed_weight > 1) {
        add_err(sprintf(
          "inputs.deterministic_climate.%s.observed_blend.observed_weight must be numeric in [0, 1]",
          series_name
        ))
      }
      observed_zero_stay_prob_raw <- unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "observed_blend", "observed_zero_stay_prob"),
        default = NULL
      )
      if (!is.null(observed_zero_stay_prob_raw)) {
        observed_zero_stay_prob <- suppressWarnings(as.numeric(observed_zero_stay_prob_raw))
        if (!is.finite(observed_zero_stay_prob) || observed_zero_stay_prob < 0 || observed_zero_stay_prob > 1) {
          add_err(sprintf(
            "inputs.deterministic_climate.%s.observed_blend.observed_zero_stay_prob must be null or numeric in [0, 1]",
            series_name
          ))
        }
      }
      observed_zero_stay_seed_raw <- unified_get(
        cfg,
        c("inputs", "deterministic_climate", series_name, "observed_blend", "observed_zero_stay_seed"),
        default = 20260415L
      )
      if (!is.null(observed_zero_stay_seed_raw)) {
        observed_zero_stay_seed <- suppressWarnings(as.integer(observed_zero_stay_seed_raw))
        if (!is.finite(observed_zero_stay_seed)) {
          add_err(sprintf(
            "inputs.deterministic_climate.%s.observed_blend.observed_zero_stay_seed must be null or an integer",
            series_name
          ))
        }
      }
      if (identical(series_name, "precip")) {
        dry_day_threshold_mm <- suppressWarnings(as.numeric(unified_get(
          cfg,
          c("inputs", "deterministic_climate", series_name, "dry_day_threshold_mm"),
          default = 0
        )))
        if (!is.finite(dry_day_threshold_mm) || dry_day_threshold_mm < 0) {
          add_err("inputs.deterministic_climate.precip.dry_day_threshold_mm must be numeric >= 0")
        }
      }
    }
    precip_enabled <- isTRUE(unified_get(
      cfg,
      c("inputs", "deterministic_climate", "precip", "enabled"),
      default = TRUE
    ))
    soil_enabled <- isTRUE(unified_get(
      cfg,
      c("inputs", "deterministic_climate", "soil", "enabled"),
      default = TRUE
    ))
    if (!precip_enabled && !soil_enabled) {
      add_err("inputs.deterministic_climate requires at least one enabled replacement series (precip or soil)")
    }
  }

  covfeat_enabled <- unified_get(cfg, c("inputs", "covariate_features", "enabled"), default = FALSE)
  if (!isTRUE(covfeat_enabled) && !identical(covfeat_enabled, FALSE)) {
    add_err("inputs.covariate_features.enabled must be boolean (true/false)")
  }
  if (isTRUE(covfeat_enabled)) {
    output_filename <- as.character(unified_get(
      cfg,
      c("inputs", "covariate_features", "output_filename"),
      default = "covariate_features.csv"
    )[[1L]])
    if (!nzchar(output_filename)) {
      add_err("inputs.covariate_features.output_filename must be a non-empty filename")
    }
    lag_orders <- unified_get(cfg, c("inputs", "covariate_features", "lag_orders"), default = c(1L, 2L, 3L))
    lag_orders <- as.integer(unlist(lag_orders, use.names = FALSE))
    if (length(lag_orders) < 1L || any(!is.finite(lag_orders)) || any(lag_orders < 1L)) {
      add_err("inputs.covariate_features.lag_orders must be a non-empty list of integers >= 1")
    }
    include_squares <- unified_get(cfg, c("inputs", "covariate_features", "include_squares"), default = TRUE)
    if (!is.logical(include_squares) || length(include_squares) != 1L || is.na(include_squares)) {
      add_err("inputs.covariate_features.include_squares must be boolean (true/false)")
    }
    include_interaction <- unified_get(cfg, c("inputs", "covariate_features", "include_interaction"), default = TRUE)
    if (!is.logical(include_interaction) || length(include_interaction) != 1L || is.na(include_interaction)) {
      add_err("inputs.covariate_features.include_interaction must be boolean (true/false)")
    }
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
  exact_snapshot_root <- unified_get(cfg, c("inputs", "shared", "exact_source_snapshot_root"), NULL)
  if (!is.null(exact_snapshot_root) && nzchar(as.character(exact_snapshot_root))) {
    if (!dir.exists(as.character(exact_snapshot_root))) {
      add_err(sprintf(
        "inputs.shared.exact_source_snapshot_root does not exist or is not a directory: %s",
        as.character(exact_snapshot_root)
      ))
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
  diagnostics_full_slice_psd <- unified_get(cfg, c("fit", "diagnostics", "full_slice_psd"), FALSE)
  if (!isTRUE(diagnostics_full_slice_psd) && !identical(diagnostics_full_slice_psd, FALSE)) {
    add_err("fit.diagnostics.full_slice_psd must be boolean (true/false)")
  }
  diagnostics_psd_warn_tol <- suppressWarnings(as.numeric(unified_get(
    cfg, c("fit", "diagnostics", "psd_warn_tol"), diagnostics_psd_tol
  )))
  if (!is.finite(diagnostics_psd_warn_tol)) {
    add_err("fit.diagnostics.psd_warn_tol must be numeric and finite")
  }
  diagnostics_psd_fail_tol <- suppressWarnings(as.numeric(unified_get(
    cfg, c("fit", "diagnostics", "psd_fail_tol"), diagnostics_psd_tol
  )))
  if (!is.finite(diagnostics_psd_fail_tol)) {
    add_err("fit.diagnostics.psd_fail_tol must be numeric and finite")
  }

  validate_exdqlm_gamma_sigma_block <- function(model_key, defaults) {
    key_prefix <- sprintf("fit.%s.gamma_sigma", model_key)
    path_prefix <- c("fit", model_key, "gamma_sigma")

    cfg_get <- function(path_tail, default = NULL) {
      unified_get(cfg, c(path_prefix, path_tail), default)
    }

    warmup_freeze_iters <- suppressWarnings(as.integer(
      cfg_get("warmup_freeze_iters", defaults$warmup_freeze_iters)
    ))
    if (!is.finite(warmup_freeze_iters) || warmup_freeze_iters < 0L) {
      add_err(sprintf("%s.warmup_freeze_iters must be an integer >= 0", key_prefix))
    }

    min_update_iters <- suppressWarnings(as.integer(
      cfg_get("min_update_iters", defaults$min_update_iters)
    ))
    if (!is.finite(min_update_iters) || min_update_iters < 0L) {
      add_err(sprintf("%s.min_update_iters must be an integer >= 0", key_prefix))
    }

    min_total_iters <- suppressWarnings(as.integer(
      cfg_get("min_total_iters", defaults$min_total_iters)
    ))
    if (!is.finite(min_total_iters) || min_total_iters < 1L) {
      add_err(sprintf("%s.min_total_iters must be an integer >= 1", key_prefix))
    }

    max_iter <- suppressWarnings(as.integer(
      cfg_get("max_iter", defaults$max_iter)
    ))
    if (!is.finite(max_iter) || max_iter < 1L) {
      add_err(sprintf("%s.max_iter must be an integer >= 1", key_prefix))
    }

    convergence_tol <- suppressWarnings(as.numeric(
      cfg_get("convergence_tol", defaults$convergence_tol)
    ))
    if (!is.finite(convergence_tol) || convergence_tol <= 0) {
      add_err(sprintf("%s.convergence_tol must be numeric and > 0", key_prefix))
    }

    elbo_tol <- suppressWarnings(as.numeric(
      cfg_get(c("convergence", "elbo_tol"), defaults$convergence$elbo_tol)
    ))
    if (!is.finite(elbo_tol) || elbo_tol <= 0) {
      add_err(sprintf("%s.convergence.elbo_tol must be numeric and > 0", key_prefix))
    }

    state_norm_sq_tol <- suppressWarnings(as.numeric(
      cfg_get(c("convergence", "state_norm_sq_tol"), defaults$convergence$state_norm_sq_tol)
    ))
    if (!is.finite(state_norm_sq_tol) || state_norm_sq_tol <= 0) {
      add_err(sprintf("%s.convergence.state_norm_sq_tol must be numeric and > 0", key_prefix))
    }

    sigma_exp_tol <- suppressWarnings(as.numeric(
      cfg_get(c("convergence", "sigma_exp_tol"), defaults$convergence$sigma_exp_tol)
    ))
    if (!is.finite(sigma_exp_tol) || sigma_exp_tol <= 0) {
      add_err(sprintf("%s.convergence.sigma_exp_tol must be numeric and > 0", key_prefix))
    }

    gamma_exp_tol <- suppressWarnings(as.numeric(
      cfg_get(c("convergence", "gamma_exp_tol"), defaults$convergence$gamma_exp_tol)
    ))
    if (!is.finite(gamma_exp_tol) || gamma_exp_tol <= 0) {
      add_err(sprintf("%s.convergence.gamma_exp_tol must be numeric and > 0", key_prefix))
    }

    freeze_target <- cfg_get("freeze_target", defaults$freeze_target)
    if (!(freeze_target %in% c("gamma_sigma", "states"))) {
      add_err(sprintf("%s.freeze_target must be one of: gamma_sigma, states", key_prefix))
    }

    guard_refreeze_iters <- suppressWarnings(as.integer(
      cfg_get("guard_refreeze_iters", defaults$guard_refreeze_iters)
    ))
    if (!is.finite(guard_refreeze_iters) || guard_refreeze_iters < 0L) {
      add_err(sprintf("%s.guard_refreeze_iters must be an integer >= 0", key_prefix))
    }

    init_mode <- cfg_get(c("init", "mode"), defaults$init_mode)
    if (!(init_mode %in% c("legacy", "robust"))) {
      add_err(sprintf("%s.init.mode must be one of: legacy, robust", key_prefix))
    }

    init_gamma <- suppressWarnings(as.numeric(
      cfg_get(c("init", "gamma"), defaults$init_gamma)
    ))
    if (!is.finite(init_gamma)) {
      add_err(sprintf("%s.init.gamma must be numeric and finite", key_prefix))
    }

    init_sigma_floor <- suppressWarnings(as.numeric(
      cfg_get(c("init", "sigma_floor"), defaults$init_sigma_floor)
    ))
    if (!is.finite(init_sigma_floor) || init_sigma_floor <= 0) {
      add_err(sprintf("%s.init.sigma_floor must be numeric and > 0", key_prefix))
    }

    init_sigma_scale <- suppressWarnings(as.numeric(
      cfg_get(c("init", "sigma_scale"), defaults$init_sigma_scale)
    ))
    if (!is.finite(init_sigma_scale) || init_sigma_scale <= 0) {
      add_err(sprintf("%s.init.sigma_scale must be numeric and > 0", key_prefix))
    }

    guard_enabled <- cfg_get(c("objective_guard", "enabled"), defaults$guard_enabled)
    if (!isTRUE(guard_enabled) && !identical(guard_enabled, FALSE)) {
      add_err(sprintf("%s.objective_guard.enabled must be boolean (true/false)", key_prefix))
    }

    guard_fail_fast <- cfg_get(c("objective_guard", "fail_fast"), defaults$guard_fail_fast)
    if (!isTRUE(guard_fail_fast) && !identical(guard_fail_fast, FALSE)) {
      add_err(sprintf("%s.objective_guard.fail_fast must be boolean (true/false)", key_prefix))
    }

    guard_log_failures <- cfg_get(c("objective_guard", "log_failures"), defaults$guard_log_failures)
    if (!isTRUE(guard_log_failures) && !identical(guard_log_failures, FALSE)) {
      add_err(sprintf("%s.objective_guard.log_failures must be boolean (true/false)", key_prefix))
    }

    guard_mode <- cfg_get(c("objective_guard", "mode"), defaults$guard_mode)
    if (!(guard_mode %in% c("penalty", "adaptive_freeze"))) {
      add_err(sprintf("%s.objective_guard.mode must be one of: penalty, adaptive_freeze", key_prefix))
    }

    guard_penalty <- suppressWarnings(as.numeric(
      cfg_get(c("objective_guard", "penalty"), defaults$guard_penalty)
    ))
    if (!is.finite(guard_penalty) || guard_penalty <= 0) {
      add_err(sprintf("%s.objective_guard.penalty must be numeric and > 0", key_prefix))
    }
  }

  exdqlm_gamma_sigma_defaults <- list(
    warmup_freeze_iters = 5L,
    min_update_iters = 50L,
    min_total_iters = 50L,
    max_iter = 100L,
    convergence_tol = 1e-6,
    convergence = list(
      elbo_tol = 1e-6,
      state_norm_sq_tol = 1e-6,
      sigma_exp_tol = 1e-6,
      gamma_exp_tol = 1e-6
    ),
    freeze_target = "gamma_sigma",
    guard_refreeze_iters = 10L,
    init_mode = "robust",
    init_gamma = 0.0,
    init_sigma_floor = 1e-3,
    init_sigma_scale = 1.0,
    guard_enabled = TRUE,
    guard_fail_fast = FALSE,
    guard_log_failures = TRUE,
    guard_mode = "adaptive_freeze",
    guard_penalty = 1e12
  )
  exdqlm_multivar_gamma_sigma_defaults <- exdqlm_gamma_sigma_defaults
  exdqlm_univar_gamma_sigma_defaults <- exdqlm_gamma_sigma_defaults
  validate_exdqlm_gamma_sigma_block("exdqlm_multivar", exdqlm_multivar_gamma_sigma_defaults)
  validate_exdqlm_gamma_sigma_block("exdqlm_univar", exdqlm_univar_gamma_sigma_defaults)

  validate_multivar_transfer_compare_fast <- function() {
    key_prefix <- "fit.exdqlm_multivar.gamma_sigma.transfer_compare_fast"
    path_prefix <- c("fit", "exdqlm_multivar", "gamma_sigma", "transfer_compare_fast")
    cfg_get <- function(path_tail, default = NULL) {
      unified_get(cfg, c(path_prefix, path_tail), default)
    }

    enabled <- cfg_get("enabled", FALSE)
    if (!isTRUE(enabled) && !identical(enabled, FALSE)) {
      add_err(sprintf("%s.enabled must be boolean (true/false)", key_prefix))
    }

    warmup_freeze_iters <- suppressWarnings(as.integer(
      cfg_get("warmup_freeze_iters", 5L)
    ))
    if (!is.finite(warmup_freeze_iters) || warmup_freeze_iters < 0L) {
      add_err(sprintf("%s.warmup_freeze_iters must be an integer >= 0", key_prefix))
    }

    min_update_iters <- suppressWarnings(as.integer(
      cfg_get("min_update_iters", 15L)
    ))
    if (!is.finite(min_update_iters) || min_update_iters < 0L) {
      add_err(sprintf("%s.min_update_iters must be an integer >= 0", key_prefix))
    }

    min_total_iters <- suppressWarnings(as.integer(
      cfg_get("min_total_iters", 20L)
    ))
    if (!is.finite(min_total_iters) || min_total_iters < 1L) {
      add_err(sprintf("%s.min_total_iters must be an integer >= 1", key_prefix))
    }

    max_iter <- suppressWarnings(as.integer(
      cfg_get("max_iter", 20L)
    ))
    if (!is.finite(max_iter) || max_iter < 1L) {
      add_err(sprintf("%s.max_iter must be an integer >= 1", key_prefix))
    }

    required_floor <- max(min_total_iters, warmup_freeze_iters + min_update_iters)
    if (isTRUE(enabled) && is.finite(max_iter) && is.finite(required_floor) && max_iter < required_floor) {
      add_err(sprintf(
        "%s.max_iter must be >= max(min_total_iters, warmup_freeze_iters + min_update_iters) when enabled",
        key_prefix
      ))
    }
  }
  validate_multivar_transfer_compare_fast()

  validation_profile <- unified_get(cfg, c("validation", "profile"), "production")
  if (!(validation_profile %in% c("production", "production_proof", "smoke"))) {
    add_err("validation.profile must be one of: production, production_proof, smoke")
  }
  validation_compare_mode <- as.character(unified_get(cfg, c("validation", "compare", "mode"), "both"))
  validation_compare_mode <- if (length(validation_compare_mode) > 0L) {
    tolower(trimws(validation_compare_mode[[1L]]))
  } else {
    "both"
  }
  if (!nzchar(validation_compare_mode)) validation_compare_mode <- "both"
  if (!(validation_compare_mode %in% c("hash", "pixel", "both", "none"))) {
    add_err("validation.compare.mode must be one of: hash, pixel, both, none")
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
