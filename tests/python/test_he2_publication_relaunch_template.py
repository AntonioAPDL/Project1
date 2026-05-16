from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_20260510.template.yaml'
ALL_CUTOFFS_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml'
DIAGNOSTIC_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_problem_quantiles_diagnostic_20260513.template.yaml'
PHASE2_DIAGNOSTIC_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.template.yaml'
Q65_RUNTIME_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q65_runtime_diagnostic_20260514.template.yaml'
Q50_STABILIZATION_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_stabilization_diagnostic_20260514.template.yaml'
Q65_TRUNCNORM_RUNTIME_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q65_truncnorm_runtime_diagnostic_20260514.template.yaml'
Q50_STATEFREEZE_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_diagnostic_20260514.template.yaml'
Q50_STATEFREEZE_RERUN_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_rerun_20260515.template.yaml'
Q50_STATEFREEZE_STEPCAP10_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap10_20260515.template.yaml'
Q50_STATEFREEZE_STEPCAP075_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap075_20260515.template.yaml'
Q50_20221225_STATEFREEZE_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_q50_statefreeze_diagnostic_20260515.template.yaml'
RECOVERY_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_remaining_cutoffs_seed_recovery_20260513.yaml'
PROOF_PROMOTION_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_remaining_cutoffs_proof_promotion_20260515.yaml'
DIAGNOSTIC_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_problem_quantiles_diagnostic_20260513.yaml'
PHASE2_DIAGNOSTIC_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.yaml'
Q65_RUNTIME_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_q65_runtime_diagnostic_20260514.yaml'
Q50_STABILIZATION_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_q50_stabilization_diagnostic_20260514.yaml'
Q65_TRUNCNORM_RUNTIME_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_q65_truncnorm_runtime_diagnostic_20260514.yaml'
Q50_STATEFREEZE_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_q50_statefreeze_stabilization_diagnostic_20260514.yaml'
Q50_STATEFREEZE_RERUN_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_q50_statefreeze_stabilization_rerun_20260515.yaml'
Q50_STATEFREEZE_STEPCAP10_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap10_20260515.yaml'
Q50_STATEFREEZE_STEPCAP075_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap075_20260515.yaml'
Q50_20221225_STATEFREEZE_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_20221225_q50_statefreeze_diagnostic_20260515.yaml'
Q50_20221225_PROOF_PROMOTION_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_20221225_q50_proof_promotion_20260515.yaml'
WAVE_A_NDLM_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml'
WAVE_A_NDLM_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'he2_wave_a_ndlm_remaining_families_20260516.yaml'
EXDQLM_RERUN_TEMPLATE = ROOT / 'config' / 'he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_rerun_20260516.template.yaml'
EXDQLM_RERUN_BATCH = ROOT / 'config' / 'he2_relaunch_batches' / 'exdqlm_multivar_keep_all_cutoffs_rerun_20260516.yaml'


