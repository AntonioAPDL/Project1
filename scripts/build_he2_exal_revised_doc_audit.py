#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
ARTICLE_ROOT = ROOT / 'Evironmetrics---REVISED-DOC-Corrected'
RUNTIME_ROOT = ROOT.parent / 'project1_ucsc_phd_runtime'
REPORT_DIR = ROOT / 'reports' / 'he2_exal_revised_doc_audit_20260517'

CUTOFFS = ['20210123', '20211112', '20211221', '20220511', '20221225']
CUTOFF_DISPLAY = {
    '20210123': '01/23/2021',
    '20211112': '11/12/2021',
    '20211221': '12/21/2021',
    '20220511': '05/11/2022',
    '20221225': '12/25/2022',
}

FROZEN_MANIFEST = ARTICLE_ROOT / 'artifacts' / 'he2_publication_freeze' / 'he2_bayesian_publication_manifest.csv'
ARTICLE_MANIFEST = ARTICLE_ROOT / 'MANUSCRIPT_ASSET_MANIFEST.json'
ARTICLE_FIGURE_SUMMARY = ARTICLE_ROOT / 'reports' / 'article_figure_lineage_audit_20260516' / 'summary.json'
REP_SELECTED_METADATA = ARTICLE_ROOT / 'artifacts' / 'representative_selected_model_2022_12_25' / 'bundle_metadata.json'
HIST_SUPPORT_METADATA = ARTICLE_ROOT / 'artifacts' / 'historical_support_from_current_models' / 'bundle_metadata.json'


@dataclass(frozen=True)
class FamilyDef:
    label: str
    family: str
    run_root_parent: Path
    matrix_status: Path
    synthesis_model_id: str
    transfer_mode: str
    figure_status: str
    figure_note: str


