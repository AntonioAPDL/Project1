from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('comment2_diagnostics', ROOT/'scripts/audit_comment2_component_diagnostics.py')
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

POLICY = ('[gamsig_policy] warmup_freeze_iters=10 min_update_iters=50 '
          'min_total_iters=50 max_iter=120 elbo_tol=1e-6 state_norm_sq_tol=1e-6 '
          'sigma_exp_tol=1e-6 gamma_exp_tol=1e-6')


class SavedDiagnosticTests(unittest.TestCase):
    def test_source_hash_guard_detects_changed_saved_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'fit.log'
            path.write_text('original saved evidence')
            evidence = audit.Evidence()
            evidence.text(path)
            path.write_text('changed saved evidence')
            with self.assertRaisesRegex(ValueError, 'Evidence changed'):
                evidence.verify()

    def test_audit_refuses_to_read_heavy_r_objects(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'fit.RData'
            path.write_bytes(b'not read by this audit')
            with self.assertRaisesRegex(ValueError, 'saved text diagnostics'):
                audit.Evidence().text(path)

    def test_legacy_success_phrase_cannot_override_terminal_failed_criteria(self):
        text = POLICY + '\n[gamsig_progress] iter=120 gamsig_update_iters=110 frozen=false\n' + (
            '[gamsig_hold] iter=120 conv_elbo=false conv_state=false conv_sigma=false '
            'conv_gamma=false conv_min_updates=true conv_min_iters=true\n'
            'VB converged: 120 iterations, 2654.397 seconds\n'
            '[sampling_preflight] phase=vb_terminal_guard blocked=false guard_count=0')
        result = audit.parse_multivar(text)
        self.assertEqual(result['stopping_status'], 'budget_limited')
        self.assertTrue(result['legacy_converged_phrase_present'])
        self.assertFalse(result['terminal_guard_blocked'])

    def test_final_criteria_can_converge_on_last_budget_iteration(self):
        text = POLICY + ('\n[gamsig_progress] iter=120 gamsig_update_iters=110 frozen=false '
                         'crit_elbo=1e-8 crit_state_norm_sq=1e-8 crit_sigma_exp=1e-8 crit_gamma_exp=1e-8')
        result = audit.parse_multivar(text)
        self.assertEqual(result['stopping_status'], 'converged')
        self.assertTrue(result['at_iteration_budget'])

    def test_frozen_zero_changes_do_not_manufacture_convergence(self):
        text = POLICY + ('\n[gamsig_progress] iter=120 gamsig_update_iters=72 frozen=true '
                         'crit_elbo=0 crit_state_norm_sq=0 crit_sigma_exp=0 crit_gamma_exp=0')
        result = audit.parse_multivar(text)
        self.assertEqual(result['stopping_status'], 'budget_limited')
        self.assertIn('frozen', result['stopping_evidence_basis'])

    def test_terminal_guard_and_historical_guard_are_distinct(self):
        base = POLICY + '\n[gamsig_state_guard] iter=15 reason=recovery\n'
        base += '[vb_fit_end] converged=true iterations_completed=70 max_iter=120 convergence_reason=convergence_criteria_satisfied\n'
        healthy = audit.parse_multivar(base + '[sampling_preflight] phase=vb_terminal_guard blocked=false')
        self.assertEqual(healthy['stopping_status'], 'converged')
        self.assertEqual(healthy['historical_state_guard_events'], 1)
        inactive = audit.parse_multivar(base + '[sampling_preflight] phase=vb_terminal_guard median=false frozen=true blocked=true')
        self.assertEqual(inactive['stopping_status'], 'converged')
        self.assertEqual(inactive['safeguard_status'], 'frozen_at_stop')
        blocked = audit.parse_multivar(base + '[sampling_preflight] phase=vb_terminal_guard blocked=true\n[terminal_sampling_guard] guard tripped')
        self.assertEqual(blocked['stopping_status'], 'guarded')
        self.assertEqual(blocked['criterion_status_before_guard'], 'converged')

    def test_tail_excludes_initialization_planned_warmup_and_refrozen_rows(self):
        rows = [dict(iter=0,elbo=0,frozen='false'),dict(iter=5,elbo=1e9,frozen='true'),
                dict(iter=11,elbo=-10,frozen='false'),dict(iter=12,elbo=-1e8,frozen='true'),
                dict(iter=13,elbo=-10.1,frozen='false')]
        result = audit.tail_metrics(rows, warmup=10)
        self.assertEqual(result['tail_rows'], 2)
        self.assertEqual(result['elbo_tail_first'], -10)
        self.assertEqual(result['elbo_tail_last'], -10.1)
        self.assertNotIn('converged', result)

    def test_missing_joint_criteria_remain_unknown_even_with_legacy_phrase(self):
        result = audit.parse_univar('elbo_final=0\nelbo_final=-100\nelbo_final=-99\nsigma=0.1',
                                    'VB converged: 100 iterations, 12 seconds')
        self.assertEqual(result['stopping_status'], 'unknown')
        self.assertEqual(result['objective_values_available'], 3)

    def test_saved_ndlm_criterion_is_not_replaced_by_forecast_performance(self):
        result = audit.parse_ndlm('converged=true\niterations_completed=23\nmax_iter=100\n'
                                 'convergence_reason=parameter_change_and_objective_stabilized')
        self.assertEqual(result['stopping_status'], 'converged')
        self.assertEqual(result['final_iter'], 23)

    @unittest.skipUnless(shutil.which('Rscript'), 'Rscript is needed to evaluate the reporting block')
    def test_actual_r_reporting_block_distinguishes_criterion_and_budget_stops(self):
        # Parse the real entrypoint, but evaluate only its terminal reporting block.
        # No model, helper, package loading, iteration or sampler is executed.
        code = r'''
        nodes <- parse(commandArgs(TRUE)[1])
        find_block <- function(x) {
          if (missing(x)) return(list())
          if (is.call(x) && identical(x[[1]], as.name("if")) &&
              identical(x[[2]], as.name("verbose")) &&
              grepl("vb_fit_end",paste(deparse(x),collapse=" "),fixed=TRUE)) return(list(x))
          if (!is.call(x) && !is.expression(x)) return(list())
          unlist(lapply(as.list(x),find_block),recursive=FALSE)
        }
        selected <- find_block(nodes)
        stopifnot(length(selected)==1L)
        run_case <- function(flag, iteration, budget) {
          e <- new.env(parent=baseenv())
          e$verbose <- TRUE; e$FLAG <- flag; e$iter <- iteration; e$max_iter <- budget
          e$p0 <- .5; e$run.time <- list(toc=3,tic=1)
          paste(capture.output(eval(selected[[1]],e)),collapse=" ")
        }
        a <- run_case(FALSE,120L,120L); b <- run_case(TRUE,120L,120L)
        c <- run_case(TRUE,50L,120L)
        stopifnot(grepl("converged=true",a,fixed=TRUE),
          grepl("convergence_reason=convergence_criteria_satisfied",a,fixed=TRUE),
          grepl("converged=false",b,fixed=TRUE),
          grepl("convergence_reason=iteration_budget_reached",b,fixed=TRUE),
          grepl("stopped_without_recorded_convergence",c,fixed=TRUE))
        cat("reporting-only cases passed\n")
        '''
        proc = subprocess.run(['Rscript','--vanilla','-e',code,
                               str(ROOT/'DISC_Optimal_Synth_Ranges_W_transfer_forecast.r')],
                              text=True,capture_output=True)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)


if __name__ == '__main__':
    unittest.main()
