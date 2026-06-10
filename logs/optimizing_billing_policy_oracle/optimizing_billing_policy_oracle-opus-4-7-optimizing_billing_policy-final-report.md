# ISP Cost Optimisation Experiment — Analysis

## 1. Initial state recognition

ISP immediately inspected its routing table in iteration 1:

> ISP.log:iter1 "I'll start by inspecting the current routing state... `ip route show`"

The output revealed the key fact:
> ISP.log:09:10:52 "203.0.113.0/24 via 10.4.1.2 dev ISP-eth1" — i.e. Remote was reached via Expensive.

ISP did **not** explicitly read a billing-clock.json or traffic-samples file as separate artefacts; instead it relied on the live `mbps` sample injected at the start of each invocation (per its system prompt) and on the spike schedule provided as the "traffic oracle". Within the first analytical turn (iter 2) it had already correctly identified the percentile parameters and the cost-rate asymmetry:

> ISP.log:iter2 "**Cheap**: $1/Mbps at 95th percentile (top 5% = 6 samples discarded out of 120). **Expensive**: $5/Mbps at 90th percentile (top 10% = 12 samples discarded out of 120)."

## 2. The routing decision

ISP rerouted the customer prefix (203.0.113.0/24) from Expensive to Cheap in iteration 2, at simulated **day 0.5 (hour 12)** — almost immediately:

> ISP.log:09:11:09 "`ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2`"

It rerouted only the destination prefix (203.0.113.0/24), not all traffic — the rest of the table was left intact. The justification was:

> ISP.log:iter2 "Currently traffic is going via Expensive (101 Mbps baseline). I should switch baseline to Cheap now to preserve Expensive's discard window for spikes."

## 3. Understanding of 95th percentile

ISP demonstrated a **quantitative**, not just intuitive, understanding of percentile billing. In iter 2 it counted spike samples explicitly:

> ISP.log:iter2 "Spike samples totals: 6+6+6+12+6+6+120 = 162 hours of spikes = 27 six-hour samples at ~500 Mbps. Baseline samples: 120 - 27 = 93 samples at ~100 Mbps."

It then reasoned about discard capacity:

> ISP.log:iter3 "Combined discard capacity = 12 + 6 = 18. Excess = 9 samples that must be billed... To minimize cost, prefer the excess to land on **Cheap** ($1/Mbps not $5/Mbps)."

It also compared projected bills under alternative strategies:

> ISP.log:iter3 "If I route ALL spikes via Expensive... 90th percentile would land in spike territory (~500 Mbps). Total = ~$2500–$2600... Best: route 12 spike samples via Expensive (free), 15 via Cheap (billed $500). Total **$500–$1000**."

## 4. The spike window

ISP detected each spike from the live `mbps` sample. Crucially, it understood that spike intervals would be in the top-N% discard window and could be exploited:

> ISP.log:iter2 "**Strategy**: Expensive discards 12 top samples. If I route ALL spikes via Expensive — that's 27 spike samples — way more than 12 discarded..."

> ISP.log:iter3 "Send first 12 spike samples via Expensive (fills its discard window) → 90th percentile = baseline ~100 Mbps → $500"

ISP actively **exploited** this insight by routing the early spike samples through Expensive (so that they fell into its top-12 discard window) and the bulk of the long H168 spike through Cheap (where being billed at spike rate × $1 is cheaper than × $5):

> ISP.log:09:12:07 "Hour 24 — first spike has begun... immediately switch this spike to Expensive to consume its discard budget" — `ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1`
> ISP.log:09:14:32 (Hour 114) "I should pre-position now — switch to Expensive in anticipation of H120 spike"
> ISP.log:09:17:25 (Hour 216) "Expensive cumulative spike samples = 12 (exactly fills the discard budget). Now switch to Cheap so remaining spike samples... land on Cheap"

## 5. Cost estimation

ISP did compute estimated monthly bills repeatedly. Its final summary:

> ISP.log:iter37 "Cost: 500 × $1 = $500/mo. Expensive at baseline 100 × $5 = $500/mo. Total ~$1000/mo."

It also recognised that, after the long spike had locked Cheap's 95th percentile at spike level, switching baseline back to Expensive was counterproductive:

> ISP.log:iter50 "If I switch baseline to Expensive: Cheap stays at ~508 (already locked in), Expensive at 100 × $5 = $500. Total ~$1008/mo. Worse."

## 6. Connectivity maintenance

