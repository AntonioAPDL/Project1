import csv
import math
import os
import subprocess
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_csv(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def _build_minimal_inputs(tmp_path: Path):
    dates_hist = ["2022-12-23", "2022-12-24", "2022-12-25"]
    dates_fore = ["2022-12-26", "2022-12-27", "2022-12-28"]

    retros_rows = [
        ["2022-12-23", 0.40, 0.30, 0.50],
        ["2022-12-24", 0.60, 0.45, 0.70],
        ["2022-12-25", 0.80, 0.55, 0.90],
    ]
    forecast_rows = [
        ["2022-12-26", 0.70, 0.90],
        ["2022-12-27", 0.80, 1.10],
        ["2022-12-28", 0.90, 1.20],
    ]

    _write_csv(tmp_path / "retros.csv", ["Date", "USGS", "GloFAS", "NWS3.0"], retros_rows)
    _write_csv(tmp_path / "nws.csv", ["target_date", "m1", "m2"], forecast_rows)
    _write_csv(tmp_path / "glo.csv", ["target_date", "m1", "m2"], forecast_rows)
    _write_csv(
        tmp_path / "usgs_daily.csv",
        ["Date", "discharge_cms"],
        [[d, v] for d, v in zip(dates_hist + dates_fore, [0.50, 0.70, 1.00, 1.20, 1.40])],
    )
    _write_csv(tmp_path / "ppt.csv", ["Date", "ppt"], [[d, v] for d, v in zip(dates_hist + dates_fore, [1, 2, 3, 4, 5])])
    _write_csv(tmp_path / "soil.csv", ["Date", "soil"], [[d, v] for d, v in zip(dates_hist + dates_fore, [10, 11, 12, 13, 14])])
    _write_csv(tmp_path / "pca.csv", ["time", "Static_PCA"], [[d, v] for d, v in zip(dates_hist + dates_fore, [0.1, 0.2, 0.3, 0.4, 0.5])])
    _write_csv(tmp_path / "eli.csv", ["time", "eli"], [["2192-12-23", 0.1], ["2192-12-24", 0.2], ["2192-12-25", 0.3]])
    _write_csv(tmp_path / "oni.csv", ["time", "oni"], [["2022-12-23", 0.1], ["2022-12-24", 0.2], ["2022-12-25", 0.3]])

    return {
        "retros": tmp_path / "retros.csv",
        "nws": tmp_path / "nws.csv",
        "glo": tmp_path / "glo.csv",
        "usgs_daily": tmp_path / "usgs_daily.csv",
        "ppt": tmp_path / "ppt.csv",
        "soil": tmp_path / "soil.csv",
        "pca": tmp_path / "pca.csv",
        "eli": tmp_path / "eli.csv",
        "oni": tmp_path / "oni.csv",
    }


def _run_r(script: str, env: dict):
    result = subprocess.run(
        ["Rscript", "--vanilla", "-e", script],
        cwd=REPO_ROOT,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def _read_rows(path: Path):
    with path.open() as f:
        return list(csv.DictReader(f))


def test_disc_w_retros_preserve_log1p_contract(tmp_path):
    inputs = _build_minimal_inputs(tmp_path)
    out_csv = tmp_path / "disc_w_y.csv"

    script = textwrap.dedent(
        f"""
        Sys.setenv(
          DISC_W_CUTOFF_DATE = "2022-12-25",
          DISC_W_FORECAST_START_DATE = "2022-12-26"
        )
        source("{(REPO_ROOT / 'R' / 'disc_w' / '_init.R').as_posix()}")
        paths <- list(
          prism_ppt_path = "{inputs['ppt'].as_posix()}",
          soil_moisture_path = "{inputs['soil'].as_posix()}",
          pca_components_path = "{inputs['pca'].as_posix()}",
          retros_path = "{inputs['retros'].as_posix()}"
        )
        bundle <- disc_w_build_covariates_and_retro(paths, ranges = c(3, 3))
        out <- data.frame(
          USGS = as.numeric(bundle$Y[1, ]),
          GloFAS = as.numeric(bundle$Y[2, ]),
          NWS3.0 = as.numeric(bundle$Y[3, ])
        )
        write.csv(out, "{out_csv.as_posix()}", row.names = FALSE)
        """
    )
    _run_r(script, {})

    rows = _read_rows(out_csv)
    assert [float(r["USGS"]) for r in rows] == [0.40, 0.60, 0.80]
    assert [float(r["GloFAS"]) for r in rows] == [0.30, 0.45, 0.55]
    assert [float(r["NWS3.0"]) for r in rows] == [0.50, 0.70, 0.90]


def test_environmetrics_data_inputs_follow_declared_scale_contract(tmp_path):
    inputs = _build_minimal_inputs(tmp_path)
    out_y_identity = tmp_path / "env_identity_y.csv"
    out_ens_identity = tmp_path / "env_identity_ens.csv"
    out_y_log = tmp_path / "env_log_y.csv"
    out_ens_log = tmp_path / "env_log_ens.csv"

    base_env = {
        "ENV_PROJECT_ROOT": str(REPO_ROOT),
        "ENV_RETROS_PATH": str(inputs["retros"]),
        "ENV_NWS_FORECAST_PATH": str(inputs["nws"]),
        "ENV_GLOFAS_FORECAST_PATH": str(inputs["glo"]),
        "ENV_USGS_DAILY_PATH": str(inputs["usgs_daily"]),
        "ENV_PPT_PATH": str(inputs["ppt"]),
        "ENV_SOIL_PATH": str(inputs["soil"]),
        "ENV_PCA_PATH": str(inputs["pca"]),
        "ENV_COV_ELI_PATH": str(inputs["eli"]),
        "ENV_COV_ONI_PATH": str(inputs["oni"]),
        "UNIFIED_CUTOFF_DATE": "2022-12-25",
        "UNIFIED_FORECAST_START_DATE": "2022-12-26",
        "UNIFIED_PLOT_START": "2022-12-23",
        "UNIFIED_PLOT_END": "2022-12-27",
    }

    script = textwrap.dedent(
        f"""
        suppressPackageStartupMessages(library(lubridate))
        suppressPackageStartupMessages(library(readr))
        source("R/environmetrics/00_paths.R")
        DATA_CBIND_RDS <- "{(tmp_path / 'data_cbind_tY_X.rds').as_posix()}"
        DATA_CBIND_CSV <- "{(tmp_path / 'data_cbind_tY_X.csv').as_posix()}"
        source("R/environmetrics/10_data_inputs.R")
        out_y <- data.frame(
          USGS = as.numeric(Y[1, ]),
          GloFAS = as.numeric(Y[2, ]),
          NWS3.0 = as.numeric(Y[3, ])
        )
        out_ens <- data.frame(
          glo_1 = as.numeric(ensembles[[1]][, 1]),
          nws_1 = as.numeric(ensembles[[2]][, 1])
        )
        write.csv(out_y, Sys.getenv("TEST_OUT_Y"), row.names = FALSE)
        write.csv(out_ens, Sys.getenv("TEST_OUT_ENS"), row.names = FALSE)
        """
    )

    identity_env = {
        **base_env,
        "UNIFIED_LEGACY_POST_INPUT_SCALE": "log1p_cms",
        "UNIFIED_ANALYSIS_SCALE_POST_INTERNAL": "log1p_cms",
        "TEST_OUT_Y": str(out_y_identity),
        "TEST_OUT_ENS": str(out_ens_identity),
    }
    _run_r(script, identity_env)

    log_env = {
        **base_env,
        "UNIFIED_LEGACY_POST_INPUT_SCALE": "log1p_cms",
        "UNIFIED_ANALYSIS_SCALE_POST_INTERNAL": "log_log1p_cms",
        "TEST_OUT_Y": str(out_y_log),
        "TEST_OUT_ENS": str(out_ens_log),
    }
    _run_r(script, log_env)

    identity_rows = _read_rows(out_y_identity)
    assert [float(r["USGS"]) for r in identity_rows] == [0.40, 0.60, 0.80]
    assert [float(r["GloFAS"]) for r in identity_rows] == [0.30, 0.45, 0.55]
    assert [float(r["NWS3.0"]) for r in identity_rows] == [0.50, 0.70, 0.90]

    identity_ens = _read_rows(out_ens_identity)
    assert [float(r["glo_1"]) for r in identity_ens] == [0.70, 0.80, 0.90]
    assert [float(r["nws_1"]) for r in identity_ens] == [0.70, 0.80, 0.90]

    log_rows = _read_rows(out_y_log)
    expected_usgs = [math.log(x) for x in (0.40, 0.60, 0.80)]
    expected_glofas = [math.log(x) for x in (0.30, 0.45, 0.55)]
    expected_nws = [math.log(x) for x in (0.50, 0.70, 0.90)]
    for got, exp in zip([float(r["USGS"]) for r in log_rows], expected_usgs):
        assert abs(got - exp) < 1e-12
    for got, exp in zip([float(r["GloFAS"]) for r in log_rows], expected_glofas):
        assert abs(got - exp) < 1e-12
    for got, exp in zip([float(r["NWS3.0"]) for r in log_rows], expected_nws):
        assert abs(got - exp) < 1e-12

    log_ens = _read_rows(out_ens_log)
    expected_fore = [math.log(0.70), math.log(0.80), math.log(0.90)]
    for got, exp in zip([float(r["glo_1"]) for r in log_ens], expected_fore):
        assert abs(got - exp) < 1e-12
    for got, exp in zip([float(r["nws_1"]) for r in log_ens], expected_fore):
        assert abs(got - exp) < 1e-12
