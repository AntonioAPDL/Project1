from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts' / 'build_he2_wave_a_ndlm_launch_readiness.py'


class HE2WaveANDLMLaunchReadinessTests(unittest.TestCase):
    def test_script_runs_and_writes_outputs(self) -> None:
        proc = subprocess.run(
            ['python3', str(SCRIPT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        out_root = ROOT / 'reports' / 'he2_full_crps_stage1_contract_20260516'
        md_path = out_root / 'HE2_WAVE_A_NDLM_LAUNCH_READINESS_20260516.md'
        json_path = out_root / 'wave_a_ndlm_launch_readiness_20260516.json'
        self.assertTrue(md_path.exists())
        self.assertTrue(json_path.exists())
        payload = json.loads(json_path.read_text(encoding='utf-8'))
        self.assertEqual(payload['status'], 'go')
        self.assertEqual(payload['wave'], 'wave_a_ndlm')
        self.assertEqual(payload['wave_a_selected_scope']['rows'], 15)


if __name__ == '__main__':
    unittest.main()