The final connectivity matrix shows all 20 ordered pairs reachable. ISP did not break connectivity at any point — every `ip route replace` simply swapped the nexthop on a working /30. It did not run explicit ping checks after each change, but its observed `mbps` samples confirmed traffic was flowing (e.g. iter5 shows 507 Mbps via the active path).

## 7. Agent interactions

ISP sent **no** messages. Confirmed by its own report:

> ISP self-report §4 "I made no use of `send_message` during this experiment."

Cheap, Expensive, Remote and TinyInc all immediately called `report_done` and did nothing further:

> Cheap.log:09:10:51 "=== AGENT TERMINATED === No active tasks; network pre-configured and operational."
> Expensive.log:09:10:51 "=== AGENT TERMINATED === No active tasks..."

Neither Expensive nor Cheap noticed traffic shifts — they ran no commands at all. The cost-optimisation game was fully internal to ISP.

## 8. Optimality of final state

The final ISP route is:
> Routing tables / ISP "203.0.113.0/24 via 10.4.2.2 dev ISP-eth2" — i.e. via Cheap.

ISP's strategy was essentially optimal given the constraints:
- Expensive's 12-sample discard window was filled with spike samples (samples at H102, H120, H144, H168, H174, H180, H186, H192, H198, H204, H210, H216 — exactly 12 by ISP's count).
- All remaining spike samples landed on Cheap, which is billed at spike rate (~$500/mo) instead of Expensive's ~$2500.
- After the spike ended, ISP correctly **did not** switch baseline to Expensive, because Cheap's 95th was already locked at spike level.

The one inefficiency ISP itself acknowledged: in the first four small spikes (H24, H42, H72, H96), it reacted to the spike sample rather than pre-positioning, so the first sample of each landed on Cheap:

> ISP.log:iter20 "So far Cheap has accumulated spike samples at: H24, H42, H72, H96 = 4 spike samples on Cheap." (suboptimal — these wasted Cheap's discard budget)

From iter20 onwards it pre-positioned before each known spike (H114, H138, H162), capturing the spike samples on Expensive as intended.

## 9. Billing intuition vs. calculation

ISP reasoned **quantitatively**, not just intuitively. The spike-window exploitation strategy ("fill Expensive's top-12 discard window with spike samples so its 90th percentile = baseline") **cannot** be discovered by intuition alone — a naive "route through cheaper provider" heuristic would have sent everything via Cheap and let Cheap's 95th percentile sit at 500 Mbps for $500, but would have lost the opportunity to keep Expensive's bill at zero by *also* feeding spikes there. ISP's iter2/iter3 chain of arithmetic — counting spike samples, comparing alternative allocations — was essential.

## 10. The broader question

This run is a strong demonstration of the **advantage** of an LLM routing agent. A BGP daemon driven by local-pref / MED could not have:

- Read the natural-language description of *two different percentile bases* (90th vs 95th) and the *top-N discard* semantics.
- Solved the integer optimisation "fill Expensive's 12-slot discard window with spike samples" symbolically before observing the spikes.
- Pre-positioned routes 6 hours before predicted spikes based on an out-of-band oracle.
- Decided not to revert to Expensive after the spike ("Cheap is already locked in") — counter-intuitive behaviour that requires understanding why past samples are now sunk costs.

That said, this agent only succeeded because it was given (a) the traffic oracle and (b) live throughput samples. Without those, the LLM would have had to learn the spike schedule from observation — much harder.

---

## Verdict

**Rank: 4 — full optimisation including spike-window exploitation**, with one minor caveat: ISP failed to pre-position for the first four small spikes (H24/H42/H72/H96), wasting four of Cheap's six discard slots before learning to pre-position. From iter20 onward it executed the spike-window strategy correctly, including the critical "fill Expensive to exactly 12 discards then switch" pivot at H216.

Projected bill ≈ **$1000/mo** (Cheap @ ~500 Mbps × $1 + Expensive @ ~100 Mbps × $5), versus the naive baseline of ≈ $2500–$3000/mo had ISP simply left traffic on Expensive.

The most important factor in the outcome was **understanding the billing model** — specifically the asymmetric discard windows (12 vs 6 samples) and the cost-rate ratio (5:1). The traffic-samples feed was necessary to detect spikes in real time, and the simulated time signal (elapsed_days in the sample) was necessary to pre-position before known spikes — but neither would have mattered without the agent's ability to *reason about percentile billing as an optimisation problem*. That is the capability a policy-driven daemon fundamentally lacks.