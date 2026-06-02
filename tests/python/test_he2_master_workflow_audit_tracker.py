from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports' / 'he2_master_workflow_audit_20260517'


def test_master_workflow_audit_tracker_current_state() -> None:
    subprocess.run(['python3', 'scripts/build_he2_master_workflow_audit_tracker.py'], cwd=ROOT, check=True)
    summary = json.loads((OUT / 'summary.json').read_text())
    assert summary['remaining_8_model_input_parity_required'] is True
    assert summary['publication_parity_gate']['promoted_rows'] == 5
    assert summary['publication_parity_gate']['pending_rows'] == 40
    assert summary['publication_parity_gate']['final_9_model_benchmark_ready'] is False
    assert summary['article_state']['historical_support_refresh']['status'] == 'ok'

    rows = list(csv.DictReader((OUT / 'family_tracker.csv').open()))
    promoted = next(r for r in rows if r['label'] == 'exAL-M-T1')
    assert promoted['current_status'] == 'authoritative_current_bundle_promoted'
    assert promoted['authoritative_state'] == 'production_authoritative'
    pending = [r for r in rows if r['label'] != 'exAL-M-T1']
    assert len(pending) == 8
    assert all(r['current_status'] == 'pending_same_bundle_promotion' for r in pending)
