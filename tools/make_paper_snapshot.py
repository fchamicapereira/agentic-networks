#!/usr/bin/env python3
"""make_paper_snapshot.py — Freeze the runs reported in the paper into paper-data/.

The paper (HotNets 2026) reports 5 scenarios x 4 models. Re-running an experiment writes
to the same file names under logs/, so the paper's runs are copied, together with the
inputs that produced them, into a separate directory that nothing else writes to:

    paper-data/
      README.md            what this is and how to verify it
      runs.json            the paper's runs: scenario, paper section, model, files
      MANIFEST.sha256      checksum of every file below (verify_paper_snapshot.py)
      logs/<scenario>/     every artifact of each paper run, copied from logs/
      inputs/              prompts, topologies, experiment config and the agent/experiment
                           code as they were when the runs were made

One-shot by design: it refuses to run if paper-data/ already exists, or if any source it
copies has uncommitted changes (the snapshot must match a commit). Standard library only.

    python3 tools/make_paper_snapshot.py
"""

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys

from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "paper-data"

PAPER = "Instantiating the Knowledge Plane (HotNets 2026)"

# The paper's models (§3.1: "We ran all experiments with four models").
MODELS = {
    "opus-4-7": "Claude Opus 4.7",
    "gpt-5.5": "GPT 5.5",
    "qwen2.5-72b-awq": "Qwen 2.5 72B (AWQ)",
    "glm-5.2": "GLM 5.2 (FP4)",
}

# The paper's scenarios (paper_experiments.toml). `stem` is the run stem with {model} filled
# in: every file of a run is named <stem>-<...> or <stem>.<ext> in logs/<dir>/.
SCENARIOS = [
    {"id": "kp_university_firewall", "title": "Knowledge Plane: university firewall",
     "paper": "§3.2 Fault Diagnosis, cause #1 (Figure 1)",
     "dir": "knowledge_plane_university_firewall", "stem": "knowledge_plane-firewall-{model}",
     "topology": "knowledge_plane", "prompts": "knowledge_plane", "script": "kp_why_fix.py"},
    {"id": "kp_dns_stale", "title": "Knowledge Plane: stale DNS",
     "paper": "§3.2 Fault Diagnosis, cause #2 (Figure 1)",
     "dir": "knowledge_plane_dns_stale", "stem": "knowledge_plane-dns_stale-{model}",
     "topology": "knowledge_plane", "prompts": "knowledge_plane", "script": "kp_why_fix.py"},
    {"id": "kp_server_overload", "title": "Knowledge Plane: overloaded server",
     "paper": "§3.2 Fault Diagnosis, cause #3 (Figure 1)",
     "dir": "knowledge_plane_server_overload", "stem": "knowledge_plane-overload-{model}",
     "topology": "knowledge_plane", "prompts": "knowledge_plane", "script": "kp_why_fix.py"},
    {"id": "celer_bridge", "title": "Celer Bridge BGP hijack",
     "paper": "§3.3 Reasoning amidst conflicting information (Figure 2)",
     "dir": "celer_bridge", "stem": "celer_bridge-{model}-celer_bridge",
     "topology": "celer_bridge", "prompts": "celer_bridge", "script": "routing_policies_converged.py"},
    {"id": "optimizing_billing_policy", "title": "Billing-aware load balancing",
     "paper": "§3.4 Agentic policy-based routing (Figure 3)",
     "dir": "optimizing_billing_policy", "stem": "optimizing_billing_policy-{model}-optimizing_billing_policy",
     "topology": "optimizing_billing_policy", "prompts": "optimizing_billing_policy", "script": "billing_policy.py"},
]

