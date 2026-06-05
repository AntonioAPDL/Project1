from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

from scripts.audit_he2_al_m_t0_gamsig_cycles import classify_two_cycle, parse_progress_lines
from scripts.prepare_he2_single_quantile_fit_diagnostic import prepare_config
from scripts.summarize_he2_al_m_t0_fit_logs import summarize


def progress_line(iteration: int, sigma: float, state: float, elbo: float = -1.0, p0: float = 0.35) -> str:
    return (
        f"[gamsig_progress] family=exdqlm_multivar p0={p0} "
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

    def test_compact_fit_log_summary_reads_terminal_health_and_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_al_m_t0_log_summary_") as tmp:
            root = Path(tmp)
            q_root = (
                root
                / "runs"
                / "multimodel_20220511_v8_he2pubgdpc1r1_dqlm_multivar_al_drop"
                / "fit"
                / "q=65"
            )
            log_dir = q_root / "logs"
            out_dir = q_root / "outputs"
            log_dir.mkdir(parents=True)
            out_dir.mkdir(parents=True)
            (log_dir / "fit.log").write_text(
                "\n".join(
                    [
                        progress_line(1, 0.2, 100.0, p0=0.65),
                        "[gamsig_state_guard] p0=0.65 iter=2 old_until=0 new_until=4 reason=state_growth_ratio=42 exceeds max_ratio=25",
                        progress_line(2, 0.25, 120.0, p0=0.65),
                        "[sampling_preflight] p0=0.65 phase=vb_terminal_guard mode=fail_fast guard_count=1",
                        "Error: stopped before required gamma/sigma updates: got=2 required=50",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "multivar_terminal_state_health.csv").write_text(
                "metric,value,limit,direction,status\n"
                "state_norm_sq_per_T,12.5,10000,max,ok\n"
                "transfer_level_max_abs,1.2,25,max,ok\n",
                encoding="utf-8",
            )
            rows = summarize([root])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["cutoff"], "20220511")
            self.assertEqual(row["q"], "0.65")
            self.assertEqual(row["upd"], 2)
            self.assertEqual(row["guards"], 1)
            self.assertEqual(row["state_norm_sq_per_T"], "12.5")
            self.assertIn("stopped before required", row["error"])

    def test_single_quantile_fit_diagnostic_helper_scopes_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_single_q_fit_diag_") as tmp:
            root = Path(tmp)
            source = root / "source.yaml"
            artifact = root / "artifact"
            source.write_text(
                "run:\n"
                "  run_id: source_run\n"
                "  threads:\n"
                "    mc_cores: 7\n"
                "stages:\n"
                "  forecats: false\n"
                "  data_prep_shared: true\n"
                "  fit: true\n"
                "  post: true\n"
                "  validate: true\n"
                "  report: true\n"
                "fit:\n"
                "  quantiles: [0.05, 0.65]\n"
                "  parallel:\n"
                "    workers: 7\n",
                encoding="utf-8",
            )
            meta = prepare_config(
                source,
                artifact,
                quantile=0.65,
                run_id_suffix="q65_fitonly",
                fit_only=True,
            )
            config_path = Path(meta["config_path"])
            self.assertTrue(config_path.exists())
            text = config_path.read_text(encoding="utf-8")
            self.assertIn("run_id: source_run_q65_fitonly", text)
            self.assertIn("quantiles:\n  - 0.65", text)
            self.assertIn("workers: 1", text)
            self.assertIn("mc_cores: 1", text)
            self.assertIn("post: false", text)
            self.assertIn("validate: false", text)
            self.assertIn("report: false", text)
            self.assertTrue(Path(meta["launch_script"]).exists())


if __name__ == "__main__":
    unittest.main()
