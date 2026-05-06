#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CFG = REPO_ROOT / "config" / "unified_runs_exalm_t1_postreplay_20260505" / "paper_exalm_t1_fullfit_20221225_20260505.yaml"
OUT_DIR = REPO_ROOT / "config" / "unified_runs_exalm_t1_r440_20260506"
OUT_CFG = OUT_DIR / "paper_exalm_t1_r440_q20_keep_20221225_20260506.yaml"


def main() -> None:
    with SOURCE_CFG.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)

    cfg["run"]["run_id"] = "paper_exalm_t1_r440_q20_keep_20221225_20260506"
    cfg["run"]["run_root"] = str(REPO_ROOT / "repro" / "runs")
    cfg["run"]["overwrite"] = True

    cfg["stages"] = {
        "forecats": False,
        "data_prep_shared": True,
        "fit": True,
        "post": False,
        "validate": False,
        "report": False,
    }

    cfg["models"]["run_exdqlm_multivar"] = True
    cfg["models"]["run_exdqlm_univar"] = False
    cfg["models"]["run_ndlm_main"] = False
    cfg["models"]["run_ndlm_univar"] = False
    cfg["models"]["exdqlm_multivar"]["forecast_transfer_mode"] = "keep"
    cfg["models"]["exdqlm_multivar"]["forecast_transfer_modes"] = ["keep"]

    cfg["fit"]["quantiles"] = [0.2]
    cfg["fit"]["parallel"]["mode"] = "one_core_per_model"
    cfg["fit"]["parallel"]["workers"] = 1

    cfg["inputs"]["post"]["use_fit_outputs_from_run"] = False

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CFG.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(cfg, handle, sort_keys=False)

    print(OUT_CFG)


if __name__ == "__main__":
    main()
