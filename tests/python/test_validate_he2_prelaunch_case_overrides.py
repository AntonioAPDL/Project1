from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_he2_bayesian_publication_relaunch_prelaunch.py"


def _load_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("validate_he2_prelaunch", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ValidateHe2PrelaunchCaseOverridesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def test_normalize_quantile_smoke_cases_preserves_case_overrides(self) -> None:
        cases = self.mod._normalize_quantile_smoke_cases(
            {
                "quantile_fit_smoke_cases": [
                    {
                        "family": "dqlm_multivar_al_keep",
                        "cutoff": "20221225",
                        "quantiles": [0.65],
                        "fit_overrides": {
                            "exdqlm_multivar": {
                                "gamma_sigma": {
                                    "min_update_iters": 50,
                                    "min_total_iters": 50,
                                    "max_iter": 100,
                                }
                            }
                        },
                    }
                ]
            },
            cases_key="quantile_fit_smoke_cases",
            family_key="quantile_fit_smoke_family",
            cutoff_key="quantile_fit_smoke_cutoff",
            quantiles_key="quantile_fit_smoke_quantiles",
            default_family="dqlm_multivar_al_keep",
            default_cutoff="20210123",
            default_quantiles=[0.5],
        )
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["quantiles"], [0.65])
        self.assertEqual(
            cases[0]["fit_overrides"]["exdqlm_multivar"]["gamma_sigma"],
            {"min_update_iters": 50, "min_total_iters": 50, "max_iter": 100},
        )

    def test_case_overrides_merge_over_global_smoke_overrides(self) -> None:
        merged = self.mod.deep_merge_dict(
            {
                "exdqlm_multivar": {
                    "gamma_sigma": {
                        "min_update_iters": 6,
                        "min_total_iters": 12,
                        "max_iter": 18,
                    },
                    "legacy": {"n_samp": 512},
                }
            },
            {
                "exdqlm_multivar": {
                    "gamma_sigma": {
                        "min_update_iters": 50,
                        "min_total_iters": 50,
                        "max_iter": 100,
                    }
                }
            },
        )
        self.assertEqual(
            merged["exdqlm_multivar"]["gamma_sigma"],
            {"min_update_iters": 50, "min_total_iters": 50, "max_iter": 100},
        )
        self.assertEqual(merged["exdqlm_multivar"]["legacy"]["n_samp"], 512)


if __name__ == "__main__":
    unittest.main()
