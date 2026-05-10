from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_20260510.template.yaml'
BUILDER = ROOT / 'scripts' / 'build_he2_bayesian_publication_relaunch_configs.py'


class HE2PublicationRelaunchBuilderSelectionTests(unittest.TestCase):
    def _run_builder(self, *extra_args: str) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        artifact_root = tmp_path / 'artifact_root'
        matrix_dir = tmp_path / 'matrix_dir'
        config_output_dir = tmp_path / 'configs'
        cmd = [
            'python3', str(BUILDER),
            '--config', str(TEMPLATE),
            '--artifact-root', str(artifact_root),
            '--matrix-dir', str(matrix_dir),
            '--config-output-dir', str(config_output_dir),
            *extra_args,
        ]
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        return proc, matrix_dir, config_output_dir, artifact_root

    def test_single_label_cutoff_quantile_subset_builds_expected_outputs(self) -> None:
        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--cutoffs', '20210123',
            '--manuscript-labels', 'exAL-M-T1',
            '--quantiles', '0.05',
            '--fit-parallel-workers', '1',
            '--mc-cores', '1',
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8') as handle:
            plan_rows = list(csv.DictReader(handle))
        self.assertEqual(len(plan_rows), 1)
        self.assertEqual(plan_rows[0]['cutoff'], '20210123')
        self.assertEqual(plan_rows[0]['manuscript_label'], 'exAL-M-T1')
        self.assertEqual(plan_rows[0]['active_quantiles'], '05')

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 1)
        self.assertEqual(frozen_rows[0]['active_quantiles'], '05')
        self.assertEqual(frozen_rows[0]['fit_parallel_workers'], '1')
        self.assertEqual(frozen_rows[0]['run_mc_cores'], '1')

        with (matrix_dir / 'cutoff_bundle_audit.csv').open('r', encoding='utf-8') as handle:
            cutoff_rows = list(csv.DictReader(handle))
        self.assertEqual(len(cutoff_rows), 1)
        self.assertEqual(cutoff_rows[0]['cutoff'], '20210123')
        self.assertEqual(cutoff_rows[0]['retros_start'], '1987-05-29')
        self.assertEqual(cutoff_rows[0]['gdpc_alias_start'], '1987-05-29')

        config_paths = list(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 1)
        payload = yaml.safe_load(config_paths[0].read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['fit']['quantiles'], [0.05])
        self.assertEqual(payload['fit']['parallel']['workers'], 1)
        self.assertEqual(payload['run']['threads']['mc_cores'], 1)
        self.assertEqual(payload['debug_he2_publication_relaunch']['model_class'], 'quantile_multivariate')

    def test_model_class_filter_returns_three_ndlm_rows_for_one_cutoff(self) -> None:
        proc, matrix_dir, _config_output_dir, _artifact_root = self._run_builder(
            '--cutoffs', '20210123',
            '--model-classes', 'ndlm',
            '--profile', 'single_core_full',
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        with (matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8') as handle:
            plan_rows = list(csv.DictReader(handle))
        self.assertEqual(len(plan_rows), 3)
        self.assertEqual(sorted({row['family_id'] for row in plan_rows}), ['ndlm_main_drop', 'ndlm_main_keep', 'ndlm_univar_keep'])
        metadata = yaml.safe_load((matrix_dir / 'matrix_metadata.yaml').read_text(encoding='utf-8')) or {}
        self.assertEqual(metadata['request']['profile'], 'single_core_full')
        self.assertEqual(metadata['request']['selection']['model_classes'], ['ndlm'])
        self.assertEqual(metadata['request']['resources']['fit_parallel_workers'], 1)
        self.assertEqual(metadata['request']['resources']['mc_cores'], 1)


if __name__ == '__main__':
    unittest.main()
