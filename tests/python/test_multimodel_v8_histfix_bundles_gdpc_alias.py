import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
import sys

sys.path.insert(0, str(ROOT / "scripts"))

import build_multimodel_v8_histfix_bundles as histfix  # noqa: E402


class HistfixBundlesGDPCRewireTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="histfix_gdpc_alias_"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_prepare_supporting_inputs_uses_canonical_gdpc_alias_for_pca(self):
        artifact_root = self.tmpdir / "artifact"
        legacy_root = self.tmpdir / "legacy_shared"
        (legacy_root / "covariates").mkdir(parents=True, exist_ok=True)
        (legacy_root / "parameters").mkdir(parents=True, exist_ok=True)

        (legacy_root / "parameters" / "parameters.txt").write_text("alpha=1\n", encoding="utf-8")
        for idx, name in enumerate(["ELI", "ONI", "PPT", "SOIL"], start=1):
            (legacy_root / "covariates" / f"cov_0{idx}_{name}.csv").write_text(
                f"time,{name}\n1987-05-29,{idx}\n", encoding="utf-8"
            )

        canonical_root = self.tmpdir / "canonical"
        (canonical_root / "outputs" / "compat").mkdir(parents=True, exist_ok=True)
        canonical_alias = canonical_root / "outputs" / "compat" / "cov_05_PCA.csv"
        canonical_alias.write_text("time,Static_PCA\n1987-05-29,9.5\n", encoding="utf-8")
        cfg = {
            "version": "vtest",
            "artifact_root": str(canonical_root),
            "canonical_window": {"start_date": "1987-05-29", "end_date": "2023-01-22"},
            "monthly_source_window": {"start_month": "1987-01-01", "end_month": "2023-01-01"},
            "postprocess": {
                "interpolation": {"method": "cubic_spline_with_linear_tail", "linear_tail_days": 30},
                "standardization": {"method": "zscore", "ddof": 1},
            },
            "gdpc": {
                "method": "gdpc",
                "component_name": "GDPC1",
                "k": 3,
                "tol": 1.0e-4,
                "niter_max": 500,
                "crit": "LOO",
                "require_convergence": True,
                "sign_rule": {"method": "positive_correlation", "anchor_index_id": "oni"},
            },
            "compatibility_aliases": [
                {"alias_filename": "cov_05_PCA.csv", "value_column": "Static_PCA"},
            ],
            "indices": [],
        }
        config_path = self.tmpdir / "canonical_gdpc_master_covariate.yaml"
        config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

        old_config = histfix.GDPC_CANONICAL_CONFIG
        old_covariates = histfix.COVARIATE_SOURCE_FILES
        old_params = histfix.PARAMETERS_SOURCE
        try:
            histfix.GDPC_CANONICAL_CONFIG = config_path
            histfix.COVARIATE_SOURCE_FILES = {
                "ELI": legacy_root / "covariates" / "cov_01_ELI.csv",
                "ONI": legacy_root / "covariates" / "cov_02_ONI.csv",
                "PPT": legacy_root / "covariates" / "cov_03_PPT.csv",
                "SOIL": legacy_root / "covariates" / "cov_04_SOIL.csv",
            }
            histfix.PARAMETERS_SOURCE = legacy_root / "parameters" / "parameters.txt"

            out = histfix._prepare_supporting_inputs(artifact_root)
            copied_pca = Path(out["PCA"])
            self.assertTrue(copied_pca.exists())
            self.assertEqual(copied_pca.read_text(encoding="utf-8"), canonical_alias.read_text(encoding="utf-8"))

            manifest = json.loads(Path(out["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["canonical_gdpc_pca_alias_source"], str(canonical_alias))
        finally:
            histfix.GDPC_CANONICAL_CONFIG = old_config
            histfix.COVARIATE_SOURCE_FILES = old_covariates
            histfix.PARAMETERS_SOURCE = old_params


if __name__ == "__main__":
    unittest.main()
