source(testthat::test_path("..", "..", "R", "unified", "utils_hash.R"))
source(testthat::test_path("..", "..", "R", "unified", "utils_env_capture.R"))

write_env_file <- function(dir_path, name, lines) {
  path <- file.path(dir_path, name)
  writeLines(lines, con = path, useBytes = TRUE)
  path
}

test_that("LD_LIBRARY_PATH normalization removes duplicate entries", {
  raw <- "/a:/b:/a:/c::/b:/c:"
  expect_equal(unified_normalize_ld_library_path(raw), "/a:/b:/c")
})

test_that("env drift passes when renviron differs only by LD_LIBRARY_PATH duplicates", {
  current_dir <- tempfile("env_current_")
  canonical_dir <- tempfile("env_canonical_")
  dir.create(current_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(canonical_dir, recursive = TRUE, showWarnings = FALSE)

  common_r <- c("captured_at_utc=2026-03-03T00:00:00Z", "R version 4.4.0")
  common_pkgs <- c("Package,Version,LibPath,Built", "foo,1.0,/tmp,4.4.0")
  common_pip <- c("numpy==1.0")
  common_threads <- c(
    "captured_at_utc=2026-03-03T00:00:00Z",
    "OMP_NUM_THREADS=1",
    "OPENBLAS_NUM_THREADS=1",
    "MKL_NUM_THREADS=1",
    "VECLIB_MAXIMUM_THREADS=1",
    "NUMEXPR_NUM_THREADS=1"
  )

  write_env_file(current_dir, "R_sessionInfo.txt", common_r)
  write_env_file(canonical_dir, "R_sessionInfo.txt", common_r)
  write_env_file(current_dir, "R_installed_packages.csv", common_pkgs)
  write_env_file(canonical_dir, "R_installed_packages.csv", common_pkgs)
  write_env_file(current_dir, "python_pip_freeze.txt", common_pip)
  write_env_file(canonical_dir, "python_pip_freeze.txt", common_pip)
  write_env_file(current_dir, "threads_snapshot.txt", common_threads)
  write_env_file(canonical_dir, "threads_snapshot.txt", common_threads)

  write_env_file(
    current_dir,
    "renviron_snapshot.txt",
    c(
      "captured_at_utc=2026-03-03T00:00:00Z",
      "PKG_CXXFLAGS=",
      "PKG_LIBS=",
      "LD_LIBRARY_PATH=/a:/b:/a:/c::/b",
      "DISC_BASE_SEED=777"
    )
  )
  write_env_file(
    canonical_dir,
    "renviron_snapshot.txt",
    c(
      "captured_at_utc=2026-03-03T00:00:00Z",
      "PKG_CXXFLAGS=",
      "PKG_LIBS=",
      "LD_LIBRARY_PATH=/a:/b:/c",
      "DISC_BASE_SEED=777"
    )
  )

  report <- unified_env_drift_report(current_dir, canonical_dir, out_json_path = NULL)
  expect_identical(report$status, "pass")
  expect_length(report$mismatched_files, 0L)
  expect_length(report$missing_files, 0L)
})
