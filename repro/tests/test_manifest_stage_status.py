from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")


class ManifestStageStatusTests(unittest.TestCase):
    def test_stage_status_helpers_emit_pass_skip_fail_shapes(self) -> None:
        script = "\n".join(
            [
                f'source("{REPO_ROOT / "R" / "unified" / "config.R"}")',
                f'source("{REPO_ROOT / "R" / "unified" / "manifest.R"}")',
                "cfg <- unified_config_defaults()",
                "repro_record <- list(",
                "  fit_rng = c('Mersenne-Twister', 'Inversion', 'Rejection'),",
                "  post_rng = c('Mersenne-Twister', 'Inversion', 'Rejection')",
                ")",
                "manifest <- unified_manifest_init(",
                "  cfg = cfg,",
                "  run_id = 'ut_stage_status',",
                "  run_root = '/tmp/ut_stage_status',",
                f"  repo_root = '{REPO_ROOT}',",
                "  repro_record = repro_record",
                ")",
                "manifest <- unified_manifest_stage_mark_skip(manifest, 'forecats', log_path='skip.log')",
                "manifest <- unified_manifest_stage_mark_start(manifest, 'fit', log_path='fit.log')",
                "manifest <- unified_manifest_stage_mark_pass(manifest, 'fit', log_path='fit.log')",
                "manifest <- unified_manifest_stage_mark_fail(manifest, 'post', log_path='post.log')",
                "as_word <- function(x) if (isTRUE(x)) 'true' else 'false'",
                "cat(sprintf('forecats.status=%s\\n', manifest$stages$forecats$status))",
                "cat(sprintf('forecats.started_is_null=%s\\n', as_word(is.null(manifest$stages$forecats$started_at_utc))))",
                "cat(sprintf('fit.status=%s\\n', manifest$stages$fit$status))",
                "cat(sprintf('fit.started_is_null=%s\\n', as_word(is.null(manifest$stages$fit$started_at_utc))))",
                "cat(sprintf('fit.finished_is_null=%s\\n', as_word(is.null(manifest$stages$fit$finished_at_utc))))",
                "cat(sprintf('post.status=%s\\n', manifest$stages$post$status))",
                "cat(sprintf('post.finished_is_null=%s\\n', as_word(is.null(manifest$stages$post$finished_at_utc))))",
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
        out = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in proc.stdout.splitlines() if "=" in line}
        self.assertEqual(out["forecats.status"], "skip")
        self.assertEqual(out["forecats.started_is_null"], "true")
        self.assertEqual(out["fit.status"], "pass")
        self.assertEqual(out["fit.started_is_null"], "false")
        self.assertEqual(out["fit.finished_is_null"], "false")
        self.assertEqual(out["post.status"], "fail")
        self.assertEqual(out["post.finished_is_null"], "true")


if __name__ == "__main__":
    unittest.main()
