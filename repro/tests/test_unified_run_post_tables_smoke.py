import csv
import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml


class TestUnifiedRunPostTablesSmoke(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.tmp_root = self.repo_root / "repro" / "_tmp_unittest" / "post_tables_e2e"
        self.tmp_root.mkdir(parents=True, exist_ok=True)
        self.work_dir = Path(tempfile.mkdtemp(prefix="case_", dir=self.tmp_root))
        self.run_root = self.work_dir / "runs"
        self.run_id = "ut_post_tables_smoke"
        self.real_rscript = shutil.which("Rscript")
        if not self.real_rscript:
            self.fail("Rscript not found in PATH")

    def tearDown(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def _write_stub_rscript(self) -> Path:
        bin_dir = self.work_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        wrapper_path = bin_dir / "Rscript"

        # Intercept only stage_post runner call; pass-through otherwise.
        script = textwrap.dedent(
            """#!/usr/bin/env bash
set -euo pipefail
real="${REAL_RSCRIPT:?REAL_RSCRIPT is required}"
if [[ "${1:-}" == "--vanilla" && "${2:-}" == "scripts/run_environmetrics_figures.R" ]]; then
  exec "$real" --vanilla -e '
source(file.path("R", "environmetrics", "02_helpers_core.R"))
out_dir <- file.path(Sys.getenv("UNIFIED_RUN_ROOT"), "post", "outputs", Sys.getenv("UNIFIED_RUN_ID"), "tables")
dir.create(out_dir, recursive=TRUE, showWarnings=FALSE)
# Use real deterministic exporter to preserve runtime semantics under test.
m <- post_export_tables(
  tables = list(example = data.frame(id = c(2L,1L), value = c(3.14, 2.72), stringsAsFactors = FALSE)),
  output_dir = out_dir,
  formats = c("csv", "rds"),
  keep_na = TRUE,
  sort_keys = list(example = c("id"))
)
post_write_table_exports_manifest(m, output_dir = out_dir)
writeLines("stub_post_runner_ok", con = file.path(Sys.getenv("UNIFIED_RUN_ROOT"), "post", "logs", "stub_post_runner.log"))
'
fi
exec "$real" "$@"
"""
        )
        wrapper_path.write_text(script, encoding="utf-8")
        wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IXUSR)
        return wrapper_path

    def _write_config(self) -> Path:
        cfg = textwrap.dedent(
            f"""
config_version: 1
run:
  run_id: "{self.run_id}"
  run_root: "{self.run_root.as_posix()}"
  repro_mode: "fast"
  seed: 777
  overwrite: true
stages:
  forecats: false
  data_prep_shared: false
  fit: false
  post: true
  validate: false
  report: false
models:
  run_exdqlm_multivar: false
  run_exdqlm_univar: false
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
fit:
  quantiles: [0.05]
post:
  figures: false
  smoke_fast: false
  sort_keep_na: true
  export_tables: true
  table_formats: ["csv", "rds"]
validation:
  profile: "smoke"
write_audit:
  enabled: false
"""
        )
        cfg_path = self.work_dir / "smoke_post_tables_manifest.yaml"
        cfg_path.write_text(cfg, encoding="utf-8")
        return cfg_path

    def test_unified_run_stage_post_tables_and_allowlist(self):
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

        run_dir = self.run_root / self.run_id
        manifest_path = run_dir / "run_manifest.yaml"
        self.assertTrue(manifest_path.exists(), "run_manifest.yaml missing")

        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        ts = ((manifest.get("timestamps") or {}).get("finished_at_utc"))
        self.assertIsNotNone(ts)
        self.assertNotEqual(str(ts).strip().lower(), "null")
        self.assertNotEqual(str(ts).strip(), "")

        tables_dir = run_dir / "post" / "outputs" / self.run_id / "tables"
        self.assertTrue(tables_dir.exists(), f"tables dir missing: {tables_dir}")
        files = [p for p in tables_dir.iterdir() if p.is_file()]
        self.assertTrue(files, "tables dir is empty")

        export_manifest = tables_dir / "posterior_table_exports_manifest.csv"
        self.assertTrue(export_manifest.exists(), "posterior_table_exports_manifest.csv missing")

        with export_manifest.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreater(len(rows), 0)
        for row in rows:
            rel = row["file_path"]
            self.assertTrue(rel)
            self.assertFalse(Path(rel).is_absolute(), msg=f"expected relative path, got {rel}")
            self.assertFalse(rel.startswith("/"), msg=f"unexpected absolute unix path: {rel}")
            self.assertRegex(rel, r"^[^\\\\]*")
            resolved = tables_dir / rel
            self.assertTrue(resolved.exists(), msg=f"manifest path does not resolve under tables dir: {rel}")

        # Run-manifest post artifacts must remain allowlist-only; at minimum exclude .tex/.md.
        artifacts = manifest.get("artifacts") or []
        post_paths = []
        for item in artifacts:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "")
            if f"post/outputs/{self.run_id}/" in path:
                post_paths.append(path)

        self.assertGreater(len(post_paths), 0, "no post artifacts recorded in run manifest")
        disallowed = [p for p in post_paths if p.lower().endswith((".tex", ".md"))]
        self.assertEqual(disallowed, [], msg=f"disallowed post artifact extensions recorded: {disallowed}")


if __name__ == "__main__":
    unittest.main()
