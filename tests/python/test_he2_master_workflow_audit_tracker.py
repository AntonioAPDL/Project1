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
    assert summary['remaining_model_input_parity_required'] is True
    assert summary['remaining_8_model_input_parity_required'] is False
    assert summary['publication_parity_gate']['promoted_rows'] == 25
    assert summary['publication_parity_gate']['pending_rows'] == 20
    assert summary['publication_parity_gate']['blocked_rows'] == 5
    assert summary['publication_parity_gate']['remaining_model_families_pending'] == 4
    assert summary['publication_parity_gate']['final_9_model_benchmark_ready'] is False
    assert summary['article_state']['historical_support_refresh']['status'] == 'ok'

    rows = list(csv.DictReader((OUT / 'family_tracker.csv').open()))
    promoted = [r for r in rows if r['label'] in {'exAL-M-T1', 'AL-M-T1', 'exAL-M-T0', 'AL-U-T1', 'exAL-U-T1'}]
    assert len(promoted) == 5
    assert all(r['current_status'] == 'authoritative_current_bundle_promoted' for r in promoted)
    assert all(r['authoritative_state'] == 'production_authoritative' for r in promoted)
    blocked = [r for r in rows if r['label'] == 'AL-M-T0']
    assert len(blocked) == 1
    assert blocked[0]['current_status'] == 'blocked_pending_targeted_diagnostics'
    pending = [r for r in rows if r['label'] in {'N-M-T1', 'N-M-T0', 'N-U-T1'}]
    assert len(pending) == 3
    assert all(r['current_status'] == 'pending_same_bundle_promotion' for r in pending)
