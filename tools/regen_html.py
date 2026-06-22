#!/usr/bin/env python3
"""
regen_html.py — Re-render all *.html timelines from experiment logs.

Each experiment writes one per-node log named '{run_stem}-{node}.log'. This tool
groups those logs back into experiments and regenerates the corresponding
'{run_stem}.html' timeline, without re-running anything. Useful after changing
the HTML/CSS template in assets/timeline_template.html.

Usage:
    python tools/regen_html.py                  # regenerate every experiment under logs/
    python tools/regen_html.py logs/bribing     # only logs found under these dirs
    python tools/regen_html.py path/to/x.log    # the experiment that these log files belong to
"""

import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from visualize_logs import parse_logs, render_logs


def _group_logs(log_files: list[Path]) -> dict[tuple[Path, str], list[Path]]:
    """Cluster per-node logs into experiments.

    Files of one experiment share the '{run_stem}-{node}.log' pattern, so dropping
    the trailing '-{node}' segment yields the run stem. Files are keyed by
    (parent_dir, run_stem) so identically-named runs in different directories stay
    separate.
    """
    groups: dict[tuple[Path, str], list[Path]] = defaultdict(list)
    for f in log_files:
        run_stem = f.stem.rsplit("-", 1)[0] if "-" in f.stem else f.stem
        groups[(f.parent, run_stem)].append(f)
    return groups


def _collect_log_files(paths: list[Path]) -> list[Path]:
    """Expand the given paths into a flat list of .log files (recursing into dirs)."""
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(p.rglob("*.log"))
        elif p.suffix == ".log":
            files.append(p)
        else:
            print(f"  [skip] {p}: not a directory or .log file")
    return files


def regen(files: list[Path]) -> None:
    files = sorted(files)
    try:
        tl = parse_logs(files)
    except Exception as exc:
        print(f"  [skip] {files[0].parent}: failed to parse logs ({exc})")
        return
    out = files[0].parent / f"{tl.label}.html"
    render_logs(files, output_path=out)
    print(f"  [done] {out}  ({len(tl.hosts)} hosts, {len(tl.epochs)} epochs, {len(tl.links)} messages)")


def main() -> None:
    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        paths = [REPO_ROOT / "logs"]

    log_files = _collect_log_files(paths)
    if not log_files:
        sys.exit("No .log files found.")

    groups = _group_logs(log_files)
    print(f"Regenerating {len(groups)} timeline(s) from {len(log_files)} log file(s)...")
    for (_parent, _run_stem), files in sorted(groups.items()):
        regen(files)


if __name__ == "__main__":
    main()
