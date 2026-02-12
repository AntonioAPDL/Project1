# unified/preflight.R

unified_df_parse_percent <- function(x) {
  suppressWarnings(as.numeric(gsub("%", "", as.character(x), fixed = TRUE)))
}

unified_storage_snapshot <- function(path) {
  target <- if (is.null(path) || !nzchar(as.character(path))) getwd() else as.character(path)
  target <- normalizePath(target, mustWork = FALSE)

  parse_line <- function(lines, expect = c("blocks", "inodes")) {
    expect <- match.arg(expect)
    lines <- lines[nzchar(lines)]
    if (length(lines) < 2L) {
      stop(sprintf("unable to parse df output for %s", target), call. = FALSE)
    }
    line <- lines[[length(lines)]]
    fields <- strsplit(trimws(line), "\\s+")[[1]]
    if (length(fields) < 6L) {
      stop(sprintf("unexpected df output format for %s: %s", target, line), call. = FALSE)
    }
    list(
      filesystem = fields[[1L]],
      total = suppressWarnings(as.numeric(fields[[2L]])),
      used = suppressWarnings(as.numeric(fields[[3L]])),
      avail = suppressWarnings(as.numeric(fields[[4L]])),
      used_pct = unified_df_parse_percent(fields[[5L]]),
      mountpoint = fields[[6L]]
    )
  }

  blocks_out <- system2("df", c("-Pk", target), stdout = TRUE, stderr = TRUE)
  blocks_status <- attr(blocks_out, "status")
  if (!is.null(blocks_status) && blocks_status != 0) {
    stop(sprintf("df -Pk failed for %s: %s", target, paste(blocks_out, collapse = " | ")), call. = FALSE)
  }
  block_info <- parse_line(blocks_out, expect = "blocks")

  inode_out <- system2("df", c("-Pi", target), stdout = TRUE, stderr = TRUE)
  inode_status <- attr(inode_out, "status")
  inode_info <- if (!is.null(inode_status) && inode_status != 0) {
    list(total = NA_real_, used = NA_real_, avail = NA_real_, used_pct = NA_real_, mountpoint = block_info$mountpoint)
  } else {
    parse_line(inode_out, expect = "inodes")
  }

  free_bytes <- as.numeric(block_info$avail) * 1024
  free_inodes_pct <- if (is.finite(inode_info$total) && inode_info$total > 0) {
    (as.numeric(inode_info$avail) / as.numeric(inode_info$total)) * 100
  } else {
    NA_real_
  }

  list(
    path = target,
    filesystem = block_info$filesystem,
    mountpoint = block_info$mountpoint,
    free_bytes = free_bytes,
    free_gb = free_bytes / (1024^3),
    used_pct = as.numeric(block_info$used_pct),
    free_inodes = as.numeric(inode_info$avail),
    total_inodes = as.numeric(inode_info$total),
    free_inodes_pct = free_inodes_pct
  )
}

unified_require_free_space <- function(path, min_free_bytes, min_free_inodes_pct = NULL, context = "") {
  scalar_num <- function(x) {
    x <- suppressWarnings(as.numeric(x))
    if (length(x) == 0L) return(NA_real_)
    x[[1L]]
  }
  min_free_bytes <- scalar_num(min_free_bytes)
  min_free_inodes_pct <- scalar_num(min_free_inodes_pct)

  thresholds_active <- (is.finite(min_free_bytes) && min_free_bytes > 0) ||
    (is.finite(min_free_inodes_pct) && min_free_inodes_pct > 0)
  if (!thresholds_active) {
    return(invisible(NULL))
  }

  snap <- unified_storage_snapshot(path)
  violations <- character(0)

  if (is.finite(min_free_bytes) && min_free_bytes > 0 && (!is.finite(snap$free_bytes) || snap$free_bytes < min_free_bytes)) {
    violations <- c(
      violations,
      sprintf(
        "free space %.2f GB below threshold %.2f GB",
        snap$free_gb,
        min_free_bytes / (1024^3)
      )
    )
  }

  if (is.finite(min_free_inodes_pct) && min_free_inodes_pct > 0 &&
      (!is.finite(snap$free_inodes_pct) || snap$free_inodes_pct < min_free_inodes_pct)) {
    violations <- c(
      violations,
      sprintf("free inode pct %.2f%% below threshold %.2f%%", snap$free_inodes_pct, min_free_inodes_pct)
    )
  }

  if (length(violations) > 0L) {
    ctx <- if (nzchar(context)) sprintf("[%s] ", context) else ""
    msg <- paste(
      c(
        sprintf("%sStorage preflight failed.", ctx),
        sprintf("- path: %s", snap$path),
        sprintf("- mountpoint: %s", snap$mountpoint),
        sprintf("- filesystem: %s", snap$filesystem),
        sprintf("- free_gb: %.2f", snap$free_gb),
        sprintf("- used_pct: %.2f%%", snap$used_pct),
        sprintf("- free_inodes_pct: %s", if (is.finite(snap$free_inodes_pct)) sprintf("%.2f%%", snap$free_inodes_pct) else "NA"),
        paste0("- ", violations),
        "- cleanup_suggestions: prune old repro/runs entries, prune repro/baseline_runs, clear large caches under /data/muscat_data/jaguir26/.cache"
      ),
      collapse = "\n"
    )
    stop(msg, call. = FALSE)
  }

  invisible(snap)
}

