from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")


class ConfigExtremeQuantileStabilizationTests(unittest.TestCase):
    def _resolve_config(self, yaml_text: str) -> dict[str, str]:
        with tempfile.TemporaryDirectory(prefix="ut_cfg_extreme_q_") as td:
            cfg_path = Path(td) / "cfg.yaml"
            cfg_path.write_text(yaml_text, encoding="utf-8")
            script = "\n".join(
                [
                    f'source("{REPO_ROOT / "R" / "unified" / "config.R"}")',
                    f"cfg <- unified_load_config('{cfg_path.as_posix()}', repo_root = '{REPO_ROOT.as_posix()}')",
                    "cat(sprintf('freeze_iters=%s\\n', cfg$fit$exdqlm_multivar$gamma_sigma$warmup_freeze_iters))",
                    "cat(sprintf('freeze_target=%s\\n', cfg$fit$exdqlm_multivar$gamma_sigma$freeze_target))",
                    "cat(sprintf('guard_refreeze_iters=%s\\n', cfg$fit$exdqlm_multivar$gamma_sigma$guard_refreeze_iters))",
                    "cat(sprintf('guard_enabled=%s\\n', if (isTRUE(cfg$fit$exdqlm_multivar$gamma_sigma$objective_guard$enabled)) 'true' else 'false'))",
                    "cat(sprintf('guard_fail_fast=%s\\n', if (isTRUE(cfg$fit$exdqlm_multivar$gamma_sigma$objective_guard$fail_fast)) 'true' else 'false'))",
                    "cat(sprintf('guard_log_failures=%s\\n', if (isTRUE(cfg$fit$exdqlm_multivar$gamma_sigma$objective_guard$log_failures)) 'true' else 'false'))",
                    "cat(sprintf('guard_mode=%s\\n', cfg$fit$exdqlm_multivar$gamma_sigma$objective_guard$mode))",
                    "cat(sprintf('guard_penalty=%s\\n', cfg$fit$exdqlm_multivar$gamma_sigma$objective_guard$penalty))",
                    "cat(sprintf('init_mode=%s\\n', cfg$fit$exdqlm_multivar$gamma_sigma$init$mode))",
                    "cat(sprintf('init_gamma=%s\\n', cfg$fit$exdqlm_multivar$gamma_sigma$init$gamma))",
                    "cat(sprintf('init_sigma_floor=%s\\n', cfg$fit$exdqlm_multivar$gamma_sigma$init$sigma_floor))",
                    "cat(sprintf('init_sigma_scale=%s\\n', cfg$fit$exdqlm_multivar$gamma_sigma$init$sigma_scale))",
                    "cat(sprintf('univar_freeze_iters=%s\\n', cfg$fit$exdqlm_univar$gamma_sigma$warmup_freeze_iters))",
                    "cat(sprintf('univar_freeze_target=%s\\n', cfg$fit$exdqlm_univar$gamma_sigma$freeze_target))",
                    "cat(sprintf('univar_guard_refreeze_iters=%s\\n', cfg$fit$exdqlm_univar$gamma_sigma$guard_refreeze_iters))",
                    "cat(sprintf('univar_guard_enabled=%s\\n', if (isTRUE(cfg$fit$exdqlm_univar$gamma_sigma$objective_guard$enabled)) 'true' else 'false'))",
                    "cat(sprintf('univar_guard_mode=%s\\n', cfg$fit$exdqlm_univar$gamma_sigma$objective_guard$mode))",
                    "cat(sprintf('univar_init_mode=%s\\n', cfg$fit$exdqlm_univar$gamma_sigma$init$mode))",
                ]
            )
            proc = subprocess.run(
                ["Rscript", "--vanilla", "-e", script],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        out: dict[str, str] = {}
        for line in proc.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
        return out

    def test_defaults_enable_adaptive_freeze_policy(self) -> None:
        cfg = textwrap.dedent(
            """
            config_version: 1
            stages:
              forecats: false
              data_prep_shared: false
              fit: false
              post: false
              validate: false
              report: false
            """
        )
        out = self._resolve_config(cfg)
        self.assertEqual(out["freeze_iters"], "20")
        self.assertEqual(out["freeze_target"], "gamma_sigma")
        self.assertEqual(out["guard_refreeze_iters"], "10")
        self.assertEqual(out["guard_enabled"], "true")
        self.assertEqual(out["guard_fail_fast"], "false")
        self.assertEqual(out["guard_log_failures"], "true")
        self.assertEqual(out["guard_mode"], "adaptive_freeze")
        self.assertEqual(out["init_mode"], "robust")
        self.assertEqual(out["univar_freeze_iters"], "20")
        self.assertEqual(out["univar_freeze_target"], "gamma_sigma")
        self.assertEqual(out["univar_guard_refreeze_iters"], "10")
        self.assertEqual(out["univar_guard_enabled"], "true")
        self.assertEqual(out["univar_guard_mode"], "adaptive_freeze")
        self.assertEqual(out["univar_init_mode"], "robust")

    def test_overrides_are_respected(self) -> None:
        cfg = textwrap.dedent(
            """
            config_version: 1
            stages:
              forecats: false
              data_prep_shared: false
              fit: false
              post: false
              validate: false
              report: false
            fit:
              exdqlm_multivar:
                gamma_sigma:
                  warmup_freeze_iters: 25
                  freeze_target: "states"
                  guard_refreeze_iters: 11
                  init:
                    mode: "robust"
                    gamma: 0.1
                    sigma_floor: 0.002
                    sigma_scale: 1.25
                  objective_guard:
                    enabled: true
                    fail_fast: true
                    log_failures: false
                    mode: "adaptive_freeze"
                    penalty: 12345
            """
        )
        out = self._resolve_config(cfg)
        self.assertEqual(out["freeze_iters"], "25")
        self.assertEqual(out["freeze_target"], "states")
        self.assertEqual(out["guard_refreeze_iters"], "11")
        self.assertEqual(out["guard_enabled"], "true")
        self.assertEqual(out["guard_fail_fast"], "true")
        self.assertEqual(out["guard_log_failures"], "false")
        self.assertEqual(out["guard_mode"], "adaptive_freeze")
        self.assertEqual(out["guard_penalty"], "12345")
        self.assertEqual(out["init_mode"], "robust")
        self.assertEqual(out["init_gamma"], "0.1")
        self.assertEqual(out["init_sigma_floor"], "0.002")
        self.assertEqual(out["init_sigma_scale"], "1.25")

    def test_negative_warmup_freeze_iters_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ut_cfg_extreme_q_bad_") as td:
            cfg_path = Path(td) / "cfg_bad.yaml"
            cfg_path.write_text(
                textwrap.dedent(
                    """
                    config_version: 1
                    stages:
                      forecats: false
                      data_prep_shared: false
                      fit: false
                      post: false
                      validate: false
                      report: false
                    fit:
                      exdqlm_multivar:
                        gamma_sigma:
                          warmup_freeze_iters: -1
                    """
                ),
                encoding="utf-8",
            )
            script = "\n".join(
                [
                    f'source("{REPO_ROOT / "R" / "unified" / "config.R"}")',
                    f"unified_load_config('{cfg_path.as_posix()}', repo_root = '{REPO_ROOT.as_posix()}')",
                    "cat('UNEXPECTED_PASS\\n')",
                ]
            )
            proc = subprocess.run(
                ["Rscript", "--vanilla", "-e", script],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(
            "fit.exdqlm_multivar.gamma_sigma.warmup_freeze_iters must be an integer >= 0",
            proc.stderr,
        )

    def test_invalid_freeze_target_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ut_cfg_extreme_q_bad_target_") as td:
            cfg_path = Path(td) / "cfg_bad_target.yaml"
            cfg_path.write_text(
                textwrap.dedent(
                    """
                    config_version: 1
                    stages:
                      forecats: false
                      data_prep_shared: false
                      fit: false
                      post: false
                      validate: false
                      report: false
                    fit:
                      exdqlm_multivar:
                        gamma_sigma:
                          freeze_target: "unknown_target"
                    """
                ),
                encoding="utf-8",
            )
            script = "\n".join(
                [
                    f'source("{REPO_ROOT / "R" / "unified" / "config.R"}")',
                    f"unified_load_config('{cfg_path.as_posix()}', repo_root = '{REPO_ROOT.as_posix()}')",
                    "cat('UNEXPECTED_PASS\\n')",
                ]
            )
            proc = subprocess.run(
                ["Rscript", "--vanilla", "-e", script],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(
            "fit.exdqlm_multivar.gamma_sigma.freeze_target must be one of: gamma_sigma, states",
            proc.stderr,
        )

    def test_invalid_univar_freeze_target_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ut_cfg_extreme_q_bad_univar_target_") as td:
            cfg_path = Path(td) / "cfg_bad_univar_target.yaml"
            cfg_path.write_text(
                textwrap.dedent(
                    """
                    config_version: 1
                    stages:
                      forecats: false
                      data_prep_shared: false
                      fit: false
                      post: false
                      validate: false
                      report: false
                    fit:
                      exdqlm_univar:
                        gamma_sigma:
                          freeze_target: "unknown_target"
                    """
                ),
                encoding="utf-8",
            )
            script = "\n".join(
                [
                    f'source("{REPO_ROOT / "R" / "unified" / "config.R"}")',
                    f"unified_load_config('{cfg_path.as_posix()}', repo_root = '{REPO_ROOT.as_posix()}')",
                    "cat('UNEXPECTED_PASS\\n')",
                ]
            )
            proc = subprocess.run(
                ["Rscript", "--vanilla", "-e", script],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(
            "fit.exdqlm_univar.gamma_sigma.freeze_target must be one of: gamma_sigma, states",
            proc.stderr,
        )


if __name__ == "__main__":
    unittest.main()
