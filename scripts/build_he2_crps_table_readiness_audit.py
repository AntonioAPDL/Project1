#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'reports' / 'he2_crps_table_readiness_20260517'
OUT_DIR.mkdir(parents=True, exist_ok=True)

EXAL_AUDIT_SUMMARY = ROOT / 'reports' / 'he2_exal_revised_doc_audit_20260517' / 'summary.json'
EXAL_AUDIT_ROWS = ROOT / 'reports' / 'he2_exal_revised_doc_audit_20260517' / 'family_status.csv'
MASTER_SUMMARY = ROOT / 'reports' / 'he2_master_workflow_audit_20260517' / 'summary.json'
MASTER_FAMILIES = ROOT / 'reports' / 'he2_master_workflow_audit_20260517' / 'family_tracker.csv'
ARTICLE_MANIFEST = ROOT / 'Evironmetrics---REVISED-DOC-2' / 'MANUSCRIPT_ASSET_MANIFEST.json'


def read_json(path: Path):
    return json.loads(path.read_text())


def read_csv(path: Path):
    with path.open() as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    exal_summary = read_json(EXAL_AUDIT_SUMMARY)
    master_summary = read_json(MASTER_SUMMARY)
    master_families = read_csv(MASTER_FAMILIES)
    article_manifest = read_json(ARTICLE_MANIFEST)

    benchmark_src = article_manifest['tables']['tab:benchmark_crps_models']['sources']['bayesian_manifest_csv']
    benchmark_note = article_manifest['tables']['tab:benchmark_crps_models']['note']

    rows = []
    for row in master_families:
        label = row['label']
        if label.startswith('N-'):
            gate = 'blocked'
            reason = 'ndlm_not_current_canonical_bundle_aligned'
        elif label in {'AL-M-T1', 'AL-M-T0'}:
            gate = 'blocked'
            reason = 'al_multivar_not_launched_and_q65_diagnostics_failed'
        elif label == 'AL-U-T1':
            gate = 'pending_family_set'
            reason = 'al_univar_complete_but_al_multivar_family_set_not_ready'
        elif label.startswith('exAL-'):
            gate = 'blocked'
            reason = 'exal_benchmark_rows_not_reconciled_to_completed_sharedspec_reruns'
        else:
            gate = 'blocked'
            reason = 'unknown'
        rows.append({
            'label': label,
            'family': row['family'],
            'current_status': row['current_status'],
            'authoritative_state': row['authoritative_state'],
            'crps_table_gate': gate,
            'blocking_reason': reason,
        })

    ready = all(r['crps_table_gate'] == 'ready' for r in rows)
    summary = {
        'crps_table_should_be_updated_now': False,
        'decision': 'keep_frozen_current_benchmark_table',
        'why': [
            'ndlm_families_are_not_current_canonical_bundle_aligned',
            'al_multivar_keep_drop_are_not_launched_and_failed_q65_diagnostics',
            'exal_completed_sharedspec_rerun_local_scores_do_not_match_frozen_benchmark_rows',
        ],
        'benchmark_table_source': benchmark_src,
        'benchmark_table_note': benchmark_note,
        'exal_benchmark_mismatch_count': exal_summary['benchmark_mismatch_count'],
        'ndlm_bundle_alignment': master_summary['ndlm_current_bundle_alignment'],
        'family_gates': rows,
        'all_ready': ready,
    }

    write_csv(OUT_DIR / 'crps_table_family_gates.csv', rows, list(rows[0].keys()))
    (OUT_DIR / 'crps_table_readiness.json').write_text(json.dumps(summary, indent=2) + '\n')

    md = []
    md.append('# HE2 CRPS Table Readiness Audit (2026-05-17)\n\n')
    md.append('## Decision\n\n')
    md.append('Do **not** rebuild or promote the revised-doc CRPS benchmark table yet.\n\n')
    md.append('The table should remain frozen on the current manuscript benchmark source until the full family set is ready under the canonical workflow.\n\n')
    md.append('## Why\n\n')
    md.append('- The three NDLM families are not yet aligned to the current `20260510` canonical shared-input bundle contract.\n')
    md.append('- `AL-M-T1` and `AL-M-T0` are not launched and are currently blocked by the late `20221225 q65` diagnostic failures.\n')
    md.append('- The completed shared-spec exAL rerun-local benchmark scores do not reconcile to the frozen exAL manuscript benchmark rows (`15/15` mismatches in the exAL audit).\n\n')
    md.append('## Current Benchmark Source\n\n')
    md.append(f"- Bayesian source: `{benchmark_src}`\n")
    md.append(f"- Note: {benchmark_note}\n\n")
    md.append('## Family Gates\n\n')
    md.append('| Label | Family | Current status | CRPS table gate | Blocking reason |\n')
    md.append('|---|---|---|---|---|\n')
    for row in rows:
        md.append(f"| `{row['label']}` | `{row['family']}` | `{row['current_status']}` | `{row['crps_table_gate']}` | `{row['blocking_reason']}` |\n")
    md.append('\n')
    md.append('## Conclusion\n\n')
    md.append('The revised-doc benchmark CRPS table should stay frozen until we have:')
    md.append('\n1. NDLM relaunched on the canonical shared bundle,')
    md.append('\n2. AL multivariate keep/drop launched successfully, and')
    md.append('\n3. a deliberate benchmark-table reconciliation policy for the completed exAL shared-spec reruns.\n')
    (OUT_DIR / 'HE2_CRPS_TABLE_READINESS_20260517.md').write_text(''.join(md) + '\n')
    print(OUT_DIR)


if __name__ == '__main__':
    main()
