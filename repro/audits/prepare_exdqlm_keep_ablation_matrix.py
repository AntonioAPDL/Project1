#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import stat
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREPARE_ONE = PROJECT_ROOT / "repro" / "audits" / "prepare_exdqlm_keep_guarded_repro.py"
DEFAULT_RUNTIME_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")
DEFAULT_SOURCE_CONFIG = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_20221225_reducedspec_defaultvb_iter3000_dfall999999_datastart2017_ready_20260520/"
    "control/generated_configs/"
    "multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep.yaml"
)
DEFAULT_CONDITIONS = "fixed-gamsig,latent-freeze,latent-cap-e-inv-u"


def parse_conditions(raw: str) -> list[str]:
    allowed = {"control", "fixed-gamsig", "latent-freeze", "latent-cap-e-inv-u", "fixed-gamsig-latent-cap"}
    out: list[str] = []
    for piece in raw.split(","):
        condition = piece.strip()
        if not condition:
            continue
        if condition not in allowed:
            raise ValueError(f"unsupported condition {condition!r}; allowed={sorted(allowed)}")
        out.append(condition)
    if not out:
        raise ValueError("at least one ablation condition is required")
    return out


def slug(value: str) -> str:
    return value.replace("-", "_").replace(".", "p")


def run_prepare(args: argparse.Namespace, condition: str) -> dict[str, object]:
    condition_tag = f"{args.tag}_{slug(condition)}"
    cmd = [
        "python3",
        str(PREPARE_ONE),
        "--source-config",
        str(args.source_config),
        "--tag",
        condition_tag,
        "--quantiles",
        args.quantiles,
        "--max-iter",
        str(args.max_iter),
        "--workers",
        str(args.workers),
        "--runtime-root",
        str(args.runtime_root),
        "--report-root",
        str(args.report_root),
        "--guard-mode",
        args.guard_mode,
        "--fff-abs-cap",
        str(args.fff_abs_cap),
        "--qqq-diag-abs-cap",
        str(args.qqq_diag_abs_cap),
        "--e-inv-u-abs-cap",
        str(args.e_inv_u_abs_cap),
        "--ablation-mode",
        condition,
        "--latent-e-inv-u-cap",
        str(args.latent_e_inv_u_cap),
        "--post-save-objective",
        args.post_save_objective,
    ]
    result = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE)
    manifest = json.loads(result.stdout)
    manifest["condition"] = condition
    manifest["condition_tag"] = condition_tag
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare an isolated exDQLM keep ablation matrix.")
    parser.add_argument("--source-config", type=Path, default=DEFAULT_SOURCE_CONFIG)
    parser.add_argument("--tag", default="ablation_log1p_q05_q35_q50_q95_20260521")
    parser.add_argument("--conditions", default=DEFAULT_CONDITIONS)
    parser.add_argument("--quantiles", default="0.05,0.35,0.5,0.95")
    parser.add_argument("--max-iter", type=int, default=3000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--report-root", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument("--guard-mode", choices=["warn", "fail"], default="warn")
    parser.add_argument("--fff-abs-cap", type=float, default=1000.0)
    parser.add_argument("--qqq-diag-abs-cap", type=float, default=10000.0)
    parser.add_argument("--e-inv-u-abs-cap", type=float, default=5000.0)
    parser.add_argument("--latent-e-inv-u-cap", type=float, default=5000.0)
    parser.add_argument("--post-save-objective", choices=["on", "off"], default="off")
    args = parser.parse_args()

    conditions = parse_conditions(args.conditions)
    matrix_report_dir = args.report_root / f"exdqlm_keep_ablation_matrix_{args.tag}"
    matrix_report_dir.mkdir(parents=True, exist_ok=True)

    manifests = [run_prepare(args, condition) for condition in conditions]
    matrix_manifest = {
        "tag": args.tag,
        "source_config": str(args.source_config),
        "conditions": conditions,
        "quantiles": args.quantiles,
        "max_iter": int(args.max_iter),
        "workers": int(args.workers),
        "guard_mode": args.guard_mode,
        "post_save_objective": args.post_save_objective,
        "matrix_report_dir": str(matrix_report_dir),
        "runs": manifests,
    }
    manifest_path = matrix_report_dir / "matrix_manifest.json"
    manifest_path.write_text(json.dumps(matrix_manifest, indent=2) + "\n", encoding="utf-8")

    launch_path = matrix_report_dir / f"launch_ablation_matrix_{args.tag}.sh"
    launch_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f'cd "{PROJECT_ROOT}"',
    ]
    for manifest in manifests:
        launch_lines.extend(
            [
                f'echo "== Running ablation condition: {manifest["condition"]} =="',
                f'bash "{manifest["launch_path"]}"',
            ]
        )
    launch_path.write_text("\n".join(launch_lines) + "\n", encoding="utf-8")
    launch_path.chmod(launch_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

    readme_lines = [
        "# exDQLM keep ablation matrix",
        "",
        "Generated by `repro/audits/prepare_exdqlm_keep_ablation_matrix.py`.",
        "",
        f"- tag: `{args.tag}`",
        f"- source config: `{args.source_config}`",
        f"- conditions: `{', '.join(conditions)}`",
        f"- quantiles: `{args.quantiles}`",
        f"- max_iter: `{args.max_iter}`",
        f"- workers: `{args.workers}`",
        f"- guard mode: `{args.guard_mode}`",
        f"- post-save objective: `{args.post_save_objective}`",
        f"- master launch script: `{launch_path}`",
        "",
        "Each condition is isolated in its own run root and report root.",
        "",
        "| condition | launch script | report root |",
        "| --- | --- | --- |",
    ]
    for manifest in manifests:
        readme_lines.append(
            f"| {manifest['condition']} | `{manifest['launch_path']}` | `{Path(manifest['guard_report_dir']).parent}` |"
        )
    (matrix_report_dir / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    matrix_manifest["launch_path"] = str(launch_path)
    print(json.dumps(matrix_manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
