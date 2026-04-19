#!/usr/bin/env python3
"""Create publication-style coverage timeline diagrams for NWS/NWM and GloFAS.

Outputs:
- repro/reports/figures/nws_nwm_version_coverage_timeline.png
- repro/reports/figures/nws_nwm_version_coverage_timeline.pdf
- repro/reports/figures/glofas_version_coverage_timeline.png
- repro/reports/figures/glofas_version_coverage_timeline.pdf

The script is metadata-only and does not download any data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Keep timeline windows consistent with the cutoff resolver.
from cutoff_version_pairing import GLOFAS_FORECAST_WINDOWS, NWS_FORECAST_WINDOWS, NWS_RETROSPECTIVE_BY_VERSION


SNAPSHOT_END = date(2026, 2, 16)
STANDARD_COVERAGE_BAR_HEIGHT = 0.70
PAPER_CUTOFFS: Sequence[Tuple[str, date]] = (
    ("01/23/2021", date(2021, 1, 23)),
    ("11/12/2021", date(2021, 11, 12)),
    ("12/21/2021", date(2021, 12, 21)),
    ("05/11/2022", date(2022, 5, 11)),
    ("12/25/2022", date(2022, 12, 25)),
)


@dataclass(frozen=True)
class IntervalRow:
    label: str
    start: date
    end: date
    color: str
    alpha: float = 0.9
    hatch: Optional[str] = None
    edgecolor: str = "#1f2937"
    linewidth: float = 0.9
    is_point_anchor: bool = False


def month_end(yyyy_mm: str) -> date:
    y, m = map(int, yyyy_mm.split("-"))
    d0 = date(y, m, 1)
    if m == 12:
        d1 = date(y + 1, 1, 1)
    else:
        d1 = date(y, m + 1, 1)
    return d1 - timedelta(days=1)


def ensure_outdir() -> Path:
    outdir = Path("repro/reports/figures")
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


def _date_num(d: date) -> float:
    return mdates.date2num(d)


def _draw_interval(ax: plt.Axes, y: float, row: IntervalRow, bar_h: float = STANDARD_COVERAGE_BAR_HEIGHT) -> None:
    start_num = _date_num(row.start)
    end_num = _date_num(row.end)
    width = max(end_num - start_num, 1.0)
    ax.broken_barh(
        [(start_num, width)],
        (y - bar_h / 2.0, bar_h),
        facecolors=row.color,
        edgecolors=row.edgecolor,
        linewidth=row.linewidth,
        alpha=row.alpha,
        hatch=row.hatch,
        zorder=3,
    )
    if row.is_point_anchor:
        ax.plot(
            row.start,
            y,
            marker="D",
            markersize=6.0,
            markerfacecolor="#111827",
            markeredgecolor="white",
            markeredgewidth=0.8,
            linestyle="None",
            zorder=5,
        )


def _set_time_axis(ax: plt.Axes, xmin: date, xmax: date, major_year_step: int = 2) -> None:
    ax.set_xlim(xmin, xmax)
    ax.xaxis.set_major_locator(mdates.YearLocator(base=major_year_step))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.grid(which="major", axis="x", color="#cbd5e1", linewidth=0.8, alpha=0.7)
    ax.grid(which="minor", axis="x", color="#e2e8f0", linewidth=0.5, alpha=0.6)
    ax.grid(which="major", axis="y", color="#f1f5f9", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)


def _apply_common_style() -> None:
    plt.style.use("default")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "figure.facecolor": "#f8fafc",
            "axes.facecolor": "#ffffff",
            "savefig.facecolor": "#f8fafc",
            "savefig.bbox": "tight",
        }
    )


def _forecast_version_lines(
    ax: plt.Axes,
    starts: Sequence[Tuple[str, date]],
    y_top: float,
    color: str = "#64748b",
    label_prefix: str = "v",
    min_gap_days: float = 140.0,
    level_offsets: Sequence[float] = (0.0, 0.10),
    rotation: float = 45.0,
    alternate_even_odd: bool = False,
    even_odd_offsets: Tuple[float, float] = (0.30, 0.0),
) -> None:
    if alternate_even_odd:
        for idx, (ver, d) in enumerate(starts):
            y_off = even_odd_offsets[0] if idx % 2 == 0 else even_odd_offsets[1]
            ax.axvline(d, color=color, linestyle=(0, (4, 4)), linewidth=0.9, alpha=0.75, zorder=1)
            ax.text(
                d,
                y_top + y_off,
                f"{label_prefix}{ver}",
                rotation=rotation,
                va="bottom",
                ha="center" if rotation >= 80 else "left",
                fontsize=8.4,
                fontweight="bold",
                color="#1f2937",
                bbox={"facecolor": "#f8fafc", "edgecolor": "none", "alpha": 0.7, "pad": 0.15},
                clip_on=False,
            )
        return

    # Assign each label to the first lane with enough horizontal gap.
    levels = list(level_offsets) if level_offsets else [0.0]
    lane_last_x: List[Optional[float]] = [None for _ in levels]
    lane_idx_by_label: List[int] = []

    for _, d in starts:
        x = _date_num(d)
        chosen_lane: Optional[int] = None
        for lane_i, last_x in enumerate(lane_last_x):
            if last_x is None or (x - last_x) >= min_gap_days:
                chosen_lane = lane_i
                break
        if chosen_lane is None:
            chosen_lane = min(
                range(len(lane_last_x)),
                key=lambda i: lane_last_x[i] if lane_last_x[i] is not None else -1e12,
            )
        lane_last_x[chosen_lane] = x
        lane_idx_by_label.append(chosen_lane)

    for (ver, d), lane_i in zip(starts, lane_idx_by_label):
        y_off = levels[lane_i]
        ax.axvline(d, color=color, linestyle=(0, (4, 4)), linewidth=0.9, alpha=0.75, zorder=1)
        ax.text(
            d,
            y_top + y_off,
            f"{label_prefix}{ver}",
            rotation=rotation,
            va="bottom",
            ha="center" if rotation >= 80 else "left",
            fontsize=8.4,
            fontweight="bold",
            color="#1f2937",
            bbox={"facecolor": "#f8fafc", "edgecolor": "none", "alpha": 0.7, "pad": 0.15},
            clip_on=False,
        )


def _save(fig: plt.Figure, outbase: Path) -> None:
    fig.savefig(outbase.with_suffix(".png"), dpi=320)
    fig.savefig(outbase.with_suffix(".pdf"))


def _fmt_range(start: date, end: date, is_open_ended: bool = False) -> str:
    if is_open_ended:
        return f"{start.isoformat()} to present"
    return f"{start.isoformat()} to {end.isoformat()}"


def _draw_cutoff_markers(
    ax: plt.Axes,
    cutoffs: Sequence[Tuple[str, date]] = PAPER_CUTOFFS,
    color: str = "#b91c1c",
    text_y: float = 1.01,
    show_labels: bool = False,
) -> None:
    for label, cutoff_date in cutoffs:
        ax.axvline(
            cutoff_date,
            color=color,
            linestyle="-",
            linewidth=1.25,
            alpha=0.8,
            zorder=2,
        )
        if show_labels:
            ax.annotate(
                label,
                xy=(mdates.date2num(cutoff_date), text_y),
                xycoords=("data", "axes fraction"),
                xytext=(0, 4),
                textcoords="offset points",
                rotation=90,
                va="bottom",
                ha="center",
                fontsize=8.2,
                fontweight="bold",
                color=color,
                bbox={"facecolor": "#f8fafc", "edgecolor": "none", "alpha": 0.85, "pad": 0.15},
                clip_on=False,
            )


def _add_rule_box(ax: plt.Axes, title: str, bullets: Sequence[str], xy: Tuple[float, float]) -> None:
    lines = [title] + [f"- {bullet}" for bullet in bullets]
    ax.text(
        xy[0],
        xy[1],
        "\n".join(lines),
        transform=ax.transAxes,
        fontsize=8.9,
        color="#0f172a",
        ha="left",
        va="top",
        bbox={
            "facecolor": "#ffffff",
            "edgecolor": "#94a3b8",
            "boxstyle": "round,pad=0.35",
            "alpha": 0.96,
        },
        zorder=10,
    )


def plot_nws_nwm(outdir: Path) -> Path:
    # Shared hue across forecast/retrospective for same version creates visual linkage.
    version_color = {
        "1.0": "#6b7280",
        "1.1": "#9ca3af",
        "1.2": "#7c3aed",
        "2.0": "#2563eb",
        "2.1": "#d97706",
        "3.0": "#059669",
    }

    forecast_rows: List[IntervalRow] = []
    forecast_labels: List[str] = []
    for w in NWS_FORECAST_WINDOWS:
        c = version_color[w.version]
        end = w.end if w.end is not None else SNAPSHOT_END
        forecast_rows.append(
            IntervalRow(
                label=f"Forecast issue dates: v{w.version}",
                start=w.start,
                end=end,
                color=c,
                alpha=0.92,
            )
        )
        forecast_labels.append(
            f"Forecast issue dates: v{w.version}\n{_fmt_range(w.start, end, is_open_ended=(w.end is None))}"
        )

    retro_versions = ["1.2", "2.0", "2.1", "3.0"]
    retro_rows: List[IntervalRow] = []
    retro_labels: List[str] = []
    for ver in retro_versions:
        meta = NWS_RETROSPECTIVE_BY_VERSION[ver]
        start = date.fromisoformat(meta.coverage_start_ym + "-01")
        end = month_end(meta.coverage_end_ym)
        retro_rows.append(
            IntervalRow(
                label=f"Retrospective coverage: v{ver}",
                start=start,
                end=end,
                color=version_color[ver],
                alpha=0.55,
                hatch="//",
            )
        )
        retro_labels.append(f"Retrospective coverage: v{ver}\n{_fmt_range(start, end)}")

    rows = forecast_rows + retro_rows
    y_positions = list(range(len(rows), 0, -1))

    fig_h = 0.64 * len(rows) + 2.6
    fig, ax = plt.subplots(figsize=(16, fig_h))

    for y, row in zip(y_positions, rows):
        _draw_interval(ax, y, row)

    # Version start lines on forecast chronology.
    _forecast_version_lines(
        ax,
        [(w.version, w.start) for w in NWS_FORECAST_WINDOWS],
        y_top=max(y_positions) + 0.14,
        min_gap_days=180.0,
        level_offsets=(0.0, 0.10),
        rotation=45.0,
    )

    # Group separator and labels.
    sep_y = len(retro_rows) + 0.5
    ax.axhline(sep_y, color="#64748b", linewidth=1.0, alpha=0.6)
    xmin = date(2010, 1, 1)
    xmax = date(2026, 12, 31)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(forecast_labels + retro_labels)
    ax.set_ylim(0.25, len(rows) + 1.5)
    _set_time_axis(ax, xmin, xmax, major_year_step=2)
    fig.subplots_adjust(left=0.36, right=0.98, top=0.885, bottom=0.15)

    ax.set_title("NWS / NOAA National Water Model: Version and Coverage Timeline", loc="left", pad=18, weight="bold")
    ax.set_xlabel("Date")

    legend_handles = [
        Patch(facecolor="#2563eb", edgecolor="#1f2937", label="Forecast version coverage by issue date"),
        Patch(facecolor="#2563eb", edgecolor="#1f2937", hatch="//", alpha=0.55, label="Retrospective coverage by version"),
        Line2D([0], [0], color="#64748b", linestyle=(0, (4, 4)), lw=1.0, label="Forecast version start"),
        Line2D([0], [0], color="#111827", lw=0, label="Same hue across rows => same version"),
    ]
    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(0.0, 0.93), frameon=True, framealpha=0.95)

    ax.text(
        0.0,
        -0.12,
        "Notes: (1) Retrospective release dates are not explicitly listed per version in reviewed metadata. "
        "(2) No authoritative NWS forecast-side reforecast/hindcast product was found in reviewed sources.",
        transform=ax.transAxes,
        fontsize=8.7,
        color="#334155",
        ha="left",
        va="top",
    )

    outbase = outdir / "nws_nwm_version_coverage_timeline"
    _save(fig, outbase)
    plt.close(fig)
    return outbase.with_suffix(".png")


def plot_nws_nwm_v21_v30_only(outdir: Path) -> Path:
    # Variant requested: only v2.1 and v3.0 forecast + retrospective windows.
    fig, ax = plt.subplots(figsize=(16, 6.0))
    _draw_nws_nwm_v21_v30_only(ax=ax, legend_mode="inside")
    fig.subplots_adjust(left=0.36, right=0.98, top=0.86, bottom=0.12)
    outbase = outdir / "nws_nwm_version_coverage_timeline_v21_v30_only"
    _save(fig, outbase)
    plt.close(fig)
    return outbase.with_suffix(".png")


def plot_nws_nwm_paper(outdir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(17.5, 6.6))
    _draw_nws_nwm_v21_v30_only(
        ax=ax,
        legend_mode="top_outside",
        keep_versions=("2.0", "2.1", "3.0"),
        xmin=date(2018, 1, 1),
    )
    fig.subplots_adjust(left=0.33, right=0.985, top=0.77, bottom=0.12)
    outbase = outdir / "nws_nwm_version_coverage_timeline_paper"
    _save(fig, outbase)
    plt.close(fig)
    return outbase.with_suffix(".png")


def _draw_nws_nwm_v21_v30_only(
    ax: plt.Axes,
    legend_mode: str = "inside",
    keep_versions: Optional[Sequence[str]] = None,
    xmin: date = date(2018, 1, 1),
) -> None:
    version_color = {
        "1.2": "#7c3aed",
        "2.0": "#2563eb",
        "2.1": "#d97706",
        "3.0": "#059669",
    }
    if keep_versions is None:
        keep_versions = ("2.1", "3.0")
    keep_versions_set = set(keep_versions)
    version_order = ["1.2", "2.0", "2.1", "3.0"]

    forecast_windows = [w for w in NWS_FORECAST_WINDOWS if w.version in keep_versions_set]
    forecast_rows: List[IntervalRow] = []
    forecast_labels: List[str] = []
    for w in forecast_windows:
        c = version_color[w.version]
        end = w.end if w.end is not None else SNAPSHOT_END
        forecast_rows.append(
            IntervalRow(
                label=f"Forecast issue dates: v{w.version}",
                start=w.start,
                end=end,
                color=c,
                alpha=0.92,
            )
        )
        forecast_labels.append(
            f"Forecast issue dates: v{w.version}\n{_fmt_range(w.start, end, is_open_ended=(w.end is None))}"
        )

    retro_versions = [v for v in version_order if v in keep_versions_set]
    retro_rows: List[IntervalRow] = []
    retro_labels: List[str] = []
    for ver in retro_versions:
        meta = NWS_RETROSPECTIVE_BY_VERSION[ver]
        start = date.fromisoformat(meta.coverage_start_ym + "-01")
        end = month_end(meta.coverage_end_ym)
        retro_rows.append(
            IntervalRow(
                label=f"Retrospective coverage: v{ver}",
                start=start,
                end=end,
                color=version_color[ver],
                alpha=0.55,
                hatch="//",
            )
        )
        retro_labels.append(f"Retrospective coverage: v{ver}\n{_fmt_range(start, end)}")

    rows = forecast_rows + retro_rows
    y_positions = list(range(len(rows), 0, -1))

    for y, row in zip(y_positions, rows):
        _draw_interval(ax, y, row)

    _forecast_version_lines(
        ax,
        [(w.version, w.start) for w in forecast_windows],
        y_top=max(y_positions) + 0.42,
        min_gap_days=180.0,
        level_offsets=(0.0, 0.14),
        rotation=45.0,
    )

    sep_y = len(retro_rows) + 0.5
    ax.axhline(sep_y, color="#64748b", linewidth=1.0, alpha=0.6)
    xmax = date(2026, 12, 31)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(forecast_labels + retro_labels)
    ax.set_ylim(0.25, len(rows) + 1.5)
    _set_time_axis(ax, xmin, xmax, major_year_step=1)

    shown = [f"v{v}" for v in version_order if v in keep_versions_set]
    if len(shown) <= 2:
        shown_txt = " and ".join(shown)
    else:
        shown_txt = ", ".join(shown[:-1]) + f", and {shown[-1]}"
    title_txt = f"NWS / NOAA National Water Model: Version and Coverage Timeline ({shown_txt})"

    if legend_mode == "top_outside":
        ax.set_title(
            title_txt,
            loc="left",
            y=1.15,
            pad=0,
            weight="bold",
        )
    else:
        ax.set_title(
            title_txt,
            loc="left",
            pad=18,
            weight="bold",
        )
    ax.set_xlabel("Date")

    legend_handles = [
        Patch(facecolor="#2563eb", edgecolor="#1f2937", label="Forecast version coverage by issue date"),
        Patch(
            facecolor="#2563eb",
            edgecolor="#1f2937",
            hatch="//",
            alpha=0.55,
            label="Retrospective coverage by version",
        ),
        Line2D([0], [0], color="#64748b", linestyle=(0, (4, 4)), lw=1.0, label="Forecast version start"),
        Line2D([0], [0], color="#111827", lw=0, label="Same hue across rows => same version"),
    ]
    if legend_mode == "inside":
        ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(0.0, 0.93), frameon=True, framealpha=0.95)
    elif legend_mode == "top_outside":
        ax.legend(
            handles=legend_handles,
            loc="lower left",
            bbox_to_anchor=(0.0, 1.035),
            ncol=2,
            fontsize=8.7,
            frameon=False,
            borderaxespad=0.0,
            columnspacing=1.0,
            handletextpad=0.5,
        )


def plot_glofas(outdir: Path) -> Path:
    # Forecast chronology from official versioning table (through v4.4).
    version_color = {
        "1.0": "#332288",
        "2.0": "#88CCEE",
        "2.1": "#44AA99",
        "2.2": "#117733",
        "3.0": "#DDCC77",  # project alias with 3.1
        "3.1": "#DDCC77",  # project alias with 3.0
        "3.2": "#CC6677",
        "3.3": "#882255",
        "3.4": "#AA4499",
        "3.5": "#661100",
        "4.0": "#6699CC",
        "4.1": "#AA4466",
        "4.2": "#4477AA",
        "4.3": "#EE6677",
        "4.4": "#228833",
    }

    forecast_rows: List[IntervalRow] = []
    forecast_labels: List[str] = []
    for w in GLOFAS_FORECAST_WINDOWS:
        c = version_color[w.version]
        end = w.end if w.end is not None else SNAPSHOT_END
        forecast_rows.append(
            IntervalRow(
                label=f"Forecast issue dates: v{w.version}",
                start=w.start,
                end=end,
                color=c,
                alpha=0.94,
            )
        )
        forecast_labels.append(
            f"Forecast issue dates: v{w.version}\n{_fmt_range(w.start, end, is_open_ended=(w.end is None))}"
        )

    # Focused bounded-probe historical windows (priority scope) plus legacy anchors.
    historical_rows: List[IntervalRow] = [
        IntervalRow(
            label="Historical coverage: v2.1 htessel_lisflood consolidated",
            start=date(1979, 1, 1),
            end=date(2022, 7, 31),
            color=version_color["2.1"],
            alpha=0.45,
            hatch="..",
        ),
        IntervalRow(
            label="Historical coverage: v3.1 lisflood consolidated",
            start=date(1979, 1, 1),
            end=date(2024, 6, 30),
            color=version_color["3.0"],
            alpha=0.45,
            hatch="..",
        ),
        IntervalRow(
            label="Historical coverage: v4.0 lisflood consolidated",
            start=date(1979, 1, 1),
            end=date(2025, 11, 30),
            color=version_color["4.0"],
            alpha=0.45,
            hatch="..",
        ),
        IntervalRow(
            label="Legacy reanalysis archive window: v3.0 (JRC)",
            start=date(1980, 1, 1),
            end=date(2018, 12, 31),
            color=version_color["3.0"],
            alpha=0.24,
            hatch="xx",
            edgecolor="#475569",
        ),
    ]
    historical_labels = [
        f"Historical coverage: v2.1 htessel_lisflood consolidated\n{_fmt_range(date(1979, 1, 1), date(2022, 7, 31))}",
        f"Historical coverage: v3.1 lisflood consolidated\n{_fmt_range(date(1979, 1, 1), date(2024, 6, 30))}",
        f"Historical coverage: v4.0 lisflood consolidated\n{_fmt_range(date(1979, 1, 1), date(2025, 11, 30))}",
        f"Legacy reanalysis archive window: v3.0 (JRC)\n{_fmt_range(date(1980, 1, 1), date(2018, 12, 31))}",
    ]

    rows = forecast_rows + historical_rows
    y_positions = list(range(len(rows), 0, -1))

    fig_h = 0.58 * len(rows) + 2.8
    fig, ax = plt.subplots(figsize=(18, fig_h))

    for y, row in zip(y_positions, rows):
        _draw_interval(ax, y, row)

    _forecast_version_lines(
        ax,
        [(w.version, w.start) for w in GLOFAS_FORECAST_WINDOWS],
        y_top=max(y_positions) + 0.40,
        color="#6b7280",
        alternate_even_odd=True,
        even_odd_offsets=(0.55, 0.0),
        rotation=45.0,
    )

    # Group separators.
    forecast_n = len(forecast_rows)
    sep1 = len(rows) - forecast_n + 0.5
    ax.axhline(sep1, color="#64748b", linewidth=1.0, alpha=0.6)

    xmin = date(2010, 1, 1)
    xmax = date(2026, 12, 31)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(forecast_labels + historical_labels)
    ax.set_ylim(0.25, len(rows) + 3.35)
    _set_time_axis(ax, xmin, xmax, major_year_step=2)
    fig.subplots_adjust(left=0.36, right=0.98, top=0.86, bottom=0.18)

    ax.set_title("GloFAS: Forecast Version Chronology and Historical Coverage", loc="left", pad=18, weight="bold")
    ax.set_xlabel("Date")

    legend_handles = [
        Patch(facecolor=version_color["4.0"], edgecolor="#1f2937", label="Forecast version coverage by issue date"),
        Patch(
            facecolor=version_color["4.0"],
            edgecolor="#1f2937",
            alpha=0.62,
            hatch="//",
            label="Focused historical coverage windows (bounded probing)",
        ),
        Patch(
            facecolor=version_color["4.0"],
            edgecolor="#475569",
            alpha=0.24,
            hatch="..",
            label="Legacy historical/reanalysis archive windows",
        ),
        Line2D([0], [0], color="#6b7280", linestyle=(0, (4, 4)), lw=1.0, label="Forecast version start"),
        Line2D([0], [0], color="#111827", lw=0, label="Same hue across rows => same version (incl. v3.x alias)"),
    ]
    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(0.0, 0.95), frameon=True, framealpha=0.95)

    ax.text(
        0.0,
        -0.12,
        "Focused evidence note: Historical rows are from priority-scope bounded probing (v3.x alias + v4.0, lisflood).\n"
        "Reforecast rows are intentionally omitted in this simplified plot; see audit tables for reforecast details.\n"
        "Project alias note: JRC v3.0 and EWDS version_3_1 are shown as one shared label/color (v3.x alias).\n"
        "Forecast 'operational' version mapping is inferred from official chronology; EWDS selectors do not always expose a numeric version for operational requests.",
        transform=ax.transAxes,
        fontsize=8.7,
        color="#334155",
        ha="left",
        va="top",
    )

    outbase = outdir / "glofas_version_coverage_timeline"
    _save(fig, outbase)
    plt.close(fig)
    return outbase.with_suffix(".png")


def plot_glofas_v3x_v4x_family_palette(outdir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(18, 11.8))
    _draw_glofas_v2_v3_v4_family_variant(ax=ax, legend_mode="inside")
    fig.subplots_adjust(left=0.36, right=0.98, top=0.86, bottom=0.13)
    outbase = outdir / "glofas_version_coverage_timeline_v3x_v4x_family_colors"
    _save(fig, outbase)
    plt.close(fig)
    return outbase.with_suffix(".png")


def plot_glofas_paper(outdir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(18.5, 11.9))
    _draw_glofas_v2_v3_v4_family_variant(
        ax=ax,
        legend_mode="top_outside",
        xmin=date(2018, 1, 1),
    )
    fig.subplots_adjust(left=0.34, right=0.985, top=0.78, bottom=0.12)
    outbase = outdir / "glofas_version_coverage_timeline_paper"
    _save(fig, outbase)
    plt.close(fig)
    return outbase.with_suffix(".png")


def _draw_glofas_v2_v3_v4_family_variant(
    ax: plt.Axes,
    legend_mode: str = "inside",
    xmin: date = date(2018, 1, 1),
) -> None:
    # Variant requested: grouped color families by major version.
    version_color = {
        # Keep older versions subdued.
        "1.0": "#64748b",
        # v2.x family (slate shades)
        "2.0": "#334155",
        "2.1": "#475569",
        "2.2": "#64748b",
        # v3.x family (orange shades)
        "3.0": "#b45309",  # project alias with 3.1
        "3.1": "#b45309",  # project alias with 3.0
        "3.2": "#c2410c",
        "3.3": "#d97706",
        "3.4": "#ea580c",
        "3.5": "#fb923c",
        # v4.x family (teal shades)
        "4.0": "#0f766e",
        "4.1": "#0d9488",
        "4.2": "#14b8a6",
        "4.3": "#2dd4bf",
        "4.4": "#5eead4",
    }

    # Variant scope: keep forecast chronology for v2.x, v3.x and v4.x.
    forecast_windows = [w for w in GLOFAS_FORECAST_WINDOWS if int(w.version.split(".")[0]) >= 2]

    forecast_rows: List[IntervalRow] = []
    forecast_labels: List[str] = []
    for w in forecast_windows:
        c = version_color[w.version]
        end = w.end if w.end is not None else SNAPSHOT_END
        forecast_rows.append(
            IntervalRow(
                label=f"Forecast issue dates: v{w.version}",
                start=w.start,
                end=end,
                color=c,
                alpha=0.94,
            )
        )
        forecast_labels.append(
            f"Forecast issue dates: v{w.version}\n{_fmt_range(w.start, end, is_open_ended=(w.end is None))}"
        )

    historical_rows: List[IntervalRow] = [
        IntervalRow(
            label="Historical coverage: v2.1 htessel_lisflood consolidated",
            start=date(1979, 1, 1),
            end=date(2022, 7, 31),
            color=version_color["2.1"],
            alpha=0.45,
            hatch="..",
        ),
        IntervalRow(
            label="Historical coverage: v3.1 lisflood consolidated",
            start=date(1979, 1, 1),
            end=date(2024, 6, 30),
            color=version_color["3.0"],
            alpha=0.45,
            hatch="..",
        ),
        IntervalRow(
            label="Historical coverage: v4.0 lisflood consolidated",
            start=date(1979, 1, 1),
            end=date(2025, 11, 30),
            color=version_color["4.0"],
            alpha=0.45,
            hatch="..",
        ),
        IntervalRow(
            label="Legacy reanalysis archive window: v3.0 (JRC)",
            start=date(1980, 1, 1),
            end=date(2018, 12, 31),
            color=version_color["3.0"],
            alpha=0.24,
            hatch="xx",
            edgecolor="#475569",
        ),
    ]
    historical_labels = [
        f"Historical coverage: v2.1 htessel_lisflood consolidated\n{_fmt_range(date(1979, 1, 1), date(2022, 7, 31))}",
        f"Historical coverage: v3.1 lisflood consolidated\n{_fmt_range(date(1979, 1, 1), date(2024, 6, 30))}",
        f"Historical coverage: v4.0 lisflood consolidated\n{_fmt_range(date(1979, 1, 1), date(2025, 11, 30))}",
        f"Legacy reanalysis archive window: v3.0 (JRC)\n{_fmt_range(date(1980, 1, 1), date(2018, 12, 31))}",
    ]

    rows = forecast_rows + historical_rows
    y_positions = list(range(len(rows), 0, -1))

    for y, row in zip(y_positions, rows):
        _draw_interval(ax, y, row)

    _forecast_version_lines(
        ax,
        [(w.version, w.start) for w in forecast_windows],
        y_top=max(y_positions) + 0.40,
        color="#6b7280",
        alternate_even_odd=True,
        even_odd_offsets=(0.55, 0.0),
        rotation=45.0,
    )

    forecast_n = len(forecast_rows)
    sep1 = len(rows) - forecast_n + 0.5
    ax.axhline(sep1, color="#64748b", linewidth=1.0, alpha=0.6)

    xmax = date(2026, 12, 31)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(forecast_labels + historical_labels)
    ax.set_ylim(0.25, len(rows) + 3.35)
    _set_time_axis(ax, xmin, xmax, major_year_step=2)

    if legend_mode == "top_outside":
        ax.set_title(
            "GloFAS: Forecast Version Chronology and Historical Coverage (v2.x/v3.x/v4.x families)",
            loc="left",
            y=1.17,
            pad=0,
            weight="bold",
        )
    else:
        ax.set_title(
            "GloFAS: Forecast Version Chronology and Historical Coverage (v2.x/v3.x/v4.x families)",
            loc="left",
            pad=18,
            weight="bold",
        )
    ax.set_xlabel("Date")

    legend_handles = [
        Patch(facecolor=version_color["2.1"], edgecolor="#1f2937", label="Forecast v2.x family (slate shades)"),
        Patch(facecolor=version_color["3.3"], edgecolor="#1f2937", label="Forecast v3.x family (orange shades)"),
        Patch(facecolor=version_color["4.2"], edgecolor="#1f2937", label="Forecast v4.x family (teal shades)"),
        Patch(
            facecolor=version_color["3.0"],
            edgecolor="#475569",
            alpha=0.45,
            hatch="..",
            label="Historical coverage windows",
        ),
        Patch(
            facecolor=version_color["4.0"],
            edgecolor="#475569",
            alpha=0.24,
            hatch="xx",
            label="Legacy historical/reanalysis archive windows (v3.0 only)",
        ),
        Line2D([0], [0], color="#6b7280", linestyle=(0, (4, 4)), lw=1.0, label="Forecast version start"),
        Line2D(
            [0],
            [0],
            color="#111827",
            lw=0,
            label="Forecast numeric versions are assigned by official release chronology",
        ),
    ]
    if legend_mode == "inside":
        ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(0.0, 0.95), frameon=True, framealpha=0.95)
    elif legend_mode == "top_outside":
        ax.legend(
            handles=legend_handles,
            loc="lower left",
            bbox_to_anchor=(0.0, 1.045),
            ncol=2,
            fontsize=8.7,
            frameon=False,
            borderaxespad=0.0,
            columnspacing=1.0,
            handletextpad=0.5,
        )


def plot_variant_matrix(outdir: Path, nws_png: Optional[Path] = None, glofas_png: Optional[Path] = None) -> Path:
    # Build a direct 2x1 comparison panel using the current working variant specs.
    fig, axes = plt.subplots(2, 1, figsize=(18, 22), facecolor="#f8fafc")
    for ax in axes:
        ax.set_facecolor("#ffffff")

    _draw_nws_nwm_v21_v30_only(
        ax=axes[0],
        legend_mode="top_outside",
        keep_versions=("1.2", "2.0", "2.1", "3.0"),
        xmin=date(2016, 1, 1),
    )
    _draw_glofas_v2_v3_v4_family_variant(
        ax=axes[1],
        legend_mode="top_outside",
        xmin=date(2016, 1, 1),
    )

    cutoff_handle = Line2D([0], [0], color="#b91c1c", lw=1.25, label="Study cutoffs")
    for ax in axes:
        _draw_cutoff_markers(ax)

    nws_legend = axes[0].get_legend()
    if nws_legend is not None:
        nws_legend.remove()
    axes[0].legend(
        handles=[
            Patch(facecolor="#2563eb", edgecolor="#1f2937", label="Forecast version coverage by issue date"),
            Patch(
                facecolor="#2563eb",
                edgecolor="#1f2937",
                hatch="//",
                alpha=0.55,
                label="Retrospective coverage by version",
            ),
            Line2D([0], [0], color="#64748b", linestyle=(0, (4, 4)), lw=1.0, label="Forecast version start"),
            cutoff_handle,
            Line2D([0], [0], color="#111827", lw=0, label="Same hue across rows => same version"),
        ],
        loc="lower left",
        bbox_to_anchor=(0.0, 1.045),
        ncol=2,
        fontsize=8.5,
        frameon=False,
        borderaxespad=0.0,
        columnspacing=1.0,
        handletextpad=0.5,
    )

    _add_rule_box(
        axes[0],
        "Pairing rule",
        (
            "Use the forecast version active at the cutoff issue date.",
            "Pair it with the same-version retrospective product first.",
            "Report the retrospective coverage gap explicitly when it ends before the cutoff.",
        ),
        xy=(0.60, 0.33),
    )
    _add_rule_box(
        axes[1],
        "Pairing rule",
        (
            "Assign the forecast family by official issue-date chronology.",
            "Pair it with the closest exposed historical family (v2.x->2.1, v3.x->3.1, v4.x->4.0).",
            "Legacy JRC v3.0 is shown separately because it is not identical to EWDS historical v3.1.",
        ),
        xy=(0.57, 0.28),
    )

    fig.text(
        0.5,
        0.012,
        "Version-audit matrix used to build valid cutoff-specific input bundles. Red lines mark the five study cutoffs "
        "(01/23/2021, 11/12/2021, 12/21/2021, 05/11/2022, and 12/25/2022).\n"
        "The version chronology shown here was combined with archive audits and provider verification before model fitting. "
        "Associated preprocessing included manifests covering 56,110 GEFS files, 4,420 NWM files, and 1,289 GloFAS historical shards.",
        ha="center",
        va="bottom",
        fontsize=9.2,
        color="#334155",
    )
    fig.subplots_adjust(left=0.34, right=0.985, top=0.93, bottom=0.05, hspace=0.30)

    outbase = outdir / "nws_glofas_version_coverage_matrix_current"
    _save(fig, outbase)
    plt.close(fig)
    return outbase.with_suffix(".png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate NWS/GloFAS version coverage timeline figures.")
    parser.add_argument(
        "--mode",
        choices=("default", "variants", "all", "matrix", "paper"),
        default="default",
        help="default: original pair; variants: variant pair + matrix; matrix: matrix only; paper: focused NWS/GloFAS pair used in manuscript drafts; all: defaults + variants + matrix.",
    )
    return parser.parse_args()


def main() -> int:
    _apply_common_style()
    args = parse_args()
    outdir = ensure_outdir()
    generated: List[Path] = []

    if args.mode in {"default", "all"}:
        generated.append(plot_nws_nwm(outdir))
        generated.append(plot_glofas(outdir))
    if args.mode in {"variants", "all", "matrix"}:
        nws_variant = plot_nws_nwm_v21_v30_only(outdir)
        glofas_variant = plot_glofas_v3x_v4x_family_palette(outdir)
        if args.mode in {"variants", "all"}:
            generated.append(nws_variant)
            generated.append(glofas_variant)
        generated.append(plot_variant_matrix(outdir, nws_png=nws_variant, glofas_png=glofas_variant))
    if args.mode in {"paper", "all"}:
        generated.append(plot_nws_nwm_paper(outdir))
        generated.append(plot_glofas_paper(outdir))

    for p in generated:
        print(f"Generated: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
