import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


REPO = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
SCRIPT = REPO / "scripts" / "prepare_reduced_defaultvb_temporal_bundle.py"


class PrepareReducedDefaultVBTemporalBundleTest(unittest.TestCase):
    def test_prepares_isolated_launch_and_prefit_configs(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            source_cfg = td_path / "source.yaml"
            target_root = td_path / "runtime"
            report_dir = td_path / "report"

            source_payload = {
                "run": {
                    "run_id": "source_run",
                    "run_root": "/tmp/source_runs",
                    "overwrite": False,
                    "auto_suffix_on_collision": True,
                    "dry_run": False,
                },
                "stages": {
                    "forecats": False,
                    "data_prep_shared": True,
                    "fit": True,
                    "post": True,
                    "validate": True,
                    "report": True,
                },
                "dates": {
                    "data_start": "2010-01-01",
                },
                "fit": {
                    "warm_start": {
                        "enabled": True,
                        "source_run_id": "old",
                        "source_run_root": "/tmp/old",
                    }
                },
            }
            source_cfg.write_text(yaml.safe_dump(source_payload, sort_keys=False), encoding="utf-8")

            subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--source-config",
                    str(source_cfg),
                    "--target-runtime-root",
                    str(target_root),
                    "--spec-label",
                    "testspec",
                    "--data-start",
                    "2016-01-01",
                    "--report-dir",
                    str(report_dir),
                ],
                check=True,
            )

            launch_cfg = target_root / "control" / "generated_configs" / "multimodel_20221225_v8_he2pubgdpc1r1_testspec_exdqlm_multivar_keep.yaml"
            prefit_cfg = target_root / "control" / "generated_configs" / "multimodel_20221225_v8_he2pubgdpc1r1_testspec_exdqlm_multivar_keep_prefitcheck.yaml"
            self.assertTrue(launch_cfg.exists())
            self.assertTrue(prefit_cfg.exists())

            launch = yaml.safe_load(launch_cfg.read_text(encoding="utf-8"))
            prefit = yaml.safe_load(prefit_cfg.read_text(encoding="utf-8"))

            self.assertEqual(launch["dates"]["data_start"], "2016-01-01")
            self.assertEqual(prefit["dates"]["data_start"], "2016-01-01")
            self.assertFalse(launch["fit"]["warm_start"]["enabled"])
            self.assertIsNone(launch["fit"]["warm_start"]["source_run_root"])
            self.assertTrue(launch["stages"]["fit"])
            self.assertFalse(prefit["stages"]["fit"])
            self.assertFalse(prefit["stages"]["post"])
            self.assertFalse(prefit["stages"]["validate"])
            self.assertFalse(prefit["stages"]["report"])

            original = yaml.safe_load(source_cfg.read_text(encoding="utf-8"))
            self.assertTrue(original["fit"]["warm_start"]["enabled"])
            self.assertEqual(original["dates"]["data_start"], "2010-01-01")

            summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["data_start"], "2016-01-01")


if __name__ == "__main__":
    unittest.main()
