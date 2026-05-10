#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from canonical_climate_indices_lib import ROOT, canonical_paths, load_config, monthly_wide_to_long, utc_now_iso

TAIL_START = '2021-01-01'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Render canonical climate-index diagnostic plots.')
    parser.add_argument(
        '--config',
        type=Path,
        default=ROOT / 'config' / 'canonical_gdpc_master_covariate.yaml',
        help='Canonical climate-index config.',
    )
    return parser.parse_args()


def load_validation(paths: Path) -> dict:
    return json.loads((paths / 'metadata' / 'validation_summary.json').read_text(encoding='utf-8'))


def build_stats_lookup(validation: dict) -> dict[str, dict]:
    return {row['index_id']: row for row in validation['standardization_stats']}


def monthly_points_for_index(monthly_csv: Path, cfg: dict) -> pd.DataFrame:
    monthly_wide = pd.read_csv(monthly_csv)
    return monthly_wide_to_long(
        monthly_wide,
        start_month=cfg['monthly_source_window']['start_month'],
        end_month=cfg['monthly_source_window']['end_month'],
    )


def render_single_index_plot(
    *,
    index_id: str,
    display_name: str,
    monthly_long: pd.DataFrame,
    raw_daily: pd.DataFrame,
    std_daily: pd.DataFrame,
    mean: float,
    std: float,
    output_path: Path,
    canonical_start: str,
    canonical_end: str,
    linear_tail_days: int,
) -> None:
    raw_daily = raw_daily.copy()
    raw_daily['time'] = pd.to_datetime(raw_daily['time'])
    std_daily = std_daily.copy()
    std_daily['time'] = pd.to_datetime(std_daily['time'])
    monthly_long = monthly_long.copy()
    monthly_long['month_start'] = pd.to_datetime(monthly_long['month_start'])
    monthly_long['value_std'] = (monthly_long['value'] - mean) / std

    tail_mask_daily = raw_daily['time'] >= pd.Timestamp(TAIL_START)
    tail_mask_monthly = monthly_long['month_start'] >= pd.Timestamp(TAIL_START)

    fig, axes = plt.subplots(3, 1, figsize=(12, 11), constrained_layout=True)
    line_color = '#1f4e79'
    point_color = '#c26d22'
    std_color = '#216e39'

    ax = axes[0]
    ax.plot(raw_daily['time'], raw_daily[index_id], color=line_color, lw=1.6, label='Daily interpolation')
    ax.scatter(monthly_long['month_start'], monthly_long['value'], color=point_color, s=16, alpha=0.8, label='Monthly source values', zorder=3)
    ax.set_ylabel('Raw index value')
    ax.set_title(f'{display_name}: full raw series', loc='left', fontsize=12, fontweight='bold')
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(frameon=False, ncol=2, loc='upper left')

    ax = axes[1]
    ax.plot(raw_daily.loc[tail_mask_daily, 'time'], raw_daily.loc[tail_mask_daily, index_id], color=line_color, lw=1.7)
    ax.scatter(
        monthly_long.loc[tail_mask_monthly, 'month_start'],
        monthly_long.loc[tail_mask_monthly, 'value'],
        color=point_color,
        s=22,
        alpha=0.9,
        zorder=3,
    )
    ax.set_ylabel('Raw index value')
    ax.set_title(f'{display_name}: tail zoom from {TAIL_START}', loc='left', fontsize=12, fontweight='bold')
    ax.grid(alpha=0.25, lw=0.5)

    ax = axes[2]
    ax.axhline(0.0, color='0.4', lw=1.0, ls='--')
    ax.plot(std_daily['time'], std_daily[index_id], color=std_color, lw=1.5, label='Daily standardized series')
    ax.scatter(monthly_long['month_start'], monthly_long['value_std'], color=point_color, s=12, alpha=0.55, label='Monthly values on same z-scale', zorder=3)
    ax.set_ylabel('Standardized value')
    ax.set_title(f'{display_name}: standardized series used for downstream GDPC fit if we keep z-scoring', loc='left', fontsize=12, fontweight='bold')
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(frameon=False, ncol=2, loc='upper left')

    for ax in axes:
        ax.set_xlim(pd.Timestamp(canonical_start), pd.Timestamp(canonical_end)) if ax is not axes[1] else None
        ax.tick_params(axis='x', labelrotation=0)
        ax.xaxis.set_major_locator(mdates.YearLocator(base=4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    axes[1].xaxis.set_major_locator(mdates.YearLocator(base=1))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[2].set_xlabel('Date')

    fig.suptitle(
        f'{display_name} ({index_id})\nCanonical window {canonical_start} to {canonical_end} | interpolation: cubic spline + {linear_tail_days}-day linear tail',
        fontsize=14,
        fontweight='bold',
        y=1.02,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches='tight')
    plt.close(fig)


def render_overview_plot(
    *,
    cfg: dict,
    raw_daily: pd.DataFrame,
    output_path: Path,
) -> None:
    raw_daily = raw_daily.copy()
    raw_daily['time'] = pd.to_datetime(raw_daily['time'])
    indices = cfg['indices']
    n = len(indices)
    ncols = 3
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 3.2 * nrows), constrained_layout=True)
    axes = axes.ravel()
    for ax, item in zip(axes, indices):
        index_id = item['index_id']
        ax.plot(raw_daily['time'], raw_daily[index_id], color='#1f4e79', lw=1.0)
        ax.set_title(item['display_name'], fontsize=10, loc='left', fontweight='bold')
        ax.grid(alpha=0.25, lw=0.4)
        ax.xaxis.set_major_locator(mdates.YearLocator(base=8))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.tick_params(axis='both', labelsize=8)
    for ax in axes[n:]:
        ax.axis('off')
    fig.suptitle('Canonical climate-index raw daily interpolation overview', fontsize=16, fontweight='bold')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches='tight')
    plt.close(fig)


