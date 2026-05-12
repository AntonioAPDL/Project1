import importlib.util
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / 'scripts' / 'run_exdqlm_median_overnight_campaign.py'
CONFIG_PATH = ROOT / 'config' / 'q35_final_background_campaign_exdqlm_multivar_keep_20210123_20260512.yaml'
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('q35_final_campaign', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class Q35FinalBackgroundCampaignConfigTests(unittest.TestCase):
    def test_campaign_has_expected_probe_count_and_no_noop_warnings(self):
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8'))
        tasks = mod._flatten_tasks(cfg)
        warnings = mod._collect_noop_warnings(cfg, tasks)
        self.assertEqual(len(tasks), 32)
        self.assertEqual(warnings, [])

    def test_campaign_uses_single_core_defaults_and_confirmation_top_n(self):
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8'))
        self.assertEqual(cfg['execution']['concurrency'], 12)
        self.assertEqual(cfg['screening']['fit_parallel_workers'], 1)
        self.assertEqual(cfg['screening']['mc_cores'], 1)
        self.assertEqual(cfg['confirmation']['fit_parallel_workers'], 1)
        self.assertEqual(cfg['confirmation']['mc_cores'], 1)
        self.assertTrue(cfg['confirmation']['enabled'])
        self.assertEqual(cfg['confirmation']['top_n'], 4)

    def test_post_thaw_probe_uses_generic_nonmedian_state_controls(self):
        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8'))
        task = next(task for task in mod._flatten_tasks(cfg) if task.probe_id == 'w2_a_hold10_blend085')
        single_cfg = mod._build_single_probe_config(cfg, task)
        stab = single_cfg['probes'][0]['config_patch']['fit']['exdqlm_multivar']['gamma_sigma']['stabilization']
        self.assertTrue(stab['state_guard_enabled'])
        self.assertEqual(stab['state_hold_after_guard_iters'], 10)
        self.assertEqual(stab['state_blend_alpha'], 0.85)
        self.assertEqual(stab['cov_blend_alpha'], 1.0)
        self.assertEqual(single_cfg['screening']['gamma_sigma']['freeze_target'], 'states')
        self.assertTrue(single_cfg['artifact_root'].endswith('/probes/wave2_post_thaw_state_control/w2_a_hold10_blend085'))


if __name__ == '__main__':
    unittest.main()
