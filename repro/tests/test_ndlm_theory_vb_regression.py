from __future__ import annotations

import csv
import math
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")


def _write_csv(path: Path, header: str, values: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([header])
        for v in values:
            w.writerow([f"{v:.10f}"])


def _parse_kv(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


class NDLMTheoryVBRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ut_ndlm_vb_"))

    def tearDown(self) -> None:
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_theory_runner_emits_stochastic_w_and_elbo_artifacts(self) -> None:
        t = list(range(1, 101))
        retros = [1.25 + 0.015 * i + 0.20 * math.sin(i / 9.0) for i in t]
        nws = [1.10 + 0.03 * i + 0.12 * math.sin(i / 3.0) for i in range(1, 25)]
        glofas = [1.00 + 0.028 * i + 0.10 * math.cos(i / 4.0) for i in range(1, 25)]

        retros_csv = self.tmpdir / "retros.csv"
        nws_csv = self.tmpdir / "nws_forecast.csv"
        glofas_csv = self.tmpdir / "glofas_forecast.csv"
        _write_csv(retros_csv, "USGS", retros)
        _write_csv(nws_csv, "nws", nws)
        _write_csv(glofas_csv, "glofas", glofas)

        cov_paths: list[Path] = []
        for idx, base in enumerate([0.1, 0.2, 0.3, 0.4, 0.5], start=1):
            vals = [base + 0.0025 * i + 0.03 * math.sin(i / (6.0 + idx)) for i in t]
            p = self.tmpdir / f"cov{idx}.csv"
            _write_csv(p, f"cov{idx}", vals)
            cov_paths.append(p)

        out_rdata = self.tmpdir / "DISC_variables_50_NDLM_synth_DISC.RData"
        summary_log = self.tmpdir / "ndlm_theory_summary.log"

        env = os.environ.copy()
        env["NDLM_RETROS_CSV"] = str(retros_csv)
        env["NDLM_NWS_FORECAST_CSV"] = str(nws_csv)
        env["NDLM_GLOFAS_FORECAST_CSV"] = str(glofas_csv)
        env["NDLM_COV1_ELI_CSV"] = str(cov_paths[0])
        env["NDLM_COV2_ONI_CSV"] = str(cov_paths[1])
        env["NDLM_PPT_CSV"] = str(cov_paths[2])
        env["NDLM_SOIL_CSV"] = str(cov_paths[3])
        env["NDLM_PCA_CSV"] = str(cov_paths[4])
        env["UNIFIED_NDLM_RDATA_OUT"] = str(out_rdata)
        env["NDLM_THEORY_SUMMARY_LOG"] = str(summary_log)

        run = subprocess.run(
            ["Rscript", "--vanilla", "scripts/run_ndlm_main.R", "777"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(run.returncode, 0, msg=run.stdout + "\n" + run.stderr)
        self.assertTrue(out_rdata.exists(), "NDLM theory output RData missing")
        self.assertTrue(summary_log.exists(), "NDLM theory summary log missing")

        summary = _parse_kv(summary_log.read_text(encoding="utf-8"))
        self.assertEqual(summary.get("implementation_mode"), "theory_aligned")
        w_hist = float(summary["w_hist"])
        w_fore = float(summary["w_fore"])
        sigma = float(summary["sigma"])
        self.assertTrue(math.isfinite(w_hist) and w_hist > 0)
        self.assertTrue(math.isfinite(w_fore) and w_fore > 0)
        self.assertTrue(math.isfinite(sigma) and sigma > 0)

        inspect_code = r'''
path <- Sys.getenv("RDATA_PATH")
load(path)
suffix <- "50_NDLM_synth_DISC"
elbo <- get(paste0("seq.elbo_", suffix))
sigma_seq <- get(paste0("seq.sigma_", suffix))
state <- get("ndlm_main_theory_state")
theta <- get(paste0("new.theta.out_", suffix))
sC <- theta$sC
cat(sprintf("elbo_len=%d\n", length(elbo)))
cat(sprintf("sigma_len=%d\n", length(sigma_seq)))
cat(sprintf("elbo_finite=%d\n", sum(is.finite(elbo))))
cat(sprintf("sigma_finite=%d\n", sum(is.finite(sigma_seq))))
cat(sprintf("state_sigma_finite=%s\n", as.character(is.finite(state$sigma))))
cat(sprintf("state_w_hist_finite=%s\n", as.character(is.finite(state$w_hist))))
cat(sprintf("state_w_fore_finite=%s\n", as.character(is.finite(state$w_fore))))
cat(sprintf("sC_dim1=%d\n", dim(sC)[1]))
cat(sprintf("sC_dim2=%d\n", dim(sC)[2]))
cat(sprintf("sC_dim3=%d\n", dim(sC)[3]))
cat(sprintf("sC_last_diag_min=%0.12f\n", min(diag(sC[,,dim(sC)[3]]))))
'''
        inspect_env = env.copy()
        inspect_env["RDATA_PATH"] = str(out_rdata)
        inspect = subprocess.run(
            ["Rscript", "--vanilla", "-e", inspect_code],
            cwd=REPO_ROOT,
            env=inspect_env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(inspect.returncode, 0, msg=inspect.stdout + "\n" + inspect.stderr)
        parsed = _parse_kv(inspect.stdout)

        self.assertEqual(int(parsed["elbo_len"]), 16)
        self.assertEqual(int(parsed["sigma_len"]), 16)
        self.assertGreaterEqual(int(parsed["elbo_finite"]), 10)
        self.assertEqual(int(parsed["sigma_finite"]), 16)
        self.assertEqual(parsed["state_sigma_finite"], "TRUE")
        self.assertEqual(parsed["state_w_hist_finite"], "TRUE")
        self.assertEqual(parsed["state_w_fore_finite"], "TRUE")
        self.assertEqual(int(parsed["sC_dim1"]), 26)
        self.assertEqual(int(parsed["sC_dim2"]), 26)
        self.assertGreaterEqual(int(parsed["sC_dim3"]), 30)
        self.assertGreater(float(parsed["sC_last_diag_min"]), 0.0)


if __name__ == "__main__":
    unittest.main()
