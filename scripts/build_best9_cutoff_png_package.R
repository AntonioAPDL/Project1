#!/usr/bin/env Rscript

`%||%` <- function(x, y) {
  if (is.null(x) || identical(x, "") || (length(x) == 1L && is.na(x))) y else x
}

parse_args <- function(argv) {
  out <- list()
  i <- 1L
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (!startsWith(key, "--")) {
      i <- i + 1L
      next
    }
    key <- sub("^--", "", key)
    key <- gsub("-", "_", key, fixed = TRUE)
    if (i == length(argv) || startsWith(argv[[i + 1L]], "--")) {
      out[[key]] <- TRUE
      i <- i + 1L
    } else {
      out[[key]] <- argv[[i + 1L]]
      i <- i + 2L
    }
  }
  out
}

args <- parse_args(commandArgs(trailingOnly = TRUE))

runtime_root <- normalizePath(
  args$runtime_root %||% "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402",
  mustWork = TRUE
)
reports_root <- file.path(runtime_root, "reports")
runs_root <- file.path(runtime_root, "runs")
default_output <- file.path(runtime_root, "exports", sprintf("best9_cutoff_png_package_%s", format(Sys.Date(), "%Y%m%d")))
output_root <- normalizePath(args$output_dir %||% default_output, mustWork = FALSE)
dir.create(output_root, recursive = TRUE, showWarnings = FALSE)

model_order <- data.frame(
  rank = sprintf("%02d", 1:9),
  model_id = c(
    "ndlm_univar_synth_keep",
    "ndlm_main_synth_drop",
    "ndlm_main_synth_keep",
    "dqlm_univar_al_synth",
    "dqlm_multivar_al_synth_drop",
    "dqlm_multivar_al_synth_keep",
    "exdqlm_univar_synth",
    "exdqlm_multivar_synth_drop",
    "exdqlm_multivar_synth_keep"
  ),
  stringsAsFactors = FALSE
)

cutoffs <- c("20210123", "20211112", "20211221", "20220511", "20221225")
invariant_models <- c(
  "dqlm_univar_al_synth",
  "exdqlm_univar_synth",
  "ndlm_main_synth_keep",
  "ndlm_main_synth_drop",
  "ndlm_univar_synth_keep"
)

parse_bundle <- function(path) {
  nm <- basename(path)
  m <- regexec("^multimodel_([0-9]{8})_v8_([^_]+)_compare$", nm)
  x <- regmatches(nm, m)[[1]]
  if (length(x) == 0L) return(NULL)
  data.frame(cutoff = x[2], bundle_label = x[3], bundle = path, stringsAsFactors = FALSE)
}

bundle_dirs <- list.dirs(reports_root, recursive = FALSE, full.names = TRUE)
bundle_df <- do.call(rbind, Filter(Negate(is.null), lapply(bundle_dirs, parse_bundle)))
if (is.null(bundle_df) || nrow(bundle_df) == 0L) {
  stop(sprintf("No compare bundles found under %s", reports_root), call. = FALSE)
}

crps_rows <- list()
for (i in seq_len(nrow(bundle_df))) {
  csv_path <- file.path(bundle_df$bundle[i], "crps_forecast_summary_all_models.csv")
  if (!file.exists(csv_path)) next
  x <- read.csv(csv_path, stringsAsFactors = FALSE, check.names = FALSE)
  x <- x[x$model_id %in% model_order$model_id, c("model_id", "mean_crps"), drop = FALSE]
  if (!nrow(x)) next
  x$cutoff <- bundle_df$cutoff[i]
  x$selected_bundle_label <- bundle_df$bundle_label[i]
  x$bundle_path <- bundle_df$bundle[i]
  crps_rows[[length(crps_rows) + 1L]] <- x
}

all_crps <- do.call(rbind, crps_rows)
all_crps <- all_crps[order(all_crps$cutoff, all_crps$model_id, all_crps$mean_crps, all_crps$selected_bundle_label, method = "radix"), , drop = FALSE]
best_crps <- all_crps[!duplicated(all_crps[c("cutoff", "model_id")]), , drop = FALSE]

source_bundle_label_for_model <- function(model_id, selected_bundle_label) {
  if (model_id %in% invariant_models) {
    "epsTT"
  } else {
    selected_bundle_label
  }
}

source_run_id_for_model <- function(cutoff, model_id, source_bundle_label) {
  suffix <- if (grepl("^dqlm_multivar_", model_id)) {
    if (identical(source_bundle_label, "epsTT")) "l1" else "l1_mv"
  } else if (grepl("^exdqlm_multivar_", model_id)) {
    if (identical(source_bundle_label, "epsTT")) "l2" else "l2_mv"
  } else if (identical(model_id, "dqlm_univar_al_synth")) {
    "l1"
  } else if (identical(model_id, "exdqlm_univar_synth")) {
    "l2"
  } else if (model_id %in% c("ndlm_main_synth_keep", "ndlm_univar_synth_keep")) {
    "l1"
  } else if (identical(model_id, "ndlm_main_synth_drop")) {
    "l2"
  } else {
    stop(sprintf("Unhandled model_id for run resolution: %s", model_id), call. = FALSE)
  }
  file.path(runs_root, sprintf("multimodel_%s_v8_%s_%s", cutoff, source_bundle_label, suffix))
}

main_plot_type_for_model <- function(model_id) {
  if (grepl("^ndlm_", model_id)) "cutoff_window_predictive_bands" else "cutoff_window_posterior_samples"
}

