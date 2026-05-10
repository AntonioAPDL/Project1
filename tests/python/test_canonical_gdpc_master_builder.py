import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
BUILDER = ROOT / "scripts" / "build_canonical_gdpc_master_covariate.py"


class CanonicalGDPCMasterBuilderTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="canonical_gdpc_builder_"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_builder_emits_canonical_factor_and_aliases(self):
        artifact_root = self.tmpdir / "artifact"
        (artifact_root / "intermediate").mkdir(parents=True, exist_ok=True)
        (artifact_root / "review" / "stationarity").mkdir(parents=True, exist_ok=True)

        time = pd.date_range("2000-01-01", periods=180, freq="D")
        base = np.sin(np.linspace(0, 8 * np.pi, len(time)))
        trend = np.linspace(-1.0, 1.0, len(time))
        noise = np.cos(np.linspace(0, 5 * np.pi, len(time)))
        df = pd.DataFrame(
            {
                "time": time.strftime("%Y-%m-%d"),
                "oni": base + 0.20 * trend,
                "amo": 0.8 * base + 0.4 * noise,
                "gmt": 0.5 * base + 0.7 * trend,
            }
        )
        for col in ["oni", "amo", "gmt"]:
            values = df[col].to_numpy()
            df[col] = (values - values.mean()) / values.std(ddof=1)

        std_csv = artifact_root / "intermediate" / "combined_climate_indices_daily_standardized_20000101_20000628.csv"
        df.to_csv(std_csv, index=False)

        stationarity_md = artifact_root / "review" / "stationarity" / "CANONICAL_GDPC_STATIONARITY_AUDIT.md"
        stationarity_md.write_text("keep all in levels\n", encoding="utf-8")

        config = {
            "version": "vtest",
            "artifact_root": str(artifact_root),
            "canonical_window": {"start_date": "2000-01-01", "end_date": "2000-06-28"},
            "monthly_source_window": {"start_month": "2000-01-01", "end_month": "2000-06-01"},
            "postprocess": {
                "interpolation": {"method": "cubic_spline_with_linear_tail", "linear_tail_days": 30},
                "standardization": {"method": "zscore", "ddof": 1},
            },
            "gdpc": {
                "method": "gdpc",
                "component_name": "GDPC1",
                "k": 1,
                "tol": 1.0e-4,
                "niter_max": 200,
                "crit": "LOO",
                "require_convergence": True,
                "sign_rule": {"method": "positive_correlation", "anchor_index_id": "oni"},
            },
            "compatibility_aliases": [
                {"alias_filename": "cov_03_PCA.csv", "value_column": "Static_PCA"},
                {"alias_filename": "cov_05_PCA.csv", "value_column": "Static_PCA"},
            ],
            "indices": [
                {"index_id": "oni", "display_name": "ONI", "url": "https://example.test/oni"},
                {"index_id": "amo", "display_name": "AMO", "url": "https://example.test/amo"},
                {"index_id": "gmt", "display_name": "GMT", "url": "https://example.test/gmt"},
            ],
        }
        config_path = self.tmpdir / "canonical_gdpc_master_covariate.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

        subprocess.run(
            ["python3", str(BUILDER), "--config", str(config_path)],
            cwd=ROOT,
            check=True,
        )

        factor_csv = artifact_root / "outputs" / "gdpc_master_component_01_20000101_20000628.csv"
        alias_csv = artifact_root / "outputs" / "compat" / "cov_05_PCA.csv"
        alias_manifest = artifact_root / "metadata" / "compatibility_alias_manifest.csv"
        metadata_json = artifact_root / "metadata" / "gdpc_build_metadata.json"
        review_md = artifact_root / "review" / "CANONICAL_GDPC_BUILD_REVIEW.md"

        self.assertTrue(factor_csv.exists())
        self.assertTrue(alias_csv.exists())
        self.assertTrue(alias_manifest.exists())
        self.assertTrue(metadata_json.exists())
        self.assertTrue(review_md.exists())

        factor_df = pd.read_csv(factor_csv)
        alias_df = pd.read_csv(alias_csv)
        self.assertEqual(factor_df.columns.tolist(), ["time", "GDPC1"])
        self.assertEqual(alias_df.columns.tolist(), ["time", "Static_PCA"])
        self.assertTrue(np.allclose(factor_df["GDPC1"].to_numpy(), alias_df["Static_PCA"].to_numpy()))

        metadata = json.loads(metadata_json.read_text(encoding="utf-8"))
        self.assertTrue(metadata["gdpc"]["conv"])
        self.assertGreaterEqual(metadata["sign_rule"]["anchor_correlation_after"], 0.0)
        self.assertEqual(len(metadata["alias_outputs"]), 2)


if __name__ == "__main__":
    unittest.main()
