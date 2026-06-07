from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.build_he2_al_m_t0_p5_closeout_report import EXPECTED_CUTOFFS, TARGET_MODEL_ID, terminal_rows, validate_and_collect


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_id(cutoff: str) -> str:
    return f"multimodel_{cutoff}_v8_he2pubgdpc1r1_dqlm_multivar_al_drop"


class He2AlMT0P5CloseoutReportTests(unittest.TestCase):
    def populate_artifact_root(self, artifact_root: Path) -> None:
        write_csv(
            artifact_root / "control" / "publication_relaunch_matrix" / "matrix_status.csv",
            [
                {
                    "cutoff": cutoff,
                    "run_id": run_id(cutoff),
                    "phase": "report",
                    "status": "pass",
                    "finished_at": f"2026-06-06T00:0{i}:00Z",
                }
                for i, cutoff in enumerate(EXPECTED_CUTOFFS)
            ],
        )
        for cutoff in EXPECTED_CUTOFFS:
            rid = run_id(cutoff)
            run_root = artifact_root / "runs" / rid
            (run_root / "run_manifest.yaml").parent.mkdir(parents=True, exist_ok=True)
            (run_root / "run_manifest.yaml").write_text("run:\n  run_id: test\n", encoding="utf-8")
            for q in ["05", "20", "35", "50", "65", "80", "95"]:
                write_csv(
                    run_root / "fit" / f"q={q}" / "outputs" / "multivar_terminal_state_health.csv",
                    [
                        {
                            "metric": "state_norm_sq_per_T",
                            "value": str(float(int(q)) / 10.0),
                            "limit": "10000",
                            "direction": "max",
                            "status": "ok",
                        }
                    ],
                )
            out_dir = run_root / "post" / "outputs" / rid
            write_csv(
                out_dir / "tables" / "crps_forecast_summary.csv",
                [
                    {"model_id": TARGET_MODEL_ID, "mean_crps": "0.25", "n_valid": "28", "score_scale": "log_cms_plus1"},
                    {"model_id": "glofas_ensemble", "mean_crps": "0.35", "n_valid": "28", "score_scale": "log_cms_plus1"},
                    {"model_id": "nws_nwm_ensemble", "mean_crps": "0.45", "n_valid": "8", "score_scale": "log_cms_plus1"},
                ],
            )
            write_csv(out_dir / "publication_figure_manifest.csv", [{"figure_id": "cutoff_window", "path": "plot.png"}])

    def test_terminal_rows_parse_metric_value_health_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_p5_terminal_rows_") as tmp:
            root = Path(tmp)
            write_csv(
                root / "fit" / "q=65" / "outputs" / "multivar_terminal_state_health.csv",
                [
                    {"metric": "state_norm_sq_per_T", "value": "8.5", "status": "ok"},
                    {"metric": "transfer_level_max_abs", "value": "1.0", "status": "ok"},
                ],
            )
            rows = terminal_rows(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["q"], "65")
            self.assertEqual(rows[0]["terminal_exists"], "true")
            self.assertEqual(rows[0]["state_norm_sq_per_T"], "8.5")
            self.assertEqual(rows[0]["non_ok_count"], "0")

    def test_validate_and_collect_accepts_complete_clean_p5_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_p5_closeout_clean_") as tmp:
            artifact_root = Path(tmp)
            self.populate_artifact_root(artifact_root)
            summary_rows, crps_rows, failures = validate_and_collect(artifact_root)
            self.assertEqual(failures, [])
            self.assertEqual(len(summary_rows), len(EXPECTED_CUTOFFS))
            self.assertEqual(len(crps_rows), 3 * len(EXPECTED_CUTOFFS))
            for row in summary_rows:
                self.assertEqual(row["matrix_status"], "pass")
                self.assertEqual(row["terminal_health_files"], 7)
                self.assertEqual(row["terminal_violation_n"], 0)
                self.assertEqual(row["publication_figure_manifest_rows"], 1)
                self.assertEqual(row["rdata_count_after_post"], 0)
                self.assertEqual(row["synth_mean_crps"], "0.25")
                self.assertEqual(row["glofas_mean_crps"], "0.35")
                self.assertEqual(row["nws_mean_crps"], "0.45")

    def test_validate_and_collect_flags_retained_rdata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="he2_p5_closeout_dirty_") as tmp:
            artifact_root = Path(tmp)
            self.populate_artifact_root(artifact_root)
            dirty = artifact_root / "runs" / run_id(EXPECTED_CUTOFFS[0]) / "fit" / "q=05" / "outputs" / "old.RData"
            dirty.write_text("heavy", encoding="utf-8")
            summary_rows, _crps_rows, failures = validate_and_collect(artifact_root)
            self.assertTrue(any("retained RData count" in item for item in failures))
            first = next(row for row in summary_rows if row["cutoff"] == EXPECTED_CUTOFFS[0])
            self.assertEqual(first["rdata_count_after_post"], 1)


if __name__ == "__main__":
    unittest.main()
