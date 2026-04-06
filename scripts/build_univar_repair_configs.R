#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(yaml)
})

args <- commandArgs(trailingOnly = TRUE)

`%||%` <- function(x, y) if (is.null(x)) y else x

parse_args <- function(args) {
  out <- list(
    base_config = "config/unified_runs/repair_r1_univar_exal_triage_20210123_20260324.yaml",
    out_dir = "config/unified_runs",
    stamp = format(Sys.time(), "%Y%m%d")
  )
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    val <- if (i < length(args)) args[[i + 1L]] else NULL
    if (identical(key, "--base-config")) out$base_config <- val
    if (identical(key, "--out-dir")) out$out_dir <- val
    if (identical(key, "--stamp")) out$stamp <- val
    i <- i + 2L
  }
  out
}

cfg_set <- function(x, path, value) {
  ref <- x
  cur <- ref
  for (i in seq_len(length(path) - 1L)) {
    nm <- path[[i]]
    if (is.null(cur[[nm]]) || !is.list(cur[[nm]])) cur[[nm]] <- list()
    parent <- cur
    cur <- cur[[nm]]
    ref <- modifyList(ref, setNames(list(parent[[nm]]), nm))
  }
  cur <- ref
  for (i in seq_len(length(path) - 1L)) {
    nm <- path[[i]]
    if (is.null(cur[[nm]]) || !is.list(cur[[nm]])) cur[[nm]] <- list()
    cur <- cur[[nm]]
  }
  # fallback to recursive assignment
  assign_into <- function(obj, idx) {
    nm <- path[[idx]]
    if (idx == length(path)) {
      obj[[nm]] <- value
      return(obj)
    }
    child <- obj[[nm]]
    if (is.null(child) || !is.list(child)) child <- list()
    obj[[nm]] <- assign_into(child, idx + 1L)
    obj
  }
  assign_into(x, 1L)
}

normalized_cfg <- function(base_cfg, run_id, likelihood_mode, quantiles) {
  cfg <- base_cfg
  cfg <- cfg_set(cfg, c("run", "run_id"), run_id)
  cfg <- cfg_set(cfg, c("run", "overwrite"), FALSE)
  cfg <- cfg_set(cfg, c("run", "auto_suffix_on_collision"), TRUE)
  cfg <- cfg_set(cfg, c("dates", "data_start"), "2010-01-01")
  cfg <- cfg_set(cfg, c("models", "run_exdqlm_multivar"), FALSE)
  cfg <- cfg_set(cfg, c("models", "run_exdqlm_univar"), TRUE)
  cfg <- cfg_set(cfg, c("models", "run_ndlm_main"), FALSE)
  cfg <- cfg_set(cfg, c("models", "run_ndlm_univar"), FALSE)
  cfg <- cfg_set(cfg, c("models", "exdqlm_univar", "implementation_mode"), "legacy_bridge")
  cfg <- cfg_set(cfg, c("models", "exdqlm_univar", "likelihood_mode"), likelihood_mode)
  cfg <- cfg_set(cfg, c("fit", "quantiles"), quantiles)
  cfg <- cfg_set(cfg, c("post", "crps_input_health", "enabled"), TRUE)
  cfg <- cfg_set(cfg, c("post", "crps_input_health", "fail_fast"), TRUE)
  cfg <- cfg_set(cfg, c("post", "export_tables"), TRUE)
  cfg
}

write_cfg <- function(cfg, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(as.yaml(cfg, indent.mapping.sequence = TRUE), con = path, useBytes = TRUE)
}

main <- function() {
  opts <- parse_args(args)
  base_cfg <- yaml::read_yaml(opts$base_config)

  specs <- list(
    list(
      run_id = sprintf("repair_p5_univar_exal_triage_20210123_%s", opts$stamp),
      likelihood_mode = "exal",
      quantiles = c(0.05, 0.50, 0.95)
    ),
    list(
      run_id = sprintf("repair_p6_univar_exal_full7_20210123_%s", opts$stamp),
      likelihood_mode = "exal",
      quantiles = c(0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95)
    ),
    list(
      run_id = sprintf("repair_p7_univar_al_triage_20210123_%s", opts$stamp),
      likelihood_mode = "al",
      quantiles = c(0.05, 0.50, 0.95)
    ),
    list(
      run_id = sprintf("repair_p7_univar_al_full7_20210123_%s", opts$stamp),
      likelihood_mode = "al",
      quantiles = c(0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95)
    )
  )

  written <- character()
  for (spec in specs) {
    cfg <- normalized_cfg(
      base_cfg = base_cfg,
      run_id = spec$run_id,
      likelihood_mode = spec$likelihood_mode,
      quantiles = spec$quantiles
    )
    out_path <- file.path(opts$out_dir, sprintf("%s.yaml", spec$run_id))
    write_cfg(cfg, out_path)
    written <- c(written, out_path)
  }

  cat(paste(written, collapse = "\n"), sep = "\n")
}

main()
