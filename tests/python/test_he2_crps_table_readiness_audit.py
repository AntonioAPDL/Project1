from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports' / 'he2_crps_table_readiness_20260517'


def test_crps_table_readiness_keeps_table_frozen() -> None:
    subprocess.run(['python3', 'scripts/build_he2_crps_table_readiness_audit.py'], cwd=ROOT, check=True)
    summary = json.loads((OUT / 'crps_table_readiness.json').read_text())
    assert summary['crps_table_should_be_updated_now'] is False
    assert summary['decision'] == 'keep_frozen_current_benchmark_table'
    assert summary['exal_benchmark_mismatch_count'] == 15
    assert summary['ndlm_bundle_alignment']['aligned_to_20260510_canonical_shared_bundle'] is False

    rows = list(csv.DictReader((OUT / 'crps_table_family_gates.csv').open()))
    assert next(r for r in rows if r['label'] == 'AL-U-T1')['crps_table_gate'] == 'pending_family_set'
    assert all(next(r for r in rows if r['label'] == label)['crps_table_gate'] == 'blocked' for label in ['N-M-T1', 'N-M-T0', 'N-U-T1'])
