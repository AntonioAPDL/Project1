"""Focused migration checks using pure/mock/temporary-file fixtures, no Git writes."""

from __future__ import annotations

import hashlib
import importlib.util
import io
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


HELPER_PATH = Path(__file__).resolve().parents[2] / "docs/article_repository_migration_20261108/verification_helpers.py"
SPEC = importlib.util.spec_from_file_location("migration_verification", HELPER_PATH)
assert SPEC is not None and SPEC.loader is not None
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def entry(path: str, data: bytes = b"manuscript\n", mode: str = "100644") -> dict:
    return {"path": path, "mode": mode, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def inventory(entries: list[dict], commit: str = "source") -> dict:
    return {"commit": commit, "tree": "tree-" + commit, "file_count": len(entries),
            "total_blob_bytes": sum(x["bytes"] for x in entries), "files": entries}


class MigrationContentVerificationTests(unittest.TestCase):
    def test_modified_content_fails_even_with_matching_counts_and_sizes(self):
        source = inventory([entry("article.tex", b"original")])
        changed = inventory([entry("article.tex", b"tampered")])
        report = helper.compare_inventories(source, changed)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["changed_contents"][0]["path"], "article.tex")
        self.assertFalse(report["all_source_blob_contents_preserved"])

    def test_missing_and_unexpected_paths_do_not_cancel_at_equal_counts(self):
        report = helper.compare_inventories(inventory([entry("required.csv")]), inventory([entry("replacement.csv")]))
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["missing_paths"], ["required.csv"])
        self.assertEqual(report["unexpected_paths"], ["replacement.csv"])

    def test_mode_exception_is_exact_path_and_direction_and_never_allows_content_change(self):
        policy = {helper.WILEY_CHECKER: ("100755", "100644")}
        source = inventory([entry(helper.WILEY_CHECKER, b"x", "100755"), entry("other.py", b"y", "100755")])
        candidate = inventory([entry(helper.WILEY_CHECKER, b"x"), entry("other.py", b"y", "100755")])
        self.assertEqual(helper.compare_inventories(source, candidate)["status"], "FAIL")
        accepted = helper.compare_inventories(source, candidate, policy)
        self.assertEqual(accepted["status"], "PASS")
        self.assertEqual(len(accepted["accepted_mode_changes"]), 1)
        candidate["files"][1]["mode"] = "100644"
        self.assertEqual(helper.compare_inventories(source, candidate, policy)["status"], "FAIL")
        changed = inventory([entry(helper.WILEY_CHECKER, b"z", "100644"), entry("other.py", b"y", "100755")])
        self.assertEqual(helper.compare_inventories(source, changed, policy)["status"], "FAIL")

    def test_duplicate_inventory_paths_are_rejected(self):
        with self.assertRaises(helper.VerificationError):
            helper.compare_inventories(inventory([entry("x"), entry("x")]), inventory([entry("x")]))

    def test_portability_exception_requires_exact_path_hashes_sizes_and_direction(self):
        old_hash, old_size, new_hash, new_size = helper.PORTABILITY_TEST_CHANGE[helper.PORTABILITY_TEST_PATH]
        old = {"path": helper.PORTABILITY_TEST_PATH, "mode": "100644", "sha256": old_hash, "bytes": old_size}
        new = {"path": helper.PORTABILITY_TEST_PATH, "mode": "100644", "sha256": new_hash, "bytes": new_size}
        source, candidate = inventory([old]), inventory([new])
        self.assertEqual(helper.compare_inventories(source, candidate)["status"], "FAIL")
        report = helper.compare_inventories(source, candidate, allowed_content_changes=helper.PORTABILITY_TEST_CHANGE)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(report["accepted_content_changes"]), 1)
        self.assertEqual(report["unapproved_content_changes"], [])
        self.assertEqual(len(report["changed_contents"]), 1)
        self.assertFalse(report["all_source_blob_contents_preserved"])
        for endpoint, field, value in [(0, "sha256", "0" * 64), (1, "sha256", "0" * 64),
                                       (0, "bytes", old_size + 1), (1, "bytes", new_size + 1)]:
            with self.subTest(endpoint=endpoint, field=field):
                endpoints = [deepcopy(source), deepcopy(candidate)]
                endpoints[endpoint]["files"][0][field] = value
                self.assertEqual(helper.compare_inventories(*endpoints, allowed_content_changes=helper.PORTABILITY_TEST_CHANGE)["status"], "FAIL")
        for before, after in [(candidate, source),
                              (inventory([{**old, "path": "article.tex"}]), inventory([{**new, "path": "article.tex"}])),
                              (source, inventory([{**new, "mode": "100755"}]))]:
            self.assertEqual(helper.compare_inventories(before, after, allowed_content_changes=helper.PORTABILITY_TEST_CHANGE)["status"], "FAIL")
        extra_change = inventory([new, entry("article.tex", b"changed")])
        self.assertEqual(helper.compare_inventories(inventory([old, entry("article.tex")]), extra_change,
                                                   allowed_content_changes=helper.PORTABILITY_TEST_CHANGE)["status"], "FAIL")

    def test_portability_profile_is_opt_in_and_never_applies_to_restoration(self):
        for profile in ("initial", "restored"):
            with self.subTest(profile=profile), patch.object(helper, "committed_inventory") as reader:
                with self.assertRaises(helper.VerificationError):
                    helper.verify_profile("source", "candidate", profile, allow_portability_test_change=True)
                reader.assert_not_called()
        old_hash, old_size, new_hash, new_size = helper.PORTABILITY_TEST_CHANGE[helper.PORTABILITY_TEST_PATH]
        source = {**inventory([{"path": helper.PORTABILITY_TEST_PATH, "mode": "100644", "sha256": old_hash, "bytes": old_size}]),
                  "commit": helper.SOURCE_COMMIT, "tree": helper.SOURCE_TREE, "file_count": 792,
                  "total_blob_bytes": 162142808}
        candidate = {**inventory([{"path": helper.PORTABILITY_TEST_PATH, "mode": "100644", "sha256": new_hash, "bytes": new_size}]),
                     "commit": "candidate", "file_count": 792, "total_blob_bytes": 162142992}
        state = {"status": "PASS", "head": "candidate"}
        with patch.object(helper, "committed_inventory", side_effect=[source, candidate]), patch.object(helper, "repository_state", return_value=state):
            self.assertEqual(helper.verify_profile("source", "candidate", "migrated")["status"], "FAIL")
        with patch.object(helper, "committed_inventory", side_effect=[source, candidate]), patch.object(helper, "repository_state", return_value=state):
            report = helper.verify_profile("source", "candidate", "migrated", allow_portability_test_change=True)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["expected_total_blob_bytes"], 162142992)
        self.assertEqual(report["expected_source_total_blob_bytes"], 162142808)
        self.assertEqual(set(report["allowed_content_changes"]), {helper.PORTABILITY_TEST_PATH})

    def test_cat_file_checks_payload_and_rejects_truncation_or_wrong_object_digest(self):
        body = b"binary\x00payload\n"
        oid = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\x00" + body).hexdigest()
        good = oid.encode() + b" blob " + str(len(body)).encode() + b"\n" + body + b"\n"
        self.assertEqual(helper._hash_batch_blob(io.BytesIO(good), oid)["sha256"], hashlib.sha256(body).hexdigest())
        with self.assertRaises(helper.VerificationError):
            helper._hash_batch_blob(io.BytesIO(good[:-3]), oid)
        with self.assertRaises(helper.VerificationError):
            helper._hash_batch_blob(io.BytesIO(good.replace(body, b"changed-payload\n")), oid)

    def test_filesystem_comparison_detects_missing_and_tampered_tracked_files(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            (root / "article.tex").write_bytes(b"changed!")
            committed = inventory([entry("article.tex", b"original"), entry("missing.csv")])
            working = helper.working_tree_inventory(root, committed)
            report = helper.compare_inventories(committed, working)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["missing_paths"], ["missing.csv"])
            self.assertEqual(report["changed_contents"][0]["path"], "article.tex")

    def test_symlink_target_is_hashed_without_reading_external_content(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            (root / "outside-link").symlink_to("/nonexistent/external-target")
            original = inventory([entry("outside-link", b"/nonexistent/external-target", "120000")])
            working = helper.working_tree_inventory(root, original)
            self.assertEqual(helper.compare_inventories(original, working)["status"], "PASS")
            (root / "escaped-parent").symlink_to("/tmp", target_is_directory=True)
            with self.assertRaises(helper.VerificationError):
                helper.working_tree_inventory(root, inventory([entry("escaped-parent/x")]))

    def test_tree_parser_keeps_tabbed_paths_and_rejects_gitlinks_or_unsafe_paths(self):
        oid = b"a" * 40
        parsed = helper._parse_tree(b"100644 blob " + oid + b"\tname\twith-tab.txt\x00")
        self.assertEqual(parsed[0]["path"], "name\twith-tab.txt")
        for raw in [b"160000 commit " + oid + b"\tsubmodule\x00", b"100644 blob " + oid + b"\t../escape\x00", b"100644 blob " + oid + b"\t.git/config\x00"]:
            with self.subTest(raw=raw), self.assertRaises(helper.VerificationError):
                helper._parse_tree(raw)


class MigrationRepositoryIdentityTests(unittest.TestCase):
    def state_reader(self, dirname: str, *, origin: str, branch: str = "main", head: str = helper.SOURCE_COMMIT,
                     ancestor: bool = True, dirty: bytes = b""):
        def read(_repo, *args, **_kwargs):
            if args == ("rev-parse", "--show-toplevel"):
                return (dirname + "\n").encode()
            if args == ("remote", "get-url", "origin"):
                return (origin + "\n").encode()
            if args == ("branch", "--show-current"):
                return (branch + "\n").encode()
            if args[:2] == ("rev-parse", "--verify"):
                return (head + "\n").encode()
            if args[0] == "status":
                return dirty
            if args[:2] == ("merge-base", "--is-ancestor"):
                return b"\x00" if ancestor else b"\x01"
            raise AssertionError(args)
        return read

    def test_wrong_origin_or_branch_is_a_failure_even_if_contents_could_match(self):
        root = str(Path("/tmp/fake-migration-repository").resolve())
        reader = self.state_reader(root, origin=helper.SOURCE_ORIGIN, branch="unexpected")
        with patch.object(helper, "_git", side_effect=reader):
            report = helper.repository_state(root, expected_origin=helper.DESTINATION_ORIGIN, expected_branch="main")
        self.assertEqual(set(report["errors"]), {"origin_identity_mismatch", "branch_identity_mismatch"})

    def test_hard_reset_is_rejected_by_required_history_and_dirty_index_is_rejected(self):
        root = str(Path("/tmp/fake-migration-repository").resolve())
        reader = self.state_reader(root, origin=helper.SOURCE_ORIGIN, head=helper.BASELINE_COMMIT, ancestor=False, dirty=b"M  article.tex\x00")
        with patch.object(helper, "_git", side_effect=reader):
            report = helper.repository_state(root, expected_origin=helper.SOURCE_ORIGIN, required_ancestor=helper.SOURCE_COMMIT)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("required_history_not_preserved", report["errors"])
        self.assertIn("tracked_worktree_or_index_not_clean", report["errors"])

    def test_origin_normalization_accepts_ssh_https_equivalence_not_repository_substitution(self):
        self.assertEqual(helper.canonical_origin("git@github.com:AntonioAPDL/Evironmetrics----Corrected-3.git"), helper.canonical_origin(helper.DESTINATION_ORIGIN))
        self.assertNotEqual(helper.canonical_origin(helper.SOURCE_ORIGIN), helper.canonical_origin(helper.DESTINATION_ORIGIN))
        for url in ["/tmp/local", "https://github.com.evil.invalid/AntonioAPDL/repo", "https://github.com/AntonioAPDL/repo?ref=main"]:
            with self.subTest(url=url), self.assertRaises(helper.VerificationError):
                helper.canonical_origin(url)

    def test_restoration_scope_covers_added_changed_and_unchanged_paths_without_mutations(self):
        baseline = inventory([entry("same"), entry("changed", b"before"), entry("restore-missing")], helper.BASELINE_COMMIT)
        current = inventory([entry("same"), entry("changed", b"after"), entry("new-artifact")], helper.SOURCE_COMMIT)
        report = helper.restoration_scope(current, baseline)
        self.assertEqual(report["restore_baseline_paths"], ["changed", "restore-missing"])
        self.assertEqual(report["remove_current_tracked_additions"], ["new-artifact"])
        self.assertEqual(report["preserve_unchanged_tracked_paths"], ["same"])
        self.assertFalse(report["untracked_or_ignored_files_deleted"])
        self.assertFalse(report["references_modified"])


if __name__ == "__main__":
    unittest.main()
