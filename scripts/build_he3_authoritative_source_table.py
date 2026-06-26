#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from he2_exdqlm_keep_authoritative import load_authoritative_spec


DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "he3_exdqlm_ablation_authoritative_20260608_best_by_cutoff_long.csv"
)
DEFAULT_PUBLICATION_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "reports"
    / "he2_publication_manifest"
    / "he2_bayesian_publication_manifest.csv"
)
SOURCE_FAMILY = "exdqlm_multivar_keep"
SOURCE_LABEL = "exAL-M-T1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a HE3-compatible best-by-cutoff source table from the authoritative exAL-M-T1 winners."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--authoritative-manifest", type=Path, default=None)
    parser.add_argument("--publication-manifest", type=Path, default=DEFAULT_PUBLICATION_MANIFEST)
    return parser.parse_args()


def row_template(
    *,
    cutoff: str,
    rank: int,
    model_variant: str,
    transfer_mode: str,
    crps: float,
    best_epsilon_label: str,
    best_epsilon_value: float,
    best_c_factor: float,
    selection_basis: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "cutoff": str(cutoff).zfill(8),
        "rank_within_cutoff": int(rank),
        "model_variant": model_variant,
        "class": "bayes",
        "transfer_mode": transfer_mode,
        "horizon_days": 28,
        "forecast_window_crps": float(crps),
        "best_epsilon_label": best_epsilon_label,
        "best_epsilon_value": float(best_epsilon_value),
        "best_c_factor": float(best_c_factor),
        "selection_basis": selection_basis,
    }
    if extra:
        row.update(extra)
    return row


def load_drop_rows(publication_manifest: Path) -> dict[str, dict[str, Any]]:
    if not publication_manifest.exists():
        return {}
    df = pd.read_csv(publication_manifest)
    if "family" not in df.columns:
        return {}
    rows = df[df["family"].astype(str).eq("exdqlm_multivar_drop")].copy()
    if rows.empty and "manuscript_label" in df.columns:
        rows = df[df["manuscript_label"].astype(str).eq("exAL-M-T0")].copy()
    out: dict[str, dict[str, Any]] = {}
    for _, row in rows.iterrows():
        cutoff = str(row["cutoff"]).zfill(8)
        out[cutoff] = row.to_dict()
    return out


def decode_json_mapping(value: Any) -> dict[str, Any]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return {}
    text = str(value).strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def source_label_from_run_id(run_id: str) -> str:
    match = re.search(r"_v8_(?P<label>.+?)_exdqlm_multivar_keep$", str(run_id))
    if not match:
        return str(run_id)
    label = match.group("label")
    if label.startswith("he2grid_"):
        label = label[len("he2grid_") :]
    return label


def load_keep_rows_from_publication_manifest(publication_manifest: Path) -> list[dict[str, Any]]:
    if not publication_manifest.exists():
        return []
    df = pd.read_csv(publication_manifest)
    if "family" not in df.columns:
        return []
    rows = df[
        df["family"].astype(str).eq(SOURCE_FAMILY)
        | df.get("manuscript_label", pd.Series(dtype=str)).astype(str).eq(SOURCE_LABEL)
    ].copy()
    if rows.empty:
        return []
    rows["cutoff"] = rows["cutoff"].astype(str).str.zfill(8)
    rows = rows.sort_values("cutoff").reset_index(drop=True)
    out: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        state = decode_json_mapping(row.get("state_evolution_json"))
        prior = decode_json_mapping(row.get("prior_json"))
        forecast_cov = prior.get("forecast_cov", {}) if isinstance(prior.get("forecast_cov", {}), dict) else {}
        run_id = str(row["run_id"])
        source_label = source_label_from_run_id(run_id)
        epsilon_value = forecast_cov.get("epsilon")
        if epsilon_value is None:
            epsilon_match = re.search(r"eps(?P<epsilon>\d+)", source_label)
            epsilon_value = float(epsilon_match.group("epsilon")) if epsilon_match else 0.0
        c_factor = forecast_cov.get("c_factor", 1.0)
        out.append(
            row_template(
                cutoff=str(row["cutoff"]),
                rank=1,
                model_variant=SOURCE_FAMILY,
                transfer_mode="keep",
                crps=float(row["crps_exact"]),
                best_epsilon_label=source_label,
                best_epsilon_value=float(epsilon_value),
                best_c_factor=float(c_factor),
                selection_basis=str(row.get("campaign_lineage", "he2_publication_manifest")),
                extra={
                    "source_label": source_label,
                    "source_run_id": run_id,
                    "source_run_dir": str(row.get("run_root", "")),
                    "source_config_path": str(row.get("resolved_config_path", "")),
                    "source_full_crps": float(row["crps_exact"]),
                    "discount_case_id": str(source_label.split("_eps", 1)[0]),
                    "df_t": state.get("df_t", ""),
                    "df_s1": state.get("df_s1", ""),
                    "df_s2": state.get("df_s2", ""),
                    "df_s67": state.get("df_s67", ""),
                    "df_discrep": state.get("df_discrep", ""),
                    "lambda": state.get("lambda", ""),
                    "df_trans": state.get("df_trans", ""),
                    "df_covs": state.get("df_covs", ""),
                },
            )
        )
    return out


