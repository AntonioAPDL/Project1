from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts" / "build_he2_ndlm_main_keep_broad_screen_configs.py"
VALIDATOR = ROOT / "scripts" / "validate_he2_ndlm_main_keep_broad_screen_prelaunch.py"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def ymd(cutoff: str) -> str:
    return f"{cutoff[:4]}-{cutoff[4:6]}-{cutoff[6:8]}"


def future_dates(cutoff: str, n: int = 3) -> list[str]:
    start = datetime.strptime(ymd(cutoff), "%Y-%m-%d") + timedelta(days=1)
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]


def write_full_usgs_truth(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dates = ["1987-05-29", "1987-05-30", "1987-05-31", "1987-06-01", "1987-06-02"]
    for cutoff in ["20210123", "20211112", "20211221", "20220511", "20221225"]:
        dates.extend(future_dates(cutoff, n=5))
    rows = ["date,discharge_cms,discharge_cfs,qualifiers"]
    for i, date in enumerate(sorted(set(dates)), start=1):
        rows.append(f"{date},{1.0 + i / 100.0},{35.0 + i},A")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def make_source_run(root: Path, cutoff: str) -> tuple[Path, Path]:
    run_root = root / f"source_{cutoff}"
    fdates = future_dates(cutoff, n=3)
    for rel, text in {
        "inputs/shared/parameters/parameters.txt": "site=11160500\n",
        "inputs/shared/retros/retros.csv": "date,usgs,nws,glofas\n1987-05-29,1,1,1\n",
        "inputs/shared/forecasts/nws_forecast.csv": "date,q50\n" + "\n".join(f"{date},1" for date in fdates) + "\n",
        "inputs/shared/forecasts/glofas_forecast.csv": "date,m01\n" + "\n".join(f"{date},1" for date in fdates) + "\n",
        "inputs/shared/usgs/usgs_daily.csv": f"date,flow\n1987-05-29,1\n{ymd(cutoff)},1\n",
        "inputs/shared/covariates/cov_01_PPT.csv": "date,value\n1987-05-29,1\n",
        "inputs/shared/covariates/cov_02_SOIL.csv": "date,value\n1987-05-29,1\n",
        "inputs/shared/covariates/cov_03_PCA.csv": "date,value\n1987-05-29,1\n",
    }.items():
        path = run_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    full_usgs_truth = root / "full_usgs_truth.csv"
    if not full_usgs_truth.exists():
        write_full_usgs_truth(full_usgs_truth)
    cfg = {
        "run": {
            "run_id": f"source_{cutoff}",
            "run_root": str(root),
            "threads": {"omp": 1, "openblas": 1, "mkl": 1, "veclib": 1, "numexpr": 1, "mc_cores": 1},
        },
        "dates": {"cutoff_date": f"{cutoff[:4]}-{cutoff[4:6]}-{cutoff[6:8]}", "data_start": "1987-05-29"},
        "stages": {"forecats": False, "data_prep_shared": True, "fit": True, "post": True, "validate": True, "report": True},
        "models": {
            "run_exdqlm_multivar": False,
            "run_exdqlm_univar": False,
            "run_ndlm_main": True,
            "run_ndlm_univar": False,
            "ndlm_main": {
                "forecast_transfer_mode": "keep",
                "implementation_mode": "theory_aligned",
                "kalman_backend": "cpp",
                "seasonality": {"harmonics": [1, 2, 1 / 6.8068493]},
                "state_evolution": {
                    "df_t": 0.99999999,
                    "df_s1": 0.99999999,
                    "df_s2": 0.99999999,
                    "df_s67": 0.99999999,
                    "df_discrep": 0.99999999,
                    "lambda": 0.97,
                    "df_trans": 0.9999999,
                    "df_covs": 0.99999999,
                },
                "prior": {"forecast_cov": {"c_factor": 1.0, "epsilon": None, "dof_offset": 4, "scale_mult": 1.0, "jitter": 1e-8}},
            },
        },
        "fit": {"parallel": {"workers": 1}, "ndlm_main": {"gamma_sigma": {"min_total_iters": 20, "max_iter": 100}}},
        "inputs": {
            "fit": {"usgs_cache_path": str(full_usgs_truth), "covariates": []},
            "shared": {"prefer_forecats_snapshot": False},
            "transfer_function_covariates": {
                "base_covariates": ["PPT", "SOIL", "PCA"],
                "engineered_terms": ["PPT_sq", "SOIL_sq", "PPT_x_SOIL"],
            },
        },
        "scale_contract": {"analysis_scale_fit_internal": "log1p_cms"},
        "post": {},
    }
    config_path = run_root / "resolved_config.yaml"
    write_yaml(config_path, cfg)
    return run_root, config_path


class He2NdlmMainKeepBroadScreenTests(unittest.TestCase):
    def test_builder_and_validator_prepare_1440_one_core_rows(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nmt1_broad_screen_") as tmpdir:
            tmp = Path(tmpdir)
            source_root = tmp / "sources"
            rows: list[dict[str, str]] = []
            for cutoff in ["20210123", "20211112", "20211221", "20220511", "20221225"]:
                run_root, config_path = make_source_run(source_root, cutoff)
                rows.append(
                    {
                        "authority_class": "article_crps_table",
                        "cutoff": cutoff,
                        "row_label": "N-M-T1",
                        "source_class": "ndlm_main_keep",
                        "mean_crps": "1.0",
                        "resolved_config": str(config_path),
                        "run_root": str(run_root),
                        "run_id": f"source_{cutoff}",
                    }
                )
            authority = tmp / "authority_rows.csv"
            write_csv(authority, rows)
            artifact_root = tmp / "artifact_root"
            matrix_dir = artifact_root / "control" / "matrix"
            config_dir = artifact_root / "control" / "configs"

            build = subprocess.run(
                [
                    "python3",
                    str(BUILDER),
                    "--authority-rows",
                    str(authority),
                    "--artifact-root",
                    str(artifact_root),
                    "--matrix-dir",
                    str(matrix_dir),
                    "--config-output-dir",
                    str(config_dir),
                    "--reset-status",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(build.returncode, 0, msg=f"STDOUT:\n{build.stdout}\nSTDERR:\n{build.stderr}")
            with (matrix_dir / "matrix_plan.csv").open("r", encoding="utf-8") as handle:
                plan = list(csv.DictReader(handle))
            self.assertEqual(len(plan), 1440)
            self.assertEqual({row["lane"] for row in plan}, {"ndlm_main_keep"})
            self.assertEqual({row["quantile_submodels"] for row in plan}, {"1"})
            self.assertEqual(len({row["grid_spec_id"] for row in plan}), 288)

            sample_cfg = yaml.safe_load(Path(plan[0]["config_path"]).read_text(encoding="utf-8"))
            self.assertTrue(sample_cfg["models"]["run_ndlm_main"])
            self.assertFalse(sample_cfg["models"]["run_exdqlm_multivar"])
            self.assertEqual(sample_cfg["models"]["ndlm_main"]["forecast_transfer_mode"], "keep")
            self.assertEqual(sample_cfg["fit"]["ndlm_main"]["gamma_sigma"]["max_iter"], 100)
            self.assertEqual(sample_cfg["run"]["threads"]["mc_cores"], 1)
            self.assertEqual(sample_cfg["models"]["ndlm_main"]["prior"]["forecast_cov"]["epsilon"], 1.0)
            self.assertEqual(Path(sample_cfg["inputs"]["fit"]["usgs_cache_path"]).name, "full_usgs_truth.csv")

            validate = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--matrix-dir",
                    str(matrix_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(validate.returncode, 0, msg=f"STDOUT:\n{validate.stdout}\nSTDERR:\n{validate.stderr}")
            metadata = yaml.safe_load((matrix_dir / "matrix_metadata.yaml").read_text(encoding="utf-8"))
            self.assertEqual(metadata["queue"]["ordinary_max_concurrent"], 3)
            self.assertEqual(metadata["queue"]["heavy_cutoff_max_concurrent"], 1)
            self.assertTrue(metadata["queue"]["cleanup_rdata_after_post"])

    def test_validator_rejects_cutoff_truncated_usgs_truth(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nmt1_broad_screen_bad_truth_") as tmpdir:
            tmp = Path(tmpdir)
            source_root = tmp / "sources"
            rows: list[dict[str, str]] = []
            for cutoff in ["20210123", "20211112", "20211221", "20220511", "20221225"]:
                run_root, config_path = make_source_run(source_root, cutoff)
                rows.append(
                    {
                        "authority_class": "article_crps_table",
                        "cutoff": cutoff,
                        "row_label": "N-M-T1",
                        "source_class": "ndlm_main_keep",
                        "mean_crps": "1.0",
                        "resolved_config": str(config_path),
                        "run_root": str(run_root),
                        "run_id": f"source_{cutoff}",
                    }
                )
            authority = tmp / "authority_rows.csv"
            write_csv(authority, rows)
            artifact_root = tmp / "artifact_root"
            matrix_dir = artifact_root / "control" / "matrix"
            config_dir = artifact_root / "control" / "configs"

            build = subprocess.run(
                [
                    "python3",
                    str(BUILDER),
                    "--authority-rows",
                    str(authority),
                    "--artifact-root",
                    str(artifact_root),
                    "--matrix-dir",
                    str(matrix_dir),
                    "--config-output-dir",
                    str(config_dir),
                    "--reset-status",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(build.returncode, 0, msg=f"STDOUT:\n{build.stdout}\nSTDERR:\n{build.stderr}")

            with (matrix_dir / "matrix_plan.csv").open("r", encoding="utf-8") as handle:
                first = next(csv.DictReader(handle))
            cfg_path = Path(first["config_path"])
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            cutoff_snapshot = Path(cfg["debug_he2_ndlm_main_keep_broad_screen"]["source_run_root"]) / "inputs/shared/usgs/usgs_daily.csv"
            cfg["inputs"]["fit"]["usgs_cache_path"] = str(cutoff_snapshot)
            write_yaml(cfg_path, cfg)

            validate = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--artifact-root",
                    str(artifact_root),
                    "--matrix-dir",
                    str(matrix_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(validate.returncode, 0, msg=f"STDOUT:\n{validate.stdout}\nSTDERR:\n{validate.stderr}")
            checks = (matrix_dir / "prelaunch_validation_checks.csv").read_text(encoding="utf-8")
            self.assertIn("usgs_truth_extends_through_forecast_window", checks)


if __name__ == "__main__":
    unittest.main()
