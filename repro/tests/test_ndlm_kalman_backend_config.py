import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_r(expr: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["Rscript", "--vanilla", "-e", expr],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class NdlmKalmanBackendConfigTests(unittest.TestCase):
    def test_default_backend_is_cpp(self) -> None:
        expr = (
            "source('R/unified/config.R');"
            "cfg <- unified_config_defaults();"
            "cat(cfg$models$ndlm_main$kalman_backend)"
        )
        res = run_r(expr)
        self.assertEqual(res.returncode, 0, msg=f"stderr:\n{res.stderr}")
        self.assertEqual(res.stdout.strip(), "cpp")

    def test_invalid_backend_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ut_ndlm_backend_cfg_") as td:
            cfg_path = Path(td) / "bad.yaml"
            cfg_path.write_text(
                textwrap.dedent(
                    """
                    config_version: 1
                    run:
                      run_id: "ut_bad_backend"
                      run_root: "repro/runs"
                      repro_mode: "strict"
                      seed: 777
                      overwrite: false
                      dry_run: true
                      git_require_clean: false
                      threads: { omp: 1, openblas: 1, mkl: 1, veclib: 1, numexpr: 1, mc_cores: 1 }
                    stages: { forecats: false, data_prep_shared: false, fit: false, post: false, validate: false, report: false }
                    models:
                      run_exdqlm_multivar: false
                      run_exdqlm_univar: false
                      run_ndlm_main: true
                      ndlm_main:
                        implementation_mode: "theory_aligned"
                        kalman_backend: "bad"
                    site: { usgs_site: "11160500", lat: 37.0443931, lon: -122.072464 }
                    dates: { cutoff_date: "2022-12-25", plot_start: "2022-12-07", plot_end: "2023-01-22" }
                    inputs:
                      fit:
                        parameters_path: "config/unified_runs/production_canonical_family.yaml"
                        retros_path: "retros_2022-12-25.csv"
                        retros_storage_scale: "log1p_cms"
                        nws_forecast_path: "nws_forecast.csv"
                        nws_storage_scale: "log1p_cms"
                        glofas_forecast_path: "weighted_time_series.csv"
                        glofas_storage_scale: "log1p_cms"
                      post:
                        use_fit_outputs_from_run: true
                    fit:
                      quantiles: [0.5]
                    post:
                      figures: false
                    validation:
                      profile: "smoke"
                    scale_contract:
                      canonical_storage_scale: "raw_cms"
                      legacy_fit_input_scale: "log1p_cms"
                      legacy_post_input_scale: "log1p_cms"
                      analysis_scale_fit_internal: "log1p_cms"
                      analysis_scale_post_internal: "log1p_cms"
                    write_audit:
                      enabled: false
                    """
                ).strip()
            )

            expr = (
                "source('R/unified/config.R');"
                f"unified_load_config('{cfg_path.as_posix()}', repo_root = '{REPO_ROOT.as_posix()}')"
            )
            res = run_r(expr)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("models.ndlm_main.kalman_backend", res.stderr)

    def test_default_internal_scales_are_log1p(self) -> None:
        expr = (
            "source('R/unified/config.R');"
            "cfg <- unified_config_defaults();"
            "cat(cfg$scale_contract$analysis_scale_fit_internal, '\\n', cfg$scale_contract$analysis_scale_post_internal)"
        )
        res = run_r(expr)
        self.assertEqual(res.returncode, 0, msg=f"stderr:\n{res.stderr}")
        self.assertEqual([line.strip() for line in res.stdout.strip().splitlines()], ["log1p_cms", "log1p_cms"])

    def test_loglog_internal_scale_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ut_ndlm_scale_cfg_") as td:
            cfg_path = Path(td) / "bad_scale.yaml"
            cfg_path.write_text(
                textwrap.dedent(
                    """
                    config_version: 1
                    run:
                      run_id: "ut_bad_scale"
                      run_root: "repro/runs"
                      repro_mode: "strict"
                      seed: 777
                      overwrite: false
                      dry_run: true
                      git_require_clean: false
                      threads: { omp: 1, openblas: 1, mkl: 1, veclib: 1, numexpr: 1, mc_cores: 1 }
                    stages: { forecats: false, data_prep_shared: false, fit: false, post: false, validate: false, report: false }
                    models:
                      run_exdqlm_multivar: false
                      run_exdqlm_univar: false
                      run_ndlm_main: false
                    site: { usgs_site: "11160500", lat: 37.0443931, lon: -122.072464 }
                    dates: { cutoff_date: "2022-12-25", plot_start: "2022-12-07", plot_end: "2023-01-22" }
                    inputs:
                      fit:
                        parameters_path: "config/unified_runs/production_canonical_family.yaml"
                        retros_path: "retros_2022-12-25.csv"
                        retros_storage_scale: "log1p_cms"
                        nws_forecast_path: "nws_forecast.csv"
                        nws_storage_scale: "raw_cms"
                        glofas_forecast_path: "weighted_time_series.csv"
                        glofas_storage_scale: "raw_cms"
                      post:
                        use_fit_outputs_from_run: true
                    fit:
                      quantiles: [0.5]
                    post:
                      figures: false
                    validation:
                      profile: "smoke"
                    scale_contract:
                      canonical_storage_scale: "raw_cms"
                      legacy_fit_input_scale: "log1p_cms"
                      legacy_post_input_scale: "log1p_cms"
                      analysis_scale_fit_internal: "log_log1p_cms"
                      analysis_scale_post_internal: "log1p_cms"
                    write_audit:
                      enabled: false
                    """
                ).strip()
            )

            expr = (
                "source('R/unified/config.R');"
                f"unified_load_config('{cfg_path.as_posix()}', repo_root = '{REPO_ROOT.as_posix()}')"
            )
            res = run_r(expr)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("must not use log-log transforms", res.stderr)


if __name__ == "__main__":
    unittest.main()
