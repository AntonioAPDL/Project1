#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_CONFIG = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_20221225_reducedspec_defaultvb_iter3000_dfall999999_datastart2017_ready_20260520/"
    "control/generated_configs/"
    "multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep.yaml"
)
DEFAULT_RUNTIME_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")


def parse_quantiles(raw: str) -> list[float]:
    out: list[float] = []
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        value = float(piece)
        if value <= 0 or value >= 1:
            raise ValueError(f"quantile must be in (0, 1): {piece}")
        out.append(value)
    if not out:
        raise ValueError("at least one quantile is required")
    return out


def q_tag(q: float) -> str:
    return f"q{int(round(q * 100)):02d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare isolated guarded exDQLM keep reproductions.")
    parser.add_argument("--source-config", type=Path, default=DEFAULT_SOURCE_CONFIG)
    parser.add_argument("--tag", default="guarded_log1p_phase_cd_20260521")
    parser.add_argument("--quantiles", default="0.05,0.35,0.5,0.95")
    parser.add_argument("--max-iter", type=int, default=3000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--report-root", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument("--guard-mode", choices=["warn", "fail"], default="warn")
    parser.add_argument("--fff-abs-cap", type=float, default=1000.0)
    parser.add_argument("--qqq-diag-abs-cap", type=float, default=10000.0)
    parser.add_argument("--e-inv-u-abs-cap", type=float, default=5000.0)
    parser.add_argument(
        "--post-save-objective",
        choices=["on", "off"],
        default="off",
        help="Keep the expensive post-save KL/JSD objective diagnostic enabled or disabled for this isolated repro.",
    )
    args = parser.parse_args()

    quantiles = parse_quantiles(args.quantiles)
    with args.source_config.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)

    run_id = f"{cfg['run']['run_id']}__{args.tag}"
    artifact_root = args.runtime_root / f"exdqlm_keep_{args.tag}"
    run_root = artifact_root / "runs"
    control_root = artifact_root / "control"
    generated_root = control_root / "generated_configs"
    report_root = args.report_root / f"exdqlm_keep_guarded_repro_{args.tag}"
    guard_report_dir = report_root / "pseudodata_guard_events"

    generated_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)
    guard_report_dir.mkdir(parents=True, exist_ok=True)

    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(run_root)
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = True
    cfg["run"]["threads"]["mc_cores"] = int(args.workers)
    cfg["fit"]["quantiles"] = quantiles
    cfg["fit"]["parallel"]["workers"] = int(args.workers)
    cfg["fit"]["exdqlm_multivar"]["gamma_sigma"]["max_iter"] = int(args.max_iter)

    config_path = generated_root / f"{run_id}.yaml"
    with config_path.open("w", encoding="utf-8") as handle:
      yaml.safe_dump(cfg, handle, sort_keys=False)

    launch_path = control_root / f"launch_{run_id}.sh"
    launch_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f'export DISC_PSEUDODATA_GUARD_ENABLED="1"',
        f'export DISC_PSEUDODATA_GUARD_MODE="{args.guard_mode}"',
        f'export DISC_PSEUDODATA_GUARD_REPORT_DIR="{guard_report_dir}"',
        f'export DISC_PSEUDODATA_FFF_ABS_CAP="{args.fff_abs_cap}"',
        f'export DISC_PSEUDODATA_QQQ_DIAG_ABS_CAP="{args.qqq_diag_abs_cap}"',
        f'export DISC_PSEUDODATA_E_INV_U_ABS_CAP="{args.e_inv_u_abs_cap}"',
        f'export DISC_W_POST_SAVE_OBJECTIVE_ENABLED="{1 if args.post_save_objective == "on" else 0}"',
        f'cd "{PROJECT_ROOT}"',
        f'exec "{PROJECT_ROOT / "scripts" / "run_unified_without_cleanup.sh"}" --config "{config_path}"',
    ]
    launch_path.write_text("\n".join(launch_lines) + "\n", encoding="utf-8")
    launch_path.chmod(launch_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

    manifest = {
        "source_config": str(args.source_config),
        "config_path": str(config_path),
        "launch_path": str(launch_path),
        "artifact_root": str(artifact_root),
        "run_root": str(run_root),
        "run_id": run_id,
        "quantiles": quantiles,
        "quantile_tags": [q_tag(q) for q in quantiles],
        "max_iter": int(args.max_iter),
        "workers": int(args.workers),
        "guard_report_dir": str(guard_report_dir),
        "guard_mode": args.guard_mode,
        "post_save_objective": args.post_save_objective,
        "caps": {
            "fff_abs_cap": args.fff_abs_cap,
            "qqq_diag_abs_cap": args.qqq_diag_abs_cap,
            "e_inv_u_abs_cap": args.e_inv_u_abs_cap,
        },
    }
    (report_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (report_root / "README.md").write_text(
        "\n".join(
            [
                "# exDQLM keep guarded reproduction",
                "",
                "Generated by `repro/audits/prepare_exdqlm_keep_guarded_repro.py`.",
                "",
                f"- source config: `{args.source_config}`",
                f"- generated config: `{config_path}`",
                f"- launch script: `{launch_path}`",
                f"- run id: `{run_id}`",
                f"- quantiles: `{', '.join(q_tag(q) for q in quantiles)}`",
                f"- max_iter: `{args.max_iter}`",
                f"- guard mode: `{args.guard_mode}`",
                f"- post-save objective: `{args.post_save_objective}`",
                f"- guard report dir: `{guard_report_dir}`",
                "",
                "This reproduction is isolated from existing production roots.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
