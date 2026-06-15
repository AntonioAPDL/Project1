#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


LATEST_FORECAST_ISSUE_MANIFEST_REL = "artifacts/latest_forecast_issue/latest_forecast_issue_manifest.json"
LATEST_FORECAST_ISSUE_CONTRACT_REL = "docs/he7_latest_forecast_issue_contract_20260615.md"
ARTICLE_LATEST_FORECAST_ISSUE_DOC_REL = "docs/latest_forecast_issue_contract.md"

LATEST_FORECAST_CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]

REQUIRED_LATEST_FORECAST_ARTICLE_CLAIMS = [
    "using the latest forecast products issued at or before",
    "the forecast matrix is the daily issue associated with the cutoff",
    "retain the most recent available issuance for each target time and ensemble member",
    "older forecast issuances are not averaged into the publication forecast matrices",
    "compatibility aliases only",
]

REQUIRED_LATEST_FORECAST_CORRECTIONS_CLAIMS = [
    "latest available forecast ensemble",
    "rather than combining earlier issuances",
    "no longer combine older forecast issuances",
    "workflow compatibility aliases",
    "not active cross-issue weighting",
]

FORBIDDEN_LATEST_FORECAST_ARTICLE_CLAIMS = [
    "weighted combination of prior forecasts",
    "lagged forecasts are weighted",
    "combining earlier issuances",
    "older forecast issuances are averaged",
]


@dataclass(frozen=True)
class LatestForecastIssueManifestCheck:
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


def check_latest_forecast_issue_manifest(data: dict[str, Any]) -> list[LatestForecastIssueManifestCheck]:
    protocol = data.get("protocol", {})
    sources = data.get("sources", {})
    glofas = sources.get("glofas", {})
    nws = sources.get("nws", {})
    claims = data.get("claims_policy", {})
    cutoffs = data.get("rolling_origin_cutoffs") or []

    return [
        LatestForecastIssueManifestCheck(
            "schema_version",
            data.get("schema_version") == "he7_latest_forecast_issue_v1",
            str(data.get("schema_version", "")),
        ),
        LatestForecastIssueManifestCheck(
            "cutoff_set",
            cutoffs == LATEST_FORECAST_CUTOFFS,
            str(cutoffs),
        ),
        LatestForecastIssueManifestCheck(
            "publication_protocol",
            protocol.get("name") == "latest_forecast_only"
            and protocol.get("publication_weighting_scheme") == "latest",
            str(protocol),
        ),
        LatestForecastIssueManifestCheck(
            "no_cross_issue_weighting",
            protocol.get("cross_issue_weighting_used") is False
            and claims.get("no_cross_issue_weighting") is True,
            f"protocol={protocol.get('cross_issue_weighting_used')}, claims={claims.get('no_cross_issue_weighting')}",
        ),
        LatestForecastIssueManifestCheck(
            "legacy_alias_policy",
            protocol.get("legacy_weighted_daily_filenames_are_aliases") is True
            and claims.get("legacy_weighted_daily_names_do_not_imply_weighting") is True,
            str(protocol.get("legacy_weighted_daily_filenames_are_aliases")),
        ),
        LatestForecastIssueManifestCheck(
            "glofas_issue_rule",
            glofas.get("selection_rule") == "issue_date_equals_cutoff"
            and glofas.get("cache_pattern") == "forecast_cache/glofas/issue_date=<cutoff>/glofas_members.csv",
            str(glofas),
        ),
        LatestForecastIssueManifestCheck(
            "nws_issue_rule",
            nws.get("selection_rule") == "latest_issue_datetime_per_target_hour_member_then_daily_mean"
            and nws.get("availability_rule") == "issue_datetime_at_or_before_cutoff_day",
            str(nws),
        ),
        LatestForecastIssueManifestCheck(
            "member_counts",
            glofas.get("member_count") == 51 and nws.get("member_count") == 7,
            f"glofas={glofas.get('member_count')}, nws={nws.get('member_count')}",
        ),
        LatestForecastIssueManifestCheck(
            "code_evidence_paths",
            bool(_nested(data, "code_evidence", "nws_extractor"))
            and bool(_nested(data, "code_evidence", "glofas_extractor"))
            and bool(_nested(data, "code_evidence", "batch_config")),
            str(data.get("code_evidence", {})),
        ),
    ]
