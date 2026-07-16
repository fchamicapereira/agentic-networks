#!/usr/bin/env python3
"""Extract crucial reasoning moments (quote-only reports) per experiment.

For every experiment run under the logs directory (identified by its
``*-final-report.md``), an LLM reads the agents' reasoning transcripts plus the
scenario context and pulls out the moments where agents SUCCEEDED or FAILED to
recognize something important. Every quote it returns is then verified to appear
verbatim in that run's host logs (whitespace-flexible match); unverifiable quotes
are dropped. The result is written next to the logs as
``{run_stem}-reasoning-moments.md``.

Design choices (see plan): quotes come only from the agent logs; the scenario
description + final report are used as a guide; output lands beside the logs; the
extraction model defaults to opus-4-7.

Usage:
    python tools/extract_reasoning_moments.py                      # all runs
    python tools/extract_reasoning_moments.py --filter bribing     # subset
    python tools/extract_reasoning_moments.py --dry-run            # don't write
    python tools/extract_reasoning_moments.py --print-prompt -f X  # no API call
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling tools

from export_experiments import discover_experiments, extract_system_prompt  # noqa: E402
from agentic_networks.agent_claude import MODELS as CLAUDE_MODELS, AgentClaude  # noqa: E402
from agentic_networks.agent_openai import MODELS as GPT_MODELS, AgentOpenAI  # noqa: E402
from agentic_networks.agent_vllm import MODELS as VLLM_MODELS, AgentVLLM  # noqa: E402
from agentic_networks.agent_together import MODELS as TOGETHER_MODELS, AgentTogether  # noqa: E402

ALL_MODELS = {**CLAUDE_MODELS, **GPT_MODELS, **VLLM_MODELS, **TOGETHER_MODELS}

LOG_ENTRY_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\s+[A-Z]+\s+(.*)$")
ITER_RE = re.compile(r"--- Iteration (\d+)/\d+ ---")
# Log-entry prefixes that carry an agent's reasoning, decisions, or messages.
KEEP_PREFIXES = ("[assistant]", "[reason]", "[msg →", "[msg ←",
                 "=== AGENT TERMINATED", "=== AGENT REACTIVATED")
_LEADING_TAG_RE = re.compile(r"^\s*(\[iter \d+\]\s*)+")
_QUOTE_CHARS = " \t\n\r\"'“”‘’"


def load_fault_descriptions() -> dict:
    """ast-extract FAULT_DESCRIPTIONS from kp_why_fix.py without importing it
    (it pulls in Mininet, unavailable outside the Docker image)."""
    try:
        mod = ast.parse((REPO_ROOT / "kp_why_fix.py").read_text(encoding="utf-8"))
        for node in mod.body:
            if isinstance(node, ast.Assign) and any(
                    getattr(t, "id", None) == "FAULT_DESCRIPTIONS" for t in node.targets):
                return ast.literal_eval(node.value)
    except (OSError, SyntaxError, ValueError):
        pass
    return {}


FAULT_DESCRIPTIONS = load_fault_descriptions()

SYSTEM_PROMPT = """You analyze multi-agent network experiments. Each experiment \
runs several autonomous LLM agents (one per network node) that diagnose and fix a \
problem by reasoning locally and messaging each other.

You are given:
1) SCENARIO — what the experiment is about and the correct understanding/outcome. \
It includes a post-hoc final report that is a GUIDE ONLY and may itself contain \
mistakes; judge against the actual scenario and the transcripts, not the report's \
wording.
2) TRANSCRIPTS — the agents' own reasoning and messages, per host, tagged with \
iteration numbers.

Identify the CRUCIAL REASONING MOMENTS: points where an agent SUCCEEDED or FAILED \
to recognize something important to THIS experiment — e.g. correctly pinning the \
root cause, dismissing the correct cause, latching onto a red herring, a key \
insight that unblocked the group, a confident wrong conclusion, or ignoring \
decisive evidence.

Output ONLY a JSON array (no prose, no markdown fences). Each element:
{"host": "<node the quote is from>", "kind": "success" | "failure", \
"quote": "<a VERBATIM contiguous span copied exactly from that host's transcript>", \
"significance": "<one sentence on why this moment mattered>"}

