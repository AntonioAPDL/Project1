#!/usr/bin/env python3
from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_publication_parity_gate import CANONICAL_LINEAGE, PROMOTED_LABEL, PROMOTED_LABELS, build_gate  # noqa: E402
from he2_exdqlm_keep_authoritative import load_authoritative_spec  # noqa: E402


class He2PublicationParityGateTests(unittest.TestCase):
    def test_gate_exposes_five_promoted_families_and_blocked_al_m_t0(self) -> None:
        rows, summary = build_gate()
        self.assertEqual(len(rows), 45)
        self.assertEqual(summary["promoted_rows"], 25)
        self.assertEqual(summary["pending_rows"], 20)
        self.assertEqual(summary["blocked_rows"], 5)
        self.assertEqual(set(summary["promoted_labels"]), PROMOTED_LABELS)
        self.assertEqual(summary["remaining_model_families_pending"], 4)
        self.assertEqual(summary["remaining_submodels_pending"], 50)
        self.assertFalse(summary["final_9_model_benchmark_ready"])
        self.assertTrue(PROMOTED_LABELS.isdisjoint(set(summary["pending_labels"])))

    def test_promoted_rows_match_authoritative_yaml(self) -> None:
        rows, _summary = build_gate()
        authoritative = load_authoritative_spec()
        by_cutoff = authoritative.winner_by_cutoff()
        promoted = [row for row in rows if row["manuscript_label"] == PROMOTED_LABEL]
        self.assertEqual(len(promoted), 5)
        for row in promoted:
            winner = by_cutoff[row["cutoff"]]
            self.assertEqual(row["current_run_id"], winner.run_id)
            self.assertEqual(row["current_campaign_lineage"], CANONICAL_LINEAGE)
            self.assertEqual(row["target_status"], "authoritative_promoted")
            self.assertEqual(row["required_action"], "none")

    def test_pending_rows_are_all_non_keep_comparison_families(self) -> None:
        rows, summary = build_gate()
        pending = [row for row in rows if row["target_status"] != "authoritative_promoted"]
        self.assertEqual(len(pending), 20)
        self.assertEqual(sorted({row["manuscript_label"] for row in pending}), summary["pending_labels"])
        for row in pending:
            self.assertNotIn(row["manuscript_label"], PROMOTED_LABELS)
            self.assertEqual(row["paper_table_gate"], "blocks_final_9_model_table")
            if row["manuscript_label"] == "AL-M-T0":
                self.assertEqual(row["target_status"], "blocked_canonical_input_promotion")
                self.assertEqual(row["required_action"], "blocked_pending_al_drop_diagnostics_or_new_discount_spec")
            else:
                self.assertEqual(row["target_status"], "pending_canonical_input_promotion")
                self.assertEqual(row["required_action"], "rerun_or_promote_on_20260510_canonical_bundle")


if __name__ == "__main__":
    unittest.main()
