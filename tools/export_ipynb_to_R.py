#!/usr/bin/env python3
"""Export code cells from a Jupyter notebook to a linear R script.

Usage:
  python3 tools/export_ipynb_to_R.py INPUT.ipynb OUTPUT.R
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _comment_markdown(md: str) -> str:
    lines = []
    for line in md.splitlines():
        lines.append("# " + line)
    return "\n".join(lines)


def _comment_magic(line: str) -> str:
    return "# " + line


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python3 tools/export_ipynb_to_R.py INPUT.ipynb OUTPUT.R")
        return 1

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    nb = json.loads(in_path.read_text(encoding="utf-8"))

    pending_md: list[str] = []
    cell_num = 0

    with out_path.open("w", encoding="utf-8") as out:
        out.write("# Auto-generated from %s\n\n" % in_path.name)
        for cell in nb.get("cells", []):
            cell_type = cell.get("cell_type")
            source = "".join(cell.get("source", []))

            if cell_type == "markdown":
                if source.strip():
                    pending_md.append(source)
                continue

            if cell_type != "code":
                continue

            cell_num += 1
            out.write(f"#### CELL {cell_num:03d} ####\n")

            if pending_md:
                for md in pending_md:
                    out.write(_comment_markdown(md))
                    out.write("\n")
                pending_md = []
                out.write("\n")

            for line in source.splitlines():
                if line.lstrip().startswith("%"):
                    out.write(_comment_magic(line) + "\n")
                else:
                    out.write(line + "\n")
            out.write("\n\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
