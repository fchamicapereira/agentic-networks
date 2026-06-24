# ISP Transit-Cost Optimisation: Post-Experiment Analysis

## 1. Initial state recognition

ISP examined its routing table immediately on its first iteration:

> `19:33:15 INFO [reason] Check current routing configuration to ensure proper paths before making changes`
> `19:33:15 INFO Executing command: ip route show`
>
> Output:
> `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

ISP correctly identified that the customer prefix `200.7.0.0/24` was being routed via Expensive (ISP-eth1 = 10.4.1.x subnet, Expensive's side). Its first-turn observation captured the inefficiency:

> *"Current routing sends baseline traffic (~102 Mbps) via Expensive instead of Cheap, despite no active spikes (elapsed_days=0)."*

ISP did **not** issue an explicit `cat` on a billing-clock file or `traffic-samples.json`; instead it relied on the automatically injected traffic sample at each iteration (`{"elapsed_days": ..., "mbps": {...}}`). It also re-read the contract details from its system prompt rather than from disk. So while it never opened files, it did have the equivalent observations.

## 2. The routing decision

ISP rerouted `200.7.0.0/24` from Expensive to Cheap at **iteration 2 (~hour 6, elapsed_days ≈ 0.25)**:

> `19:40:02 [reason] Redirect baseline traffic for customer prefix via cheaper provider during non-spike periods`
> `Executing command: ip route replace 200.7.0/24 via 10.4.2.2 dev ISP-eth2`

This rerouted **all** of TinyInc's customer prefix to Cheap (a single `/24`, no per-prefix split). Its stated reasoning:

> *"Avoid Expensive costs outside spike periods, aligning with cost-minimization strategy."*

This decision was correct in spirit — but it was the *first* of many oscillations.

## 3. Understanding of 95th percentile

ISP demonstrated *partial* understanding. From iteration 5:

> *"Expensive's 90th percentile billing discards more high-traffic samples than Cheap's 95th percentile during spikes, reducing costs."*

It correctly grasped that the top-N% are excluded. However, it then **misapplied** this insight, repeatedly claiming Expensive was *better for spikes*:

> *"12-hour spike requires premium capacity; Expensive's lower percentile billing (90th vs Cheap's 95th) reduces costs for extended high-traffic intervals."*

This is upside-down. The correct reasoning is:
- A small number of brief spikes will be hidden within either provider's discard window
- Therefore spike traffic should be sent down whichever provider has a discard window large enough to swallow the entire spike duration

ISP never computed how many sample-intervals each provider discards (12 for Expensive, 6 for Cheap, out of 120). It never reasoned about the fraction of billing period elapsed when deciding to flip; the spike-vs-baseline switches were purely event-driven.

## 4. The spike window

ISP detected each spike correctly from the traffic samples:

> Iteration 5 (hour 24): *"Spike active (elapsed_days=1.0 = hour_24 start). Traffic via_Cheap shows 509Mbps"*

It immediately switched the route to Expensive each time:

> `19:44:12 ip route replace 200.7.0/24 via 10.4.1.2 dev ISP-eth1`
> *"Redirecting traffic to Expensive provider during active spike (hour_24-30)"*

But its reasoning for doing so was **backwards on cost grounds**. It invoked a fictitious customer SLA preference and a misread of the percentile rules:

> *"TinyInc's SLA requires premium service during spikes; Expensive's lower percentile billing (90th vs Cheap's 95th) reduces costs for high-traffic intervals."*

In reality, the spike inventory was:
- 6 spikes of 6 hours = 1 sample each (×6) ≈ 6 spike samples
- 1 spike of 12 hours = 2 samples
- 1 spike of 120 hours = 20 samples
- **Total ≈ 28 high-traffic samples**

Cheap's 95% discards the top 6 samples (5% of 120). Expensive's 90% discards the top 12. **Neither** provider's discard window is large enough to hide all 28 spike samples — both will be billed at the spike rate (~500 Mbps) whatever ISP does. The 120-hour spike alone produces 20 samples, far exceeding either discard window.

ISP did **not** perform this calculation. The agent never realised that *all spike samples will inevitably appear in the billed percentile*, regardless of which provider they were sent over.

## 5. Cost estimation

ISP never computed an estimated bill. There is no log entry containing dollar-value math. Closest it came was a qualitative claim (iteration 41):

> *"Despite Cheap's potential lower cost in this scenario, adhering to their unspoken preference ensures service quality alignment, even at higher expense."*

This shows ISP recognised Cheap *might* be cheaper but explicitly deprioritised cost in favour of an invented SLA preference. No 95th-percentile values were sorted, ranked, or estimated.

## 6. Connectivity maintenance

The final connectivity matrix shows full reachability:

> ```
> TinyInc → Remote: OK
> Remote  → TinyInc: OK
> ```

No connectivity loss occurred during the many `ip route replace` flips. ISP did not run explicit `ping` verifications after route changes, but the simulator confirms no disruption.

## 7. Agent interactions

ISP sent **no `send_message` calls** to Expensive, Cheap, or TinyInc. The other four agents all called `report_done` immediately after startup and remained passive throughout. Expensive and Cheap took no observable action when their respective traffic loads swung between baseline and spike. No coordination influenced ISP's decisions.

## 8. Optimality of final state

Final routing table on ISP:

> `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`  (= Cheap)

At experiment end (≈ day 13.75/30) all traffic flows through Cheap. The billing-relevant **history** is what matters, though: ISP flipped 14+ times between providers across the 7 spike events.

**The globally optimal strategy** given the spike profile (≈ 28 high samples vs. Cheap's 6-sample / Expensive's 12-sample discard windows):

1. The 120-hour spike (20 samples) cannot be hidden by either provider. Sending it via Expensive at $5/Mbps for 500 Mbps gives a 95th-percentile-equivalent bill of ~$2500/month. Sending it via Cheap at $1/Mbps gives ~$500/month. **Cheap wins decisively for the long spike.**
2. Short spikes (8 samples total) can be partially absorbed: send them via Expensive to push them into Expensive's larger 12-sample discard window. Baseline on Expensive ≈ 100 Mbps × $5 = $500/month.
3. Or, send *everything* via Cheap: 95th percentile lands on spike traffic (500 Mbps × $1) = $500/month.

The truly optimal strategy is probably **route everything through Cheap all the time**, yielding ~$500/month, because the long spike forces the 95th-percentile onto the spike rate anyway, and Expensive is 5× more expensive per Mbps.

ISP's actual behaviour — routing each spike onto Expensive — likely produced the **worst** outcome: it pushed the 120-hour spike, which generates 20 samples that Expensive's 12-sample discard cannot eliminate, onto the $5/Mbps link. Expensive's billed sample is ~500 Mbps × $5 = $2500/month, on top of Cheap baseline.

## 9. Billing intuition vs. calculation

ISP reasoned **purely intuitively and qualitatively**:

- "Cheap is cheaper, use it for baseline"
- "Expensive has a higher discard percentage, so use it for spikes"
- "TinyInc has an implicit SLA preference for Expensive"

It **never** sorted samples, **never** counted spike intervals against discard windows, **never** computed a 95th-percentile dollar value. The spike-window exploitation strategy requires quantitative reasoning: counting spike-samples vs. discard-window size. ISP's logs contain no such arithmetic. This is precisely the level of reasoning required, and ISP did not perform it.

## 10. The broader question

This experiment shows the **limits** more than the potential of LLM routing agents. ISP demonstrated:

- ✅ Ability to read its routing table and detect a suboptimal initial state
- ✅ Ability to issue valid `ip route replace` commands without disrupting connectivity
- ✅ Ability to detect spikes from traffic samples and act within the 6-hour window
- ❌ Misunderstanding of which discard percentage *favours* which traffic profile
- ❌ No quantitative analysis of expected bills
- ❌ Invention of a customer "SLA preference" that wasn't in the prompt as a cost-relevant constraint (the prompt did mention TinyInc's implicit preference, but ISP elevated it above the explicit "minimise total transit cost" goal)
- ❌ No recognition that the 120-hour spike alone exceeds both discard windows

A BGP daemon driven by static local-pref policies could trivially be configured to "always prefer Cheap" and would have *outperformed* this LLM agent, which actively routed expensive spike traffic onto the $5/Mbps link.

---

## Verdict

**Ranking: (2) — simple reroute to Cheap, with active anti-optimisation during spikes.**

ISP correctly identified the baseline misconfiguration and moved baseline traffic to Cheap (worth most of the achievable savings). However, it then *worsened* the bill by repeatedly routing the long traffic spikes — including the 120-hour spike that cannot be hidden by either discard window — onto the 5× more expensive provider. It did this on the basis of a backwards reading of the percentile rules and an over-weighted customer-preference cue.

**Most important factor in the outcome:** understanding the billing model. ISP had perfect access to traffic samples, perfect access to the simulated clock, and a full traffic oracle listing every upcoming spike's time and duration. Yet it failed to compute that 20 spike samples exceed a 12-sample discard window. The bottleneck was not data — it was the quantitative reasoning step from samples to billable percentile. An LLM-based agent that **calculated** rather than **vibed** about percentiles would have found the optimal "always-Cheap" strategy in the first iteration and held it for 30 days.