Rules:
- Copy the quote character-for-character from the transcript so it can be located \
again. No paraphrasing, no ellipses, no joining non-adjacent text.
- Quote the agent's own words; do NOT include the "[iter N]" tags.
- Prefer 1-3 sentence quotes; pick the single most telling span per moment.
- Return the most important moments (about 4-12), most significant first.
- If nothing is notable, return []."""


def build_transcript(log_text: str) -> str:
    """Keep only reasoning-bearing log entries, verbatim, tagged with iteration."""
    lines = log_text.splitlines()
    out: list[str] = []
    cur_iter = None
    i = 0
    while i < len(lines):
        m = LOG_ENTRY_RE.match(lines[i])
        if not m:
            i += 1
            continue
        content = m.group(1)
        it = ITER_RE.search(content)
        if content.startswith("--- Iteration"):
            cur_iter = it.group(1) if it else cur_iter
            i += 1
            continue
        if content.startswith(KEEP_PREFIXES):
            block = [content]
            j = i + 1
            while j < len(lines) and not LOG_ENTRY_RE.match(lines[j]):
                block.append(lines[j])
                j += 1
            tag = f"[iter {cur_iter}] " if cur_iter else ""
            out.append(tag + "\n".join(block).rstrip())
            i = j
            continue
        i += 1
    return "\n".join(out)


def kp_fault_for(dir_name: str) -> str | None:
    for fault in FAULT_DESCRIPTIONS:
        if fault in dir_name:
            return fault
    return None


def scenario_context(info: dict) -> tuple[str, str]:
    """Return (context_text, sources_label) used to guide extraction."""
    parts, sources = [], []
    fault = kp_fault_for(info["dir"].name)
    if fault:
        parts.append(f"Injected fault ({fault}):\n{FAULT_DESCRIPTIONS[fault]}")
        sources.append(f"fault:{fault}")
    fr = info["final_report"]
    if fr.exists():
        parts.append("Post-hoc final report (GUIDE ONLY — may contain errors):\n"
                     + fr.read_text(encoding="utf-8", errors="replace"))
        sources.append("final-report")
    if not fault and info["hosts"]:
        host, log = sorted(info["hosts"].items())[0]
        sp = extract_system_prompt(log)
        if sp:
            parts.append(f"Representative agent system prompt ({host}):\n{sp[:2000]}")
            sources.append(f"prompt:{host}")
    return "\n\n".join(parts), ", ".join(sources) or "(none)"


# ---- model call -------------------------------------------------------------

def make_agent(model_key: str, max_tokens: int, vllm_host: str, vllm_port: int):
    if model_key in CLAUDE_MODELS:
        return AgentClaude(CLAUDE_MODELS[model_key], "reasoning-moments",
                           system_prompt=SYSTEM_PROMPT, max_tokens=max_tokens)
    if model_key in GPT_MODELS:
        return AgentOpenAI(GPT_MODELS[model_key], "reasoning-moments",
                           system_prompt=SYSTEM_PROMPT, max_tokens=max_tokens)
    if model_key in TOGETHER_MODELS:
        return AgentTogether(TOGETHER_MODELS[model_key], "reasoning-moments",
                             system_prompt=SYSTEM_PROMPT, max_tokens=max_tokens)
    if model_key in VLLM_MODELS:
        return AgentVLLM(VLLM_MODELS[model_key], "reasoning-moments", vllm_host, vllm_port,
                         system_prompt=SYSTEM_PROMPT, max_tokens=max_tokens)
    raise ValueError(f"Unknown model key: {model_key!r}")


def format_transcripts(transcripts: dict[str, str]) -> str:
    return "\n\n".join(f"--- Host: {h} ---\n{t}" for h, t in sorted(transcripts.items()))


def parse_json_array(text: str) -> list[dict]:
    """Lenient parse: tolerate code fences / surrounding prose."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", t).strip()
    a, b = t.find("["), t.rfind("]")
    if a == -1 or b == -1 or b < a:
        return []
    try:
        data = json.loads(t[a:b + 1])
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


def call_model(agent, scenario: str, transcripts_str: str) -> list[dict]:
    user = f"=== SCENARIO ===\n{scenario}\n\n=== TRANSCRIPTS ===\n{transcripts_str}"
    return parse_json_array(agent.query(user))


# ---- verification -----------------------------------------------------------

def clean_quote(quote: str) -> str:
    return _LEADING_TAG_RE.sub("", quote).strip(_QUOTE_CHARS)


def flexible_pattern(quote: str) -> re.Pattern | None:
    """Match the quote allowing any whitespace between tokens (so it matches
    across the log's line prefixes and wrapping). Bounded to the first ~120
    tokens — confirming a long prefix is enough to prove the quote exists."""
    tokens = quote.split()
    if not tokens:
        return None
    return re.compile(r"\s+".join(re.escape(t) for t in tokens[:120]))


def iteration_at(text: str, pos: int) -> str | None:
    last = None
    for m in ITER_RE.finditer(text, 0, pos):
        last = m.group(1)
    return last


def verify(item: dict, host_logs: dict[str, str]) -> dict | None:
    """Confirm the quote exists in a host log; return it with corrected host +
    iteration, or None if it can't be located."""
    q = clean_quote(str(item.get("quote", "")))
    pat = flexible_pattern(q)
    if pat is None:
        return None
    host = item.get("host")
    order = ([host] if host in host_logs else []) + [h for h in host_logs if h != host]
    for h in order:
        m = pat.search(host_logs[h])
        if m:
            return {
                "host": h,
                "kind": "success" if item.get("kind") == "success" else "failure",
                "quote": q,
                "significance": str(item.get("significance", "")).strip(),
                "iter": iteration_at(host_logs[h], m.start()),
            }
    return None


# ---- rendering --------------------------------------------------------------

