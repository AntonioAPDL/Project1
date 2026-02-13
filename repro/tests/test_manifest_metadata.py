from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")


class ManifestMetadataTests(unittest.TestCase):
    def _probe_manifest(self, extra_assignments: str = "") -> dict[str, str]:
        script = "\n".join(
            [
                f'source("{REPO_ROOT / "R" / "unified" / "config.R"}")',
                f'source("{REPO_ROOT / "R" / "unified" / "manifest.R"}")',
                "cfg <- unified_config_defaults()",
                "cfg$models$run_exdqlm_multivar <- TRUE",
                "cfg$models$run_exdqlm_univar <- TRUE",
                "cfg$models$run_ndlm_main <- TRUE",
                "cfg$models$exdqlm_univar$implementation_mode <- 'theory_aligned'",
                "cfg$models$ndlm_main$implementation_mode <- 'legacy_bridge'",
                extra_assignments,
                "manifest <- unified_manifest_init(",
                "  cfg = cfg,",
                "  run_id = 'ut_manifest_meta',",
                "  run_root = '/tmp/ut_manifest_meta',",
                f"  repo_root = '{REPO_ROOT}',",
                "  repro_record = list(",
                "    fit_rng = c('Mersenne-Twister', 'Inversion', 'Rejection'),",
                "    post_rng = c('Mersenne-Twister', 'Inversion', 'Rejection')",
                "  )",
                ")",
                "as_word <- function(x) if (isTRUE(x)) 'true' else 'false'",
                "cat(sprintf('multivar.enabled=%s\\n', as_word(manifest$families$exdqlm_multivar$enabled)))",
                "cat(sprintf('multivar.implementation_mode=%s\\n', manifest$families$exdqlm_multivar$implementation_mode))",
                "cat(sprintf('multivar.authoritative=%s\\n', as_word(manifest$families$exdqlm_multivar$authoritative)))",
                "cat(sprintf('univar.enabled=%s\\n', as_word(manifest$families$exdqlm_univar$enabled)))",
                "cat(sprintf('univar.implementation_mode=%s\\n', manifest$families$exdqlm_univar$implementation_mode))",
                "cat(sprintf('univar.authoritative=%s\\n', as_word(manifest$families$exdqlm_univar$authoritative)))",
                "cat(sprintf('ndlm.enabled=%s\\n', as_word(manifest$families$ndlm_main$enabled)))",
                "cat(sprintf('ndlm.implementation_mode=%s\\n', manifest$families$ndlm_main$implementation_mode))",
                "cat(sprintf('ndlm.authoritative=%s\\n', as_word(manifest$families$ndlm_main$authoritative)))",
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

    def test_family_authoritative_defaults(self) -> None:
        out = self._probe_manifest()
        self.assertEqual(out["multivar.enabled"], "true")
        self.assertEqual(out["multivar.implementation_mode"], "legacy_bridge")
        self.assertEqual(out["multivar.authoritative"], "true")
        self.assertEqual(out["univar.enabled"], "true")
        self.assertEqual(out["univar.implementation_mode"], "theory_aligned")
        self.assertEqual(out["univar.authoritative"], "false")
        self.assertEqual(out["ndlm.enabled"], "true")
        self.assertEqual(out["ndlm.implementation_mode"], "legacy_bridge")
        self.assertEqual(out["ndlm.authoritative"], "false")

    def test_family_authoritative_explicit_overrides(self) -> None:
        out = self._probe_manifest(
            extra_assignments="\n".join(
                [
                    "cfg$models$exdqlm_multivar$implementation_mode <- 'theory_aligned'",
                    "cfg$models$exdqlm_multivar$authoritative <- FALSE",
                    "cfg$models$exdqlm_univar$authoritative <- TRUE",
                    "cfg$models$ndlm_main$authoritative <- TRUE",
                ]
            )
        )
        self.assertEqual(out["multivar.implementation_mode"], "theory_aligned")
        self.assertEqual(out["multivar.authoritative"], "false")
        self.assertEqual(out["univar.authoritative"], "true")
        self.assertEqual(out["ndlm.authoritative"], "true")


if __name__ == "__main__":
    unittest.main()
