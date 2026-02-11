#!/usr/bin/env python3
"""
Compare current outputs vs canonical outputs by filename.
Supports hash mode and pixel mode for images.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_hashes(dir_path: Path, out_path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    entries: List[Tuple[str, str]] = []
    if dir_path.exists():
        for p in sorted(dir_path.glob("*")):
            if p.is_file():
                h = sha256_file(p)
                out[p.name] = h
                entries.append((h, p.name))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join([f"{h}  {name}" for h, name in entries]) + "\n", encoding="utf-8")
    return out


def parse_hash_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        h = parts[0]
        name = Path(parts[1]).name
        out[name] = h
    return out


def png_dimensions(path: Path) -> Optional[Tuple[int, int]]:
    try:
        with path.open("rb") as f:
            sig = f.read(8)
            if sig != b"\x89PNG\r\n\x1a\n":
                return None
            f.read(4)
            chunk_type = f.read(4)
            if chunk_type != b"IHDR":
                return None
            data = f.read(8)
            w = int.from_bytes(data[0:4], "big")
            h = int.from_bytes(data[4:8], "big")
            return w, h
    except Exception:
        return None


def file_size(path: Path) -> Optional[int]:
    try:
        return path.stat().st_size
    except Exception:
        return None


def try_pillow() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


def pixel_compare_pillow(a: Path, b: Path) -> Tuple[bool, Tuple[int, int], Dict[str, float]]:
    from PIL import Image, ImageChops, ImageStat

    im1 = Image.open(a).convert("RGB")
    im2 = Image.open(b).convert("RGB")
    if im1.size != im2.size:
        return False, im1.size, {"max_abs": -1.0, "mean_abs": -1.0}
    diff = ImageChops.difference(im1, im2)
    stat = ImageStat.Stat(diff)
    max_abs = max(stat.extrema[0][1], stat.extrema[1][1], stat.extrema[2][1])
    mean_abs = sum(stat.mean) / 3.0
    return max_abs == 0, im1.size, {"max_abs": float(max_abs), "mean_abs": float(mean_abs)}


PIXEL_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"}


def is_pixel_file(path: Path) -> bool:
    return path.suffix.lower() in PIXEL_EXTS


def write_diff_pillow(a: Path, b: Path, out_path: Path) -> None:
    from PIL import Image, ImageChops
    im1 = Image.open(a).convert("RGB")
    im2 = Image.open(b).convert("RGB")
    if im1.size != im2.size:
        return
    diff = ImageChops.difference(im1, im2)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    diff.save(out_path)


def compare_by_filename(canon_dir: Path, curr_dir: Path) -> Tuple[List[str], List[str], List[str]]:
    canon = sorted([p.name for p in canon_dir.glob("*") if p.is_file()]) if canon_dir.exists() else []
    curr = sorted([p.name for p in curr_dir.glob("*") if p.is_file()]) if curr_dir.exists() else []
    canon_set = set(canon)
    curr_set = set(curr)
    missing = sorted(canon_set - curr_set)
    extra = sorted(curr_set - canon_set)
    common = sorted(canon_set & curr_set)
    return missing, extra, common


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="")
    parser.add_argument("--canonical-dir", default="Environmetrics_reproduce")
    parser.add_argument("--current-dir", default="Environmetrics_reproduce_script")
    parser.add_argument("--canonical-sha", default="repro/canonical_Environmetrics_reproduce.sha256")
    parser.add_argument("--current-sha", default="repro/current_Environmetrics_reproduce_script.sha256")
    parser.add_argument("--report", default="repro/compare_report_script_vs_canonical.txt")
    parser.add_argument("--diff-dir", default="repro/diff")
    parser.add_argument("--mode", choices=["hash", "pixel", "both"], default="pixel")
    parser.add_argument("--max-diffs", type=int, default=20)
    parser.add_argument("--generate-diffs", action="store_true")
    args = parser.parse_args()

    root = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = (root / manifest_path).resolve()
        if manifest_path.exists():
            try:
                import yaml  # type: ignore

                manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                manifest = None
            if isinstance(manifest, dict):
                run_root = manifest.get("run_root")
                run_id = manifest.get("run_id")
                if run_root and run_id:
                    if args.current_dir == "Environmetrics_reproduce_script":
                        args.current_dir = str(Path(run_root) / "post" / "outputs" / str(run_id))
                    if args.current_sha == "repro/current_Environmetrics_reproduce_script.sha256":
                        args.current_sha = str(Path(run_root) / "validate" / "current.sha256")
                    if args.report == "repro/compare_report_script_vs_canonical.txt":
                        args.report = str(Path(run_root) / "validate" / "compare_report.txt")
                    if args.diff_dir == "repro/diff":
                        args.diff_dir = str(Path(run_root) / "validate" / "diff")

    canon_dir = (root / args.canonical_dir) if not Path(args.canonical_dir).is_absolute() else Path(args.canonical_dir)
    curr_dir = (root / args.current_dir) if not Path(args.current_dir).is_absolute() else Path(args.current_dir)
    canon_sha_path = (root / args.canonical_sha) if not Path(args.canonical_sha).is_absolute() else Path(args.canonical_sha)
    curr_sha_path = (root / args.current_sha) if not Path(args.current_sha).is_absolute() else Path(args.current_sha)
    report_path = (root / args.report) if not Path(args.report).is_absolute() else Path(args.report)
    diff_dir = (root / args.diff_dir) if not Path(args.diff_dir).is_absolute() else Path(args.diff_dir)

    # compute current hashes regardless (useful for audit)
    curr_hashes = compute_hashes(curr_dir, curr_sha_path)
    canon_hashes = parse_hash_file(canon_sha_path)

    missing, extra, common = compare_by_filename(canon_dir, curr_dir)

    mismatched: List[str] = []
    pixel_mismatched: List[str] = []
    pixel_matched: List[str] = []
    per_file_stats: Dict[str, Dict[str, str]] = {}

    pillow_ok = try_pillow()

    for name in common:
        c_path = canon_dir / name
        s_path = curr_dir / name
        dims_c = png_dimensions(c_path)
        dims_s = png_dimensions(s_path)
        size_c = file_size(c_path)
        size_s = file_size(s_path)

        if args.mode in ("hash", "both"):
            if canon_hashes.get(name) != curr_hashes.get(name):
                mismatched.append(name)

        if args.mode in ("pixel", "both"):
            # Pixel compare is valid only for image files; non-images are hash-only.
            if not (is_pixel_file(c_path) and is_pixel_file(s_path)):
                pass
            elif pillow_ok and c_path.exists() and s_path.exists():
                try:
                    same, dims, stats = pixel_compare_pillow(c_path, s_path)
                except Exception:
                    same = False
                    dims = (-1, -1)
                    stats = {"max_abs": -1.0, "mean_abs": -1.0}
                if same:
                    pixel_matched.append(name)
                else:
                    pixel_mismatched.append(name)
                per_file_stats[name] = {
                    "canonical_dim": str(dims_c),
                    "current_dim": str(dims_s),
                    "canonical_size": str(size_c),
                    "current_size": str(size_s),
                    "max_abs_diff": f"{stats['max_abs']:.3f}",
                    "mean_abs_diff": f"{stats['mean_abs']:.3f}",
                }
            else:
                # no pillow, fallback to hash mismatch as proxy for image files
                if canon_hashes.get(name) != curr_hashes.get(name):
                    pixel_mismatched.append(name)
                per_file_stats[name] = {
                    "canonical_dim": str(dims_c),
                    "current_dim": str(dims_s),
                    "canonical_size": str(size_c),
                    "current_size": str(size_s),
                    "max_abs_diff": "NA",
                    "mean_abs_diff": "NA",
                }

    if args.generate_diffs and pillow_ok:
        for name in pixel_mismatched[: args.max_diffs]:
            c_path = canon_dir / name
            s_path = curr_dir / name
            if c_path.exists() and s_path.exists():
                try:
                    out_path = diff_dir / f"{name}__diff.png"
                    write_diff_pillow(c_path, s_path, out_path)
                except Exception:
                    pass

    matched = len(common) - (len(pixel_mismatched) if args.mode in ("pixel", "both") else len(mismatched))

    lines: List[str] = []
    lines.append("# Script vs Canonical Comparison")
    lines.append("")
    lines.append(f"Canonical dir: {canon_dir}")
    lines.append(f"Current dir: {curr_dir}")
    lines.append(f"Mode: {args.mode}")
    lines.append("")
    lines.append(f"Matched: {matched}")
    lines.append(f"Missing: {len(missing)}")
    lines.append(f"Extra: {len(extra)}")
    lines.append(f"Mismatched: {len(pixel_mismatched) if args.mode in ('pixel','both') else len(mismatched)}")
    lines.append("")

    if missing:
        lines.append("## Missing")
        for name in missing:
            lines.append(f"- {name}")
        lines.append("")
    if extra:
        lines.append("## Extra")
        for name in extra:
            lines.append(f"- {name}")
        lines.append("")

    if args.mode in ("pixel", "both") and pixel_mismatched:
        lines.append("## Pixel Mismatched")
        for name in pixel_mismatched:
            stats = per_file_stats.get(name, {})
            lines.append(f"- {name}")
            lines.append(f"  canonical: dim={stats.get('canonical_dim')} size={stats.get('canonical_size')}")
            lines.append(f"  current:   dim={stats.get('current_dim')} size={stats.get('current_size')}")
            lines.append(f"  diff: max_abs={stats.get('max_abs_diff')} mean_abs={stats.get('mean_abs_diff')}")
        lines.append("")

    if args.mode in ("hash", "both") and mismatched:
        lines.append("## Hash Mismatched")
        for name in mismatched:
            lines.append(f"- {name}")
            lines.append(f"  canonical: {canon_hashes.get(name)}")
            lines.append(f"  current:   {curr_hashes.get(name)}")
        lines.append("")

    if not pillow_ok and args.mode in ("pixel", "both"):
        lines.append("Pillow not available; pixel comparison fell back to hash for mismatches.")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
