from __future__ import annotations

import json
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
RUNS_ROOT = REPO_ROOT / "repro" / "runs"


def _write_text(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class StageReportFamilySummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run_id = f"ut_report_{uuid.uuid4().hex[:12]}"
        self.run_root = RUNS_ROOT / self.run_id
        self.run_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.run_root.exists():
            shutil.rmtree(self.run_root, ignore_errors=True)

    def test_report_summary_json_contains_family_sections(self) -> None:
        _write_text(self.run_root / "validate" / "compare_report.json", json.dumps({"metrics": {"matched": 2, "missing": 0, "extra": 0, "mismatched": 0}, "env_drift": {"status": "clean"}}))
        _write_text(self.run_root / "validate" / "write_audit" / "fit" / "fs_diff.patch", "")

        mv01 = self.run_root / "fit" / "q=01" / "outputs" / "DISC_variables_1_exAL_synth_DISC.RData"
        mv50 = self.run_root / "fit" / "q=50" / "outputs" / "DISC_variables_50_exAL_synth_DISC.RData"
        uv01 = self.run_root / "fit" / "exdqlm_univar" / "q=01" / "outputs" / "variables_01_exAL_synth_DISC_uni.RData"
        uv50 = self.run_root / "fit" / "exdqlm_univar" / "q=50" / "outputs" / "variables_50_exAL_synth_DISC_uni.RData"
        ndlm = self.run_root / "fit" / "ndlm_main" / "outputs" / "DISC_variables_50_NDLM_synth_DISC.RData"
        for p in (mv01, mv50, uv01, uv50, ndlm):
            _write_text(p, "dummy\n")

        r_code = f"""
        repo_root <- normalizePath('{REPO_ROOT.as_posix()}', mustWork = TRUE)
        run_root <- normalizePath('{self.run_root.as_posix()}', mustWork = TRUE)
        source(file.path(repo_root, 'R', 'unified', 'stages', 'stage_report.R'))

        cfg <- list(
          run = list(run_id = '{self.run_id}', repro_mode = 'strict', seed = 777),
          fit = list(quantiles = c(0.01, 0.50)),
          stages = list(forecats = FALSE, data_prep_shared = FALSE, fit = TRUE, post = TRUE, validate = TRUE, report = TRUE),
          post = list(profile = FALSE),
          models = list(run_exdqlm_multivar = TRUE, run_exdqlm_univar = TRUE, run_ndlm_main = TRUE)
        )

        manifest <- list(
          git = list(commit = 'deadbeef'),
          inputs = list(),
          artifacts = list(
            list(path = 'fit/q=01/outputs/DISC_variables_1_exAL_synth_DISC.RData'),
            list(path = 'fit/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData'),
            list(path = 'fit/exdqlm_univar/q=01/outputs/variables_01_exAL_synth_DISC_uni.RData'),
            list(path = 'fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData'),
            list(path = 'fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData')
          ),
          validation = list(status = 'pass', compare_report_path = file.path(run_root, 'validate', 'compare_report.json')),
          change_approval = list(status = 'approved')
        )

        unified_stage_report(cfg, run_root, repo_root, manifest)
        """

        run = subprocess.run(
            ["Rscript", "--vanilla", "-e", r_code],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(run.returncode, 0, msg=run.stdout + "\n" + run.stderr)

        summary_json = self.run_root / "report" / "summary.json"
        self.assertTrue(summary_json.exists(), "report summary.json missing")
        payload = json.loads(summary_json.read_text(encoding="utf-8"))

        families = ((payload.get("report") or {}).get("families") or {})
        mv = families.get("exdqlm_multivar") or {}
        uv = families.get("exdqlm_univar") or {}
        nd = families.get("ndlm_main") or {}

        self.assertTrue(mv.get("enabled"))
        self.assertEqual(mv.get("quantiles_expected"), [1, 50])
        self.assertEqual(mv.get("quantiles_found"), [1, 50])

        self.assertTrue(uv.get("enabled"))
        self.assertEqual(uv.get("quantiles_expected"), [1, 50])
        self.assertEqual(uv.get("quantiles_found"), [1, 50])

        self.assertTrue(nd.get("enabled"))
        self.assertTrue(nd.get("output_present"))


if __name__ == "__main__":
    unittest.main()
