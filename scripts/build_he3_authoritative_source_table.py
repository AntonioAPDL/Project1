#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def build_rows(authoritative_manifest: Path | None, publication_manifest: Path) -> list[dict[str, Any]]:
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
