import importlib.util
import sys
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
            )
            self.assertFalse(result.healthy)
            self.assertEqual(result.guard_events, 1)
            self.assertEqual(result.hessian_failures, 1)
            self.assertEqual(result.refreezes, 1)
            self.assertEqual(result.last_updates, 1)


if __name__ == '__main__':
    unittest.main()
