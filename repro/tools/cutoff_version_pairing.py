#!/usr/bin/env python3
"""Resolve forecast/retrospective version pairing from a cutoff date.

This is a metadata-only resolver built from the curated audit document:
`repro/NWS_NWM_GLOFAS_DATA_AUDIT_PLAN.md`.

It does not download any data and does not call external services.
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
    forecast_version: str
    retrospective_version: str
    reforecast_version: str
    decision: str
    recommended_strategy: str
    recommended_bias_training_version: str
    recommended_reforecast_version: str
    strategy_notes: List[str]
    alternatives: List[str]
    notes: List[str]


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

GLOFAS_HISTORICAL_VERSIONS: Set[str] = {"2.1", "3.1", "4.0"}
GLOFAS_REFORECAST_VERSIONS: Set[str] = {"2.2", "3.1", "4.0"}
GLOFAS_SHARED_ANCHOR_VERSIONS: Set[str] = GLOFAS_HISTORICAL_VERSIONS & GLOFAS_REFORECAST_VERSIONS
GLOFAS_REFORECAST_FREEZE_NOTICE_DATE = date(2024, 11, 11)


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
        # Prefer closest absolute distance, then avoid stepping forward in version when tied.
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
            forecast_version=NOT_FOUND,
            retrospective_version=NOT_FOUND,
            reforecast_version=NOT_FOUND,
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
        notes.append(
            f"Forecast version {forecast_version} has no same-version retrospective in reviewed metadata."
        )
        notes.append("No authoritative NWS forecast-side reforecast/hindcast product was found in reviewed sources.")
        return CenterResolution(
            center="NWS/NWM",
            cutoff_date=cutoff.isoformat(),
            forecast_version=forecast_version,
            retrospective_version=NOT_FOUND,
            reforecast_version=NOT_FOUND,
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
            f"Retrospective {retro.version} coverage ends at {retro.coverage_end_ym} "
            f"({coverage_gap_days} days before cutoff)."
        )
    else:
        notes.append(f"Retrospective {retro.version} coverage includes the cutoff date range.")

    notes.append("Per-version retrospective release dates are not explicitly listed in reviewed metadata.")
    notes.append("NWM retrospective runs are documented as no streamflow/data-assimilation simulations.")

    strategy_notes.append(
        f"Primary strategy: use same-version pairing ({forecast_version} forecast -> {retro.version} retrospective)."
    )
    strategy_notes.append(
        "Train bias only on the retrospective coverage window and report the coverage-end-to-cutoff gap explicitly."
    )
    if coverage_gap_days > 365:
        strategy_notes.append(
            "Gap is larger than one year; run sensitivity checks on how correction quality changes near the retrospective boundary."
        )

    alternatives.append(
        "If diagnostics degrade, keep same-version pairing but shorten training window to recent years inside retrospective coverage."
    )

    return CenterResolution(
        center="NWS/NWM",
        cutoff_date=cutoff.isoformat(),
        forecast_version=forecast_version,
        retrospective_version=retro.version,
        reforecast_version=NOT_FOUND,
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
            forecast_version=NOT_FOUND,
            retrospective_version=NOT_FOUND,
            reforecast_version=NOT_FOUND,
            decision="ambiguous",
            recommended_strategy="hold_for_metadata_review",
            recommended_bias_training_version=NOT_FOUND,
            recommended_reforecast_version=NOT_FOUND,
            strategy_notes=["Do not run version-based bias transfer until forecast version is resolved for this cutoff."],
            alternatives=[],
            notes=notes,
        )

    historical_exact = forecast_version in GLOFAS_HISTORICAL_VERSIONS
    reforecast_exact = forecast_version in GLOFAS_REFORECAST_VERSIONS

    retrospective_version = forecast_version if historical_exact else NOT_FOUND
    reforecast_version = forecast_version if reforecast_exact else NOT_FOUND

    nearest_historical = nearest_supported_version(forecast_version, GLOFAS_HISTORICAL_VERSIONS)
    nearest_reforecast = nearest_supported_version(forecast_version, GLOFAS_REFORECAST_VERSIONS)
    nearest_shared = nearest_supported_version(forecast_version, GLOFAS_SHARED_ANCHOR_VERSIONS)

    if historical_exact and reforecast_exact:
        decision = "allowed"
        notes.append("Exact version match exists for both historical and reforecast metadata options.")

        recommended_strategy = "strict_same_version_pairing"
        recommended_bias_training_version = forecast_version
        recommended_reforecast_version = forecast_version
        strategy_notes.append(
            f"Primary strategy: strict same-version pairing ({forecast_version}) for historical, forecast, and reforecast usage."
        )

    elif historical_exact and not reforecast_exact:
        decision = "conditional"
        notes.append("Only partial exact version matching is available across historical/reforecast products.")

        recommended_strategy = "exact_historical_plus_nearest_reforecast"
        recommended_bias_training_version = forecast_version
        recommended_reforecast_version = nearest_reforecast
        strategy_notes.append(
            f"Use exact historical version {forecast_version} for bias-learning baseline."
        )
        strategy_notes.append(
            f"For reforecast diagnostics, use nearest available version {nearest_reforecast} and tag it as cross-version evidence."
        )
        if nearest_shared != NOT_FOUND and nearest_shared != forecast_version:
            alternatives.append(
                f"Fully aligned fallback: use shared anchor version {nearest_shared} for both historical and reforecast diagnostics."
            )

    elif (not historical_exact) and reforecast_exact:
        decision = "conditional"
        notes.append("Only partial exact version matching is available across historical/reforecast products.")

        recommended_strategy = "nearest_historical_plus_exact_reforecast"
        recommended_bias_training_version = nearest_historical
        recommended_reforecast_version = forecast_version
        strategy_notes.append(
            f"Use exact reforecast version {forecast_version} for diagnostics/post-processing."
        )
        strategy_notes.append(
            f"Use nearest historical version {nearest_historical} for bias-learning, flagged as cross-version."
        )
        if nearest_shared != NOT_FOUND and nearest_shared != forecast_version:
            alternatives.append(
                f"Fully aligned fallback: use shared anchor version {nearest_shared} for both historical and reforecast diagnostics."
            )

    else:
        decision = "ambiguous"
        notes.append("No exact same-version historical/reforecast option found in reviewed retrieve metadata.")

        recommended_strategy = "nearest_shared_anchor"
        if nearest_shared != NOT_FOUND:
            recommended_bias_training_version = nearest_shared
            recommended_reforecast_version = nearest_shared
            strategy_notes.append(
                f"Use nearest shared anchor version {nearest_shared} for both historical and reforecast to keep internal consistency."
            )
        else:
            recommended_bias_training_version = nearest_historical
            recommended_reforecast_version = nearest_reforecast
            strategy_notes.append(
                "No shared historical+reforecast anchor found; use nearest available per product and treat as exploratory only."
            )

        if nearest_historical != NOT_FOUND:
            alternatives.append(f"Historical-only nearest option: {nearest_historical}.")
        if nearest_reforecast != NOT_FOUND:
            alternatives.append(f"Reforecast-only nearest option: {nearest_reforecast}.")

    if forecast_version.startswith("4.") and forecast_version != "4.0":
        notes.append(
            "Operational forecast chronology reaches newer 4.x versions, but reviewed historical/reforecast "
            "retrieve options list up to version 4.0 only."
        )

    if forecast_version == "2.1":
        notes.append("Reforecast options start at version 2.2 in reviewed retrieve metadata.")

    if forecast_version == "2.2":
        notes.append("Historical options include 2.1/3.1/4.0, so exact 2.2 historical matching is unresolved.")

    if forecast_version not in {"2.1", "3.1", "4.0"}:
        notes.append("Cross-version pairing is blocked by default unless explicit compatibility evidence is found.")

    if cutoff >= GLOFAS_REFORECAST_FREEZE_NOTICE_DATE:
        notes.append(
            "EWDS reforecast message feed includes a temporary freeze notice (dated 2024-11-11) for medium-range "
            "reforecast updates from the v4.2 release point."
        )
        strategy_notes.append(
            "Before relying on recent reforecast availability, check the current EWDS collection messages/support guidance."
        )

    return CenterResolution(
        center="GloFAS",
        cutoff_date=cutoff.isoformat(),
        forecast_version=forecast_version,
        retrospective_version=retrospective_version,
        reforecast_version=reforecast_version,
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
    lines: List[str] = []
    lines.append(f"Cutoff date: {report['cutoff_date']}")
    lines.append("")
    for rec in report["results"]:
        r = rec
        lines.append(f"Center: {r['center']}")
        lines.append(f"  Forecast version: {r['forecast_version']}")
        lines.append(f"  Retrospective/Historical version: {r['retrospective_version']}")
        lines.append(f"  Reforecast version: {r['reforecast_version']}")
        lines.append(f"  Decision: {r['decision']}")
        lines.append(f"  Recommended strategy: {r['recommended_strategy']}")
        lines.append(f"  Recommended bias-training version: {r['recommended_bias_training_version']}")
        lines.append(f"  Recommended reforecast version: {r['recommended_reforecast_version']}")

        lines.append("  Strategy notes:")
        for note in r["strategy_notes"]:
            lines.append(f"    - {note}")

        if r["alternatives"]:
            lines.append("  Alternatives:")
            for alt in r["alternatives"]:
                lines.append(f"    - {alt}")

        lines.append("  Notes:")
        for note in r["notes"]:
            lines.append(f"    - {note}")
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
