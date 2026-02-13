from __future__ import annotations

import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
CFG_PATH = REPO_ROOT / "config" / "unified_runs" / "production_canonical_family.yaml"


class ProductionCanonicalFamilyConfigTests(unittest.TestCase):
    def test_config_parses_and_declares_canonical_production_contract(self) -> None:
        self.assertTrue(CFG_PATH.exists(), f"missing config: {CFG_PATH}")
        cfg = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(cfg, dict)

        models = cfg.get("models") or {}
        self.assertTrue(models.get("run_exdqlm_multivar"))
        self.assertTrue(models.get("run_exdqlm_univar"))
        self.assertTrue(models.get("run_ndlm_main"))

        univar_mode = ((models.get("exdqlm_univar") or {}).get("implementation_mode"))
        ndlm_mode = ((models.get("ndlm_main") or {}).get("implementation_mode"))
        self.assertEqual(univar_mode, "theory_aligned")
        self.assertEqual(ndlm_mode, "theory_aligned")

        fit = cfg.get("fit") or {}
        quantiles = fit.get("quantiles") or []
        norm = [round(float(q), 8) for q in quantiles]
        self.assertEqual(norm, [0.01, 0.05, 0.10, 0.50, 0.90, 0.95, 0.99])

        validation = cfg.get("validation") or {}
        self.assertEqual(validation.get("profile"), "production")

        write_audit = cfg.get("write_audit") or {}
        self.assertEqual(int(write_audit.get("enforce_from_stage")), 4)


if __name__ == "__main__":
    unittest.main()
