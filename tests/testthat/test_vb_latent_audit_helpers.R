test_that("VB latent audit parses HE3 specs and aggregates missing groups", {
  old_flag <- Sys.getenv("EXDQLM_VB_LATENT_AUDIT_NO_MAIN", unset = NA_character_)
  Sys.setenv(EXDQLM_VB_LATENT_AUDIT_NO_MAIN = "TRUE")
  on.exit({
    if (is.na(old_flag)) {
      Sys.unsetenv("EXDQLM_VB_LATENT_AUDIT_NO_MAIN")
    } else {
      Sys.setenv(EXDQLM_VB_LATENT_AUDIT_NO_MAIN = old_flag)
    }
  }, add = TRUE)

  script_candidates <- c(
    file.path("scripts", "audit_exdqlm_multivar_keep_vb_latents.R"),
    file.path("..", "..", "scripts", "audit_exdqlm_multivar_keep_vb_latents.R")
  )
  script_path <- script_candidates[file.exists(script_candidates)][[1L]]
  source(script_path)

  he3_run <- "multimodel_20220511_v8_c02_eps060_exdqlm_multivar_keep_he3_noH1"
  legacy_grid_run <- "multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep"

  expect_equal(spec_from_run_id(he3_run), "c02_eps060")
  expect_equal(spec_from_run_id(legacy_grid_run), "c05_eps030")

  df <- data.frame(
    run_id = he3_run,
    cutoff = "20220511",
    cutoff_date = "2022-05-11",
    spec = NA_character_,
    q = 5L,
    block = "forecast",
    source = "GloFAS",
    day_rel = c(1L, 2L),
    quantity = "E_inv_u",
    value = c(2, 4),
    stringsAsFactors = FALSE
  )

  out <- aggregate_quantity_long(df)
  expect_equal(nrow(out), 2L)
  expect_true("E_inv_u" %in% names(out))
  expect_true(all(out$spec == "__missing__"))
  expect_equal(out$E_inv_u[order(out$day_rel)], c(2, 4))
})
