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


if __name__ == "__main__":
    unittest.main()
