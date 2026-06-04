from __future__ import annotations

import math
import unittest

from scripts.audit_he2_al_m_t0_gamsig_cycles import classify_two_cycle, parse_progress_lines


def progress_line(iteration: int, sigma: float, state: float, elbo: float = -1.0) -> str:
    return (
        "[gamsig_progress] family=exdqlm_multivar p0=0.35 "
        f"iter={iteration} elbo={elbo} crit_elbo=0 sigma_exp={sigma} "
        "crit_sigma_exp=0 gamma_exp=0 crit_gamma_exp=0 sigma_exp_vec=[0] "
        "gamma_exp_vec=[0] sigma_delta_vec=[0] gamma_delta_vec=[0] "
        f"state_norm_sq={state} crit_state_norm_sq=0 conv_check=0 "
        f"gamsig_update_iters={iteration} min_update_iters=50 min_total_iters=50 frozen=false"
    )


class He2AlMT0GamsigCycleAuditTests(unittest.TestCase):
    def test_detects_terminal_two_cycle(self) -> None:
        lines = [
            progress_line(95, 0.25, 5.9e4),
            progress_line(96, 999.0, 1.3e12),
            progress_line(97, 0.25, 5.9e4),
            progress_line(98, 999.0, 1.3e12),
            progress_line(99, 0.25, 5.9e4),
            progress_line(100, 999.0, 1.3e12),
        ]
        rows, _, _, _ = parse_progress_lines(lines)
        summary = classify_two_cycle(rows, window=6)
        self.assertTrue(summary["two_cycle_suspect"])
        self.assertEqual(summary["tail_sigma_pattern"], "LHLHLH")
        self.assertGreater(float(summary["tail_sigma_ratio"]), 1000)
        self.assertGreater(float(summary["tail_state_ratio"]), 1e6)

    def test_stable_tail_is_not_two_cycle(self) -> None:
        lines = [progress_line(iteration, 0.101 + iteration * 1e-8, 55000 + iteration) for iteration in range(91, 101)]
        rows, _, _, _ = parse_progress_lines(lines)
        summary = classify_two_cycle(rows)
        self.assertFalse(summary["two_cycle_suspect"])
        self.assertEqual(summary["cycle_reason"], "stable_or_non_alternating_tail")
        self.assertLess(float(summary["tail_sigma_ratio"]), 1.01)

    def test_policy_and_preflight_are_parsed(self) -> None:
        lines = [
            "[gamsig_policy] p0=0.35 likelihood_mode=al freeze_target=states "
            "state_guard=true state_guard_effective_policy=true terminal_sampling_guard_mode=fail_fast",
            progress_line(1, 0.2, 1.0),
            "[sampling_preflight] p0=0.35 phase=vb_terminal_guard mode=fail_fast guard_count=1",
        ]
        rows, policy, preflight, guard_count = parse_progress_lines(lines)
        self.assertEqual(len(rows), 1)
        self.assertEqual(policy["likelihood_mode"], "al")
        self.assertEqual(policy["terminal_sampling_guard_mode"], "fail_fast")
        self.assertEqual(preflight["guard_count"], "1")
        self.assertEqual(guard_count, 0)
        self.assertTrue(math.isfinite(rows[0].sigma_exp))


if __name__ == "__main__":
    unittest.main()
