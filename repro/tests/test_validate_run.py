from __future__ import annotations

import json
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
RUNS_ROOT = REPO_ROOT / "repro" / "runs"
VALIDATE_SCRIPT = REPO_ROOT / "repro" / "tools" / "validate_run.sh"


def write_text(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class ValidateRunScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run_id = f"ut_validate_{uuid.uuid4().hex[:12]}"
        self.run_root = RUNS_ROOT / self.run_id
        self.run_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.run_root.exists():
            shutil.rmtree(self.run_root, ignore_errors=True)

    def _write_common_success_files(self) -> None:
        write_text(
            self.run_root / "run_manifest.yaml",
            "\n".join(
                [
                    "manifest_version: 1",
                    f"run_id: {self.run_id}",
                    f"run_root: {self.run_root}",
                    "timestamps:",
                    "  started_at_utc: '2026-02-11T00:00:00Z'",
                    "  finished_at_utc: '2026-02-11T00:10:00Z'",
                    "validation:",
                    "  status: pass",
                ]
            )
            + "\n",
        )
        write_json(
            self.run_root / "validate" / "compare_report.json",
            {
                "status": "pass",
                "metrics": {"matched": 1, "missing": 0, "extra": 0, "mismatched": 0},
            },
        )
        write_text(self.run_root / "validate" / "write_audit" / "fit" / "fs_diff.patch", "")
        write_json(self.run_root / "report" / "summary.json", {"ok": True})
        write_text(self.run_root / "report" / "summary.md", "# ok\n")
        write_text(self.run_root / "post" / "outputs" / self.run_id / "dummy.txt", "ok\n")

    def _run_validate(self, profile: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash",
                str(VALIDATE_SCRIPT),
                self.run_id,
                "--profile",
                profile,
                "--exit-nonzero",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_smoke_profile_passes_q50_for_all_families(self) -> None:
        self._write_common_success_files()
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: true",
                    "  run_exdqlm_univar: true",
                    "  run_ndlm_main: true",
                    "fit:",
                    "  quantiles: [0.5]",
                    "  contract_checks:",
                    "    enabled: true",
                    "  diagnostics:",
                    "    enabled: true",
                    "validation:",
                    "  profile: smoke",
                ]
            )
            + "\n",
        )
        write_text(self.run_root / "fit" / "q=50" / "outputs" / "DISC_variables_50_exAL_synth_DISC.RData")
        write_text(self.run_root / "fit" / "exdqlm_univar" / "q=50" / "outputs" / "variables_50_exAL_synth_DISC_uni.RData")
        write_text(self.run_root / "fit" / "ndlm_main" / "outputs" / "DISC_variables_50_NDLM_synth_DISC.RData")
        write_json(self.run_root / "fit" / "contract_checks" / "exdqlm_univar" / "q=50" / "contract.json", {"status": "pass"})
        write_json(self.run_root / "fit" / "contract_checks" / "ndlm_main" / "contract.json", {"status": "pass"})
        write_json(self.run_root / "fit" / "diagnostics" / "exdqlm_univar" / "q=50" / "diag.json", {"status": "pass"})
        write_json(self.run_root / "fit" / "diagnostics" / "ndlm_main" / "diag.json", {"status": "pass"})

        result = self._run_validate("smoke")
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("RESULT=PASS", result.stdout)

    def test_production_profile_fails_when_only_q50_multivar_exists(self) -> None:
        self._write_common_success_files()
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: true",
                    "  run_exdqlm_univar: false",
                    "  run_ndlm_main: false",
                    "fit:",
                    "  quantiles: [0.5]",
                    "validation:",
                    "  profile: production",
                ]
            )
            + "\n",
        )
        write_text(self.run_root / "fit" / "q=50" / "outputs" / "DISC_variables_50_exAL_synth_DISC.RData")

        result = self._run_validate("production")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RESULT=FAIL", result.stdout)

    def test_production_profile_fails_if_univar_enabled_but_missing(self) -> None:
        self._write_common_success_files()
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: true",
                    "  run_exdqlm_univar: true",
                    "  run_ndlm_main: false",
                    "fit:",
                    "  quantiles: [0.05,0.20,0.35,0.50,0.65,0.80,0.95]",
                    "  contract_checks:",
                    "    enabled: false",
                    "  diagnostics:",
                    "    enabled: false",
                    "validation:",
                    "  profile: production",
                ]
            )
            + "\n",
        )
        for q in ("05", "20", "35", "50", "65", "80", "95"):
            write_text(self.run_root / "fit" / f"q={q}" / "outputs" / f"DISC_variables_{int(q)}_exAL_synth_DISC.RData")

        result = self._run_validate("production")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RESULT=FAIL", result.stdout)
        self.assertIn("family_check.univar_outputs=FAIL", result.stdout)

    def test_smoke_profile_fails_hard_on_malformed_resolved_config(self) -> None:
        self._write_common_success_files()
        write_text(self.run_root / "resolved_config.yaml", "models: [\n")

        result = self._run_validate("smoke")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            ("Failed to parse" in result.stderr) or ("ERROR:" in result.stderr),
            msg=result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