# Code that defines what the agents were given: the shared system prompt and tools, and each
# scenario's setup. routing_policies_converged.py runs routing_policies.py.
CODE = ["agentic_networks/network_agent.py", "experiments/kp_why_fix.py",
        "experiments/routing_policies.py", "experiments/routing_policies_converged.py",
        "experiments/billing_policy.py"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.strip()


def topology_nodes(name: str) -> list[str]:
    nodes = []
    for line in (REPO_ROOT / "topologies" / f"{name}.csv").read_text().splitlines():
        if line.startswith("node,"):
            nodes.append(line.split(",")[1])
    return nodes


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if OUT.exists():
        print(f"error: {OUT.relative_to(REPO_ROOT)}/ already exists. The snapshot is frozen; "
              "it is never regenerated in place.", file=sys.stderr)
        return 1

    sources = ["logs", "prompts", "topologies", "paper_experiments.toml", *CODE]
    dirty = git("status", "--porcelain", "--", *sources)
    if dirty:
        print("error: uncommitted changes in the snapshot's sources; commit or revert them first:\n"
              + dirty, file=sys.stderr)
        return 1
    commit = git("rev-parse", "HEAD")

    # Collect and check every run before writing anything.
    plan: list[tuple[Path, Path]] = []
    scenarios_out = []
    for sc in SCENARIOS:
        src_dir = REPO_ROOT / "logs" / sc["dir"]
        nodes = topology_nodes(sc["topology"])
        runs = []
        for model, label in MODELS.items():
            stem = sc["stem"].format(model=model)
            files = sorted(f for f in src_dir.iterdir()
                           if f.is_file() and (f.name.startswith(stem + "-") or f.name.startswith(stem + ".")))
            missing = [n for n in nodes if not (src_dir / f"{stem}-{n}.log").exists()]
            if missing:
                print(f"error: {sc['id']} / {model}: no log for {', '.join(missing)}", file=sys.stderr)
                return 1
            rel = [f"logs/{sc['dir']}/{f.name}" for f in files]
            plan += [(f, OUT / r) for f, r in zip(files, rel)]
            runs.append({"model": model, "model_label": label, "stem": stem, "files": rel})
        scenarios_out.append({**{k: sc[k] for k in ("id", "title", "paper", "topology", "prompts", "script")},
                              "logs_dir": f"logs/{sc['dir']}", "nodes": nodes, "runs": runs})

    inputs = sorted({f"prompts/{sc['prompts']}" for sc in SCENARIOS})
    for d in inputs:
        for f in sorted((REPO_ROOT / d).iterdir()):
            plan.append((f, OUT / "inputs" / d / f.name))
    for t in sorted({sc["topology"] for sc in SCENARIOS}):
        plan.append((REPO_ROOT / "topologies" / f"{t}.csv", OUT / "inputs" / "topologies" / f"{t}.csv"))
    plan.append((REPO_ROOT / "paper_experiments.toml", OUT / "inputs" / "paper_experiments.toml"))
    for c in CODE:
        plan.append((REPO_ROOT / c, OUT / "inputs" / "code" / Path(c).name))

    for src, dst in plan:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    (OUT / "runs.json").write_text(json.dumps({
        "paper": PAPER,
        "source_commit": commit,
        "created": date.today().isoformat(),
        "scenarios": scenarios_out,
    }, indent=2) + "\n")

    write_readme(commit, len(plan))

    # Every file except README.md (documentation that may be improved) and the manifest itself.
    data = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in ("README.md", "MANIFEST.sha256"))
    (OUT / "MANIFEST.sha256").write_text(
        "".join(f"{sha256(p)}  {p.relative_to(OUT).as_posix()}\n" for p in data))

    # Read-only on disk: a script or editor that tries to overwrite a file fails loudly.
    for p in data + [OUT / "MANIFEST.sha256"]:
        os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    n_runs = sum(len(s["runs"]) for s in scenarios_out)
    print(f"Snapshot written to {OUT.relative_to(REPO_ROOT)}/: {n_runs} runs, {len(plan)} files copied, "
          f"{len(data)} files in the manifest, source commit {commit[:7]}.")
    return 0


def write_readme(commit: str, n_files: int) -> None:
    rows = "\n".join(f"| {sc['title']} | {sc['paper']} | `{sc['dir']}/` |" for sc in SCENARIOS)
    models = ", ".join(MODELS.values())
    (OUT / "README.md").write_text(f"""# Paper data — {PAPER}

**Frozen.** These are the exact runs reported in the paper, copied out of `logs/` so that
re-running an experiment (which writes to the same file names there) can never touch them.
Nothing in this directory is ever regenerated or edited; new runs go elsewhere.

- Source commit: `{commit}`
- Runs: 5 scenarios × 4 models ({models}) = 20 runs
- Checksums: `MANIFEST.sha256` covers every file except this README. Verify with
  `python3 tools/verify_paper_snapshot.py` (the website build runs it too).

| Scenario | In the paper | Runs |
|---|---|---|
{rows}

## Layout

- `runs.json` — the list above, machine-readable: each scenario's paper section, topology,
  prompts, nodes, and each model's run with all of its files.
- `logs/<scenario>/` — every artifact of each run, as produced: per-agent logs (`*.log`),
  per-agent and final reports (`*-report.md`), timelines (`*.html`), transcripts, routes
  PDFs, and for billing the traffic samples (`*-data.json`) and the paper's Figure 3
  (`*-tput-paper.pdf`).
- `inputs/` — what the agents were given: `prompts/` (per-agent prompts), `topologies/`,
  `paper_experiments.toml`, and `code/` (the shared system prompt and tools in
  `network_agent.py`, and each scenario's experiment script). The same files are in the
  repository at the source commit above.

Made by `tools/make_paper_snapshot.py` ({n_files} files).
""")


if __name__ == "__main__":
    sys.exit(main())
