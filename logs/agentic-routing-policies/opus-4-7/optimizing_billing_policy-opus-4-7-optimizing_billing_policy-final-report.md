# Analysis: ISP Cost Optimisation Experiment

## 1. Initial state recognition

ISP examined both the routing table and billing clock immediately on iteration 1:

> ISP.log:12:13:47 — "I'll start by examining current state and understanding the routing setup."
> ISP.log:12:13:47 — `cat /tmp/billing-clock.json && echo "---" && ip route show`

Output showed `"elapsed_days": 0.0` and `203.0.113.0/24 via 10.4.1.2 dev ISP-eth1` (i.e., via Expensive). ISP correctly identified that the Remote prefix was traversing Expensive at the very start of the billing period.

The billing-clock read confirmed 0% of the period had elapsed — maximum optimisation opportunity. The traffic sample provided in the system prompt header (~100 Mbps baseline via Expensive) was used to characterise current state.

## 2. The routing decision

Yes, ISP rerouted within iteration 2, at `elapsed_days = 0.0`:

> ISP.log:12:14:00 — `ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2`

Only the customer-destination prefix `203.0.113.0/24` (Remote) was rerouted; infrastructure routes (Expensive's 192.0.2.0/24 and Cheap's 198.18.0.0/24) were left untouched. The stated reasoning was that baseline traffic via Cheap is $1/Mbps vs $5/Mbps via Expensive (ISP.log:12:14:00).

## 3. Understanding of 95th percentile

ISP demonstrated explicit, quantitative understanding of percentile billing. From ISP.log:12:14:00:

> "Spikes occur ~15 times in 30 days, each lasting 'several hours' — total spike time could be ~30-45 hours out of 720h = 4-6%, fitting within the 10% discard."
> "If spikes went via Cheap (95th percentile, discards top 5% = 36 hours), spike time might exceed discard window..."
> "Via Expensive, spikes get discarded, billed at baseline 0 × $5 = $0 spike cost."

This is precisely the reasoning needed: convert discard fraction to hours, compare against expected spike duration, and pick the provider whose discard window will absorb the spikes.

ISP did not bother with elapsed-period reasoning after iteration 1 because it correctly noted the period had only just begun — there was no advantage to deferring action.

## 4. The spike window

ISP detected every spike from the live traffic sample and reacted **immediately**. Examples:

> ISP.log:12:14:24 — "Traffic is 355 Mbps via Cheap — this looks like the start of a spike … switch to Expensive immediately so this spike falls into Expensive's larger 10% discard window." → `ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1`
> ISP.log:12:15:22 — "Spike detected on Cheap (~353 Mbps). Switch to Expensive immediately."
> ISP.log:12:16:15, 12:17:08, 12:18:05, 12:18:59 — same pattern.

After each spike, ISP reverted to Cheap as soon as the next sample showed ~100 Mbps:

> ISP.log:12:14:47 — "Traffic is back to baseline (~102 Mbps) on Expensive. Switch back to Cheap…"

This is the **exact spike-window exploitation strategy** the experiment was designed to test. The spike around day 15 referenced in the question corresponds to one of the ~6 spike events ISP rerouted (the agent does not log per-spike elapsed_days, but the cadence ~every two iterations is consistent with the 2-day inter-spike interval stated in the prompt).

## 5. Cost estimation

ISP produced a quantitative cost estimate in its final report:

> ISP report — "Net effect: total bill ≈ $100/month vs. naive single-provider choices of $500/month."
> ISP.log:12:14:00 — "baseline 100 × $1 = $100/month — much cheaper than 100 × $5 = $500/month via Expensive."

The calculation is correct given the assumed traffic model: baseline 100 Mbps × $1 on Cheap (spikes absorbed by 5% discard if rare enough — but ISP correctly chose not to rely on that) plus $0 from Expensive (spikes within its 10% discard).

## 6. Connectivity maintenance

The final connectivity matrix shows full reachability among all five nodes. `ip route replace` is atomic, so each toggle was non-disruptive. ISP did not explicitly run post-change pings, but the matrix and the fact that the live traffic sample reported sensible Mbps numbers on whichever link was active confirm continuous connectivity.

## 7. Agent interactions

No inter-agent messages occurred. Cheap, Expensive, Remote, and TinyInc all called `report_done` at iteration 1 (e.g., Cheap.log:12:13:47, Expensive.log:12:13:47, Remote.log:12:13:46, TinyInc.log:12:13:47) and remained idle. ISP deliberately avoided disclosing strategy to neighbours, as it noted in its report ("I deliberately did not disclose my routing strategy, contract terms, or provider preferences"), consistent with the privacy guidance. Cheap and Expensive therefore had no observability into traffic shifts beyond their own physical link counters (which they never inspected).

## 8. Optimality of final state

Final routing in `ISP` route table: `203.0.113.0/24 via 10.4.2.2 dev ISP-eth2` (Cheap), which is correct for the baseline interval that closed the run. Over the experiment:

- Baseline (~94% of intervals) → Cheap
- Spike (~6% of intervals, 6 spikes observed) → Expensive

This is the globally optimal strategy given the contract structure: Expensive's 10% discard absorbs the spikes for $0, Cheap bills the 95th percentile at the 100 Mbps baseline for $100. Any alternative (all-Cheap, all-Expensive, or any partial-rerouting that doesn't shift spikes specifically to Expensive) yields a strictly higher bill.

## 9. Billing intuition vs. calculation

ISP reasoned **quantitatively**, not merely intuitively. From ISP.log:12:14:00 it computed:

- Discard windows in hours (36h for Cheap, 72h for Expensive)
- Expected total spike duration (30–45h)
- Compared the two to decide where each spike would or would not be billed
- Estimated dollar amounts for both strategies

The spike-exploitation insight ("route the spike through the provider whose discard window is largest") cannot be derived from intuitive "use the cheaper provider" reasoning — it requires understanding that the *top N% intervals are free* and converting that into hours. ISP made exactly this leap, on the first iteration, without observing any spikes first (relying on the prompt's stated pattern, as instructed).

## 10. The broader question

ISP demonstrated the central thesis of LLM-based routing: it discovered a strategy a static policy daemon cannot express. BGP local-pref or AS-path prepending can prefer one provider over another, but cannot dynamically time-shift specific traffic bursts into a billing discard window. ISP did this not by responding to a measured anomaly but by **reasoning about the economic contract structure ahead of time** and acting on the first sample.

Limitations: ISP cannot terminate (per its prompt) so it consumed all 48 iterations and was marked INCOMPLETE — a procedural artefact, not a failure. It also did not attempt to verify that its model of "spike duration ≤ 10% of intervals" actually held by checking historical samples; it trusted the prompt.

---

## Verdict

**Rank: (4) Full optimisation including spike-window exploitation.**

ISP executed the optimal strategy: baseline via Cheap, spikes via Expensive, switched on a per-invocation basis using the live traffic sample. It reasoned quantitatively about both percentile discard windows (95% / 5%, 90% / 10%) converted into hours, compared expected spike duration to those windows, and estimated the resulting bill ($100 vs $500). It performed six clean spike-onset reroutes and six clean spike-end reverts.

The most important factor in the outcome was **understanding the billing model** — specifically the insight that the top-N% discard means the busiest intervals are *free*, inverting the naive "always use the cheaper link" heuristic. The traffic samples were essential for timing the toggles, and the billing clock confirmed it was worth acting immediately, but neither would have helped without the conceptual leap that spikes belong on the provider with the *larger* discard window. That leap is the value an LLM-based routing agent adds over a policy-driven daemon.