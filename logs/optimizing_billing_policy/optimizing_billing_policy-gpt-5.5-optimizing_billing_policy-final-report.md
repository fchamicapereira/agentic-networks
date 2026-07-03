# Analysis of ISP Cost-Optimisation Experiment

## 1. Initial state recognition

ISP did **not** explicitly examine the routing table or read billing-clock/traffic-sample files as separate observations. It relied entirely on the automatic traffic-sample injection described in the system prompt:

> "Traffic sample: a live throughput measurement is automatically provided at the start of each invocation"

On the very first iteration, ISP correctly recognised that traffic was going via Expensive at baseline and immediately acted:

> `09:41:36 [reason] Observed baseline (~100 Mbps), not a spike; move TinyInc-to-Remote traffic from Expensive to Cheap for the current 6-hour billing sample.`
> `Executing command: ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

No inspection of `ip route show`, no reads of `billing-clock.json`, no separate traffic-samples file access. Recognition was implicit — driven by the injected sample.

## 2. The routing decision

ISP rerouted the customer prefix `200.7.0.0/24` from Expensive (`via 10.4.1.2 dev ISP-eth1`) to Cheap (`via 10.4.2.2 dev ISP-eth2`) at iteration 1 (very start of the billing period, effectively day 0). The command was:

> `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

It rerouted **only the customer prefix** `200.7.0.0/24` — not all traffic. This is appropriate: it left other prefixes (`23.45.0.0/24` via Cheap, `62.115.0.0/24` via Expensive) untouched. Reasoning:

> "Cheap is much less expensive at $1/Mbps, so I used Cheap for normal ~100 Mbps baseline traffic."

## 3. Understanding of 95th percentile

ISP demonstrated **correct qualitative understanding**, but with a critical **factual error**. From its self-report:

> "Cheap uses 95th-percentile billing, discarding only 6 of 120 samples. To avoid raising Cheap's billable rate with short spikes, I moved observed ~500 Mbps bursts to Expensive whenever possible."

> "Expensive costs $5/Mbps but has a 90th-percentile billing model, discarding the top 10% of samples. Since there are 120 samples per month, up to 12 high samples can be discarded."

**This is wrong.** The system prompt actually said Expensive bills at the **90th percentile** but also stated:

> "Expensive: $5.00 per Mbps, billed at the 90th percentile of periodic samples... Top 10% of samples discarded."

Wait — re-reading the prompt, ISP did read it correctly. Expensive discards top 10% (12 samples), Cheap discards top 5% (6 samples). So ISP's reasoning here was correct. It quantified the discard window (12 vs 6 samples out of 120) and used that to justify preferring to place spikes on Expensive.

ISP did **not** appear to reason explicitly about the fraction of the billing period elapsed when making decisions, though it noted per-window billing samples. It made no explicit projected-bill calculation — no dollar-value estimate appears in any log entry.

## 4. The spike window

ISP detected spikes and acted on each one. From its self-report:

> "Day 1.0: switched to Expensive; day 1.25 switched back to Cheap
> Day 1.75: switched to Expensive; day 2.0 switched back to Cheap
> Day 3.0: switched to Expensive; day 3.25 switched back to Cheap"
> …and so on through day 7

ISP's strategy was the **opposite** of what the question frames as naive: it deliberately **routed spike traffic through Expensive** to exploit its larger 10% discard window. Log evidence:

> `09:42:06 [reason] Detected a traffic spike (~500 Mbps); switch Remote prefix to Expensive immediately to keep the spike within Expensive's larger 90th-percentile discard window and avoid raising Cheap's 95th-percentile billable rate.`

This is exactly the spike-window exploitation strategy described in the question — but with a nuance: ISP put spikes on **Expensive** (where the discard window is *larger*), not Cheap. The reasoning is that ANY provider will discard a small number of top samples; the provider whose *rate* is higher benefits more from having its high samples land in the discard window, because that keeps its billable percentile at baseline.

Actually — the optimal strategy depends on whether spike duration exceeds the discard window of one or both providers. ISP eventually recognised this. During the prolonged spike (~day 7 to ~day 12), ISP initially kept it on Expensive but then reversed course:

> `09:50:29 [reason] Spike is still ongoing, but Cheap has already exceeded its 95th-percentile discard allowance while Expensive must be kept below its 90th-percentile high-sample limit; move the Remote prefix to Cheap now to avoid raising Expensive's billable rate.`

## 5. Cost estimation

ISP **never produced explicit dollar figures**. No log line shows a "$X projected bill" calculation. It reasoned in units of *number of samples in the discard window* rather than dollars. From iteration 33 onward, ISP spent multiple long reasoning turns (up to 3,611 reasoning tokens in iteration 38) working through discard-window math but never emitted a concrete cost comparison.

The implicit calculation it did perform was: "count of high samples so far vs. size of the discard window." This was tracked qualitatively — ISP eventually concluded that Cheap had "exceeded its 95th-percentile discard allowance" and therefore additional high samples on Cheap were "free" (no longer raising the billable percentile).

