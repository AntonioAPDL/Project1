import unittest

from scripts.build_ndlm_reaudit_postcorrection_reports import (
    build_anomaly_digest,
    build_runtime_inventory,
)


class TestNDLMReauditPostCorrectionReports(unittest.TestCase):
    def test_anomaly_digest_identifies_multivariate_keep_outlier(self) -> None:
        rows = build_anomaly_digest()
        self.assertEqual(len(rows), 15)
        self.assertEqual(
            rows[0]["run_name"],
            "multimodel_20211221_v8_ndlm_featurecov_v1_ndlm_main_keep",
        )
        self.assertGreater(float(rows[0]["max_q95_log1p"]), 1000.0)
        self.assertGreater(float(rows[0]["ensemble_max_q95_log1p"]), 1.0)
        self.assertLess(float(rows[0]["quantile_max_q95_log1p"]), 10.0)
        univar_rows = [row for row in rows if row["model_variant"] == "ndlm_univar_keep"]
        self.assertEqual(len(univar_rows), 5)
        self.assertTrue(all(row["ensemble_max_q95_log1p"] is None for row in univar_rows))

    def test_runtime_inventory_covers_all_corrected_rows(self) -> None:
        rows = build_runtime_inventory()
        self.assertEqual(len(rows), 15)
        self.assertTrue(all(row["post_crps_summary_exists"] == "True" for row in rows))
        self.assertTrue(all(row["post_quantiles_exists"] == "True" for row in rows))
        main_rows = [row for row in rows if row["model_variant"].startswith("ndlm_main")]
        univar_rows = [row for row in rows if row["model_variant"] == "ndlm_univar_keep"]
        self.assertTrue(all(row["diag_covariance_exists"] == "True" for row in main_rows))
        self.assertTrue(all(row["diag_covariance_exists"] == "False" for row in univar_rows))
        self.assertTrue(all(row["diag_ensemble_summary_exists"] == "True" for row in main_rows))
        self.assertTrue(all(row["diag_ensemble_summary_exists"] == "False" for row in univar_rows))


if __name__ == "__main__":
    unittest.main()
