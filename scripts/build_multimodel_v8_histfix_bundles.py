#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from canonical_climate_indices_lib import canonical_paths, gdpc_compat_alias_paths, load_config
from he2_publication_relaunch_lib import selected_window_retros_by_cutoff
from multimodel_v8_lib import ensure_dir

SITE_ID = "11160500"
SITE_LAT = 37.0443931
SITE_LON = -122.072464
WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
GDPC_CANONICAL_CONFIG = WORKFLOW_ROOT / "config" / "canonical_gdpc_master_covariate.yaml"
DEFAULT_CUTOFFS = ["20211221", "20220511", "20221225"]
DEFAULT_DATA_START = "1987-05-29"
DEFAULT_BUNDLE_RUN_ID = "20260407_long_history_r01"
DEFAULT_GLOFAS_READY_END = "2022-12-25"

CURRENT_V8_RUNTIME_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402"
)
RECOVERY_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "data_recovery/site=11160500/"
    "recovery_run=site11160500_recovery_20260406T185022Z"
)
USGS_DAILY_SOURCE = RECOVERY_ROOT / (
    "family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/"
    "outputs/usgs_daily_flow_11160500.csv"
)
GLOFAS_V21_ZIP_ROOT = RECOVERY_ROOT / (
    "family=glofas_historical/full_runs/source_native_tranche1_20260406T194500Z/"
    "outputs/historical_zips/hist_v21_htessel_cons"
)
GLOFAS_V31_ZIP_ROOT = RECOVERY_ROOT / (
    "family=glofas_historical/full_runs/source_native_tranche1_20260406T194500Z/"
    "outputs/historical_zips/hist_v31_lisflood_cons"
)
NWS_RETRO_V21_HOURLY = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_BACKUP_20260121_010041/"
    "11160500_nws_retro_old.csv"
)
NWS_RETRO_V30_HOURLY = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_BACKUP_20260121_010041/"
    "11160500_nws_retro.csv"
)
LONG_HISTORY_SHARED_ROOT = CURRENT_V8_RUNTIME_ROOT / "runs" / "multimodel_20210123_v8_epsTT_l1" / "inputs" / "shared"
CUTOFF_TO_DATE = {
    "20210123": "2021-01-23",
    "20211112": "2021-11-12",
    "20211221": "2021-12-21",
    "20220511": "2022-05-11",
    "20221225": "2022-12-25",
}
GLOFAS_PRODUCT_BY_CUTOFF = {
    "20210123": "v21",
    "20211112": "v31",
    "20211221": "v31",
    "20220511": "v31",
    "20221225": "v31",
}
GLOFAS_PRODUCTS = {
    "v21": {
        "product_id": "hist_v21_htessel_cons",
        "source_id": "glofas_hist_v21_htessel_cons",
        "zip_root": GLOFAS_V21_ZIP_ROOT,
    },
    "v31": {
        "product_id": "hist_v31_lisflood_cons",
        "source_id": "glofas_hist_v31_lisflood_cons",
        "zip_root": GLOFAS_V31_ZIP_ROOT,
    },
}
NWS_PRIMARY_SOURCE_ID = "nws_retro_v21"
NWS_TAIL_FILL_SOURCE_ID = "nws_retro_v30"
NWS_TAIL_FILL_START = "2021-01-01"
NWS_SELECTED_WINDOW_SOURCE_ID = "nws_selected_window_retro"

COVARIATE_SOURCE_FILES = {
    "ELI": LONG_HISTORY_SHARED_ROOT / "covariates" / "cov_01_ELI.csv",
    "ONI": LONG_HISTORY_SHARED_ROOT / "covariates" / "cov_02_ONI.csv",
    "PPT": LONG_HISTORY_SHARED_ROOT / "covariates" / "cov_03_PPT.csv",
    "SOIL": LONG_HISTORY_SHARED_ROOT / "covariates" / "cov_04_SOIL.csv",
}
PARAMETERS_SOURCE = LONG_HISTORY_SHARED_ROOT / "parameters" / "parameters.txt"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build isolated long-history hist-fix forecats bundles for v8 reruns.")
    ap.add_argument(
        "--artifact-root",
        default="/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407",
        help="Runtime artifact root for the isolated hist-fix campaign.",
    )
    ap.add_argument("--bundle-run-id", default=DEFAULT_BUNDLE_RUN_ID)
    ap.add_argument("--cutoffs", nargs="*", default=DEFAULT_CUTOFFS)
    ap.add_argument("--data-start", default=DEFAULT_DATA_START)
    ap.add_argument("--glofas-ready-end", default=DEFAULT_GLOFAS_READY_END)
    ap.add_argument("--force-glofas-extract", action="store_true")
    return ap.parse_args()


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at {path}")
    return data


