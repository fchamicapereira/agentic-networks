# Paper data — Instantiating the Knowledge Plane (HotNets 2026)

**Frozen.** These are the exact runs reported in the paper, copied out of `logs/` so that
re-running an experiment (which writes to the same file names there) can never touch them.
Nothing in this directory is ever regenerated or edited; new runs go elsewhere.

- Source commit: `c317e3935ea807e0ba6b077a56fea9c16c21782d`
- Runs: 5 scenarios × 4 models (Claude Opus 4.7, GPT 5.5, Qwen 2.5 72B (AWQ), GLM 5.2 (FP4)) = 20 runs
- Checksums: `MANIFEST.sha256` covers every file except this README. Verify with
  `python3 tools/verify_paper_snapshot.py` (the website build runs it too).

| Scenario | In the paper | Runs |
|---|---|---|
| Knowledge Plane: university firewall | §3.2 Fault Diagnosis, cause #1 (Figure 1) | `knowledge_plane_university_firewall/` |
| Knowledge Plane: stale DNS | §3.2 Fault Diagnosis, cause #2 (Figure 1) | `knowledge_plane_dns_stale/` |
| Knowledge Plane: overloaded server | §3.2 Fault Diagnosis, cause #3 (Figure 1) | `knowledge_plane_server_overload/` |
| Celer Bridge BGP hijack | §3.3 Reasoning amidst conflicting information (Figure 2) | `celer_bridge/` |
| Billing-aware load balancing | §3.4 Agentic policy-based routing (Figure 3) | `optimizing_billing_policy/` |

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

Made by `tools/make_paper_snapshot.py` (371 files).
