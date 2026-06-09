from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DISC_SOURCE = ROOT / 'DISC_Optimal_Synth_Ranges_W.r'
DISC_TRANSFER_SOURCE = ROOT / 'DISC_Optimal_Synth_Ranges_W_transfer_forecast.r'
STAGE_FIT_SOURCE = ROOT / 'R' / 'unified' / 'stages' / 'stage_fit.R'
RUN_DISC_SOURCE = ROOT / 'scripts' / 'run_DISC_Optimal_Synth_Ranges_W.R'
STATE_BLEND_SOURCE = ROOT / 'R' / 'disc_w' / '09_state_blend.R'
FIT_GUARDS_SOURCE = ROOT / 'R' / 'disc_w' / '09_fit_guards.R'


class DiscSamplingDiagnosticsSourceContractTests(unittest.TestCase):
    def test_disc_sources_write_sampling_diagnostics_to_dedicated_sink(self) -> None:
        for source in (DISC_SOURCE, DISC_TRANSFER_SOURCE):
            text = source.read_text(encoding='utf-8')
            self.assertIn('DISC_W_SAMPLING_DIAG_PATH', text, source.name)
            self.assertIn('DISC_W_SAMPLING_DIAG_STDERR_ENABLED', text, source.name)
            self.assertIn('DISC_W_SAMPLING_MEMBER_WALLTIME_SECONDS', text, source.name)
            self.assertIn('sampling_preflight', text, source.name)
            self.assertIn('sampling_latent_states_done', text, source.name)
            self.assertIn('sampling_forecast_mvnorm_done', text, source.name)
            self.assertIn('sampling_forecast_member_gig_done', text, source.name)
            self.assertIn('sampling_forecast_member_truncnorm_done', text, source.name)
            self.assertIn('sts.alpha', text, source.name)
            self.assertIn('samp.sts_member', text, source.name)
            self.assertIn('sampling_invalid_input', text, source.name)
            self.assertIn('sampling_error', text, source.name)

    def test_disc_sources_block_sampling_when_gamma_sigma_updates_are_insufficient(self) -> None:
        for source in (DISC_SOURCE, DISC_TRANSFER_SOURCE):
            text = source.read_text(encoding='utf-8')
            self.assertIn('stopped before required gamma/sigma updates', text, source.name)
            self.assertIn('terminal sampling guard tripped for p0=', text, source.name)
            self.assertIn('terminal_sampling_guard_recent', text, source.name)

    def test_disc_sources_materialize_cpp_theta_payload_before_state_blending(self) -> None:
        state_blend_text = STATE_BLEND_SOURCE.read_text(encoding='utf-8')
        for source in (DISC_SOURCE, DISC_TRANSFER_SOURCE):
            text = source.read_text(encoding='utf-8')
            self.assertIn('disc_materialize_theta_cpp_payload <- function', text, source.name)
            self.assertIn('theta_cpp,', text, source.name)
            self.assertIn('J,', text, source.name)
            self.assertIn('p,', text, source.name)
            self.assertIn('ppx,', text, source.name)
            self.assertIn('num_mem,', text, source.name)
            self.assertIn('update.theta.raw <- DISC_update_theta_synth_cpp_W(', text, source.name)
            self.assertIn('update.theta <- disc_materialize_theta_cpp_payload(', text, source.name)
            self.assertIn('J = J,', text, source.name)
            self.assertIn('p = p,', text, source.name)
            self.assertIn('ppx = ppx,', text, source.name)
            self.assertIn('num_mem = num_mem,', text, source.name)
            blend_contract_text = text
            if 'source("R/disc_w/09_state_blend.R")' in text:
                blend_contract_text += state_blend_text
            self.assertIn('blend dim mismatch for %s current=%s candidate=%s', blend_contract_text, source.name)
            self.assertIn('if (is.null(current) && is.null(candidate))', blend_contract_text, source.name)
            self.assertIn('if (is.null(candidate))', blend_contract_text, source.name)
            self.assertIn('if (is.null(current_list) && is.null(candidate_list))', blend_contract_text, source.name)
            self.assertIn('if (is.null(candidate_list))', blend_contract_text, source.name)
            self.assertIn('theta payload horizon mismatch for %s', text, source.name)

    def test_stage_fit_exports_quantile_sampling_diagnostic_path(self) -> None:
        text = STAGE_FIT_SOURCE.read_text(encoding='utf-8')
        self.assertIn('DISC_W_SAMPLING_DIAG_PATH = file.path(q_logs, "sampling_diagnostics.log")', text)
        self.assertIn('DISC_W_SAMPLING_DIAG_STDERR_ENABLED = "TRUE"', text)
        self.assertIn('DISC_W_SAMPLING_MEMBER_WALLTIME_SECONDS', text)

    def test_stage_fit_exports_guarded_keep_promotion_controls(self) -> None:
        text = STAGE_FIT_SOURCE.read_text(encoding='utf-8')
        for token in (
            'DISC_LATENT_ABLATION_MODE',
            'DISC_LATENT_E_INV_U_CAP',
            'DISC_PSEUDODATA_GUARD_ENABLED',
            'DISC_PSEUDODATA_GUARD_MODE',
            'DISC_PSEUDODATA_GUARD_REPORT_DIR',
            'DISC_PSEUDODATA_FFF_ABS_CAP',
            'DISC_PSEUDODATA_QQQ_DIAG_ABS_CAP',
            'DISC_PSEUDODATA_E_S_ABS_CAP',
            'DISC_PSEUDODATA_E_S2_ABS_CAP',
            'DISC_PSEUDODATA_E_U_ABS_CAP',
            'DISC_PSEUDODATA_E_INV_U_ABS_CAP',
            'DISC_GAMSIG_STATE_GUARD_START_ITER',
            'DISC_GAMSIG_STATE_GUARD_STEP_BACKOFF_ENABLED',
            'DISC_GAMSIG_STATE_GUARD_STEP_BACKOFF_FACTOR',
            'DISC_GAMSIG_STATE_GUARD_MIN_STEP_SCALE',
            'DISC_GAMSIG_STATE_HOLD_FREEZE_LATENTS_ENABLED',
            'DISC_GAMSIG_STATE_GUARD_HOLD_STEP_SCALE_ENABLED',
            'DISC_GAMSIG_STATE_GUARD_MIN_REFREEZE_ITERS',
            'DISC_GAMSIG_STATE_GUARD_MIN_HOLD_ITERS',
            'DISC_GAMSIG_MEDIAN_STATE_GUARD_SIGMA_ONLY_ENABLED',
            'DISC_GAMSIG_MEDIAN_STATE_GUARD_SIGMA_ONLY_AFTER',
            'DISC_GAMSIG_MEDIAN_STATE_GUARD_SIGMA_ONLY_ANCHOR',
            'DISC_GAMSIG_NEAR_ZERO_FALLBACK_ENABLED',
            'DISC_GAMSIG_NEAR_ZERO_FALLBACK_MODE',
            'DISC_GAMSIG_NEAR_ZERO_GAMMA_ANCHOR',
        ):
            self.assertIn(token, text)

    def test_legacy_multivar_entrypoints_use_unconditional_finite_iteration_guard(self) -> None:
        forbidden = 'state_guard_active <- (!isTRUE(DISC_W_AL_MODE) &&'
        fit_guard_text = FIT_GUARDS_SOURCE.read_text(encoding='utf-8')
        self.assertIn('disc_w_iteration_guard_decision <- function', fit_guard_text)
        self.assertIn('disc_w_guard_backoff_step_scale <- function', fit_guard_text)
        self.assertIn('disc_w_guard_scaled_hold_iters <- function', fit_guard_text)
        self.assertIn('disc_w_effective_step_cap <- function', fit_guard_text)
        self.assertIn('disc_w_scalar_finite_or_default <- function', fit_guard_text)
        self.assertIn('disc_w_reanchor_gamsig_to_gamma <- function', fit_guard_text)
        self.assertIn('bad_core <- names(core_values)[!is.finite(core_values)]', fit_guard_text)
        self.assertIn('finite_guard = TRUE', fit_guard_text)
        for source in (DISC_SOURCE, DISC_TRANSFER_SOURCE):
            text = source.read_text(encoding='utf-8')
            self.assertNotIn(forbidden, text, source.name)
            self.assertIn('disc_w_iteration_guard_decision(', text, source.name)
            self.assertIn('disc_w_numeric_mean_all_finite(new.sig, positive_required = TRUE)', text, source.name)
            self.assertIn('disc_w_numeric_mean_all_finite(new.gam)', text, source.name)
            self.assertIn('disc_w_state_norm_sq_all_finite(new.theta.out$sm)', text, source.name)
            self.assertIn('disc_w_scalar_finite_or_default(new.theta.out$elbo.part, default = 0)', text, source.name)
            self.assertIn('prev_ELBO_iter <- disc_w_scalar_finite_or_default(ELBO, default = NA_real_)', text, source.name)
            self.assertIn('rollback_elbo <- disc_w_scalar_finite_or_default(prev_ELBO_iter, default = 0)', text, source.name)
            self.assertIn('rollback_state_norm_sq <- disc_w_state_norm_sq_all_finite(new.theta.out$sm)', text, source.name)
            self.assertIn('gamsig_finite_guard', text, source.name)
            self.assertIn('state_compatible.gamsig.out <- new.gamsig.out', text, source.name)
            self.assertIn('new.gamsig.out <- state_compatible.gamsig.out', text, source.name)
            self.assertIn('state_compatible_gamsig_update_iters <- as.integer(gamsig_update_iters)', text, source.name)
            self.assertIn('gamsig_update_iters <- as.integer(state_compatible_gamsig_update_iters)', text, source.name)
            self.assertIn('gamsig_state_guard_step_scale <- disc_w_guard_backoff_step_scale(', text, source.name)
            self.assertIn('effective_refreeze_iters <- disc_w_guard_scaled_hold_iters(', text, source.name)
            self.assertIn('effective_hold_iters <- disc_w_guard_scaled_hold_iters(', text, source.name)
            self.assertIn('step_scale=%s', text, source.name)
            self.assertIn('effective_refreeze_iters=%d effective_hold_iters=%d', text, source.name)
            self.assertIn('state_guard_step_backoff_enabled', text, source.name)
            self.assertIn('state_hold_freeze_latents_enabled', text, source.name)
            self.assertIn('state_guard_hold_step_scale_enabled', text, source.name)
            self.assertIn('gamsig_median_state_guard_sigma_only_active <- FALSE', text, source.name)
            self.assertIn('median state guard sigma-only anchor=%s', text, source.name)
            self.assertIn('disc_w_reanchor_gamsig_to_gamma(', text, source.name)
            self.assertIn('state_compatible_gamsig_update_iters <- 0L', text, source.name)
            self.assertIn('[gamsig_state_guard_recovery] p0=%s iter=%d recovery=%s sigma_exp=%s gamma_exp=%s reason=%s', text, source.name)
            self.assertIn('recovery=%s step_scale=%s->%s', text, source.name)
            self.assertIn('sigma-only fallback damping at p0=%s context=%s after %s step_scale=%s sigma_log_step=%s->%s', text, source.name)
            self.assertIn('[gamsig_median_state_guard_sigma_only] p0=%s iter=%d guard_count=%d activate=true anchor=%s reason=%s', text, source.name)
            self.assertIn('[latent_hold] p0=%s iter=%d hold_until_iter=%d freeze_latents=true', text, source.name)
            self.assertIn('disc_w_assert_finite_square_matrix(M, label = label)', text, source.name)
            self.assertIn('initial seq.eigen covariance slice', text, source.name)
            self.assertNotIn('mean(new.sig, na.rm = TRUE)', text, source.name)
            self.assertNotIn('sum(new.theta.out$sm^2, na.rm = TRUE)', text, source.name)
            self.assertNotIn('M[!is.finite(M)] <- 0', text, source.name)
            for token in (
                'DISC_GAMSIG_STATE_GUARD_START_ITER',
                'likelihood_mode=%s',
                'state_guard_configured=%s',
                'state_guard_effective_policy=%s',
                'state_guard_disabled_reason=%s',
                'terminal_sampling_guard_mode',
            ):
                self.assertIn(token, text, source.name)

    def test_run_disc_entrypoint_routes_keep_to_transfer_source(self) -> None:
        text = RUN_DISC_SOURCE.read_text(encoding='utf-8')
        self.assertIn('DISC_W_FORECAST_TRANSFER_MODE', text)
        self.assertIn('"DISC_Optimal_Synth_Ranges_W_transfer_forecast.r"', text)
        self.assertIn('"DISC_Optimal_Synth_Ranges_W.r"', text)
        self.assertIn('if (identical(transfer_mode, "keep"))', text)


if __name__ == '__main__':
    unittest.main()
