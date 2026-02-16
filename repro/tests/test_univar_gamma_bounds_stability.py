from __future__ import annotations

import math
import subprocess
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")


class UnivarGammaBoundsStabilityTests(unittest.TestCase):
    def _run_r(self, script: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["Rscript", "--vanilla", "-e", script],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_gamma_bounds_extreme_tails_are_finite(self) -> None:
        script = textwrap.dedent(
            f"""
            source("{(REPO_ROOT / "R" / "unified" / "families" / "exdqlm_univar" / "02_model_spec.R").as_posix()}")
            p0_vals <- c(0.005, 0.01, 0.02, 0.98, 0.99, 0.995)
            for (p0 in p0_vals) {{
              b <- univar_theory_gamma_bounds(p0)
              cat(sprintf("p0=%.3f L=%.12f U=%.12f\\n", p0, b[["L"]], b[["U"]]))
            }}
            """
        ).strip()
        proc = self._run_r(script)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        seen = 0
        for line in proc.stdout.splitlines():
            if not line.startswith("p0="):
                continue
            seen += 1
            toks = dict(tok.split("=", 1) for tok in line.split())
            l_val = float(toks["L"])
            u_val = float(toks["U"])
            self.assertTrue(math.isfinite(l_val), msg=line)
            self.assertTrue(math.isfinite(u_val), msg=line)
            self.assertLess(l_val, u_val, msg=line)

        self.assertEqual(seen, 6, msg=proc.stdout)

    def test_exal_g_is_finite_for_large_gamma(self) -> None:
        script = textwrap.dedent(
            f"""
            source("{(REPO_ROOT / "R" / "unified" / "families" / "exdqlm_univar" / "02_model_spec.R").as_posix()}")
            xs <- c(40, 60, 80, 100, 160)
            vals <- univar_theory_exal_g(xs)
            for (i in seq_along(xs)) {{
              cat(sprintf("x=%d g=%.12f finite=%s\\n", xs[[i]], vals[[i]], ifelse(is.finite(vals[[i]]), "TRUE", "FALSE")))
            }}
            """
        ).strip()
        proc = self._run_r(script)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        seen = 0
        for line in proc.stdout.splitlines():
            if not line.startswith("x="):
                continue
            seen += 1
            toks = dict(tok.split("=", 1) for tok in line.split())
            g_val = float(toks["g"])
            finite = toks["finite"] == "TRUE"
            self.assertTrue(finite, msg=line)
            self.assertTrue(math.isfinite(g_val), msg=line)
            self.assertGreater(g_val, 0.0, msg=line)

        self.assertEqual(seen, 5, msg=proc.stdout)


if __name__ == "__main__":
    unittest.main()