def build_rows(authoritative_manifest: Path | None, publication_manifest: Path) -> list[dict[str, Any]]:
    publication_keep_rows = load_keep_rows_from_publication_manifest(publication_manifest)
    if publication_keep_rows:
        drop_by_cutoff = load_drop_rows(publication_manifest)
        rows = list(publication_keep_rows)
        for keep in publication_keep_rows:
            cutoff = str(keep["cutoff"]).zfill(8)
            drop = drop_by_cutoff.get(cutoff)
            if not drop:
                continue
            rows.append(
                row_template(
                    cutoff=cutoff,
                    rank=2,
                    model_variant="exdqlm_multivar_drop",
                    transfer_mode="drop",
                    crps=float(drop["crps_exact"]),
                    best_epsilon_label="publication_manifest",
                    best_epsilon_value=float(keep["best_epsilon_value"]),
                    best_c_factor=1.0,
                    selection_basis="he2_publication_manifest_exal_m_t0_for_he3_notf_delta",
                    extra={
                        "source_run_id": str(drop.get("run_id", "")),
                        "discount_case_id": "",
                        "df_t": "",
                        "df_s1": "",
                        "df_s2": "",
                        "df_s67": "",
                        "df_discrep": "",
                        "lambda": "",
                        "df_trans": "",
                        "df_covs": "",
                    },
                )
            )
        return rows

    spec = load_authoritative_spec(authoritative_manifest)
    drop_by_cutoff = load_drop_rows(publication_manifest)
    rows: list[dict[str, Any]] = []
    for winner in spec.winners:
        rows.append(
            row_template(
                cutoff=winner.cutoff,
                rank=1,
                model_variant="exdqlm_multivar_keep",
                transfer_mode="keep",
                crps=winner.mean_crps,
                best_epsilon_label=winner.grid_spec_id,
                best_epsilon_value=winner.epsilon_value,
                best_c_factor=winner.c_factor,
                selection_basis="authoritative_exdqlm_keep_winner_manifest_20260601",
                extra={
                    "source_run_id": winner.run_id,
                    "discount_case_id": winner.discount_case_id,
                    "df_t": winner.df_t,
                    "df_s1": winner.df_s1,
                    "df_s2": winner.df_s2,
                    "df_s67": winner.df_s67,
                    "df_discrep": winner.df_discrep,
                    "lambda": winner.lambda_value,
                    "df_trans": winner.df_trans,
                    "df_covs": winner.df_covs,
                },
            )
        )
        drop = drop_by_cutoff.get(winner.cutoff)
        if drop:
            rows.append(
                row_template(
                    cutoff=winner.cutoff,
                    rank=2,
                    model_variant="exdqlm_multivar_drop",
                    transfer_mode="drop",
                    crps=float(drop["crps_exact"]),
                    best_epsilon_label="publication_manifest",
                    best_epsilon_value=float(winner.epsilon_value),
                    best_c_factor=1.0,
                    selection_basis="he2_publication_manifest_exal_m_t0_for_he3_notf_delta",
                    extra={
                        "source_run_id": str(drop.get("run_id", "")),
                        "discount_case_id": "",
                        "df_t": "",
                        "df_s1": "",
                        "df_s2": "",
                        "df_s67": "",
                        "df_discrep": "",
                        "lambda": "",
                        "df_trans": "",
                        "df_covs": "",
                    },
                )
            )
    return rows


def main() -> int:
    args = parse_args()
    rows = build_rows(args.authoritative_manifest, args.publication_manifest)
    df = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
