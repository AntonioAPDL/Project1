#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


DEFAULT_SOURCE_CONFIG_DIR = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/"
    "control/generated_configs"
)
DEFAULT_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "exdqlm_keep_latent_diag_20260529"
)
DEFAULT_TARGETS = [
    {"phase": "A", "cutoff": "20220511", "grid_spec_id": "c02_eps090", "q": 0.20, "state_guard_start_iter": ""},
    {"phase": "A", "cutoff": "20221225", "grid_spec_id": "c03_eps060", "q": 0.20, "state_guard_start_iter": ""},
    {"phase": "B", "cutoff": "20220511", "grid_spec_id": "c02_eps180", "q": 0.20, "state_guard_start_iter": ""},
    {"phase": "B", "cutoff": "20220511", "grid_spec_id": "c02_eps060", "q": 0.20, "state_guard_start_iter": ""},
    {"phase": "B", "cutoff": "20221225", "grid_spec_id": "c03_eps090", "q": 0.20, "state_guard_start_iter": ""},
    {"phase": "B", "cutoff": "20221225", "grid_spec_id": "c03_eps030", "q": 0.20, "state_guard_start_iter": ""},
    {"phase": "B", "cutoff": "20211112", "grid_spec_id": "c02_eps090", "q": 0.20, "state_guard_start_iter": ""},
    {"phase": "B", "cutoff": "20211112", "grid_spec_id": "c03_eps060", "q": 0.20, "state_guard_start_iter": ""},
    {"phase": "C", "cutoff": "20220511", "grid_spec_id": "c02_eps090", "q": 0.20, "state_guard_start_iter": 20},
    {"phase": "C", "cutoff": "20221225", "grid_spec_id": "c03_eps060", "q": 0.20, "state_guard_start_iter": 20},
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Prepare isolated targeted latent diagnostic configs for exDQLM multivar keep q-lanes."
    )
    ap.add_argument("--source-config-dir", default=str(DEFAULT_SOURCE_CONFIG_DIR))
    ap.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    ap.add_argument("--targets-csv", help="CSV with cutoff, grid_spec_id, q, and optional phase/state_guard_start_iter.")
    ap.add_argument("--write-default-targets", action="store_true", help="Write the built-in A/B/C target CSV then exit.")
    ap.add_argument("--diagnostic-top-k", type=int, default=20)
    ap.add_argument("--latent-mode", default="cap_e_inv_u")
    ap.add_argument("--e-inv-u-cap", type=float, default=5000.0)
    ap.add_argument("--e-u-cap", type=float, default=1e6)
    ap.add_argument("--pseudodata-guard-mode", choices=["warn", "fail"], default="fail")
    ap.add_argument("--max-iter", type=int, default=None, help="Optional max_iter override for diagnostic runs.")
    ap.add_argument("--cleanup-rdata-after-post", action="store_true", default=True)
    ap.add_argument("--no-cleanup-rdata-after-post", dest="cleanup_rdata_after_post", action="store_false")
    return ap.parse_args()


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def q_label(q: float) -> str:
    return f"q{int(round(float(q) * 100)):02d}"


def safe_token(value: Any) -> str:
    out = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value))
    return out.strip("_") or "target"


def load_targets(args: argparse.Namespace, out_dir: Path) -> pd.DataFrame:
    if args.write_default_targets:
        df = pd.DataFrame(DEFAULT_TARGETS)
        out = out_dir / "latent_diag_default_targets.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        print(f"wrote_default_targets={out}")
        raise SystemExit(0)
    if args.targets_csv:
        df = pd.read_csv(args.targets_csv, dtype={"cutoff": str, "grid_spec_id": str, "phase": str})
    else:
        df = pd.DataFrame(DEFAULT_TARGETS)
    for col in ["cutoff", "grid_spec_id", "q"]:
        if col not in df.columns:
            raise ValueError(f"targets CSV missing required column: {col}")
    if "phase" not in df.columns:
        df["phase"] = "diag"
    if "state_guard_start_iter" not in df.columns:
        df["state_guard_start_iter"] = ""
    df["cutoff"] = df["cutoff"].astype(str).str.zfill(8)
    df["q"] = pd.to_numeric(df["q"], errors="raise")
    return df


def source_config_path(source_config_dir: Path, cutoff: str, grid_spec_id: str) -> Path:
    hits = sorted(source_config_dir.glob(f"multimodel_{cutoff}_v8_he2grid_{grid_spec_id}_exdqlm_multivar_keep.yaml"))
    if not hits:
        raise FileNotFoundError(f"missing source config for cutoff={cutoff} grid_spec_id={grid_spec_id} in {source_config_dir}")
    if len(hits) > 1:
        raise ValueError(f"ambiguous source config for cutoff={cutoff} grid_spec_id={grid_spec_id}: {hits}")
    return hits[0]


