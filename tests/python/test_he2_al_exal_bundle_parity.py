from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _generated_config(artifact_root: Path, run_id: str) -> Path:
    return artifact_root / "control" / "generated_configs" / f"{run_id}.yaml"


def _drop_none(value):
    if isinstance(value, dict):
        return {k: _drop_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_none(v) for v in value]
    return value


class He2AlExalBundleParityTests(unittest.TestCase):
    def _assert_pair_parity(
        self,
        *,
        al_artifact_root: Path,
        ex_artifact_root: Path,
        al_run_pattern: str,
        ex_run_pattern: str,
        cutoffs: list[str],
        model_key: str,
    ) -> None:
        for cutoff in cutoffs:
            al_cfg = _load_yaml(_generated_config(al_artifact_root, al_run_pattern.format(cutoff=cutoff)))
            ex_cfg = _load_yaml(_generated_config(ex_artifact_root, ex_run_pattern.format(cutoff=cutoff)))

            self.assertEqual(
                al_cfg["inputs"]["fit"]["retros_path"],
                ex_cfg["inputs"]["fit"]["retros_path"],
                msg=f"{cutoff}: retros path mismatch",
            )
            self.assertEqual(
                al_cfg["inputs"]["fit"]["nws_forecast_path"],
                ex_cfg["inputs"]["fit"]["nws_forecast_path"],
                msg=f"{cutoff}: nws path mismatch",
            )
            self.assertEqual(
                al_cfg["inputs"]["fit"]["glofas_forecast_path"],
                ex_cfg["inputs"]["fit"]["glofas_forecast_path"],
                msg=f"{cutoff}: glofas path mismatch",
            )
            self.assertEqual(
                al_cfg["inputs"]["fit"]["covariates"],
                ex_cfg["inputs"]["fit"]["covariates"],
                msg=f"{cutoff}: covariate bundle mismatch",
            )
            self.assertEqual(
                al_cfg["inputs"]["covariate_features"],
                ex_cfg["inputs"]["covariate_features"],
                msg=f"{cutoff}: covariate feature contract mismatch",
            )
            self.assertEqual(
                _drop_none(al_cfg["inputs"]["deterministic_climate"]),
                _drop_none(ex_cfg["inputs"]["deterministic_climate"]),
                msg=f"{cutoff}: deterministic climate contract mismatch",
            )
            self.assertEqual(
                al_cfg["run"]["threads"],
                ex_cfg["run"]["threads"],
                msg=f"{cutoff}: thread/runtime contract mismatch",
            )
            self.assertEqual(
                al_cfg["models"][model_key]["implementation_mode"],
                ex_cfg["models"][model_key]["implementation_mode"],
                msg=f"{cutoff}: implementation mode mismatch",
            )

    def test_multivar_keep_bundle_parity(self) -> None:
        self._assert_pair_parity(
            al_artifact_root=Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517"),
            ex_artifact_root=Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516"),
            al_run_pattern="multimodel_{cutoff}_v8_he2pubgdpc1r1_dqlm_multivar_al_keep",
            ex_run_pattern="multimodel_{cutoff}_v8_he2pubgdpc1r1_exdqlm_multivar_keep",
            cutoffs=["20210123", "20211112", "20211221", "20220511", "20221225"],
            model_key="exdqlm_multivar",
        )

    def test_multivar_drop_bundle_parity(self) -> None:
        self._assert_pair_parity(
            al_artifact_root=Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517"),
            ex_artifact_root=Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516"),
            al_run_pattern="multimodel_{cutoff}_v8_he2pubgdpc1r1_dqlm_multivar_al_drop",
            ex_run_pattern="multimodel_{cutoff}_v8_he2pubgdpc1r1_exdqlm_multivar_drop",
            cutoffs=["20210123", "20211112", "20211221", "20220511", "20221225"],
            model_key="exdqlm_multivar",
        )

    def test_univar_bundle_parity(self) -> None:
        self._assert_pair_parity(
            al_artifact_root=Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_univar_al_all_cutoffs_sharedspec_20260517"),
            ex_artifact_root=Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516"),
            al_run_pattern="multimodel_{cutoff}_v8_he2pubgdpc1r1_dqlm_univar_al",
            ex_run_pattern="multimodel_{cutoff}_v8_he2pubgdpc1r1_exdqlm_univar",
            cutoffs=["20210123", "20211112", "20211221", "20220511", "20221225"],
            model_key="exdqlm_univar",
        )


if __name__ == "__main__":
    unittest.main()
