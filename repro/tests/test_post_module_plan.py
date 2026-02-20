import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class TestPostModulePlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.plan_file = cls.repo_root / "R" / "unified" / "post_module_plan.R"
        cls.ndlm_init_file = cls.repo_root / "R" / "environmetrics" / "30_ndlm_only_init.R"

    def _run_r(self, script: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["Rscript", "--vanilla", "-e", script],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_module_plan_ndlm_only_uses_ndlm_init_and_smoke_figures(self):
        script = textwrap.dedent(
            f"""
            source("{self.plan_file.as_posix()}")
            core <- c("00_paths.R","00_setup.R")
            mods <- unified_post_select_modules(
              post_figures = TRUE,
              post_smoke_fast = FALSE,
              model_run_exdqlm_multivar = FALSE,
              model_run_exdqlm_univar = FALSE,
              model_run_ndlm_main = TRUE,
              core_modules = core
            )
            cat(paste(mods, collapse="|"))
            """
        )
        res = self._run_r(script)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        mods = res.stdout.strip().split("|")
        self.assertIn("30_ndlm_only_init.R", mods)
        self.assertIn("40_figures_smoke_fast.R", mods)
        self.assertNotIn("30_univariate_and_misc.R", mods)
        self.assertNotIn("40_figures.R", mods)

    def test_module_plan_non_ndlm_only_keeps_full_path(self):
        script = textwrap.dedent(
            f"""
            source("{self.plan_file.as_posix()}")
            core <- c("00_paths.R","00_setup.R")
            mods_univar <- unified_post_select_modules(
              post_figures = TRUE,
              post_smoke_fast = FALSE,
              model_run_exdqlm_multivar = FALSE,
              model_run_exdqlm_univar = TRUE,
              model_run_ndlm_main = FALSE,
              core_modules = core
            )
            mods_multivar <- unified_post_select_modules(
              post_figures = TRUE,
              post_smoke_fast = FALSE,
              model_run_exdqlm_multivar = TRUE,
              model_run_exdqlm_univar = FALSE,
              model_run_ndlm_main = FALSE,
              core_modules = core
            )
            mods_mixed <- unified_post_select_modules(
              post_figures = TRUE,
              post_smoke_fast = FALSE,
              model_run_exdqlm_multivar = TRUE,
              model_run_exdqlm_univar = TRUE,
              model_run_ndlm_main = TRUE,
              core_modules = core
            )
            cat(
              paste(mods_univar, collapse="|"), "\\n",
              paste(mods_multivar, collapse="|"), "\\n",
              paste(mods_mixed, collapse="|")
            )
            """
        )
        res = self._run_r(script)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        for line in [x.strip() for x in res.stdout.strip().splitlines() if x.strip()]:
            mods = line.split("|")
            self.assertIn("30_univariate_and_misc.R", mods)
            self.assertIn("40_figures.R", mods)
            self.assertNotIn("30_ndlm_only_init.R", mods)

    def test_ndlm_only_init_passes_for_valid_bundle_and_fails_fast_for_empty_path(self):
        with tempfile.TemporaryDirectory(prefix="ndlm_init_ut_") as td:
            td_path = Path(td)
            bundle_path = td_path / "ndlm_bundle.RData"

            # Build a minimal valid NDLM bundle.
            build_script = textwrap.dedent(
                f"""
                new.theta.out_50_NDLM_synth_DISC <- list(
                  sm = matrix(1, 2, 3),
                  sC = array(1, dim = c(2,2,3)),
                  exps = matrix(1, 2, 3),
                  sm_ens = list(matrix(1, 2, 2)),
                  sC_ens = list(array(1, dim = c(2,2,2))),
                  standard_forecast_errors = matrix(1, 2, 3)
                )
                samp.theta_50_NDLM_synth_DISC <- list(samp_theta = array(1, dim = c(2,3,4)))
                samp.sigma_50_NDLM_synth_DISC <- matrix(1, 1, 4)
                seq.elbo_50_NDLM_synth_DISC <- c(0, 1, 2, 3)
                save(
                  new.theta.out_50_NDLM_synth_DISC,
                  samp.theta_50_NDLM_synth_DISC,
                  samp.sigma_50_NDLM_synth_DISC,
                  seq.elbo_50_NDLM_synth_DISC,
                  file = "{bundle_path.as_posix()}"
                )
                """
            )
            build_res = self._run_r(build_script)
            self.assertEqual(build_res.returncode, 0, msg=build_res.stderr)

            pass_script = textwrap.dedent(
                f"""
                profile_section <- function(name, expr) eval.parent(substitute(expr))
                MODEL_RUN_NDLM_MAIN <- TRUE
                MODEL_RUN_EXDQLM_MULTIVAR <- FALSE
                MODEL_RUN_EXDQLM_UNIVAR <- FALSE
                NDLM_VAR_50 <- "{bundle_path.as_posix()}"
                source("{self.ndlm_init_file.as_posix()}")
                cat("ok")
                """
            )
            pass_res = self._run_r(pass_script)
            self.assertEqual(pass_res.returncode, 0, msg=pass_res.stderr)
            self.assertIn("ok", pass_res.stdout)

            fail_script = textwrap.dedent(
                f"""
                profile_section <- function(name, expr) eval.parent(substitute(expr))
                MODEL_RUN_NDLM_MAIN <- TRUE
                MODEL_RUN_EXDQLM_MULTIVAR <- FALSE
                MODEL_RUN_EXDQLM_UNIVAR <- FALSE
                NDLM_VAR_50 <- ""
                source("{self.ndlm_init_file.as_posix()}")
                """
            )
            fail_res = self._run_r(fail_script)
            self.assertNotEqual(fail_res.returncode, 0)
            self.assertIn("[POST_NDLM_ONLY_INIT] NDLM artifact path is empty", fail_res.stderr)

    def test_post_contract_smoke_fast_relaxes_full_cache_and_table_requirements(self):
        with tempfile.TemporaryDirectory(prefix="post_contract_smoke_ut_") as td:
            td_path = Path(td)
            outputs_dir = td_path / "outputs"
            cache_dir = td_path / "cache"
            outputs_dir.mkdir(parents=True, exist_ok=True)
            cache_dir.mkdir(parents=True, exist_ok=True)
            # Minimal smoke-fast artifact set: one figure + contract reports.
            (outputs_dir / "All_ELBOS_DISC.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (outputs_dir / "post_artifacts_manifest.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (outputs_dir / "post_artifacts_summary.json").write_text("{}", encoding="utf-8")

            script = textwrap.dedent(
                f"""
                source("{(self.repo_root / "R" / "unified" / "post_artifact_contract.R").as_posix()}")
                artifacts <- unified_collect_post_artifacts(
                  outputs_dir = "{outputs_dir.as_posix()}",
                  cache_dir = "{cache_dir.as_posix()}"
                )
                chk <- unified_post_contract_check(
                  artifacts_df = artifacts,
                  outputs_dir = "{outputs_dir.as_posix()}",
                  cache_dir = "{cache_dir.as_posix()}",
                  post_figures = TRUE,
                  export_tables = TRUE,
                  post_smoke_fast = TRUE
                )
                if (!isTRUE(chk$status)) {{
                  cat(paste(chk$messages, collapse=" | "))
                  quit(status = 1)
                }}
                cat("ok")
                """
            )
            res = self._run_r(script)
            self.assertEqual(res.returncode, 0, msg=res.stderr + "\n" + res.stdout)
            self.assertIn("ok", res.stdout)


if __name__ == "__main__":
    unittest.main()