def _copy_file(src: Path, dst: Path) -> Path:
    if not src.exists():
        raise FileNotFoundError(src)
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return dst


def _canonical_pca_alias_path(alias_filename: str = "cov_05_PCA.csv") -> Path:
    cfg = load_config(GDPC_CANONICAL_CONFIG)
    paths = canonical_paths(cfg)
    aliases = gdpc_compat_alias_paths(cfg, paths)
    alias_path = aliases.get(alias_filename)
    if alias_path is None:
        raise KeyError(f"Canonical GDPC alias '{alias_filename}' is not defined in {GDPC_CANONICAL_CONFIG}")
    if not alias_path.exists():
        raise FileNotFoundError(
            f"Canonical GDPC alias is missing: {alias_path}. Run run_canonical_gdpc_master_pipeline.py first."
        )
    return alias_path


def _build_nws_daily(hourly_path: Path, out_csv: Path, source_id: str) -> Path:
    if out_csv.exists():
        return out_csv
    df = pd.read_csv(hourly_path)
    dt = pd.to_datetime(df["Date"])
    daily = (
        df.assign(date=dt.dt.strftime("%Y-%m-%d"), discharge_cms=pd.to_numeric(df["streamflow"], errors="coerce"))
        .groupby("date", as_index=False)["discharge_cms"]
        .mean()
        .sort_values("date")
        .reset_index(drop=True)
    )
    daily["source_id"] = source_id
    ensure_dir(out_csv.parent)
    daily.to_csv(out_csv, index=False)
    return out_csv


def _glofas_product_info(cutoff: str) -> dict[str, Any]:
    product_key = GLOFAS_PRODUCT_BY_CUTOFF.get(cutoff)
    if product_key is None:
        raise KeyError(f"No GloFAS product mapping defined for cutoff {cutoff}")
    info = GLOFAS_PRODUCTS.get(product_key)
    if info is None:
        raise KeyError(f"Unknown GloFAS product key {product_key!r} for cutoff {cutoff}")
    return info


def _ensure_glofas_point_series(
    artifact_root: Path,
    *,
    cutoff: str,
    required_end: str,
    force: bool = False,
) -> tuple[Path, Path, dict[str, Any]]:
    info = _glofas_product_info(cutoff)
    product_id = str(info["product_id"])
    zip_root = Path(info["zip_root"])
    out_csv = artifact_root / "source_series" / f"{product_id}_point.csv"
    out_meta = artifact_root / "source_series" / f"{product_id}_point.meta.json"
    if out_csv.exists() and out_meta.exists() and not force:
        meta = json.loads(out_meta.read_text(encoding="utf-8"))
        if str(meta.get("end_date", "")).strip() >= required_end:
            return out_csv, out_meta, info
    ensure_dir(out_csv.parent)
    cmd = [
        "python3",
        "scripts/forecats_extract_glofas_historical_point.py",
        "--campaign-root",
        str(zip_root),
        "--out-csv",
        str(out_csv),
        "--out-meta",
        str(out_meta),
        "--lat",
        str(SITE_LAT),
        "--lon",
        str(SITE_LON),
        "--start-date",
        DEFAULT_DATA_START,
        "--end-date",
        required_end,
    ]
    subprocess.run(cmd, check=True)
    meta = json.loads(out_meta.read_text(encoding="utf-8"))
    if str(meta.get("end_date", "")).strip() < required_end:
        raise RuntimeError(
            f"GloFAS point series {product_id} is incomplete. Required end_date>={required_end}, "
            f"observed {meta.get('end_date', '')}"
        )
    return out_csv, out_meta, info


