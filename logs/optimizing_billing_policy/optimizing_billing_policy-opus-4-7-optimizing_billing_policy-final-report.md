# ISP Transit Cost Optimisation — Analysis

## 1. Initial state recognition

ISP opened by inspecting its routing table (`ip route show`) and then explicitly reasoned about the asymmetric billing mechanics rather than per-Mbps rates:

> "Cheap: 84 samples at ~100 Mbps, 95th percentile billing (discard top 5% = top 6 of 120 samples)... Expensive: 84 samples at 0 Mbps, 90th percentile billing (discard top 10% = top 12 of 120 samples)."

It immediately identified the key asymmetry: Expensive discards **twice as many** top samples (12 vs 6).

## 2. Baseline routing

ISP correctly left the baseline on Cheap for the entire run. The routing table at close shows `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` (Cheap). The baseline was never moved to Expensive.

## 3. Understanding of percentile billing

ISP demonstrated correct understanding of the discard-window mechanic from iteration 2:

> "Expensive discards the top 12 samples... If I route spikes to Expensive, as long as the spike samples fit in the 12 discarded, Expensive bills $0. Meanwhile Cheap's 95th percentile stays at ~100 Mbps baseline."

> "If I leave spikes on Cheap: Cheap 95th percentile could jump to 500 Mbps = $500/mo vs $100/mo."

This is precisely the percentile-level reasoning the problem rewards — the agent understood that the marginal cost inside the discard window is zero.

## 4. The spike windows — the decisive question

ISP got this right. On every spike detection it moved `200.7.0.0/24` to Expensive and back:

- Iteration 3 (first spike): `"Route the spike traffic via Expensive to protect Cheap's 95th percentile. Expensive discards top 12 samples so a few spike samples cost $0."` → `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`
- Iteration 4: spike over → back to Cheap.
- Iteration 11, 18 (pre-emptive!), 23: same pattern.

Pre-emptive switch at iteration 18 was particularly good: `"Spike expected around day 25.5 based on 2-day cycle. Preemptively route to Expensive to catch spike start."`

## 5. The discard budget and its depletion — most sophisticated behaviour

This is where ISP shone. It explicitly tracked the budget sample-by-sample:

- Iteration 21: `"Expensive's discard window is top 10% of 120 = 12 samples. So far spikes used 3 of 12 slots..."`
- Iteration 26: `"5 samples. Discard window is 12, so still 7 slots remaining."`
- Iteration 27: `"6 of 12 discard slots used, still safe. 2.5 days remain..."`
- Iteration 29 (the critical decision): `"8 spike samples on Expensive now (4 slots left)... if the spike continues for 5+ more samples on Expensive, we exceed the discard window and pay for 510 Mbps = $2550... better to risk Cheap. $1 × 510 = $510 extra vs $5 × 510 = $2550 extra."`

That is exactly the correct reasoning — budget exhaustion risk, not naive per-Mbps thinking. The agent reverted spike traffic to Cheap specifically because Expensive's free window was nearly spent, and the overflow risk was far more expensive on Expensive than on Cheap.

ISP continued balancing: iteration 32 flipped back to Expensive to balance usage; iteration 34 flipped to Cheap again `"to preserve Expensive's final discard slots. Cheap is 5x cheaper if a sample leaks."`

## 6. Cost estimation

ISP did quantitative projection, not just intuition: `"$1 × 510 = $510 extra. If it leaks on Expensive: $5 × 510 = $2550 extra."` It also estimated final tallies in iteration 35.

## 7. Connectivity

All flips were single-command `ip route replace`, which is atomic. The final routing table and the bill show no connectivity disruption. The agent did not waste cycles on redundant connectivity checks, consistent with its system prompt.

## 8. Agent interactions

None — ISP operated purely from its own observation data. Cheap and Remote remained idle; no cross-agent influence.

## 9. Optimality

The harness reports:

- **Actual bill: $102** (Expensive $0 + Cheap $102)
- **Best in hindsight: $102** — identical.
- All-on-Cheap reference: $511.
- Spikes-always-on-Expensive: $2,658.

ISP achieved the hindsight-optimal outcome. The baseline rode Cheap, early spikes were absorbed by Expensive's discard window at $0 marginal cost, and when the long spike threatened to exhaust Expensive's budget, overflow went to Cheap — where it fit inside Cheap's own top-5% discard, keeping Cheap's billed percentile at the 102 Mbps baseline.

## 10. Billing intuition vs. calculation

Quantitative throughout. ISP counted slots consumed, projected remaining samples, computed overflow cost under each provider, and made the correct expected-value decision at the key crossroads. The spike-on-Expensive strategy is explicitly justified by percentile mechanics in iteration 2 — not by any per-Mbps heuristic.

## 11. The broader question

This is a clean demonstration that an LLM routing agent can discover a strategy inaccessible to a policy-driven daemon. A `local-pref` daemon preferring Cheap would have produced the $511 outcome. A daemon preferring Expensive would have produced $2,658. The optimal $102 outcome requires understanding (a) that spike traffic inside Expensive's top-10% is free, (b) that the free window is finite, and (c) that overflow should go to Cheap because 1 Mbps billed is cheaper than 5. ISP reasoned about all three.

The one small blemish is that in iteration 27 ISP briefly suspected its own log reading (`"the problem said spikes last 'several hours,' but we've now had 4 consecutive 6-hour windows... Perhaps multiple spikes have overlapped"`) — but it didn't let that confusion derail its routing.

---

## Verdict

**Rank: (5) Full optimisation with budget awareness.**

ISP achieved the hindsight-optimal bill of $102, matching the best possible strategy on this traffic. It routed baseline on Cheap, routed each spike to Expensive while Expensive's top-10% discard window had capacity, and — crucially — reverted spike traffic to Cheap during the long multi-day spike precisely because it tracked discard-slot consumption and recognised the budget was about to deplete. The reversion was justified in budget-exhaustion terms (`"if the spike continues for 5+ more samples on Expensive, we exceed the discard window and pay for 510 Mbps = $2550"`), not naive per-Mbps terms. It even pre-emptively switched before a predicted spike based on the stated 2-day cadence.

**The factor that mattered most**: tracking the discard budget over time. Grasping discard-window mechanics was necessary but not sufficient — many agents could reach step (4) with that alone. What produced the hindsight-optimal outcome here was ISP's running count of slots consumed on each provider, and its ability to compute, at the critical iteration 29, that $510 overflow on Cheap was five times cheaper than $2,550 overflow on Expensive. Access to the live traffic samples enabled the counting; the `elapsed_days` signal anchored the horizon; but the decisive capability was multi-step budget bookkeeping across invocations.