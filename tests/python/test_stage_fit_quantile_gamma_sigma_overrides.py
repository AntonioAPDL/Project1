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
                    stabilization = list(
                      theta_sigma_lower = -5,
                      theta_sigma_upper = 6,
                      median_sigma_only_fallback_enabled = TRUE,
                      median_state_norm_max_ratio = 25,
                      median_state_hold_after_guard_iters = 0L,
                      median_state_blend_alpha = 1.0,
                      median_cov_blend_alpha = 1.0
                    ),
                    quantile_overrides = list(
                      q50 = list(
                        init = list(gamma = -0.25),
                        guard_refreeze_iters = 30L,
                        stabilization = list(
                          theta_sigma_upper = 4,
                          median_state_norm_abs_cap = 5e7,
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
            cat(sprintf('p50_state_hold=%s\n', p50$stabilization$median_state_hold_after_guard_iters))
            cat(sprintf('p50_state_blend=%s\n', p50$stabilization$median_state_blend_alpha))
            cat(sprintf('p50_cov_blend=%s\n', p50$stabilization$median_cov_blend_alpha))
            cat(sprintf('p80_theta_sigma_upper=%s\n', p80$stabilization$theta_sigma_upper))
            cat(sprintf('p80_state_ratio=%s\n', p80$stabilization$median_state_norm_max_ratio))
            cat(sprintf('p80_median_sigma_only=%s\n', p80$stabilization$median_sigma_only_fallback_enabled))
            cat(sprintf('p80_state_hold=%s\n', p80$stabilization$median_state_hold_after_guard_iters))
            cat(sprintf('p80_state_blend=%s\n', p80$stabilization$median_state_blend_alpha))
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
        self.assertEqual(out['p50_gamma'], '-0.25')
        self.assertEqual(out['p50_refreeze'], '30')
        self.assertEqual(out['p05_gamma'], '0.1')
        self.assertEqual(out['p80_gamma'], '0')
        self.assertEqual(out['p80_refreeze'], '20')
        self.assertEqual(out['p50_theta_sigma_upper'], '4')
        self.assertEqual(out['p50_state_abs_cap'], '5e+07')
        self.assertEqual(out['p50_state_hold'], '12')
        self.assertEqual(out['p50_state_blend'], '0.5')
        self.assertEqual(out['p50_cov_blend'], '0.25')
        self.assertEqual(out['p80_theta_sigma_upper'], '6')
        self.assertEqual(out['p80_state_ratio'], '25')
        self.assertEqual(out['p80_median_sigma_only'], 'TRUE')
        self.assertEqual(out['p80_state_hold'], '0')
        self.assertEqual(out['p80_state_blend'], '1')


if __name__ == '__main__':
    unittest.main()
