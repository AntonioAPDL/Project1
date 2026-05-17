from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts' / 'audit_current_model_output_support_contract.py'


class CurrentModelOutputSupportContractAuditTests(unittest.TestCase):
    def test_script_runs_and_writes_outputs(self) -> None:
        proc = subprocess.run(
            ['python3', str(SCRIPT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        out_root = ROOT / 'reports' / 'current_model_output_support_contract_audit_20260517'
        md_path = out_root / 'CURRENT_MODEL_OUTPUT_SUPPORT_CONTRACT_AUDIT_20260517.md'
        json_path = out_root / 'current_model_output_support_contract_audit_20260517.json'
        self.assertTrue(md_path.exists())
        self.assertTrue(json_path.exists())
        payload = json.loads(json_path.read_text(encoding='utf-8'))
        self.assertIn(payload['status'], {'repair_open', 'repair_ready', 'repaired_via_retained_support_contract', 'ready'})
        self.assertTrue(payload['univar_png_exists'])
        self.assertIn('support_run_fit_contract_present', payload)
        self.assertIn('retained_state_summary_exists', payload)


if __name__ == '__main__':
    unittest.main()
