#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_discount_screen_20260628")
DEFAULT_MATRIX_DIR = DEFAULT_ARTIFACT_ROOT / "control/univar_discount_screen"
PROGRESS_RE = re.compile(
    r"family=exdqlm_univar\s+p0=(?P<q>[0-9.]+)\s+iter=(?P<iter>\d+)\s+elbo=(?P<elbo>[^\s]+).*?"
    r"sigma_exp=(?P<sigma>[^\s]+).*?gamma_exp=(?P<gamma>[^\s]+).*?state_norm_sq=(?P<state>[^\s]+)"
)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def stage_status(manifest_path: Path) -> tuple[str, str]:
    if not manifest_path.exists():
        return "not_started", "not_started"
    manifest = load_yaml(manifest_path)
    stages = manifest.get("stages", {}) if isinstance(manifest, dict) else {}
    for stage in ["data_prep_shared", "fit", "post", "validate", "report"]:
        entry = stages.get(stage, {}) if isinstance(stages, dict) else {}
        status = str(entry.get("status", "")).strip().lower() if isinstance(entry, dict) else ""
        if status in {"pending", "fail"}:
            return stage, status
    report_status = str(((stages.get("report") or {}).get("status", ""))).strip().lower() if isinstance(stages, dict) else ""
    return ("report", "pass") if report_status == "pass" else ("unknown", report_status or "unknown")


def as_float(raw: Any) -> float | None:
    try:
        value = float(str(raw))
    except Exception:
        return None
    return value if value == value else None


def latest_progress(run_dir: Path) -> dict[str, Any]:
    best: dict[str, Any] = {"iter": "", "elbo": "", "sigma": "", "gamma": "", "state_norm_sq": ""}
    logs = sorted((run_dir / "fit/exdqlm_univar").glob("q=*/logs/univar_theory_summary.log"))
    max_iter = -1
    rows = []
    for log in logs:
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        matches = list(PROGRESS_RE.finditer(text))
        if not matches:
            continue
        m = matches[-1]
        item = {
            "q": m.group("q"),
            "iter": int(m.group("iter")),
            "elbo": m.group("elbo"),
            "sigma": m.group("sigma"),
            "gamma": m.group("gamma"),
            "state_norm_sq": m.group("state"),
        }
        rows.append(item)
        if item["iter"] > max_iter:
            max_iter = item["iter"]
            best = item
    if rows:
        best["quantile_logs"] = len(rows)
        best["iter_min"] = min(row["iter"] for row in rows)
        best["iter_max"] = max(row["iter"] for row in rows)
    return best


def crps_from_run(run_dir: Path) -> float | None:
    candidates = list((run_dir / "post/outputs").glob("*/tables/crps_forecast_summary.csv"))
    candidates += list((run_dir / "post/outputs").glob("*/crps_forecast_summary.csv"))
    for path in candidates:
        try:
            rows = list(csv.DictReader(path.open("r", encoding="utf-8")))
        except Exception:
            continue
        for row in rows:
            model_id = " ".join(str(v) for v in row.values())
            if "exdqlm_univar" not in model_id and "exdqlm_univar_synth" not in model_id:
                continue
            for key in ["mean_crps", "crps", "crps_mean"]:
                if key in row:
                    value = as_float(row[key])
                    if value is not None:
                        return value
    return None


def baseline_crps() -> dict[str, float]:
    path = ROOT / "reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv"
    out: dict[str, float] = {}
    if not path.exists():
        return out
    for row in csv.DictReader(path.open("r", encoding="utf-8")):
        if row.get("family") == "exdqlm_univar":
            value = as_float(row.get("crps_exact"))
            if value is not None:
                out[str(row["cutoff"])] = value
    return out


def summarize(matrix_dir: Path, artifact_root: Path) -> pd.DataFrame:
    plan = pd.read_csv(matrix_dir / "matrix_plan.csv", dtype=str, keep_default_na=False)
    base = baseline_crps()
    rows: list[dict[str, Any]] = []
    for _, row in plan.iterrows():
        run_id = str(row["run_id"])
        run_dir = artifact_root / "runs" / run_id
        phase, status = stage_status(run_dir / "run_manifest.yaml")
        prog = latest_progress(run_dir)
        crps = crps_from_run(run_dir)
        b = base.get(str(row["cutoff"]))
        rows.append({
            "cutoff": row["cutoff"],
            "spec": row["spec_short_label"],
            "grid_spec_id": row["grid_spec_id"],
            "phase": phase,
            "status": status,
            "iter_min": prog.get("iter_min", ""),
            "iter_max": prog.get("iter_max", prog.get("iter", "")),
            "latest_q": prog.get("q", ""),
            "latest_elbo": prog.get("elbo", ""),
            "latest_sigma": prog.get("sigma", ""),
            "latest_gamma": prog.get("gamma", ""),
            "latest_state_norm_sq": prog.get("state_norm_sq", ""),
            "crps": "" if crps is None else crps,
            "baseline_crps": "" if b is None else b,
            "delta_vs_baseline": "" if crps is None or b is None else crps - b,
            "run_id": run_id,
        })
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize HE2 exDQLM univariate discount screen status and CRPS.")
    parser.add_argument("--matrix-dir", type=Path, default=DEFAULT_MATRIX_DIR)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "reports/he2_exdqlm_univar_discount_screen_20260628")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    df = summarize(args.matrix_dir.resolve(), args.artifact_root.resolve())
    out_csv = out_dir / "status_summary.csv"
    df.to_csv(out_csv, index=False)
    counts = df.groupby(["phase", "status"]).size().reset_index(name="n").to_dict(orient="records")
    payload = {
        "matrix_dir": str(args.matrix_dir.resolve()),
        "artifact_root": str(args.artifact_root.resolve()),
        "rows": int(len(df)),
        "counts": counts,
        "status_csv": str(out_csv),
    }
    (out_dir / "status_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(df.loc[:, ["cutoff", "spec", "phase", "status", "iter_min", "iter_max", "crps", "delta_vs_baseline"]].to_string(index=False))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
