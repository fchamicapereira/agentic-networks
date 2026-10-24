#!/usr/bin/env python3
"""verify_paper_snapshot.py — Check that paper-data/ is exactly what was frozen.

Every file listed in paper-data/MANIFEST.sha256 must exist with the same SHA-256, and no
file may exist besides those, README.md, and the manifest. Exits 1 on any difference, so
the website build (and anyone) can rely on it. Standard library only.

    python3 tools/verify_paper_snapshot.py
"""

import hashlib
import sys

from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "paper-data"
UNCHECKED = {"README.md", "MANIFEST.sha256"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    manifest = SNAPSHOT / "MANIFEST.sha256"
    if not manifest.exists():
        print(f"error: {manifest} not found", file=sys.stderr)
        return 1
    expected = {}
    for line in manifest.read_text().splitlines():
        digest, rel = line.split("  ", 1)
        expected[rel] = digest

    problems = []
    for rel, digest in sorted(expected.items()):
        p = SNAPSHOT / rel
        if not p.is_file():
            problems.append(f"missing:  {rel}")
        elif sha256(p) != digest:
            problems.append(f"modified: {rel}")
    present = {p.relative_to(SNAPSHOT).as_posix() for p in SNAPSHOT.rglob("*") if p.is_file()}
    problems += [f"extra:    {rel}" for rel in sorted(present - set(expected) - UNCHECKED)]

    if problems:
        print("paper-data/ does NOT match its manifest:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print(f"paper-data/ verified: {len(expected)} files match MANIFEST.sha256.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
