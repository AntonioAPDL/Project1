from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
COMPARE_SCRIPT = REPO_ROOT / "repro" / "compare_to_canonical.py"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def write_sha_file(target_dir: Path, sha_path: Path) -> None:
    lines = []
    for file_path in sorted(target_dir.glob("*")):
        if file_path.is_file():
            lines.append(f"{sha256_file(file_path)}  {file_path.name}")
    sha_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_report(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    return out


class CompareToCanonicalTests(unittest.TestCase):
    def run_compare(
        self,
        *,
        manifest: Path,
        canonical_dir: Path,
        canonical_sha: Path,
        current_sha: Path,
        report: Path,
        current_dir: Path | None = None,
    ) -> dict:
        cmd = [
            "python3",
            str(COMPARE_SCRIPT),
            "--manifest",
            str(manifest),
            "--canonical-dir",
            str(canonical_dir),
            "--canonical-sha",
            str(canonical_sha),
            "--current-sha",
            str(current_sha),
            "--report",
            str(report),
            "--mode",
            "both",
        ]
        if current_dir is not None:
            cmd.extend(["--current-dir", str(current_dir)])
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)
        return parse_report(report)

    def test_manifest_derived_current_dir_keeps_run_id_underscore(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_id = "20260211_120855"
            run_root = base / "runs" / run_id
            current_dir = run_root / "post" / "outputs" / run_id
            canonical_dir = base / "canonical"
            current_dir.mkdir(parents=True, exist_ok=True)
            canonical_dir.mkdir(parents=True, exist_ok=True)
            (current_dir / "a.txt").write_text("same", encoding="utf-8")
            (canonical_dir / "a.txt").write_text("same", encoding="utf-8")

            canonical_sha = base / "canonical.sha256"
            current_sha = base / "current.sha256"
            report = base / "compare_report.txt"
            manifest = base / "run_manifest.yaml"
            write_sha_file(canonical_dir, canonical_sha)
            manifest.write_text(
                "\n".join(
                    [
                        "run_id: 20260211_120855",
                        f"run_root: {run_root}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            summary = self.run_compare(
                manifest=manifest,
                canonical_dir=canonical_dir,
                canonical_sha=canonical_sha,
                current_sha=current_sha,
                report=report,
            )

            self.assertEqual(summary.get("Current dir"), str(current_dir))
            self.assertEqual(summary.get("Matched"), "1")
            self.assertEqual(summary.get("Missing"), "0")
            self.assertEqual(summary.get("Extra"), "0")
            self.assertEqual(summary.get("Mismatched"), "0")

    def test_explicit_current_dir_is_not_overridden_by_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_root = base / "runs" / "any_run"
            explicit_current = base / "explicit_current"
            manifest_current = run_root / "post" / "outputs" / "any_run"
            canonical_dir = base / "canonical"
            explicit_current.mkdir(parents=True, exist_ok=True)
            manifest_current.mkdir(parents=True, exist_ok=True)
            canonical_dir.mkdir(parents=True, exist_ok=True)
            (explicit_current / "a.txt").write_text("same", encoding="utf-8")
            (canonical_dir / "a.txt").write_text("same", encoding="utf-8")
            (manifest_current / "a.txt").write_text("different", encoding="utf-8")

            canonical_sha = base / "canonical.sha256"
            current_sha = base / "current.sha256"
            report = base / "compare_report.txt"
            manifest = base / "run_manifest.yaml"
            write_sha_file(canonical_dir, canonical_sha)
            manifest.write_text(
                "\n".join(
                    [
                        "run_id: any_run",
                        f"run_root: {run_root}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            summary = self.run_compare(
                manifest=manifest,
                canonical_dir=canonical_dir,
                canonical_sha=canonical_sha,
                current_sha=current_sha,
                report=report,
                current_dir=explicit_current,
            )

            self.assertEqual(summary.get("Current dir"), str(explicit_current))
            self.assertEqual(summary.get("Matched"), "1")
            self.assertEqual(summary.get("Missing"), "0")
            self.assertEqual(summary.get("Extra"), "0")
            self.assertEqual(summary.get("Mismatched"), "0")

    def test_self_compare_passes_with_matches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_root = base / "runs" / "self_run"
            current_dir = run_root / "post" / "outputs" / "self_run"
            current_dir.mkdir(parents=True, exist_ok=True)
            (current_dir / "one.txt").write_text("alpha", encoding="utf-8")
            (current_dir / "two.txt").write_text("beta", encoding="utf-8")

            canonical_sha = base / "canonical.sha256"
            current_sha = base / "current.sha256"
            report = base / "compare_report.txt"
            manifest = base / "run_manifest.yaml"
            write_sha_file(current_dir, canonical_sha)
            manifest.write_text(
                "\n".join(
                    [
                        "run_id: self_run",
                        f"run_root: {run_root}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            summary = self.run_compare(
                manifest=manifest,
                canonical_dir=current_dir,
                canonical_sha=canonical_sha,
                current_sha=current_sha,
                report=report,
            )

            matched = int(summary.get("Matched", "0"))
            self.assertGreater(matched, 0)
            self.assertEqual(summary.get("Missing"), "0")
            self.assertEqual(summary.get("Extra"), "0")
            self.assertEqual(summary.get("Mismatched"), "0")


if __name__ == "__main__":
    unittest.main()
