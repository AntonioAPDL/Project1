#!/usr/bin/env python3
"""Generate strict unified rerun configs for (cutoff x epsilon-suffix) matrix.

This builder enforces:
- forecats mode = use_existing (no build fallback)
- fixed cutoff->bundle mapping (policy-vetted)
- 22 workers per cutoff with global_models parallel mode
- fixed model hyperparameters (discount factors + Wishart knobs)
- epsilon per suffix: base(TT/null), _v2=30, _v3=90
"""

from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]

BASE_RUNS: List[Tuple[str, str]] = [
    ("multimodel_20210123", "2021-01-23"),
    ("multimodel_20211112", "2021-11-12"),
    ("multimodel_20211221", "2021-12-21"),
    ("multimodel_20220511", "2022-05-11"),
    ("multimodel_20221225", "2022-12-25"),
]

DEFAULT_SUFFIX_TO_EPSILON: Dict[str, float | None] = {
    "": None,
    "_v2": 30.0,
    "_v3": 90.0,
}

BUNDLE_BY_CUTOFF: Dict[str, str] = {
    "2021-01-23": "/data/muscat_data/jaguir26/project1_ucsc_phd/data/forecats_inputs/site=11160500/cutoff_date=2021-01-23/run_id=20260305_single_retro_policy_pre1080_gapfix_r01/meta.yaml",
    "2021-11-12": "/data/muscat_data/jaguir26/project1_ucsc_phd/data/forecats_inputs/site=11160500/cutoff_date=2021-11-12/run_id=20260219_single_retro_policy_pre1080_r01/meta.yaml",
    "2021-12-21": "/data/muscat_data/jaguir26/project1_ucsc_phd/data/forecats_inputs/site=11160500/cutoff_date=2021-12-21/run_id=20260219_single_retro_policy_pre1080_r01/meta.yaml",
    "2022-05-11": "/data/muscat_data/jaguir26/project1_ucsc_phd/data/forecats_inputs/site=11160500/cutoff_date=2022-05-11/run_id=20260219_single_retro_policy_pre1080_r01/meta.yaml",
    "2022-12-25": "/data/muscat_data/jaguir26/project1_ucsc_phd/repro/forecats_inputs_compat/site=11160500/cutoff_date=2022-12-25/run_id=20260220_single_retro_policy_pre20_r01_compat_fullhist2010",
}


