from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")


class ConfigImplementationModeDefaultsTests(unittest.TestCase):
    def _resolve_config(self, yaml_text: str) -> dict[str, str]:
        with tempfile.TemporaryDirectory(prefix="ut_cfg_modes_") as td:
            cfg_path = Path(td) / "cfg.yaml"
            cfg_path.write_text(yaml_text, encoding="utf-8")
            script = "\n".join(
                [
                    f'source("{REPO_ROOT / "R" / "unified" / "config.R"}")',
                    f"cfg <- unified_load_config('{cfg_path.as_posix()}', repo_root = '{REPO_ROOT.as_posix()}')",
                    "cat(sprintf('run_univar=%s\\n', if (isTRUE(cfg$models$run_exdqlm_univar)) 'true' else 'false'))",
                    "cat(sprintf('run_ndlm=%s\\n', if (isTRUE(cfg$models$run_ndlm_main)) 'true' else 'false'))",
                    "cat(sprintf('univar_mode=%s\\n', cfg$models$exdqlm_univar$implementation_mode))",
                    "cat(sprintf('ndlm_mode=%s\\n', cfg$models$ndlm_main$implementation_mode))",
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

    def test_defaults_theory_modes_while_families_disabled(self) -> None:
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
        self.assertEqual(out["run_univar"], "false")
        self.assertEqual(out["run_ndlm"], "false")
        self.assertEqual(out["univar_mode"], "theory_aligned")
        self.assertEqual(out["ndlm_mode"], "theory_aligned")

    def test_legacy_overrides_are_respected(self) -> None:
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
            models:
              exdqlm_univar:
                implementation_mode: legacy_bridge
              ndlm_main:
                implementation_mode: legacy_bridge
            """
        )
        out = self._resolve_config(cfg)
        self.assertEqual(out["univar_mode"], "legacy_bridge")
        self.assertEqual(out["ndlm_mode"], "legacy_bridge")


if __name__ == "__main__":
    unittest.main()
