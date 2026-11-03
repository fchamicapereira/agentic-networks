#!/usr/bin/env python3
"""narrate.py — Narrate a recorded run with Claude, offline (demo/narrator.py).

Reads a run's event stream (a recording, or a live run's events.jsonl) and writes its captions to
a sidecar: a `narrator` header line (model, effort, and the SHA-256 of the stream it narrated, so
a narration made from an older recording can be recognised), then one `caption` event per line.
Captions are printed as they are made.

    python3 demo/tools/narrate.py _site/demo/recordings/kp_university_firewall__opus-4-7.jsonl
    python3 demo/tools/narrate.py REC.jsonl --dry-run     # the prompt and the beats; no model calls
    python3 demo/tools/narrate.py REC.jsonl --edit-only   # only redo the editing pass, on its narration

After the beats and the outcome, an editing pass over the whole run hides thoughts that only
repeat (demo/narrator.py, EDIT); --edit-only runs just that pass again on an existing narration.

Needs ANTHROPIC_API_KEY (or another credential the Anthropic SDK finds), except with --dry-run.
"""

import argparse
import hashlib
import json
import sys
import time

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "demo"))

import narrator as nr  # noqa: E402

NARRATION_DIR = REPO_ROOT / "demo" / "narration"
# $ per million tokens, Claude Opus 5.5: input, output, cache read, cache write (5 min).
PRICE = {"in": 4.0, "out": 20.0, "cache_read": 0.20, "cache_write": 5.0}


def show(c: dict) -> None:
    t = f"{c['t']:7.1f}s"
    if c["kind"] == "thought":
        mark = " " if c.get("weight") == "key" else "·"
        print(f"{t} {mark} 💭 {c['node']:>9}: {c['text']}")
    elif c["kind"] == "message":
        print(f"{t}   ✉  {c['node']:>9}: {c['text']}")
    elif c["kind"] == "story":
        print(f"{t}   ★  STORY: {c['text']}")
    elif c["kind"] == "outcome":
        print(f"{t}   ■  OUTCOME: {c['headline']}\n             {c['text']}")
    sys.stdout.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recording", type=Path, help="event stream (JSONL)")
    ap.add_argument("-o", "--output", type=Path, help=f"sidecar to write (default: {NARRATION_DIR.relative_to(REPO_ROOT)}/<name>.jsonl)")
    ap.add_argument("--model", default=nr.MODEL)
    ap.add_argument("--effort", default=nr.DEFAULT_EFFORT, choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--no-fallback", action="store_true", help="don't ask the API to retry refused requests on a fallback model")
    ap.add_argument("--dry-run", action="store_true", help="print the system prompt and every beat; call no model")
    ap.add_argument("--no-edit", action="store_true", help="skip the editing pass")
    ap.add_argument("--edit-only", action="store_true", help="run only the editing pass on the existing narration")
    args = ap.parse_args()

    # A recording the build already merged captions into is narrated (and hashed) without them.
    lines = [line for line in args.recording.read_text().split("\n") if line.strip()]
    lines = [line for line in lines if json.loads(line)["type"] not in ("caption", "narrator")]
    events = [json.loads(line) for line in lines]
    source_sha = hashlib.sha256("".join(line + "\n" for line in lines).encode()).hexdigest()
    if not events or events[0]["type"] != "run_start":
        print("error: not an event stream (no run_start first)", file=sys.stderr)
        return 1

    if args.dry_run:
        def factory(run_start, prompts):
            n = nr.Narrator(run_start, prompts, client=None)
            print("=" * 30, "SYSTEM PROMPT", f"({len(n.system)} chars)", "=" * 30)
            print(n.system)
            return n
        _, narrator = nr.narrate(events, factory)
        print("=" * 30, f"{narrator.n} BEATS", "=" * 30)
        for m in narrator.messages:
            if m["role"] == "user":
                print(m["content"], end="\n\n")
        chars = len(narrator.system) + sum(len(m["content"]) for m in narrator.messages if m["role"] == "user")
        print(f"{narrator.n} model calls; ~{chars // 4:,} new input tokens in all (≈ chars/4), "
              "plus the growing history re-read from cache on every call.")
        return 0

    import anthropic

    client = anthropic.Anthropic()
    out = args.output or NARRATION_DIR / args.recording.name
    started = time.monotonic()

    def factory(run_start, prompts):
        return nr.Narrator(run_start, prompts, client=client, model=args.model, effort=args.effort,
                           fallback=not args.no_fallback)

    def show_cuts(hidden):
        print(f"\nEditing pass: hid {len(hidden)} thought(s) that only repeat.")
        for c in hidden:
            print(f"  {c['t']:7.1f}s {c['node']:>9}: {c['text']}\n             (covered by: {c['cut']})")

    if args.edit_only:
        if not out.exists():
            print(f"error: no narration to edit at {out}", file=sys.stderr)
            return 1
        header, *captions = [json.loads(line) for line in out.read_text().split("\n") if line.strip()]
        if header.get("source_sha256") != source_sha:
            print(f"error: {out} narrates another version of this recording; narrate it again", file=sys.stderr)
            return 1
        prompts = {e["node"]: e["text"] for e in events if e["type"] == "prompt"}
        narrator = factory(events[0], prompts)
        show_cuts(narrator.edit(captions))
    else:
        captions, narrator = nr.narrate(events, factory, on_caption=show)
        if not args.no_edit:
            show_cuts(narrator.edit(captions))
        header = {"type": "narrator", "v": 1, "model": args.model, "effort": args.effort,
                  "source": args.recording.name, "source_sha256": source_sha}
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for ev in [header, *captions]:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    u = narrator.usage
    usd = sum(u[k] * PRICE[k] for k in PRICE) / 1e6
    what = "edited" if args.edit_only else f"from {narrator.n} beats"
    print(f"\n{len(captions)} captions {what} in {time.monotonic() - started:.0f}s "
          f"({u['calls']} calls; tokens in {u['in']:,}, cache read {u['cache_read']:,}, "
          f"cache write {u['cache_write']:,}, out {u['out']:,}; ≈ ${usd:.2f}) → {out}")
    if args.edit_only:
        return 0
    print(f"{narrator.retries} replies broke a style rule and were asked again", end="")
    print(":" if narrator.unfixed else "; all fixed.")
    for p in narrator.unfixed:
        print(f"  still: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
