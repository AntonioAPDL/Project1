from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_20260510.template.yaml'
ALL_CUTOFFS_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml'
PHASE2_DIAGNOSTIC_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.template.yaml'
PHASE2_DIAGNOSTIC_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.yaml'
PROOF_PROMOTION_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_remaining_cutoffs_proof_promotion_20260515.yaml'
Q50_20221225_STATEFREEZE_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_20221225_q50_statefreeze_diagnostic_20260515.yaml'
Q50_20221225_PROOF_PROMOTION_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_20221225_q50_proof_promotion_20260515.yaml'
Q50_20221225_STATEFREEZE_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_q50_statefreeze_diagnostic_20260515.template.yaml'
WAVE_A_NDLM_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml'
WAVE_A_NDLM_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'he2_wave_a_ndlm_remaining_families_20260516.yaml'
BUILDER = ROOT / 'scripts' / 'build_he2_bayesian_publication_relaunch_configs.py'


class HE2PublicationRelaunchBuilderSelectionTests(unittest.TestCase):
    def _run_builder(self, *extra_args: str, template: Path | None = None) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        artifact_root = tmp_path / 'artifact_root'
        matrix_dir = tmp_path / 'matrix_dir'
        config_output_dir = tmp_path / 'configs'
        cmd = [
            'python3', str(BUILDER),
            '--config', str(template or TEMPLATE),
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
        self.assertEqual(payload['scale_contract']['legacy_fit_input_scale'], 'log1p_cms')
        self.assertEqual(payload['scale_contract']['analysis_scale_fit_internal'], 'log1p_cms')
        self.assertEqual(payload['scale_contract']['analysis_scale_post_internal'], 'log1p_cms')

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

    def test_quantile_family_defaults_to_one_worker_per_active_quantile(self) -> None:
        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--cutoffs', '20210123',
            '--families', 'exdqlm_multivar_keep',
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 1)
        self.assertEqual(frozen_rows[0]['family'], 'exdqlm_multivar_keep')
        self.assertEqual(frozen_rows[0]['active_quantile_count'], '7')
        self.assertEqual(frozen_rows[0]['fit_parallel_workers'], '7')
        self.assertEqual(frozen_rows[0]['run_mc_cores'], '7')

        config_paths = list(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 1)
        payload = yaml.safe_load(config_paths[0].read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['fit']['parallel']['workers'], 7)
        self.assertEqual(payload['run']['threads']['mc_cores'], 7)
        self.assertEqual(payload['debug_he2_publication_relaunch']['fit_parallel_workers_effective'], 7)
        self.assertEqual(payload['debug_he2_publication_relaunch']['mc_cores_effective'], 7)
        self.assertEqual(payload['scale_contract']['legacy_fit_input_scale'], 'log1p_cms')
        self.assertEqual(payload['scale_contract']['analysis_scale_fit_internal'], 'log1p_cms')
        self.assertEqual(payload['debug_he2_publication_relaunch']['transform_policy'], 'log1p_only')

    def test_batch_row_config_patch_overrides_discount_block_and_is_audited(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        batch_path = tmp_path / 'discount_probe.yaml'
        batch_path.write_text(
            yaml.safe_dump(
                {
                    'selection': {
                        'cutoffs': ['20210123'],
                        'families': ['exdqlm_multivar_keep'],
                    },
                    'overrides': {
                        'row_config_patches': [
                            {
                                'cutoff': '20210123',
                                'family': 'exdqlm_multivar_keep',
                                'config_patch': {
                                    'models': {
                                        'exdqlm_multivar': {
                                            'state_evolution': {
                                                'df_s1': 0.99999,
                                                'df_s2': 0.99999,
                                                'df_s67': 0.99999,
                                                'df_discrep': 0.9999,
                                                'df_covs': 0.999999,
                                            },
                                        },
                                    },
                                },
                            },
                        ],
                    },
                },
                sort_keys=False,
            ),
            encoding='utf-8',
        )

        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(batch_path),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 1)
        self.assertEqual(frozen_rows[0]['df_s1'], '0.99999')
        self.assertEqual(frozen_rows[0]['df_s2'], '0.99999')
        self.assertEqual(frozen_rows[0]['df_s67'], '0.99999')
        self.assertEqual(frozen_rows[0]['df_discrep'], '0.9999')
        self.assertEqual(frozen_rows[0]['df_covs'], '0.999999')
        self.assertEqual(frozen_rows[0]['config_patch_applied'], 'True')
        self.assertTrue(frozen_rows[0]['config_patch_source'].endswith('discount_probe.yaml'))
        self.assertIn('"df_covs": 0.999999', frozen_rows[0]['config_patch_json'])

        config_paths = list(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 1)
        payload = yaml.safe_load(config_paths[0].read_text(encoding='utf-8')) or {}
        state = payload['models']['exdqlm_multivar']['state_evolution']
        self.assertEqual(state['df_s1'], 0.99999)
        self.assertEqual(state['df_s2'], 0.99999)
        self.assertEqual(state['df_s67'], 0.99999)
        self.assertEqual(state['df_discrep'], 0.9999)
        self.assertEqual(state['df_covs'], 0.999999)
        self.assertTrue(payload['debug_he2_publication_relaunch']['config_patch_applied'])
        self.assertTrue(str(payload['debug_he2_publication_relaunch']['config_patch_source']).endswith('discount_probe.yaml'))

    def test_batch_row_config_patch_can_apply_q50_gamma_sigma_override(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        batch_path = tmp_path / 'median_q50_probe.yaml'
        batch_path.write_text(
            yaml.safe_dump(
                {
                    'selection': {
                        'cutoffs': ['20210123'],
                        'families': ['exdqlm_multivar_keep'],
                        'quantiles': [0.50],
                    },
                    'resources': {
                        'fit_parallel_workers': 1,
                        'mc_cores': 1,
                    },
                    'overrides': {
                        'row_config_patches': [
                            {
                                'cutoff': '20210123',
                                'family': 'exdqlm_multivar_keep',
                                'manuscript_label': 'exAL-M-T1',
                                'config_patch': {
                                    'fit': {
                                        'exdqlm_multivar': {
                                            'gamma_sigma': {
                                                'quantile_overrides': {
                                                    'q50': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                },
                            },
                        ],
                    },
                },
                sort_keys=False,
            ),
            encoding='utf-8',
        )

        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(batch_path),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 1)
        self.assertEqual(frozen_rows[0]['active_quantiles'], '50')
        self.assertEqual(frozen_rows[0]['fit_parallel_workers'], '1')
        self.assertEqual(frozen_rows[0]['run_mc_cores'], '1')
        self.assertEqual(frozen_rows[0]['config_patch_applied'], 'True')
        self.assertTrue(frozen_rows[0]['config_patch_source'].endswith('median_q50_probe.yaml'))
        self.assertIn('"sigma_scale": 0.5', frozen_rows[0]['config_patch_json'])

        config_paths = list(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 1)
        payload = yaml.safe_load(config_paths[0].read_text(encoding='utf-8')) or {}
        override = payload['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']['init']
        self.assertEqual(override['mode'], 'robust')
        self.assertEqual(override['gamma'], 0.0)
        self.assertEqual(override['sigma_floor'], 0.01)

    def test_row_quantile_patch_recomputes_workers_and_debug_metadata(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        batch_path = tmp_path / 'q50_only_no_resource_override.yaml'
        batch_path.write_text(
            yaml.safe_dump(
                {
                    'selection': {
                        'cutoffs': ['20211221'],
                        'families': ['exdqlm_multivar_keep'],
                    },
                    'overrides': {
                        'row_config_patches': [
                            {
                                'cutoff': '20211221',
                                'family': 'exdqlm_multivar_keep',
                                'config_patch': {
                                    'fit': {
                                        'quantiles': [0.50],
                                    },
                                },
                            },
                        ],
                    },
                },
                sort_keys=False,
            ),
            encoding='utf-8',
        )

        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(batch_path),
            template=ALL_CUTOFFS_TEMPLATE,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 1)
        self.assertEqual(frozen_rows[0]['active_quantiles'], '50')
        self.assertEqual(frozen_rows[0]['fit_parallel_workers'], '1')
        self.assertEqual(frozen_rows[0]['run_mc_cores'], '1')

        config_paths = list(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 1)
        payload = yaml.safe_load(config_paths[0].read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['fit']['quantiles'], [0.5])
        self.assertEqual(payload['fit']['parallel']['workers'], 1)
        self.assertEqual(payload['run']['threads']['mc_cores'], 1)
        self.assertEqual(payload['debug_he2_publication_relaunch']['active_quantiles'], [0.5])
        self.assertEqual(payload['debug_he2_publication_relaunch']['fit_parallel_workers_effective'], 1)
        self.assertEqual(payload['debug_he2_publication_relaunch']['mc_cores_effective'], 1)

    def test_batch_row_config_patch_can_apply_multiple_quantile_gamma_sigma_overrides(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        batch_path = tmp_path / 'spillover_probe.yaml'
        batch_path.write_text(
            yaml.safe_dump(
                {
                    'selection': {
                        'cutoffs': ['20210123'],
                        'families': ['exdqlm_multivar_keep'],
                    },
                    'resources': {
                        'fit_parallel_workers': 7,
                        'mc_cores': 7,
                    },
                    'overrides': {
                        'row_config_patches': [
                            {
                                'cutoff': '20210123',
                                'family': 'exdqlm_multivar_keep',
                                'manuscript_label': 'exAL-M-T1',
                                'config_patch': {
                                    'fit': {
                                        'exdqlm_multivar': {
                                            'gamma_sigma': {
                                                'quantile_overrides': {
                                                    'q20': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        },
                                                    },
                                                    'q50': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        },
                                                    },
                                                    'q80': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        },
                                                    },
                                                }
                                            }
                                        }
                                    }
                                },
                            },
                        ],
                    },
                },
                sort_keys=False,
            ),
            encoding='utf-8',
        )

        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(batch_path),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 1)
        self.assertEqual(frozen_rows[0]['fit_parallel_workers'], '7')
        self.assertEqual(frozen_rows[0]['run_mc_cores'], '7')
        self.assertEqual(frozen_rows[0]['config_patch_applied'], 'True')
        self.assertTrue(frozen_rows[0]['config_patch_source'].endswith('spillover_probe.yaml'))

        config_paths = list(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 1)
        payload = yaml.safe_load(config_paths[0].read_text(encoding='utf-8')) or {}
        overrides = payload['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']
        self.assertEqual(set(overrides.keys()), {'q20', 'q50', 'q80'})
        for q in ('q20', 'q50', 'q80'):
            override = overrides[q]['init']
            self.assertEqual(override['mode'], 'robust')
            self.assertEqual(override['gamma'], 0.0)
            self.assertEqual(override['sigma_floor'], 0.01)
            self.assertEqual(override['sigma_scale'], 0.5)

    def test_batch_row_config_patch_can_apply_q35_lighter_override(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        batch_path = tmp_path / 'q35_lighter_probe.yaml'
        batch_path.write_text(
            yaml.safe_dump(
                {
                    'selection': {
                        'cutoffs': ['20210123'],
                        'families': ['exdqlm_multivar_keep'],
                        'quantiles': [0.35],
                    },
                    'resources': {
                        'fit_parallel_workers': 1,
                        'mc_cores': 1,
                    },
                    'overrides': {
                        'row_config_patches': [
                            {
                                'cutoff': '20210123',
                                'family': 'exdqlm_multivar_keep',
                                'manuscript_label': 'exAL-M-T1',
                                'config_patch': {
                                    'fit': {
                                        'exdqlm_multivar': {
                                            'gamma_sigma': {
                                                'quantile_overrides': {
                                                    'q35': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.001,
                                                            'sigma_scale': 1.0,
                                                        },
                                                        'stabilization': {
                                                            'median_state_hold_after_guard_iters': 10,
                                                            'median_state_blend_alpha': 1.0,
                                                            'median_cov_blend_alpha': 1.0,
                                                        },
                                                    }
                                                }
                                            }
                                        }
                                    }
                                },
                            },
                        ],
                    },
                },
                sort_keys=False,
            ),
            encoding='utf-8',
        )

        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(batch_path),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 1)
        self.assertEqual(frozen_rows[0]['active_quantiles'], '35')
        self.assertEqual(frozen_rows[0]['config_patch_applied'], 'True')

        config_paths = list(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 1)
        payload = yaml.safe_load(config_paths[0].read_text(encoding='utf-8')) or {}
        override = payload['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q35']
        self.assertEqual(override['init']['mode'], 'robust')
        self.assertEqual(override['init']['gamma'], 0.0)
        self.assertEqual(override['init']['sigma_floor'], 0.001)
        self.assertEqual(override['init']['sigma_scale'], 1.0)
        self.assertEqual(override['stabilization']['median_state_hold_after_guard_iters'], 10)

    def test_batch_row_config_patch_can_apply_final_quantile_policy_map(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        batch_path = tmp_path / 'row_final_quantile_map.yaml'
        batch_path.write_text(
            yaml.safe_dump(
                {
                    'selection': {
                        'cutoffs': ['20210123'],
                        'families': ['exdqlm_multivar_keep'],
                    },
                    'resources': {
                        'fit_parallel_workers': 7,
                        'mc_cores': 7,
                    },
                    'overrides': {
                        'row_config_patches': [
                            {
                                'cutoff': '20210123',
                                'family': 'exdqlm_multivar_keep',
                                'manuscript_label': 'exAL-M-T1',
                                'config_patch': {
                                    'fit': {
                                        'exdqlm_multivar': {
                                            'gamma_sigma': {
                                                'quantile_overrides': {
                                                    'q20': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        },
                                                    },
                                                    'q35': {
                                                        'freeze_target': 'states',
                                                        'warmup_freeze_iters': 8,
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        },
                                                        'stabilization': {
                                                            'state_guard_enabled': True,
                                                            'state_norm_max_ratio': 25,
                                                            'state_norm_abs_cap': 1.0e12,
                                                            'state_guard_refreeze_iters': 10,
                                                            'state_hold_after_guard_iters': 10,
                                                            'state_blend_alpha': 1.0,
                                                            'cov_blend_alpha': 1.0,
                                                        },
                                                    },
                                                    'q50': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        },
                                                        'stabilization': {
                                                            'median_state_hold_after_guard_iters': 10,
                                                            'median_state_blend_alpha': 1.0,
                                                            'median_cov_blend_alpha': 1.0,
                                                        },
                                                    },
                                                    'q65': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        },
                                                    },
                                                    'q80': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        },
                                                    },
                                                }
                                            }
                                        }
                                    }
                                },
                            },
                        ],
                    },
                },
                sort_keys=False,
            ),
            encoding='utf-8',
        )

        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(batch_path),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 1)
        self.assertEqual(frozen_rows[0]['fit_parallel_workers'], '7')
        self.assertEqual(frozen_rows[0]['run_mc_cores'], '7')
        self.assertEqual(frozen_rows[0]['config_patch_applied'], 'True')

        config_paths = list(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 1)
        payload = yaml.safe_load(config_paths[0].read_text(encoding='utf-8')) or {}
        overrides = payload['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']
        self.assertEqual(set(overrides.keys()), {'q20', 'q35', 'q50', 'q65', 'q80'})
        self.assertEqual(overrides['q20']['init']['sigma_scale'], 0.5)
        self.assertEqual(overrides['q65']['init']['sigma_scale'], 0.5)
        self.assertEqual(overrides['q80']['init']['sigma_scale'], 0.5)
        self.assertEqual(overrides['q35']['freeze_target'], 'states')
        self.assertEqual(overrides['q35']['warmup_freeze_iters'], 8)
        self.assertTrue(overrides['q35']['stabilization']['state_guard_enabled'])
        self.assertEqual(overrides['q35']['stabilization']['state_hold_after_guard_iters'], 10)
        self.assertEqual(overrides['q50']['stabilization']['median_state_hold_after_guard_iters'], 10)

    def test_family_level_quantile_policy_patch_applies_to_all_selected_cutoffs(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        batch_path = tmp_path / 'family_all_cutoffs.yaml'
        batch_path.write_text(
            yaml.safe_dump(
                {
                    'selection': {
                        'cutoffs': ['20210123', '20211112', '20211221', '20220511', '20221225'],
                        'families': ['exdqlm_multivar_keep'],
                    },
                    'resources': {
                        'fit_parallel_workers': 7,
                        'mc_cores': 7,
                    },
                    'overrides': {
                        'row_config_patches': [
                            {
                                'family': 'exdqlm_multivar_keep',
                                'manuscript_label': 'exAL-M-T1',
                                'config_patch': {
                                    'fit': {
                                        'exdqlm_multivar': {
                                            'gamma_sigma': {
                                                'quantile_overrides': {
                                                    'q35': {
                                                        'freeze_target': 'states',
                                                        'warmup_freeze_iters': 8,
                                                        'stabilization': {
                                                            'state_guard_enabled': True,
                                                            'state_hold_after_guard_iters': 10,
                                                        },
                                                    }
                                                }
                                            }
                                        }
                                    }
                                },
                            }
                        ]
                    },
                },
                sort_keys=False,
            ),
            encoding='utf-8',
        )

        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(batch_path),
            template=ALL_CUTOFFS_TEMPLATE,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8') as handle:
            plan_rows = list(csv.DictReader(handle))
        self.assertEqual(len(plan_rows), 5)
        self.assertEqual(sorted({row['cutoff'] for row in plan_rows}), ['20210123', '20211112', '20211221', '20220511', '20221225'])

        config_paths = sorted(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 5)
        for path in config_paths:
            payload = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
            override = payload['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q35']
            self.assertEqual(override['freeze_target'], 'states')
            self.assertEqual(override['warmup_freeze_iters'], 8)
            self.assertTrue(override['stabilization']['state_guard_enabled'])
            self.assertEqual(override['stabilization']['state_hold_after_guard_iters'], 10)

    def test_builder_enforces_log1p_internal_scales_even_if_patch_requests_loglog(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        batch_path = tmp_path / 'bad_scale_patch.yaml'
        batch_path.write_text(
            yaml.safe_dump(
                {
                    'selection': {
                        'cutoffs': ['20210123'],
                        'families': ['exdqlm_multivar_keep'],
                    },
                    'overrides': {
                        'row_config_patches': [
                            {
                                'cutoff': '20210123',
                                'family': 'exdqlm_multivar_keep',
                                'config_patch': {
                                    'scale_contract': {
                                        'analysis_scale_fit_internal': 'log_log1p_cms',
                                        'analysis_scale_post_internal': 'log_log1p_cms',
                                    },
                                },
                            },
                        ],
                    },
                },
                sort_keys=False,
            ),
            encoding='utf-8',
        )

        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(batch_path),
            template=ALL_CUTOFFS_TEMPLATE,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 1)
        self.assertEqual(frozen_rows[0]['analysis_scale_fit_internal'], 'log1p_cms')
        self.assertEqual(frozen_rows[0]['analysis_scale_post_internal'], 'log1p_cms')

        config_paths = list(config_output_dir.glob('*.yaml'))
        self.assertEqual(len(config_paths), 1)
        payload = yaml.safe_load(config_paths[0].read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['scale_contract']['analysis_scale_fit_internal'], 'log1p_cms')
        self.assertEqual(payload['scale_contract']['analysis_scale_post_internal'], 'log1p_cms')

    def test_cutoff_specific_run_seed_patch_applies_to_generated_configs(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)
        batch_path = tmp_path / 'seed_recovery.yaml'
        batch_path.write_text(
            yaml.safe_dump(
                {
                    'selection': {
                        'cutoffs': ['20211221', '20221225'],
                        'families': ['exdqlm_multivar_keep'],
                    },
                    'resources': {
                        'fit_parallel_workers': 7,
                        'mc_cores': 7,
                    },
                    'overrides': {
                        'row_config_patches': [
                            {
                                'family': 'exdqlm_multivar_keep',
                                'manuscript_label': 'exAL-M-T1',
                                'config_patch': {
                                    'fit': {
                                        'exdqlm_multivar': {
                                            'gamma_sigma': {
                                                'quantile_overrides': {
                                                    'q50': {
                                                        'init': {
                                                            'mode': 'robust',
                                                            'gamma': 0.0,
                                                            'sigma_floor': 0.01,
                                                            'sigma_scale': 0.5,
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                },
                            },
                            {
                                'cutoff': '20211221',
                                'family': 'exdqlm_multivar_keep',
                                'manuscript_label': 'exAL-M-T1',
                                'config_patch': {
                                    'run': {
                                        'seed': 20211221,
                                    }
                                },
                            },
                            {
                                'cutoff': '20221225',
                                'family': 'exdqlm_multivar_keep',
                                'manuscript_label': 'exAL-M-T1',
                                'config_patch': {
                                    'run': {
                                        'seed': 20221225,
                                    }
                                },
                            },
                        ]
                    },
                },
                sort_keys=False,
            ),
            encoding='utf-8',
        )

        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(batch_path),
            template=ALL_CUTOFFS_TEMPLATE,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8') as handle:
            plan_rows = list(csv.DictReader(handle))
        self.assertEqual(sorted({row['cutoff'] for row in plan_rows}), ['20211221', '20221225'])

        payloads = {}
        for path in sorted(config_output_dir.glob('*.yaml')):
            payload = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
            run_id = payload['run']['run_id']
            cutoff = run_id.split('_')[1]
            payloads[cutoff] = payload

        self.assertEqual(payloads['20211221']['run']['seed'], 20211221)
        self.assertEqual(payloads['20221225']['run']['seed'], 20221225)
        self.assertEqual(payloads['20211221']['scale_contract']['analysis_scale_fit_internal'], 'log1p_cms')
        self.assertEqual(payloads['20221225']['scale_contract']['analysis_scale_post_internal'], 'log1p_cms')

    def test_phase2_control_batch_recomputes_quantile_workers_and_debug_metadata(self) -> None:
        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(PHASE2_DIAGNOSTIC_BATCH),
            template=PHASE2_DIAGNOSTIC_TEMPLATE,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8') as handle:
            plan_rows = list(csv.DictReader(handle))
        self.assertEqual(len(plan_rows), 2)
        self.assertEqual(sorted((row['cutoff'], row['active_quantiles']) for row in plan_rows), [
            ('20211221', '50|65'),
            ('20221225', '65|80'),
        ])

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 2)
        by_cutoff = {row['cutoff']: row for row in frozen_rows}
        self.assertEqual(by_cutoff['20211221']['fit_parallel_workers'], '2')
        self.assertEqual(by_cutoff['20211221']['run_mc_cores'], '2')
        self.assertEqual(by_cutoff['20211221']['active_quantile_count'], '2')
        self.assertEqual(by_cutoff['20221225']['fit_parallel_workers'], '2')
        self.assertEqual(by_cutoff['20221225']['run_mc_cores'], '2')
        self.assertEqual(by_cutoff['20221225']['active_quantile_count'], '2')

        payloads = {}
        for path in sorted(config_output_dir.glob('*.yaml')):
            payload = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
            cutoff = payload['run']['run_id'].split('_')[1]
            payloads[cutoff] = payload

        self.assertEqual(payloads['20211221']['fit']['quantiles'], [0.5, 0.65])
        self.assertEqual(payloads['20211221']['fit']['parallel']['workers'], 2)
        self.assertEqual(payloads['20211221']['run']['threads']['mc_cores'], 2)
        self.assertEqual(payloads['20211221']['fit']['exdqlm_multivar']['legacy']['n_samp'], 8)
        self.assertEqual(payloads['20211221']['run']['seed'], 20211221)
        self.assertEqual(
            payloads['20211221']['debug_he2_publication_relaunch']['active_quantiles'],
            [0.5, 0.65],
        )
        self.assertEqual(
            payloads['20211221']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']['terminal_sampling_guard']['mode'],
            'fail_fast',
        )

        self.assertEqual(payloads['20221225']['fit']['quantiles'], [0.65, 0.8])
        self.assertEqual(payloads['20221225']['fit']['parallel']['workers'], 2)
        self.assertEqual(payloads['20221225']['run']['threads']['mc_cores'], 2)
        self.assertEqual(payloads['20221225']['fit']['exdqlm_multivar']['legacy']['n_samp'], 8)
        self.assertEqual(payloads['20221225']['run']['seed'], 20221225)
        self.assertEqual(
            payloads['20221225']['debug_he2_publication_relaunch']['active_quantiles'],
            [0.65, 0.8],
        )

    def test_proof_promotion_batch_builds_remaining_cutoffs_with_winning_q50_policy_only_on_20211221(self) -> None:
        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(PROOF_PROMOTION_BATCH),
            template=ALL_CUTOFFS_TEMPLATE,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8') as handle:
            plan_rows = list(csv.DictReader(handle))
        self.assertEqual([row['cutoff'] for row in plan_rows], ['20211221', '20221225'])

        cfg_20211221 = yaml.safe_load(
            (config_output_dir / 'multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml').read_text(encoding='utf-8')
        ) or {}
        cfg_20221225 = yaml.safe_load(
            (config_output_dir / 'multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml').read_text(encoding='utf-8')
        ) or {}

        self.assertEqual(cfg_20211221['run']['seed'], 20211221)
        self.assertEqual(cfg_20221225['run']['seed'], 20221225)
        self.assertEqual(cfg_20211221['fit']['parallel']['workers'], 7)
        self.assertEqual(cfg_20221225['run']['threads']['mc_cores'], 7)

        q50_20211221 = cfg_20211221['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertEqual(q50_20211221['freeze_target'], 'states')
        self.assertEqual(q50_20211221['terminal_sampling_guard']['mode'], 'fail_fast')
        self.assertEqual(q50_20211221['stabilization']['median_state_hold_after_guard_iters'], 0)
        self.assertEqual(q50_20211221['stabilization']['median_state_blend_alpha'], 0.5)
        self.assertEqual(q50_20211221['stabilization']['median_cov_blend_alpha'], 0.5)
        self.assertEqual(q50_20211221['stabilization']['median_max_abs_gamma_step'], 0.15)
        self.assertEqual(q50_20211221['stabilization']['median_max_abs_log_sigma_step'], 0.25)

        q50_20221225 = cfg_20221225['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertNotIn('freeze_target', q50_20221225)
        self.assertNotIn('terminal_sampling_guard', q50_20221225)
        self.assertEqual(q50_20221225['stabilization']['median_state_hold_after_guard_iters'], 10)
        self.assertEqual(q50_20221225['stabilization']['median_state_blend_alpha'], 1.0)
        self.assertEqual(q50_20221225['stabilization']['median_cov_blend_alpha'], 1.0)

        diag_20211221 = cfg_20211221['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']
        diag_20221225 = cfg_20221225['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']
        self.assertEqual(diag_20211221['walltime_seconds'], 900)
        self.assertTrue(diag_20211221['heartbeat_enabled'])
        self.assertEqual(diag_20221225['member_walltime_seconds'], 20)

    def test_20221225_q50_statefreeze_diagnostic_and_promotion_batches_build_expected_configs(self) -> None:
        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(Q50_20221225_STATEFREEZE_BATCH),
            template=Q50_20221225_STATEFREEZE_TEMPLATE,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8') as handle:
            plan_rows = list(csv.DictReader(handle))
        self.assertEqual(len(plan_rows), 1)
        self.assertEqual(plan_rows[0]['cutoff'], '20221225')
        self.assertEqual(plan_rows[0]['active_quantiles'], '50|80')

        cfg_diag = yaml.safe_load(
            (config_output_dir / 'multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml').read_text(encoding='utf-8')
        ) or {}
        self.assertEqual(cfg_diag['run']['seed'], 20221225)
        self.assertEqual(cfg_diag['fit']['quantiles'], [0.5, 0.8])
        self.assertEqual(cfg_diag['fit']['parallel']['workers'], 2)
        self.assertEqual(cfg_diag['run']['threads']['mc_cores'], 2)
        self.assertEqual(cfg_diag['fit']['exdqlm_multivar']['legacy']['n_samp'], 8)
        q50_diag = cfg_diag['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertEqual(q50_diag['freeze_target'], 'states')
        self.assertEqual(q50_diag['terminal_sampling_guard']['mode'], 'fail_fast')
        self.assertEqual(q50_diag['stabilization']['median_state_hold_after_guard_iters'], 0)
        self.assertEqual(q50_diag['stabilization']['median_state_blend_alpha'], 0.5)
        self.assertEqual(q50_diag['stabilization']['median_cov_blend_alpha'], 0.5)
        self.assertEqual(q50_diag['stabilization']['median_max_abs_gamma_step'], 0.15)
        self.assertEqual(q50_diag['stabilization']['median_max_abs_log_sigma_step'], 0.25)

        proc2, matrix_dir2, config_output_dir2, _artifact_root2 = self._run_builder(
            '--batch-file', str(Q50_20221225_PROOF_PROMOTION_BATCH),
            template=ALL_CUTOFFS_TEMPLATE,
        )
        self.assertEqual(proc2.returncode, 0, msg=proc2.stderr)

        with (matrix_dir2 / 'matrix_plan.csv').open('r', encoding='utf-8') as handle:
            plan_rows2 = list(csv.DictReader(handle))
        self.assertEqual(len(plan_rows2), 1)
        self.assertEqual(plan_rows2[0]['cutoff'], '20221225')

        cfg_prod = yaml.safe_load(
            (config_output_dir2 / 'multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml').read_text(encoding='utf-8')
        ) or {}
        self.assertEqual(cfg_prod['run']['seed'], 20221225)
        self.assertEqual(cfg_prod['fit']['parallel']['workers'], 7)
        self.assertEqual(cfg_prod['run']['threads']['mc_cores'], 7)
        q50_prod = cfg_prod['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertEqual(q50_prod['freeze_target'], 'states')
        self.assertEqual(q50_prod['terminal_sampling_guard']['mode'], 'fail_fast')
        self.assertEqual(q50_prod['stabilization']['median_state_hold_after_guard_iters'], 0)
        self.assertEqual(q50_prod['stabilization']['median_state_blend_alpha'], 0.5)
        self.assertEqual(q50_prod['stabilization']['median_cov_blend_alpha'], 0.5)
        self.assertEqual(q50_prod['stabilization']['median_max_abs_gamma_step'], 0.15)
        self.assertEqual(q50_prod['stabilization']['median_max_abs_log_sigma_step'], 0.25)
        diag_prod = cfg_prod['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']
        self.assertEqual(diag_prod['heartbeat_seconds'], 30)
        self.assertEqual(diag_prod['walltime_seconds'], 900)
        self.assertEqual(diag_prod['member_walltime_seconds'], 20)

    def test_wave_a_ndlm_batch_builds_only_the_remaining_ndlm_rows(self) -> None:
        proc, matrix_dir, config_output_dir, _artifact_root = self._run_builder(
            '--batch-file', str(WAVE_A_NDLM_BATCH),
            template=WAVE_A_NDLM_TEMPLATE,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with (matrix_dir / 'matrix_plan.csv').open('r', encoding='utf-8') as handle:
            plan_rows = list(csv.DictReader(handle))
        self.assertEqual(len(plan_rows), 15)
        self.assertEqual(sorted({row['family_id'] for row in plan_rows}), ['ndlm_main_drop', 'ndlm_main_keep', 'ndlm_univar_keep'])
        self.assertEqual({row['model_class'] for row in plan_rows}, {'ndlm'})

        with (matrix_dir / 'frozen_spec_manifest.csv').open('r', encoding='utf-8') as handle:
            frozen_rows = list(csv.DictReader(handle))
        self.assertEqual(len(frozen_rows), 15)
        self.assertTrue(all(row['selected_spec_token'] == 'ndlm_featurecov_v1_postfix' for row in frozen_rows))

        self.assertEqual(len(list(config_output_dir.glob('*.yaml'))), 15)
        sample_cfg = yaml.safe_load(
            (config_output_dir / 'multimodel_20210123_v8_he2pubgdpc1r1_ndlm_univar_keep.yaml').read_text(encoding='utf-8')
        ) or {}
        self.assertEqual(sample_cfg['debug_he2_publication_relaunch']['model_class'], 'ndlm')
        self.assertEqual(sample_cfg['inputs']['covariate_features']['enabled'], True)
        self.assertEqual(
            [entry['name'] for entry in sample_cfg['inputs']['fit']['covariates']],
            ['PPT', 'SOIL', 'PCA'],
        )
        self.assertEqual(sample_cfg['run']['threads']['mc_cores'], 1)


if __name__ == '__main__':
    unittest.main()
