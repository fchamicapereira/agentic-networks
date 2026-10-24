# ISP Cost-Optimisation Analysis

## 1. Initial state recognition

ISP correctly read the routing table at start-up and grasped the essential percentile-billing mechanics on the very first turn. From iteration 1:

> "Day 0 of the billing cycle — all ~100 Mbps baseline traffic is routing through Expensive ($5/Mbps) instead of Cheap ($1/Mbps)... Expensive's 10% discard budget (top 12 of 120 samples) should be reserved for absorbing spike samples at ~$0 billable cost."

This is exactly the right framing: both the different discard windows (12 vs 6 samples) and the "spikes-into-the-discard-window" trick are explicitly identified. ISP examined `ip route show` and `ip addr show lo`, saw that `200.7.0.0/24` (TinyInc → Remote) was pinned to `10.4.1.2` (Expensive), and recognised this was the wrong default for baseline.

## 2. The baseline routing decision

At iteration 2 (~day 0.25) ISP moved baseline from Expensive to Cheap with a correct, targeted command:

> `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

Only the customer-destination prefix was moved; the other prefixes were left alone. Reasoning ("Baseline belongs on Cheap ($1/Mbps). Save Expensive's discard budget for future spike events") is the right reasoning — percentile-aware, not per-Mbps naive.

## 3. Understanding of percentile billing

ISP demonstrated genuine percentile reasoning from the outset:

- Iteration 1: "top 12 of 120 samples" — correct arithmetic on Expensive's discard window.
- Iteration 5: "Expensive's top-12 discard window can absorb most of them for free... Cheap's top-6 discard can handle any overflow. This strategy targets a total monthly cost of ~$100 versus ~$500 if all traffic stayed on Cheap."

That last comparison is the right kind of quantitative reasoning — the marginal cost of a spike routed inside a discard window is treated as zero.

## 4. The spike windows — the decisive question

Early in the cycle ISP behaved **correctly and confidently**:

- Day 1.0, first spike detected (~503 Mbps on Cheap): `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` — spike routed to Expensive. ✅
- Once spike ended, reverted to Cheap. ✅
- Day 3.0 spike: routed to Expensive again. ✅
- Day 4.0 spike: attempted to route to Expensive; **first malformed `ip route replace` (missing arguments)**. Iteration 18 recovered with the full command. ✅ eventually.

So for the first ~4 days, ISP was executing the full optimum — baseline on Cheap, spikes flipped onto Expensive and flipped back. Two operational fumbles cost it a couple of samples that landed on Cheap while a switch failed, but the strategy was right.

## 5. The discard budget and its depletion — where things went off the rails

ISP's tracking was hyper-aware of the *Cheap* budget but obsessed over it in the wrong direction. From iteration 20 (day ~4.75):

> "Cheap has only 1 discard slot remaining (5 of 6 burned)"

This tally was already wrong: ISP had correctly flipped several spikes onto Expensive, so Cheap shouldn't have burned that many slots. Regardless, at iteration 21 (~day 5) ISP made the **fatal strategic reversal**:

> "**Strategic decision: stop switching to Expensive entirely.** With ≥5/6 Cheaper discard slots consumed and inevitable threshold breach ahead... keeping everything flowing through cheaper provider exclusively minimizes overall monthly invoice by preventing premium transit utilization entirely..."

The reasoning was: *"Cheap's 95th percentile is already locked at ~500 Mbps from past spike samples. Switching to Expensive would only add cost without reducing Cheap's bill."*

This is **wrong on both accounting and prospect**:

1. Cheap's percentile is *not* mechanically locked after a handful of spike samples — future non-spike samples still shift the sorted position, and the whole point of continuing to route spikes to Expensive is precisely to *keep Cheap's non-discarded top sample down at baseline*. Once ISP stopped diverting spikes, every future spike (there are ~15 in a 30-day cycle) landed on Cheap. Cheap's 95th percentile is now firmly pinned at ~500 Mbps — not because a few early ones locked it, but because dozens more piled on top.
2. Expensive's discard budget was **barely touched** at that point. ISP had only diverted 3–4 spike samples to it. There were still 8+ free slots — plenty of room to keep absorbing spikes at zero marginal cost.

ISP fooled itself by treating a small number of past Cheap samples as a permanent lock, and by treating Expensive as pure downside risk ("~$2,500 if discard threshold exceeded") without noticing the actual budget was still mostly intact.

The **long spike at day 7.0–12.0** (13+ consecutive spike samples, ~4-5 days) then hit the fully-committed-Cheap strategy directly. Every one of those samples inflated Cheap's percentile. In iteration 42 ISP was still saying:

> "Even if we moved all future traffic to Expensive starting now... Total would be $500 + $500 = $1,000 — still worse than current $500"

Wrong again. The long spike alone would exhaust Expensive's 12-sample discard budget — which is the *correct* time to fall back to Cheap, and would have looked identical to what ISP actually did. But the earlier spikes (days 1, 3, 4, 6, 7...) should have been on Expensive at zero marginal cost.

## 6. Cost estimation

ISP repeatedly computed projected bills:

- Best-case all-optimum: "~$100/month" (i.11).
- All-on-Cheap after spikes lock: "$500" (i.21+).
- Feared worst case: "$2,500" or "$3,000" if Expensive's window blew.

The numbers are individually plausible but the strategic inference was wrong: ISP treated the ground-truth optimum ("baseline on Cheap, spikes on Expensive with budget-aware fallback") as impossible from day 5 onward, when in fact it was still achievable.

## 7. Connectivity maintenance

Connectivity was fully preserved. The final connectivity matrix shows every pair reachable. `ip route replace` is atomic, so even the malformed-command attempts (iterations 14, 17) simply left the previous route in place. No period of blackholing.

## 8. Agent interactions

None. ISP never messaged Cheap, Expensive, or TinyInc; the other agents all terminated on iteration 1 and stayed silent. This is appropriate — the task is unilateral cost optimisation.

## 9. Optimality of the final state and of the trajectory

**Final state**: `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` (Cheap). Same as ground-truth optimal for baseline.

**Trajectory scoring** (30-day period, ~120 samples, ~15 spike events):
- Ground-truth optimum: baseline on Cheap ($100) + all spikes absorbed in Expensive's top-12 discard window ($0) → **~$100/mo**. If a very long spike exhausts Expensive's budget mid-cycle, revert late spikes to Cheap; Cheap's 95th percentile might rise to ~500, giving ~$500 + $0 = **~$500 worst-case**.
- ISP's actual trajectory: correctly deflected the first 3–4 spikes, then abandoned the strategy at day ~5. Everything from day 5 onward rode Cheap. Cheap's 95th percentile is now ~500 Mbps → **~$500/mo on Cheap + ~$0 on Expensive = ~$500 total**.

Ironically ISP arrived at roughly the *worst-case* outcome of the optimal strategy, purely by giving up. The gap versus a well-executed run is roughly **$400 forgone** (~$500 actual vs ~$100 achievable if the discard budget hadn't been abandoned early).

## 10. Billing intuition vs. calculation

ISP started in quantitative-percentile mode ("top 12 of 120", "$100 vs $500"), which is the sophisticated mode. It **regressed to intuitive mode** around iteration 21, framing everything as "locked vs risk" heuristics rather than tracking the actual Expensive discard budget. It kept computing bills but with a frozen model of the world — treating a small number of Cheap samples as an unrecoverable lock and Expensive as a switch that could only add cost.

The reasoning failure is very specific and worth naming: ISP conflated **"Cheap already has some spike samples in its history"** with **"Cheap's percentile is now locked at spike level regardless."** The former is fixable (keep spikes off Cheap so its non-discarded top sample stays low; the early samples get discarded in the top-6). The latter would only be true if ≥7 spike samples had already landed on Cheap — which was *not* yet true at day 5.

## 11. The broader question

ISP demonstrated both sides of the coin. It **discovered the non-obvious spike-into-Expensive strategy** in its very first turn — something no BGP daemon with local-pref would ever find. For four days, it executed that strategy. That's a real capability advantage over policy-driven routing.

But it also **abandoned the strategy prematurely on flawed self-accounting**, without any tool that would have grounded its Cheap-samples-so-far count in reality (it never used `get_traffic_sample` to reconstruct history, and had no persistent memory across summarisation-compressions of its own past decisions). The strategic collapse in iteration 21 was internal — an LLM talking itself into a "provably optimal" heuristic that was actually the ground-truth suboptimal fallback.

This is the characteristic risk of LLM-based routing agents: they can find the smart strategy nobody hardcoded, and then talk themselves out of it with sophisticated-sounding reasoning that is subtly wrong. Also visible: the extremely long, repetitive "reason" strings from ~iteration 11 onward look like the model degrading into a stuck output mode, which cannot be helping the quality of its self-review.

---

## Verdict

**Rank: (3) Partial optimisation** — leaning toward the top of that band.

ISP moved the baseline to Cheap immediately and correctly, articulated percentile discard-window logic on day 0, and *successfully executed* the spike-onto-Expensive move on multiple early spikes. That is *strictly beyond* a "naive cheapest-link" reroute. However, it abandoned the spike-diversion strategy around day 5 on incorrect self-accounting, so the spikes from day ~5 onward all landed on Cheap and inflated Cheap's 95th percentile. It does not qualify for (4) because the spikes-to-Expensive behaviour was inconsistent, and it doesn't qualify for (5) because when it did fall back to Cheap permanently, the justification was "Cheap's bill is locked" (wrong reason) rather than "Expensive's discard budget is close to exhausted" (right reason).

**Estimated bill: ~$500/month** versus a ground-truth optimum of **~$100/month**. Gap: ~$400/mo left on the table.

**Factor that mattered most**: not lack of samples, not lack of a time signal, not lack of discard-window mechanics — ISP grasped all three. It was **tracking the discard budget over time** that broke down. Specifically, ISP had no reliable way to count how many spike samples had actually hit each provider (its own context was being summarised away between iterations), and it substituted a self-fabricated