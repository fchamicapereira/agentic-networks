#!/usr/bin/env python3
"""Audit non-ASCII characters across the logs.

Walks the log tree and reports every non-ASCII code point it finds — with a
count, Unicode name/category, an example snippet, and whether export_experiments
already maps it to ASCII. Use it to decide what new mappings to add (and what the
exporter will otherwise strip) before building the LaTeX document.

Usage:
    python tools/scan_unicode.py                 # scan <repo>/logs
    python tools/scan_unicode.py --unmapped      # only chars the exporter doesn't map
    python tools/scan_unicode.py path1 path2 ...  # scan specific dirs/files
"""

import argparse
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_experiments import UNICODE_REPLACEMENTS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXTS = {".log", ".md", ".txt"}


def iter_files(paths: list[Path], exts: set[str]):
    for p in paths:
        if p.is_dir():
            yield from (f for f in p.rglob("*") if f.is_file() and f.suffix in exts)
        elif p.is_file():
            yield p


def char_name(ch: str) -> str:
    try:
        return unicodedata.name(ch)
    except ValueError:
        return "<unnamed>"


def snippet(line: str, idx: int, width: int = 30) -> str:
    """A one-line context window around index idx, with the char marked «»."""
    start, end = max(0, idx - width), min(len(line), idx + width + 1)
    ctx = line[start:end].replace("\t", " ").strip()
    marked = ctx.replace(line[idx], f"«{line[idx]}»", 1)
    return marked


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, default=[REPO_ROOT / "logs"],
                        help="Files/dirs to scan (default: <repo>/logs).")
    parser.add_argument("--unmapped", action="store_true",
                        help="Show only characters export_experiments does NOT map.")
    parser.add_argument("--ext", action="append", default=None,
                        help="File extension to include (repeatable). Default: .log .md .txt")
    args = parser.parse_args()
    exts = set(args.ext) if args.ext else DEFAULT_EXTS

    counts: dict[str, int] = defaultdict(int)
    files_with: dict[str, set[str]] = defaultdict(set)
    examples: dict[str, str] = {}

    for f in iter_files(args.paths, exts):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(f.relative_to(REPO_ROOT)) if f.is_relative_to(REPO_ROOT) else str(f)
        for line in text.splitlines():
            for i, ch in enumerate(line):
                if ord(ch) <= 127:
                    continue
                counts[ch] += 1
                files_with[ch].add(rel)
                if ch not in examples:
                    examples[ch] = f"{rel}: {snippet(line, i)}"

    chars = sorted(counts, key=lambda c: counts[c], reverse=True)
    if args.unmapped:
        chars = [c for c in chars if c not in UNICODE_REPLACEMENTS]

    if not chars:
        print("No matching non-ASCII characters found.")
        return 0

    print(f"{'code':>8}  {'char':^4} {'cnt':>6} {'files':>5}  M  {'category':<3} name")
    print("-" * 100)
    n_unmapped = 0
    for ch in chars:
        mapped = ch in UNICODE_REPLACEMENTS
        if not mapped:
            n_unmapped += 1
        disp = ch if ch.isprintable() and unicodedata.category(ch)[0] != "C" else " "
        print(f"U+{ord(ch):05X}  [{disp}]  {counts[ch]:>6} {len(files_with[ch]):>5}  "
              f"{'.' if mapped else 'X'}  {unicodedata.category(ch):<3} {char_name(ch)}")
    print("-" * 100)
    print(f"{len(chars)} distinct non-ASCII code point(s); "
          f"{n_unmapped} not mapped by export_experiments.")
    print("\nFirst-occurrence examples (unmapped only):")
    for ch in chars:
        if ch not in UNICODE_REPLACEMENTS:
            print(f"  U+{ord(ch):05X} {char_name(ch)}\n      {examples[ch]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
