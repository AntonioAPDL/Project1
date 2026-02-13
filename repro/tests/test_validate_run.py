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

    def _write_common_success_files(self, validator_profile: str | None = None) -> None:
        validation_lines = [
            "validation:",
            "  status: pass",
        ]
        if validator_profile:
            validation_lines.append(f"  validator_profile: {validator_profile}")
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
                    *validation_lines,
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

    def _write_three_quantile_full_family_artifacts(self, include_validation_profile: bool = True) -> None:
        config_lines = [
            "models:",
            "  run_exdqlm_multivar: true",
            "  run_exdqlm_univar: true",
            "  run_ndlm_main: true",
            "fit:",
            "  quantiles: [0.05, 0.5, 0.95]",
            "  contract_checks:",
            "    enabled: true",
            "  diagnostics:",
            "    enabled: true",
        ]
        if include_validation_profile:
            config_lines.extend(
                [
                    "validation:",
                    "  profile: production_proof",
                ]
            )
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(config_lines) + "\n",
        )
        for q in ("5", "50", "95"):
            write_text(self.run_root / "fit" / f"q={int(q):02d}" / "outputs" / f"DISC_variables_{q}_exAL_synth_DISC.RData")
        for qlab in ("05", "50", "95"):
            write_text(
                self.run_root / "fit" / "exdqlm_univar" / f"q={qlab}" / "outputs" / f"variables_{qlab}_exAL_synth_DISC_uni.RData"
            )
            write_json(
                self.run_root / "fit" / "contract_checks" / "exdqlm_univar" / f"q={qlab}" / "contract.json",
                {"status": "pass"},
            )
            write_json(
                self.run_root / "fit" / "diagnostics" / "exdqlm_univar" / f"q={qlab}" / "diag.json",
                {"status": "pass"},
            )
        write_text(self.run_root / "fit" / "ndlm_main" / "outputs" / "DISC_variables_50_NDLM_synth_DISC.RData")
        write_json(self.run_root / "fit" / "contract_checks" / "ndlm_main" / "contract.json", {"status": "pass"})
        write_json(self.run_root / "fit" / "diagnostics" / "ndlm_main" / "diag.json", {"status": "pass"})

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

    def test_production_proof_profile_passes_config_declared_three_quantiles(self) -> None:
        self._write_common_success_files()
        self._write_three_quantile_full_family_artifacts()

        result = self._run_validate("production_proof")
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("RESULT=PASS", result.stdout)
        self.assertIn("quantile_rule=config_declared_quantiles_enforced", result.stdout)
        self.assertIn("quantile_outputs=3/3", result.stdout)

    def test_production_profile_still_fails_for_three_quantile_setup(self) -> None:
        self._write_common_success_files()
        self._write_three_quantile_full_family_artifacts()

        result = self._run_validate("production")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RESULT=FAIL", result.stdout)
        self.assertIn("quantile_rule=canonical_7_quantiles_enforced", result.stdout)
        self.assertIn("missing_quantiles=20,35,65,80", result.stdout)

    def test_auto_profile_prefers_manifest_validator_profile(self) -> None:
        self._write_common_success_files(validator_profile="production_proof")
        self._write_three_quantile_full_family_artifacts(include_validation_profile=False)

        result = self._run_validate("auto")
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("RESULT=PASS", result.stdout)
        self.assertIn("profile_resolved=production_proof", result.stdout)
        self.assertIn("profile_source=manifest", result.stdout)

    def test_auto_profile_prefers_manifest_over_conflicting_resolved_config(self) -> None:
        self._write_common_success_files(validator_profile="production_proof")
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: true",
                    "  run_exdqlm_univar: true",
                    "  run_ndlm_main: true",
                    "fit:",
                    "  quantiles: [0.05, 0.5, 0.95]",
                    "  contract_checks:",
                    "    enabled: true",
                    "  diagnostics:",
                    "    enabled: true",
                    "validation:",
                    "  profile: production",
                ]
            )
            + "\n",
        )
        for q in ("5", "50", "95"):
            write_text(self.run_root / "fit" / f"q={int(q):02d}" / "outputs" / f"DISC_variables_{q}_exAL_synth_DISC.RData")
        for qlab in ("05", "50", "95"):
            write_text(
                self.run_root / "fit" / "exdqlm_univar" / f"q={qlab}" / "outputs" / f"variables_{qlab}_exAL_synth_DISC_uni.RData"
            )
            write_json(
                self.run_root / "fit" / "contract_checks" / "exdqlm_univar" / f"q={qlab}" / "contract.json",
                {"status": "pass"},
            )
            write_json(
                self.run_root / "fit" / "diagnostics" / "exdqlm_univar" / f"q={qlab}" / "diag.json",
                {"status": "pass"},
            )
        write_text(self.run_root / "fit" / "ndlm_main" / "outputs" / "DISC_variables_50_NDLM_synth_DISC.RData")
        write_json(self.run_root / "fit" / "contract_checks" / "ndlm_main" / "contract.json", {"status": "pass"})
        write_json(self.run_root / "fit" / "diagnostics" / "ndlm_main" / "diag.json", {"status": "pass"})

        result = self._run_validate("auto")
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("RESULT=PASS", result.stdout)
        self.assertIn("profile_resolved=production_proof", result.stdout)
        self.assertIn("profile_source=manifest", result.stdout)
        self.assertIn("quantile_rule=config_declared_quantiles_enforced", result.stdout)

    def test_auto_profile_falls_back_to_resolved_config_profile(self) -> None:
        self._write_common_success_files()
        self._write_three_quantile_full_family_artifacts(include_validation_profile=True)

        result = self._run_validate("auto")
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("RESULT=PASS", result.stdout)
        self.assertIn("profile_resolved=production_proof", result.stdout)
        self.assertIn("profile_source=resolved_config", result.stdout)

    def test_auto_profile_defaults_to_production_when_not_declared(self) -> None:
        self._write_common_success_files()
        self._write_three_quantile_full_family_artifacts(include_validation_profile=False)

        result = self._run_validate("auto")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RESULT=FAIL", result.stdout)
        self.assertIn("profile_resolved=production", result.stdout)
        self.assertIn("profile_source=default", result.stdout)
        self.assertIn("quantile_rule=canonical_7_quantiles_enforced", result.stdout)

    def test_production_proof_still_enforces_compare_report_gate(self) -> None:
        self._write_common_success_files()
        self._write_three_quantile_full_family_artifacts()
        (self.run_root / "validate" / "compare_report.json").unlink()

        result = self._run_validate("production_proof")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RESULT=FAIL", result.stdout)
        self.assertIn("compare_report_exists=false", result.stdout)

    def test_smoke_profile_accepts_neutral_ndlm_output_name(self) -> None:
        self._write_common_success_files()
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: false",
                    "  run_exdqlm_univar: false",
                    "  run_ndlm_main: true",
                    "fit:",
                    "  quantiles: [0.5]",
                    "validation:",
                    "  profile: smoke",
                ]
            )
            + "\n",
        )
        write_text(self.run_root / "fit" / "ndlm_main" / "outputs" / "ndlm_main_state.RData")

        result = self._run_validate("smoke")
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("RESULT=PASS", result.stdout)

    def test_smoke_profile_accepts_single_digit_q05_univar_filename(self) -> None:
        self._write_common_success_files()
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: false",
                    "  run_exdqlm_univar: true",
                    "  run_ndlm_main: false",
                    "fit:",
                    "  quantiles: [0.05]",
                    "validation:",
                    "  profile: smoke",
                ]
            )
            + "\n",
        )
        write_text(
            self.run_root
            / "fit"
            / "exdqlm_univar"
            / "q=05"
            / "outputs"
            / "variables_5_exAL_synth_DISC_uni.RData"
        )

        result = self._run_validate("smoke")
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("RESULT=PASS", result.stdout)

    def test_stage_report_univar_quantile_parsing_handles_single_digit_filenames(self) -> None:
        script = (
            "source('R/unified/stages/stage_report.R'); "
            "p1 <- 'fit/exdqlm_univar/q=05/outputs/variables_5_exAL_synth_DISC_uni.RData'; "
            "p2 <- 'fit/exdqlm_univar/q=05/outputs/variables_20_exAL_synth_DISC_uni.RData'; "
            "p3 <- 'fit/exdqlm_univar/legacy/outputs/variables_35_exAL_synth_DISC_uni.RData'; "
            "o1 <- unified_extract_artifact_quantiles(c(p1, p3), family='univar'); "
            "o2 <- unified_extract_artifact_quantiles(c(p2), family='univar'); "
            "cat(sprintf('o1=%s\\n', paste(o1, collapse=','))); "
            "cat(sprintf('o2=%s\\n', paste(o2, collapse=','))); "
            "cat(sprintf('class=%s\\n', class(o1)[1]));"
        )
        result = subprocess.run(
            ["Rscript", "-e", script],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("o1=5,35", result.stdout)
        self.assertIn("o2=5", result.stdout)  # Prefer q=<QQ> directory over filename token.
        self.assertIn("class=integer", result.stdout)

    def test_manifest_init_sets_validator_profile_from_config(self) -> None:
        script = (
            "source('R/unified/utils_hash.R'); "
            "source('R/unified/config.R'); "
            "source('R/unified/manifest.R'); "
            "cfg <- unified_config_defaults(); "
            "cfg$validation$profile <- 'production_proof'; "
            "repro_record <- list(fit_rng = c('Mersenne-Twister', 'Inversion', 'Rejection'), "
            "post_rng = c('Mersenne-Twister', 'Inversion', 'Rejection')); "
            "m <- unified_manifest_init(cfg, run_id='ut_manifest', run_root=tempdir(), "
            f"repo_root='{REPO_ROOT.as_posix()}', repro_record=repro_record); "
            "cat(sprintf('validator_profile=%s\\n', m$validation$validator_profile)); "
            "cat(sprintf('validation_status=%s\\n', m$validation$status));"
        )
        result = subprocess.run(
            ["Rscript", "-e", script],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("validator_profile=production_proof", result.stdout)
        self.assertIn("validation_status=pending", result.stdout)

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

    def test_production_proof_passes_with_pattern_ndlm_filename_when_required(self) -> None:
        self._write_common_success_files()
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: false",
                    "  run_exdqlm_univar: false",
                    "  run_ndlm_main: true",
                    "fit:",
                    "  quantiles: [0.5]",
                    "validation:",
                    "  profile: production_proof",
                ]
            )
            + "\n",
        )
        write_text(self.run_root / "fit" / "ndlm_main" / "outputs" / "ndlm_main_20260213.RData")

        result = self._run_validate("production_proof")
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("RESULT=PASS", result.stdout)
        self.assertIn("require_ndlm=true", result.stdout)
        self.assertIn("ndlm_accepted_output_names=", result.stdout)

    def test_production_proof_fails_if_ndlm_enabled_but_missing_output(self) -> None:
        self._write_common_success_files()
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: false",
                    "  run_exdqlm_univar: false",
                    "  run_ndlm_main: true",
                    "fit:",
                    "  quantiles: [0.5]",
                    "validation:",
                    "  profile: production_proof",
                ]
            )
            + "\n",
        )
        (self.run_root / "fit" / "ndlm_main" / "outputs").mkdir(parents=True, exist_ok=True)

        result = self._run_validate("production_proof")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RESULT=FAIL", result.stdout)
        self.assertIn("require_ndlm=true", result.stdout)
        self.assertIn("family_check.ndlm_output=FAIL", result.stdout)
        self.assertIn("ndlm_output_path=<not-required-or-missing>", result.stdout)

    def test_production_proof_fails_cleanly_when_ndlm_outputs_dir_absent(self) -> None:
        self._write_common_success_files()
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: false",
                    "  run_exdqlm_univar: false",
                    "  run_ndlm_main: true",
                    "fit:",
                    "  quantiles: [0.5]",
                    "validation:",
                    "  profile: production_proof",
                ]
            )
            + "\n",
        )
        # Intentionally do not create fit/ndlm_main/outputs to verify clean FAIL reporting.

        result = self._run_validate("production_proof")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RESULT=FAIL", result.stdout)
        self.assertIn("require_ndlm=true", result.stdout)
        self.assertIn("family_check.ndlm_output=FAIL", result.stdout)
        self.assertIn("ndlm_output_path=<not-required-or-missing>", result.stdout)

    def test_validator_reports_shared_snapshot_source_map_paths(self) -> None:
        self._write_common_success_files()
        write_text(
            self.run_root / "resolved_config.yaml",
            "\n".join(
                [
                    "models:",
                    "  run_exdqlm_multivar: false",
                    "  run_exdqlm_univar: false",
                    "  run_ndlm_main: false",
                    "fit:",
                    "  quantiles: [0.5]",
                    "validation:",
                    "  profile: smoke",
                ]
            )
            + "\n",
        )
        write_text(self.run_root / "inputs" / "shared" / "source_map.txt", "source_mode=forecats_snapshot_mixed\n")
        write_text(
            self.run_root / "inputs" / "shared" / "forecats_bundle" / "snapshot_source_map.txt",
            "mode=build\n",
        )
        (self.run_root / "fit").mkdir(parents=True, exist_ok=True)

        result = self._run_validate("smoke")
        self.assertEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        self.assertIn("shared_source_map_exists=true", result.stdout)
        self.assertIn("snapshot_source_map_exists=true", result.stdout)
        self.assertIn("shared_source_map_path=", result.stdout)
        self.assertIn("snapshot_source_map_path=", result.stdout)

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
