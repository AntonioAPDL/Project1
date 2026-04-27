import unittest

from scripts.build_ndlm_discount_crps_comparison import (
    CUTOFF_ORDER,
    CORRECTIONS_TEX,
    build_he_winner_table,
    collect_campaign_rows,
    parse_he2_table,
)


class NDLMDiscountCRPSComparisonTest(unittest.TestCase):
    def test_parse_he2_table_includes_ndlm_main_keep(self) -> None:
        he2 = parse_he2_table(CORRECTIONS_TEX)
        row = he2[he2["label"] == "N-M-T1"]
        self.assertEqual(len(row), 1)
        self.assertAlmostEqual(float(row.iloc[0]["2022-12-25"]), 0.5363, places=4)

    def test_he2_winner_for_final_cutoff_is_current_ndlm_main_keep(self) -> None:
        he2 = parse_he2_table(CORRECTIONS_TEX)
        winners = build_he_winner_table(he2)
        row = winners[winners["cutoff"] == "2022-12-25"].iloc[0]
        self.assertEqual(row["he_best_label"], "N-M-T1")
        self.assertAlmostEqual(float(row["he_best_crps"]), 0.5363, places=4)

    def test_collect_campaign_rows_finds_two_meaningful_discount_regimes(self) -> None:
        rows = collect_campaign_rows()
        self.assertTrue({"baseline_20260402", "postfix_20260421"}.issubset(set(rows["campaign"])))
        subset = rows[
            rows["campaign"].isin(["baseline_20260402", "postfix_20260421"])
            & rows["model_variant"].eq("ndlm_main_keep")
        ]
        self.assertEqual(set(subset["discount_label"]), {"baseline_tt_regime", "tuned_postfix_regime"})

    def test_collect_campaign_rows_covers_all_cutoffs_for_current_he_rows(self) -> None:
        rows = collect_campaign_rows()
        subset = rows[rows["campaign"] == "postfix_20260421"]
        observed = sorted(subset["cutoff"].unique().tolist())
        self.assertEqual(observed, CUTOFF_ORDER)


if __name__ == "__main__":
    unittest.main()
