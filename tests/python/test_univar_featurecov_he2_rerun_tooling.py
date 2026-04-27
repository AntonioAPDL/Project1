from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_template_queue_and_family_contract() -> None:
    template_path = ROOT / "config" / "multimodel_v8_univar_featurecov_he2_rerun_20260422.template.yaml"
    with template_path.open("r", encoding="utf-8") as handle:
        template = yaml.safe_load(handle) or {}

    queue = template["queue"]
    assert int(queue["ordinary_max_concurrent"]) == 4
    assert int(queue["heavy_cutoff_max_concurrent"]) == 4
    assert queue["heavy_cutoff_blocks_ordinary"] is False

    families = template["families"]
    assert set(families) == {"exdqlm_univar", "dqlm_univar_al"}
    assert all(int(families[family]["fit_parallel_workers"]) == 7 for family in families)


def test_builder_generates_two_proper_spec_univar_rows_for_single_cutoff() -> None:
    template_path = ROOT / "config" / "multimodel_v8_univar_featurecov_he2_rerun_20260422.template.yaml"
    with template_path.open("r", encoding="utf-8") as handle:
        template = yaml.safe_load(handle) or {}

    with tempfile.TemporaryDirectory(prefix="univar_featurecov_he2_builder_") as td:
        tmp = Path(td)
        artifact_root = tmp / "artifact"
        matrix_dir = artifact_root / "control" / "univar_featurecov_he2_v1"
        config_output_dir = tmp / "generated_configs"
        template["campaign"]["artifact_root"] = str(artifact_root)
        template["campaign"]["matrix_dir"] = str(matrix_dir)
        template["campaign"]["config_output_dir"] = str(config_output_dir)
        tmp_config = tmp / "template.yaml"
        tmp_config.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")

        proc = subprocess.run(
            [
                "python3",
                "scripts/build_multimodel_v8_all9_feature_matrix_configs.py",
                "--config",
                str(tmp_config),
                "--cutoffs",
                "20210123",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr

        configs = sorted(config_output_dir.glob("*.yaml"))
        assert len(configs) == 2
        for path in configs:
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
            assert payload["models"]["run_exdqlm_univar"] is True
            assert payload["models"]["run_exdqlm_multivar"] is False
            assert payload["models"]["run_ndlm_main"] is False
            assert payload["models"]["run_ndlm_univar"] is False
            cov_names = [row["name"] for row in payload["inputs"]["fit"]["covariates"]]
            assert cov_names == ["PPT", "SOIL", "PCA"]
            assert payload["inputs"]["deterministic_climate"]["enabled"] is True
            assert payload["inputs"]["covariate_features"]["enabled"] is True
            assert payload["inputs"]["shared"]["prefer_forecats_snapshot"] is False
            assert int(payload["run"]["threads"]["mc_cores"]) == 7
            assert int(payload["fit"]["parallel"]["workers"]) == 7
