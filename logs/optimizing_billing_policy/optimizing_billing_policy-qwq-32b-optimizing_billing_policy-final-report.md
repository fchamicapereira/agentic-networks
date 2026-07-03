# ISP Transit Cost Optimisation Experiment — Analysis

## 1. Initial state recognition

ISP examined its routing table immediately in iteration 1:

> `10:13:53 [reason] Check current routing configuration to identify existing paths for Remote prefixes`
> `Executing command: ip route show`

Output revealed: `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` — i.e., all traffic to Remote via Expensive.

ISP correctly recognised this in iteration 2:
> *"The route for 200.7.0.0/24 uses Expensive (ISP-eth1), with baseline traffic (102 Mbps) flowing through it while Cheap remains unused."*

However, ISP **never invoked `get_traffic_sample` explicitly**, never read a "billing-clock.json" file, and never inspected a traffic-samples file. It relied entirely on the automatic traffic sample injected at each invocation (`elapsed_days` and `mbps` fields). The billing contracts came from the system prompt, not from disk.

## 2. The routing decision

ISP rerouted from Expensive → Cheap in **iteration 2**, at simulated **elapsed_days ≈ 0.5** (i.e., approximately half a day into the 30-day billing period):

> `10:14:22 Executing command: ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`
> Reason: *"Route baseline Remote traffic through cheaper provider (Cheap) during non-spike periods"*

