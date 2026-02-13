from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
RUNS_ROOT = REPO_ROOT / "repro" / "runs"


class UnifiedRunStageSkipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run_id = f"ut_skip_{uuid.uuid4().hex[:12]}"
        self.run_root = RUNS_ROOT / self.run_id
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ut_unified_skip_", dir=str(REPO_ROOT / "repro")))
        self.config_path = self.tmpdir / "cfg.yaml"

    def tearDown(self) -> None:
        if self.run_root.exists():
            shutil.rmtree(self.run_root, ignore_errors=True)
        if self.tmpdir.exists():
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_runner_writes_skip_status_for_disabled_stages(self) -> None:
        cfg = {
            "config_version": 1,
            "run": {
                "run_id": self.run_id,
                "run_root": "repro/runs",
                "overwrite": False,
                "dry_run": False,
            },
            "stages": {
                "forecats": False,
                "data_prep_shared": False,
                "fit": False,
                "post": False,
                "validate": False,
                "report": False,
            },
        }
        self.config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

        proc = subprocess.run(
            ["Rscript", "--vanilla", "scripts/unified_run.R", "--config", str(self.config_path)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        manifest_path = self.run_root / "run_manifest.yaml"
        self.assertTrue(manifest_path.exists(), msg="Expected run_manifest.yaml to be created")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        self.assertTrue((manifest.get("timestamps") or {}).get("finished_at_utc"))

        stages = manifest.get("stages") or {}
        for stage in ("forecats", "data_prep_shared", "fit", "post", "validate", "report"):
            self.assertEqual((stages.get(stage) or {}).get("status"), "skip", msg=f"stage={stage}")


if __name__ == "__main__":
    unittest.main()