def compute_interpolation_health(monthly_long: pd.DataFrame, raw_daily: pd.DataFrame, index_id: str) -> dict[str, float | str]:
    month_vals = pd.to_numeric(monthly_long['value'], errors='coerce')
    day_vals = pd.to_numeric(raw_daily[index_id], errors='coerce')
    monthly_min = float(month_vals.min())
    monthly_max = float(month_vals.max())
    daily_min = float(day_vals.min())
    daily_max = float(day_vals.max())
    monthly_range = monthly_max - monthly_min
    lower_overshoot = monthly_min - daily_min
    upper_overshoot = daily_max - monthly_max
    overshoot_frac = 0.0 if monthly_range == 0 else max(lower_overshoot, upper_overshoot) / monthly_range
    diffs = day_vals.diff().abs().dropna()
    return {
        'index_id': index_id,
        'monthly_min': monthly_min,
        'monthly_max': monthly_max,
        'daily_min': daily_min,
        'daily_max': daily_max,
        'lower_overshoot': float(lower_overshoot),
        'upper_overshoot': float(upper_overshoot),
        'overshoot_frac_of_monthly_range': float(overshoot_frac),
        'max_abs_daily_jump': float(diffs.max()) if not diffs.empty else 0.0,
    }


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config.resolve())
    paths = canonical_paths(cfg)
    validation = load_validation(paths.root)
    stats_lookup = build_stats_lookup(validation)

    raw_daily = pd.read_csv(paths.intermediate_root / 'combined_climate_indices_daily_19870529_20230122.csv')
    std_daily = pd.read_csv(paths.intermediate_root / 'combined_climate_indices_daily_standardized_19870529_20230122.csv')

    figures_dir = paths.review_root / 'figures'
    figures_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, str]] = []
    health_rows: list[dict[str, float | str]] = []
    for item in cfg['indices']:
        index_id = item['index_id']
        display_name = item['display_name']
        monthly_long = monthly_points_for_index(paths.monthly_csv_root / f'{index_id}.csv', cfg)
        stats = stats_lookup[index_id]
        output_path = figures_dir / f'{index_id}_diagnostic.png'
        render_single_index_plot(
            index_id=index_id,
            display_name=display_name,
            monthly_long=monthly_long,
            raw_daily=raw_daily[['time', index_id]],
            std_daily=std_daily[['time', index_id]],
            mean=float(stats['raw_mean']),
            std=float(stats['raw_std']),
            output_path=output_path,
            canonical_start=cfg['canonical_window']['start_date'],
            canonical_end=cfg['canonical_window']['end_date'],
            linear_tail_days=int(cfg['postprocess']['interpolation']['linear_tail_days']),
        )
        manifest_rows.append({'index_id': index_id, 'display_name': display_name, 'plot_path': str(output_path)})
        health_rows.append(compute_interpolation_health(monthly_long, raw_daily[['time', index_id]], index_id))

    overview_path = figures_dir / 'all_indices_raw_daily_overview.png'
    render_overview_plot(cfg=cfg, raw_daily=raw_daily, output_path=overview_path)

    manifest_path = figures_dir / 'manifest.csv'
    with manifest_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['index_id', 'display_name', 'plot_path'])
        writer.writeheader()
        for row in manifest_rows:
            writer.writerow(row)

    health_rows = sorted(health_rows, key=lambda row: float(row['overshoot_frac_of_monthly_range']), reverse=True)
    health_path = figures_dir / 'interpolation_health_summary.csv'
    with health_path.open('w', newline='', encoding='utf-8') as handle:
        fieldnames = [
            'index_id',
            'monthly_min',
            'monthly_max',
            'daily_min',
            'daily_max',
            'lower_overshoot',
            'upper_overshoot',
            'overshoot_frac_of_monthly_range',
            'max_abs_daily_jump',
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in health_rows:
            writer.writerow(row)

    review_path = paths.review_root / 'CANONICAL_CLIMATE_INDEX_DIAGNOSTIC_PLOTS.md'
    lines = [
        '# Canonical Climate Index Diagnostic Plots',
        '',
        f'- generated_at_utc: `{utc_now_iso()}`',
        f"- canonical_window: `{cfg['canonical_window']['start_date']}` -> `{cfg['canonical_window']['end_date']}`",
        f"- figure_manifest: `{manifest_path}`",
        f"- overview_plot: `{overview_path}`",
        f"- interpolation_health_summary: `{health_path}`",
        '',
        'Each per-index diagnostic plot contains:',
        '- full raw daily interpolation with monthly source anchors,',
        f'- raw tail zoom from `{TAIL_START}` onward,',
        '- standardized daily series and the monthly anchors placed on the same z-scale.',
        '',
        'Use these plots to verify interpolation health and to inspect whether z-scoring is a sensible preprocessing step before fitting GDPC.',
        '',
        'Top overshoot cases from the numeric health summary:',
    ]
    for row in health_rows[:5]:
        lines.append(
            f"- `{row['index_id']}`: overshoot fraction `{row['overshoot_frac_of_monthly_range']:.4f}`, max daily jump `{row['max_abs_daily_jump']:.4f}`"
        )
    review_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[OK] wrote diagnostic plot manifest: {manifest_path}')
    print(f'[OK] wrote overview plot: {overview_path}')
    print(f'[OK] wrote interpolation health summary: {health_path}')
    print(f'[OK] wrote per-index diagnostic plots: {len(manifest_rows)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
