import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class KalmanCppCompileSmokeTests(unittest.TestCase):
    def run_r(self, expr: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["Rscript", "--vanilla", "-e", expr],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_disc_kalman_cpp_compile_smoke(self) -> None:
        expr = (
            f"Rcpp::sourceCpp('{(REPO_ROOT / 'DISC_kalman_synth.cpp').as_posix()}');"
            f"Rcpp::sourceCpp('{(REPO_ROOT / 'DISC_kalman_synth_NDLM.cpp').as_posix()}');"
            "stopifnot(exists('DISC_update_theta_synth_cpp_W', mode='function'));"
            "stopifnot(exists('update_theta_synth_cpp_ndlm', mode='function'));"
        )
        res = self.run_r(expr)
        self.assertEqual(
            res.returncode,
            0,
            msg=f'R compile smoke failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}',
        )

    def test_ndlm_unified_cpp_backend_compile_smoke(self) -> None:
        expr = (
            f"Rcpp::sourceCpp('{(REPO_ROOT / 'R' / 'unified' / 'families' / 'ndlm_main' / 'ndlm_kalman_backend.cpp').as_posix()}');"
            "stopifnot(exists('ndlm_kalman_smoother_cpp', mode='function'));"
        )
        res = self.run_r(expr)
        self.assertEqual(
            res.returncode,
            0,
            msg=f'NDLM backend compile smoke failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}',
        )


if __name__ == "__main__":
    unittest.main()

