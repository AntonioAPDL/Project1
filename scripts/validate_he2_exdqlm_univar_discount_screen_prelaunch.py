#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_discount_screen_20260628")
DEFAULT_MATRIX_DIR = DEFAULT_ARTIFACT_ROOT / "control/univar_discount_screen"
EXPECTED_CUTOFFS = {"20210123", "20211112", "20211221", "20220511", "20221225"}
EXPECTED_SPEC_SHORTS = {"u01", "u02", "u03", "u04", "u05"}
EXPECTED_QUANTILES = "05|20|35|50|65|80|95"
STATE_FIELDS = ["df_t", "df_s1", "df_s2", "df_s67", "lambda", "df_trans", "df_covs"]


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def check(self, scope: str, check: str, passed: bool, detail: Any = "") -> None:
        self.rows.append({"scope": scope, "check": check, "status": "pass" if passed else "fail", "detail": str(detail)})
        if not passed:
            raise AssertionError(f"{scope}:{check}: {detail}")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def nested(obj: dict[str, Any], path: list[str], default: Any = None) -> Any:
    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def same_float(a: Any, b: Any, tol: float = 1e-12) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def count_rdata(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".rdata", ".rda", ".rds"})


def validate(matrix_dir: Path, artifact_root: Path, *, allow_existing_runs: bool = False) -> tuple[Recorder, dict[str, Any]]:
    rec = Recorder()
    metadata_path = matrix_dir / "matrix_metadata.yaml"
    plan_path = matrix_dir / "matrix_plan.csv"
    specs_path = matrix_dir / "grid_spec_manifest_resolved.csv"
    registry_path = matrix_dir / "grid_run_registry.csv"
    frozen_path = matrix_dir / "frozen_spec_manifest.csv"
    launch_script = matrix_dir / "launch_univar_discount_screen.sh"
    for path in [metadata_path, plan_path, specs_path, registry_path, frozen_path, launch_script]:
        rec.check("matrix", f"exists:{path.name}", path.exists(), path)

    metadata = load_yaml(metadata_path)
    plan = read_csv(plan_path)
    specs = read_csv(specs_path)
    registry = read_csv(registry_path)
    frozen = read_csv(frozen_path)

    rec.check("matrix", "run_rows_25", len(plan) == 25, len(plan))
    rec.check("matrix", "spec_rows_5", len(specs) == 5, len(specs))
    rec.check("matrix", "registry_rows_match_plan", len(registry) == len(plan), f"registry={len(registry)} plan={len(plan)}")
    rec.check("matrix", "frozen_rows_match_plan", len(frozen) == len(plan), f"frozen={len(frozen)} plan={len(plan)}")
    rec.check("matrix", "cutoffs", set(plan["cutoff"].astype(str)) == EXPECTED_CUTOFFS, sorted(plan["cutoff"].unique()))
    rec.check("matrix", "spec_short_labels", set(plan["spec_short_label"].astype(str)) == EXPECTED_SPEC_SHORTS, sorted(plan["spec_short_label"].unique()))
    rec.check("matrix", "run_ids_unique", plan["run_id"].is_unique, "")
    rec.check("matrix", "one_family", set(plan["family"].astype(str)) == {"exdqlm_univar"}, sorted(plan["family"].unique()))
    rec.check("matrix", "active_quantiles", set(plan["active_quantiles"].astype(str)) == {EXPECTED_QUANTILES}, sorted(plan["active_quantiles"].unique()))
    rec.check("matrix", "cleanup_enabled", set(plan["cleanup_rdata_after_post"].astype(str).str.lower()) == {"true"}, "")
    rec.check("queue", "ordinary_max_concurrent_4", int(metadata["queue"]["ordinary_max_concurrent"]) == 4, metadata["queue"])
    rec.check("queue", "skip_compares", bool(metadata.get("skip_compare_bundles")) is True, metadata.get("skip_compare_bundles"))
    rec.check("queue", "allow_run_failures", bool(metadata.get("allow_run_failures")) is True, metadata.get("allow_run_failures"))
    rec.check("cleanup", "metadata_cleanup_after_post", bool(metadata.get("cleanup_rdata_after_post")) is True, metadata.get("cleanup_rdata_after_post"))
    rec.check("cleanup", "launch_script_uses_cleanup", "--no-cleanup" not in launch_script.read_text(encoding="utf-8"), launch_script)
    rec.check("cleanup", "no_existing_rdata", count_rdata(artifact_root) == 0, artifact_root)

    spec_map = {row["spec_short_label"]: row for _, row in specs.iterrows()}
    for _, row in plan.iterrows():
        cfg_path = Path(str(row["config_path"]))
        rec.check("config", f"exists:{cfg_path.name}", cfg_path.exists(), cfg_path)
        cfg = load_yaml(cfg_path)
        spec = spec_map[str(row["spec_short_label"])]
        rec.check("config", f"{cfg_path.name}:run_id", nested(cfg, ["run", "run_id"]) == row["run_id"], nested(cfg, ["run", "run_id"]))
        rec.check("config", f"{cfg_path.name}:run_root", str(nested(cfg, ["run", "run_root"], "")).startswith(str(artifact_root / "runs")), nested(cfg, ["run", "run_root"]))
        rec.check("config", f"{cfg_path.name}:data_start", nested(cfg, ["dates", "data_start"]) == "1987-05-29", nested(cfg, ["dates", "data_start"]))
        rec.check("config", f"{cfg_path.name}:family_enabled", nested(cfg, ["models", "run_exdqlm_univar"]) is True, nested(cfg, ["models", "run_exdqlm_univar"]))
        rec.check("config", f"{cfg_path.name}:multivar_disabled", nested(cfg, ["models", "run_exdqlm_multivar"]) is False, nested(cfg, ["models", "run_exdqlm_multivar"]))
        rec.check("config", f"{cfg_path.name}:likelihood", nested(cfg, ["models", "exdqlm_univar", "likelihood_mode"]) == "exal", nested(cfg, ["models", "exdqlm_univar", "likelihood_mode"]))
        rec.check("config", f"{cfg_path.name}:implementation", nested(cfg, ["models", "exdqlm_univar", "implementation_mode"]) == "legacy_bridge", nested(cfg, ["models", "exdqlm_univar", "implementation_mode"]))
        state = nested(cfg, ["models", "exdqlm_univar", "state_evolution"], {})
        rec.check("config", f"{cfg_path.name}:no_df_discrep", "df_discrep" not in state, state)
        for field in STATE_FIELDS:
            rec.check("config", f"{cfg_path.name}:state_{field}", same_float(state.get(field), spec[field]), f"cfg={state.get(field)} spec={spec[field]}")
        rec.check("config", f"{cfg_path.name}:workers7", int(nested(cfg, ["fit", "parallel", "workers"], 0)) == 7, nested(cfg, ["fit", "parallel", "workers"]))
        rec.check("config", f"{cfg_path.name}:mc_cores7", int(nested(cfg, ["run", "threads", "mc_cores"], 0)) == 7, nested(cfg, ["run", "threads", "mc_cores"]))
        rec.check("config", f"{cfg_path.name}:omp1", int(nested(cfg, ["run", "threads", "omp"], 0)) == 1, nested(cfg, ["run", "threads", "omp"]))
        rec.check("config", f"{cfg_path.name}:max_iter100", int(nested(cfg, ["fit", "exdqlm_univar", "gamma_sigma", "max_iter"], 0)) == 100, nested(cfg, ["fit", "exdqlm_univar", "gamma_sigma", "max_iter"]))
        rec.check("config", f"{cfg_path.name}:quantile_count7", len(nested(cfg, ["fit", "quantiles"], [])) == 7, nested(cfg, ["fit", "quantiles"]))
        rec.check("config", f"{cfg_path.name}:no_forecast_cov", nested(cfg, ["fit", "exdqlm_univar", "legacy", "forecast_cov"], None) is None, "")
        rec.check("config", f"{cfg_path.name}:shared_bundle", "multimodel_v8_he2_publication_shared_inputs_20260510" in str(nested(cfg, ["inputs", "forecats", "existing_bundle_path"], "")), nested(cfg, ["inputs", "forecats", "existing_bundle_path"]))
        if not allow_existing_runs:
            run_dir = artifact_root / "runs" / str(row["run_id"])
            rec.check("runtime", f"{row['run_id']}:not_started", not run_dir.exists(), run_dir)

    summary = {
        "matrix_dir": str(matrix_dir),
        "artifact_root": str(artifact_root),
        "run_rows": int(len(plan)),
        "spec_rows": int(len(specs)),
        "checks": len(rec.rows),
        "status": "pass",
    }
    return rec, summary


def write_outputs(matrix_dir: Path, rec: Recorder, summary: dict[str, Any]) -> None:
    pd.DataFrame(rec.rows).to_csv(matrix_dir / "prelaunch_validation_checks.csv", index=False)
    (matrix_dir / "prelaunch_validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# HE2 exDQLM Univariate Discount Screen Prelaunch Validation",
        "",
        f"- status: `{summary['status']}`",
        f"- matrix_dir: `{summary['matrix_dir']}`",
        f"- artifact_root: `{summary['artifact_root']}`",
        f"- run rows: `{summary['run_rows']}`",
        f"- spec rows: `{summary['spec_rows']}`",
        f"- checks: `{summary['checks']}`",
    ]
    (matrix_dir / "PRELAUNCH_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate HE2 exDQLM univariate discount screen before launch.")
    parser.add_argument("--matrix-dir", type=Path, default=DEFAULT_MATRIX_DIR)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--allow-existing-runs", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rec, summary = validate(args.matrix_dir.resolve(), args.artifact_root.resolve(), allow_existing_runs=args.allow_existing_runs)
    write_outputs(args.matrix_dir.resolve(), rec, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
