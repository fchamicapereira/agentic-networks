# ISP Agent Evaluation

## 1. Initial state recognition

ISP never inspected its routing table at startup, nor did it enumerate the contract terms side by side. Its first-iteration reasoning jumped straight to a plan:

> "the baseline traffic is around 100 Mbps and is being carried entirely by Cheap… we need to prepare for the next spike by ensuring that we can offload some of this traffic to Expensive during the spike to avoid high costs on Cheap."

The framing is already wrong: it treats Cheap as the thing to be protected from spikes rather than recognising that Cheap's 95th percentile is the *only* dimension that matters, and that spikes placed on Expensive would land inside Expensive's 10% discard window and be free. There is no mention of percentiles, discard windows, or the 10%/5% asymmetry anywhere in the log — only the raw $/Mbps rates are implicit in the reasoning.

## 2. The baseline routing decision

The baseline was correctly left on Cheap by default — ISP never moved it. However, in iteration 26, during spike-handling confusion, ISP did temporarily delete the primary Cheap route (`ip route del 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`), briefly sending *all* traffic — baseline included — through Expensive, before re-adding Cheap. That window is short but shows the baseline-on-Cheap outcome was a happy accident, not a defended invariant.

## 3. Understanding of percentile billing

Essentially none. ISP mentions "90th percentile billing" once, in iteration 3:

> "offload some of this traffic to Expensive, which has a higher cost per Mbps but a lower overall impact due to the 90th percentile billing."

But this is namedropping, not reasoning. ISP never:
- counts samples remaining in the cycle (9 days × 4 = 36 samples) vs. samples already recorded (84);
- computes a projected percentile under either configuration;
- notes that Expensive has 84 zero-Mbps samples that already *guarantee* its 90th percentile will be at or below the first spike load;
- recognises that putting a spike on Cheap *will* push its 95th percentile from ~102 to ~500 Mbps unless the spike duration stays under the 5% window.

## 4. The spike windows — the decisive question

ISP detected spikes (iterations 3, 11, 19, 23) and did add a secondary route to Expensive each time:

> "The traffic has spiked to around 500 Mbps… Let's add a route to direct some of the traffic to Expensive… `ip route add 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1 metric 10`"

But this was fundamentally broken: the Cheap route had no metric (metric 0) and the Expensive route was added at metric 10, so Linux kept routing all traffic via Cheap. ISP didn't understand this and reported "offloaded" when nothing had moved. In every spike before iteration 23, ISP also *removed* the Expensive route almost immediately — in iteration 4, the Expensive route was deleted while the live sample still showed the ~500 Mbps traffic.

In iteration 23 onward ISP finally noticed the traffic wasn't shifting and began frantically churning metrics:

> "This suggests that the metric for the primary route via Cheap is lower, causing all traffic to prefer that path."

It then thrashed between configurations, failed `ip route change` twice (RTNETLINK errors because it was targeting the wrong existing route), briefly deleted the Cheap route entirely, re-added routes at metric 5 then 10 then 20, and ended the run with three conflicting routes to 200.7.0.0/24 in the table (metrics 5, 10, 20). The *reasoning* throughout was per-Mbps and load-balancing-oriented — "balance the load," "make both paths more competitive" — not percentile-oriented.

## 5. The discard budget

Never considered. ISP never counts spike samples sent through Expensive, never notes that Expensive has 84/120 samples already at zero (making the discard window effectively huge), and never reasons about whether spikes would fit in it. The question of budget depletion never comes up.

## 6. Cost estimation

No quantitative cost estimation of any kind. No arithmetic on samples, percentiles, or projected invoice amounts.

## 7. Connectivity maintenance

Connectivity was never explicitly verified, and the brief moments where the Cheap route was deleted (iteration 26) could in principle have disrupted baseline flow — though with the Expensive route still installed, forwarding would have continued via Expensive. No ping or traceroute was ever issued. By pure luck, no persistent outage occurred.

## 8. Agent interactions

None. ISP sent zero messages. Cheap, Expensive, Remote, and TinyInc all idled through the whole run. No external agent influenced routing.

## 9. Optimality of the final state and trajectory

Per the harness:
- **Actual bill: $511** (Cheap billed at 511 Mbps, Expensive at 0 Mbps)
- **All-on-Cheap reference: $511** — identical
- **Best-in-hindsight: $102**
- **Spikes-always-on-Expensive: $2,658**

So ISP's thrashing produced *exactly* the all-on-Cheap outcome: it never actually moved any traffic to Expensive, because the metrics it set were always wrong. The spikes rode on Cheap and set Cheap's 95th percentile to 511 Mbps. ISP overpaid by $409 vs. the optimum, missing the entire opportunity to shelter spikes inside Expensive's 10% discard window. The final routing table has three stale conflicting routes to 200.7.0.0/24, a configuration no competent operator would leave in place.

## 10. Billing intuition vs. calculation

Pure intuition, and the wrong kind of intuition at that: "cheaper per Mbps = send more there." No percentile-level calculation ever occurred, and the one time percentile billing was mentioned it was a label, not a computation.

## 11. The broader question

ISP showed none of the economic-reasoning advantage that distinguishes an LLM agent from a BGP daemon. It verbalised the right vocabulary ("90th percentile," "offload during spike") but applied it mechanically, without model-based thinking about discard windows or budget. Worse, it couldn't even *execute* its naive plan: Linux metrics tripped it up, and it spent the back half of the run thrashing on `ip route change` without diagnosing why the command was failing. A static local-pref policy on a BGP daemon ("prefer Cheap, failover to Expensive") would have produced the same final bill without the operational chaos.

## Verdict

**Rank: (2) No optimisation.** Everything ended up on Cheap, spikes included — the spikes set Cheap's 95th percentile and the agent paid full price for them. The one half-correct intention (route spikes via Expensive) was never implemented because the agent didn't understand Linux route metrics, and the underlying *reason* for the intention was wrong anyway (naive $/Mbps load balancing, not percentile sheltering). Note that this is only tier-2 by luck: ISP's deletion of the Cheap route in iteration 26 could easily have left the baseline on Expensive at the wrong moment, which would have been strictly worse.

**Most important factor:** failure to grasp discard-window mechanics. Every subsequent problem — treating spike cost as a per-Mbps problem, chasing "load balance," never computing a bill — follows from not understanding that the top 10% of Expensive's samples are literally free. Access to traffic samples and the elapsed-time signal was fine; ISP simply had no model to interpret them with.