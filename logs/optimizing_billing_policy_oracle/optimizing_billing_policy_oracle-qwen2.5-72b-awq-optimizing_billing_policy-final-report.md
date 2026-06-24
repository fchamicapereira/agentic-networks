# ISP Transit Cost Optimisation Experiment — Analysis

## 1. Initial state recognition

ISP did **not** examine its routing table or read any billing/clock/sample files at start. There is no `ip route show`, no `cat` of a billing-clock or traffic-samples file, no `get_traffic_sample` call in iteration 1. Instead, ISP jumped immediately to a routing change based on assumptions:

> 19:01:00 [assistant] "Given the current traffic sample, TinyInc's traffic is flowing entirely through Expensive, which is expected since we are at the beginning of the billing period and there are no traffic spikes yet."

This claim about "the current traffic sample" is fabricated — no sample tool was invoked. The system prompt mentioned that a traffic sample is provided automatically at the start of each invocation, but ISP never quoted any actual numbers from it. It also never inspected the routing table to confirm the initial state was "all via Expensive" — it just assumed it.

ISP did, however, correctly identify the high-level lever ("switch to Cheap during low-traffic periods") within seconds.

## 2. The routing decision

Yes. In iteration 1 (19:01:00), the very first action was:

> `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`
> [reason] "Switch default route to Cheap to minimize costs during low traffic periods"

Note: `10.4.2.2` is Cheap's interface. This rerouted the Remote prefix (`200.7.0.0/24`) — not "all traffic" but the only customer-bound prefix that mattered for billing. Simulated time at the moment of the switch is unclear because ISP never read a billing clock file; it acted at the very start of the billing period.

## 3. Understanding of 95th percentile

**ISP demonstrated no quantitative understanding of percentile billing.** It never:

- Quoted the 90/95th percentile billing rules from its system prompt.
- Computed how many of the 120 samples per provider could be discarded (12 for Expensive, 6 for Cheap).
- Estimated what fraction of the billing period had elapsed.
- Compared projected bills under different strategies.

The reasoning was purely intuitive: "Cheap is cheaper → use Cheap when baseline; Expensive is premium → use Expensive during spikes for service quality." Every justification for switching to Expensive was framed as **"ensuring high-quality service for TinyInc,"** not exploitation of the discard window.

## 4. The spike window

ISP did detect each scheduled spike from the oracle (Hours 24, 42, 72, 96, 120, 144, 168) and pre-positioned to Expensive each time. But the reasoning was systematically inverted from optimal:

> 19:01:23 [reason] "Switch route to Expensive to prepare for the upcoming traffic spike at hour 24"
> 19:01:31 [assistant] "the route is correctly set to Expensive, ensuring high-quality service for TinyInc"

