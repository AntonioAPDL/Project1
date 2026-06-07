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
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
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
        if row['authoritative_state'] == 'production_authoritative':
            gate = 'ready_transitional_snapshot'
            reason = 'canonical_bundle_promoted_current_manifest_row'
        elif label.startswith('N-'):
            gate = 'blocked'
            reason = 'ndlm_not_current_canonical_bundle_aligned'
        else:
            gate = 'blocked'
            reason = 'not_current_canonical_bundle_aligned'
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
        'decision': 'current_manifest_snapshot_updated_but_not_paper_final',
        'why': [
            'ndlm_families_are_not_current_canonical_bundle_aligned',
            'full_9_model_benchmark_requires_ndlm_same_bundle_promotion',
        ],
        'benchmark_table_source': benchmark_src,
        'benchmark_table_note': benchmark_note,
        'exal_benchmark_mismatch_count': exal_summary['benchmark_mismatch_count'],
        'ndlm_bundle_alignment': {
            'aligned_to_20260510_canonical_shared_bundle': False,
            'pending_labels': [row['label'] for row in master_families if row['label'].startswith('N-')],
        },
        'publication_parity_gate': master_summary.get('publication_parity_gate', {}),
        'family_gates': rows,
        'all_ready': ready,
    }

    write_csv(OUT_DIR / 'crps_table_family_gates.csv', rows, list(rows[0].keys()))
    (OUT_DIR / 'crps_table_readiness.json').write_text(json.dumps(summary, indent=2) + '\n')

    md = []
    md.append('# HE2 CRPS Table Readiness Audit (2026-05-17)\n\n')
    md.append('## Decision\n\n')
    md.append('The revised-doc CRPS benchmark table may use the current manifest snapshot as a transitional source, but it is **not paper-final** yet.\n\n')
    md.append('The full 9-model benchmark should not be interpreted as final until the three NDLM families are promoted onto the canonical workflow.\n\n')
    md.append('## Why\n\n')
    md.append('- The three NDLM families are not yet aligned to the current `20260510` canonical shared-input bundle contract.\n')
    md.append('- Six Bayesian families are now canonical-bundle promoted in the manifest: `exAL-M-T1`, `AL-M-T1`, `exAL-M-T0`, `AL-M-T0`, `AL-U-T1`, and `exAL-U-T1`.\n\n')
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
    md.append('The revised-doc benchmark CRPS table should remain labeled transitional until we have:')
    md.append('\n1. NDLM relaunched or promoted on the canonical shared bundle,')
    md.append('\n2. a rebuilt publication manifest and parity gate with no pending families, and')
    md.append('\n3. refreshed article assets and generated tables from that final manifest.\n')
    (OUT_DIR / 'HE2_CRPS_TABLE_READINESS_20260517.md').write_text(''.join(md) + '\n')
    print(OUT_DIR)


if __name__ == '__main__':
    main()
