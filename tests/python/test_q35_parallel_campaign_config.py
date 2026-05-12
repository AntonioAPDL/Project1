import importlib.util
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / 'scripts' / 'run_exdqlm_median_overnight_campaign.py'
CONFIG_PATH = ROOT / 'config' / 'q35_parallel_campaign_exdqlm_multivar_keep_20210123_20260512.yaml'
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('q35_campaign', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class Q35ParallelCampaignConfigTests(unittest.TestCase):
    def test_q35_campaign_has_expected_screening_contract(self):
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8'))
        self.assertEqual(cfg['screening']['quantile'], 0.35)
        self.assertEqual(cfg['execution']['concurrency'], 4)
        self.assertEqual(cfg['screening']['gamma_sigma']['min_update_iters'], 5)
        self.assertEqual(cfg['screening']['gamma_sigma']['max_iter'], 10)

    def test_q35_campaign_flattens_expected_probe_ids(self):
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8'))
        tasks = mod._flatten_tasks(cfg)
        probe_ids = [task.probe_id for task in tasks]
        self.assertEqual(len(tasks), 15)
        self.assertIn('current_midscale_anchor', probe_ids)
        self.assertIn('scale060_floor5e4_step015_thetaUpper45', probe_ids)
        self.assertIn('freeze8_scale060_floor5e4_step020_hold20', probe_ids)

    def test_q35_single_probe_config_uses_q35_quantile(self):
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8'))
        task = next(task for task in mod._flatten_tasks(cfg) if task.probe_id == 'scale060_floor1e3_step025')
        single_cfg = mod._build_single_probe_config(cfg, task)
        self.assertEqual(single_cfg['screening']['quantile'], 0.35)
        self.assertTrue(single_cfg['artifact_root'].endswith('/probes/wave2_damping/scale060_floor1e3_step025'))


if __name__ == '__main__':
    unittest.main()
