from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")


class StageFitParallelGuardTests(unittest.TestCase):
    def _run_r(self, expr: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["Rscript", "-e", expr],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_invalid_parallel_result_has_actionable_error(self) -> None:
        expr = (
            "source('R/unified/stages/stage_fit.R');"
            "tryCatch({"
            "  unified_normalize_fit_worker_result('worker boom', 'fit stage parallel worker');"
            "  cat('NO_ERROR\\n');"
            "}, error=function(e){"
            "  cat(conditionMessage(e), '\\n');"
            "  quit(status=0);"
            "});"
            "quit(status=1)"
        )
        result = self._run_r(expr)
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("fit stage parallel worker returned invalid result", result.stdout)
        self.assertIn("worker boom", result.stdout)

    def test_valid_parallel_result_passes_through(self) -> None:
        expr = (
            "source('R/unified/stages/stage_fit.R');"
            "x <- unified_normalize_fit_worker_result("
            "  list(quantile=0.5, output_path='out.RData', log_path='fit.log', status=0L)"
            ");"
            "cat(sprintf('q=%s status=%s\\n', x$quantile, x$status));"
            "quit(status=0)"
        )
        result = self._run_r(expr)
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("q=0.5 status=0", result.stdout)

    def test_fit_parallel_mode_unknown_falls_back(self) -> None:
        expr = (
            "source('R/unified/config.R');"
            "source('R/unified/stages/stage_fit.R');"
            "cfg <- list(fit=list(parallel=list(mode='bad_mode')));"
            "m <- unified_resolve_fit_parallel_mode(cfg);"
            "cat(sprintf('mode=%s\\n', m));"
            "quit(status=0)"
        )
        result = self._run_r(expr)
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("mode=by_family", result.stdout)

    def test_fit_parallel_workers_caps_to_job_count(self) -> None:
        expr = (
            "source('R/unified/config.R');"
            "source('R/unified/stages/stage_fit.R');"
            "cfg <- list(fit=list(parallel=list(workers=20)));"
            "w <- unified_resolve_fit_parallel_workers(cfg, n_jobs=15L, default_workers=3L);"
            "cat(sprintf('workers=%s\\n', w));"
            "quit(status=0)"
        )
        result = self._run_r(expr)
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("workers=15", result.stdout)


if __name__ == "__main__":
    unittest.main()
