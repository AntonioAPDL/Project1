from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DISC_SOURCE = ROOT / 'DISC_Optimal_Synth_Ranges_W.r'
DISC_TRANSFER_SOURCE = ROOT / 'DISC_Optimal_Synth_Ranges_W_transfer_forecast.r'
STAGE_FIT_SOURCE = ROOT / 'R' / 'unified' / 'stages' / 'stage_fit.R'
RUN_DISC_SOURCE = ROOT / 'scripts' / 'run_DISC_Optimal_Synth_Ranges_W.R'
STATE_BLEND_SOURCE = ROOT / 'R' / 'disc_w' / '09_state_blend.R'


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
            'DISC_GAMSIG_NEAR_ZERO_FALLBACK_ENABLED',
            'DISC_GAMSIG_NEAR_ZERO_FALLBACK_MODE',
            'DISC_GAMSIG_NEAR_ZERO_GAMMA_ANCHOR',
        ):
            self.assertIn(token, text)

    def test_al_state_guard_is_not_bypassed_in_legacy_multivar_entrypoints(self) -> None:
        forbidden = 'state_guard_active <- (!isTRUE(DISC_W_AL_MODE) &&'
        expected_condition = (
            'state_guard_active <- (isTRUE(state_guard_enabled) &&\n'
            '    as.integer(iter) >= as.integer(DISC_GAMSIG_STATE_GUARD_START_ITER))'
        )
        for source in (DISC_SOURCE, DISC_TRANSFER_SOURCE):
            text = source.read_text(encoding='utf-8')
            self.assertNotIn(forbidden, text, source.name)
            self.assertIn(expected_condition, text, source.name)
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
