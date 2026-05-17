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
    assert summary['article_state']['historical_support_contract_status'] == 'repaired_via_retained_support_contract'
    assert summary['article_state']['crps_table_readiness']['decision'] == 'keep_frozen_current_benchmark_table'
    assert summary['article_state']['lineage_status_counts'] == {'unchanged_intentionally': 8, 'updated_now': 39}

    rows = list(csv.DictReader((OUT / 'family_tracker.csv').open()))
    al_univar = next(r for r in rows if r['label'] == 'AL-U-T1')
    assert al_univar['current_status'] == 'authoritative_complete'
    assert al_univar['authoritative_state'] == 'production_complete'
