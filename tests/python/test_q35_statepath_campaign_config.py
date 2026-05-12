import importlib.util
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / 'scripts' / 'run_exdqlm_median_overnight_campaign.py'
NEW_CONFIG_PATH = ROOT / 'config' / 'q35_statepath_campaign_exdqlm_multivar_keep_20210123_20260512.yaml'
OLD_CONFIG_PATH = ROOT / 'config' / 'q35_parallel_campaign_exdqlm_multivar_keep_20210123_20260512.yaml'
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('q35_statepath_campaign', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class Q35StatepathCampaignConfigTests(unittest.TestCase):
    def test_old_q35_campaign_emits_nonmedian_noop_warnings(self):
        cfg = yaml.safe_load(OLD_CONFIG_PATH.read_text(encoding='utf-8'))
        tasks = mod._flatten_tasks(cfg)
        warnings = mod._collect_noop_warnings(cfg, tasks)
        self.assertGreater(len(warnings), 0)
        probe_ids = {item['probe_id'] for item in warnings}
        self.assertIn('current_midscale_anchor', probe_ids)

    def test_new_q35_campaign_has_no_nonmedian_noop_warnings(self):
        cfg = yaml.safe_load(NEW_CONFIG_PATH.read_text(encoding='utf-8'))
        tasks = mod._flatten_tasks(cfg)
        warnings = mod._collect_noop_warnings(cfg, tasks)
        self.assertEqual(warnings, [])

    def test_new_q35_campaign_flattens_expected_probe_ids(self):
        cfg = yaml.safe_load(NEW_CONFIG_PATH.read_text(encoding='utf-8'))
        tasks = mod._flatten_tasks(cfg)
        probe_ids = [task.probe_id for task in tasks]
        self.assertEqual(len(tasks), 20)
        self.assertIn('sfreeze5_scale050_floor1e2', probe_ids)
        self.assertIn('gfreeze1_scale060_floor5e4_thetaUpper30_ridge1e3', probe_ids)

    def test_state_freeze_probe_sets_screening_freeze_target(self):
        cfg = yaml.safe_load(NEW_CONFIG_PATH.read_text(encoding='utf-8'))
        task = next(task for task in mod._flatten_tasks(cfg) if task.probe_id == 'sfreeze5_scale050_floor1e2')
        single_cfg = mod._build_single_probe_config(cfg, task)
        self.assertEqual(single_cfg['screening']['quantile'], 0.35)
        self.assertEqual(single_cfg['screening']['gamma_sigma']['freeze_target'], 'states')
        self.assertTrue(single_cfg['artifact_root'].endswith('/probes/wave1_state_freeze/sfreeze5_scale050_floor1e2'))

    def test_new_q35_campaign_enables_confirmation(self):
        cfg = yaml.safe_load(NEW_CONFIG_PATH.read_text(encoding='utf-8'))
        self.assertTrue(cfg['confirmation']['enabled'])
        self.assertEqual(cfg['confirmation']['gamma_sigma']['min_update_iters'], 10)
        self.assertEqual(cfg['execution']['concurrency'], 6)


if __name__ == '__main__':
    unittest.main()