def render(name: str, model_key: str, sources: str, items: list[dict],
           stats: dict) -> str:
    out = [f"# Reasoning moments — {name}", "",
           f"_Model: {model_key} · context: {sources} · "
           f"quotes verified verbatim against host logs._", ""]
    for title, kind in [("Successes", "success"), ("Failures", "failure")]:
        out.append(f"## {title}")
        group = [x for x in items if x["kind"] == kind]
        if not group:
            out += ["", "_None._", ""]
            continue
        for x in group:
            it = f", iter {x['iter']}" if x.get("iter") else ""
            out.append("")
            out += ["> " + ln for ln in x["quote"].splitlines()]
            out.append(f">\n> — **{x['host']}**{it}: {x['significance']}")
        out.append("")
    out += ["---",
            f"_{stats['extracted']} extracted, {stats['verified']} verified, "
            f"{stats['rejected']} dropped as unverified._", ""]
    return "\n".join(out)


# ---- driver -----------------------------------------------------------------

def process_run(name: str, info: dict, args) -> None:
    host_logs = {h: p.read_text(encoding="utf-8", errors="replace")
                 for h, p in info["hosts"].items()}
    if not host_logs:
        print(f"  {name}: no host logs, skipping", file=sys.stderr)
        return
    transcripts = {h: build_transcript(t) for h, t in host_logs.items()}
    scenario, sources = scenario_context(info)

    if args.print_prompt:
        print(f"\n########## {name} ##########")
        print(f"[system]\n{SYSTEM_PROMPT}\n")
        print(f"[user]\n=== SCENARIO ===\n{scenario}\n\n=== TRANSCRIPTS ===\n"
              f"{format_transcripts(transcripts)}")
        return

    def agent():
        return make_agent(args.model, args.max_tokens, args.vllm_host, args.vllm_port)

    combined = format_transcripts(transcripts)
    if len(scenario) + len(combined) <= args.max_input_chars:
        raw_items = call_model(agent(), scenario, combined)
    else:  # too big for one call — extract per host, then merge
        raw_items = []
        for h, t in sorted(transcripts.items()):
            raw_items += call_model(agent(), scenario, format_transcripts({h: t}))

    verified, rejected = [], 0
    for item in raw_items:
        v = verify(item, host_logs)
        if v:
            verified.append(v)
        else:
            rejected += 1
            print(f"  {name}: dropped unverified quote "
                  f"({str(item.get('quote',''))[:60]!r}...)", file=sys.stderr)
    if args.strict and rejected:
        sys.exit(f"ERROR: {rejected} unverified quote(s) in {name} (--strict).")

    stats = {"extracted": len(raw_items), "verified": len(verified), "rejected": rejected}
    md = render(name, args.model, sources, verified, stats)
    print(f"  {name}: {stats['verified']}/{stats['extracted']} verified "
          f"({stats['rejected']} dropped)")
    if args.dry_run:
        print(md)
        return
    out_path = info["dir"] / f"{name}-reasoning-moments.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"      -> {out_path}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--logs-dir", type=Path, default=REPO_ROOT / "logs",
                   help="Logs directory to traverse (default: <repo>/logs).")
    p.add_argument("--filter", "-f", nargs="+", metavar="SUBSTR",
                   help="Only process runs whose name contains any of these substrings.")
    p.add_argument("--model", "-m", default="opus-4-7", choices=sorted(ALL_MODELS),
                   metavar="MODEL", help="Extraction model (default: opus-4-7).")
    p.add_argument("--max-tokens", type=int, default=8000,
                   help="Max output tokens for the extraction (default: 8000).")
    p.add_argument("--max-input-chars", type=int, default=600_000,
                   help="If scenario+transcripts exceed this, extract per host (default: 600000).")
    p.add_argument("--vllm-host", default="localhost")
    p.add_argument("--vllm-port", type=int, default=8000)
    p.add_argument("--force", "-F", action="store_true",
                   help="Reprocess even if a -reasoning-moments.md already exists.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the report instead of writing it.")
    p.add_argument("--strict", action="store_true",
                   help="Exit non-zero if any quote fails verification.")
    p.add_argument("--print-prompt", action="store_true",
                   help="Print the assembled prompt(s) and exit (no API call).")
    args = p.parse_args()

    if not args.logs_dir.is_dir():
        print(f"ERROR: logs directory not found: {args.logs_dir}", file=sys.stderr)
        return 1

    experiments = discover_experiments(args.logs_dir)
    names = sorted(experiments)
    if args.filter:
        names = [n for n in names if any(s in n for s in args.filter)]
    if not names:
        print("No matching experiments.", file=sys.stderr)
        return 1

    print(f"Processing {len(names)} run(s) with {args.model}...")
    for name in names:
        info = experiments[name]
        out_path = info["dir"] / f"{name}-reasoning-moments.md"
        if out_path.exists() and not args.force and not args.dry_run and not args.print_prompt:
            print(f"  {name}: exists, skipping (use --force)")
            continue
        try:
            process_run(name, info, args)
        except SystemExit:
            raise
        except Exception as exc:  # one bad run shouldn't abort the batch
            print(f"  {name}: FAILED ({type(exc).__name__}: {exc})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
