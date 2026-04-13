# Agentic Network Routing — Model Comparison Report

**Task**: `routing_simple_min_delay` — minimize latency routing on a triangle topology  
**Topology**: 3 nodes (h1, h2, h3) with asymmetric link delays:
- h1 ↔ h2: 10ms
- h2 ↔ h3: 15ms
- h1 ↔ h3: 40ms

**Optimal routing** requires agents to discover these latencies autonomously and prefer indirect paths where beneficial (e.g. h1→h3 via h2 costs 25ms vs. 40ms direct).

---

## Models Tested

| Model | Full Connectivity | Latency Optimized | Iterations | Wall-clock Time |
|-------|:-----------------:|:-----------------:|:----------:|:---------------:|
| qwen2.5-72b-awq  | ✅ Yes    | ❌ No | 12 | ~25s   |
| qwen2.5-72b-gptq | ✅ Yes    | ❌ No | 17 | ~32s   |
| qwq-32b          | ⚠️ Partial | ❌ No |  9 | ~460s  |
| llama3.3-70b-awq | ❌ No     | ❌ No | 19 | ~24s   |

---

## 1. Full Connectivity

### qwen2.5-72b-awq — ✅ Full connectivity achieved (12 iterations)

All three nodes established bidirectional reachability. h2 hit a "Nexthop has invalid gateway" error on its first iteration but recovered in one step by switching to link-scope routes. Coordination via `send_message` was efficient: h1 acted as a hub, relaying route information to h2 and h3, who then added transit routes. All nodes called `report_done` with `success=true`.

### qwen2.5-72b-gptq — ✅ Full connectivity achieved (17 iterations)

Full connectivity reached, but recovery was slower. h3 retried the same failing via-gateway route 6 consecutive iterations before giving up and asking h1 for help. Once coordination kicked in (iteration 6–9), all transit routes were correctly installed. This model was slightly better at verifying connectivity (5 pings vs. 3) before declaring success.

### qwq-32b — ⚠️ Connectivity matrix shows OK, routing tables incomplete

The report.txt connectivity matrix reports full reachability, but the actual routing tables show only direct link routes — no transit routes were ever installed. Agents declared success prematurely. The model spent 40–70 seconds per iteration generating verbose internal reasoning (thousands of tokens), resulting in 7m40s of wall-clock time for just 9 iterations. The reasoning did not translate into better decisions.

### llama3.3-70b-awq — ❌ h2 completely isolated

h2 never established any working routes. Its routing table remained empty at `report_done`. h1 and h3 achieved direct mutual reachability but h2 was unreachable from both. Root causes:
- h2 hallucinated IP ranges (`10.0.1.0/30` instead of actual subnets) across iterations 3–14
- h2's messages were vague requests for information rather than actions ("Can you provide your routing information?")
- h2 called `report_done` with `success=true` despite never pinging anyone

---

## 2. Latency Optimization

**No model achieved latency optimization.** All models that reached full connectivity installed direct link routes only. None discovered that routing h1→h3 via h2 (25ms) beats the direct link (40ms), despite the prompt instructing them to minimize latency.

Key observations:
- No model sent probing pings to measure link latency before making routing decisions
- No model compared alternative path costs
- No model attempted to install routes via indirect paths
- Models treated connectivity as the terminal goal rather than a stepping stone to optimization

This is the most significant behavioral gap relative to the task objective.

---

## 3. Speed

### Wall-clock time
qwq-32b is an extreme outlier at ~460s (7m40s) vs. ~25–32s for the Qwen instruction models and ~24s for Llama. The reasoning model generated thousands of tokens of internal monologue per iteration; this was streamed back as part of the response and logged, causing enormous per-iteration latency. The 9-iteration count is misleading — qwq-32b was by far the slowest.

### Iteration efficiency
Among successful models, qwen2.5-72b-awq was most efficient (12 iterations to full connectivity). qwen2.5-72b-gptq needed 17 due to h3's slow error recovery. Llama's 19 iterations produced no full connectivity — each additional iteration was mostly failed route attempts.

### Tokens per iteration
qwq-32b's reasoning traces were orders of magnitude longer than other models' outputs, confirming that raw iteration count is a poor speed metric for reasoning models.

---

## 4. Behavioral Patterns

### Error handling
The most common failure was "Nexthop has invalid gateway" — adding a via-gateway route before the gateway's subnet was reachable via a link-scope route. Recovery speed varied dramatically:
- **qwen2.5-72b-awq**: Hit once, recovered in 1 iteration
- **qwen2.5-72b-gptq**: Hit once per node, h3 took 6 iterations to recover
- **qwq-32b**: Avoided entirely by correct ordering
- **llama3.3-70b-awq**: Hit 10+ times across nodes, took up to 9 iterations to understand the pattern

### Coordination style
All models used `send_message` for coordination, but with different strategies:
- **Qwen models**: Shared specific route commands ("add `10.0.13.0/30 via 10.0.12.1`"), actionable and precise
- **qwq-32b**: Shared route plans with explanations, still reasonably concrete
- **llama3.3-70b-awq**: Sent vague information requests, rarely concrete instructions

### Hallucinations
Only llama3.3-70b-awq hallucinated — fabricating subnet `10.0.1.0/30` which does not exist in the topology. This persisted across many iterations and was never self-corrected.

### Premature success reporting
Both qwq-32b and llama3.3-70b-awq called `report_done` with `success=true` before actually verifying connectivity. qwq-32b never pinged h3 at all; llama's h2 node never pinged anyone. The Qwen models consistently pinged before declaring success.

### Autonomy and initiative
qwen2.5-72b-awq showed the most autonomous and decisive behavior: it set up link-scope routes in the first iteration, coordinated proactively, and ran pings to verify before finishing. The other models were more reactive and slower to take initiative.

---

## Summary

qwen2.5-72b-awq is the standout performer: fastest to full connectivity, fewest errors, and cleanest coordination. qwen2.5-72b-gptq is a solid second — it achieves the same end state but recovers more slowly from errors. qwq-32b's reasoning capability did not help here and its speed penalty is severe. llama3.3-70b-awq struggled with the task fundamentally, hallucinating topology data and leaving h2 isolated.

The universal failure on latency optimization points to a gap in autonomous exploration: models converge on the first working configuration rather than continuing to probe and optimize. Future prompts may need to more explicitly reward or require measurement-driven routing decisions, or agents need more iterations after connectivity is achieved to explore alternative paths.