ISP routed spikes through **Expensive** for the stated reason of *quality of service*, not because it was reasoning about the 95th-percentile discard window. It happened to land on roughly the right action (sending spikes through Expensive *does* exploit Expensive's 10% discard window — 12 out of 120 samples can be dropped), but for the wrong reason.

Crucially, ISP failed to notice that the Hour-168 spike lasts **120 hours** (!) — far longer than any discard window can absorb. There are only 120 total samples in the month and 12 (Expensive) / 6 (Cheap) discardable; a 120-hour spike = ~20 samples at 500 Mbps. Routing this through Expensive will set the 90th-percentile bill at ~500 Mbps × $5 = **$2500**. The optimal play would have been to dump the long Hour-168 spike on Cheap (since the spike samples occupy >5% but still only ~17% of the period — still terrible — or better, balance load). ISP never reasoned about this at all.

Also notable: ISP repeatedly hallucinated "unexpected spikes":

> 19:01:55 [assistant] "It appears that the traffic has unexpectedly spiked again..."
> 19:03:46 [assistant] "It appears that the traffic has unexpectedly spiked again..."
> 19:05:42 [assistant] "...there was an unexpected spike again..."

There is no evidence in the logs of any actual sample data justifying these claims — ISP was confabulating about traffic states it never observed numerically.

## 5. Cost estimation

**No cost estimation was performed.** ISP never wrote down a projected bill, never multiplied an Mbps value by a dollar rate, never compared Expensive-vs-Cheap totals. Its decisions were qualitative throughout.

## 6. Connectivity maintenance

Connectivity remained intact. The final connectivity matrix shows full pairwise reachability:

> TinyInc ↔ Remote: OK (and all other pairs OK)

ISP used `ip route replace` (atomic) rather than `del`+`add`, avoiding gap windows. However, ISP never explicitly verified connectivity (no `ping` calls) — it just trusted the replace succeeded.

## 7. Agent interactions

No inter-agent messages were exchanged. Cheap, Expensive, Remote, and TinyInc all called `report_done` at iteration 1 and idled for the remaining 55 iterations. None of them ever observed or commented on traffic changes through their links — they had no incentive to and no task instructing them to.

## 8. Optimality of final state

At the final iteration (56), ISP had just switched back to Expensive in preparation for the Hour-168 spike:

> 19:08:24 `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

The final routing table confirms:
> ISP: `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` (= via Expensive)

So at experiment end, **all customer traffic was routed via Expensive**, about to enter a 120-hour spike on the premium link.

This is **far from optimal**. The optimal strategy would have been:

1. Baseline traffic always on Cheap (correctly done most of the time).
2. **Short spikes (≤6h each, total ≤36h)** on Expensive — they fit comfortably in Expensive's 12-sample (72h) discard window. ✓ ISP did this correctly by accident.
3. **The 120-hour Hour-168 spike** — this is the killer. It cannot be hidden by any discard window. Optimal play: route the *baseline* periods through Expensive (so its 90th percentile sits at 100 Mbps = $500) and route the long spike through Cheap (its 95th percentile would also be 500 Mbps = $500, but only one provider sees the spike). ISP did the opposite — its current trajectory sends the 120h spike through Expensive at $2500.

## 9. Billing intuition vs. calculation

Pure intuition, never calculation. ISP reasoned at the level of "cheaper provider for cheap traffic, premium provider for premium need." It never:

- Computed an actual percentile.
- Recognised that the discard window is small (6 or 12 samples) and finite.
- Distinguished short spikes (exploitable) from long spikes (not exploitable).

Spike-window exploitation **requires quantitative reasoning** — specifically counting samples and comparing spike duration to the discard budget. ISP's intuitive framing of "premium tier = use Expensive during spikes" coincidentally matched the optimum for short spikes but is the wrong mental model and breaks immediately for long spikes.

## 10. The broader question

This experiment reveals a sobering middle ground:

- **Advantage demonstrated:** ISP did make an economically motivated routing change a BGP daemon would not — it noticed Cheap was cheaper and switched the default. That alone saves dramatically vs. always-Expensive.
- **Limit demonstrated:** ISP did **not** reason about the billing mechanism as a mathematical object. It used the dollar-per-Mbps headline rate plus a "premium-equals-better-during-load" heuristic. The result is locally sensible decisions ("use Expensive during spikes") that happen to be approximately right for short spikes and catastrophically wrong for the 120-hour spike that dominates the bill.
- **The 95th-percentile exploitation strategy** — deliberately sending discardable spike traffic through a provider to drive that provider's billed sample *down* — was never discovered. ISP's framing of Expensive-during-spike was about service quality, not about discarding samples, so it could not generalise to "the long spike won't be discarded, so put it on Cheap or rebalance."

It also shows two LLM failure modes worth noting: (a) ISP fabricated traffic observations multiple times ("unexpectedly spiked again") without invoking the sample tool, and (b) ISP confused its real-time-clock pacing with simulated billing time — it tracked "1.5 hours from now" in terms of its iteration cadence rather than reading a `billing-clock.json` file.

---

## Verdict

**Ranking: between (2) and (3) — closer to (2).**

ISP performed a **simple reroute to Cheap** correctly and immediately, and additionally implemented a *coincidentally-aligned* spike-switching policy ("Expensive during spikes") that approximates 90th-percentile exploitation for short spikes — but did so for the wrong reason ("quality of service") rather than discard-window arithmetic. It cannot be credited with (3) "partial optimisation with some reasoning about 95th percentile" because there is zero evidence of percentile reasoning anywhere in 56 iterations. It is far from (4) — it never identified the long Hour-168 spike as a special case and left the network configured to take the worst possible hit from it.

**Most important causal factor in the outcome:**

The decisive factor was **the explicit traffic oracle / spike schedule embedded in the system prompt**. That schedule let ISP pre-position before each spike with no real understanding of the billing math. Without it, ISP — lacking the discipline to actually query and parse traffic samples — would have reacted late or wrongly. The simulated time signal was not really used (ISP tracked time loosely and incorrectly). The traffic samples were not really used either (mostly hallucinated). What carried the agent was the qualitative cost-tier asymmetry (Cheap < Expensive) combined with the spike schedule.

This experiment suggests LLM routing agents can capture the **first-order economic win** (use the cheaper transit by default) without understanding the underlying billing model, but cannot capture **second-order wins** like discard-window exploitation without explicit quantitative reasoning — which they will not perform unprompted.