## 6. Connectivity maintenance

Connectivity was maintained throughout. The final connectivity matrix shows all pairs `OK`. ISP did not run any `ping`/`traceroute` verification after route changes (the system prompt told it not to). Because `ip route replace` is atomic and both next-hops (`10.4.1.2` and `10.4.2.2`) had working paths to `200.7.0.0/24`, no disruption occurred.

## 7. Agent interactions

**No inter-agent communication occurred.** All four other agents (Cheap, Expensive, Remote, TinyInc) called `report_done` immediately in iteration 1:

> Cheap: `=== AGENT TERMINATED === Cheap is pre-configured and fully operational…`
> Expensive: `=== AGENT TERMINATED === Expensive is pre-configured and fully operational…`

They then received wake-ups every ~6 hours (iterations 2–56 for each) but had already terminated. Expensive and Cheap therefore had no opportunity to notice traffic-level changes on their links, nor did they attempt to communicate with ISP.

ISP itself sent no messages. All decisions were unilateral, based only on injected traffic samples.

## 8. Optimality of final state

At experiment end, the routing table shows:

> `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`   (Cheap)

That is: baseline TinyInc-to-Remote traffic is on Cheap. This is the correct **baseline** placement.

Over the whole billing period, ISP's dynamic strategy was:
- Baseline → Cheap ✓ (huge win vs the starting configuration on Expensive)
- Short spikes (days 1, 1.75, 3, 4, 5, 6) → Expensive ✓ (absorbed by Expensive's discard window)
- Long spike (day 7–12) → Expensive initially, then Cheap at day 9.25 ✓ (correct switch once Cheap's percentile was already elevated)

This is close to **optimal (level 4)** behaviour. The one arguable inefficiency: during the prolonged spike, ISP burned some of Expensive's 12-sample discard budget before switching to Cheap. A perfectly optimal actor would have computed spike duration in advance from the "every ~2 days for several hours" pattern in the system prompt and made a global allocation; ISP instead reacted greedily and only re-planned when it realised the spike was prolonged.

## 9. Billing intuition vs. calculation

ISP operated at a **hybrid intuitive/semi-quantitative** level:
- Intuitive: "Cheap costs less, so use Cheap for baseline."
- Quantitative-ish: "Cheap discards 6 of 120; Expensive discards 12 of 120."
- Not fully quantitative: no dollar calculations, no explicit spike-count tracking against remaining discard budget.

To identify the spike-window exploitation strategy at all, **quantitative reasoning was required** — a purely intuitive "route through the cheaper provider" agent would send spikes to Cheap and pay for them. ISP correctly performed the meta-level reasoning: spikes are top-of-distribution samples and will be discarded, so route them to whichever provider has more remaining discard budget.

## 10. The broader question

This experiment supports the thesis that **LLM-based routing agents can reason about economics in ways policy-driven daemons cannot**. Concretely:

- A BGP daemon with a static `local-pref` for Cheap would put ALL traffic (including spikes) on Cheap, driving Cheap's 95th-percentile bill up to ~$500/Mbps × Cheap's rate.
- A BGP daemon with `local-pref` for Expensive (the starting state) would pay ~$5/Mbps × baseline for a whole month, wildly over-paying.
- ISP found the non-obvious *split* strategy: baseline on Cheap, spikes on Expensive — with dynamic re-planning when a spike outran Expensive's discard budget.

Limits also visible:
- ISP burned enormous reasoning-token budgets during the prolonged spike (iteration 38: 3,611 reasoning tokens) working out something that a simple counter could have decided instantly.
- ISP hit the max-iteration limit (56) without ever calling `report_done` — appropriate, since it was told never to terminate, but it never produced any consolidated cost projection.
- ISP made no dollar-value calculations at all — its reasoning was structural, not numerical.

## Verdict

**Level 4 — full optimisation including spike-window exploitation.**

ISP:
1. Immediately identified the misconfigured default route (Expensive for baseline) and corrected it.
2. Correctly reasoned that spikes are top-of-distribution samples and can be routed to whichever provider has the wider discard window.
3. Deliberately sent short spikes to Expensive to exploit its 10%-discard allowance.
4. Correctly recognised when a prolonged spike would exhaust Expensive's discard budget and re-routed to Cheap mid-spike.
5. Returned baseline traffic to Cheap at every spike's end.

The single dominant factor in this outcome was **understanding of the billing model** — specifically, the meta-insight that discarded samples are effectively free bandwidth. Access to the traffic sample was necessary (without it, ISP could not have detected spikes in real time), but it was not sufficient: many agents given the same sample would simply route baseline to Cheap and stop there (level 2). The simulated time signal was largely unused — ISP acted per-window without integrating over billing-period elapsed time.

**Ranking of causal factors:**
1. Billing-model comprehension (most important — enabled spike-window strategy)
2. Real-time traffic samples (necessary for reactive routing)
3. Billing clock (least important — ISP essentially ignored it)