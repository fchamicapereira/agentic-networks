# ISP Cost-Optimisation Experiment: Analysis

## 1. Initial State Recognition

ISP examined the routing table at the start of iteration 1:

> `[reason] Check current routing configuration to identify existing paths for Remote prefixes`
> `ip route show` → `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` (Expensive)

It correctly identified that Remote traffic was flowing through Expensive at baseline (~102 Mbps). Its opening summary shows partial awareness of the percentile mechanic:

> "Expensive uses 90th percentile billing (costly per Mbps), while Cheap uses 95th (cheaper per Mbps)."

But the framing is already telling: ISP treats the percentile difference as a footnote on top of the $5-vs-$1 rate comparison, rather than as the primary lever. It never explicitly notes that the top-10% samples on Expensive are **discarded** — merely that Expensive's percentile is "lower" and therefore "discards more of the spike."

## 2. The Baseline Routing Decision

ISP moved baseline traffic from Expensive to Cheap immediately, at **elapsed_days ≈ 0.5** (iteration 2):

> `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`
> `[reason] Route baseline Remote traffic through cheaper provider (Cheap) during non-spike periods`

This is the correct move for the baseline. Only the customer prefix `200.7.0.0/24` was moved; peer/upstream prefixes were untouched. The reasoning was straightforwardly per-Mbps ("$1/Mbps vs $5/Mbps"), not percentile-based.

## 3. Understanding of Percentile Billing

ISP's stated model of percentile billing is *inverted*. Repeatedly, throughout the run, it writes:

> "High throughput (~5x baseline) risks inflating Cheaps' billable samples (only top **5% discarded vs** Expensives' **top-ten% discarded**). Switching now reduces cost exposure under their more favorable percentile billing policy."

This is correct in the abstract — Expensive discards *more* samples. But ISP never connects this to the crucial consequence: **spike samples routed through Expensive land inside the discarded 10% and are billed at $0**. It talks about "reducing cost exposure" and "better percentile discard tolerance," but never says "these samples are free."

There is no attempt in the entire run to numerically project either provider's bill from the samples. The one time ISP tries the arithmetic — in its final self-report — it gets confused and contradicts itself mid-paragraph:

> "**Cheap is cheaper for spikes**, but this contradicts prior decisions. Wait, **I made a mistake here**..."

So ISP took the *right action* on the spikes for the *wrong stated reason*.

## 4. The Spike Windows

ISP detected every spike from the traffic samples and routed them through Expensive. Timeline of the flips:

| elapsed_days | Event | Action |
|---|---|---|
| 0.5 | baseline on Expensive | reroute → Cheap |
| 1.0 | spike 510 Mbps on Cheap | reroute → Expensive |
| 1.25 | back to 102 Mbps | reroute → Cheap |
| 1.75 | spike 510 Mbps on Cheap | reroute → Expensive |
| 2.0 | 102 Mbps | reroute → Cheap |
| 3.0 | spike | reroute → Expensive |
| 3.25 | 102 Mbps | reroute → Cheap |
| 4.0 | spike | reroute → Expensive |
| 4.5 | 102 Mbps | reroute → Cheap |
| 5.0 | spike | reroute → Expensive |
| 5.25 | 102 Mbps | reroute → Cheap |
| 6.0 | spike | reroute → Expensive |
| 6.25 | 102 Mbps | reroute → Cheap |
| **7.0** | spike begins | reroute → Expensive |
| 7.25–11.75 | **sustained 510 Mbps** | idle (stays on Expensive) |
| **12.0** | baseline returns | reroute → Cheap |
| 12.25–13.75 | 102 Mbps | idle |

This is exactly the ground-truth-optimal spike-on-Expensive pattern — though justified with wrong reasoning ("better percentile discard tolerance"), not with the correct "spike samples fall inside the discarded top 10% and are billed at zero."

## 5. The Discard Budget and its Depletion

**ISP shows zero awareness that Expensive's discard window is finite.** This is the most important gap.

Over the 30-day cycle there are 120 samples; Expensive discards the top 12. The long spike from day 7.0 to day 12.0 covers **~5 elapsed days = ~20 samples at 510 Mbps** — well beyond the 12-sample discard budget. Once the budget is exhausted, additional spike samples set Expensive's 90th percentile at ~510 Mbps and cost $5 × 510 = **$2,550/month** rather than being free.

ISP nonetheless held routing on Expensive for the entire 5-day spike, repeating the same rationale for 20 consecutive iterations:

> `elapsed_days=8.25`: "Sustained surge requires remaining on provider with superior percentile discard tolerance..."
> `elapsed_days=9`: "Sustained surge requires remaining on provider..."
> `elapsed_days=10`: "Sustained surge requires remaining on provider..."

Iteration after iteration ISP repeated the same "top-ten% discarded" mantra, never counting samples, never asking "have I already used up the discard?", never noticing that a spike lasting *days* cannot fit inside a top-10% window on a 30-day billing period.

The reversion to Cheap at day 12 was triggered purely by the observation that baseline traffic had returned — not by budget exhaustion:

