#!/usr/bin/env python3
"""Resolve forecast/retrospective version pairing from a cutoff date.

This is a metadata-only resolver based on:
- `repro/NWS_NWM_GLOFAS_DATA_AUDIT_PLAN.md`
- focused bounded-probe evidence (`GLOFAS-LOCAL-11`)

The script does not call external services and does not download data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Sequence, Set


NOT_FOUND = "not found in reviewed sources"
NA = "n/a"


@dataclass(frozen=True)
class VersionWindow:
    version: str
    start: date
    end: Optional[date]


@dataclass(frozen=True)
class RetrospectiveMeta:
    version: str
    coverage_start_ym: str
    coverage_end_ym: str


@dataclass(frozen=True)
class CenterResolution:
    center: str
    cutoff_date: str
    cutoff_convention: str
    forecast_version: str
    retrospective_version: str
    reforecast_version: str
    retrospective_coverage_end_date: str
    days_cutoff_after_retro_end: Optional[int]
    decision: str
    recommended_strategy: str
    recommended_bias_training_version: str
    recommended_reforecast_version: str
    strategy_notes: List[str]
    alternatives: List[str]
    notes: List[str]


# ---------------------------------------------------------------------------
# NWS/NWM metadata
# ---------------------------------------------------------------------------

NWS_FORECAST_WINDOWS: List[VersionWindow] = [
    VersionWindow(version="1.0", start=date(2016, 8, 16), end=date(2017, 5, 7)),
    VersionWindow(version="1.1", start=date(2017, 5, 8), end=date(2018, 3, 5)),
    VersionWindow(version="1.2", start=date(2018, 3, 6), end=date(2019, 6, 18)),
    VersionWindow(version="2.0", start=date(2019, 6, 19), end=date(2021, 4, 19)),
    VersionWindow(version="2.1", start=date(2021, 4, 20), end=date(2023, 9, 19)),
    VersionWindow(version="3.0", start=date(2023, 9, 20), end=None),
]

NWS_RETROSPECTIVE_BY_VERSION: Dict[str, RetrospectiveMeta] = {
    "1.2": RetrospectiveMeta(version="1.2", coverage_start_ym="1993-01", coverage_end_ym="2017-12"),
    "2.0": RetrospectiveMeta(version="2.0", coverage_start_ym="1993-01", coverage_end_ym="2018-12"),
    "2.1": RetrospectiveMeta(version="2.1", coverage_start_ym="1979-02", coverage_end_ym="2020-12"),
    "3.0": RetrospectiveMeta(version="3.0", coverage_start_ym="1979-02", coverage_end_ym="2023-01"),
}


# ---------------------------------------------------------------------------
# GloFAS metadata and bounded evidence summary
# ---------------------------------------------------------------------------

GLOFAS_FORECAST_WINDOWS: List[VersionWindow] = [
    VersionWindow(version="1.0", start=date(2018, 4, 23), end=date(2018, 11, 13)),
    VersionWindow(version="2.0", start=date(2018, 11, 14), end=date(2019, 11, 4)),
    VersionWindow(version="2.1", start=date(2019, 11, 5), end=date(2020, 12, 8)),
    VersionWindow(version="2.2", start=date(2020, 12, 9), end=date(2021, 5, 25)),
    VersionWindow(version="3.1", start=date(2021, 5, 26), end=date(2021, 10, 26)),
    VersionWindow(version="3.2", start=date(2021, 10, 27), end=date(2022, 10, 18)),
    VersionWindow(version="3.3", start=date(2022, 10, 19), end=date(2022, 12, 13)),
    VersionWindow(version="3.4", start=date(2022, 12, 14), end=date(2023, 6, 27)),
    VersionWindow(version="3.5", start=date(2023, 6, 28), end=date(2023, 7, 25)),
    VersionWindow(version="4.0", start=date(2023, 7, 26), end=date(2024, 2, 27)),
    VersionWindow(version="4.1", start=date(2024, 2, 28), end=date(2024, 11, 11)),
    VersionWindow(version="4.2", start=date(2024, 11, 12), end=date(2025, 6, 3)),
    VersionWindow(version="4.3", start=date(2025, 6, 4), end=date(2025, 9, 9)),
    VersionWindow(version="4.4", start=date(2025, 9, 10), end=None),
]

# Retrieve-selector availability (metadata)
GLOFAS_HISTORICAL_SELECTORS: Set[str] = {"2.1", "3.1", "4.0"}
GLOFAS_REFORECAST_SELECTORS: Set[str] = {"2.2", "3.1", "4.0"}
GLOFAS_SHARED_ANCHOR_SELECTORS: Set[str] = GLOFAS_HISTORICAL_SELECTORS & GLOFAS_REFORECAST_SELECTORS

# Current bounded evidence snapshot (focused 3.1/4.0 historical+reforecast follow-up)
GLOFAS_EVIDENCE_TAG = "GLOFAS-LOCAL-11 (focused_20260216T075254Z)"
GLOFAS_REFORECAST_FREEZE_NOTICE_DATE = date(2024, 11, 11)

# Focused lisflood+consolidated historical window evidence by selector version.
# These are bounded-probe windows, not full endpoint guarantee windows.
GLOFAS_HISTORICAL_LISFLOOD_CONSOLIDATED_END_BY_VERSION: Dict[str, date] = {
    "3.1": date(2024, 6, 30),
    "4.0": date(2025, 11, 30),
}


def parse_cutoff_date(raw: str) -> date:
    text = str(raw).strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid cutoff date '{text}'. Expected format YYYY-MM-DD.") from exc


def month_end(yyyy_mm: str) -> date:
    month_start = datetime.strptime(yyyy_mm, "%Y-%m").date().replace(day=1)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    return next_month - timedelta(days=1)


def version_for_date(cutoff: date, windows: Sequence[VersionWindow]) -> Optional[str]:
    for item in windows:
        if cutoff < item.start:
            continue
        if item.end is None or cutoff <= item.end:
            return item.version
    return None


def parse_version_key(version: str) -> Optional[int]:
    m = re.fullmatch(r"(\d+)\.(\d+)", str(version).strip())
    if not m:
        return None
    return int(m.group(1)) * 100 + int(m.group(2))


def nearest_supported_version(target_version: str, supported_versions: Set[str]) -> str:
    target_key = parse_version_key(target_version)
    if target_key is None:
        return NOT_FOUND

    valid = [v for v in supported_versions if parse_version_key(v) is not None]
    if not valid:
        return NOT_FOUND

    def rank(candidate: str) -> tuple[int, int, int]:
        ckey = parse_version_key(candidate)
        assert ckey is not None
        # Prefer smallest absolute version distance, then prefer non-forward jumps.
        return (abs(ckey - target_key), 0 if ckey <= target_key else 1, -ckey)

    return sorted(valid, key=rank)[0]


def resolve_nws_nwm(cutoff: date) -> CenterResolution:
    forecast_version = version_for_date(cutoff, NWS_FORECAST_WINDOWS)
    notes: List[str] = []
    strategy_notes: List[str] = []
    alternatives: List[str] = []

    if forecast_version is None:
        notes.append("Cutoff is outside the reviewed NWS operational timeline.")
        return CenterResolution(
            center="NWS/NWM",
            cutoff_date=cutoff.isoformat(),
            cutoff_convention="date_only",
            forecast_version=NOT_FOUND,
            retrospective_version=NOT_FOUND,
            reforecast_version=NOT_FOUND,
            retrospective_coverage_end_date=NOT_FOUND,
            days_cutoff_after_retro_end=None,
            decision="ambiguous",
            recommended_strategy="hold_for_metadata_review",
            recommended_bias_training_version=NOT_FOUND,
            recommended_reforecast_version=NOT_FOUND,
            strategy_notes=["Do not run version-based bias transfer until forecast version is resolved for this cutoff."],
            alternatives=[],
            notes=notes,
        )

    retro = NWS_RETROSPECTIVE_BY_VERSION.get(forecast_version)
    if retro is None:
        notes.append(f"Forecast version {forecast_version} has no same-version retrospective in reviewed metadata.")
        notes.append("No authoritative NWS forecast-side reforecast/hindcast product was found in reviewed sources.")
        return CenterResolution(
            center="NWS/NWM",
            cutoff_date=cutoff.isoformat(),
            cutoff_convention="date_only",
            forecast_version=forecast_version,
            retrospective_version=NOT_FOUND,
            reforecast_version=NOT_FOUND,
            retrospective_coverage_end_date=NOT_FOUND,
            days_cutoff_after_retro_end=None,
            decision="ambiguous",
            recommended_strategy="hold_for_metadata_review",
            recommended_bias_training_version=NOT_FOUND,
            recommended_reforecast_version=NOT_FOUND,
            strategy_notes=["Pause production pairing and resolve retrospective-version linkage first."],
            alternatives=[],
            notes=notes,
        )

    retro_end = month_end(retro.coverage_end_ym)
    coverage_gap_days = (cutoff - retro_end).days
    if coverage_gap_days > 0:
        notes.append(
            f"Retrospective {retro.version} coverage ends at {retro.coverage_end_ym} ({coverage_gap_days} days before cutoff)."
        )
    else:
        notes.append(f"Retrospective {retro.version} coverage includes the cutoff date range.")

    notes.append("Per-version retrospective release dates are not explicitly listed in reviewed metadata.")
    notes.append("NWM retrospective runs are documented as no streamflow/data-assimilation simulations.")
    notes.append("Project scope for NWS/NWM pairing is CONUS only.")

    strategy_notes.append(
        f"Primary strategy: use same-version pairing ({forecast_version} forecast -> {retro.version} retrospective)."
    )
    strategy_notes.append(
        "Train bias only on the retrospective coverage window and report the coverage-end-to-cutoff gap explicitly."
    )
    if coverage_gap_days > 365:
        strategy_notes.append(
            "Gap is larger than one year; run sensitivity checks on correction stability near the retrospective boundary."
        )

    alternatives.append(
        "If diagnostics degrade, keep same-version pairing but shorten training window to recent years within retrospective coverage."
    )

    return CenterResolution(
        center="NWS/NWM",
        cutoff_date=cutoff.isoformat(),
        cutoff_convention="date_only",
        forecast_version=forecast_version,
        retrospective_version=retro.version,
        reforecast_version=NOT_FOUND,
        retrospective_coverage_end_date=retro_end.isoformat(),
        days_cutoff_after_retro_end=max(coverage_gap_days, 0),
        decision="conditional",
        recommended_strategy="same_version_with_gap_reporting",
        recommended_bias_training_version=retro.version,
        recommended_reforecast_version=NOT_FOUND,
        strategy_notes=strategy_notes,
        alternatives=alternatives,
        notes=notes,
    )


def resolve_glofas(cutoff: date) -> CenterResolution:
    forecast_version = version_for_date(cutoff, GLOFAS_FORECAST_WINDOWS)
    notes: List[str] = []
    strategy_notes: List[str] = []
    alternatives: List[str] = []

    if forecast_version is None:
        notes.append("Cutoff is outside the reviewed GloFAS operational timeline.")
        return CenterResolution(
            center="GloFAS",
            cutoff_date=cutoff.isoformat(),
            cutoff_convention="date_only",
            forecast_version=NOT_FOUND,
            retrospective_version=NOT_FOUND,
            reforecast_version=NOT_FOUND,
            retrospective_coverage_end_date=NOT_FOUND,
            days_cutoff_after_retro_end=None,
            decision="ambiguous",
            recommended_strategy="hold_for_metadata_review",
            recommended_bias_training_version=NOT_FOUND,
            recommended_reforecast_version=NOT_FOUND,
            strategy_notes=["Do not run version-based bias transfer until forecast version is resolved for this cutoff."],
            alternatives=[],
            notes=notes,
        )

    historical_exact = forecast_version in GLOFAS_HISTORICAL_SELECTORS
    reforecast_exact = forecast_version in GLOFAS_REFORECAST_SELECTORS

    retrospective_version = forecast_version if historical_exact else NOT_FOUND
    reforecast_version = forecast_version if reforecast_exact else NOT_FOUND

    nearest_historical = nearest_supported_version(forecast_version, GLOFAS_HISTORICAL_SELECTORS)
    nearest_reforecast = nearest_supported_version(forecast_version, GLOFAS_REFORECAST_SELECTORS)
    fkey = parse_version_key(forecast_version)

    if forecast_version == "4.0":
        decision = "conditional"
        recommended_strategy = "same_version_v4_with_operational_alias_caveats"
        recommended_bias_training_version = "4.0"
        recommended_reforecast_version = "4.0"
        notes.append(
            "Historical v4.0 (lisflood+consolidated) and reforecast v4.0 (lisflood control/ensemble) anchors are confirmed in focused bounded probes; forecast retrieval is via the operational alias."
        )
        notes.append(
            "Operational+lisflood forecast boundaries show mixed success/timeout behavior near tested edges; treat windows as bounded evidence."
        )
        strategy_notes.append(
            "Use v4.0 historical + v4.0 reforecast as the primary anchor for v4.0-era cutoffs."
        )
        strategy_notes.append(
            f"Record evidence tag {GLOFAS_EVIDENCE_TAG} and boundary caveats in run metadata."
        )

    elif forecast_version == "3.1":
        decision = "conditional"
        recommended_strategy = "chronology_mapped_v3_1_with_selector_mismatch_caveats"
        recommended_bias_training_version = "3.1"
        recommended_reforecast_version = "3.1"
        notes.append(
            "Historical and reforecast version_3_1 selectors have focused bounded windows for lisflood products."
        )
        notes.append(
            "Forecast endpoint requests with explicit system_version=version_3_1 previously produced invalid_request; pairing relies on official chronology mapping to operational windows."
        )
        strategy_notes.append(
            "Use 3.1 historical/reforecast for v3.1-era cutoffs, but keep an explicit selector-mismatch caveat in metadata."
        )
        alternatives.append(
            "Sensitivity fallback: rerun with v4.0 anchor and compare correction stability under explicit cross-version labeling."
        )

    elif forecast_version == "2.1":
        decision = "ambiguous"
        recommended_strategy = "exact_historical_only_reforecast_missing"
        recommended_bias_training_version = "2.1"
        recommended_reforecast_version = NOT_FOUND
        notes.append(
            "Historical version_2_1 is available, but reforecast options start at 2.2 and forecast-side version_2_1 combinations were invalid in bounded probes."
        )
        strategy_notes.append(
            "Historical 2.1 can be used for exploratory bias-learning, but strict retrospective+forecast+reforecast alignment is unresolved."
        )
        if nearest_reforecast != NOT_FOUND:
            alternatives.append(f"Exploratory reforecast fallback: {nearest_reforecast} (cross-version).")

    elif forecast_version == "2.2":
        decision = "ambiguous"
        recommended_strategy = "exact_reforecast_only_historical_missing"
        recommended_bias_training_version = NOT_FOUND
        recommended_reforecast_version = "2.2"
        notes.append(
            "Reforecast version_2_2 is available, but historical selectors do not include 2.2 and strict same-version alignment is unresolved."
        )
        strategy_notes.append(
            "Treat 2.2-era retrospective pairing as cross-version unless new authoritative lineage mapping is found."
        )
        if nearest_historical != NOT_FOUND:
            alternatives.append(f"Exploratory historical fallback: {nearest_historical} (cross-version).")

    elif forecast_version.startswith("4."):
        decision = "ambiguous"
        recommended_strategy = "nearest_shared_anchor_4_0"
        recommended_bias_training_version = "4.0"
        recommended_reforecast_version = "4.0"
        notes.append(
            "Operational chronology reaches newer 4.x versions, but reviewed historical/reforecast selectors stop at version_4_0."
        )
        strategy_notes.append(
            "Use 4.0 as nearest shared anchor only with explicit cross-version labeling and sensitivity checks."
        )

    elif fkey is not None and 300 <= fkey < 400:
        decision = "ambiguous"
        recommended_strategy = "nearest_shared_anchor_3_1"
        recommended_bias_training_version = "3.1" if "3.1" in GLOFAS_HISTORICAL_SELECTORS else NOT_FOUND
        recommended_reforecast_version = "3.1" if "3.1" in GLOFAS_REFORECAST_SELECTORS else NOT_FOUND
        notes.append(
            "This 3.x forecast version has no strict same-version historical/reforecast selector in reviewed metadata."
        )
        strategy_notes.append(
            "Use 3.1 as nearest shared anchor only as a cross-version fallback with explicit sensitivity checks."
        )

    else:
        decision = "ambiguous"
        recommended_strategy = "hold_for_metadata_review"
        recommended_bias_training_version = NOT_FOUND
        recommended_reforecast_version = NOT_FOUND
        notes.append("No validated strict same-version historical/reforecast pairing was found for this forecast version.")
        strategy_notes.append(
            "Pause automatic version transfer for this cutoff and review version lineage/availability before training."
        )
        if nearest_historical != NOT_FOUND:
            alternatives.append(f"Historical nearest option: {nearest_historical}.")
        if nearest_reforecast != NOT_FOUND:
            alternatives.append(f"Reforecast nearest option: {nearest_reforecast}.")

    if cutoff >= GLOFAS_REFORECAST_FREEZE_NOTICE_DATE:
        notes.append(
            "EWDS reforecast message feed includes a temporary freeze notice (dated 2024-11-11) for medium-range reforecast updates from the v4.2 release point."
        )
        strategy_notes.append(
            "Before relying on recent reforecast availability, check current EWDS collection messages/support guidance."
        )

    retro_end = GLOFAS_HISTORICAL_LISFLOOD_CONSOLIDATED_END_BY_VERSION.get(recommended_bias_training_version)
    if retro_end is not None:
        coverage_gap_days = (cutoff - retro_end).days
        if coverage_gap_days > 0:
            notes.append(
                f"Focused lisflood+consolidated historical window for v{recommended_bias_training_version} ends at {retro_end.isoformat()} ({coverage_gap_days} days before cutoff)."
            )
        else:
            notes.append(
                f"Focused lisflood+consolidated historical window for v{recommended_bias_training_version} includes the cutoff."
            )
        notes.append(
            "Coverage-end evidence is from bounded probing; treat as validated lower bound on availability, not exhaustive endpoint metadata."
        )
    else:
        coverage_gap_days = None
        notes.append(
            "Per-system_version historical/reforecast coverage windows remain partially unresolved for this recommendation and should be validated with lightweight boundary probes."
        )

    return CenterResolution(
        center="GloFAS",
        cutoff_date=cutoff.isoformat(),
        cutoff_convention="date_only",
        forecast_version=forecast_version,
        retrospective_version=retrospective_version,
        reforecast_version=reforecast_version,
        retrospective_coverage_end_date=retro_end.isoformat() if retro_end is not None else NOT_FOUND,
        days_cutoff_after_retro_end=max(coverage_gap_days, 0) if coverage_gap_days is not None else None,
        decision=decision,
        recommended_strategy=recommended_strategy,
        recommended_bias_training_version=recommended_bias_training_version,
        recommended_reforecast_version=recommended_reforecast_version,
        strategy_notes=strategy_notes,
        alternatives=alternatives,
        notes=notes,
    )


def build_report(cutoff: date) -> Dict[str, object]:
    results = [resolve_nws_nwm(cutoff), resolve_glofas(cutoff)]
    return {
        "cutoff_date": cutoff.isoformat(),
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": [asdict(item) for item in results],
    }


def render_text(report: Dict[str, object]) -> str:
    lines: List[str] = [f"Cutoff date: {report['cutoff_date']}", ""]

    for rec in report["results"]:
        lines.append(f"Center: {rec['center']}")
        lines.append(f"  Cutoff convention: {rec['cutoff_convention']}")
        lines.append(f"  Forecast version: {rec['forecast_version']}")
        lines.append(f"  Retrospective/Historical version: {rec['retrospective_version']}")
        lines.append(f"  Reforecast version: {rec['reforecast_version']}")
        lines.append(f"  Retrospective coverage end date: {rec['retrospective_coverage_end_date']}")
        days_gap = rec["days_cutoff_after_retro_end"]
        lines.append(
            f"  Days cutoff after retrospective end: {NA if days_gap is None else days_gap}"
        )
        lines.append(f"  Decision: {rec['decision']}")
        lines.append(f"  Recommended strategy: {rec['recommended_strategy']}")
        lines.append(f"  Recommended bias-training version: {rec['recommended_bias_training_version']}")
        lines.append(f"  Recommended reforecast version: {rec['recommended_reforecast_version']}")

        lines.append("  Strategy notes:")
        if rec["strategy_notes"]:
            for note in rec["strategy_notes"]:
                lines.append(f"    - {note}")
        else:
            lines.append("    - none")

        if rec["alternatives"]:
            lines.append("  Alternatives:")
            for alt in rec["alternatives"]:
                lines.append(f"    - {alt}")

        lines.append("  Notes:")
        if rec["notes"]:
            for note in rec["notes"]:
                lines.append(f"    - {note}")
        else:
            lines.append("    - none")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve forecast and retrospective/reforecast version pairing for NWS/NWM and GloFAS "
            "from a cutoff date (metadata-only)."
        )
    )
    parser.add_argument("cutoff_date", help="Cutoff date in YYYY-MM-DD format")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text output")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    try:
        cutoff = parse_cutoff_date(args.cutoff_date)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = build_report(cutoff)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
