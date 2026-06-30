#!/usr/bin/env python3
"""Find experiment runs affected by the 'reactivated-then-stalled' bug.

Background: a terminated agent used to get exactly one LLM turn per incoming
message, then was forced back to sleep (see network_agent.py history). If that
single turn wasn't enough to finish its response, the agent went silent for the
rest of the run. This scans the per-host logs and flags the runs where that
truncation actually changed behaviour, so only those need re-running.

Classification (per host log, based on its LAST reactivation):
  * stalled         — the wake turn ran tools/commands but never sent a reply,
                      and the agent never acted again. The clearest harm: it was
                      investigating in order to answer, and got cut off before it
                      could (this is the ACM / DNS-stale case). RERUN THESE.
  * reply-truncated — the wake turn did send a reply, but the agent was then cut
                      off before any possible follow-up (verify a fix, etc.).
                      Lower confidence; review/rerun if the scenario needs it.
  * idle-only       — the wake turn only idled (agent chose to do nothing).
                      Harmless — no rerun needed.
  * kept-going      — activity continued after the last reactivation (a healthy
                      multi-turn response, or a run already redone with the fix).

Usage:
    python tools/scan_reactivation_stalls.py            # rerun recommendation
    python tools/scan_reactivation_stalls.py --all      # every tier, per host
"""

import argparse
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REACT = "=== AGENT REACTIVATED ==="
ITER_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\s+\S+\s+--- Iteration \d+/\d+")
CMD_RE = re.compile(r"\sExecuting command:")
OUT_RE = re.compile(r"\s\[msg → ")          # [msg -> X]  (outgoing)
IDLE_RE = re.compile(r"\sIdle —")            # "Idle —"
# Any sign the agent took another turn after its last reactivation.
ACT_RE = re.compile(
    r"\s(\[assistant\]|\[reason\]|Executing command|\[msg →|Idle —|"
    r"=== AGENT TERMINATED|=== AGENT REACTIVATED)"
)

TIER_ORDER = ["stalled", "reply-truncated", "idle-only", "kept-going"]
TIER_DESC = {
    "stalled": "investigated, never replied, then silent",
    "reply-truncated": "replied once, follow-up cut off",
    "idle-only": "woke, idled, harmless",
    "kept-going": "continued after wake (healthy / already fixed)",
}


def classify(lines: list[str]) -> str:
    react = [i for i, l in enumerate(lines) if REACT in l]
    if not react:
        return ""
    last = react[-1]
    if any(ACT_RE.search(l) for l in lines[last + 1:]):
        return "kept-going"
    it = max((i for i in range(last) if ITER_RE.match(lines[i])), default=0)
    block = lines[it:last]
    had_reply = any(OUT_RE.search(l) for l in block)
    had_cmd = any(CMD_RE.search(l) for l in block)
    had_idle = any(IDLE_RE.search(l) for l in block)
    if had_reply:
        return "reply-truncated"
    if had_cmd:
        return "stalled"
    if had_idle:
        return "idle-only"
    return "stalled"  # did something non-idle without replying -> treat as harm


def category_of(log: Path, logs_dir: Path) -> str:
    """Experiment name = the top-level logs subdirectory the log lives under.

    Using the top-level dir (rather than the immediate parent) folds nested
    partial reruns, e.g. logs/as7007/qwq-32b/..., back under 'as7007'.
    """
    rel = log.relative_to(logs_dir).parts
    return rel[0] if len(rel) > 1 else "(root)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--logs-dir", type=Path, default=REPO_ROOT / "logs",
                        help="Logs directory to scan (default: <repo>/logs).")
    parser.add_argument("--all", action="store_true",
                        help="List every host log grouped by tier, not just the "
                             "rerun recommendation.")
    args = parser.parse_args()
    if not args.logs_dir.is_dir():
        print(f"ERROR: logs directory not found: {args.logs_dir}")
        return 1

    today = date.today()
    # (category, run_stem) -> {tier -> [hosts], newest_mtime}
    runs: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"tiers": defaultdict(list), "mtime": 0.0})
    counts: dict[str, int] = defaultdict(int)
    n_logs = 0

    for log in sorted(args.logs_dir.rglob("*.log")):
        tier = classify(log.read_text(encoding="utf-8", errors="replace").splitlines())
        if not tier:
            continue
        n_logs += 1
        counts[tier] += 1
        stem = log.stem.rsplit("-", 1)[0]
        host = log.stem.rsplit("-", 1)[1]
        rec = runs[(category_of(log, args.logs_dir), stem)]
        rec["tiers"][tier].append(host)
        rec["mtime"] = max(rec["mtime"], log.stat().st_mtime)

    print(f"Scanned host logs with a reactivation: {n_logs}\n")
    print("Tier breakdown (by each log's last reactivation):")
    for t in TIER_ORDER:
        print(f"  {t:16} {counts[t]:4}   {TIER_DESC[t]}")
    print()

    if args.all:
        for t in TIER_ORDER:
            print(f"=== {t} — {TIER_DESC[t]} ===")
            for (exp, stem), rec in sorted(runs.items()):
                hosts = rec["tiers"].get(t)
                if hosts:
                    print(f"  {exp}/{stem}: {', '.join(sorted(set(hosts)))}")
            print()
        return 0

    print("=== RERUN — runs with >=1 stalled agent (investigated, never replied) ===")
    rerun = [(k, r) for k, r in runs.items() if r["tiers"].get("stalled")]
    for (exp, stem), rec in sorted(rerun):
        redone = date.fromtimestamp(rec["mtime"]) >= today
        tag = "   [logs updated today — already rerun?]" if redone else ""
        hosts = ", ".join(sorted(set(rec["tiers"]["stalled"])))
        also = rec["tiers"].get("reply-truncated")
        extra = f"  (+reply-truncated: {', '.join(sorted(set(also)))})" if also else ""
        print(f"  {exp}/{stem}\n      stalled: {hosts}{extra}{tag}")
    print(f"\n{len(rerun)} experiment/model run(s) recommended for rerun.")
    secondary = sum(1 for _, r in runs.items()
                    if r["tiers"].get("reply-truncated") and not r["tiers"].get("stalled"))
    print(f"{secondary} more run(s) only have 'reply-truncated' agents "
          f"(lower priority — see --all).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
