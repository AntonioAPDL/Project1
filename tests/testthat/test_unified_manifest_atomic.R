source(testthat::test_path("..", "..", "R", "unified", "manifest.R"))

test_that("unified_manifest_write replaces an existing manifest atomically", {
  tmp <- tempfile("manifest_atomic_")
  dir.create(tmp)
  on.exit(unlink(tmp, recursive = TRUE, force = TRUE), add = TRUE)

  out <- file.path(tmp, "run_manifest.yaml")
  writeLines("[]", out, useBytes = TRUE)

  unified_manifest_write(list(manifest_version = 1L, stages = list(report = list(status = "pass"))), out)

  loaded <- yaml::read_yaml(out)
  expect_true(is.list(loaded))
  expect_equal(loaded$manifest_version, 1L)
  expect_equal(loaded$stages$report$status, "pass")
  expect_length(list.files(tmp, pattern = "^\\.run_manifest\\.yaml\\.", all.files = TRUE), 0L)
})
