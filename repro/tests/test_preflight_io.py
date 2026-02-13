import subprocess
import unittest
from pathlib import Path


class PreflightIoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]

    def run_r(self, expr: str):
        return subprocess.run(
            ["Rscript", "-e", expr],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_require_free_space_success_zero_threshold(self):
        expr = (
            "source('R/unified/preflight.R'); "
            "unified_require_free_space(tempdir(), min_free_bytes = 0, context = 'ut-ok'); "
            "cat('OK\\n')"
        )
        proc = self.run_r(expr)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("OK", proc.stdout)

    def test_require_free_space_failure_message(self):
        expr = (
            "source('R/unified/preflight.R'); "
            "unified_require_free_space(tempdir(), min_free_bytes = 1e18, context = 'ut-fail')"
        )
        proc = self.run_r(expr)
        self.assertNotEqual(proc.returncode, 0)
        merged = f"{proc.stdout}\n{proc.stderr}"
        self.assertIn("ut-fail", merged)
        self.assertIn("mountpoint", merged)
        self.assertIn("free", merged)

    def test_unified_safe_save_writes_nonempty_file_and_no_tmp(self):
        expr = (
            "source('R/unified/preflight.R'); "
            "td <- tempdir(); "
            "target <- file.path(td, 'safe_save_ut.RData'); "
            "unified_safe_save(function(path){ obj <- 1:5; save(obj, file = path) }, target, context = 'safe-save-ut'); "
            "if (!file.exists(target) || is.na(file.info(target)$size) || file.info(target)$size <= 0) stop('missing target'); "
            "tmp_left <- list.files(td, pattern = 'safe_save_ut\\\\.RData\\\\.tmp\\\\.[0-9]+$', full.names = TRUE); "
            "if (length(tmp_left) > 0) stop('tmp files remain'); "
            "cat('OK\\n')"
        )
        proc = self.run_r(expr)
        self.assertEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")
        self.assertIn("OK", proc.stdout)

    def test_fit_start_only_continue_is_warning_not_error_above_critical_floor(self):
        expr = (
            "source('R/unified/preflight.R'); "
            "io <- list(enabled=TRUE, preflight_scope='fit_start_only', "
            "min_free_bytes=0, min_free_bytes_start=0, min_free_bytes_continue=1e18, "
            "min_free_inodes_pct=0, critical_free_bytes=1); "
            "td <- tempdir(); "
            "out <- tryCatch({"
            "  unified_run_io_preflight(td, io, check_point='continue', context='ut-fit-start-only', "
            "report_dir=td, stage_label='ut_fit_start_only', log_path=file.path(td,'preflight.log')); "
            "  cat('NO_WARN\\n');"
            "}, warning=function(w){cat('WARN\\n'); cat(conditionMessage(w), '\\n')}, error=function(e){cat('ERR\\n'); cat(conditionMessage(e), '\\n')}); "
            "cat('DONE\\n')"
        )
        proc = self.run_r(expr)
        self.assertEqual(proc.returncode, 0, msg=f"{proc.stdout}\n{proc.stderr}")
        self.assertIn("WARN", proc.stdout)
        self.assertNotIn("ERR", proc.stdout)
        self.assertIn("ut-fit-start-only", proc.stdout)

    def test_fit_start_and_continue_enforces_start_threshold(self):
        expr = (
            "source('R/unified/preflight.R'); "
            "io <- list(enabled=TRUE, preflight_scope='fit_start_and_continue', "
            "min_free_bytes=0, min_free_bytes_start=1e18, min_free_bytes_continue=0, "
            "min_free_inodes_pct=0, critical_free_bytes=5*1024^3); "
            "unified_run_io_preflight(tempdir(), io, check_point='fit_start', context='ut-fit-start', "
            "report_dir=tempdir(), stage_label='ut_fit_start', log_path=file.path(tempdir(),'preflight.log'))"
        )
        proc = self.run_r(expr)
        self.assertNotEqual(proc.returncode, 0)
        merged = f"{proc.stdout}\n{proc.stderr}"
        self.assertIn("ut-fit-start", merged)
        self.assertIn("Storage preflight fail", merged)


if __name__ == "__main__":
    unittest.main()
