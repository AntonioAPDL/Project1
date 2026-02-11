# unified/contract_checks.R

unified_contract_env_load <- function(rdata_path) {
  env <- new.env(parent = emptyenv())
  load(rdata_path, envir = env)
  env
}

unified_contract_object <- function(env, name) {
  if (!exists(name, envir = env, inherits = FALSE)) return(NULL)
  get(name, envir = env, inherits = FALSE)
}

unified_contract_all_finite <- function(x) {
  if (is.null(x)) return(TRUE)
  if (is.list(x)) {
    if (length(x) == 0L) return(TRUE)
    return(all(vapply(x, unified_contract_all_finite, logical(1))))
  }
  if (is.numeric(x)) {
    return(all(is.finite(x)))
  }
  TRUE
}

unified_contract_ndims <- function(x) {
  d <- dim(x)
  if (is.null(d)) {
    if (length(x) == 0L) return(integer(0))
    return(length(x))
  }
  d
}

unified_contract_write_report <- function(report, report_dir, stem, write_reports = TRUE) {
  out <- list(yaml_path = NULL, json_path = NULL)
  if (!isTRUE(write_reports)) {
    return(out)
  }
  dir.create(report_dir, recursive = TRUE, showWarnings = FALSE)

  yaml_path <- file.path(report_dir, sprintf("%s_contract_check.yaml", stem))
  writeLines(yaml::as.yaml(report, indent.mapping.sequence = TRUE), con = yaml_path, useBytes = TRUE)
  out$yaml_path <- normalizePath(yaml_path, mustWork = FALSE)

  if (requireNamespace("jsonlite", quietly = TRUE)) {
    json_path <- file.path(report_dir, sprintf("%s_contract_check.json", stem))
    jsonlite::write_json(report, path = json_path, auto_unbox = TRUE, pretty = TRUE)
    out$json_path <- normalizePath(json_path, mustWork = FALSE)
  }
  out
}