companion_plot_type_for_model <- function(model_id) {
  if (grepl("^ndlm_", model_id)) {
    "cutoff_window_predictive_bands_with_raw_ensembles"
  } else {
    "cutoff_window_posterior_samples_with_raw_ensembles"
  }
}

plot_path_for_model <- function(run_dir, model_id, plot_type) {
  outputs_dir <- file.path(run_dir, "post", "outputs", basename(run_dir))
  file.path(outputs_dir, sprintf("%s_%s.png", model_id, plot_type))
}

manifest_rows <- list()
copied <- 0L

for (cutoff in cutoffs) {
  cutoff_dir <- file.path(output_root, cutoff)
  dir.create(cutoff_dir, recursive = TRUE, showWarnings = FALSE)
  selected <- merge(
    model_order,
    best_crps[best_crps$cutoff == cutoff, c("cutoff", "model_id", "mean_crps", "selected_bundle_label"), drop = FALSE],
    by = "model_id",
    all.x = TRUE,
    sort = FALSE
  )
  selected <- selected[match(model_order$model_id, selected$model_id), , drop = FALSE]
  if (anyNA(selected$selected_bundle_label)) {
    stop(sprintf("Missing CRPS selection rows for cutoff %s", cutoff), call. = FALSE)
  }

  for (i in seq_len(nrow(selected))) {
    row <- selected[i, , drop = FALSE]
    source_bundle_label <- source_bundle_label_for_model(row$model_id[[1L]], row$selected_bundle_label[[1L]])
    run_dir <- source_run_id_for_model(cutoff, row$model_id[[1L]], source_bundle_label)
    if (!dir.exists(run_dir)) {
      stop(sprintf("Missing run directory for %s %s: %s", cutoff, row$model_id[[1L]], run_dir), call. = FALSE)
    }

    main_plot_type <- main_plot_type_for_model(row$model_id[[1L]])
    comp_plot_type <- companion_plot_type_for_model(row$model_id[[1L]])
    src_main <- plot_path_for_model(run_dir, row$model_id[[1L]], main_plot_type)
    src_comp <- plot_path_for_model(run_dir, row$model_id[[1L]], comp_plot_type)
    if (!file.exists(src_main) || !file.exists(src_comp)) {
      stop(sprintf("Missing source plots for %s %s", cutoff, row$model_id[[1L]]), call. = FALSE)
    }

    dest_main <- file.path(cutoff_dir, sprintf("%s_%s.png", row$rank[[1L]], row$model_id[[1L]]))
    dest_comp <- file.path(cutoff_dir, sprintf("%s_%s_with_raw_ensembles.png", row$rank[[1L]], row$model_id[[1L]]))
    ok_main <- file.copy(src_main, dest_main, overwrite = TRUE)
    ok_comp <- file.copy(src_comp, dest_comp, overwrite = TRUE)
    if (!isTRUE(ok_main) || !isTRUE(ok_comp)) {
      stop(sprintf("Failed copying package plots for %s %s", cutoff, row$model_id[[1L]]), call. = FALSE)
    }
    copied <- copied + 2L

    manifest_rows[[length(manifest_rows) + 1L]] <- data.frame(
      cutoff = cutoff,
      rank = row$rank[[1L]],
      model_id = row$model_id[[1L]],
      mean_crps = as.numeric(row$mean_crps[[1L]]),
      selected_bundle_label = row$selected_bundle_label[[1L]],
      source_bundle_label = source_bundle_label,
      source_run_dir = normalizePath(run_dir, mustWork = FALSE),
      main_plot_type = main_plot_type,
      companion_plot_type = comp_plot_type,
      main_source_path = normalizePath(src_main, mustWork = FALSE),
      companion_source_path = normalizePath(src_comp, mustWork = FALSE),
      packaged_main_path = normalizePath(dest_main, mustWork = FALSE),
      packaged_companion_path = normalizePath(dest_comp, mustWork = FALSE),
      stringsAsFactors = FALSE
    )
  }
}

selection_manifest <- do.call(rbind, manifest_rows)
selection_manifest <- selection_manifest[order(selection_manifest$cutoff, selection_manifest$rank, method = "radix"), , drop = FALSE]
write.csv(selection_manifest, file.path(output_root, "selection_manifest.csv"), row.names = FALSE)

readme_lines <- c(
  "Best 9 model PNG package by cutoff",
  "",
  "Structure:",
  "- one subfolder per cutoff",
  "- 18 PNGs per cutoff",
  "- 9 main plots + 9 raw-ensemble companion plots",
  "",
  "Model order:",
  "01 ndlm_univar_synth_keep",
  "02 ndlm_main_synth_drop",
  "03 ndlm_main_synth_keep",
  "04 dqlm_univar_al_synth",
  "05 dqlm_multivar_al_synth_drop",
  "06 dqlm_multivar_al_synth_keep",
  "07 exdqlm_univar_synth",
  "08 exdqlm_multivar_synth_drop",
  "09 exdqlm_multivar_synth_keep",
  "",
  "For invariant families, the CRPS best selection can appear under different compare bundles,",
  "but the packaged source plot is normalized to the epsTT run because the figure itself is invariant."
)
writeLines(readme_lines, con = file.path(output_root, "README.txt"))

cat(sprintf("PACKAGE_ROOT %s\n", output_root))
cat(sprintf("COPIED_PNGS %d\n", copied))
cat(sprintf("SELECTION_MANIFEST %s\n", file.path(output_root, "selection_manifest.csv")))