def _ensure_dict(parent: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        value = {}
        parent[key] = value
    return value


def _load_base_config(base_run_id: str) -> Dict[str, Any]:
    candidates = [
        ROOT / "repro" / "tmp" / f"{base_run_id}_rerun_full.yaml",
        ROOT / "repro" / "runs" / base_run_id / "resolved_config.yaml",
    ]
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            if isinstance(data, dict):
                return data
    raise FileNotFoundError(
        f"Could not find base config for {base_run_id}; checked: "
        + ", ".join(str(p) for p in candidates)
    )


def _set_model_hyperparams(cfg: Dict[str, Any], epsilon: float | None) -> None:
    models = _ensure_dict(cfg, "models")
    models["run_exdqlm_multivar"] = True
    models["run_exdqlm_univar"] = True
    models["run_ndlm_main"] = True

    exdqlm_multivar = _ensure_dict(models, "exdqlm_multivar")
    exdqlm_multivar["forecast_transfer_mode"] = "drop"
    exdqlm_multivar["forecast_transfer_modes"] = ["drop", "keep"]
    exdqlm_multivar["state_evolution"] = {
        "df_t": 0.99999999,
        "df_s1": 0.9999,
        "df_s2": 0.9999,
        "df_s67": 0.9999,
        "df_discrep": 0.999,
        "lambda": 0.97,
        "df_trans": 0.9999999,
        "df_covs": 0.99999,
    }

    exdqlm_univar = _ensure_dict(models, "exdqlm_univar")
    exdqlm_univar["state_evolution"] = {
        "df_t": 0.99999999,
        "df_s1": 0.9999,
        "df_s2": 0.9999,
        "df_s67": 0.9999,
        "lambda": 0.97,
        "df_trans": 0.9999999,
        "df_covs": 0.99999,
    }

    ndlm_main = _ensure_dict(models, "ndlm_main")
    ndlm_main["state_evolution"] = {
        "df_t": 0.99999999,
        "df_s1": 0.9999,
        "df_s2": 0.9999,
        "df_s67": 0.9999,
        "df_discrep": 0.999,
        "lambda": 0.97,
        "df_trans": 0.9999999,
        "df_covs": 0.9999,
    }

    fit = _ensure_dict(cfg, "fit")
    fit["parallel"] = {"mode": "global_models", "workers": 22}

    multivar_fit = _ensure_dict(fit, "exdqlm_multivar")
    multivar_legacy = _ensure_dict(multivar_fit, "legacy")
    multivar_legacy["lam1"] = 1.0
    multivar_legacy["lam2"] = 1.0
    multivar_legacy["n_samp"] = 2000.0
    multivar_legacy["sims_enabled"] = True
    multivar_legacy["use_covariates"] = True
    forecast_cov = _ensure_dict(multivar_legacy, "forecast_cov")
    forecast_cov["c_factor"] = 1.0
    forecast_cov["epsilon"] = epsilon

    univar_fit = _ensure_dict(fit, "exdqlm_univar")
    univar_legacy = _ensure_dict(univar_fit, "legacy")
    univar_legacy["lam1"] = 1.0
    univar_legacy["lam2"] = 1.0
    univar_legacy["n_samp"] = 2000.0
    univar_legacy["sims_enabled"] = True
    univar_legacy["use_covariates"] = True

    ndlm_fit = _ensure_dict(fit, "ndlm_main")
    ndlm_legacy = _ensure_dict(ndlm_fit, "legacy")
    ndlm_legacy["lam1"] = 1.0
    ndlm_legacy["lam2"] = 1.0
    ndlm_legacy["n_samp"] = 2000.0
    ndlm_legacy["sims_enabled"] = True
    ndlm_legacy["use_covariates"] = True


def _set_forecats_policy(cfg: Dict[str, Any], cutoff_date: str) -> None:
    inputs = _ensure_dict(cfg, "inputs")
    forecats = _ensure_dict(inputs, "forecats")
    shared = _ensure_dict(inputs, "shared")
    post = _ensure_dict(inputs, "post")

    forecats["mode"] = "use_existing"
    forecats["existing_bundle_path"] = BUNDLE_BY_CUTOFF[cutoff_date]
    forecats["pipeline_config_path"] = str((ROOT / "config" / "forecats_pipeline.template.yaml").resolve())

    snapshot = _ensure_dict(forecats, "snapshot")
    snapshot["enabled"] = True
    if not snapshot.get("dest_rel"):
        snapshot["dest_rel"] = "inputs/shared/forecats_bundle"

    shared["prefer_forecats_snapshot"] = True

    post["use_fit_outputs_from_run"] = True
    if not post.get("source_run_root"):
        run = _ensure_dict(cfg, "run")
        post["source_run_root"] = run.get("run_root", str((ROOT / "repro" / "runs").resolve()))


def _set_stage_flags(cfg: Dict[str, Any]) -> None:
    stages = _ensure_dict(cfg, "stages")
    stages["forecats"] = True
    stages["data_prep_shared"] = True
    stages["fit"] = True
    stages["post"] = True
    stages["validate"] = False
    stages["report"] = False


def _write_config(path: Path, cfg: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(cfg, handle, sort_keys=False, default_flow_style=False)


def parse_suffix_to_epsilon(entries: List[str]) -> Dict[str, float | None]:
    if not entries:
        return dict(DEFAULT_SUFFIX_TO_EPSILON)

    parsed: Dict[str, float | None] = {}
    for raw in entries:
        if "=" not in raw:
            raise ValueError(
                f"Invalid --suffix-epsilon entry {raw!r}; expected format <suffix>=<epsilon|null>"
            )
        suffix, eps_raw = raw.split("=", 1)
        suffix = suffix.strip()
        eps_raw = eps_raw.strip().lower()
        if suffix in parsed:
            raise ValueError(f"Duplicate suffix entry: {suffix!r}")
        if eps_raw in {"null", "none", "tt", "~", ""}:
            parsed[suffix] = None
        else:
            parsed[suffix] = float(eps_raw)

    return parsed


def build_configs(
    out_dir: Path,
    verify_bundles: bool,
    suffix_to_epsilon: Dict[str, float | None],
) -> List[Path]:
    generated: List[Path] = []

    for base_run_id, cutoff_date in BASE_RUNS:
        base_cfg = _load_base_config(base_run_id)

        dates = _ensure_dict(base_cfg, "dates")
        cfg_cutoff = str(dates.get("cutoff_date", ""))
        if cfg_cutoff != cutoff_date:
            raise ValueError(
                f"Base config cutoff mismatch for {base_run_id}: expected {cutoff_date}, got {cfg_cutoff!r}"
            )

        bundle_path = Path(BUNDLE_BY_CUTOFF[cutoff_date])
        if verify_bundles and not bundle_path.exists():
            raise FileNotFoundError(f"Bundle path missing for cutoff {cutoff_date}: {bundle_path}")

        for suffix, epsilon in suffix_to_epsilon.items():
            run_id = f"{base_run_id}{suffix}"
            out_path = out_dir / f"{run_id}_rerun_full.yaml"
            cfg = copy.deepcopy(base_cfg)

            run = _ensure_dict(cfg, "run")
            run["run_id"] = run_id
            run["overwrite"] = True
            run["auto_suffix_on_collision"] = False
            run["dry_run"] = False
            run_root = str(run.get("run_root", str((ROOT / "repro" / "runs").resolve())))
            run["resolved_run_root"] = os.path.join(run_root, run_id)
            run["resolved_config_path"] = str(out_path.resolve())

            _set_stage_flags(cfg)
            _set_forecats_policy(cfg, cutoff_date)
            _set_model_hyperparams(cfg, epsilon)

            cfg["debug_relaunch_matrix"] = {
                "source_base_run_id": base_run_id,
                "cutoff_date": cutoff_date,
                "suffix": suffix,
                "wishart_epsilon": epsilon,
                "bundle_path": BUNDLE_BY_CUTOFF[cutoff_date],
            }

            _write_config(out_path, cfg)
            generated.append(out_path)

    return generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        default=str((ROOT / "repro" / "tmp").resolve()),
        help="Directory for generated *_rerun_full.yaml files",
    )
    parser.add_argument(
        "--no-verify-bundles",
        action="store_true",
        help="Skip existence checks for mapped existing_bundle_path targets",
    )
    parser.add_argument(
        "--suffix-epsilon",
        action="append",
        default=[],
        help=(
            "Suffix/epsilon mapping in format <suffix>=<epsilon|null>. "
            "Repeat flag for multiple entries. "
            "Example: --suffix-epsilon '=null' --suffix-epsilon '_v2=30' --suffix-epsilon '_v3=90'"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir).resolve()
    suffix_to_epsilon = parse_suffix_to_epsilon(args.suffix_epsilon)
    generated = build_configs(
        out_dir=out_dir,
        verify_bundles=not args.no_verify_bundles,
        suffix_to_epsilon=suffix_to_epsilon,
    )

    print(f"Generated {len(generated)} configs under {out_dir}")
    for path in sorted(generated):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
