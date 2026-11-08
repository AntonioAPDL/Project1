#!/usr/bin/env python3
"""Read-only, content-bound checks for the Corrected-2/Corrected-3 migration.

This program never checks out, fetches, stages, commits, deletes, or updates a
Git reference. JSON reports go to stdout. Lazy fetching and optional Git locks
are disabled so a missing local object fails instead of changing a repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from typing import Any
from urllib.parse import urlsplit


BASELINE_COMMIT = "1272bfc10442a28add5a4c74ff641e9b9a8e9666"
BASELINE_TREE = "35b2c6d2af808a09618ad7365474826e0bf928fd"
SOURCE_COMMIT = "32ab28b6c709bf001456090751edb413ae747a7b"
SOURCE_TREE = "571dda459c2fab4c2411d96461d5c7722468a936"
DESTINATION_ROOT = "80ac992f4ea1b3feda90add7f3b4dd00451f84a4"
DESTINATION_ROOT_TREE = "bddcc018df2dd18e45df2080dc7ff86e88d51ef6"
SOURCE_ORIGIN = "https://github.com/AntonioAPDL/Evironmetrics---REVISED-DOC-Corrected-2.git"
DESTINATION_ORIGIN = "https://github.com/AntonioAPDL/Evironmetrics----Corrected-3.git"
RESPONSE_COMMITS = [
    "dd7855dfe821074ba526308d6a4891ee2b269a7d",
    "373bed4a580e18bbc2b33e1ebe26649b009168b1",
    "2583ee41c1367e65d4d71ed36cf280a4f555a513",
    SOURCE_COMMIT,
]
WILEY_CHECKER = "scripts/check_wiley_submission_requirements.py"
ARCHIVED_EXECUTABLES = (
    "artifacts/comment1_figure_revision/renderer_sources/scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py",
    "artifacts/comment1_figure_revision/renderer_sources/scripts/render_focus_publication_posterior_plot.R",
    "artifacts/comment1_figure_revision/renderer_sources/scripts/render_setup_support_bundle_v2.R",
)
# One reviewed test-only portability repair after the exact transplant. Both
# endpoints are pinned; this policy cannot authorize arbitrary edits to this path.
PORTABILITY_TEST_PATH = "tests/test_no_refit_revision.py"
PORTABILITY_TEST_CHANGE = {
    PORTABILITY_TEST_PATH: (
        "cbeeaee1297273dba5aab588f98c6ea61b44604c95c0ef9aeaecda86b7410730", 5065,
        "c1dc35ed7c6f79117398b370b67b216adcf4d65ab8cbb47e408bd319229eebaf", 5249,
    ),
}
PORTABILITY_TEST_BYTE_DELTA = 184


class VerificationError(RuntimeError):
    pass


def _environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
    return env


def _git(repo: str | Path, *args: str, allow_failure: bool = False) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, env=_environment(), timeout=60,
    )
    if result.returncode and not allow_failure:
        raise VerificationError(result.stderr.decode("utf-8", "replace").strip() or f"Git read failed: {args}")
    if allow_failure:
        if not 0 <= result.returncode <= 255:
            raise VerificationError("Read-only Git process was interrupted")
        return bytes([result.returncode]) + result.stdout
    return result.stdout


def _path(path: str) -> str:
    if (not path or path.startswith("/") or "\x00" in path
            or any(p in ("", ".", "..") or p.casefold() == ".git" for p in path.split("/"))):
        raise VerificationError(f"Unsafe tree path: {path!r}")
    return path


def resolve_commit(repo: str | Path, revision: str) -> str:
    if not revision or revision.startswith("-") or any(c in revision for c in "\x00\r\n"):
        raise VerificationError("Invalid revision")
    return _git(repo, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}").decode().strip()


def _parse_tree(raw: bytes) -> list[dict[str, Any]]:
    entries = []
    for record in raw.split(b"\x00"):
        if not record:
            continue
        try:
            metadata, name = record.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split(" ")
        except (ValueError, UnicodeError) as exc:
            raise VerificationError("Malformed git ls-tree record") from exc
        if kind != "blob" or mode not in {"100644", "100755", "120000"}:
            raise VerificationError(f"Unsupported tree entry: {kind} {mode}; submodules are not followed")
        entries.append({"path": _path(name.decode("utf-8", "surrogateescape")), "mode": mode, "git_oid": oid})
    if len({e["path"] for e in entries}) != len(entries):
        raise VerificationError("Duplicate tree path")
    return sorted(entries, key=lambda e: e["path"])


def _hash_batch_blob(stream: Any, expected_oid: str) -> dict[str, Any]:
    header = stream.readline()
    try:
        oid, kind, size_text = header.rstrip(b"\n").decode("ascii").split(" ")
        size = int(size_text)
    except (ValueError, UnicodeError) as exc:
        raise VerificationError(f"Missing or malformed local blob header for {expected_oid}") from exc
    if oid != expected_oid or kind != "blob" or size < 0:
        raise VerificationError("Unexpected local blob identity/type/size")
    content_hash = hashlib.sha256()
    object_hash = hashlib.sha1() if len(oid) == 40 else hashlib.sha256()
    object_hash.update(b"blob " + str(size).encode() + b"\x00")
    remaining = size
    while remaining:
        chunk = stream.read(min(remaining, 1024 * 1024))
        if not chunk:
            raise VerificationError("Truncated local blob")
        content_hash.update(chunk)
        object_hash.update(chunk)
        remaining -= len(chunk)
    if stream.read(1) != b"\n" or object_hash.hexdigest() != oid:
        raise VerificationError("Blob framing or recomputed Git object digest mismatch")
    return {"bytes": size, "sha256": content_hash.hexdigest()}


def committed_inventory(repo: str | Path, revision: str) -> dict[str, Any]:
    repo = Path(repo).resolve()
    commit = resolve_commit(repo, revision)
    tree = _git(repo, "rev-parse", commit + "^{tree}").decode().strip()
    entries = _parse_tree(_git(repo, "ls-tree", "-r", "-z", "--full-tree", commit))
    hashes = {}
    process = subprocess.Popen(
        ["git", "-C", str(repo), "cat-file", "--batch"], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_environment(),
    )
    try:
        assert process.stdin is not None and process.stdout is not None
        for oid in dict.fromkeys(e["git_oid"] for e in entries):
            process.stdin.write(oid.encode("ascii") + b"\n")
            process.stdin.flush()
            hashes[oid] = _hash_batch_blob(process.stdout, oid)
        process.stdin.close()
        if process.wait(timeout=60):
            raise VerificationError("Read-only cat-file process failed")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
    for entry in entries:
        entry.update(hashes[entry["git_oid"]])
    return {"schema_version": 1, "repository": str(repo), "commit": commit, "tree": tree,
            "file_count": len(entries), "total_blob_bytes": sum(e["bytes"] for e in entries),
            "content_hash": "sha256", "git_objects_independently_rehashed": True, "files": entries}


def compare_inventories(source: dict[str, Any], candidate: dict[str, Any],
                        allowed_mode_changes: dict[str, tuple[str, str]] | None = None,
                        allowed_content_changes: dict[str, tuple[str, int, str, int]] | None = None) -> dict[str, Any]:
    allowed_mode_changes = allowed_mode_changes or {}
    allowed_content_changes = allowed_content_changes or {}
    left = {e["path"]: e for e in source["files"]}
    right = {e["path"]: e for e in candidate["files"]}
    if len(left) != len(source["files"]) or len(right) != len(candidate["files"]):
        raise VerificationError("Duplicate inventory paths")
    missing = sorted(left.keys() - right.keys())
    unexpected = sorted(right.keys() - left.keys())
    changed, content_errors, accepted_contents, mode_errors, accepted_modes = [], [], [], [], []
    for path in sorted(left.keys() & right.keys()):
        a, b = left[path], right[path]
        if a["sha256"] != b["sha256"] or a["bytes"] != b["bytes"]:
            difference = {"path": path, "source_sha256": a["sha256"], "candidate_sha256": b["sha256"],
                          "source_bytes": a["bytes"], "candidate_bytes": b["bytes"]}
            changed.append(difference)
            endpoints = (a["sha256"], a["bytes"], b["sha256"], b["bytes"])
            if allowed_content_changes.get(path) == endpoints:
                accepted_contents.append(difference)
            else:
                content_errors.append(difference)
        if a["mode"] != b["mode"]:
            difference = {"path": path, "source_mode": a["mode"], "candidate_mode": b["mode"]}
            if allowed_mode_changes.get(path) == (a["mode"], b["mode"]):
                accepted_modes.append(difference)
            else:
                mode_errors.append(difference)
    passed = not (missing or unexpected or content_errors or mode_errors)
    return {"status": "PASS" if passed else "FAIL", "source_commit": source.get("commit"),
            "source_tree": source.get("tree"), "candidate_commit": candidate.get("commit"),
            "candidate_tree": candidate.get("tree"), "source_file_count": len(left),
            "candidate_file_count": len(right), "missing_paths": missing, "unexpected_paths": unexpected,
            "changed_contents": changed, "unapproved_content_changes": content_errors,
            "accepted_content_changes": accepted_contents, "unapproved_mode_changes": mode_errors,
            "accepted_mode_changes": accepted_modes, "all_source_blob_contents_preserved": not (missing or unexpected or changed)}


def canonical_origin(url: str) -> str:
    value = url.strip()
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.removeprefix("git@github.com:")
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "ssh"} or parsed.hostname != "github.com" or parsed.password or parsed.query or parsed.fragment:
        raise VerificationError("Origin must identify the intended GitHub repository")
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if len(path.split("/")) != 2 or any(p in {"", ".", ".."} for p in path.split("/")):
        raise VerificationError("Invalid GitHub owner/repository origin")
    return "github.com/" + path.casefold()


def repository_state(repo: str | Path, *, expected_origin: str, expected_branch: str | None = None,
                     expected_head: str | None = None, required_ancestor: str | None = None,
                     require_clean_tracked: bool = True) -> dict[str, Any]:
    repo = Path(repo).resolve()
    top = Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != repo:
        raise VerificationError("Repository path is not its top-level directory")
    actual_origin = _git(repo, "remote", "get-url", "origin").decode().strip()
    branch = _git(repo, "branch", "--show-current").decode().strip()
    head = resolve_commit(repo, "HEAD")
    dirty = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=no", "--ignore-submodules=none")
    errors = []
    if canonical_origin(actual_origin) != canonical_origin(expected_origin):
        errors.append("origin_identity_mismatch")
    if expected_branch is not None and branch != expected_branch:
        errors.append("branch_identity_mismatch")
    if expected_head is not None and head != expected_head:
        errors.append("head_identity_mismatch")
    if require_clean_tracked and dirty:
        errors.append("tracked_worktree_or_index_not_clean")
    ancestor_verified = None
    if required_ancestor is not None:
        result = _git(repo, "merge-base", "--is-ancestor", required_ancestor, head, allow_failure=True)
        ancestor_verified = result[0] == 0
        if not ancestor_verified:
            errors.append("required_history_not_preserved")
    return {"status": "PASS" if not errors else "FAIL", "repository": str(repo), "origin": actual_origin,
            "branch": branch, "head": head, "clean_tracked": not bool(dirty),
            "required_ancestor": required_ancestor, "ancestor_verified": ancestor_verified, "errors": errors,
            "untracked_and_ignored_files": "outside this tracked-state check; never deleted by this verifier"}


def working_tree_inventory(repo: str | Path, committed: dict[str, Any]) -> dict[str, Any]:
    root = Path(repo).resolve()
    entries, missing = [], []
    for expected in committed["files"]:
        relative = _path(expected["path"])
        path = root.joinpath(*PurePosixPath(relative).parts)
        if not path.parent.resolve().is_relative_to(root):
            raise VerificationError(f"Tracked parent directory escapes repository: {relative}")
        try:
            info = path.lstat()
        except FileNotFoundError:
            missing.append(relative)
            continue
        if stat.S_ISLNK(info.st_mode):
            # Hash the stored link target, never the external target's contents.
            data = os.fsencode(os.readlink(path))
            mode = "120000"
        elif stat.S_ISREG(info.st_mode):
            data = path.read_bytes()
            mode = "100755" if info.st_mode & stat.S_IXUSR else "100644"
        else:
            raise VerificationError(f"Unsupported tracked filesystem type: {relative}")
        entries.append({"path": relative, "mode": mode, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {"schema_version": 1, "repository": str(root), "commit": "WORKING_TREE", "tree": None,
            "file_count": len(entries), "total_blob_bytes": sum(e["bytes"] for e in entries),
            "missing_paths": missing, "files": entries}


def restoration_scope(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    before = {e["path"]: e for e in current["files"]}
    target = {e["path"]: e for e in baseline["files"]}
    restore, unchanged = [], []
    for path in sorted(target):
        a, b = before.get(path), target[path]
        if a is None or any(a[key] != b[key] for key in ("mode", "sha256", "bytes")):
            restore.append(path)
        else:
            unchanged.append(path)
    return {"status": "READ_ONLY_PLAN", "current_commit": current.get("commit"),
            "current_tree": current.get("tree"), "target_commit": baseline.get("commit"),
            "target_tree": baseline.get("tree"), "restore_baseline_paths": restore,
            "remove_current_tracked_additions": sorted(before.keys() - target.keys()),
            "preserve_unchanged_tracked_paths": unchanged,
            "untracked_or_ignored_files_deleted": False, "references_modified": False,
            "history_requirement": SOURCE_COMMIT + " must remain an ancestor of the restoration commit",
            "scope": "tracked contents only; canonical ignored PDF/build files require separate preservation and rebuilt-source labeling"}


def verify_profile(source_repo: str | Path, candidate_repo: str | Path, profile: str,
                   candidate_revision: str = "HEAD", expected_branch: str | None = None,
                   allow_archived_mode_normalization: bool = False,
                   allow_portability_test_change: bool = False) -> dict[str, Any]:
    if profile not in {"initial", "migrated", "restored"}:
        raise VerificationError("Unknown migration profile")
    if allow_portability_test_change and profile != "migrated":
        raise VerificationError("The pinned portability test change is permitted only for the migrated profile")
    source_revision = SOURCE_COMMIT if profile == "migrated" else BASELINE_COMMIT
    source = committed_inventory(source_repo, source_revision)
    candidate = committed_inventory(candidate_repo, candidate_revision)
    expected_count, expected_source_bytes = (792, 162142808) if profile == "migrated" else (440, 106709049)
    expected_bytes = expected_source_bytes + (PORTABILITY_TEST_BYTE_DELTA if allow_portability_test_change else 0)
    expected_source_tree = SOURCE_TREE if profile == "migrated" else BASELINE_TREE
    guards = []
    if source["tree"] != expected_source_tree or source["file_count"] != expected_count or source["total_blob_bytes"] != expected_source_bytes:
        guards.append("known_source_inventory_mismatch")
    if candidate["file_count"] != expected_count or candidate["total_blob_bytes"] != expected_bytes:
        guards.append("candidate_count_or_byte_total_mismatch")
    if profile == "initial" and (candidate["commit"] != DESTINATION_ROOT or candidate["tree"] != DESTINATION_ROOT_TREE):
        guards.append("destination_root_identity_mismatch")
    allowed_modes = {} if profile == "restored" else {WILEY_CHECKER: ("100755", "100644")}
    if profile == "migrated" and allow_archived_mode_normalization:
        allowed_modes.update({p: ("100755", "100644") for p in ARCHIVED_EXECUTABLES})
    allowed_contents = PORTABILITY_TEST_CHANGE if allow_portability_test_change else {}
    comparison = compare_inventories(source, candidate, allowed_modes, allowed_contents)
    state = repository_state(
        candidate_repo, expected_origin=SOURCE_ORIGIN if profile == "restored" else DESTINATION_ORIGIN,
        expected_branch=expected_branch, required_ancestor=SOURCE_COMMIT if profile == "restored" else DESTINATION_ROOT,
    )
    if profile != "initial" and state["head"] != candidate["commit"]:
        guards.append("candidate_revision_is_not_checked_out_head")
    if profile == "initial":
        parents = _git(candidate_repo, "show", "-s", "--format=%P", DESTINATION_ROOT).decode().strip()
        if parents:
            guards.append("destination_import_is_not_an_independent_root")
    if profile == "restored" and candidate["tree"] != BASELINE_TREE:
        guards.append("restored_tree_is_not_exact_baseline")
    passed = not guards and comparison["status"] == "PASS" and state["status"] == "PASS"
    return {"status": "PASS" if passed else "FAIL", "profile": profile, "guards": guards,
            "comparison": comparison, "repository_state": state,
            "expected_file_count": expected_count, "expected_total_blob_bytes": expected_bytes,
            "expected_source_total_blob_bytes": expected_source_bytes,
            "allowed_mode_changes": {p: list(v) for p, v in allowed_modes.items()},
            "allowed_content_changes": {p: {"source_sha256": v[0], "source_bytes": v[1],
                                            "candidate_sha256": v[2], "candidate_bytes": v[3],
                                            "scope": "test fixture creation only: EXDEV hard-link fallback to copy2"}
                                        for p, v in allowed_contents.items()},
            "references_or_working_files_modified": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inv = commands.add_parser("inventory")
    inv.add_argument("--repo", required=True)
    inv.add_argument("--revision", default="HEAD")
    compare = commands.add_parser("compare")
    compare.add_argument("--source-repo", required=True)
    compare.add_argument("--candidate-repo", required=True)
    compare.add_argument("--profile", choices=["initial", "migrated", "restored"], required=True)
    compare.add_argument("--candidate-revision", default="HEAD")
    compare.add_argument("--expected-branch")
    compare.add_argument("--allow-archived-mode-normalization", action="store_true")
    compare.add_argument("--allow-portability-test-change", action="store_true",
                         help="accept only the pinned test-only EXDEV repair, migrated profile only")
    state = commands.add_parser("state")
    state.add_argument("--repo", required=True)
    state.add_argument("--expected-origin", required=True)
    state.add_argument("--expected-branch", default="main")
    state.add_argument("--expected-head")
    state.add_argument("--required-ancestor")
    work = commands.add_parser("working-tree")
    work.add_argument("--repo", required=True)
    work.add_argument("--revision", default="HEAD")
    restore = commands.add_parser("restoration-scope")
    restore.add_argument("--repo", required=True)
    restore.add_argument("--current", default=SOURCE_COMMIT)
    restore.add_argument("--baseline", default=BASELINE_COMMIT)
    args = parser.parse_args(argv)
    try:
        if args.command == "inventory":
            result = committed_inventory(args.repo, args.revision)
        elif args.command == "compare":
            result = verify_profile(args.source_repo, args.candidate_repo, args.profile,
                                    args.candidate_revision, args.expected_branch, args.allow_archived_mode_normalization,
                                    args.allow_portability_test_change)
        elif args.command == "state":
            result = repository_state(args.repo, expected_origin=args.expected_origin, expected_branch=args.expected_branch,
                                      expected_head=args.expected_head, required_ancestor=args.required_ancestor)
        elif args.command == "working-tree":
            committed = committed_inventory(args.repo, args.revision)
            working = working_tree_inventory(args.repo, committed)
            result = compare_inventories(committed, working)
        else:
            result = restoration_scope(committed_inventory(args.repo, args.current), committed_inventory(args.repo, args.baseline))
        print(json.dumps(result, indent=2, sort_keys=True))
        return int(result.get("status") == "FAIL")
    except (VerificationError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc), "references_or_working_files_modified": False}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
