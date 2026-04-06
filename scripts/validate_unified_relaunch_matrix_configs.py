#!/usr/bin/env python3
"""Validate rerun-full configs for strict no-legacy relaunch policy."""

from __future__ import annotations

import argparse
import glob
import math
import sys
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

EXPECTED_CUTOFF_BY_BASE = {base: cutoff for base, cutoff in BASE_RUNS}


def _get(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _is_close(a: Any, b: Any, tol: float = 1e-12) -> bool:
    try:
        fa = float(a)
        fb = float(b)
    except Exception:
        return False
    return math.isfinite(fa) and math.isfinite(fb) and abs(fa - fb) <= tol


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


def _expected_suffix(run_id: str, suffix_to_epsilon: Dict[str, float | None]) -> str:
    suffixes = sorted((s for s in suffix_to_epsilon.keys() if s), key=len, reverse=True)
    for suffix in suffixes:
        if run_id.endswith(suffix):
            return suffix
    return "" if "" in suffix_to_epsilon else (suffixes[0] if suffixes else "")


def _expected_base_run(run_id: str, suffix_to_epsilon: Dict[str, float | None]) -> str:
    suffix = _expected_suffix(run_id, suffix_to_epsilon)
    if suffix:
        return run_id[: -len(suffix)]
    return run_id


def validate_config(
    path: Path,
    suffix_to_epsilon: Dict[str, float | None],
    expected_cutoff_by_base: Dict[str, str],
    expected_run_ids: set[str],
) -> List[str]:
    errors: List[str] = []
    with path.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    if not isinstance(cfg, dict):
        return [f"{path}: config root is not a mapping"]

    run_id = str(_get(cfg, "run", "run_id", default=""))
    if run_id not in expected_run_ids:
        errors.append(f"{path}: unexpected run_id={run_id!r}")

    base_run = _expected_base_run(run_id, suffix_to_epsilon)
    suffix = _expected_suffix(run_id, suffix_to_epsilon)
    cutoff_date = str(_get(cfg, "dates", "cutoff_date", default=""))
    expected_cutoff = expected_cutoff_by_base.get(base_run)
    if expected_cutoff != cutoff_date:
        errors.append(
            f"{path}: cutoff mismatch for {run_id}; expected {expected_cutoff}, got {cutoff_date!r}"
        )

    fore_mode = str(_get(cfg, "inputs", "forecats", "mode", default=""))
    if fore_mode != "use_existing":
        errors.append(f"{path}: inputs.forecats.mode must be 'use_existing' (got {fore_mode!r})")

    bundle_path = str(_get(cfg, "inputs", "forecats", "existing_bundle_path", default=""))
    expected_bundle = BUNDLE_BY_CUTOFF.get(cutoff_date)
    if expected_bundle is None:
        errors.append(f"{path}: no bundle mapping for cutoff {cutoff_date!r}")
    else:
        if bundle_path != expected_bundle:
            errors.append(
                f"{path}: existing_bundle_path mismatch; expected {expected_bundle!r}, got {bundle_path!r}"
            )
        if not Path(bundle_path).exists():
            errors.append(f"{path}: existing_bundle_path does not exist: {bundle_path}")

    par_mode = str(_get(cfg, "fit", "parallel", "mode", default=""))
    workers = _get(cfg, "fit", "parallel", "workers", default=None)
    if par_mode != "global_models":
        errors.append(f"{path}: fit.parallel.mode must be 'global_models' (got {par_mode!r})")
    if workers != 22:
        errors.append(f"{path}: fit.parallel.workers must be 22 (got {workers!r})")

    exm = _get(cfg, "models", "exdqlm_multivar", "state_evolution", default={}) or {}
    exu = _get(cfg, "models", "exdqlm_univar", "state_evolution", default={}) or {}
    ndl = _get(cfg, "models", "ndlm_main", "state_evolution", default={}) or {}

    expected_multivar = {
        "df_t": 0.99999999,
        "df_s1": 0.9999,
        "df_s2": 0.9999,
        "df_s67": 0.9999,
        "df_discrep": 0.999,
        "lambda": 0.97,
        "df_trans": 0.9999999,
        "df_covs": 0.99999,
    }
    expected_univar = {
        "df_t": 0.99999999,
        "df_s1": 0.9999,
        "df_s2": 0.9999,
        "df_s67": 0.9999,
        "lambda": 0.97,
        "df_trans": 0.9999999,
        "df_covs": 0.99999,
    }
    expected_ndlm = {
        "df_t": 0.99999999,
        "df_s1": 0.9999,
        "df_s2": 0.9999,
        "df_s67": 0.9999,
        "df_discrep": 0.999,
        "lambda": 0.97,
        "df_trans": 0.9999999,
        "df_covs": 0.9999,
    }

    for key, exp in expected_multivar.items():
        if not _is_close(exm.get(key), exp):
            errors.append(f"{path}: models.exdqlm_multivar.state_evolution.{key} expected {exp}, got {exm.get(key)!r}")
    for key, exp in expected_univar.items():
        if not _is_close(exu.get(key), exp):
            errors.append(f"{path}: models.exdqlm_univar.state_evolution.{key} expected {exp}, got {exu.get(key)!r}")
    for key, exp in expected_ndlm.items():
        if not _is_close(ndl.get(key), exp):
            errors.append(f"{path}: models.ndlm_main.state_evolution.{key} expected {exp}, got {ndl.get(key)!r}")

    for fam in ("exdqlm_multivar", "exdqlm_univar", "ndlm_main"):
        legacy = _get(cfg, "fit", fam, "legacy", default={}) or {}
        if not _is_close(legacy.get("lam1"), 1.0):
            errors.append(f"{path}: fit.{fam}.legacy.lam1 expected 1.0, got {legacy.get('lam1')!r}")
        if not _is_close(legacy.get("lam2"), 1.0):
            errors.append(f"{path}: fit.{fam}.legacy.lam2 expected 1.0, got {legacy.get('lam2')!r}")
        if not _is_close(legacy.get("n_samp"), 2000.0):
            errors.append(f"{path}: fit.{fam}.legacy.n_samp expected 2000.0, got {legacy.get('n_samp')!r}")

    c_factor = _get(cfg, "fit", "exdqlm_multivar", "legacy", "forecast_cov", "c_factor", default=None)
    if not _is_close(c_factor, 1.0):
        errors.append(f"{path}: fit.exdqlm_multivar.legacy.forecast_cov.c_factor expected 1.0, got {c_factor!r}")

    epsilon = _get(cfg, "fit", "exdqlm_multivar", "legacy", "forecast_cov", "epsilon", default="__missing__")
    expected_epsilon = suffix_to_epsilon[suffix]
    if expected_epsilon is None:
        if epsilon is not None:
            errors.append(f"{path}: epsilon for TT/base run must be null/None, got {epsilon!r}")
    else:
        if not _is_close(epsilon, expected_epsilon):
            errors.append(f"{path}: epsilon expected {expected_epsilon}, got {epsilon!r}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        default=str((ROOT / "repro" / "tmp").resolve()),
        help="Directory containing *_rerun_full.yaml files",
    )
    parser.add_argument(
        "--glob",
        default="multimodel_*_rerun_full.yaml",
        help="Glob pattern within --config-dir",
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
    config_dir = Path(args.config_dir).resolve()
    suffix_to_epsilon = parse_suffix_to_epsilon(args.suffix_epsilon)
    expected_run_ids = {
        f"{base}{suffix}" for base, _ in BASE_RUNS for suffix in suffix_to_epsilon.keys()
    }

    # Strictly validate only the intended matrix files.
    wanted = sorted(config_dir / f"{rid}_rerun_full.yaml" for rid in expected_run_ids)
    missing = [p for p in wanted if not p.exists()]
    if missing:
        print("Missing expected matrix configs:", file=sys.stderr)
        for p in missing:
            print(f"  - {p}", file=sys.stderr)
        return 2

    errors: List[str] = []
    for path in wanted:
        errors.extend(
            validate_config(
                path=path,
                suffix_to_epsilon=suffix_to_epsilon,
                expected_cutoff_by_base=EXPECTED_CUTOFF_BY_BASE,
                expected_run_ids=expected_run_ids,
            )
        )

    if errors:
        print("Matrix config validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"Matrix config validation PASSED ({len(wanted)} configs)")
    for p in wanted:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