unified_get_run_io_settings <- function(cfg) {
  io <- NULL
  if (is.list(cfg) && is.list(cfg$run)) io <- cfg$run$io
  if (is.null(io) || !is.list(io)) io <- list()

  enabled <- isTRUE(io$enabled)
  min_free_gb <- suppressWarnings(as.numeric(io$min_free_gb))
  min_free_inodes_pct <- suppressWarnings(as.numeric(io$min_free_inodes_pct))

  list(
    enabled = enabled,
    min_free_bytes = if (is.finite(min_free_gb) && min_free_gb > 0) min_free_gb * 1024^3 else 0,
    min_free_inodes_pct = if (is.finite(min_free_inodes_pct) && min_free_inodes_pct > 0) min_free_inodes_pct else NA_real_
  )
}

unified_safe_save <- function(save_fun, final_path, tmp_suffix = ".tmp", context = "") {
  if (!is.function(save_fun)) {
    stop("save_fun must be a function(path)", call. = FALSE)
  }
  final_path <- normalizePath(final_path, mustWork = FALSE)
  final_dir <- dirname(final_path)
  dir.create(final_dir, recursive = TRUE, showWarnings = FALSE)

  tmp_path <- sprintf("%s%s.%d", final_path, tmp_suffix, Sys.getpid())
  if (file.exists(tmp_path)) unlink(tmp_path, force = TRUE)

  result <- tryCatch(
    {
      save_fun(tmp_path)
      TRUE
    },
    error = function(e) e
  )

  if (inherits(result, "error")) {
    unlink(tmp_path, force = TRUE)
    storage_msg <- tryCatch(
      {
        snap <- unified_storage_snapshot(final_dir)
        sprintf("mount=%s free_gb=%.2f used_pct=%.2f free_inodes_pct=%s",
                snap$mountpoint, snap$free_gb, snap$used_pct,
                if (is.finite(snap$free_inodes_pct)) sprintf("%.2f", snap$free_inodes_pct) else "NA")
      },
      error = function(e) "storage snapshot unavailable"
    )
    stop(
      sprintf(
        "safe save failed%s: %s | target=%s | %s",
        if (nzchar(context)) sprintf(" (%s)", context) else "",
        conditionMessage(result),
        final_path,
        storage_msg
      ),
      call. = FALSE
    )
  }

  tmp_size <- suppressWarnings(file.info(tmp_path)$size)
  if (!file.exists(tmp_path) || !is.finite(tmp_size) || tmp_size <= 0) {
    unlink(tmp_path, force = TRUE)
    stop(
      sprintf(
        "safe save produced missing/empty temp file%s: %s",
        if (nzchar(context)) sprintf(" (%s)", context) else "",
        tmp_path
      ),
      call. = FALSE
    )
  }

  if (file.exists(final_path)) unlink(final_path, force = TRUE)
  moved <- isTRUE(file.rename(tmp_path, final_path))
  if (!moved) {
    copied <- file.copy(tmp_path, final_path, overwrite = TRUE)
    unlink(tmp_path, force = TRUE)
    if (!isTRUE(copied)) {
      stop(
        sprintf(
          "safe save rename/copy failed%s: %s",
          if (nzchar(context)) sprintf(" (%s)", context) else "",
          final_path
        ),
        call. = FALSE
      )
    }
  }

  final_size <- suppressWarnings(file.info(final_path)$size)
  if (!file.exists(final_path) || !is.finite(final_size) || final_size <= 0) {
    stop(
      sprintf(
        "safe save produced missing/empty final file%s: %s",
        if (nzchar(context)) sprintf(" (%s)", context) else "",
        final_path
      ),
      call. = FALSE
    )
  }

  invisible(final_path)
}