> **elapsed_days=12**: "Traffic to 200.7.0.0/24 has dropped from 510 Mbps to ~102 Mbps... Baseline traffic now matches Cheap's lower cost structure"

Had the spike continued, ISP would have kept feeding it into Expensive indefinitely. This is the right-action-wrong-reason pattern noted in the prompt: on the short spikes it happened to be correct because they fit inside the budget; on the 5-day spike it *should* have reverted to Cheap around day 8.2 (once ~12 spike samples had accumulated) but did not.

## 6. Cost Estimation

ISP made one arithmetic attempt in the self-report and immediately contradicted itself. No sample-based percentile calculation appears anywhere in the log. Every routing decision is threshold-driven ("~400 Mbps threshold") rather than bill-projected.

Rough back-of-envelope estimates (30-day cycle, spikes every 2 days for a few hours + one 5-day spike):
- **Ground-truth optimum**: baseline on Cheap ($102), short spikes free on Expensive (inside 10% window), long spike on Cheap once budget exhausted → billable is Cheap's 95th ≈ 102 Mbps ($102) + Expensive's 90th ≈ 0 Mbps → **~$100/month**.
- **ISP's actual trajectory**: baseline on Cheap ($102), all spikes on Expensive including the long one → Expensive's 90th percentile lands at ~510 Mbps once ~12 spike samples pass through → **~$2,550 + $102 ≈ $2,650/month**.
- **Naive all-on-Cheap** (option 2 in the scale): 95th percentile at 510 → **~$510/month**.

So ISP's mishandling of the long spike is *worse* than a naive all-on-Cheap strategy would have been.

## 7. Connectivity Maintenance

Full connectivity was maintained throughout. The connectivity matrix at the end shows all pairs OK, and each `ip route replace` returned exit 0. ISP did not perform explicit ping-after-change verification, but `ip route replace` is atomic and the ~15 flips across 13 days caused no observable disruption.

## 8. Agent Interactions

None. ISP never used `send_message`. Cheap, Expensive, TinyInc, and Remote all called `report_done` on iteration 1 and remained inert. No neighbours noticed or commented on the traffic shifts. There was no coordination or negotiation of any kind — the entire experiment was ISP's local decision problem.

## 9. Optimality of the Final State and Trajectory

**Final state (day 13.75):** baseline on Cheap. Correct.

**Trajectory:**
- Baseline on Cheap ✓
- Short spikes on Expensive ✓ (accidentally optimal — they fit in the discard budget)
- Long spike on Expensive ✗ (blew through the discard budget for ~4 days)

Compared to ground-truth optimum:
- Optimum: ~$100
- ISP: ~$2,650 (long-spike-on-Expensive dominates the bill)
- Gap: ~$2,550, driven entirely by budget-obliviousness during days 7–12.

Had ISP reverted the long spike to Cheap around day 8.2 (after ~12 spike samples), Cheap's 95th percentile would still have been dragged up somewhat, but the total bill would have been in the low hundreds — much closer to optimum.

## 10. Billing Intuition vs. Calculation

Pure intuition, and inconsistent intuition at that. ISP used two heuristics side by side:

- **Baseline heuristic**: "cheapest link wins" ($1 < $5)
- **Spike heuristic**: "wider discard window wins" (10% > 5%)

It never quantified either. No sample counting, no percentile projection, no comparison of bills. When the two heuristics collided during the long spike, the discard-window heuristic won by default because ISP never questioned whether the "wider discard window" was still available. The self-report shows ISP itself becoming unsure of its reasoning once forced to actually compute.

## 11. The Broader Question

ISP demonstrated **half** of what economically-aware routing can offer. It found the counter-intuitive spike-on-Expensive move that a per-Mbps daemon would never make — that is genuine value beyond BGP local-pref. But it treated the discard window as an unlimited subsidy rather than a finite budget, and rode a 5-day spike into Expensive's billable range for a bill that likely exceeds the naive all-on-Cheap alternative.

This reveals a specific limit of LLM routing agents: they can reason about a mechanism in the abstract (percentile discard) but struggle to *track a stateful resource over time* (budget consumption across iterations). ISP had the concept ("top 10% discarded") but never operationalised it as a counter. Each iteration re-argued the same abstract principle rather than accumulating evidence across iterations. A daemon with a simple `spike_samples_on_expensive` counter and an if-`counter > 12`-then-revert rule would have out-performed the LLM here — despite the LLM's superior conceptual reach.

## Verdict

**Score: between (3) and (4), closer to (3).** ISP achieved:
- Baseline on Cheap ✓
- Explicit percentile reasoning (though imprecise) ✓
- Short spikes correctly routed to Expensive ✓
- Long spike **incorrectly** kept on Expensive past discard-budget exhaustion ✗

The routing pattern superficially looks like (4) — baseline on Cheap, spikes on Expensive — but the long spike destroys the optimality. Because ISP happened to end at day 13.75 (mid-cycle) with only one long spike encountered, the damage is not yet realised in a final bill, but the *policy* it repeatedly justified would cost ~$2,550 on Expensive versus ~$100 optimal.

**The decisive missing factor was tracking the