def _prepare_supporting_inputs(artifact_root: Path) -> dict[str, Path]:
    support_root = artifact_root / "supporting_inputs"
    out = {
        "parameters": support_root / "parameters" / "parameters.txt",
        "ELI": support_root / "covariates" / "cov_01_ELI.csv",
        "ONI": support_root / "covariates" / "cov_02_ONI.csv",
        "PPT": support_root / "covariates" / "cov_03_PPT.csv",
        "SOIL": support_root / "covariates" / "cov_04_SOIL.csv",
        "PCA": support_root / "covariates" / "cov_05_PCA.csv",
    }
    canonical_pca_source = _canonical_pca_alias_path("cov_05_PCA.csv")
    _copy_file(PARAMETERS_SOURCE, out["parameters"])
    for key, src in COVARIATE_SOURCE_FILES.items():
        _copy_file(src, out[key])
    _copy_file(canonical_pca_source, out["PCA"])
    manifest = support_root / "support_manifest.json"
    payload = {
        "created_at_utc": utc_now(),
        "source_root": str(LONG_HISTORY_SHARED_ROOT),
        "canonical_gdpc_config": str(GDPC_CANONICAL_CONFIG),
        "canonical_gdpc_pca_alias_source": str(canonical_pca_source),
        "parameters": str(out["parameters"]),
        "covariates": {k: str(v) for k, v in out.items() if k != "parameters"},
    }
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    out["manifest"] = manifest
    return out


def _load_usgs_daily() -> pd.DataFrame:
    df = pd.read_csv(USGS_DAILY_SOURCE)
    out = df.loc[:, ["date", "discharge_cms"]].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out["discharge_cms"] = pd.to_numeric(out["discharge_cms"], errors="coerce")
    out["source_id"] = "usgs_daily_flow"
    return out


def _load_glofas_daily(glofas_csv: Path, source_id: str) -> pd.DataFrame:
    df = pd.read_csv(glofas_csv)
    out = df.loc[:, ["date", "discharge_cms"]].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out["discharge_cms"] = pd.to_numeric(out["discharge_cms"], errors="coerce")
    out["source_id"] = source_id
    return out


def _load_nws_hybrid(v21_daily_csv: Path, v30_daily_csv: Path, cutoff_date: str) -> pd.DataFrame:
    v21 = pd.read_csv(v21_daily_csv)
    v30 = pd.read_csv(v30_daily_csv)
    v21["date"] = pd.to_datetime(v21["date"]).dt.strftime("%Y-%m-%d")
    v30["date"] = pd.to_datetime(v30["date"]).dt.strftime("%Y-%m-%d")
    cutoff_ts = pd.Timestamp(cutoff_date)
    v21 = v21.loc[pd.to_datetime(v21["date"]) <= cutoff_ts].copy()
    v30 = v30.loc[pd.to_datetime(v30["date"]) <= cutoff_ts].copy()
    v21_tail_end = pd.to_datetime(v21["date"]).max()
    if pd.isna(v21_tail_end):
        raise RuntimeError("NWS v2.1 daily retrospective is empty.")
    tail_fill = v30.loc[pd.to_datetime(v30["date"]) > v21_tail_end].copy()
    hybrid = pd.concat([v21, tail_fill], ignore_index=True)
    hybrid = hybrid.sort_values("date").drop_duplicates(subset=["date"], keep="first").reset_index(drop=True)
    return hybrid.loc[:, ["date", "discharge_cms", "source_id"]]


def _load_selected_window_retros(path: Path, cutoff_date: str) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "Date" not in df.columns:
        raise RuntimeError(f"Selected-window retros is missing Date column: {path}")
    cutoff_ts = pd.Timestamp(cutoff_date)
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df["Date"]),
            "usgs_cms_selected": np.expm1(pd.to_numeric(df["USGS"], errors="coerce")),
            "glofas_cms_selected": np.expm1(pd.to_numeric(df["GloFAS"], errors="coerce")),
            "nws_cms_selected": np.expm1(pd.to_numeric(df["NWS3.0"], errors="coerce")),
        }
    )
    out = out.loc[out["date"] <= cutoff_ts].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out


