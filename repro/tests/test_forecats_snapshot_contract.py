from __future__ import annotations

import csv
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
RUNS_ROOT = REPO_ROOT / "repro" / "runs"


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def _date_rows(n: int) -> list[str]:
    return [f"2022-12-{i+1:02d}" for i in range(n)]


class ForecatsSnapshotContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run_id = f"ut_snapshot_{uuid.uuid4().hex[:10]}"
        self.run_root = RUNS_ROOT / self.run_id
        self.bundle_root = self.run_root / "bundle_existing"
        self.params_path = self.run_root / "inputs_src" / "parameters.txt"
        self.cfg_retros = self.run_root / "inputs_src" / "retros_configured.csv"
        self.cfg_nws = self.run_root / "inputs_src" / "nws_configured.csv"
        self.cfg_glofas = self.run_root / "inputs_src" / "glofas_configured.csv"
        self.run_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.run_root.exists():
            shutil.rmtree(self.run_root, ignore_errors=True)

    def _prepare_inputs(self) -> None:
        self.params_path.parent.mkdir(parents=True, exist_ok=True)
        self.params_path.write_text("alpha=1\n", encoding="utf-8")

        dates20 = _date_rows(20)
        _write_csv(
            self.cfg_retros,
            ["Date", "USGS", "GloFAS", "NWS3.0"],
            [[d, i + 1, i + 2, i + 3] for i, d in enumerate(dates20)],
        )
        _write_csv(
            self.cfg_nws,
            ["Date", "nws_1", "nws_2"],
            [[d, i + 0.1, i + 0.2] for i, d in enumerate(_date_rows(12))],
        )
        _write_csv(
            self.cfg_glofas,
            ["Date", "g1", "g2"],
            [[d, i + 0.3, i + 0.4] for i, d in enumerate(_date_rows(12))],
        )

        (self.bundle_root / "meta.yaml").parent.mkdir(parents=True, exist_ok=True)
        (self.bundle_root / "meta.yaml").write_text("bundle: test\n", encoding="utf-8")
        _write_csv(
            self.bundle_root / "inputs" / "retros_daily.csv",
            ["Date", "USGS", "GloFAS", "NWS3.0"],
            [[d, i + 10, i + 11, i + 12] for i, d in enumerate(dates20)],
        )
        _write_csv(
            self.bundle_root / "inputs" / "nws_weighted_daily.csv",
            ["Date", "nws_w_1", "nws_w_2"],
            [[d, i + 1.1, i + 1.2] for i, d in enumerate(_date_rows(12))],
        )

        glofas_header = ["Date"] + [f"member_{i:02d}" for i in range(1, 21)]
        glofas_rows = []
        for i, d in enumerate(dates20):
            glofas_rows.append([d] + [i + j + 0.01 for j in range(20)])
        _write_csv(self.bundle_root / "inputs" / "glofas_members.csv", glofas_header, glofas_rows)
        _write_csv(self.bundle_root / "inputs" / "glofas_weighted_daily.csv", glofas_header, glofas_rows)

        _write_csv(
            self.bundle_root / "inputs" / "nws_members.csv",
            ["Date", "member_01", "member_02"],
            [[d, i + 2.1, i + 2.2] for i, d in enumerate(_date_rows(12))],
        )

    def test_snapshot_bundle_records_input_snapshot_and_fit_source_map_evidence(self) -> None:
        self._prepare_inputs()
        run_root_str = str(self.run_root).replace("\\", "/")
        repo_root_str = str(REPO_ROOT).replace("\\", "/")

        script = "\n".join(
            [
                f'source("{REPO_ROOT / "R" / "unified" / "utils_hash.R"}")',
                f'source("{REPO_ROOT / "R" / "unified" / "config.R"}")',
                f'source("{REPO_ROOT / "R" / "unified" / "manifest.R"}")',
                f'source("{REPO_ROOT / "R" / "unified" / "inputs_shared_validate.R"}")',
                f'source("{REPO_ROOT / "R" / "unified" / "stages" / "stage_forecats.R"}")',
                f'source("{REPO_ROOT / "R" / "unified" / "stages" / "stage_data_prep_shared.R"}")',
                "cfg <- unified_config_defaults()",
                f"cfg$run$run_id <- '{self.run_id}'",
                "cfg$stages$forecats <- TRUE",
                "cfg$stages$data_prep_shared <- TRUE",
                "cfg$inputs$forecats$mode <- 'use_existing'",
                f"cfg$inputs$forecats$existing_bundle_path <- '{self.bundle_root}'",
                "cfg$inputs$forecats$snapshot$enabled <- TRUE",
                "cfg$inputs$shared$prefer_forecats_snapshot <- TRUE",
                f"cfg$inputs$fit$parameters_path <- '{self.params_path}'",
                f"cfg$inputs$fit$retros_path <- '{self.cfg_retros}'",
                f"cfg$inputs$fit$nws_forecast_path <- '{self.cfg_nws}'",
                f"cfg$inputs$fit$glofas_forecast_path <- '{self.cfg_glofas}'",
                "repro_record <- list(",
                "  fit_rng = c('Mersenne-Twister', 'Inversion', 'Rejection'),",
                "  post_rng = c('Mersenne-Twister', 'Inversion', 'Rejection')",
                ")",
                "manifest <- unified_manifest_init(",
                "  cfg = cfg,",
                f"  run_id = '{self.run_id}',",
                f"  run_root = '{run_root_str}',",
                f"  repo_root = '{repo_root_str}',",
                "  repro_record = repro_record",
                ")",
                f"manifest <- unified_stage_forecats(cfg, run_root = '{run_root_str}', repo_root = '{repo_root_str}', manifest = manifest)$manifest",
                f"manifest <- unified_stage_data_prep_shared(cfg, run_root = '{run_root_str}', repo_root = '{repo_root_str}', manifest = manifest)$manifest",
                f"shared_check <- unified_validate_required_shared_inputs(run_root = '{run_root_str}', stage_name = 'fit', manifest = manifest, enabled_models = cfg$models)",
                "input_snapshot_count <- sum(vapply(manifest$artifacts, function(a) identical(a$role, 'input_snapshot'), logical(1)))",
                f"source_map_path <- file.path('{run_root_str}', 'inputs', 'shared', 'source_map.txt')",
                "source_map_lines <- if (file.exists(source_map_path)) readLines(source_map_path) else character(0)",
                "glofas_origin <- source_map_lines[grepl('^source.glofas_origin=', source_map_lines)]",
                "nws_origin <- source_map_lines[grepl('^source.nws_origin=', source_map_lines)]",
                f"fit_source_log <- file.path('{run_root_str}', 'fit', 'logs', 'shared_input_source_map.log')",
                "cat(sprintf('input_snapshot_count=%d\\n', input_snapshot_count))",
                "cat(sprintf('source_map_exists=%s\\n', if (file.exists(source_map_path)) 'true' else 'false'))",
                "cat(sprintf('snapshot_source_map_exists=%s\\n', if (file.exists(shared_check$snapshot_source_map_path)) 'true' else 'false'))",
                "cat(sprintf('fit_source_log_exists=%s\\n', if (file.exists(fit_source_log)) 'true' else 'false'))",
                "cat(sprintf('source_glofas_origin=%s\\n', if (length(glofas_origin) > 0) glofas_origin[[1]] else 'missing'))",
                "cat(sprintf('source_nws_origin=%s\\n', if (length(nws_origin) > 0) nws_origin[[1]] else 'missing'))",
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
        self.assertGreater(int(out["input_snapshot_count"]), 0)
        self.assertEqual(out["source_map_exists"], "true")
        self.assertEqual(out["snapshot_source_map_exists"], "true")
        self.assertEqual(out["fit_source_log_exists"], "true")
        self.assertEqual(out["source_glofas_origin"], "source.glofas_origin=snapshot")
        self.assertEqual(out["source_nws_origin"], "source.nws_origin=snapshot")

        fit_log = (self.run_root / "fit" / "logs" / "shared_input_source_map.log").read_text(encoding="utf-8")
        self.assertIn("shared_source_map_path=", fit_log)
        self.assertIn("snapshot_source_map_path=", fit_log)


if __name__ == "__main__":
    unittest.main()
