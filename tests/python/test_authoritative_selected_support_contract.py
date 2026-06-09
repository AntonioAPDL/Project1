from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class AuthoritativeSelectedSupportContractTests(unittest.TestCase):
    def run_r(self, script: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as td:
            script_path = Path(td) / "check.R"
            script_path.write_text(script, encoding="utf-8")
            return subprocess.run(
                ["Rscript", "--vanilla", str(script_path)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_contract_requires_support_artifacts_only_when_enabled(self) -> None:
        script = textwrap.dedent(
            r"""
            source("R/unified/post_artifact_contract.R")
            out <- tempfile("post_outputs_")
            dir.create(out)
            file.create(file.path(out, "some_figure.png"))
            artifacts <- unified_collect_post_artifacts(outputs_dir = out)
            ordinary <- unified_post_contract_check(
              artifacts_df = artifacts,
              outputs_dir = out,
              post_figures = TRUE,
              export_tables = FALSE,
              post_smoke_fast = TRUE,
              model_run_exdqlm_multivar = TRUE,
              model_run_exdqlm_univar = FALSE,
              model_run_ndlm_main = FALSE,
              model_run_ndlm_univar = FALSE,
              authoritative_selected_model_support = FALSE
            )
            if (!isTRUE(ordinary$status)) stop("ordinary smoke contract unexpectedly failed")
            requested <- unified_post_contract_check(
              artifacts_df = artifacts,
              outputs_dir = out,
              post_figures = TRUE,
              export_tables = FALSE,
              post_smoke_fast = TRUE,
              model_run_exdqlm_multivar = TRUE,
              model_run_exdqlm_univar = FALSE,
              model_run_ndlm_main = FALSE,
              model_run_ndlm_univar = FALSE,
              authoritative_selected_model_support = TRUE
            )
            if (isTRUE(requested$status)) stop("selected-support contract should fail when artifacts are missing")
            required <- c(
              "authoritative_usgs_quantile_dynamics_summary.csv",
              "authoritative_usgs_quantile_dynamics_summary.rds",
              "authoritative_component_summary.csv",
              "authoritative_component_summary.rds",
              "authoritative_selected_support_lineage.csv",
              "authoritative_selected_support_manifest.json"
            )
            for (name in required) writeLines("ok", file.path(out, name))
            artifacts2 <- unified_collect_post_artifacts(outputs_dir = out)
            satisfied <- unified_post_contract_check(
              artifacts_df = artifacts2,
              outputs_dir = out,
              post_figures = TRUE,
              export_tables = FALSE,
              post_smoke_fast = TRUE,
              model_run_exdqlm_multivar = TRUE,
              model_run_exdqlm_univar = FALSE,
              model_run_ndlm_main = FALSE,
              model_run_ndlm_univar = FALSE,
              authoritative_selected_model_support = TRUE
            )
            if (!isTRUE(satisfied$status)) stop(paste(satisfied$messages, collapse = "; "))
            """
        )
        proc = self.run_r(script)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