It rerouted only the customer prefix `200.7.0.0/24` (correct — this is TinyInc's traffic to Remote). Reasoning was quantitative on price ($1/Mbps vs. $5/Mbps) but did not yet consider the 95th-percentile mechanics.

## 3. Understanding of 95th percentile

ISP demonstrated **surface-level** understanding of percentile billing but got the strategic implication **backwards**. From iteration 5:

> *"High throughput (~5x baseline) risks disproportionately inflating Cheaps' billable samples (only top 5% discarded vs Expensives' top-ten% discarded). Switching now reduces cost exposure under their more favorable percentile billing policy"*

This is a **critical inversion**. The correct interpretation:
- **Cheap discards 5% (top 6 samples in a 120-sample month) — spikes will land in this discard window** if they are rare and short. So Cheap's billed rate stays at ~100 Mbps despite the spike.
- **Expensive discards 10% — a larger discard window**, but Expensive costs 5× more per Mbps.

ISP inverted the reasoning: it treated the larger discard window on Expensive as intrinsically better, ignoring that the whole point of the exclusion is that spike samples fall into the top-N% and are not billed regardless.

ISP's own final report acknowledges this in retrospect (see Section 5 quotation).

ISP did not compute how many samples had elapsed or how many the spike would consume relative to the 5%/10% budget.

## 4. The spike window

ISP detected spikes clearly — e.g., iteration 5:
> *"Traffic spiked to ~514 Mbps via Cheap provider—indicative of an unexpected early surge"*

But its **response was the opposite of optimal**. Every time it saw a spike, it rerouted spike traffic to Expensive:

> `10:16:56 Executing command: ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`
> Reason: *"Redirect surge traffic (~514Mbps) through Expensive provider during surge for cost-effective metering"*

**Optimal behaviour** would have been the reverse: leave spikes on Cheap because they fall in Cheap's top-5% discard window and are not billed. Instead ISP:
- Sent all spike samples through Expensive, where they still may fall in the top-10% window — **but at $5/Mbps** they're catastrophic if they don't.
- More importantly, ISP kept the baseline samples on Cheap, which was correct, but it treated Expensive as the "spike absorber". Since Expensive's 90th-percentile would still be dominated by any residual traffic ISP happens to leave there, it exposes Expensive to a much higher billable rate.

ISP did explicitly reason about the spike falling in a discard window, but attributed the benefit to the wrong provider.

## 5. Cost estimation

ISP attempted a numerical estimate only in its final self-report, and got it wrong in real-time. In the retrospective:

> *"Expensive Cost: 510 Mbps * $5/Mbps = $2,550/month … Cheap Cost: At 510 Mbps, 95th percentile would discard 5%, so billed ~485 Mbps → $485/month. Conclusion: Cheap is cheaper for spikes"*
> *"Error Acknowledgment: The earlier decisions to route to Expensive during spikes were erroneous."*

So ISP realised post-hoc that its strategy was wrong, but only after the experiment ended. During the run, no genuine 95th-percentile computation was performed — decisions were governed by hand-wavy percentile-discard heuristics.

## 6. Connectivity maintenance

Full connectivity was preserved. The final connectivity matrix shows **OK** across all pairs. ISP used `ip route replace` (atomic), so no black-hole windows occurred. ISP did not run explicit post-change ping verification, but the automatic traffic sample in each subsequent iteration confirmed traffic was flowing on the newly-selected link (e.g., after switching to Expensive, the next sample showed "via Expensive: 510 Mbps, via Cheap: 0").

## 7. Agent interactions

No messages were exchanged. Cheap, Expensive, Remote, and TinyInc all called `report_done` on iteration 1 and remained silent. ISP made all decisions autonomously from local traffic samples. Cheap and Expensive, having terminated, could not have observed traffic-level changes even if they had wanted to.

## 8. Optimality of final state

At end (`elapsed_days=13.75`, iteration 56), the route is `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` (Cheap). The final routing table confirms:

> `ISP: 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

Over the 13.75 simulated days observed:
- Multiple short spikes (days 1, 1.75, 3, 4, 5, 6, 7) — each was moved to Expensive briefly.
- One long spike (days 7 → 12, ~5 days = ~20 samples) — ISP kept this on Expensive the whole time.

**This is close to worst-case for Expensive's bill.** Twenty consecutive samples at 510 Mbps mean Expensive's 90th percentile lands at 510 Mbps → **$2,550/month bill on Expensive alone**, while Cheap sees only baseline (~$100/month at 95th percentile).

**Optimal strategy:** leave *everything* on Cheap for the entire billing period. Six samples of 510 Mbps in a 30-day period (three ~2-day spikes at 6-hourly samples ≈ 24 samples… actually more) — the top 5% (6 samples) of Cheap's 120 samples get discarded. As long as spike-days ≤ ~6 samples worth, Cheap's 95th percentile stays at ~100 Mbps → **$100/month total**.

The long 5-day spike observed here (~20 samples) would exceed Cheap's discard budget too, but even then Cheap's 95th percentile ≈ 510 Mbps × $1 = $510/month, still 5× cheaper than Expensive's $2,550.

## 9. Billing intuition vs. calculation

ISP reasoned **qualitatively** ("larger discard window is better"), never quantitatively. It never computed:
- Number of samples already taken (elapsed_days × 4)
- Number of samples remaining in the top-5% discard budget
- Projected 95th percentile of the observed distribution

Identifying the spike-window exploitation strategy required **quantitative** reasoning: recognising that 6 samples of the 120-sample month can be "free" on Cheap, so short spikes cost nothing there. ISP's qualitative reasoning was insufficient — and in fact drove it in the wrong direction.

## 10. The broader question

This experiment is a **cautionary tale**. LLM-based routing agents *can* reason about economics, but reasoning is not the same as reasoning *correctly*. ISP:

- ✅ Recognised billing contracts existed and mattered
- ✅ Read its routing table and identified the sub-optimal starting state
- ✅ Made the trivial fix (baseline → Cheap) within one iteration
- ❌ Inverted the percentile logic and did the opposite of optimal for spikes
- ❌ Never quantified its projected bill
- ❌ Locked itself into Expensive during the 5-day long spike — the most expensive possible mistake in this billing model

A BGP daemon with a simple "prefer cheaper provider" policy would have done **strictly better** here, because it would have left all traffic on Cheap and let the 95th-percentile mechanism naturally discard the spikes. The LLM's economic reasoning was worse than no economic reasoning.

## Verdict

**Ranking: (2) Simple reroute to Cheap, with active anti-optimisation on spike handling.**

ISP found the trivial win (baseline traffic to Cheap) but then *actively harmed* the bill by routing spikes to Expensive under an inverted understanding of percentile billing. The single 5-day spike parked on Expensive likely cost ~$2,500 more than doing nothing after the initial reroute.

**Most important factor in the outcome:** **understanding of the billing model**. ISP had the traffic samples and the elapsed_days clock; both were used. What it lacked was correct intuition about *which direction* percentile-billing exclusion favours. A model that had internalised "the top-N% samples are free" would have recognised that Cheap's smaller discard window is still *sufficient* for short rare spikes, and that the cost-optimal move is to **do nothing** during spikes on the cheap link. That single conceptual inversion determined the entire outcome — access to data and the clock were necessary but not sufficient.