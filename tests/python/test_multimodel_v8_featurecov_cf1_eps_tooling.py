#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
os.sys.path.insert(0, str(ROOT / 'scripts'))

from build_multimodel_v8_featurecov_cf1_eps_compare_bundle import build_bundle  # noqa: E402
from build_multimodel_v8_featurecov_cf1_eps_matrix_configs import (  # noqa: E402
    _build_run_config,
    _configs_match_for_reuse,
)
from multimodel_v8_lib import load_yaml, runs_dir  # noqa: E402


class FeaturecovCf1EpsToolingTests(unittest.TestCase):
    def _make_source_snapshot(self, td: Path, run_name: str = 'source_run') -> Path:
        run_root = td / 'source_artifact' / 'runs' / run_name
        shared_root = run_root / 'inputs' / 'shared'
        (shared_root / 'parameters').mkdir(parents=True, exist_ok=True)
        (shared_root / 'retros').mkdir(parents=True, exist_ok=True)
        (shared_root / 'forecasts').mkdir(parents=True, exist_ok=True)
        (shared_root / 'forecats_bundle').mkdir(parents=True, exist_ok=True)
        (shared_root / 'covariates').mkdir(parents=True, exist_ok=True)
        (shared_root / 'parameters' / 'parameters.txt').write_text('alpha=1\n', encoding='utf-8')
        (shared_root / 'retros' / 'retros.csv').write_text('Date,USGS,GloFAS,NWS3.0\n2021-01-01,1,2,3\n', encoding='utf-8')
        (shared_root / 'forecasts' / 'nws_forecast.csv').write_text('Date,value\n2021-01-24,1\n', encoding='utf-8')
        (shared_root / 'forecasts' / 'glofas_forecast.csv').write_text('Date,value\n2021-01-24,1\n', encoding='utf-8')
        (shared_root / 'forecats_bundle' / 'meta.yaml').write_text('bundle: ok\n', encoding='utf-8')
        for name, filename in [('PPT', 'cov_03_PPT.csv'), ('SOIL', 'cov_04_SOIL.csv'), ('PCA', 'cov_05_PCA.csv')]:
            (shared_root / 'covariates' / filename).write_text(f'Date,{name}\n2021-01-01,1\n', encoding='utf-8')

        cfg = load_yaml(ROOT / 'config' / 'unified_run.template.yaml')
        cfg['run']['run_id'] = run_name
        cfg['run']['run_root'] = str(run_root.parent.parent)
        cfg['models']['run_exdqlm_multivar'] = True
        cfg['models']['run_exdqlm_univar'] = False
        cfg['models']['run_ndlm_main'] = False
        cfg['models']['run_ndlm_univar'] = False
        cfg['models']['exdqlm_multivar']['likelihood_mode'] = 'exal'
        cfg['models']['exdqlm_multivar']['forecast_transfer_mode'] = 'keep'
        cfg['inputs']['fit']['covariates'] = [
            {'name': 'PPT', 'path': str(shared_root / 'covariates' / 'cov_03_PPT.csv')},
            {'name': 'SOIL', 'path': str(shared_root / 'covariates' / 'cov_04_SOIL.csv')},
            {'name': 'PCA', 'path': str(shared_root / 'covariates' / 'cov_05_PCA.csv')},
        ]
        cfg['inputs']['deterministic_climate'] = {'enabled': True, 'handoff_root': '/tmp/handoff'}
        cfg['inputs']['covariate_features'] = {
            'enabled': True,
            'output_filename': 'covariate_features.csv',
            'lag_orders': [1, 2, 3],
            'include_squares': True,
            'include_interaction': True,
        }
        cfg['inputs']['forecats']['existing_bundle_path'] = str(shared_root / 'forecats_bundle' / 'meta.yaml')
        cfg['inputs']['fit']['parameters_path'] = str(shared_root / 'parameters' / 'parameters.txt')
        cfg['inputs']['fit']['retros_path'] = str(shared_root / 'retros' / 'retros.csv')
        cfg['inputs']['fit']['nws_forecast_path'] = str(shared_root / 'forecasts' / 'nws_forecast.csv')
        cfg['inputs']['fit']['glofas_forecast_path'] = str(shared_root / 'forecasts' / 'glofas_forecast.csv')
        resolved = run_root / 'resolved_config.yaml'
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8')
        return resolved

    def test_build_run_config_scopes_multivar_and_sets_cf1_epsilon(self) -> None:
        td = Path(tempfile.mkdtemp(prefix='featurecov_cf1_eps_cfg_'))
        try:
            source_cfg = self._make_source_snapshot(td)
            template_cfg = load_yaml(source_cfg)
            artifact_root = td / 'artifact_root'
            family_cfg = {
                'model_id': 'dqlm_multivar_al_synth_keep',
                'model_key': 'exdqlm_multivar',
                'likelihood_mode': 'al',
                'transfer_mode': 'keep',
            }
            cfg = _build_run_config(
                template_cfg=template_cfg,
                run_id='multimodel_20210123_v8_eps90cf1_dqlm_multivar_al_keep_featurecov_cf1',
                artifact_root=artifact_root,
                family_id='dqlm_multivar_al_keep',
                family_cfg=family_cfg,
                inputs_overrides={
                    'deterministic_climate': {'enabled': True, 'handoff_root': '/tmp/handoff'},
                    'covariate_features': {'enabled': True, 'output_filename': 'covariate_features.csv', 'lag_orders': [1, 2, 3], 'include_squares': True, 'include_interaction': True},
                    'transfer_function_covariates': {'base_covariates': ['PPT', 'SOIL', 'PCA'], 'engineered_terms': ['PPT_sq', 'SOIL_sq', 'PPT_x_SOIL', 'PPT_lag1', 'PPT_lag2', 'PPT_lag3', 'SOIL_lag1', 'SOIL_lag2', 'SOIL_lag3']},
                },
                selection={'source_run': 'source_run', 'source_type': 'baseline', 'compare_dir': '/tmp/compare', 'mean_crps': 0.1, 'source_config': str(source_cfg)},
                epsilon_label='eps90cf1',
                epsilon_value=90.0,
                c_factor=1.0,
                fit_parallel_mode='global_models',
                fit_parallel_workers=1,
                transfer_covariates={'base_covariates': ['PPT', 'SOIL', 'PCA'], 'engineered_terms': ['PPT_sq', 'SOIL_sq', 'PPT_x_SOIL', 'PPT_lag1', 'PPT_lag2', 'PPT_lag3', 'SOIL_lag1', 'SOIL_lag2', 'SOIL_lag3']},
            )
            self.assertTrue(cfg['models']['run_exdqlm_multivar'])
            self.assertFalse(cfg['models']['run_ndlm_main'])
            self.assertEqual(cfg['models']['exdqlm_multivar']['likelihood_mode'], 'al')
            self.assertEqual(cfg['models']['exdqlm_multivar']['forecast_transfer_mode'], 'keep')
            self.assertEqual(cfg['fit']['exdqlm_multivar']['legacy']['forecast_cov']['c_factor'], 1.0)
            self.assertEqual(cfg['fit']['exdqlm_multivar']['legacy']['forecast_cov']['epsilon'], 90.0)
            self.assertEqual(cfg['run']['threads']['mc_cores'], 1)
            self.assertEqual(cfg['fit']['parallel']['workers'], 1)
            self.assertEqual([row['name'] for row in cfg['inputs']['fit']['covariates']], ['PPT', 'SOIL', 'PCA'])
            self.assertEqual(cfg['debug_featurecov_cf1_eps_campaign']['transfer_function_covariates']['base_covariates'], ['PPT', 'SOIL', 'PCA'])
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_build_run_config_scopes_ndlm_main_and_sets_cf1_epsilon(self) -> None:
        td = Path(tempfile.mkdtemp(prefix='featurecov_cf1_eps_ndlm_'))
        try:
            source_cfg = self._make_source_snapshot(td)
            template_cfg = load_yaml(source_cfg)
            artifact_root = td / 'artifact_root'
            family_cfg = {
                'model_id': 'ndlm_main_synth_drop',
                'model_key': 'ndlm_main',
                'transfer_mode': 'drop',
            }
            cfg = _build_run_config(
                template_cfg=template_cfg,
                run_id='multimodel_20210123_v8_eps60cf1_ndlm_main_drop_featurecov_cf1',
                artifact_root=artifact_root,
                family_id='ndlm_main_drop',
                family_cfg=family_cfg,
                inputs_overrides={
                    'deterministic_climate': {'enabled': True, 'handoff_root': '/tmp/handoff'},
                    'covariate_features': {'enabled': True, 'output_filename': 'covariate_features.csv', 'lag_orders': [1, 2, 3], 'include_squares': True, 'include_interaction': True},
                },
                selection={'source_run': 'source_run', 'source_type': 'baseline', 'compare_dir': '/tmp/compare', 'mean_crps': 0.1, 'source_config': str(source_cfg)},
                epsilon_label='eps60cf1',
                epsilon_value=60.0,
                c_factor=1.0,
                fit_parallel_mode='global_models',
                fit_parallel_workers=1,
                transfer_covariates={'base_covariates': ['PPT', 'SOIL', 'PCA'], 'engineered_terms': ['PPT_sq', 'SOIL_sq', 'PPT_x_SOIL', 'PPT_lag1', 'PPT_lag2', 'PPT_lag3', 'SOIL_lag1', 'SOIL_lag2', 'SOIL_lag3']},
            )
            self.assertTrue(cfg['models']['run_ndlm_main'])
            self.assertFalse(cfg['models']['run_exdqlm_multivar'])
            self.assertEqual(cfg['models']['ndlm_main']['forecast_transfer_mode'], 'drop')
            self.assertEqual(cfg['models']['ndlm_main']['prior']['forecast_cov']['c_factor'], 1.0)
            self.assertEqual(cfg['models']['ndlm_main']['prior']['forecast_cov']['epsilon'], 60.0)
            self.assertEqual(cfg['run']['threads']['mc_cores'], 1)
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_configs_match_for_reuse_requires_exact_scientific_match(self) -> None:
        td = Path(tempfile.mkdtemp(prefix='featurecov_cf1_eps_reuse_'))
        try:
            source_cfg = self._make_source_snapshot(td)
            base = load_yaml(source_cfg)
            family_cfg = {
                'model_id': 'exdqlm_multivar_synth_keep',
                'model_key': 'exdqlm_multivar',
                'likelihood_mode': 'exal',
                'transfer_mode': 'keep',
            }
            new_cfg = _build_run_config(
                template_cfg=base,
                run_id='new_run',
                artifact_root=td / 'artifact_root',
                family_id='exdqlm_multivar_keep',
                family_cfg=family_cfg,
                inputs_overrides={'deterministic_climate': {'enabled': True, 'handoff_root': '/tmp/handoff'}, 'covariate_features': {'enabled': True, 'output_filename': 'covariate_features.csv', 'lag_orders': [1, 2, 3], 'include_squares': True, 'include_interaction': True}},
                selection={'source_run': 'source_run', 'source_type': 'baseline', 'compare_dir': '/tmp/compare', 'mean_crps': 0.1, 'source_config': str(source_cfg)},
                epsilon_label='eps180cf1',
                epsilon_value=180.0,
                c_factor=1.0,
                fit_parallel_mode='global_models',
                fit_parallel_workers=1,
                transfer_covariates={'base_covariates': ['PPT', 'SOIL', 'PCA'], 'engineered_terms': ['PPT_sq', 'SOIL_sq', 'PPT_x_SOIL', 'PPT_lag1', 'PPT_lag2', 'PPT_lag3', 'SOIL_lag1', 'SOIL_lag2', 'SOIL_lag3']},
            )
            prior_cfg = yaml.safe_load(yaml.safe_dump(new_cfg))
            self.assertTrue(_configs_match_for_reuse(new_cfg, prior_cfg, family_cfg, 1.0, 180.0))
            prior_cfg['fit']['exdqlm_multivar']['legacy']['forecast_cov']['epsilon'] = 90.0
            self.assertFalse(_configs_match_for_reuse(new_cfg, prior_cfg, family_cfg, 1.0, 180.0))
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_compare_bundle_replaces_only_swept_rows(self) -> None:
        td = Path(tempfile.mkdtemp(prefix='featurecov_cf1_eps_bundle_'))
        artifact_root = td / 'artifact_root'
        matrix_dir = td / 'matrix'
        reports_dir = artifact_root / 'reports'
        try:
            matrix_dir.mkdir(parents=True, exist_ok=True)
            auth_dir = reports_dir / 'multimodel_20210123_v8_epsTT_compare'
            auth_dir.mkdir(parents=True, exist_ok=True)

            auth_crps = pd.DataFrame([
                {'model_id': 'exdqlm_multivar_synth_keep', 'mean_crps': 9.0, 'median_crps': 9.0, 'source_type': 'authoritative'},
                {'model_id': 'exdqlm_multivar_synth_drop', 'mean_crps': 9.0, 'median_crps': 9.0, 'source_type': 'authoritative'},
                {'model_id': 'dqlm_multivar_al_synth_keep', 'mean_crps': 9.0, 'median_crps': 9.0, 'source_type': 'authoritative'},
                {'model_id': 'dqlm_multivar_al_synth_drop', 'mean_crps': 9.0, 'median_crps': 9.0, 'source_type': 'authoritative'},
                {'model_id': 'ndlm_main_synth_keep', 'mean_crps': 9.0, 'median_crps': 9.0, 'source_type': 'authoritative'},
                {'model_id': 'ndlm_main_synth_drop', 'mean_crps': 9.0, 'median_crps': 9.0, 'source_type': 'authoritative'},
                {'model_id': 'exdqlm_univar_synth', 'mean_crps': 0.4, 'median_crps': 0.4, 'source_type': 'authoritative'},
                {'model_id': 'dqlm_univar_al_synth', 'mean_crps': 0.5, 'median_crps': 0.5, 'source_type': 'authoritative'},
                {'model_id': 'ndlm_univar_synth_keep', 'mean_crps': 0.6, 'median_crps': 0.6, 'source_type': 'authoritative'},
                {'model_id': 'glofas_ensemble', 'mean_crps': 0.7, 'median_crps': 0.7, 'source_type': 'authoritative'},
                {'model_id': 'nws_nwm_ensemble', 'mean_crps': 0.8, 'median_crps': 0.8, 'source_type': 'authoritative'},
            ])
            auth_health = pd.DataFrame([{'model_id': mid, 'status': 'pass', 'source_type': 'authoritative'} for mid in auth_crps['model_id'] if 'ensemble' not in mid])
            auth_cov = pd.DataFrame([{'model_id': mid, 'model_variant': mid, 'transfer_mode': '', 'source_lane': 'auth', 'source_run': 'auth_run', 'source_type': 'authoritative', 'export_status': 'exported', 'caveat': ''} for mid in auth_crps['model_id'] if mid in {'exdqlm_univar_synth','dqlm_univar_al_synth','ndlm_univar_synth_keep','exdqlm_multivar_synth_keep','exdqlm_multivar_synth_drop','dqlm_multivar_al_synth_keep','dqlm_multivar_al_synth_drop','ndlm_main_synth_keep','ndlm_main_synth_drop'}])
            auth_source = auth_cov.copy()
            auth_fig = pd.DataFrame([{'model_id': mid, 'plot_type': 'posterior', 'path': f'/tmp/{mid}.png', 'source_run': 'auth_run', 'source_lane': 'auth', 'source_type': 'authoritative'} for mid in auth_cov['model_id']])
            auth_crps.to_csv(auth_dir / 'crps_forecast_summary_all_models.csv', index=False)
            auth_health.to_csv(auth_dir / 'crps_input_health_all_models.csv', index=False)
            auth_cov.to_csv(auth_dir / 'model_coverage.csv', index=False)
            auth_source.to_csv(auth_dir / 'source_provenance.csv', index=False)
            auth_fig.to_csv(auth_dir / 'figure_manifest.csv', index=False)

            families = [
                ('exdqlm_multivar_keep', 'exdqlm_multivar_synth_keep', 'keep'),
                ('exdqlm_multivar_drop', 'exdqlm_multivar_synth_drop', 'drop'),
                ('dqlm_multivar_al_keep', 'dqlm_multivar_al_synth_keep', 'keep'),
                ('dqlm_multivar_al_drop', 'dqlm_multivar_al_synth_drop', 'drop'),
                ('ndlm_main_keep', 'ndlm_main_synth_keep', 'keep'),
                ('ndlm_main_drop', 'ndlm_main_synth_drop', 'drop'),
            ]
            plan_rows = []
            for idx, (family_id, model_id, transfer_mode) in enumerate(families, start=1):
                run_id = f'multimodel_20210123_v8_eps30cf1_{family_id}_featurecov_cf1'
                out_root = runs_dir(artifact_root) / run_id / 'post' / 'outputs' / run_id
                (out_root / 'tables').mkdir(parents=True, exist_ok=True)
                pd.DataFrame([{'model_id': model_id, 'mean_crps': float(idx), 'median_crps': float(idx)/10.0}]).to_csv(out_root / 'tables' / 'crps_forecast_summary.csv', index=False)
                pd.DataFrame([{'model_id': model_id, 'status': 'pass'}]).to_csv(out_root / 'tables' / 'crps_input_health.csv', index=False)
                pd.DataFrame([{'model_id': model_id, 'plot_type': 'posterior', 'path': f'/tmp/{run_id}.png'}]).to_csv(out_root / 'figure_manifest.csv', index=False)
                plan_rows.append({
                    'order_index': idx,
                    'cutoff': '20210123',
                    'epsilon': 'eps30cf1',
                    'lane': family_id,
                    'run_id': run_id,
                    'family_id': family_id,
                    'model_id': model_id,
                    'transfer_mode': transfer_mode,
                    'authoritative_compare_dir': str(auth_dir),
                    'selected_source_run': 'source',
                    'selected_c_factor': 1.0,
                    'selected_epsilon': 30.0,
                    'target_c_factor': 1.0,
                    'target_epsilon': 30.0,
                    'reused': False,
                    'reuse_source_run_id': '',
                    'reuse_source_run_root': '',
                })
            pd.DataFrame(plan_rows).to_csv(matrix_dir / 'matrix_plan.csv', index=False)
            outdir = reports_dir / 'multimodel_20210123_v8_eps30cf1_compare'
            build_bundle('20210123', 'eps30cf1', matrix_dir, outdir, artifact_root=artifact_root)
            crps = pd.read_csv(outdir / 'crps_forecast_summary_all_models.csv')
            self.assertEqual(float(crps.loc[crps['model_id'] == 'exdqlm_univar_synth', 'mean_crps'].iloc[0]), 0.4)
            self.assertEqual(float(crps.loc[crps['model_id'] == 'exdqlm_multivar_synth_keep', 'mean_crps'].iloc[0]), 1.0)
            self.assertEqual(
                crps.loc[crps['model_id'] == 'ndlm_main_synth_drop', 'source_type'].iloc[0],
                'featurecov_cf1_eps_sweep',
            )
            src = pd.read_csv(outdir / 'source_provenance.csv')
            self.assertEqual(src.loc[src['model_id'] == 'dqlm_univar_al_synth', 'source_type'].iloc[0], 'authoritative')
            self.assertEqual(src.loc[src['model_id'] == 'dqlm_multivar_al_synth_keep', 'source_type'].iloc[0], 'featurecov_cf1_eps_sweep')
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
