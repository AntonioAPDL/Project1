#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FORECAST_DESIGN_MANIFEST_REL = "artifacts/forecast_design/forecast_design_manifest.json"
FORECAST_DESIGN_CONTRACT_REL = "docs/he6_out_of_sample_forecast_design_contract_20260615.md"
ARTICLE_FORECAST_DESIGN_DOC_REL = "docs/forecast_design_contract.md"

FORECAST_CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]

REQUIRED_FORECAST_DESIGN_ARTICLE_CLAIMS = [
    "Post-cutoff USGS observations are reserved strictly for verification",
    "are not used to fit or update the predictive distributions",
    "At a cutoff \\(c\\), the model is fit using USGS observations and retrospective products available through \\(c\\)",
    "The forecast-window predictive distributions are then synthesized using the latest forecast products issued at or before \\(c\\)",
    "latest forecast products issued at or before",
    "forecast-window precipitation and soil-moisture covariates",
    "canonical GDPC climate-index factor",
    "not treated as an operational forecast product or verification target",
    "time-ordered analogue of cross-validation",
    "each fold fixes a forecast origin",
    "heavily overlapping forecast windows would overrepresent the same hydrological episode",
]

REQUIRED_FORECAST_DESIGN_CORRECTIONS_CLAIMS = [
    "five rolling-origin cutoff-based forecasting folds",
    "the model is fit using only observations and retrospective information available through \\(\\textbf{c}\\)",
    "Forecasts are then generated over the post-cutoff forecast window using the latest forecast products issued at or before \\(\\textbf{c}\\)",
    "Post-cutoff USGS observations remain verification only",
    "forecast-window precipitation and soil-moisture covariates",
    "canonical GDPC climate-index covariate",
    "not treated as an operational forecast product",
    "archive-feasible and version-consistent",
    "time-ordered analogue of cross-validation",
    "post-cutoff USGS observations are used only for verification",
    "avoid dense overlapping windows that would repeatedly score the same hydrological regime",
]

FORBIDDEN_FORECAST_DESIGN_CLAIMS = [
    "post-cutoff USGS observations are used to fit",
    "forecast-window USGS observations are used to fit",
    "the model is fit using only information available through \\(\\textbf{c}\\): observed discharge up to \\(\\textbf{c}\\), retrospective/historical products available at \\(\\textbf{c}\\), and forecast products issued at or before \\(\\textbf{c}\\)",
    "the model is fit using forecast products issued at or before",
    "forecast products issued at or before \\(\\textbf{c}\\). Post-cutoff USGS observations remain verification only",
    "GDPC forecast product",
    "PCA forecast product",
    "post-cutoff USGS observations enter fitting",
    "random K-fold cross-validation",
    "continuous daily post-2022 hindcast",
]


@dataclass(frozen=True)
class ForecastDesignManifestCheck:
    item: str
    ok: bool
    detail: str


def _nested(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def check_forecast_design_manifest(data: dict[str, Any]) -> list[ForecastDesignManifestCheck]:
    cutoffs = _nested(data, "rolling_origin_design", "cutoffs") or []
    target = _nested(data, "rolling_origin_design", "held_out_target")
    fit_inputs = _nested(data, "rolling_origin_design", "fit_inputs") or []
    fair_assessment = _nested(data, "rolling_origin_design", "fair_assessment") or {}
    forecast_products = _nested(data, "forecast_origin_inputs", "forecast_products") or {}
    local_covariates = _nested(data, "forecast_origin_inputs", "local_covariates") or {}
    gdpc = _nested(data, "forecast_origin_inputs", "gdpc_pca") or {}
    claims_policy = data.get("claims_policy", {})

    local_names = local_covariates.get("names") or []
    return [
        ForecastDesignManifestCheck(
            "schema_version",
            data.get("schema_version") == "he6_forecast_design_v1",
            str(data.get("schema_version", "")),
        ),
        ForecastDesignManifestCheck("cutoff_count", cutoffs == FORECAST_CUTOFFS, str(cutoffs)),
        ForecastDesignManifestCheck("held_out_target", target == "post_cutoff_usgs_only", str(target)),
        ForecastDesignManifestCheck(
            "fit_inputs_through_cutoff",
            {"usgs_through_cutoff", "retrospective_products_through_cutoff"}.issubset(set(fit_inputs)),
            str(fit_inputs),
        ),
        ForecastDesignManifestCheck(
            "fair_assessment_cross_validation_analogue",
            fair_assessment.get("cross_validation_analogue") == "time_ordered_rolling_origin_folds"
            and fair_assessment.get("fold_unit") == "forecast_origin_cutoff",
            str(fair_assessment),
        ),
        ForecastDesignManifestCheck(
            "no_dense_overlapping_origin_claim",
            fair_assessment.get("dense_overlapping_origins_claimed") is False,
            str(fair_assessment.get("dense_overlapping_origins_claimed")),
        ),
        ForecastDesignManifestCheck(
            "forecast_products_timing",
            forecast_products.get("timing") == "latest_issued_at_or_before_cutoff",
            str(forecast_products.get("timing")),
        ),
        ForecastDesignManifestCheck(
            "forecast_products_issue_selection_manifest",
            forecast_products.get("issue_selection_manifest")
            == "artifacts/latest_forecast_issue/latest_forecast_issue_manifest.json",
            str(forecast_products.get("issue_selection_manifest")),
        ),
        ForecastDesignManifestCheck(
            "local_forecast_window_covariates",
            local_names == ["precipitation", "soil_moisture"]
            and local_covariates.get("role") == "forecast_window_transfer_covariates",
            f"names={local_names}, role={local_covariates.get('role')}",
        ),
        ForecastDesignManifestCheck(
            "gdpc_not_forecast_product",
            gdpc.get("role") == "deterministic_climate_index_covariate"
            and gdpc.get("operational_forecast_product") is False
            and gdpc.get("verification_target") is False,
            str(gdpc),
        ),
        ForecastDesignManifestCheck(
            "no_usgs_leakage_policy",
            claims_policy.get("post_cutoff_usgs_used_for_fit_or_update") is False,
            str(claims_policy.get("post_cutoff_usgs_used_for_fit_or_update")),
        ),
        ForecastDesignManifestCheck(
            "gdpc_claims_policy",
            claims_policy.get("gdpc_pca_described_as_forecast_product") is False,
            str(claims_policy.get("gdpc_pca_described_as_forecast_product")),
        ),
        ForecastDesignManifestCheck(
            "no_continuous_dense_hindcast_claim",
            claims_policy.get("continuous_daily_post_2022_hindcast_claimed") is False,
            str(claims_policy.get("continuous_daily_post_2022_hindcast_claimed")),
        ),
    ]