class HE2PublicationRelaunchTemplateTests(unittest.TestCase):
    def test_template_exists_and_has_expected_campaign_contract(self) -> None:
        self.assertTrue(TEMPLATE.exists())
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(len(payload['campaign']['cutoffs']), 5)
        self.assertEqual(len(payload['bundles']['cutoffs']), 5)
        self.assertEqual(payload['campaign']['campaign_spec_id'], 'he2pubgdpc1r1')
        self.assertEqual(payload['validation']['fit_smoke_family'], 'ndlm_univar_keep')
        self.assertEqual(payload['validation']['fit_smoke_cutoff'], '20210123')

    def test_template_exposes_selection_resource_and_profile_controls(self) -> None:
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        selection = payload['selection']
        self.assertEqual(selection['cutoffs'], [])
        self.assertEqual(selection['families'], [])
        self.assertEqual(selection['manuscript_labels'], [])
        self.assertEqual(selection['run_ids'], [])
        self.assertEqual(selection['model_classes'], [])
        self.assertEqual(selection['quantiles'], [])
        self.assertEqual(selection['batch_file'], '')

        resources = payload['resources']
        self.assertIn('fit_parallel_workers', resources)
        self.assertIn('mc_cores', resources)

        profiles = payload['profiles']
        self.assertEqual(profiles['active'], 'default')
        self.assertIn('serial_debug', profiles['definitions'])
        self.assertIn('single_core_full', profiles['definitions'])
        self.assertEqual(profiles['definitions']['serial_debug']['resources']['fit_parallel_workers'], 1)
        self.assertEqual(profiles['definitions']['single_core_full']['resources']['mc_cores'], 1)

    def test_template_validation_includes_quantile_and_full_pipeline_smokes(self) -> None:
        payload = yaml.safe_load(TEMPLATE.read_text(encoding='utf-8')) or {}
        validation = payload['validation']
        self.assertIn('smoke_fit_overrides', validation)
        self.assertEqual(validation['smoke_fit_overrides']['exdqlm_multivar']['gamma_sigma']['max_iter'], 10)
        self.assertEqual(validation['smoke_fit_overrides']['exdqlm_univar']['gamma_sigma']['min_total_iters'], 10)
        self.assertEqual(validation['quantile_fit_smoke_family'], 'exdqlm_multivar_keep')
        self.assertEqual(validation['quantile_fit_smoke_quantiles'], [0.05])
        self.assertEqual(validation['full_pipeline_ndlm_family'], 'ndlm_univar_keep')
        self.assertEqual(validation['full_pipeline_quantile_family'], 'exdqlm_univar')
        self.assertEqual(validation['full_pipeline_quantiles'], [0.05])

    def test_all_cutoffs_template_hardens_queue_and_covers_both_cutoff_classes(self) -> None:
        payload = yaml.safe_load(ALL_CUTOFFS_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['queue']['pause_free_gb'], 25)
        self.assertEqual(payload['queue']['launch_free_gb'], 35)
        self.assertEqual(payload['queue']['heavy_free_gb'], 35)
        self.assertEqual(payload['profiles']['definitions']['disk_guarded_serial']['resources']['fit_parallel_workers'], 7)
        self.assertEqual(payload['profiles']['definitions']['disk_guarded_dual']['queue']['ordinary_max_concurrent'], 2)
        self.assertEqual(payload['profiles']['definitions']['disk_guarded_dual']['resources']['mc_cores'], 7)
        self.assertEqual(payload['profiles']['definitions']['disk_guarded_dual_recovery']['queue']['ordinary_max_concurrent'], 2)
        self.assertFalse(payload['profiles']['definitions']['disk_guarded_dual_recovery']['queue']['heavy_cutoff_blocks_ordinary'])
        self.assertEqual(payload['profiles']['definitions']['disk_guarded_dual_recovery']['resources']['fit_parallel_workers'], 7)

        validation = payload['validation']
        self.assertEqual([case['cutoff'] for case in validation['quantile_fit_smoke_cases']], ['20210123', '20211221'])
        self.assertEqual([case['cutoff'] for case in validation['full_pipeline_quantile_smoke_cases']], ['20210123', '20211221'])
        self.assertEqual(validation['quantile_fit_smoke_cases'][0]['quantiles'], [0.2, 0.35, 0.5, 0.65, 0.8])

    def test_problem_quantile_diagnostic_template_uses_isolated_runtime_root(self) -> None:
        self.assertTrue(DIAGNOSTIC_TEMPLATE.exists())
        payload = yaml.safe_load(DIAGNOSTIC_TEMPLATE.read_text(encoding='utf-8')) or {}
        campaign = payload['campaign']
        self.assertIn('problem_quantiles_diagnostic_20260513', campaign['artifact_root'])
        self.assertIn('problem_quantiles_diagnostic_20260513', campaign['matrix_dir'])
        self.assertIn('problem_quantiles_diagnostic_20260513', campaign['config_output_dir'])

    def test_seed_recovery_batch_targets_only_remaining_cutoffs_and_changes_only_run_seed(self) -> None:
        self.assertTrue(RECOVERY_BATCH.exists())
        payload = yaml.safe_load(RECOVERY_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['cutoffs'], ['20211221', '20221225'])
        self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 7)
        self.assertEqual(payload['resources']['mc_cores'], 7)

        patches = payload['overrides']['row_config_patches']
        seed_patches = [item for item in patches if item.get('config_patch', {}).get('run')]
        self.assertEqual(len(seed_patches), 2)
        seed_by_cutoff = {item['cutoff']: item['config_patch']['run']['seed'] for item in seed_patches}
        self.assertEqual(seed_by_cutoff, {'20211221': 20211221, '20221225': 20221225})

    def test_proof_promotion_batch_promotes_only_winning_q50_policy_and_runtime_diagnostics(self) -> None:
        self.assertTrue(PROOF_PROMOTION_BATCH.exists())
        payload = yaml.safe_load(PROOF_PROMOTION_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['cutoffs'], ['20211221', '20221225'])
        self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 7)
        self.assertEqual(payload['resources']['mc_cores'], 7)

        patches = payload['overrides']['row_config_patches']
        family_patch = next(item for item in patches if item.get('cutoff') in (None, ''))
        legacy_diag = family_patch['config_patch']['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']
        self.assertTrue(legacy_diag['heartbeat_enabled'])
        self.assertEqual(legacy_diag['heartbeat_seconds'], 30)
        self.assertEqual(legacy_diag['walltime_seconds'], 900)
        self.assertEqual(legacy_diag['member_walltime_seconds'], 20)

        family_q50 = family_patch['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertEqual(family_q50['stabilization']['median_state_hold_after_guard_iters'], 10)
        self.assertEqual(family_q50['stabilization']['median_state_blend_alpha'], 1.0)
        self.assertEqual(family_q50['stabilization']['median_cov_blend_alpha'], 1.0)

        q50_row = next(item for item in patches if item.get('cutoff') == '20211221')
        self.assertEqual(q50_row['config_patch']['run']['seed'], 20211221)
        q50_override = q50_row['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertEqual(q50_override['freeze_target'], 'states')
        self.assertEqual(q50_override['terminal_sampling_guard']['mode'], 'fail_fast')
        self.assertEqual(q50_override['stabilization']['median_state_hold_after_guard_iters'], 0)
        self.assertEqual(q50_override['stabilization']['median_state_blend_alpha'], 0.5)
        self.assertEqual(q50_override['stabilization']['median_cov_blend_alpha'], 0.5)
        self.assertEqual(q50_override['stabilization']['median_max_abs_gamma_step'], 0.15)
        self.assertEqual(q50_override['stabilization']['median_max_abs_log_sigma_step'], 0.25)

        q65_row = next(item for item in patches if item.get('cutoff') == '20221225')
        self.assertEqual(q65_row['config_patch']['run']['seed'], 20221225)
        self.assertEqual(set(q65_row['config_patch'].keys()), {'run'})

    def test_20221225_q50_statefreeze_diagnostic_and_followon_promotion_batches_are_wired_correctly(self) -> None:
        self.assertTrue(Q50_20221225_STATEFREEZE_TEMPLATE.exists())
        self.assertTrue(Q50_20221225_STATEFREEZE_BATCH.exists())
        self.assertTrue(Q50_20221225_PROOF_PROMOTION_BATCH.exists())

        template_payload = yaml.safe_load(Q50_20221225_STATEFREEZE_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertIn('20221225_q50_statefreeze_diagnostic_20260515', template_payload['campaign']['artifact_root'])
        self.assertIn('20221225_q50_statefreeze_diagnostic_20260515', template_payload['campaign']['matrix_dir'])

        diag_payload = yaml.safe_load(Q50_20221225_STATEFREEZE_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(diag_payload['selection']['cutoffs'], ['20221225'])
        self.assertEqual(diag_payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(diag_payload['resources']['fit_parallel_workers'], 2)
        self.assertEqual(diag_payload['resources']['mc_cores'], 2)

        diag_patches = diag_payload['overrides']['row_config_patches']
        diag_row = next(item for item in diag_patches if item.get('cutoff') == '20221225')
        self.assertEqual(diag_row['config_patch']['run']['seed'], 20221225)
        self.assertEqual(diag_row['config_patch']['fit']['quantiles'], [0.5, 0.8])
        self.assertEqual(diag_row['config_patch']['fit']['exdqlm_multivar']['legacy']['n_samp'], 8)
        q50_diag = diag_row['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertEqual(q50_diag['freeze_target'], 'states')
        self.assertEqual(q50_diag['terminal_sampling_guard']['mode'], 'fail_fast')
        self.assertEqual(q50_diag['stabilization']['median_state_hold_after_guard_iters'], 0)
        self.assertEqual(q50_diag['stabilization']['median_state_blend_alpha'], 0.5)
        self.assertEqual(q50_diag['stabilization']['median_cov_blend_alpha'], 0.5)
        self.assertEqual(q50_diag['stabilization']['median_max_abs_gamma_step'], 0.15)
        self.assertEqual(q50_diag['stabilization']['median_max_abs_log_sigma_step'], 0.25)

        promotion_payload = yaml.safe_load(Q50_20221225_PROOF_PROMOTION_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(promotion_payload['selection']['cutoffs'], ['20221225'])
        self.assertEqual(promotion_payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(promotion_payload['resources']['fit_parallel_workers'], 7)
        self.assertEqual(promotion_payload['resources']['mc_cores'], 7)
        promotion_patches = promotion_payload['overrides']['row_config_patches']
        family_patch = next(item for item in promotion_patches if item.get('cutoff') in (None, ''))
        family_q50 = family_patch['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertEqual(family_q50['freeze_target'], 'states')
        self.assertEqual(family_q50['terminal_sampling_guard']['mode'], 'fail_fast')
        self.assertEqual(family_q50['stabilization']['median_state_hold_after_guard_iters'], 0)
        self.assertEqual(family_q50['stabilization']['median_state_blend_alpha'], 0.5)
        self.assertEqual(family_q50['stabilization']['median_cov_blend_alpha'], 0.5)
        self.assertEqual(family_patch['config_patch']['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']['heartbeat_seconds'], 30)

        row_patch = next(item for item in promotion_patches if item.get('cutoff') == '20221225')
        self.assertEqual(row_patch['config_patch']['run']['seed'], 20221225)
        self.assertEqual(set(row_patch['config_patch'].keys()), {'run'})

    def test_problem_quantile_diagnostic_batch_is_targeted_and_instrumented(self) -> None:
        self.assertTrue(DIAGNOSTIC_BATCH.exists())
        payload = yaml.safe_load(DIAGNOSTIC_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['cutoffs'], ['20211221', '20221225'])
        self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 1)
        self.assertEqual(payload['resources']['mc_cores'], 1)

        patches = payload['overrides']['row_config_patches']
        family_patch = next(item for item in patches if item.get('cutoff') in (None, ''))
        self.assertEqual(family_patch['family'], 'exdqlm_multivar_keep')
        self.assertEqual(family_patch['manuscript_label'], 'exAL-M-T1')

        q50_patch = next(item for item in patches if item.get('cutoff') == '20211221')
        self.assertEqual(q50_patch['config_patch']['run']['seed'], 20211221)
        self.assertEqual(q50_patch['config_patch']['fit']['quantiles'], [0.5])
        self.assertEqual(q50_patch['config_patch']['fit']['exdqlm_multivar']['legacy']['n_samp'], 128)
        self.assertTrue(q50_patch['config_patch']['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']['heartbeat_enabled'])
        self.assertEqual(
            q50_patch['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']['terminal_sampling_guard']['mode'],
            'fail_fast',
        )

        q65_patch = next(item for item in patches if item.get('cutoff') == '20221225')
        self.assertEqual(q65_patch['config_patch']['run']['seed'], 20221225)
        self.assertEqual(q65_patch['config_patch']['fit']['quantiles'], [0.65])
        self.assertEqual(q65_patch['config_patch']['fit']['exdqlm_multivar']['legacy']['n_samp'], 128)
        self.assertEqual(
            q65_patch['config_patch']['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']['walltime_seconds'],
            1800,
        )

    def test_phase2_control_diagnostic_batch_pairs_problem_and_control_quantiles(self) -> None:
        self.assertTrue(PHASE2_DIAGNOSTIC_TEMPLATE.exists())
        self.assertTrue(PHASE2_DIAGNOSTIC_BATCH.exists())

        template_payload = yaml.safe_load(PHASE2_DIAGNOSTIC_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertIn('phase2_controls_diagnostic_20260514', template_payload['campaign']['artifact_root'])
        self.assertIn('phase2_controls_diagnostic_20260514', template_payload['campaign']['matrix_dir'])

        payload = yaml.safe_load(PHASE2_DIAGNOSTIC_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['cutoffs'], ['20211221', '20221225'])
        self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 2)
        self.assertEqual(payload['resources']['mc_cores'], 2)

        patches = payload['overrides']['row_config_patches']
        q50_row = next(item for item in patches if item.get('cutoff') == '20211221')
        q65_row = next(item for item in patches if item.get('cutoff') == '20221225')

        self.assertEqual(q50_row['config_patch']['run']['seed'], 20211221)
        self.assertEqual(q50_row['config_patch']['fit']['quantiles'], [0.5, 0.65])
        self.assertEqual(q50_row['config_patch']['fit']['exdqlm_multivar']['legacy']['n_samp'], 8)
        self.assertEqual(
            q50_row['config_patch']['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']['heartbeat_seconds'],
            5,
        )
        self.assertEqual(
            q50_row['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']['terminal_sampling_guard']['mode'],
            'fail_fast',
        )

        self.assertEqual(q65_row['config_patch']['run']['seed'], 20221225)
        self.assertEqual(q65_row['config_patch']['fit']['quantiles'], [0.65, 0.8])
        self.assertEqual(q65_row['config_patch']['fit']['exdqlm_multivar']['legacy']['n_samp'], 8)
        self.assertTrue(
            q65_row['config_patch']['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']['phase_markers_enabled']
        )
        self.assertEqual(
            q65_row['config_patch']['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']['walltime_seconds'],
            300,
        )

    def test_q65_runtime_diagnostic_batch_targets_runtime_bug_with_member_guard(self) -> None:
        self.assertTrue(Q65_RUNTIME_TEMPLATE.exists())
        self.assertTrue(Q65_RUNTIME_BATCH.exists())

        template_payload = yaml.safe_load(Q65_RUNTIME_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertIn('q65_runtime_diagnostic_20260514', template_payload['campaign']['artifact_root'])
        self.assertIn('q65_runtime_diagnostic_20260514', template_payload['campaign']['matrix_dir'])

        payload = yaml.safe_load(Q65_RUNTIME_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['cutoffs'], ['20221225'])
        self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 2)
        self.assertEqual(payload['resources']['mc_cores'], 2)

        row = payload['overrides']['row_config_patches'][-1]
        self.assertEqual(row['config_patch']['run']['seed'], 20221225)
        self.assertEqual(row['config_patch']['fit']['quantiles'], [0.65, 0.80])
        legacy = row['config_patch']['fit']['exdqlm_multivar']['legacy']
        self.assertEqual(legacy['n_samp'], 8)
        diag = legacy['sampling_diagnostics']
        self.assertEqual(diag['heartbeat_seconds'], 5)
        self.assertTrue(diag['phase_markers_enabled'])
        self.assertEqual(diag['walltime_seconds'], 300)
        self.assertEqual(diag['member_walltime_seconds'], 20)

    def test_q50_stabilization_diagnostic_batch_targets_candidate_policy(self) -> None:
        self.assertTrue(Q50_STABILIZATION_TEMPLATE.exists())
        self.assertTrue(Q50_STABILIZATION_BATCH.exists())

        template_payload = yaml.safe_load(Q50_STABILIZATION_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertIn('q50_stabilization_diagnostic_20260514', template_payload['campaign']['artifact_root'])
        self.assertIn('q50_stabilization_diagnostic_20260514', template_payload['campaign']['matrix_dir'])

        payload = yaml.safe_load(Q50_STABILIZATION_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['cutoffs'], ['20211221'])
        self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 2)
        self.assertEqual(payload['resources']['mc_cores'], 2)

        row = payload['overrides']['row_config_patches'][-1]
        self.assertEqual(row['config_patch']['run']['seed'], 20211221)
        self.assertEqual(row['config_patch']['fit']['quantiles'], [0.50, 0.65])
        legacy = row['config_patch']['fit']['exdqlm_multivar']['legacy']
        self.assertEqual(legacy['n_samp'], 8)
        diag = legacy['sampling_diagnostics']
        self.assertEqual(diag['walltime_seconds'], 300)
        self.assertEqual(diag['member_walltime_seconds'], 20)
        q50 = row['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertEqual(q50['terminal_sampling_guard']['mode'], 'fail_fast')
        self.assertEqual(q50['stabilization']['median_state_hold_after_guard_iters'], 0)

    def test_q65_truncnorm_runtime_batch_preserves_runtime_scope_on_new_artifact_root(self) -> None:
        self.assertTrue(Q65_TRUNCNORM_RUNTIME_TEMPLATE.exists())
        self.assertTrue(Q65_TRUNCNORM_RUNTIME_BATCH.exists())

        template_payload = yaml.safe_load(Q65_TRUNCNORM_RUNTIME_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertIn('q65_truncnorm_runtime_diagnostic_20260514', template_payload['campaign']['artifact_root'])
        self.assertIn('q65_truncnorm_runtime_diagnostic_20260514', template_payload['campaign']['matrix_dir'])

        payload = yaml.safe_load(Q65_TRUNCNORM_RUNTIME_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['cutoffs'], ['20221225'])
        self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 2)
        self.assertEqual(payload['resources']['mc_cores'], 2)

        row = payload['overrides']['row_config_patches'][-1]
        self.assertEqual(row['config_patch']['run']['seed'], 20221225)
        self.assertEqual(row['config_patch']['fit']['quantiles'], [0.65, 0.80])
        diag = row['config_patch']['fit']['exdqlm_multivar']['legacy']['sampling_diagnostics']
        self.assertEqual(diag['member_walltime_seconds'], 20)
        self.assertEqual(diag['walltime_seconds'], 300)

    def test_q50_statefreeze_stabilization_batch_encodes_second_candidate(self) -> None:
        self.assertTrue(Q50_STATEFREEZE_TEMPLATE.exists())
        self.assertTrue(Q50_STATEFREEZE_BATCH.exists())

        template_payload = yaml.safe_load(Q50_STATEFREEZE_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertIn('q50_statefreeze_stabilization_diagnostic_20260514', template_payload['campaign']['artifact_root'])
        self.assertIn('q50_statefreeze_stabilization_diagnostic_20260514', template_payload['campaign']['matrix_dir'])

        payload = yaml.safe_load(Q50_STATEFREEZE_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(payload['selection']['cutoffs'], ['20211221'])
        self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(payload['resources']['fit_parallel_workers'], 2)
        self.assertEqual(payload['resources']['mc_cores'], 2)

        row = payload['overrides']['row_config_patches'][-1]
        self.assertEqual(row['config_patch']['run']['seed'], 20211221)
        self.assertEqual(row['config_patch']['fit']['quantiles'], [0.50, 0.65])
        q50 = row['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
        self.assertEqual(q50['freeze_target'], 'states')
        self.assertEqual(q50['terminal_sampling_guard']['mode'], 'fail_fast')
        self.assertEqual(q50['stabilization']['median_state_hold_after_guard_iters'], 0)
        self.assertEqual(q50['stabilization']['median_state_blend_alpha'], 0.5)
        self.assertEqual(q50['stabilization']['median_cov_blend_alpha'], 0.5)
        self.assertEqual(q50['stabilization']['median_max_abs_gamma_step'], 0.15)
        self.assertEqual(q50['stabilization']['median_max_abs_log_sigma_step'], 0.25)

    def test_q50_statefreeze_rerun_and_stepcap_ladder_batches_are_isolated_and_monotone(self) -> None:
        variants = [
            (
                Q50_STATEFREEZE_RERUN_TEMPLATE,
                Q50_STATEFREEZE_RERUN_BATCH,
                'q50_statefreeze_stabilization_rerun_20260515',
                0.15,
                0.25,
            ),
            (
                Q50_STATEFREEZE_STEPCAP10_TEMPLATE,
                Q50_STATEFREEZE_STEPCAP10_BATCH,
                'q50_statefreeze_stabilization_stepcap10_20260515',
                0.10,
                0.20,
            ),
            (
                Q50_STATEFREEZE_STEPCAP075_TEMPLATE,
                Q50_STATEFREEZE_STEPCAP075_BATCH,
                'q50_statefreeze_stabilization_stepcap075_20260515',
                0.075,
                0.15,
            ),
        ]

        for template_path, batch_path, root_token, gamma_cap, sigma_cap in variants:
            self.assertTrue(template_path.exists())
            self.assertTrue(batch_path.exists())

            template_payload = yaml.safe_load(template_path.read_text(encoding='utf-8')) or {}
            self.assertIn(root_token, template_payload['campaign']['artifact_root'])
            self.assertIn(root_token, template_payload['campaign']['matrix_dir'])
            self.assertEqual(template_payload['profiles']['definitions']['overnight_q50_ladder']['queue']['ordinary_max_concurrent'], 4)
            self.assertEqual(template_payload['profiles']['definitions']['overnight_q50_ladder']['resources']['fit_parallel_workers'], 2)

            payload = yaml.safe_load(batch_path.read_text(encoding='utf-8')) or {}
            self.assertEqual(payload['selection']['cutoffs'], ['20211221'])
            self.assertEqual(payload['selection']['families'], ['exdqlm_multivar_keep'])
            row = payload['overrides']['row_config_patches'][-1]
            self.assertEqual(row['config_patch']['run']['seed'], 20211221)
            self.assertEqual(row['config_patch']['fit']['quantiles'], [0.50, 0.65])
            q50 = row['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['quantile_overrides']['q50']
            self.assertEqual(q50['freeze_target'], 'states')
            self.assertEqual(q50['terminal_sampling_guard']['mode'], 'fail_fast')
            self.assertEqual(q50['stabilization']['median_state_hold_after_guard_iters'], 0)
            self.assertEqual(q50['stabilization']['median_state_blend_alpha'], 0.5)
            self.assertEqual(q50['stabilization']['median_cov_blend_alpha'], 0.5)
            self.assertEqual(q50['stabilization']['median_max_abs_gamma_step'], gamma_cap)
            self.assertEqual(q50['stabilization']['median_max_abs_log_sigma_step'], sigma_cap)

    def test_wave_a_ndlm_template_and_batch_freeze_scope_to_theory_aligned_remaining_families(self) -> None:
        self.assertTrue(WAVE_A_NDLM_TEMPLATE.exists())
        self.assertTrue(WAVE_A_NDLM_BATCH.exists())

        template_payload = yaml.safe_load(WAVE_A_NDLM_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(
            template_payload['campaign']['families'],
            ['ndlm_univar_keep', 'ndlm_main_drop', 'ndlm_main_keep'],
        )
        self.assertIn('wave_a_ndlm_20260516', template_payload['campaign']['artifact_root'])
        self.assertEqual(template_payload['queue']['ordinary_max_concurrent'], 2)
        self.assertEqual(template_payload['validation']['cutoff_smoke_family'], 'ndlm_univar_keep')
        self.assertEqual(template_payload['validation']['full_pipeline_ndlm_family'], 'ndlm_univar_keep')

        batch_payload = yaml.safe_load(WAVE_A_NDLM_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(
            batch_payload['selection']['families'],
            ['ndlm_univar_keep', 'ndlm_main_drop', 'ndlm_main_keep'],
        )
        self.assertEqual(batch_payload['selection']['model_classes'], ['ndlm'])
        self.assertEqual(batch_payload['resources']['fit_parallel_workers'], 1)
        self.assertEqual(batch_payload['resources']['mc_cores'], 1)
        self.assertEqual(batch_payload['queue']['ordinary_max_concurrent'], 2)

    def test_exdqlm_rerun_template_and_batch_freeze_all_cutoff_publication_specs(self) -> None:
        self.assertTrue(EXDQLM_RERUN_TEMPLATE.exists())
        self.assertTrue(EXDQLM_RERUN_BATCH.exists())

        template_payload = yaml.safe_load(EXDQLM_RERUN_TEMPLATE.read_text(encoding='utf-8')) or {}
        self.assertEqual(template_payload['campaign']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(template_payload['campaign']['cutoffs'], ['20210123', '20211112', '20211221', '20220511', '20221225'])
        self.assertIn('all_cutoffs_rerun_20260516', template_payload['campaign']['artifact_root'])
        self.assertEqual(
            [case['cutoff'] for case in template_payload['validation']['quantile_fit_smoke_cases']],
            ['20210123', '20211221', '20221225'],
        )
        self.assertEqual(template_payload['validation']['quantile_fit_smoke_cases'][0]['quantiles'], [0.5])
        self.assertEqual(template_payload['validation']['quantile_fit_smoke_cases'][-1]['quantiles'], [0.5, 0.65])
        self.assertEqual(template_payload['validation']['full_pipeline_quantile_smoke_cases'][-1]['quantiles'], [0.5, 0.65])
        self.assertEqual(template_payload['profiles']['definitions']['disk_guarded_serial']['resources']['fit_parallel_workers'], 7)
        self.assertEqual(template_payload['profiles']['definitions']['single_core_validation']['resources']['mc_cores'], 1)

        batch_payload = yaml.safe_load(EXDQLM_RERUN_BATCH.read_text(encoding='utf-8')) or {}
        self.assertEqual(batch_payload['selection']['families'], ['exdqlm_multivar_keep'])
        self.assertEqual(batch_payload['selection']['model_classes'], ['quantile_multivariate'])
        self.assertEqual(batch_payload['resources']['fit_parallel_workers'], 7)
        self.assertEqual(batch_payload['resources']['mc_cores'], 7)

        patches = {item['cutoff']: item['config_patch'] for item in batch_payload['overrides']['row_config_patches']}
        self.assertEqual(sorted(patches), ['20210123', '20211112', '20211221', '20220511', '20221225'])
        self.assertEqual(patches['20211221']['run']['seed'], 20211221)
        self.assertEqual(patches['20211221']['fit']['exdqlm_multivar']['legacy']['forecast_cov']['c_factor'], 1.0)
        self.assertEqual(patches['20211221']['fit']['exdqlm_multivar']['legacy']['forecast_cov']['epsilon'], 1.0)
        self.assertEqual(patches['20221225']['run']['seed'], 20221225)
        self.assertEqual(patches['20221225']['fit']['exdqlm_multivar']['legacy']['forecast_cov']['epsilon'], 360.0)
        self.assertEqual(patches['20221225']['models']['exdqlm_multivar']['state_evolution']['df_s1'], 0.9998)
        self.assertEqual(patches['20221225']['models']['exdqlm_multivar']['state_evolution']['df_discrep'], 0.998)
        self.assertEqual(patches['20221225']['models']['exdqlm_multivar']['state_evolution']['df_covs'], 0.9999999)


if __name__ == '__main__':
    unittest.main()
