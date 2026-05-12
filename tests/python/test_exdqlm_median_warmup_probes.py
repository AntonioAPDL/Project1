import importlib.util
import tempfile
import sys
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / 'scripts' / 'run_exdqlm_median_warmup_probes.py'
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('median_probes', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class MedianWarmupProbeTests(unittest.TestCase):
    def test_parse_health_file_extracts_numeric_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'multivar_forecast_health.txt'
            path.write_text(
                '\n'.join([
                    'max_abs_sm_ens=3.5',
                    'nonfinite_sm_ens=0',
                    'max_abs_forecast_exps=9.1',
                    'finite_forecast_exps=36',
                    'nonfinite_forecast_exps=48',
                    'max_E_sigma=0.37',
                ]),
                encoding='utf-8',
            )
            metrics = mod._parse_health_file(path)
        self.assertEqual(metrics['nonfinite_sm_ens'], 0)
        self.assertEqual(metrics['finite_forecast_exps'], 36)
        self.assertEqual(metrics['nonfinite_forecast_exps'], 48)
        self.assertAlmostEqual(metrics['max_E_sigma'], 0.37)

    def test_remove_tree_if_exists_removes_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'run_root'
            (root / 'fit' / 'logs').mkdir(parents=True)
            (root / 'fit' / 'logs' / 'fit.log').write_text('x', encoding='utf-8')
            self.assertTrue(root.exists())
            mod._remove_tree_if_exists(root)
            self.assertFalse(root.exists())

    def test_prepare_config_single_quantile_and_fit_only(self):
        base_cfg = {
            'run': {'run_id': 'base', 'run_root': '/tmp/base', 'overwrite': False, 'auto_suffix_on_collision': False, 'threads': {'mc_cores': 7}},
            'fit': {'quantiles': [0.05, 0.5], 'parallel': {'mode': 'global_models', 'workers': 7}, 'exdqlm_multivar': {'gamma_sigma': {'warmup_freeze_iters': 5}}},
            'models': {'run_exdqlm_multivar': True, 'run_exdqlm_univar': True, 'run_ndlm_main': True, 'run_ndlm_univar': True},
            'stages': {'forecats': True, 'data_prep_shared': True, 'fit': True, 'post': True, 'validate': True, 'report': True},
        }
        cfg = mod._prepare_config(
            base_cfg,
            artifact_root=Path('/tmp/artifacts'),
            run_id='probe',
            quantile=0.5,
            workers=1,
            mc_cores=1,
            stages={'data_prep_shared': True, 'fit': True},
            gamma_sigma_patch={'max_iter': 30, 'min_update_iters': 10, 'min_total_iters': 20},
            probe_patch={'fit': {'exdqlm_multivar': {'gamma_sigma': {'warmup_freeze_iters': 15}}}},
        )
        self.assertEqual(cfg['fit']['quantiles'], [0.5])
        self.assertEqual(cfg['fit']['parallel']['workers'], 1)
        self.assertEqual(cfg['run']['threads']['mc_cores'], 1)
        self.assertTrue(cfg['stages']['fit'])
        self.assertFalse(cfg['stages']['post'])
        self.assertTrue(cfg['models']['run_exdqlm_multivar'])
        self.assertFalse(cfg['models']['run_exdqlm_univar'])
        self.assertEqual(cfg['fit']['exdqlm_multivar']['gamma_sigma']['warmup_freeze_iters'], 15)
        self.assertEqual(cfg['fit']['exdqlm_multivar']['gamma_sigma']['max_iter'], 30)

    def test_analyze_log_flags_pathology(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log = tmp_path / 'fit.log'
            log.write_text(
                '\n'.join([
                    '[gamsig_guard] non-finite dq_transf at p0=0.5',
                    '[gamsig_guard] non-invertible Hessian at p0=0.5',
                    '[gamsig_refreeze] p0=0.5 iter=6 old_until=5 new_until=16',
                    '[gamsig_progress] family=exdqlm_multivar p0=0.5 iter=20 elbo=-10 crit_elbo=1 sigma_exp=6258 crit_sigma_exp=0 gamma_exp=0.5 crit_gamma_exp=0 sigma_exp_vec=[1,2,3] gamma_exp_vec=[0,0,0] sigma_delta_vec=[0,0,0] gamma_delta_vec=[0,0,0] state_norm_sq=1000000000 crit_state_norm_sq=1 conv_check=NA gamsig_update_iters=1 min_update_iters=10 min_total_iters=20 frozen=true'
                ]),
                encoding='utf-8',
            )
            result = mod._analyze_log(
                log,
                {
                    'max_guard_events': 0,
                    'max_hessian_failures': 0,
                    'max_sigma_exp': 100.0,
                    'max_state_norm_sq': 1e8,
                    'min_gamsig_update_iters': 8,
                    'require_finite_conv_check': True,
                },
                'baseline',
                'screening',
                'run1',
                0,
                tmp_path,
                0.5,
            )
            self.assertFalse(result.healthy)
            self.assertEqual(result.guard_events, 1)
            self.assertEqual(result.hessian_failures, 1)
            self.assertEqual(result.refreezes, 1)
            self.assertEqual(result.last_updates, 1)

    def test_analyze_log_uses_forecast_health_rules(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_root = tmp_path / 'runs' / 'demo'
            q_dir = run_root / 'fit' / 'exdqlm_multivar' / 'keep' / 'q=35'
            (q_dir / 'logs').mkdir(parents=True)
            (q_dir / 'outputs').mkdir(parents=True)
            log = q_dir / 'logs' / 'fit.log'
            log.write_text(
                '[gamsig_progress] family=exdqlm_multivar p0=0.35 iter=18 elbo=-1 crit_elbo=0.1 sigma_exp=3.08 crit_sigma_exp=0.001 gamma_exp=-0.53 crit_gamma_exp=0.001 sigma_exp_vec=[1,2,3] gamma_exp_vec=[0,0,0] sigma_delta_vec=[0,0,0] gamma_delta_vec=[0,0,0] state_norm_sq=294797.2 crit_state_norm_sq=0 conv_check=0.00002 gamsig_update_iters=17 min_update_iters=6 min_total_iters=12 frozen=false\n',
                encoding='utf-8',
            )
            (q_dir / 'outputs' / 'multivar_forecast_health.txt').write_text(
                '\n'.join([
                    'max_abs_sm_ens=3.879350942',
                    'nonfinite_sm_ens=0',
                    'max_abs_forecast_exps=3.070998062',
                    'finite_forecast_exps=36',
                    'nonfinite_forecast_exps=48',
                    'max_E_sigma=9.034567899',
                ]),
                encoding='utf-8',
            )
            result = mod._analyze_log(
                log,
                {
                    'max_guard_events': 0,
                    'max_hessian_failures': 0,
                    'max_sigma_exp': 20.0,
                    'max_state_norm_sq': 5e14,
                    'min_gamsig_update_iters': 6,
                    'require_finite_conv_check': True,
                    'max_abs_sm_ens': 1000.0,
                    'max_abs_forecast_exps': 650.0,
                    'max_E_sigma': 100.0,
                    'max_nonfinite_sm_ens': 0,
                    'max_nonfinite_forecast_exps': 48,
                },
                'q35',
                'screening',
                'run_q35',
                0,
                run_root,
                0.35,
            )
            self.assertTrue(result.healthy)
            self.assertAlmostEqual(result.max_abs_sm_ens or 0.0, 3.879350942)
            self.assertEqual(result.nonfinite_forecast_exps, 48)

    def test_probe_id_filter_errors_when_missing(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_cfg = tmp_path / 'base.yaml'
            base_cfg.write_text(
                '\n'.join([
                    'run: {run_id: base, run_root: /tmp/base_runs, overwrite: false, auto_suffix_on_collision: false, threads: {mc_cores: 1}}',
                    'fit: {quantiles: [0.5], parallel: {mode: global_models, workers: 1}, exdqlm_multivar: {gamma_sigma: {}}}',
                    'models: {run_exdqlm_multivar: true, run_exdqlm_univar: false, run_ndlm_main: false, run_ndlm_univar: false}',
                    'stages: {data_prep_shared: true, fit: true, post: false, validate: false, report: false}',
                ]),
                encoding='utf-8',
            )
            cfg = tmp_path / 'probes.yaml'
            cfg.write_text(
                '\n'.join([
                    'probe: {id: test, description: test}',
                    f'base_generated_config: {base_cfg.as_posix()}',
                    'artifact_root: /tmp/artifacts',
                    'screening:',
                    '  quantile: 0.5',
                    '  stages: {data_prep_shared: true, fit: true}',
                    '  fit_parallel_workers: 1',
                    '  mc_cores: 1',
                    '  gamma_sigma: {}',
                    '  health_rules: {max_guard_events: 0, max_hessian_failures: 0, max_sigma_exp: 100.0, max_state_norm_sq: 100000000.0, min_gamsig_update_iters: 1, require_finite_conv_check: true}',
                    'probes:',
                    '  - {id: baseline, config_patch: {}}',
                ]),
                encoding='utf-8',
            )
            proc = subprocess.run(
                ['python3', str(MODULE_PATH), '--config', str(cfg), '--probe-id', 'missing'],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('No probes matched --probe-id values', proc.stderr + proc.stdout)


if __name__ == '__main__':
    unittest.main()
