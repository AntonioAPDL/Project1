from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path('/data/muscat_data/jaguir26/project1_ucsc_phd')


class StageFitQuantileGammaSigmaOverrideTests(unittest.TestCase):
    def test_quantile_specific_override_is_resolved(self) -> None:
        script = textwrap.dedent(
            f'''
            source("{(REPO_ROOT / 'R' / 'unified' / 'config.R').as_posix()}")
            source("{(REPO_ROOT / 'R' / 'unified' / 'stages' / 'stage_fit.R').as_posix()}")
            cfg <- list(
              fit = list(
                exdqlm_multivar = list(
                  gamma_sigma = list(
                    warmup_freeze_iters = 15L,
                    guard_refreeze_iters = 20L,
                    init = list(gamma = 0.0, sigma_floor = 0.01, sigma_scale = 0.5),
                    near_zero_fallback = list(
                      enabled = TRUE,
                      mode = "sigma_only",
                      gamma_anchor = "full_candidate"
                    ),
                    stabilization = list(
                      theta_sigma_lower = -5,
                      theta_sigma_upper = 6,
                      median_sigma_only_fallback_enabled = TRUE,
                      state_guard_step_backoff_enabled = TRUE,
                      state_guard_step_backoff_factor = 0.25,
                      state_guard_min_step_scale = 0.05,
                      state_hold_freeze_latents_enabled = TRUE,
                      state_guard_hold_step_scale_enabled = TRUE,
                      state_guard_min_refreeze_iters = 1L,
                      state_guard_min_hold_iters = 1L,
                      median_state_guard_sigma_only_enabled = TRUE,
                      median_state_guard_sigma_only_after = 1L,
                      median_state_guard_sigma_only_anchor = "zero",
                      median_state_norm_max_ratio = 25,
                      state_norm_abs_cap_scale = "per_time",
                      state_norm_ratio_ref_floor = 0.1,
                      median_state_hold_after_guard_iters = 0L,
                      median_state_blend_alpha = 1.0,
                      median_cov_blend_alpha = 1.0
                    ),
                    quantile_overrides = list(
                      q50 = list(
                        init = list(gamma = -0.25),
                        guard_refreeze_iters = 30L,
                        near_zero_fallback = list(
                          gamma_anchor = "zero"
                        ),
                        stabilization = list(
                          theta_sigma_upper = 4,
                          state_guard_step_backoff_factor = 0.2,
                          state_guard_min_step_scale = 0.025,
                          state_hold_freeze_latents_enabled = FALSE,
                          state_guard_hold_step_scale_enabled = FALSE,
                          state_guard_min_refreeze_iters = 3L,
                          state_guard_min_hold_iters = 4L,
                          median_state_guard_sigma_only_enabled = FALSE,
                          median_state_guard_sigma_only_after = 2L,
                          median_state_guard_sigma_only_anchor = "previous",
                          median_state_norm_abs_cap = 5e7,
                          state_norm_abs_cap_scale = "total",
                          state_norm_ratio_ref_floor = 0.2,
                          median_state_hold_after_guard_iters = 12L,
                          median_state_blend_alpha = 0.5,
                          median_cov_blend_alpha = 0.25
                        )
                      ),
                      `0.05` = list(init = list(gamma = 0.1))
                    )
                  )
                )
              )
            )
            p50 <- unified_resolve_gamma_sigma_policy(cfg, 'exdqlm_multivar', q = 0.50)
            p05 <- unified_resolve_gamma_sigma_policy(cfg, 'exdqlm_multivar', q = 0.05)
            p80 <- unified_resolve_gamma_sigma_policy(cfg, 'exdqlm_multivar', q = 0.80)
            cat(sprintf('p50_gamma=%s\n', p50$init$gamma))
            cat(sprintf('p50_refreeze=%s\n', p50$guard_refreeze_iters))
            cat(sprintf('p05_gamma=%s\n', p05$init$gamma))
            cat(sprintf('p80_gamma=%s\n', p80$init$gamma))
            cat(sprintf('p80_refreeze=%s\n', p80$guard_refreeze_iters))
            cat(sprintf('p50_theta_sigma_upper=%s\n', p50$stabilization$theta_sigma_upper))
            cat(sprintf('p50_state_abs_cap=%s\n', p50$stabilization$median_state_norm_abs_cap))
            cat(sprintf('p50_state_abs_cap_scale=%s\n', p50$stabilization$state_norm_abs_cap_scale))
            cat(sprintf('p50_state_ratio_ref_floor=%s\n', p50$stabilization$state_norm_ratio_ref_floor))
            cat(sprintf('p50_state_hold=%s\n', p50$stabilization$median_state_hold_after_guard_iters))
            cat(sprintf('p50_state_blend=%s\n', p50$stabilization$median_state_blend_alpha))
            cat(sprintf('p50_cov_blend=%s\n', p50$stabilization$median_cov_blend_alpha))
            cat(sprintf('p50_step_backoff=%s\n', p50$stabilization$state_guard_step_backoff_factor))
            cat(sprintf('p50_min_step_scale=%s\n', p50$stabilization$state_guard_min_step_scale))
            cat(sprintf('p50_freeze_latents=%s\n', p50$stabilization$state_hold_freeze_latents_enabled))
            cat(sprintf('p50_hold_step_scale_enabled=%s\n', p50$stabilization$state_guard_hold_step_scale_enabled))
            cat(sprintf('p50_min_refreeze=%s\n', p50$stabilization$state_guard_min_refreeze_iters))
            cat(sprintf('p50_min_hold=%s\n', p50$stabilization$state_guard_min_hold_iters))
            cat(sprintf('p50_state_guard_sigma_only=%s\n', p50$stabilization$median_state_guard_sigma_only_enabled))
            cat(sprintf('p50_state_guard_sigma_only_after=%s\n', p50$stabilization$median_state_guard_sigma_only_after))
            cat(sprintf('p50_state_guard_sigma_only_anchor=%s\n', p50$stabilization$median_state_guard_sigma_only_anchor))
            cat(sprintf('p50_near_zero_anchor=%s\n', p50$near_zero_fallback$gamma_anchor))
            cat(sprintf('p80_theta_sigma_upper=%s\n', p80$stabilization$theta_sigma_upper))
            cat(sprintf('p80_step_backoff_enabled=%s\n', p80$stabilization$state_guard_step_backoff_enabled))
            cat(sprintf('p80_step_backoff=%s\n', p80$stabilization$state_guard_step_backoff_factor))
            cat(sprintf('p80_min_step_scale=%s\n', p80$stabilization$state_guard_min_step_scale))
            cat(sprintf('p80_freeze_latents=%s\n', p80$stabilization$state_hold_freeze_latents_enabled))
            cat(sprintf('p80_hold_step_scale_enabled=%s\n', p80$stabilization$state_guard_hold_step_scale_enabled))
            cat(sprintf('p80_min_refreeze=%s\n', p80$stabilization$state_guard_min_refreeze_iters))
            cat(sprintf('p80_min_hold=%s\n', p80$stabilization$state_guard_min_hold_iters))
            cat(sprintf('p80_state_guard_sigma_only=%s\n', p80$stabilization$median_state_guard_sigma_only_enabled))
            cat(sprintf('p80_state_guard_sigma_only_after=%s\n', p80$stabilization$median_state_guard_sigma_only_after))
            cat(sprintf('p80_state_guard_sigma_only_anchor=%s\n', p80$stabilization$median_state_guard_sigma_only_anchor))
            cat(sprintf('p80_state_ratio=%s\n', p80$stabilization$median_state_norm_max_ratio))
            cat(sprintf('p80_state_abs_cap_scale=%s\n', p80$stabilization$state_norm_abs_cap_scale))
            cat(sprintf('p80_state_ratio_ref_floor=%s\n', p80$stabilization$state_norm_ratio_ref_floor))
            cat(sprintf('p80_median_sigma_only=%s\n', p80$stabilization$median_sigma_only_fallback_enabled))
            cat(sprintf('p80_state_hold=%s\n', p80$stabilization$median_state_hold_after_guard_iters))
            cat(sprintf('p80_state_blend=%s\n', p80$stabilization$median_state_blend_alpha))
            cat(sprintf('p80_near_zero_anchor=%s\n', p80$near_zero_fallback$gamma_anchor))
            '''
        )
        with tempfile.NamedTemporaryFile('w', suffix='.R', delete=False) as handle:
            handle.write(script)
            script_path = Path(handle.name)
        try:
            proc = subprocess.run(
                ['Rscript', '--vanilla', script_path.as_posix()],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            script_path.unlink(missing_ok=True)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + '\n' + proc.stderr)
        out = {}
        for line in proc.stdout.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                out[k.strip()] = v.strip()
        self.assertEqual(out['p50_gamma'], '-0.25')
        self.assertEqual(out['p50_refreeze'], '30')
        self.assertEqual(out['p05_gamma'], '0.1')
        self.assertEqual(out['p80_gamma'], '0')
        self.assertEqual(out['p80_refreeze'], '20')
        self.assertEqual(out['p50_theta_sigma_upper'], '4')
        self.assertEqual(out['p50_state_abs_cap'], '5e+07')
        self.assertEqual(out['p50_state_abs_cap_scale'], 'total')
        self.assertEqual(out['p50_state_ratio_ref_floor'], '0.2')
        self.assertEqual(out['p50_state_hold'], '12')
        self.assertEqual(out['p50_state_blend'], '0.5')
        self.assertEqual(out['p50_cov_blend'], '0.25')
        self.assertEqual(out['p50_step_backoff'], '0.2')
        self.assertEqual(out['p50_min_step_scale'], '0.025')
        self.assertEqual(out['p50_freeze_latents'], 'FALSE')
        self.assertEqual(out['p50_hold_step_scale_enabled'], 'FALSE')
        self.assertEqual(out['p50_min_refreeze'], '3')
        self.assertEqual(out['p50_min_hold'], '4')
        self.assertEqual(out['p50_state_guard_sigma_only'], 'FALSE')
        self.assertEqual(out['p50_state_guard_sigma_only_after'], '2')
        self.assertEqual(out['p50_state_guard_sigma_only_anchor'], 'previous')
        self.assertEqual(out['p50_near_zero_anchor'], 'zero')
        self.assertEqual(out['p80_theta_sigma_upper'], '6')
        self.assertEqual(out['p80_step_backoff_enabled'], 'TRUE')
        self.assertEqual(out['p80_step_backoff'], '0.25')
        self.assertEqual(out['p80_min_step_scale'], '0.05')
        self.assertEqual(out['p80_freeze_latents'], 'TRUE')
        self.assertEqual(out['p80_hold_step_scale_enabled'], 'TRUE')
        self.assertEqual(out['p80_min_refreeze'], '1')
        self.assertEqual(out['p80_min_hold'], '1')
        self.assertEqual(out['p80_state_guard_sigma_only'], 'TRUE')
        self.assertEqual(out['p80_state_guard_sigma_only_after'], '1')
        self.assertEqual(out['p80_state_guard_sigma_only_anchor'], 'zero')
        self.assertEqual(out['p80_state_ratio'], '25')
        self.assertEqual(out['p80_state_abs_cap_scale'], 'per_time')
        self.assertEqual(out['p80_state_ratio_ref_floor'], '0.1')
        self.assertEqual(out['p80_median_sigma_only'], 'TRUE')
        self.assertEqual(out['p80_state_hold'], '0')
        self.assertEqual(out['p80_state_blend'], '1')
        self.assertEqual(out['p80_near_zero_anchor'], 'full_candidate')

    def test_nonmedian_generic_state_controls_survive_quantile_override_resolution(self) -> None:
        script = textwrap.dedent(
            f'''
            source("{(REPO_ROOT / 'R' / 'unified' / 'config.R').as_posix()}")
            source("{(REPO_ROOT / 'R' / 'unified' / 'stages' / 'stage_fit.R').as_posix()}")
            cfg <- list(
              fit = list(
                exdqlm_multivar = list(
                  gamma_sigma = list(
                    stabilization = list(
                      state_guard_enabled = FALSE,
                      state_norm_max_ratio = 10,
                      state_norm_abs_cap = 1e11,
                      state_norm_abs_cap_scale = "total",
                      state_norm_ratio_ref_floor = 0.05,
                      state_guard_refreeze_iters = 7L,
                      state_hold_after_guard_iters = 0L,
                      state_blend_alpha = 1.0,
                      cov_blend_alpha = 1.0
                    ),
                    quantile_overrides = list(
                      q35 = list(
                        stabilization = list(
                          state_guard_enabled = TRUE,
                          state_norm_max_ratio = 25,
                          state_norm_abs_cap = 1e12,
                          state_norm_abs_cap_scale = "per_time",
                          state_norm_ratio_ref_floor = 0.1,
                          state_guard_refreeze_iters = 10L,
                          state_hold_after_guard_iters = 10L,
                          state_blend_alpha = 0.85,
                          cov_blend_alpha = 1.0
                        )
                      )
                    )
                  )
                )
              )
            )
            p35 <- unified_resolve_gamma_sigma_policy(cfg, 'exdqlm_multivar', q = 0.35)
            p80 <- unified_resolve_gamma_sigma_policy(cfg, 'exdqlm_multivar', q = 0.80)
            cat(sprintf('p35_state_guard=%s\\n', p35$stabilization$state_guard_enabled))
            cat(sprintf('p35_state_ratio=%s\\n', p35$stabilization$state_norm_max_ratio))
            cat(sprintf('p35_state_abs_cap=%s\\n', p35$stabilization$state_norm_abs_cap))
            cat(sprintf('p35_state_abs_cap_scale=%s\\n', p35$stabilization$state_norm_abs_cap_scale))
            cat(sprintf('p35_state_ratio_ref_floor=%s\\n', p35$stabilization$state_norm_ratio_ref_floor))
            cat(sprintf('p35_state_refreeze=%s\\n', p35$stabilization$state_guard_refreeze_iters))
            cat(sprintf('p35_state_hold=%s\\n', p35$stabilization$state_hold_after_guard_iters))
            cat(sprintf('p35_state_blend=%s\\n', p35$stabilization$state_blend_alpha))
            cat(sprintf('p80_state_guard=%s\\n', p80$stabilization$state_guard_enabled))
            cat(sprintf('p80_state_ratio=%s\\n', p80$stabilization$state_norm_max_ratio))
            cat(sprintf('p80_state_abs_cap_scale=%s\\n', p80$stabilization$state_norm_abs_cap_scale))
            cat(sprintf('p80_state_ratio_ref_floor=%s\\n', p80$stabilization$state_norm_ratio_ref_floor))
            '''
        )
        proc = subprocess.run(
            ['Rscript', '--vanilla', '-e', script],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + '\n' + proc.stderr)
        out = {}
        for line in proc.stdout.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                out[k.strip()] = v.strip()
        self.assertEqual(out['p35_state_guard'], 'TRUE')
        self.assertEqual(out['p35_state_ratio'], '25')
        self.assertEqual(out['p35_state_abs_cap'], '1e+12')
        self.assertEqual(out['p35_state_abs_cap_scale'], 'per_time')
        self.assertEqual(out['p35_state_ratio_ref_floor'], '0.1')
        self.assertEqual(out['p35_state_refreeze'], '10')
        self.assertEqual(out['p35_state_hold'], '10')
        self.assertEqual(out['p35_state_blend'], '0.85')
        self.assertEqual(out['p80_state_guard'], 'FALSE')
        self.assertEqual(out['p80_state_ratio'], '10')
        self.assertEqual(out['p80_state_abs_cap_scale'], 'total')
        self.assertEqual(out['p80_state_ratio_ref_floor'], '0.05')

    def test_sampling_diagnostics_and_terminal_guard_validate_and_resolve(self) -> None:
        script = textwrap.dedent(
            f'''
            source("{(REPO_ROOT / 'R' / 'unified' / 'config.R').as_posix()}")
            source("{(REPO_ROOT / 'R' / 'unified' / 'stages' / 'stage_fit.R').as_posix()}")
            tmp_root <- file.path(tempdir(), "sampling_diag_cfg")
            dir.create(tmp_root, recursive = TRUE, showWarnings = FALSE)
            parameters_path <- file.path(tmp_root, "dummy_parameters.csv")
            retros_path <- file.path(tmp_root, "dummy_retros.csv")
            nws_path <- file.path(tmp_root, "dummy_nws.csv")
            glofas_path <- file.path(tmp_root, "dummy_glofas.csv")
            bundle_path <- file.path(tmp_root, "dummy_bundle")
            file.create(parameters_path, retros_path, nws_path, glofas_path)
            dir.create(bundle_path, recursive = TRUE, showWarnings = FALSE)
            cfg <- unified_deep_merge(
              unified_config_defaults(),
              list(
                inputs = list(
                  fit = list(
                    parameters_path = parameters_path,
                    retros_path = retros_path,
                    nws_forecast_path = nws_path,
                    glofas_forecast_path = glofas_path
                  ),
                  forecats = list(
                    existing_bundle_path = bundle_path
                  )
                ),
                fit = list(
                  exdqlm_multivar = list(
                    legacy = list(
                      sampling_diagnostics = list(
                        heartbeat_enabled = TRUE,
                        heartbeat_seconds = 30L,
                        phase_markers_enabled = TRUE,
                        walltime_seconds = 900L
                      )
                    ),
                    gamma_sigma = list(
                      terminal_sampling_guard = list(
                        mode = "fail_fast",
                        min_guard_count = 2L,
                        max_guard_lag_iters = 1L,
                        require_frozen = TRUE
                      ),
                      quantile_overrides = list(
                        q50 = list(
                          terminal_sampling_guard = list(
                            min_guard_count = 3L
                          )
                        )
                      )
                    )
                  )
                )
              )
            )
            errs <- unified_validate_config(cfg)
            p50 <- unified_resolve_gamma_sigma_policy(cfg, 'exdqlm_multivar', q = 0.50)
            p80 <- unified_resolve_gamma_sigma_policy(cfg, 'exdqlm_multivar', q = 0.80)
            cat(sprintf('err_count=%s\\n', length(errs)))
            cat(sprintf('diag_heartbeat=%s\\n', cfg$fit$exdqlm_multivar$legacy$sampling_diagnostics$heartbeat_enabled))
            cat(sprintf('diag_walltime=%s\\n', cfg$fit$exdqlm_multivar$legacy$sampling_diagnostics$walltime_seconds))
            cat(sprintf('p50_guard_mode=%s\\n', p50$terminal_sampling_guard$mode))
            cat(sprintf('p50_guard_min=%s\\n', p50$terminal_sampling_guard$min_guard_count))
            cat(sprintf('p80_guard_min=%s\\n', p80$terminal_sampling_guard$min_guard_count))
            cat(sprintf('p80_guard_require_frozen=%s\\n', p80$terminal_sampling_guard$require_frozen))
            '''
        )
        proc = subprocess.run(
            ['Rscript', '--vanilla', '-e', script],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + '\n' + proc.stderr)
        out = {}
        for line in proc.stdout.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                out[k.strip()] = v.strip()
        self.assertEqual(out['err_count'], '0')
        self.assertEqual(out['diag_heartbeat'], 'TRUE')
        self.assertEqual(out['diag_walltime'], '900')
        self.assertEqual(out['p50_guard_mode'], 'fail_fast')
        self.assertEqual(out['p50_guard_min'], '3')
        self.assertEqual(out['p80_guard_min'], '2')
        self.assertEqual(out['p80_guard_require_frozen'], 'TRUE')


if __name__ == '__main__':
    unittest.main()
