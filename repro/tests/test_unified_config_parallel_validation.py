from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")


class UnifiedConfigParallelValidationTests(unittest.TestCase):
    def _run_r(self, expr: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["Rscript", "-e", expr],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_one_core_per_model_mode_is_valid(self) -> None:
        expr = (
            "source('R/unified/config.R');"
            "cfg <- unified_config_defaults();"
            "cfg$stages <- as.list(setNames(rep(FALSE, length(cfg$stages)), names(cfg$stages)));"
            "cfg$fit$parallel$mode <- 'one-core-per-model';"
            "errs <- unified_validate_config(cfg);"
            "cat(sprintf('n_err=%d\\n', length(errs)));"
            "quit(status=ifelse(length(errs)==0,0,1))"
        )
        result = self._run_r(expr)
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("n_err=0", result.stdout)

    def test_invalid_parallel_mode_is_rejected(self) -> None:
        expr = (
            "source('R/unified/config.R');"
            "cfg <- unified_config_defaults();"
            "cfg$stages <- as.list(setNames(rep(FALSE, length(cfg$stages)), names(cfg$stages)));"
            "cfg$fit$parallel$mode <- 'bad_mode';"
            "errs <- unified_validate_config(cfg);"
            "hit <- any(grepl('fit.parallel.mode', errs, fixed=TRUE));"
            "cat(sprintf('hit=%s\\n', ifelse(hit, 'yes', 'no')));"
            "quit(status=ifelse(hit,0,1))"
        )
        result = self._run_r(expr)
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("hit=yes", result.stdout)

    def test_invalid_parallel_workers_is_rejected(self) -> None:
        expr = (
            "source('R/unified/config.R');"
            "cfg <- unified_config_defaults();"
            "cfg$stages <- as.list(setNames(rep(FALSE, length(cfg$stages)), names(cfg$stages)));"
            "cfg$fit$parallel$workers <- 0;"
            "errs <- unified_validate_config(cfg);"
            "hit <- any(grepl('fit.parallel.workers', errs, fixed=TRUE));"
            "cat(sprintf('hit=%s\\n', ifelse(hit, 'yes', 'no')));"
            "quit(status=ifelse(hit,0,1))"
        )
        result = self._run_r(expr)
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("hit=yes", result.stdout)


if __name__ == "__main__":
    unittest.main()
