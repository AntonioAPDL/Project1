from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / 'reports' / 'he2_exal_revised_doc_audit_20260517'


def test_exal_revised_doc_audit_marks_benchmark_blocker() -> None:
    subprocess.run(['python3', 'scripts/build_he2_exal_revised_doc_audit.py'], cwd=ROOT, check=True)

    summary = json.loads((REPORT_DIR / 'summary.json').read_text())
    assert summary['final_certification'] == 'blocked_on_benchmark_table_reconciliation'
    assert summary['benchmark_mismatch_count'] == 15
    assert summary['representative_table_sources_current'] is True
    assert summary['historical_support_repaired'] is True

    rows = list(csv.DictReader((REPORT_DIR / 'family_status.csv').open()))
    keep = next(row for row in rows if row['label'] == 'exAL-M-T1')
    assert keep['revised_doc_figure_wiring'] == 'fully_closed_for_figures'
    assert keep['benchmark_table_authoritative'] == 'no'
    assert keep['overall_status'] == 'figures_closed_benchmark_blocked'
