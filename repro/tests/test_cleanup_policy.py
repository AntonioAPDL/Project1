from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import sys

REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
TOOLS_DIR = REPO_ROOT / "repro" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import cleanup_policy  # noqa: E402


def write_text(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_manifest(path: Path, run_id: str, finished_at: str | None, status: str = "pass") -> None:
    finished_yaml = "null" if finished_at is None else f"'{finished_at}'"
    write_text(
        path,
        "\n".join(
            [
                "manifest_version: 1",
                f"run_id: {run_id}",
                "timestamps:",
                "  started_at_utc: '2026-02-01T00:00:00Z'",
                f"  finished_at_utc: {finished_yaml}",
                "validation:",
                f"  status: {status}",
                "git:",
                "  commit: deadbeef",
            ]
        )
        + "\n",
    )


def write_resolved_config(path: Path, profile: str = "smoke", multivar: bool = True, univar: bool = False, ndlm: bool = False) -> None:
    write_text(
        path,
        "\n".join(
            [
                "models:",
                f"  run_exdqlm_multivar: {'true' if multivar else 'false'}",
                f"  run_exdqlm_univar: {'true' if univar else 'false'}",
                f"  run_ndlm_main: {'true' if ndlm else 'false'}",
                "validation:",
                f"  profile: {profile}",
            ]
        )
        + "\n",
    )


class CleanupPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="cleanup_policy_ut_"))
        self.repo_root = self.tmpdir
        (self.repo_root / "config" / "unified_runs").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "repro" / "runs").mkdir(parents=True, exist_ok=True)
        (self.repo_root / "repro" / "baseline_runs").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _set_age_days(self, path: Path, days: int) -> None:
        now = cleanup_policy.utc_now().timestamp()
        ts = now - days * 86400
        for p in [path, *path.rglob("*")]:
            try:
                p.touch(exist_ok=True)
                p.stat()
                p.utime((ts, ts))  # type: ignore[attr-defined]
            except Exception:
                try:
                    import os

                    os.utime(p, (ts, ts))
                except Exception:
                    continue

    def test_protected_set_detection_baseline_yaml_and_canonical(self) -> None:
        runs = self.repo_root / "repro" / "runs"
        baseline = self.repo_root / "repro" / "baseline_runs"

        canonical = runs / "canonical_run"
        canonical.mkdir(parents=True)
        write_manifest(canonical / "run_manifest.yaml", "canonical_run", "2026-02-01T01:00:00Z")
        write_resolved_config(canonical / "resolved_config.yaml", profile="production")
        self._set_age_days(canonical, 30)

        yaml_protected = runs / "yaml_protected"
        yaml_protected.mkdir(parents=True)
        write_manifest(yaml_protected / "run_manifest.yaml", "yaml_protected", "2026-02-01T01:00:00Z")
        write_resolved_config(yaml_protected / "resolved_config.yaml")
        self._set_age_days(yaml_protected, 30)

        active = runs / "active_unfinished"
        active.mkdir(parents=True)
        write_manifest(active / "run_manifest.yaml", "active_unfinished", None)
        write_resolved_config(active / "resolved_config.yaml")

        failed_old = runs / "failed_old"
        failed_old.mkdir(parents=True)
        write_manifest(failed_old / "run_manifest.yaml", "failed_old", None)
        write_resolved_config(failed_old / "resolved_config.yaml")
        self._set_age_days(failed_old, 12)

        baseline_run = baseline / "baseline_keep"
        baseline_run.mkdir(parents=True)
        write_manifest(baseline_run / "run_manifest.yaml", "baseline_keep", "2026-02-01T01:00:00Z")
        write_resolved_config(baseline_run / "resolved_config.yaml")
        self._set_age_days(baseline_run, 30)

        write_text(
            self.repo_root / "config" / "unified_runs" / "c.yaml",
            "validation:\n  canonical_run_id: canonical_run\n",
        )
        write_text(
            self.repo_root / "repro" / "protected_runs.yaml",
            "protected_run_ids:\n  - yaml_protected\nnotes:\n  yaml_protected: protected for test\nbaseline_delete_allowlist: []\n",
        )

        records = cleanup_policy.collect_run_records(
            runs_dir=runs,
            baseline_dir=baseline,
            include_baseline=True,
            safety_window_hours=6,
        )
        plan = cleanup_policy.build_cleanup_plan(
            repo_root=self.repo_root,
            records=records,
            keep_last=0,
            older_than_days=7,
            thin_old=False,
            thin_old_days=7,
            thin_failed=False,
            thin_baseline=False,
            delete_failed=True,
            include_baseline=False,
            inventory_root_rdata=False,
            prune_root_rdata=False,
            protected_config_path=self.repo_root / "repro" / "protected_runs.yaml",
        )

        protected = {r.run_id: set(r.protect_reasons) for r in plan.protected_runs}
        self.assertIn("baseline_default_protected", protected["baseline_keep"])
        self.assertIn("protected_runs_yaml", protected["yaml_protected"])
        self.assertIn("canonical_config_reference", protected["canonical_run"])
        self.assertIn("in_progress_manifest", protected["active_unfinished"])

        actions = {a.run_id: a for a in plan.actions}
        self.assertIn("failed_old", actions)
        self.assertEqual(actions["failed_old"].reason, "delete_failed_unfinished")

    def test_thinning_deletes_only_allowed_paths(self) -> None:
        runs = self.repo_root / "repro" / "runs"
        baseline = self.repo_root / "repro" / "baseline_runs"
        run = runs / "thin_target"
        run.mkdir(parents=True)

        write_manifest(run / "run_manifest.yaml", "thin_target", "2026-02-01T01:00:00Z")
        write_resolved_config(run / "resolved_config.yaml")
        write_text(run / "fit" / "q=50" / "outputs" / "state.RData", "state")
        write_text(run / "fit" / "q=50" / "outputs" / "draws.rds", "draws")
        write_text(run / "fit" / "q=50" / "logs" / "fit.log", "keep")
        write_text(run / "fit" / "q=50" / "cache" / "tmp.bin", "cache")
        write_text(run / "post" / "cache" / "post_cache.bin", "cache")
        write_text(run / "post" / "logs" / "post.log", "keep")
        write_text(run / "post" / "outputs" / "thin_target" / "figure.txt", "keep")
        write_text(run / "validate" / "compare_report.json", "{}")
        write_text(run / "report" / "summary.json", "{}")
        self._set_age_days(run, 30)

        write_text(self.repo_root / "repro" / "protected_runs.yaml", "protected_run_ids: []\nnotes: {}\n")

        records = cleanup_policy.collect_run_records(runs, baseline, include_baseline=False, safety_window_hours=6)
        plan = cleanup_policy.build_cleanup_plan(
            repo_root=self.repo_root,
            records=records,
            keep_last=0,
            older_than_days=7,
            thin_old=True,
            thin_old_days=7,
            thin_failed=False,
            thin_baseline=False,
            delete_failed=False,
            include_baseline=False,
            inventory_root_rdata=False,
            prune_root_rdata=False,
            protected_config_path=self.repo_root / "repro" / "protected_runs.yaml",
        )

        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].action, "thin_run")
        apply_result = cleanup_policy.apply_cleanup_plan(plan, apply=True)
        self.assertEqual(apply_result["mode"], "apply")

        self.assertFalse((run / "fit" / "q=50" / "outputs" / "state.RData").exists())
        self.assertFalse((run / "fit" / "q=50" / "outputs" / "draws.rds").exists())
        self.assertFalse((run / "fit" / "q=50" / "cache").exists())
        self.assertFalse((run / "post" / "cache").exists())

        self.assertTrue((run / "run_manifest.yaml").exists())
        self.assertTrue((run / "resolved_config.yaml").exists())
        self.assertTrue((run / "fit" / "q=50" / "logs" / "fit.log").exists())
        self.assertTrue((run / "post" / "logs" / "post.log").exists())
        self.assertTrue((run / "post" / "outputs" / "thin_target" / "figure.txt").exists())
        self.assertTrue((run / "validate" / "compare_report.json").exists())
        self.assertTrue((run / "report" / "summary.json").exists())

    def test_dry_run_produces_no_changes(self) -> None:
        runs = self.repo_root / "repro" / "runs"
        baseline = self.repo_root / "repro" / "baseline_runs"
        run = runs / "dryrun_target"
        run.mkdir(parents=True)

        write_manifest(run / "run_manifest.yaml", "dryrun_target", "2026-02-01T01:00:00Z")
        write_resolved_config(run / "resolved_config.yaml")
        write_text(run / "fit" / "q=05" / "outputs" / "artifact.RData", "artifact")
        self._set_age_days(run, 30)

        write_text(self.repo_root / "repro" / "protected_runs.yaml", "protected_run_ids: []\nnotes: {}\n")

        records = cleanup_policy.collect_run_records(runs, baseline, include_baseline=False, safety_window_hours=6)
        plan = cleanup_policy.build_cleanup_plan(
            repo_root=self.repo_root,
            records=records,
            keep_last=0,
            older_than_days=7,
            thin_old=False,
            thin_old_days=7,
            thin_failed=False,
            thin_baseline=False,
            delete_failed=False,
            include_baseline=False,
            inventory_root_rdata=False,
            prune_root_rdata=False,
            protected_config_path=self.repo_root / "repro" / "protected_runs.yaml",
        )

        self.assertEqual(len(plan.actions), 1)
        cleanup_policy.apply_cleanup_plan(plan, apply=False)
        self.assertTrue((run / "fit" / "q=05" / "outputs" / "artifact.RData").exists())

    def test_thin_failed_blocked_by_protected_set(self) -> None:
        runs = self.repo_root / "repro" / "runs"
        baseline = self.repo_root / "repro" / "baseline_runs"
        run = runs / "failed_protected"
        run.mkdir(parents=True)

        write_manifest(run / "run_manifest.yaml", "failed_protected", None, status="pending")
        write_resolved_config(run / "resolved_config.yaml", profile="production", multivar=True)
        write_text(run / "fit" / "q=05" / "outputs" / "state.RData", "state")
        self._set_age_days(run, 20)

        write_text(
            self.repo_root / "repro" / "protected_runs.yaml",
            "protected_run_ids:\n  - failed_protected\nnotes: {}\nbaseline_delete_allowlist: []\n",
        )

        records = cleanup_policy.collect_run_records(runs, baseline, include_baseline=False, safety_window_hours=6)
        plan = cleanup_policy.build_cleanup_plan(
            repo_root=self.repo_root,
            records=records,
            keep_last=0,
            older_than_days=7,
            thin_old=False,
            thin_old_days=7,
            thin_failed=True,
            thin_baseline=False,
            delete_failed=False,
            include_baseline=False,
            inventory_root_rdata=False,
            prune_root_rdata=False,
            protected_config_path=self.repo_root / "repro" / "protected_runs.yaml",
        )

        self.assertEqual(len(plan.actions), 0)
        blocked_ids = {x["run_id"] for x in plan.thin_failed_blocked}
        self.assertIn("failed_protected", blocked_ids)

    def test_root_rdata_inventory_and_prune_action(self) -> None:
        root_rdata = self.repo_root / "DISC_variables_50_exAL_synth_DISC.RData"
        write_text(root_rdata, "state")
        write_text(self.repo_root / "repro" / "protected_runs.yaml", "protected_run_ids: []\nnotes: {}\n")

        plan = cleanup_policy.build_cleanup_plan(
            repo_root=self.repo_root,
            records=[],
            keep_last=0,
            older_than_days=7,
            thin_old=False,
            thin_old_days=7,
            thin_failed=False,
            thin_baseline=False,
            delete_failed=False,
            include_baseline=False,
            inventory_root_rdata=True,
            prune_root_rdata=True,
            protected_config_path=self.repo_root / "repro" / "protected_runs.yaml",
        )
        self.assertTrue(any(c["path"] == str(root_rdata) for c in plan.root_rdata_candidates))
        prune_actions = [a for a in plan.actions if a.action == "delete_root_rdata"]
        self.assertEqual(len(prune_actions), 1)
        self.assertIn(str(root_rdata), prune_actions[0].targets)

    def test_keep_last_success_does_not_protect_failed_completed_run(self) -> None:
        runs = self.repo_root / "repro" / "runs"
        baseline = self.repo_root / "repro" / "baseline_runs"

        passed = runs / "passed_new"
        passed.mkdir(parents=True)
        write_manifest(passed / "run_manifest.yaml", "passed_new", "2026-02-02T01:00:00Z", status="pass")
        write_resolved_config(passed / "resolved_config.yaml", profile="production")
        self._set_age_days(passed, 30)

        failed = runs / "failed_closed"
        failed.mkdir(parents=True)
        write_manifest(failed / "run_manifest.yaml", "failed_closed", "2026-02-03T01:00:00Z", status="fail")
        write_resolved_config(failed / "resolved_config.yaml", profile="production")
        self._set_age_days(failed, 30)

        write_text(self.repo_root / "repro" / "protected_runs.yaml", "protected_run_ids: []\nnotes: {}\n")

        records = cleanup_policy.collect_run_records(runs, baseline, include_baseline=False, safety_window_hours=0)
        plan = cleanup_policy.build_cleanup_plan(
            repo_root=self.repo_root,
            records=records,
            keep_last=12,
            older_than_days=0,
            thin_old=False,
            thin_old_days=0,
            thin_failed=False,
            thin_baseline=False,
            delete_failed=True,
            include_baseline=False,
            inventory_root_rdata=False,
            prune_root_rdata=False,
            protected_config_path=self.repo_root / "repro" / "protected_runs.yaml",
        )

        protected_ids = {r.run_id for r in plan.protected_runs}
        self.assertIn("passed_new", protected_ids)
        self.assertNotIn("failed_closed", protected_ids)
        action_ids = {a.run_id for a in plan.actions}
        self.assertIn("failed_closed", action_ids)


if __name__ == "__main__":
    unittest.main()