def set_nested(data: dict[str, Any], keys: list[str], value: Any) -> None:
    cur = data
    for key in keys[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[keys[-1]] = value


def prepare_config(
    cfg: dict[str, Any],
    *,
    artifact_root: Path,
    config_output_dir: Path,
    target: pd.Series,
    args: argparse.Namespace,
) -> tuple[str, Path]:
    cutoff = str(target["cutoff"]).zfill(8)
    grid_spec_id = str(target["grid_spec_id"])
    phase = safe_token(target.get("phase", "diag"))
    q = float(target["q"])
    qtok = q_label(q)
    source_run_id = str(cfg["run"]["run_id"])
    run_id = f"{source_run_id}_latentdiag_{phase}_{qtok}"
    config_path = config_output_dir / f"{run_id}.yaml"
    run_root = artifact_root / "runs"
    resolved_run_root = run_root / run_id

    cfg.setdefault("run", {})
    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(run_root)
    cfg["run"]["resolved_run_root"] = str(resolved_run_root)
    cfg["run"]["resolved_config_path"] = str(config_path)
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = False
    cfg.setdefault("fit", {})
    cfg["fit"]["quantiles"] = [q]
    set_nested(cfg, ["fit", "parallel", "workers"], 1)
    set_nested(cfg, ["run", "threads", "mc_cores"], 1)
    set_nested(cfg, ["fit", "exdqlm_multivar", "latent_ablation", "mode"], str(args.latent_mode))
    set_nested(cfg, ["fit", "exdqlm_multivar", "latent_ablation", "e_inv_u_cap"], float(args.e_inv_u_cap))
    set_nested(cfg, ["fit", "exdqlm_multivar", "latent_ablation", "e_u_cap"], float(args.e_u_cap))
    set_nested(cfg, ["fit", "exdqlm_multivar", "pseudodata_guard", "enabled"], True)
    set_nested(cfg, ["fit", "exdqlm_multivar", "pseudodata_guard", "mode"], str(args.pseudodata_guard_mode))
    set_nested(cfg, ["fit", "exdqlm_multivar", "diagnostics", "latent", "enabled"], True)
    set_nested(cfg, ["fit", "exdqlm_multivar", "diagnostics", "latent", "report_dir"], str(resolved_run_root / "diagnostics" / qtok))
    set_nested(cfg, ["fit", "exdqlm_multivar", "diagnostics", "latent", "top_k"], int(args.diagnostic_top_k))
    set_nested(cfg, ["fit", "exdqlm_multivar", "diagnostics", "latent", "write_iteration_summary"], True)
    set_nested(cfg, ["fit", "exdqlm_multivar", "diagnostics", "latent", "write_top_cells"], True)
    if args.max_iter is not None:
        set_nested(cfg, ["fit", "exdqlm_multivar", "gamma_sigma", "max_iter"], int(args.max_iter))

    state_guard_raw = target.get("state_guard_start_iter", "")
    if pd.notna(state_guard_raw) and str(state_guard_raw).strip() != "":
        set_nested(
            cfg,
            ["fit", "exdqlm_multivar", "gamma_sigma", "stabilization", "state_guard_start_iter"],
            int(float(state_guard_raw)),
        )

    cfg.setdefault("debug_he2_exdqlm_keep_latent_diag", {})
    cfg["debug_he2_exdqlm_keep_latent_diag"].update({
        "source_run_id": source_run_id,
        "cutoff": cutoff,
        "grid_spec_id": grid_spec_id,
        "phase": phase,
        "q": q,
        "cleanup_rdata_after_post": bool(args.cleanup_rdata_after_post),
    })
    return run_id, config_path


def main() -> int:
    args = parse_args()
    source_config_dir = Path(args.source_config_dir).expanduser().resolve()
    artifact_root = Path(args.artifact_root).expanduser().resolve()
    matrix_dir = artifact_root / "control" / "latent_diag_matrix"
    config_output_dir = artifact_root / "control" / "generated_configs"
    matrix_dir.mkdir(parents=True, exist_ok=True)
    config_output_dir.mkdir(parents=True, exist_ok=True)

    targets = load_targets(args, matrix_dir)
    rows: list[dict[str, Any]] = []
    for _, target in targets.iterrows():
        cutoff = str(target["cutoff"]).zfill(8)
        grid_spec_id = str(target["grid_spec_id"])
        src_path = source_config_path(source_config_dir, cutoff, grid_spec_id)
        cfg = read_yaml(src_path)
        run_id, config_path = prepare_config(
            cfg,
            artifact_root=artifact_root,
            config_output_dir=config_output_dir,
            target=target,
            args=args,
        )
        write_yaml(config_path, cfg)
        rows.append({
            "phase": target.get("phase", "diag"),
            "cutoff": cutoff,
            "grid_spec_id": grid_spec_id,
            "q": float(target["q"]),
            "q_label": q_label(float(target["q"])),
            "run_id": run_id,
            "config_path": str(config_path),
            "source_config_path": str(src_path),
            "artifact_root": str(artifact_root),
            "state_guard_start_iter": target.get("state_guard_start_iter", ""),
            "latent_mode": str(args.latent_mode),
            "e_inv_u_cap": float(args.e_inv_u_cap),
            "e_u_cap": float(args.e_u_cap),
            "diagnostic_top_k": int(args.diagnostic_top_k),
        })

    plan = pd.DataFrame(rows)
    plan.to_csv(matrix_dir / "latent_diag_matrix_plan.csv", index=False)
    (matrix_dir / "README.md").write_text(
        "\n".join([
            "# exDQLM Multivar Keep Latent Diagnostic Matrix",
            "",
            f"- status: `prepared_not_launched`",
            f"- artifact_root: `{artifact_root}`",
            f"- source_config_dir: `{source_config_dir}`",
            f"- generated_configs: `{config_output_dir}`",
            f"- matrix_plan: `{matrix_dir / 'latent_diag_matrix_plan.csv'}`",
            f"- targets: `{len(plan)}`",
            "",
            "Launch only after explicit approval. These configs run one quantile lane per row with diagnostics enabled.",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"artifact_root={artifact_root}")
    print(f"matrix_dir={matrix_dir}")
    print(f"config_output_dir={config_output_dir}")
    print(f"targets={len(plan)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