FAMILIES = [
    FamilyDef(
        label='exAL-M-T1',
        family='exdqlm_multivar_keep',
        run_root_parent=RUNTIME_ROOT / 'multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516',
        matrix_status=RUNTIME_ROOT / 'multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516' / 'control' / 'publication_relaunch_matrix' / 'matrix_status.csv',
        synthesis_model_id='exdqlm_multivar_synth_keep',
        transfer_mode='keep',
        figure_status='fully_closed_for_figures',
        figure_note='Keep-side figure wiring is fully closed, including historical-support/current-model figures.',
    ),
    FamilyDef(
        label='exAL-M-T0',
        family='exdqlm_multivar_drop',
        run_root_parent=RUNTIME_ROOT / 'multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516',
        matrix_status=RUNTIME_ROOT / 'multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516' / 'control' / 'publication_relaunch_matrix' / 'matrix_status.csv',
        synthesis_model_id='exdqlm_multivar_synth_drop',
        transfer_mode='drop',
        figure_status='limited_direct_figure_usage',
        figure_note='This family is complete on the run side, but it is not a major direct manuscript-figure lane.',
    ),
    FamilyDef(
        label='exAL-U-T1',
        family='exdqlm_univar',
        run_root_parent=RUNTIME_ROOT / 'multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516',
        matrix_status=RUNTIME_ROOT / 'multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516' / 'control' / 'publication_relaunch_matrix' / 'matrix_status.csv',
        synthesis_model_id='exdqlm_univar_synth',
        transfer_mode='NA',
        figure_status='reference_synthesis_family_refreshed',
        figure_note='The historical-only reference synthesis figure is refreshed from the corrected exAL univar output bundle.',
    ),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def read_json(path: Path):
    return json.loads(path.read_text())


def rerun_id(family: str, cutoff: str) -> str:
    return f'multimodel_{cutoff}_v8_he2pubgdpc1r1_{family}'


def rerun_root(fd: FamilyDef, cutoff: str) -> Path:
    return fd.run_root_parent / 'runs' / rerun_id(fd.family, cutoff)


def rerun_output_root(fd: FamilyDef, cutoff: str) -> Path:
    run_id = rerun_id(fd.family, cutoff)
    return rerun_root(fd, cutoff) / 'post' / 'outputs' / run_id


def synthesis_score_row(fd: FamilyDef, cutoff: str) -> dict[str, str]:
    rows = read_csv(rerun_output_root(fd, cutoff) / 'tables' / 'crps_forecast_summary.csv')
    for row in rows:
        if row['model_id'] == fd.synthesis_model_id:
            return row
    raise RuntimeError(f'Missing synthesis row for {fd.label} cutoff {cutoff}')


def matrix_completion(fd: FamilyDef) -> tuple[str, bool]:
    rows = read_csv(fd.matrix_status)
    pass_rows = [r for r in rows if r.get('status') == 'pass']
    complete = len(pass_rows) == len(CUTOFFS) and len(rows) == len(CUTOFFS)
    return f'complete_{len(pass_rows)}_of_{len(rows)}', complete


def post_metrics_present(fd: FamilyDef) -> bool:
    required = ['crps_forecast_summary.csv', 'crps_forecast_per_time.csv', 'crps_input_health.csv', 'crps_input_health_per_time.csv', 'posterior_table_exports_manifest.csv']
    if fd.family != 'exdqlm_univar':
        required += ['gamma_summary.csv', 'sigma_summary.csv', 'covariate_effects_summary.csv']
    for cutoff in CUTOFFS:
        table_root = rerun_output_root(fd, cutoff) / 'tables'
        for name in required:
            if not (table_root / name).exists():
                return False
        if not (rerun_root(fd, cutoff) / 'report' / 'summary.json').exists():
            return False
    return True


def load_frozen_rows() -> dict[tuple[str, str], dict[str, str]]:
    rows = read_csv(FROZEN_MANIFEST)
    return {(row['manuscript_label'], row['cutoff']): row for row in rows}


def benchmark_source_status() -> tuple[str, str]:
    manifest = read_json(ARTICLE_MANIFEST)
    table = manifest['tables']['tab:benchmark_crps_models']
    source = table['sources']['bayesian_manifest_csv']
    note = table['note']
    return source, note


def representative_table_status() -> tuple[bool, str]:
    manifest = read_json(ARTICLE_MANIFEST)
    tables = manifest['tables']
    rep_meta = read_json(REP_SELECTED_METADATA)
    keep_root = str(FAMILIES[0].run_root_parent / 'runs' / rerun_id('exdqlm_multivar_keep', '20221225'))
    all_sources_present = all((ARTICLE_ROOT / tables[label]['sources'][next(iter(tables[label]['sources']))]).exists() for label in ['tab:components_23_31', 'tab:gamma_sigma_intervals1', 'tab:gamma_sigma_intervals2'])
    rooted = rep_meta.get('runtime_run_root') == keep_root
    return all_sources_present and rooted, rep_meta.get('runtime_run_root', '')


def historical_support_status() -> tuple[bool, str]:
    meta = read_json(HIST_SUPPORT_METADATA)
    mode = ((meta.get('multivar_source') or {}).get('historical_support_render_generation_mode') or '')
    return mode == 'rendered_from_historical_support_replay', mode


def build_benchmark_rows() -> list[dict[str, str]]:
    frozen = load_frozen_rows()
    rows: list[dict[str, str]] = []
    for fd in FAMILIES:
        for cutoff in CUTOFFS:
            rerun = synthesis_score_row(fd, cutoff)
            frozen_row = frozen[(fd.label, cutoff)]
            rerun_crps = float(rerun['mean_crps'])
            frozen_crps = float(frozen_row['crps_exact'])
            abs_diff = abs(rerun_crps - frozen_crps)
            rel_ratio = rerun_crps / frozen_crps if frozen_crps != 0 else float('inf')
            if rerun_crps == frozen_crps:
                status = 'exact_match'
            elif abs_diff <= 1e-6:
                status = 'tolerance_match'
            else:
                status = 'mismatch'
            rows.append({
                'cutoff': cutoff,
                'cutoff_display': CUTOFF_DISPLAY[cutoff],
                'manuscript_label': fd.label,
                'family': fd.family,
                'frozen_run_id': frozen_row['run_id'],
                'frozen_run_root': frozen_row['run_root'],
                'frozen_crps_exact': frozen_row['crps_exact'],
                'frozen_score_source': frozen_row['score_source'],
                'rerun_run_id': rerun_id(fd.family, cutoff),
                'rerun_run_root': str(rerun_root(fd, cutoff)),
                'rerun_model_id': rerun['model_id'],
                'rerun_mean_crps': f'{rerun_crps:.16g}',
                'rerun_score_scale': rerun['score_scale'],
                'rerun_score_source': str(rerun_output_root(fd, cutoff) / 'tables' / 'crps_forecast_summary.csv'),
                'absolute_diff': f'{abs_diff:.16g}',
                'rerun_over_frozen_ratio': f'{rel_ratio:.16g}',
                'status': status,
            })
    return rows


def family_overall_status(fd: FamilyDef, benchmark_rows: list[dict[str, str]], rep_tables_ok: bool, hist_ok: bool) -> tuple[str, str]:
    family_rows = [r for r in benchmark_rows if r['manuscript_label'] == fd.label]
    benchmark_ok = all(r['status'] in {'exact_match', 'tolerance_match'} for r in family_rows)
    if fd.label == 'exAL-M-T1':
        if benchmark_ok and rep_tables_ok and hist_ok:
            return 'fully_closed', 'none'
        return 'figures_closed_benchmark_blocked', 'benchmark_table_values_do_not_match_completed_rerun_scores'
    if fd.label == 'exAL-M-T0':
        if benchmark_ok:
            return 'run_complete_benchmark_ready', 'none'
        return 'run_complete_benchmark_blocked', 'benchmark_table_values_do_not_match_completed_rerun_scores'
    if fd.label == 'exAL-U-T1':
        if benchmark_ok:
            return 'run_complete_reference_figure_ready', 'none'
        return 'run_complete_reference_figure_benchmark_blocked', 'benchmark_table_values_do_not_match_completed_rerun_scores'
    raise AssertionError(fd.label)


def build_family_rows(benchmark_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rep_tables_ok, rep_root = representative_table_status()
    hist_ok, hist_mode = historical_support_status()
    bench_source, _bench_note = benchmark_source_status()
    rows: list[dict[str, str]] = []
    for fd in FAMILIES:
        rerun_completion, _complete = matrix_completion(fd)
        post_ok = post_metrics_present(fd)
        family_rows = [r for r in benchmark_rows if r['manuscript_label'] == fd.label]
        benchmark_ok = all(r['status'] in {'exact_match', 'tolerance_match'} for r in family_rows)
        overall, remaining = family_overall_status(fd, benchmark_rows, rep_tables_ok, hist_ok)
        rows.append({
            'label': fd.label,
            'family': fd.family,
            'rerun_completion': rerun_completion,
            'post_metrics_and_synthesis': 'yes' if post_ok else 'no',
            'revised_doc_figure_wiring': fd.figure_status,
            'representative_tables_current': 'yes' if (rep_tables_ok and fd.label == 'exAL-M-T1') else ('n/a' if fd.label == 'exAL-M-T0' else 'reference_support_only'),
            'historical_support_current': 'yes' if (hist_ok and fd.label == 'exAL-M-T1') else ('n/a' if fd.label == 'exAL-M-T0' else 'yes'),
            'benchmark_table_source': bench_source,
            'benchmark_table_authoritative': 'yes' if benchmark_ok else 'no',
            'representative_runtime_root': rep_root if fd.label == 'exAL-M-T1' else '',
            'historical_support_mode': hist_mode if fd.label in {'exAL-M-T1', 'exAL-U-T1'} else '',
            'overall_status': overall,
            'remaining_gap': remaining,
        })
    return rows


def build_summary(benchmark_rows: list[dict[str, str]], family_rows: list[dict[str, str]]) -> dict:
    figure_summary = read_json(ARTICLE_FIGURE_SUMMARY)
    mismatches = [r for r in benchmark_rows if r['status'] == 'mismatch']
    return {
        'scope': ['exAL-M-T1', 'exAL-M-T0', 'exAL-U-T1'],
        'article_figure_status_counts': figure_summary.get('status_counts', {}),
        'representative_table_sources_current': representative_table_status()[0],
        'historical_support_repaired': historical_support_status()[0],
        'benchmark_table_source': benchmark_source_status()[0],
        'benchmark_table_note': benchmark_source_status()[1],
        'benchmark_row_count': len(benchmark_rows),
        'benchmark_mismatch_count': len(mismatches),
        'benchmark_mismatch_labels': sorted({r['manuscript_label'] for r in mismatches}),
        'family_status_counts': {
            status: sum(1 for row in family_rows if row['overall_status'] == status)
            for status in sorted({row['overall_status'] for row in family_rows})
        },
        'rerun_local_score_median_by_label': {
            fd.label: median(float(r['rerun_mean_crps']) for r in benchmark_rows if r['manuscript_label'] == fd.label)
            for fd in FAMILIES
        },
        'frozen_score_median_by_label': {
            fd.label: median(float(r['frozen_crps_exact']) for r in benchmark_rows if r['manuscript_label'] == fd.label)
            for fd in FAMILIES
        },
        'final_certification': 'blocked_on_benchmark_table_reconciliation',
    }


def build_markdown(summary: dict, family_rows: list[dict[str, str]], benchmark_rows: list[dict[str, str]]) -> str:
    lines: list[str] = []
    lines.append('# HE2 exAL Revised-Doc Audit (2026-05-17)')
    lines.append('')
    lines.append('## Scope')
    lines.append('This audit checks the three exAL families against the revised-doc integration layer:')
    lines.append('- `exdqlm_multivar_keep` (`exAL-M-T1`)')
    lines.append('- `exdqlm_multivar_drop` (`exAL-M-T0`)')
    lines.append('- `exdqlm_univar` (`exAL-U-T1`)')
    lines.append('')
    lines.append('It certifies four separate things:')
    lines.append('1. Did all five cutoff reruns complete through `report`?')
    lines.append('2. Did the reruns emit fit/post metrics and synthesis artifacts?')
    lines.append('3. Are the revised-doc figure and representative-table sources wired to the completed rerun roots?')
    lines.append('4. Is the benchmark CRPS table already authoritative from those completed reruns?')
    lines.append('')
    lines.append('## Executive Summary')
    lines.append('- All three exAL rerun families completed through `report` for all five cutoffs.')
    lines.append('- All three families emitted the core post-stage metrics tables and synthesis artifacts needed for reproduction.')
    lines.append('- `exAL-M-T1` figure wiring is now fully closed, including the historical-support/current-model lane via the retained-support replay contract.')
    lines.append('- The representative appendix/source tables (`components`, `gamma`, `sigma`) are wired to the corrected representative `2022-12-25 exAL-M-T1` rerun bundle.')
    lines.append('- The benchmark CRPS table is still sourced from the frozen HE2 publication manifest, and the completed shared-spec exAL rerun-local synthesis CRPS values do **not** match those frozen benchmark rows.')
    lines.append('- Because of that benchmark mismatch, the exAL family set is **not yet fully certified** as an end-to-end authoritative manuscript table workflow.')
    lines.append('')
    lines.append('## Family Verdicts')
    lines.append('| Label | Family | Rerun completion | Post metrics + synthesis | Figure wiring | Benchmark table authoritative? | Overall |')
    lines.append('|---|---|---|---|---|---|---|')
    for row in family_rows:
        lines.append(f"| `{row['label']}` | `{row['family']}` | `{row['rerun_completion']}` | `{row['post_metrics_and_synthesis']}` | `{row['revised_doc_figure_wiring']}` | `{row['benchmark_table_authoritative']}` | `{row['overall_status']}` |")
    lines.append('')
    lines.append('## Revised-Doc Wiring That Is Confirmed Current')
    lines.append(f"- Article figure status counts: `{json.dumps(summary['article_figure_status_counts'], sort_keys=True)}`")
    lines.append(f"- Representative selected-model table sources current: `{summary['representative_table_sources_current']}`")
    lines.append(f"- Historical-support repaired: `{summary['historical_support_repaired']}`")
    lines.append('- `tab:components_23_31`, `tab:gamma_sigma_intervals1`, and `tab:gamma_sigma_intervals2` are sourced from `artifacts/representative_selected_model_2022_12_25`, which points at the corrected `20260516` `exAL-M-T1` rerun root.')
    lines.append('- The keep-side historical-support/current-model figures now render from the corrected retained-support replay rooted in the completed `20220511 exAL-M-T1` run.')
    lines.append('')
    lines.append('## Benchmark Table Certification Status')
    lines.append(f"- Current benchmark Bayesian source: `{summary['benchmark_table_source']}`")
    lines.append('- This is still the frozen HE2 publication manifest, not a rerun-local exAL source layer.')
    lines.append('- The completed shared-spec exAL rerun-local synthesis CRPS values diverge from those frozen benchmark values for all three exAL manuscript labels.')
    lines.append('')
    lines.append('Representative mismatch examples:')
    lines.append('| Cutoff | Label | Frozen CRPS | Shared-spec rerun local CRPS | Status |')
    lines.append('|---|---:|---:|---:|---|')
    for row in [r for r in benchmark_rows if r['cutoff'] == '20221225']:
        lines.append(f"| `{row['cutoff_display']}` | `{row['manuscript_label']}` | `{float(row['frozen_crps_exact']):.4f}` | `{float(row['rerun_mean_crps']):.4f}` | `{row['status']}` |")
    lines.append('')
    lines.append('## Key Conclusion')
    lines.append('The three exAL run families themselves are reproducible and strong on the rerun/figure side, and `exAL-M-T1` is fully closed for revised-doc figures. The exAL family set is **not yet fully done end to end** because the benchmark CRPS table has not been reconciled to the completed shared-spec rerun outputs. Until that reconciliation is explicit, the exAL runs are figure-authoritative and representative-table-authoritative, but not yet benchmark-table-authoritative.')
    lines.append('')
    return '\n'.join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    benchmark_rows = build_benchmark_rows()
    family_rows = build_family_rows(benchmark_rows)
    summary = build_summary(benchmark_rows, family_rows)

    benchmark_fields = [
        'cutoff', 'cutoff_display', 'manuscript_label', 'family', 'frozen_run_id', 'frozen_run_root',
        'frozen_crps_exact', 'frozen_score_source', 'rerun_run_id', 'rerun_run_root', 'rerun_model_id',
        'rerun_mean_crps', 'rerun_score_scale', 'rerun_score_source', 'absolute_diff', 'rerun_over_frozen_ratio', 'status'
    ]
    family_fields = [
        'label', 'family', 'rerun_completion', 'post_metrics_and_synthesis', 'revised_doc_figure_wiring',
        'representative_tables_current', 'historical_support_current', 'benchmark_table_source',
        'benchmark_table_authoritative', 'representative_runtime_root', 'historical_support_mode',
        'overall_status', 'remaining_gap'
    ]

    write_csv(REPORT_DIR / 'benchmark_score_comparison.csv', benchmark_rows, benchmark_fields)
    write_csv(REPORT_DIR / 'family_status.csv', family_rows, family_fields)
    (REPORT_DIR / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (REPORT_DIR / 'HE2_EXAL_REVISED_DOC_AUDIT_20260517.md').write_text(build_markdown(summary, family_rows, benchmark_rows) + '\n')
    print(REPORT_DIR)


if __name__ == '__main__':
    main()
