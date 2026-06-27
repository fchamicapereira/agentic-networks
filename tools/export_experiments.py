#!/usr/bin/env python3
"""Export experiment artifacts into a flat per-experiment directory layout.

For every experiment found under the logs directory (identified by its
``*-final-report.md`` file), this creates one folder in the target directory
named after the experiment and populates it with:

  1. ``report.md``        — the experiment's final report (copied verbatim).
  2. ``{host}-prompt.txt`` — the system prompt handed to each host's agent,
                             extracted from that host's ``.log`` file.

The system prompt is recovered from the log because each run prints the full
system prompt as its first logged action ("... INFO  System prompt:"), followed
by the prompt body until the next timestamped log line.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# A normal log entry starts with "HH:MM:SS  LEVEL  ...". The system prompt body
# is everything between the "System prompt:" marker and the next such entry.
LOG_LINE_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\s+[A-Z]+\s")
SYS_PROMPT_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\s+[A-Z]+\s+System prompt:\s?(.*)$")

FINAL_SUFFIX = "-final-report.md"

# Map the non-ASCII characters that show up in agent reports/prompts to plain
# ASCII. Prompts are inserted into the paper verbatim and reports are parsed as
# markdown, so neither tolerates LaTeX commands (\rightarrow etc.) — ASCII is the
# only representation that is safe in both. Anything not listed here is left
# alone and reported via warn_unmapped() so new characters surface loudly.
UNICODE_REPLACEMENTS = {
    "→": "->",    # → rightarrow
    "←": "<-",    # ← leftarrow
    "↔": "<->",   # ↔ leftrightarrow
    "⇒": "=>",    # ⇒ Rightarrow
    "⇐": "<=",    # ⇐ Leftarrow
    "—": "--",    # — em dash
    "–": "-",     # – en dash
    "“": '"',     # " left double quote
    "”": '"',     # " right double quote
    "‘": "'",     # ' left single quote
    "’": "'",     # ' right single quote / apostrophe
    "≤": "<=",    # ≤ leq
    "≥": ">=",    # ≥ geq
    "≠": "!=",    # ≠ neq
    "≈": "~",     # ≈ approx
    "×": "x",     # × times
    "…": "...",   # … ellipsis
    "∈": "in",    # ∈ element of
    "§": "Sec.",  # § section
    "¹": "^1",    # ¹ superscript one
    # Subscript digits (e.g. "AS₁" -> "AS1"). Reports use these as plain
    # identifier suffixes, so map them to bare digits rather than "_1".
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    # Arabic-Indic digits: agents occasionally emit these (e.g. the firewall
    # run's "٩/[...]" red herring). Fold them to the ASCII digits they denote.
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    # Combining enclosing keycap: the trailing half of keycap emoji like
    # "1️⃣" (the preceding VS-16 is stripped above). Drop it, leaving the digit.
    "⃣": "",      # U+20E3 combining enclosing keycap
    "•": "*",     # • bullet
    "✓": "[OK]",  # ✓ check mark
    "✅": "[OK]",  # ✅ white heavy check mark
    "✗": "[X]",   # ✗ ballot x
    "❌": "[X]",   # ❌ cross mark
    "⚠": "[!]",   # ⚠ warning sign
    "️": "",      # variation selector-16 (emoji presentation, invisible)
    "\U0001f6a8": "",  # 🚨 police car light
}

_REPLACE_RE = re.compile("|".join(re.escape(c) for c in UNICODE_REPLACEMENTS))


def sanitize(text: str, source: str) -> str:
    """Replace known non-ASCII characters with ASCII; warn on any others."""
    text = _REPLACE_RE.sub(lambda m: UNICODE_REPLACEMENTS[m.group()], text)
    warn_unmapped(text, source)
    return text


def warn_unmapped(text: str, source: str) -> None:
    """Print a warning for any non-ASCII character left after sanitizing."""
    seen = set()
    for ch in text:
        if ord(ch) > 127 and ch not in seen:
            seen.add(ch)
            print(f"WARNING: unmapped non-ASCII U+{ord(ch):04X} {ch!r} in {source}",
                  file=sys.stderr)


def extract_system_prompt(log_path: Path) -> str | None:
    """Return the system prompt body from a host log, or None if not found."""
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()

    start = None
    inline_remainder = ""
    for i, line in enumerate(lines):
        m = SYS_PROMPT_RE.match(line)
        if m:
            start = i
            inline_remainder = m.group(1)
            break
    if start is None:
        return None

    body: list[str] = []
    if inline_remainder:
        body.append(inline_remainder)
    for line in lines[start + 1:]:
        if LOG_LINE_RE.match(line):
            break
        body.append(line)

    while body and not body[-1].strip():
        body.pop()
    if not body:
        return None
    return "\n".join(body) + "\n"


def discover_experiments(logs_dir: Path) -> dict[str, dict]:
    """Map experiment name -> {dir, final_report, hosts: {host: log_path}}."""
    prefixes_by_dir: dict[Path, list[str]] = defaultdict(list)
    for fr in logs_dir.rglob("*" + FINAL_SUFFIX):
        prefixes_by_dir[fr.parent].append(fr.name[: -len(FINAL_SUFFIX)])

    experiments: dict[str, dict] = {}
    for d, prefixes in prefixes_by_dir.items():
        # Longest-first so a host log is attributed to the most specific
        # experiment when one prefix is itself a prefix of another.
        prefixes_sorted = sorted(prefixes, key=len, reverse=True)
        hosts_by_prefix: dict[str, dict[str, Path]] = defaultdict(dict)
        for log in d.glob("*.log"):
            name = log.name[: -len(".log")]
            for p in prefixes_sorted:
                if name.startswith(p + "-"):
                    hosts_by_prefix[p][name[len(p) + 1:]] = log
                    break

        for p in prefixes:
            if p in experiments:
                print(
                    f"WARNING: duplicate experiment name {p!r} "
                    f"({experiments[p]['dir']} and {d}); keeping the first.",
                    file=sys.stderr,
                )
                continue
            experiments[p] = {
                "dir": d,
                "final_report": d / f"{p}{FINAL_SUFFIX}",
                "hosts": dict(hosts_by_prefix.get(p, {})),
            }
    return experiments


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output_dir", type=Path,
                        help="Directory to populate with one folder per experiment.")
    parser.add_argument("--logs-dir", type=Path,
                        default=Path(__file__).resolve().parent.parent / "logs",
                        help="Logs directory to traverse (default: <repo>/logs).")
    parser.add_argument("--raw", action="store_true",
                        help="Copy reports/prompts verbatim without replacing "
                             "non-ASCII characters with ASCII equivalents.")
    args = parser.parse_args()

    if not args.logs_dir.is_dir():
        print(f"ERROR: logs directory not found: {args.logs_dir}", file=sys.stderr)
        return 1

    experiments = discover_experiments(args.logs_dir)
    if not experiments:
        print(f"No experiments (*{FINAL_SUFFIX}) found under {args.logs_dir}",
              file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)

    total_prompts = 0
    for name in sorted(experiments):
        info = experiments[name]
        dest = args.output_dir / name
        dest.mkdir(parents=True, exist_ok=True)

        if info["final_report"].exists():
            report = info["final_report"].read_text(encoding="utf-8", errors="replace")
            if not args.raw:
                report = sanitize(report, f"{name}/report.md")
            (dest / "report.md").write_text(report, encoding="utf-8")
        else:
            print(f"WARNING: missing final report for {name}", file=sys.stderr)

        n_prompts = 0
        for host, log_path in sorted(info["hosts"].items()):
            prompt = extract_system_prompt(log_path)
            if prompt is None:
                print(f"WARNING: no system prompt in {log_path}", file=sys.stderr)
                continue
            if not args.raw:
                prompt = sanitize(prompt, f"{name}/{host}-prompt.txt")
            (dest / f"{host}-prompt.txt").write_text(prompt, encoding="utf-8")
            n_prompts += 1
            total_prompts += 1

        print(f"{name}: report + {n_prompts} host prompt(s)")

    print(f"\nExported {len(experiments)} experiment(s), "
          f"{total_prompts} prompt(s) to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
