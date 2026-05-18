from __future__ import annotations

import os
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SamplingTruncnormTailGuardTests(unittest.TestCase):
    def test_extreme_left_tail_draws_are_finite_and_reproducible(self) -> None:
        script = textwrap.dedent(
            f"""
            suppressWarnings(suppressMessages({{
              library(Rcpp)
            }}))
            Sys.setenv(
              PKG_CXXFLAGS = "-I/data/muscat_data/jaguir26/libs/eigen -I/data/muscat_data/jaguir26/libs/boost/include -DEIGEN_DONT_VECTORIZE",
              PKG_LIBS = "-L/data/muscat_data/jaguir26/libs/lib64 -L/data/muscat_data/jaguir26/libs/boost/lib -llapack -lblas -lboost_random -lboost_system -fopenmp",
              LD_LIBRARY_PATH = "/data/muscat_data/jaguir26/libs/lib64:/data/muscat_data/jaguir26/libs/boost/lib:/lib64",
              OMP_NUM_THREADS = "1",
              OPENBLAS_NUM_THREADS = "1",
              MKL_NUM_THREADS = "1",
              VECLIB_MAXIMUM_THREADS = "1",
              NUMEXPR_NUM_THREADS = "1"
            )
            Rcpp::sourceCpp("{(ROOT / 'sampling_truncnorm.cpp').as_posix()}")

            mu <- c(-0.906216, -0.700000, -0.500000, 0.100000)
            sig2 <- c(0.0094224, 0.0100000, 0.0200000, 0.0500000)

            set_sampling_truncnorm_seed(4242)
            x1 <- sample_truncnorm_icdf(64L, length(mu), mu, sig2)
            set_sampling_truncnorm_seed(4242)
            x2 <- sample_truncnorm_icdf(64L, length(mu), mu, sig2)

            stopifnot(all(is.finite(x1)))
            stopifnot(all(x1 >= 0))
            stopifnot(identical(x1, x2))
            cat("ok\\n")
            """
        )

        env = os.environ.copy()
        proc = subprocess.run(
            ["Rscript", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(
                "Rscript truncnorm tail guard test failed\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )
        self.assertIn("ok", proc.stdout)


if __name__ == "__main__":
    unittest.main()