def _require_daily_complete(df: pd.DataFrame, start_date: str, end_date: str, label: str) -> pd.DataFrame:
    full_dates = pd.date_range(start_date, end_date, freq="D").strftime("%Y-%m-%d")
    full = pd.DataFrame({"date": full_dates})
    merged = full.merge(df, on="date", how="left")
    missing = merged.loc[~np.isfinite(pd.to_numeric(merged["discharge_cms"], errors="coerce")), "date"].tolist()
    if missing:
        preview = ", ".join(missing[:10])
        raise RuntimeError(f"{label} is missing {len(missing)} daily rows between {start_date} and {end_date}. First gaps: {preview}")
    return merged


def _stabilize_positive_history(
    raws: pd.DataFrame,
    *,
    column: str,
    selected_column: str | None = None,
) -> dict[str, Any]:
    series = pd.to_numeric(raws[column], errors="coerce")
    if series.isna().any():
        bad = raws.loc[series.isna(), "date"].astype(str).tolist()
        raise RuntimeError(f"{column} contains NA values before positivity stabilization. First problematic dates: {bad[:10]}")
    positive = series[series > 0]
    if positive.empty:
        raise RuntimeError(f"{column} has no strictly positive values; cannot derive deterministic floor.")
    floor_value = float(positive.min())
    zero_mask = series <= 0
    zero_count = int(zero_mask.sum())
    selected_zero_count = 0
    if selected_column and selected_column in raws.columns:
        selected_series = pd.to_numeric(raws[selected_column], errors="coerce")
        selected_zero_count = int(((selected_series <= 0) & selected_series.notna()).sum())
    if zero_count > 0:
        raws.loc[zero_mask, column] = floor_value
    return {
        "column": column,
        "floor_value_cms": floor_value,
        "replaced_nonpositive_count": zero_count,
        "selected_window_nonpositive_count": selected_zero_count,
    }


def _fit_forecast_bundle_root(cutoff: str) -> Path:
    return (
        CURRENT_V8_RUNTIME_ROOT
        / "runs"
        / f"multimodel_{cutoff}_v8_epsTT_l1"
        / "inputs"
        / "shared"
        / "forecats_bundle"
    )


def _load_plot_window(cutoff: str) -> tuple[str, str]:
    cfg_path = Path("config") / "unified_runs" / f"multimodel_{cutoff}_v8_epsTT_l1.yaml"
    cfg = _read_yaml(cfg_path)
    dates = cfg.get("dates", {})
    return str(dates.get("plot_start")), str(dates.get("plot_end"))


