# unified/utils_write_audit.R

unified_write_audit_snapshot <- function(repo_root, run_root, out_path) {
  dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
  repo_root_abs <- normalizePath(repo_root, mustWork = TRUE)
  run_root_abs <- normalizePath(run_root, mustWork = FALSE)

  rel_from_repo <- function(path_abs) {
    rel <- sub(paste0("^", repo_root_abs, "/?"), "", path_abs)
    if (identical(rel, path_abs)) return(NULL)
    rel
  }

  run_rel <- rel_from_repo(run_root_abs)
  base_rel <- if (!is.null(run_rel)) dirname(run_rel) else NULL
  prune_rels <- unique(Filter(function(x) !is.null(x) && nzchar(x) && x != ".", c(run_rel, base_rel)))
  prune_expr <- if (length(prune_rels) > 0) {
    paste(vapply(prune_rels, function(p) sprintf("-path './%s' -prune -o", p), character(1)), collapse = " ")
  } else {
    ""
  }

  cmd <- paste(
    "cd", shQuote(repo_root_abs), "&&",
    "find .",
    "-path './.git' -prune -o",
    prune_expr,
    "-printf '%P\\t%s\\t%TY-%Tm-%TdT%TH:%TM:%TS\\n' | LC_ALL=C sort"
  )
  out <- system(cmd, intern = TRUE)
  writeLines(out, out_path, useBytes = TRUE)
  invisible(out_path)
}

unified_write_audit_diff <- function(before_path, after_path, diff_path) {
  dir.create(dirname(diff_path), recursive = TRUE, showWarnings = FALSE)
  cmd <- sprintf("diff -u %s %s > %s || true", shQuote(before_path), shQuote(after_path), shQuote(diff_path))
  system(cmd)
  invisible(diff_path)
}

unified_write_audit_is_clean <- function(diff_path) {
  !file.exists(diff_path) || file.info(diff_path)$size == 0
}

unified_write_audit_enforce <- function(diff_path, allowlist = character(0)) {
  if (unified_write_audit_is_clean(diff_path)) return(invisible(TRUE))
  if (length(allowlist) == 0) {
    stop(sprintf("Write-audit violation detected. Diff is not empty: %s", diff_path), call. = FALSE)
  }

  lines <- readLines(diff_path, warn = FALSE)
  changed <- lines[grepl("^[+-][^+-]", lines)]
  changed <- sub("^[+-]", "", changed)
  changed <- vapply(strsplit(changed, "\\t"), function(parts) trimws(parts[[1]]), character(1))
  changed <- changed[nzchar(changed)]

  matched <- vapply(changed, function(path) any(vapply(allowlist, function(pat) grepl(pat, path), logical(1))), logical(1))
  if (!all(matched)) {
    bad <- changed[!matched]
    stop(sprintf("Write-audit violation: paths outside allowlist detected (%s)", paste(unique(bad), collapse = ", ")), call. = FALSE)
  }

  invisible(TRUE)
}
