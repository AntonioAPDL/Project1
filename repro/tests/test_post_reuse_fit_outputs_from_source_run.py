from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml


class TestPostReuseFitOutputsFromSourceRun(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.tmp_root = self.repo_root / "repro" / "_tmp_unittest" / "post_reuse_source_run"
        self.tmp_root.mkdir(parents=True, exist_ok=True)
        self.work_dir = Path(tempfile.mkdtemp(prefix="case_", dir=self.tmp_root))
        self.run_root = self.work_dir / "runs"
        self.source_run_id = "ut_source_fit_run"
        self.replay_run_id = "ut_post_reuse_fit_run"
        self.real_rscript = shutil.which("Rscript")
        if not self.real_rscript:
            self.fail("Rscript not found in PATH")

    def tearDown(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def _write_source_fit_artifacts(self) -> None:
        src_fit = (
            self.run_root
            / self.source_run_id
            / "fit"
            / "exdqlm_univar"
            / "q=05"
            / "outputs"
        )
        src_fit.mkdir(parents=True, exist_ok=True)
        # Existence is sufficient for stage_post path resolution in this test.
        (src_fit / "variables_05_exAL_synth_DISC_uni.RData").write_bytes(b"stub")

    def _write_stub_rscript(self) -> None:
        bin_dir = self.work_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        wrapper_path = bin_dir / "Rscript"
        script = textwrap.dedent(
            """#!/usr/bin/env bash
set -euo pipefail
real="${REAL_RSCRIPT:?REAL_RSCRIPT is required}"
if [[ "${1:-}" == "--vanilla" && "${2:-}" == "scripts/run_environmetrics_figures.R" ]]; then
  exec "$real" --vanilla -e '
paths <- strsplit(Sys.getenv("UNIFIED_UNIV_RDATA_PATHS"), ",", fixed=TRUE)[[1]]
paths <- paths[nzchar(paths)]
if (length(paths) != 1L) stop("expected exactly one univariate path")
if (!file.exists(paths[[1]])) stop("resolved univariate source path does not exist")
out_dir <- file.path(Sys.getenv("UNIFIED_RUN_ROOT"), "post", "outputs", Sys.getenv("UNIFIED_RUN_ID"))
dir.create(out_dir, recursive=TRUE, showWarnings=FALSE)
writeLines(paths[[1]], con=file.path(out_dir, "resolved_univ_path.txt"))
writeLines("post_reuse_source_run_ok", con=file.path(out_dir, "post_smoke_marker.txt"))
'
fi
exec "$real" "$@"
"""
        )
        wrapper_path.write_text(script, encoding="utf-8")
        wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IXUSR)

    def _write_config(self) -> Path:
        cfg_text = textwrap.dedent(
            f"""
config_version: 1
run:
  run_id: "{self.replay_run_id}"
  run_root: "{self.run_root.as_posix()}"
  repro_mode: "strict"
  seed: 777
  overwrite: false
stages:
  forecats: false
  data_prep_shared: false
  fit: false
  post: true
  validate: false
  report: false
models:
  run_exdqlm_multivar: false
  run_exdqlm_univar: true
  run_ndlm_main: false
inputs:
  fit:
    parameters_path: "{(self.repo_root / 'parameters.txt').as_posix()}"
    retros_path: "{(self.repo_root / 'retros_2022-12-25.csv').as_posix()}"
    retros_storage_scale: "log1p_cms"
    nws_forecast_path: "{(self.repo_root / 'nws_forecast.csv').as_posix()}"
    nws_storage_scale: "log1p_cms"
    glofas_forecast_path: "{(self.repo_root / 'glofas_forecast.csv').as_posix()}"
    glofas_storage_scale: "log1p_cms"
  post:
    use_fit_outputs_from_run: true
    source_run_id: "{self.source_run_id}"
    source_run_root: "{self.run_root.as_posix()}"
fit:
  quantiles: [0.05]
post:
  figures: false
  smoke_fast: false
  export_tables: false
validation:
  profile: "smoke"
write_audit:
  enabled: false
"""
        )
        cfg_path = self.work_dir / "post_reuse_source_run.yaml"
        cfg_path.write_text(cfg_text, encoding="utf-8")
        return cfg_path

    def test_post_stage_reuses_fit_outputs_from_source_run(self) -> None:
        self._write_source_fit_artifacts()
        self._write_stub_rscript()
        cfg_path = self._write_config()

        env = os.environ.copy()
        env["REAL_RSCRIPT"] = self.real_rscript
        env["PATH"] = f"{(self.work_dir / 'bin').as_posix()}:{env.get('PATH', '')}"

        proc = subprocess.run(
            ["Rscript", "--vanilla", "scripts/unified_run.R", "--config", str(cfg_path)],
            cwd=self.repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout[-4000:])

        replay_root = self.run_root / self.replay_run_id
        manifest = yaml.safe_load((replay_root / "run_manifest.yaml").read_text(encoding="utf-8")) or {}
        stages = manifest.get("stages") or {}
        self.assertEqual((stages.get("post") or {}).get("status"), "pass")
        self.assertEqual((stages.get("fit") or {}).get("status"), "skip")

        resolved_path_file = replay_root / "post" / "outputs" / self.replay_run_id / "resolved_univ_path.txt"
        self.assertTrue(resolved_path_file.exists(), "resolved_univ_path.txt missing")
        resolved_path = resolved_path_file.read_text(encoding="utf-8").strip()
        self.assertIn(self.source_run_id, resolved_path)
        self.assertTrue(resolved_path.endswith("variables_05_exAL_synth_DISC_uni.RData"))
        self.assertTrue(Path(resolved_path).exists(), f"resolved source path missing: {resolved_path}")


if __name__ == "__main__":
    unittest.main()