unified_contract_check_exdqlm_univar <- function(
  rdata_path,
  q_num,
  report_dir,
  write_reports = TRUE
) {
  checks <- list()
  errors <- character(0)
  warnings <- character(0)

  add_check <- function(id, ok, detail) {
    checks[[length(checks) + 1L]] <<- list(
      id = id,
      status = if (isTRUE(ok)) "pass" else "fail",
      detail = as.character(detail)
    )
    if (!isTRUE(ok)) {
      errors <<- c(errors, sprintf("%s: %s", id, detail))
    }
  }
  add_warning <- function(msg) {
    warnings <<- c(warnings, as.character(msg))
  }

  env <- unified_contract_env_load(rdata_path)
  suffix <- sprintf("%d_exAL_synth_DISC_uni", as.integer(q_num))

  obj_new_theta <- unified_contract_object(env, sprintf("new.theta.out_%s", suffix))
  obj_samp_theta <- unified_contract_object(env, sprintf("samp.theta_%s", suffix))
  obj_samp_sigma <- unified_contract_object(env, sprintf("samp.sigma_%s", suffix))
  obj_seq_elbo <- unified_contract_object(env, sprintf("seq.elbo_%s", suffix))

  add_check("univar.new_theta.exists", !is.null(obj_new_theta), "required object missing")
  add_check("univar.samp_theta.exists", !is.null(obj_samp_theta), "required object missing")
  add_check("univar.samp_sigma.exists", !is.null(obj_samp_sigma), "required object missing")
  add_check("univar.seq_elbo.exists", !is.null(obj_seq_elbo), "required object missing")

  Tn <- NA_integer_
  if (!is.null(obj_new_theta)) {
    is_list <- is.list(obj_new_theta)
    add_check("univar.new_theta.is_list", is_list, "expected list with sm/sC/exps fields")
    if (isTRUE(is_list)) {
      req_fields <- c("sm", "sC", "exps")
      missing_fields <- req_fields[!req_fields %in% names(obj_new_theta)]
      add_check(
        "univar.new_theta.required_fields",
        length(missing_fields) == 0L,
        if (length(missing_fields) == 0L) "ok" else sprintf("missing fields: %s", paste(missing_fields, collapse = ", "))
      )
      if (length(missing_fields) == 0L) {
        sm <- obj_new_theta$sm
        sC <- obj_new_theta$sC
        exps <- obj_new_theta$exps

        add_check("univar.new_theta.sm.numeric", is.numeric(sm), "sm must be numeric")
        add_check("univar.new_theta.sm.has_dim", !is.null(dim(sm)) && length(dim(sm)) == 2L, "sm must be a matrix")
        if (!is.null(dim(sm)) && length(dim(sm)) == 2L) {
          Tn <- as.integer(dim(sm)[2])
          add_check("univar.new_theta.sm.T_gt_1000", is.finite(Tn) && Tn > 1000L, sprintf("T=%s", as.character(Tn)))
        } else {
          add_warning("new.theta.sm did not provide a 2D shape; downstream T checks skipped.")
        }
        add_check("univar.new_theta.sm.finite", unified_contract_all_finite(sm), "sm contains non-finite values")

        sC_dim <- dim(sC)
        add_check("univar.new_theta.sC.numeric", is.numeric(sC), "sC must be numeric")
        add_check("univar.new_theta.sC.shape", !is.null(sC_dim) && length(sC_dim) == 3L, "sC must be a 3D array")
        if (!is.null(sC_dim) && length(sC_dim) == 3L && is.finite(Tn)) {
          add_check("univar.new_theta.sC.T_matches_sm", as.integer(sC_dim[3]) == as.integer(Tn), sprintf("sC third dim=%d, sm T=%d", as.integer(sC_dim[3]), as.integer(Tn)))
        }
        add_check("univar.new_theta.sC.finite", unified_contract_all_finite(sC), "sC contains non-finite values")

        add_check("univar.new_theta.exps.numeric", is.numeric(exps), "exps must be numeric")
        exps_dim <- dim(exps)
        add_check("univar.new_theta.exps.shape", !is.null(exps_dim) && length(exps_dim) == 2L, "exps must be a 2D matrix")
        if (!is.null(exps_dim) && length(exps_dim) == 2L && is.finite(Tn)) {
          add_check("univar.new_theta.exps.T_matches_sm", as.integer(exps_dim[2]) == as.integer(Tn), sprintf("exps ncol=%d, sm T=%d", as.integer(exps_dim[2]), as.integer(Tn)))
        }
        add_check("univar.new_theta.exps.finite", unified_contract_all_finite(exps), "exps contains non-finite values")
      }
    }
  }

  if (!is.null(obj_samp_theta)) {
    if (is.list(obj_samp_theta) && ("samp_theta" %in% names(obj_samp_theta))) {
      obj_samp_theta <- obj_samp_theta$samp_theta
    }
    add_check("univar.samp_theta.numeric", is.numeric(obj_samp_theta), "samp.theta must be numeric")
    st_dim <- dim(obj_samp_theta)
    add_check("univar.samp_theta.has_dim", !is.null(st_dim), "samp.theta must have dimensions")
    if (!is.null(st_dim) && is.finite(Tn)) {
      add_check("univar.samp_theta.contains_T", any(as.integer(st_dim) == as.integer(Tn)), sprintf("dims=%s, expected one dim == T=%d", paste(st_dim, collapse = "x"), as.integer(Tn)))
    }
    add_check("univar.samp_theta.finite", unified_contract_all_finite(obj_samp_theta), "samp.theta contains non-finite values")
  }

  if (!is.null(obj_samp_sigma)) {
    if (is.list(obj_samp_sigma) && ("samp_sigma" %in% names(obj_samp_sigma))) {
      obj_samp_sigma <- obj_samp_sigma$samp_sigma
    }
    add_check("univar.samp_sigma.numeric", is.numeric(obj_samp_sigma), "samp.sigma must be numeric")
    add_check("univar.samp_sigma.len_ge_1", length(obj_samp_sigma) >= 1L, sprintf("length=%d", length(obj_samp_sigma)))
    add_check("univar.samp_sigma.finite", unified_contract_all_finite(obj_samp_sigma), "samp.sigma contains non-finite values")
  }

  if (!is.null(obj_seq_elbo)) {
    add_check("univar.seq_elbo.numeric", is.numeric(obj_seq_elbo), "seq.elbo must be numeric")
    add_check("univar.seq_elbo.len_ge_1", length(obj_seq_elbo) >= 1L, sprintf("length=%d", length(obj_seq_elbo)))
    add_check("univar.seq_elbo.finite", unified_contract_all_finite(obj_seq_elbo), "seq.elbo contains non-finite values")
  }

  status <- if (length(errors) == 0L) "pass" else "fail"
  report <- list(
    family = "exdqlm_univar",
    implementation_mode = "theory_aligned",
    quantile = as.integer(q_num),
    rdata_path = normalizePath(rdata_path, mustWork = FALSE),
    status = status,
    errors = unname(errors),
    warnings = unname(warnings),
    checks = checks,
    checked_at_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  )
  report_paths <- unified_contract_write_report(
    report = report,
    report_dir = report_dir,
    stem = sprintf("q%s_exdqlm_univar", sprintf("%02d", as.integer(q_num))),
    write_reports = write_reports
  )
  report$report_paths <- report_paths
  report
}