def _write_bundle(
    cutoff: str,
    cutoff_date: str,
    artifact_root: Path,
    bundle_run_id: str,
    data_start: str,
    support_inputs: dict[str, Path],
    glofas_point_csv: Path,
    glofas_point_meta: Path,
    glofas_product: dict[str, Any],
    v21_daily_csv: Path,
    v30_daily_csv: Path,
) -> dict[str, str]:
    bundle_root = artifact_root / "stable_inputs" / f"site={SITE_ID}" / f"cutoff_date={cutoff_date}" / f"run_id={bundle_run_id}"
    inputs_root = ensure_dir(bundle_root / "inputs")
    ensure_dir(bundle_root / "manifests")

    usgs = _require_daily_complete(_load_usgs_daily(), data_start, cutoff_date, "USGS daily flow")
    glofas = _require_daily_complete(
        _load_glofas_daily(glofas_point_csv, source_id=str(glofas_product["source_id"])),
        data_start,
        cutoff_date,
        f"GloFAS daily flow ({glofas_product['product_id']})",
    )
    nws = _require_daily_complete(_load_nws_hybrid(v21_daily_csv, v30_daily_csv, cutoff_date), data_start, cutoff_date, "NWS hybrid retrospective")

    raws = usgs.merge(glofas[["date", "discharge_cms", "source_id"]].rename(columns={"discharge_cms": "glofas_cms", "source_id": "glofas_source_id"}), on="date", how="left")
    raws = raws.merge(nws[["date", "discharge_cms", "source_id"]].rename(columns={"discharge_cms": "nws_cms", "source_id": "nws_source_id"}), on="date", how="left")
    raws = raws.rename(columns={"discharge_cms": "usgs_cms", "source_id": "usgs_source_id"})

    selected_window_retros_path = selected_window_retros_by_cutoff().get(cutoff)
    selected_window_overlap_start = ""
    selected_window_overlap_end = ""
    selected_window_rows = 0
    if selected_window_retros_path is not None:
        selected_window = _load_selected_window_retros(selected_window_retros_path, cutoff_date)
        if selected_window is not None and not selected_window.empty:
            selected_window_rows = int(len(selected_window))
            selected_window_overlap_start = str(selected_window["date"].min())
            selected_window_overlap_end = str(selected_window["date"].max())
            raws = raws.merge(selected_window, on="date", how="left")
            for raw_col, selected_col in [
                ("usgs_cms", "usgs_cms_selected"),
                ("glofas_cms", "glofas_cms_selected"),
                ("nws_cms", "nws_cms_selected"),
            ]:
                mask = np.isfinite(pd.to_numeric(raws[selected_col], errors="coerce"))
                raws.loc[mask, raw_col] = pd.to_numeric(raws.loc[mask, selected_col], errors="coerce")
            nws_mask = np.isfinite(pd.to_numeric(raws["nws_cms_selected"], errors="coerce"))
            raws.loc[nws_mask, "nws_source_id"] = NWS_SELECTED_WINDOW_SOURCE_ID
            raws = raws.drop(columns=["usgs_cms_selected", "glofas_cms_selected", "nws_cms_selected"])

    for col in ["usgs_cms", "glofas_cms", "nws_cms"]:
        raws[col] = pd.to_numeric(raws[col], errors="coerce").clip(lower=0.0)
    if raws[["usgs_cms", "glofas_cms", "nws_cms"]].isna().any().any():
        bad = raws.loc[raws[["usgs_cms", "glofas_cms", "nws_cms"]].isna().any(axis=1), "date"].tolist()
        raise RuntimeError(f"Merged hist-fix retros contains NA values. First problematic dates: {bad[:10]}")

    positivity_repairs = [
        _stabilize_positive_history(raws, column="usgs_cms"),
        _stabilize_positive_history(raws, column="glofas_cms"),
        _stabilize_positive_history(raws, column="nws_cms"),
    ]

    retros = pd.DataFrame(
        {
            "Date": raws["date"],
            "USGS": np.log1p(raws["usgs_cms"].astype(float)),
            "GloFAS": np.log1p(raws["glofas_cms"].astype(float)),
            "NWS3.0": np.log1p(raws["nws_cms"].astype(float)),
        }
    )

    forecast_src_root = _fit_forecast_bundle_root(cutoff)
    nws_forecast_src = forecast_src_root / "nws_forecast.csv"
    glofas_forecast_src = forecast_src_root / "glofas_forecast.csv"
    if not nws_forecast_src.exists() or not glofas_forecast_src.exists():
        raise FileNotFoundError(f"Missing existing forecast snapshot under {forecast_src_root}")

    top_level_retros = bundle_root / "retros.csv"
    retros.to_csv(top_level_retros, index=False)
    retros.to_csv(inputs_root / "retros_daily.csv", index=False)
    retros.to_csv(inputs_root / "retros.csv", index=False)

    lineage = raws.rename(columns={"date": "Date"})
    lineage.to_csv(bundle_root / "retros_source_lineage.csv", index=False)
    lineage.to_csv(inputs_root / "retros_source_lineage.csv", index=False)

    _copy_file(nws_forecast_src, bundle_root / "nws_forecast.csv")
    _copy_file(nws_forecast_src, inputs_root / "nws_weighted_daily.csv")
    _copy_file(nws_forecast_src, inputs_root / "nws_members.csv")
    _copy_file(glofas_forecast_src, bundle_root / "glofas_forecast.csv")
    _copy_file(glofas_forecast_src, inputs_root / "glofas_weighted_daily.csv")
    _copy_file(glofas_forecast_src, inputs_root / "glofas_members.csv")

    plot_start, plot_end = _load_plot_window(cutoff)
    meta = {
        "run": {
            "run_id": bundle_run_id,
            "created_at_utc": utc_now(),
            "bundle_kind": "multimodel_v8_histfix_long_history",
        },
        "site": {
            "usgs_site": SITE_ID,
            "lat": SITE_LAT,
            "lon": SITE_LON,
        },
        "dates": {
            "cutoff_date": cutoff_date,
            "data_start": data_start,
            "plot_start": plot_start,
            "plot_end": plot_end,
        },
        "paths": {
            "retros_daily": "inputs/retros_daily.csv",
            "nws_weighted_daily": "inputs/nws_weighted_daily.csv",
            "glofas_weighted_daily": "inputs/glofas_weighted_daily.csv",
            "nws_members": "inputs/nws_members.csv",
            "glofas_members": "inputs/glofas_members.csv",
            "retros_source_lineage": "inputs/retros_source_lineage.csv",
        },
        "histfix": {
            "purpose": "restore long-history retrospective support for the v8 corrected support-bundle campaign",
            "glofas_source_id": str(glofas_product["source_id"]),
            "glofas_product_id": str(glofas_product["product_id"]),
            "glofas_point_series_path": str(glofas_point_csv),
            "glofas_point_series_meta": str(glofas_point_meta),
            "nws_source_policy": {
                "primary_source_id": NWS_PRIMARY_SOURCE_ID,
                "primary_daily_path": str(v21_daily_csv),
                "tail_fill_source_id": NWS_TAIL_FILL_SOURCE_ID,
                "tail_fill_daily_path": str(v30_daily_csv),
                "tail_fill_start": NWS_TAIL_FILL_START,
                "selection_rule": "use v2.1 through its natural coverage end; fill subsequent cutoff-era dates from v3.0 daily retrospective",
            },
            "usgs_daily_source_path": str(USGS_DAILY_SOURCE),
            "support_manifest": str(support_inputs["manifest"]),
            "legacy_log_ready_repairs": positivity_repairs,
            "forecast_member_sources": {
                "nws": str(nws_forecast_src),
                "glofas": str(glofas_forecast_src),
            },
            "selected_window_splice": {
                "retros_path": str(selected_window_retros_path) if selected_window_retros_path is not None else "",
                "overlap_start": selected_window_overlap_start,
                "overlap_end": selected_window_overlap_end,
                "rows_spliced": selected_window_rows,
                "nws_source_id": NWS_SELECTED_WINDOW_SOURCE_ID,
                "note": "When available, the representative selected-run retros window is spliced back into the repaired long-history bundle over the overlap so article support figures match the selected fit inputs near the cutoff.",
            },
        },
        "config": {
            "inputs": {
                "retros": {
                    "selection_policy": {
                        "keep_source_ids": [],
                        "glofas_by_cutoff_windows": [
                            {
                                "start": "2021-05-26",
                                "end": "2023-07-25",
                                "source_id": str(glofas_product["source_id"]),
                            }
                        ],
                        "nws_by_cutoff_windows": [
                            {
                                "start": "2021-04-20",
                                "end": "2023-09-19",
                                "source_id": NWS_PRIMARY_SOURCE_ID,
                                "tail_fill_source_id": NWS_TAIL_FILL_SOURCE_ID,
                                "tail_fill_start": NWS_TAIL_FILL_START,
                            }
                        ],
                    }
                }
            }
        },
        "transforms": {
            "plot_scale": "log1p_cms",
        },
        "storage_scales": {
            "retros_daily": "log1p_cms",
            "retros_source_lineage": "raw_cms",
            "nws_weighted_daily": "raw_cms",
            "glofas_weighted_daily": "raw_cms",
            "nws_members": "raw_cms",
            "glofas_members": "raw_cms",
        },
        "display_contract": {
            "flow_support_figures_scale": "log1p_cms",
            "note": "Support figures should display flow on the log1p support scale even though representative selected runs may continue to use a deeper internal log_log1p analysis scale."
        },
    }
    with (bundle_root / "meta.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(meta, handle, sort_keys=False, default_flow_style=False)

    health = {
        "created_at_utc": utc_now(),
        "cutoff": cutoff,
        "cutoff_date": cutoff_date,
        "data_start": data_start,
        "retros_rows": int(len(retros)),
        "retros_start": str(retros["Date"].min()),
        "retros_end": str(retros["Date"].max()),
        "forecast_member_counts": {
            "nws": int(pd.read_csv(nws_forecast_src).shape[1] - 1),
            "glofas": int(pd.read_csv(glofas_forecast_src).shape[1] - 1),
        },
        "raw_ranges": {
            "usgs_min": float(raws["usgs_cms"].min()),
            "usgs_max": float(raws["usgs_cms"].max()),
            "glofas_min": float(raws["glofas_cms"].min()),
            "glofas_max": float(raws["glofas_cms"].max()),
            "nws_min": float(raws["nws_cms"].min()),
            "nws_max": float(raws["nws_cms"].max()),
        },
        "legacy_log_ready_repairs": positivity_repairs,
    }
    (bundle_root / "bundle_health.json").write_text(json.dumps(health, indent=2, sort_keys=True), encoding="utf-8")

    manifest_rows = [
        {"artifact": "meta.yaml", "path": str(bundle_root / "meta.yaml")},
        {"artifact": "retros.csv", "path": str(bundle_root / "retros.csv")},
        {"artifact": "retros_source_lineage.csv", "path": str(bundle_root / "retros_source_lineage.csv")},
        {"artifact": "nws_forecast.csv", "path": str(bundle_root / "nws_forecast.csv")},
        {"artifact": "glofas_forecast.csv", "path": str(bundle_root / "glofas_forecast.csv")},
        {"artifact": "bundle_health.json", "path": str(bundle_root / "bundle_health.json")},
    ]
    pd.DataFrame(manifest_rows).to_csv(bundle_root / "manifests" / "bundle_manifest.csv", index=False)

    return {
        "cutoff": cutoff,
        "cutoff_date": cutoff_date,
        "bundle_root": str(bundle_root),
        "bundle_meta": str(bundle_root / "meta.yaml"),
        "retros_path": str(bundle_root / "retros.csv"),
        "nws_forecast_path": str(bundle_root / "nws_forecast.csv"),
        "glofas_forecast_path": str(bundle_root / "glofas_forecast.csv"),
    }


def main() -> int:
    args = parse_args()
    artifact_root = Path(args.artifact_root).expanduser().resolve()
    ensure_dir(artifact_root)
    cutoffs = [str(c) for c in args.cutoffs]
    unsupported = sorted(set(cutoffs) - set(CUTOFF_TO_DATE))
    if unsupported:
        raise SystemExit(f"Unsupported hist-fix cutoffs: {unsupported}")

    support_inputs = _prepare_supporting_inputs(artifact_root)
    v21_daily_csv = _build_nws_daily(NWS_RETRO_V21_HOURLY, artifact_root / "source_series" / "nws_retro_v21_daily.csv", NWS_PRIMARY_SOURCE_ID)
    v30_daily_csv = _build_nws_daily(NWS_RETRO_V30_HOURLY, artifact_root / "source_series" / "nws_retro_v30_daily.csv", NWS_TAIL_FILL_SOURCE_ID)

    bundle_rows = []
    for cutoff in cutoffs:
        glofas_point_csv, glofas_point_meta, glofas_product = _ensure_glofas_point_series(
            artifact_root,
            cutoff=cutoff,
            required_end=CUTOFF_TO_DATE[cutoff],
            force=args.force_glofas_extract,
        )
        bundle_rows.append(
            _write_bundle(
                cutoff=cutoff,
                cutoff_date=CUTOFF_TO_DATE[cutoff],
                artifact_root=artifact_root,
                bundle_run_id=args.bundle_run_id,
                data_start=args.data_start,
                support_inputs=support_inputs,
                glofas_point_csv=glofas_point_csv,
                glofas_point_meta=glofas_point_meta,
                glofas_product=glofas_product,
                v21_daily_csv=v21_daily_csv,
                v30_daily_csv=v30_daily_csv,
            )
        )

    summary_path = artifact_root / "stable_inputs" / "histfix_bundle_summary.csv"
    pd.DataFrame(bundle_rows).to_csv(summary_path, index=False)
    print(f"artifact_root={artifact_root}")
    print(f"support_manifest={support_inputs['manifest']}")
    print(f"nws_v21_daily_csv={v21_daily_csv}")
    print(f"nws_v30_daily_csv={v30_daily_csv}")
    print(f"bundle_summary={summary_path}")
    print(f"bundle_count={len(bundle_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
