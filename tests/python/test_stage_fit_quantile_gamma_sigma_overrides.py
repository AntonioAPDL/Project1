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
                    quantile_overrides = list(
                      q50 = list(init = list(gamma = -0.25), guard_refreeze_iters = 30L),
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


if __name__ == '__main__':
    unittest.main()