unified_contract_check_ndlm_main <- function(
  rdata_path,
  report_dir,
  summary_log_path = NULL,
  write_reports = TRUE
) {
  checks <- list()
  errors <- character(0)
  warnings <- character(0)

  add_check <- function(id, ok, detail) {
    checks[[length(checks) + 1L]] <<- list(
      id = id,
      status = if (isTRUE(ok)) "pass" else "fail",
      detail = as.character(detail)
    )
    if (!isTRUE(ok)) {
      errors <<- c(errors, sprintf("%s: %s", id, detail))
    }
  }
  add_warning <- function(msg) {
    warnings <<- c(warnings, as.character(msg))
  }

  env <- unified_contract_env_load(rdata_path)
  required_names <- c(
    "new.theta.out_50_NDLM_synth_DISC",
    "samp.theta_50_NDLM_synth_DISC",
    "samp.sigma_50_NDLM_synth_DISC",
    "samp.theta_ens_50_NDLM_synth_DISC",
    "seq.elbo_50_NDLM_synth_DISC",
    "seq.sigma_50_NDLM_synth_DISC",
    "delta_50_NDLM_synth_DISC"
  )
  for (nm in required_names) {
    add_check(
      sprintf("ndlm.%s.exists", nm),
      exists(nm, envir = env, inherits = FALSE),
      "required object missing"
    )
  }

  new_theta <- unified_contract_object(env, "new.theta.out_50_NDLM_synth_DISC")
  samp_theta <- unified_contract_object(env, "samp.theta_50_NDLM_synth_DISC")
  samp_sigma <- unified_contract_object(env, "samp.sigma_50_NDLM_synth_DISC")
  samp_theta_ens <- unified_contract_object(env, "samp.theta_ens_50_NDLM_synth_DISC")
  seq_elbo <- unified_contract_object(env, "seq.elbo_50_NDLM_synth_DISC")
  seq_sigma <- unified_contract_object(env, "seq.sigma_50_NDLM_synth_DISC")
  delta <- unified_contract_object(env, "delta_50_NDLM_synth_DISC")

  Tn <- NA_integer_
  if (!is.null(new_theta)) {
    add_check("ndlm.new_theta.is_list", is.list(new_theta), "new.theta must be a list")
    if (is.list(new_theta)) {
      req_fields <- c("sm", "sC", "sm_ens", "sC_ens", "exps")
      missing_fields <- req_fields[!req_fields %in% names(new_theta)]
      add_check(
        "ndlm.new_theta.required_fields",
        length(missing_fields) == 0L,
        if (length(missing_fields) == 0L) "ok" else sprintf("missing fields: %s", paste(missing_fields, collapse = ", "))
      )
      if (length(missing_fields) == 0L) {
        sm <- new_theta$sm
        sC <- new_theta$sC
        exps <- new_theta$exps
        sm_ens <- new_theta$sm_ens
        sC_ens <- new_theta$sC_ens

        add_check("ndlm.new_theta.sm.numeric", is.numeric(sm), "sm must be numeric")
        add_check("ndlm.new_theta.sm.shape", !is.null(dim(sm)) && length(dim(sm)) == 2L, "sm must be a matrix")
        if (!is.null(dim(sm)) && length(dim(sm)) == 2L) {
          Tn <- as.integer(dim(sm)[2])
          add_check("ndlm.new_theta.sm.T_gt_1000", is.finite(Tn) && Tn > 1000L, sprintf("T=%s", as.character(Tn)))
        }
        add_check("ndlm.new_theta.sm.finite", unified_contract_all_finite(sm), "sm contains non-finite values")

        sC_dim <- dim(sC)
        add_check("ndlm.new_theta.sC.numeric", is.numeric(sC), "sC must be numeric")
        add_check("ndlm.new_theta.sC.shape", !is.null(sC_dim) && length(sC_dim) == 3L, "sC must be a 3D array")
        if (!is.null(sC_dim) && length(sC_dim) == 3L && is.finite(Tn)) {
          add_check("ndlm.new_theta.sC.T_matches_sm", as.integer(sC_dim[3]) == as.integer(Tn), sprintf("sC third dim=%d, sm T=%d", as.integer(sC_dim[3]), as.integer(Tn)))
        }
        add_check("ndlm.new_theta.sC.finite", unified_contract_all_finite(sC), "sC contains non-finite values")

        add_check("ndlm.new_theta.sm_ens.is_list", is.list(sm_ens), "sm_ens must be a list")
        if (is.list(sm_ens) && length(sm_ens) > 0L) {
          sm_ens_ok <- vapply(sm_ens, function(x) is.numeric(x) && !is.null(dim(x)) && length(dim(x)) == 2L, logical(1))
          add_check("ndlm.new_theta.sm_ens.shape", all(sm_ens_ok), "sm_ens entries must be numeric matrices")
          add_check("ndlm.new_theta.sm_ens.finite", unified_contract_all_finite(sm_ens), "sm_ens contains non-finite values")
        } else {
          add_warning("new.theta.sm_ens is empty; downstream ensemble diagnostics may be limited.")
        }

        add_check("ndlm.new_theta.sC_ens.is_list", is.list(sC_ens), "sC_ens must be a list")
        if (is.list(sC_ens) && length(sC_ens) > 0L) {
          sC_ens_ok <- vapply(sC_ens, function(x) is.numeric(x) && !is.null(dim(x)) && length(dim(x)) == 3L, logical(1))
          add_check("ndlm.new_theta.sC_ens.shape", all(sC_ens_ok), "sC_ens entries must be numeric 3D arrays")
          add_check("ndlm.new_theta.sC_ens.finite", unified_contract_all_finite(sC_ens), "sC_ens contains non-finite values")
        }

        exps_dim <- dim(exps)
        add_check("ndlm.new_theta.exps.numeric", is.numeric(exps), "exps must be numeric")
        add_check("ndlm.new_theta.exps.shape", !is.null(exps_dim) && length(exps_dim) == 2L, "exps must be a 2D matrix")
        if (!is.null(exps_dim) && length(exps_dim) == 2L && is.finite(Tn)) {
          add_check("ndlm.new_theta.exps.T_matches_sm", as.integer(exps_dim[2]) == as.integer(Tn), sprintf("exps ncol=%d, sm T=%d", as.integer(exps_dim[2]), as.integer(Tn)))
        }
        add_check("ndlm.new_theta.exps.finite", unified_contract_all_finite(exps), "exps contains non-finite values")
      }
    }
  }

  if (!is.null(samp_theta)) {
    if (is.list(samp_theta) && ("samp_theta" %in% names(samp_theta))) {
      samp_theta <- samp_theta$samp_theta
    }
    add_check("ndlm.samp_theta.numeric", is.numeric(samp_theta), "samp.theta must be numeric")
    st_dim <- dim(samp_theta)
    add_check("ndlm.samp_theta.has_dim", !is.null(st_dim), "samp.theta must have dimensions")
    if (!is.null(st_dim) && is.finite(Tn)) {
      add_check("ndlm.samp_theta.contains_T", any(as.integer(st_dim) == as.integer(Tn)), sprintf("dims=%s, expected one dim == T=%d", paste(st_dim, collapse = "x"), as.integer(Tn)))
    }
    add_check("ndlm.samp_theta.finite", unified_contract_all_finite(samp_theta), "samp.theta contains non-finite values")
  }

  if (!is.null(samp_sigma)) {
    if (is.list(samp_sigma) && ("samp_sigma" %in% names(samp_sigma))) {
      samp_sigma <- samp_sigma$samp_sigma
    }
    add_check("ndlm.samp_sigma.numeric", is.numeric(samp_sigma), "samp.sigma must be numeric")
    add_check("ndlm.samp_sigma.len_ge_1", length(samp_sigma) >= 1L, sprintf("length=%d", length(samp_sigma)))
    add_check("ndlm.samp_sigma.finite", unified_contract_all_finite(samp_sigma), "samp.sigma contains non-finite values")
  }

  if (!is.null(samp_theta_ens)) {
    if (is.list(samp_theta_ens) && ("samp_theta_ens" %in% names(samp_theta_ens))) {
      samp_theta_ens <- samp_theta_ens$samp_theta_ens
    }
    leaf_arrays <- list()
    collect_numeric_leaves <- function(x) {
      if (is.list(x)) {
        if (length(x) == 0L) return(invisible(NULL))
        for (item in x) collect_numeric_leaves(item)
        return(invisible(NULL))
      }
      if (is.numeric(x)) {
        leaf_arrays[[length(leaf_arrays) + 1L]] <<- x
      }
      invisible(NULL)
    }
    collect_numeric_leaves(samp_theta_ens)
    add_check("ndlm.samp_theta_ens.numeric_leaves", length(leaf_arrays) > 0L, "samp.theta_ens must contain numeric leaves")
    if (length(leaf_arrays) > 0L) {
      add_check("ndlm.samp_theta_ens.finite", all(vapply(leaf_arrays, unified_contract_all_finite, logical(1))), "samp.theta_ens contains non-finite values")
      dims_ok <- vapply(leaf_arrays, function(x) {
        d <- dim(x)
        !is.null(d) && length(d) >= 2L
      }, logical(1))
      add_check("ndlm.samp_theta_ens.dim_rank_ge_2", all(dims_ok), "samp.theta_ens numeric leaves must have rank >= 2")
    }
  }

  for (nm in c("seq_elbo", "seq_sigma", "delta")) {
    obj <- switch(
      nm,
      seq_elbo = seq_elbo,
      seq_sigma = seq_sigma,
      delta = delta
    )
    if (!is.null(obj)) {
      add_check(sprintf("ndlm.%s.numeric", nm), is.numeric(obj), sprintf("%s must be numeric", nm))
      add_check(sprintf("ndlm.%s.len_ge_1", nm), length(obj) >= 1L, sprintf("length=%d", length(obj)))
      add_check(sprintf("ndlm.%s.finite", nm), unified_contract_all_finite(obj), sprintf("%s contains non-finite values", nm))
    }
  }

  if (!is.null(summary_log_path) && nzchar(summary_log_path)) {
    add_check("ndlm.summary_log.exists", file.exists(summary_log_path), "summary log file missing")
    if (file.exists(summary_log_path)) {
      add_check("ndlm.summary_log.nonempty", file.info(summary_log_path)$size > 0L, sprintf("summary log size=%d", as.integer(file.info(summary_log_path)$size)))
    }
  } else {
    add_warning("summary log path was not provided to NDLM contract check.")
  }

  status <- if (length(errors) == 0L) "pass" else "fail"
  report <- list(
    family = "ndlm_main",
    implementation_mode = "theory_aligned",
    rdata_path = normalizePath(rdata_path, mustWork = FALSE),
    summary_log_path = if (is.null(summary_log_path)) NULL else normalizePath(summary_log_path, mustWork = FALSE),
    status = status,
    errors = unname(errors),
    warnings = unname(warnings),
    checks = checks,
    checked_at_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  )
  report_paths <- unified_contract_write_report(
    report = report,
    report_dir = report_dir,
    stem = "ndlm_main",
    write_reports = write_reports
  )
  report$report_paths <- report_paths
  report
}
