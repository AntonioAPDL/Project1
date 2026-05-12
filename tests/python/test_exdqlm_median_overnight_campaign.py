import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / 'scripts' / 'run_exdqlm_median_overnight_campaign.py'
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('median_overnight', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class MedianOvernightCampaignTests(unittest.TestCase):
    def _campaign_cfg(self) -> dict:
        return {
            'campaign': {'id': 'demo_campaign', 'description': 'demo'},
            'base_generated_config': '/tmp/base.yaml',
            'artifact_root': '/tmp/median_campaign',
            'execution': {'concurrency': 4},
            'screening': {
                'quantile': 0.5,
                'stages': {'data_prep_shared': True, 'fit': True},
                'fit_parallel_workers': 1,
                'mc_cores': 1,
                'gamma_sigma': {'min_update_iters': 10},
                'health_rules': {'max_guard_events': 0},
            },
            'waves': [
                {
                    'id': 'wave1',
                    'probes': [
                        {'id': 'a', 'batch': 'anchors', 'description': 'A', 'config_patch': {}},
                        {'id': 'b', 'batch': 'anchors', 'description': 'B', 'config_patch': {'fit': {'x': 1}}},
                    ],
                },
                {
                    'id': 'wave2',
                    'probes': [
                        {'id': 'c', 'batch': 'state', 'description': 'C', 'config_patch': {'fit': {'y': 2}}},
                    ],
                },
            ],
        }

    def test_flatten_tasks_respects_filters_and_limit(self):
        cfg = self._campaign_cfg()
        tasks = mod._flatten_tasks(cfg, selected_waves={'wave1'}, selected_probe_ids={'b'}, max_probes=1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].wave_id, 'wave1')
        self.assertEqual(tasks[0].probe_id, 'b')
        self.assertEqual(tasks[0].batch, 'anchors')

    def test_build_single_probe_config_uses_probe_root(self):
        cfg = self._campaign_cfg()
        task = mod._flatten_tasks(cfg)[1]
        single_cfg = mod._build_single_probe_config(cfg, task)
        self.assertEqual(single_cfg['probes'][0]['id'], 'b')
        self.assertTrue(single_cfg['artifact_root'].endswith('/probes/wave1/b'))
        self.assertEqual(single_cfg['screening']['quantile'], 0.5)
        self.assertEqual(single_cfg['base_generated_config'], '/tmp/base.yaml')

    def test_build_result_row_marks_missing_outputs(self):
        cfg = self._campaign_cfg()
        task = mod._flatten_tasks(cfg)[0]
        with tempfile.TemporaryDirectory() as tmp:
            row = mod._build_result_row(
                task,
                phase='screening',
                config_path=Path(tmp) / 'cfg.yaml',
                artifact_root=Path(tmp) / 'artifact',
                worker_log_path=Path(tmp) / 'worker.log',
                process_exit_code=7,
                elapsed_seconds=1.25,
            )
        self.assertFalse(row['selected_healthy'])
        self.assertEqual(row['phase'], 'screening')
        self.assertEqual(row['selected_note'], 'missing_probe_summary')
        self.assertEqual(row['process_exit_code'], 7)

    def test_read_single_probe_outputs_parses_single_probe_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / 'reports'
            reports.mkdir(parents=True)
            (reports / 'winner_summary.json').write_text(
                json.dumps({'selected_healthy': True, 'selected_note': 'healthy', 'best_healthy': True, 'best_note': 'healthy'}),
                encoding='utf-8',
            )
            (reports / 'probe_results.csv').write_text(
                'probe_id,phase,guard_events,hessian_failures,refreezes,last_iter,last_updates,max_sigma_exp,max_state_norm_sq,last_conv_check\n'
                'demo,screening,0,0,0,12,9,2.5,1000,0.01\n',
                encoding='utf-8',
            )
            summary, screening = mod._read_single_probe_outputs(root)
        self.assertTrue(summary['selected_healthy'])
        self.assertEqual(screening['phase'], 'screening')
        self.assertEqual(screening['last_updates'], '9')

    def test_build_confirmation_probe_config_uses_confirmation_contract(self):
        cfg = self._campaign_cfg()
        cfg['confirmation'] = {
            'enabled': True,
            'top_n': 2,
            'stages': {'data_prep_shared': True, 'fit': True},
            'fit_parallel_workers': 1,
            'mc_cores': 1,
            'gamma_sigma': {'min_update_iters': 12, 'max_iter': 40},
            'health_rules': {'max_guard_events': 0, 'min_gamsig_update_iters': 12},
        }
        task = mod._flatten_tasks(cfg)[0]
        single_cfg = mod._build_confirmation_probe_config(cfg, task)
        self.assertEqual(single_cfg['screening']['quantile'], 0.5)
        self.assertEqual(single_cfg['screening']['gamma_sigma']['min_update_iters'], 12)
        self.assertEqual(single_cfg['screening']['fit_parallel_workers'], 1)
        self.assertTrue(single_cfg['artifact_root'].endswith('/confirmations/wave1/a'))

    def test_select_confirmation_tasks_returns_top_healthy_screening_rows(self):
        cfg = self._campaign_cfg()
        tasks = mod._flatten_tasks(cfg)
        task_map = {task.probe_id: task for task in tasks}
        results = [
            {'phase': 'screening', 'probe_id': 'a', 'selected_healthy': False, 'guard_events': 1, 'hessian_failures': 0, 'max_sigma_exp': 50, 'last_conv_check': None, 'patch_leaf_count': 0, 'wave_order': 1, 'wave_id': 'wave1'},
            {'phase': 'screening', 'probe_id': 'b', 'selected_healthy': True, 'guard_events': 0, 'hessian_failures': 0, 'max_sigma_exp': 2.0, 'last_conv_check': 0.01, 'patch_leaf_count': 1, 'wave_order': 1, 'wave_id': 'wave1'},
            {'phase': 'confirmation', 'probe_id': 'c', 'selected_healthy': True, 'guard_events': 0, 'hessian_failures': 0, 'max_sigma_exp': 1.0, 'last_conv_check': 0.001, 'patch_leaf_count': 1, 'wave_order': 2, 'wave_id': 'wave2'},
            {'phase': 'screening', 'probe_id': 'c', 'selected_healthy': True, 'guard_events': 0, 'hessian_failures': 0, 'max_sigma_exp': 3.0, 'last_conv_check': 0.02, 'patch_leaf_count': 1, 'wave_order': 2, 'wave_id': 'wave2'},
        ]
        selected = mod._select_confirmation_tasks(results, task_map, top_n=1)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].probe_id, 'b')


if __name__ == '__main__':
    unittest.main()
