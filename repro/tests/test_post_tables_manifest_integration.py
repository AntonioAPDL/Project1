import csv
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestPostTablesManifestIntegration(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.tmpdir = Path(tempfile.mkdtemp(prefix="post_tables_integ_"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_r(self, expr: str) -> None:
        subprocess.run(
            ["Rscript", "-e", expr],
            cwd=self.repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_tables_manifest_paths_relative_and_stable(self):
        tables_dir = self.tmpdir / "repro" / "runs" / "it_post_tables" / "post" / "outputs" / "it_post_tables" / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)
        tables_dir_s = str(tables_dir).replace("\\", "/")

        r_expr = f"""
        source(file.path('{self.repo_root}', 'R', 'environmetrics', '02_helpers_core.R'))
        out_dir <- '{tables_dir_s}'
        tbl <- data.frame(id=c(2L,1L), val=c(10.5,3.25), tag=c('b','a'), stringsAsFactors=FALSE)
        m <- post_export_tables(
          tables=list(example=tbl),
          output_dir=out_dir,
          formats=c('csv','rds'),
          keep_na=TRUE,
          sort_keys=list(example=c('id'))
        )
        post_write_table_exports_manifest(m, output_dir=out_dir)
        """

        self._run_r(r_expr)

        self.assertTrue(tables_dir.exists())
        produced = [p for p in tables_dir.iterdir() if p.is_file()]
        self.assertTrue(produced)

        manifest_path = tables_dir / "posterior_table_exports_manifest.csv"
        self.assertTrue(manifest_path.exists())

        first_manifest_bytes = manifest_path.read_bytes()

        with manifest_path.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        self.assertGreaterEqual(len(rows), 2)
        for row in rows:
            rel = row["file_path"]
            self.assertTrue(rel)
            self.assertFalse(os.path.isabs(rel), msg=f"expected relative path, got: {rel}")
            self.assertFalse(rel.startswith("/"), msg=f"expected non-absolute unix path: {rel}")
            self.assertFalse(re.match(r"^[A-Za-z]:[/\\]", rel or ""), msg=f"expected non-absolute windows path: {rel}")
            self.assertTrue((tables_dir / rel).exists(), msg=f"manifest file_path does not resolve: {rel}")

        # Re-run with the same payload and ensure manifest file remains byte-stable.
        self._run_r(r_expr)
        second_manifest_bytes = manifest_path.read_bytes()
        self.assertEqual(first_manifest_bytes, second_manifest_bytes)

    def test_stage_post_allowlist_and_branch_consistency(self):
        stage_post = (self.repo_root / "R" / "unified" / "stages" / "stage_post.R").read_text(encoding="utf-8")

        # Enforced allowlist in stage_post scanner.
        self.assertIn(r"\\.(png|pdf|csv|tsv|txt|json|yaml|yml|rds)$", stage_post)

        # Ensure no excluded branches are still being captured.
        self.assertNotIn(r"\\.tex$", stage_post)
        self.assertNotIn(r"\\.md$", stage_post)

        # Ensure all allowed extension branches exist.
        for ext in ["png", "pdf", "rds", "csv", "tsv", "json", "yaml|yml", "txt"]:
            if ext == "yaml|yml":
                self.assertIn(r"\\.(yaml|yml)$", stage_post)
            else:
                self.assertIn(fr"\\.{ext}$", stage_post)


if __name__ == "__main__":
    unittest.main()
