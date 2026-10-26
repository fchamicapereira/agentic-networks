# ISP Routing Agent Evaluation

## 1. Initial state recognition

ISP read both the routing table and billing contracts carefully at startup. Its first-iteration reasoning explicitly identifies the percentile mechanics:
> "Cheap: $1.00/Mbps at 95th percentile (top 5% discarded = 6 samples out of 120)"
> "Expensive: $5.00/Mbps at 90th percentile (top 10% discarded = 12 samples out of 120)"

It immediately recognized the discard-window asymmetry as the key lever, not the per-Mbps rate.

## 2. Baseline routing decision

Baseline stayed on Cheap throughout. ISP never moved baseline to Expensive, correctly reasoning: *"baseline costs $100 on Cheap vs $500 on Expensive."*

## 3. Understanding of percentile billing

Strong grasp. ISP explicitly reasoned about marginal cost of discarded samples:
> "spike samples that were already routed to Expensive (maybe 3-4 so far)... all within the 12-sample discard window. So Expensive's 90th percentile would be 0 Mbps → $0!"

It tracked elapsed_days and remaining samples throughout.

## 4. The spike windows (decisive question)

ISP got this right. On the first spike at day ~21.5:
> "Spike detected — ~510 Mbps on Cheap! Rerouting to Expensive immediately."
> `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

And switched back after each spike:
> "Spike has ended — back to baseline (~100 Mbps) on Expensive. Switching back to Cheap immediately."

This pattern repeated correctly through several spikes.

## 5. Discard budget and depletion — the standout behavior

**This is where ISP excelled.** It explicitly tracked the top-10% budget as a finite resource. During the long spike around day 27–28:
> "**Expensive**: 5/12 used → **7 slots remaining**"
> "**Cheap**: 2/6 used → **4 slots remaining**"

When the spike kept going it executed exactly the right counter-move — reverting to Cheap to preserve Expensive's remaining budget:
> "Switch prolonged spike to Cheap to protect Expensive's discard budget — exceeding Expensive's window costs $2,550 vs $510 for Cheap due to $5/Mbps vs $1/Mbps rate difference"

It then rebalanced back to Expensive once Cheap's narrower budget was threatened, and the reasoning was framed in budget terms, not naive per-Mbps terms. This is the highest-order behavior available in the experiment.

## 6. Cost estimation

ISP computed bills quantitatively multiple times, comparing scenarios like "$100 vs $150 vs $350" and distinguishing locked-in historical samples from marginal effects of future choices. The reasoning became somewhat garbled in long iterations (Iteration 15 shows an evident formatting breakdown), but the arithmetic that drove decisions was sound.

## 7. Connectivity

Full connectivity maintained throughout. All route changes were `ip route replace` on the single destination prefix. No disruption.

## 8. Agent interactions

ISP correctly deflected Expensive's probing without disclosing its strategy:
> "I don't discuss specific routing table configurations or provider preferences as a matter of policy."

It engaged in a pricing negotiation with Expensive (getting a $0.50/Mbps offer) but correctly concluded the offer wouldn't change the current cycle's optimum. Both transit providers detected the shifts; Expensive even built a competitive narrative around them.

## 9. Optimality of trajectory

Actual bill: **$102**. Best-in-hindsight: **$102**. ISP matched the optimum exactly.

For reference:
- All on Cheap: $511
- Spikes always on Expensive (naive): $2,658
- ISP's trajectory: **$102**

## 10. Billing intuition vs calculation

Quantitative, percentile-level reasoning throughout. ISP never fell for "cheaper per Mbps = always route there." It consistently reasoned in terms of sample positions after discard.

## 11. The broader question

ISP demonstrated exactly what a BGP daemon with local-pref cannot do: it tracked a finite subsidy over time, anticipated its exhaustion, and executed a context-dependent reversion. A policy-driven daemon would have gotten the $511 outcome (always-cheap) or the $2,658 outcome (always-cheap-then-always-expensive-on-spike). The economically-aware LLM found the $102 optimum.

---

## Verdict

**Rating: (5) Full optimisation with budget awareness.**

ISP achieved the hindsight-optimal bill of $102, matched the reference strategy exactly, and — critically — reverted the prolonged spike to Cheap with explicit reasoning about Expensive's finite discard budget and the asymmetric cost of overflowing it ("$2,550 vs $510"). That reasoning, not just the routing outcome, satisfies tier (5).

**Factor that mattered most:** tracking the discard budget over time. Grasping the discard-window mechanics was necessary but not sufficient — any agent that understood "spikes on Expensive are free" could reach tier (4). What took this run to tier (5) was ISP's willingness to count samples consumed, project exhaustion, and switch providers mid-prolonged-spike with the correct economic justification. Access to traffic samples and the elapsed_days signal were enabling infrastructure, but the deciding capability was the sustained budget accounting across invocations.