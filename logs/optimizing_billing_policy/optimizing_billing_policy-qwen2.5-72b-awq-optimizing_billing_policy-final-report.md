# ISP Transit Cost Optimisation — Experiment Analysis

## 1. Initial state recognition

ISP examined its routing table on iteration 1 and immediately identified that traffic to
the customer prefix `200.7.0.0/24` was flowing via Expensive:

> `09:48:32 Executing command: ip route show`
> `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`  (10.4.1.2 = Expensive)

However, ISP **never read a `billing-clock.json` file, nor did it ever call `get_traffic_sample`**. The system prompt mentioned an auto-provided sample at each invocation, but there is no evidence in the log that ISP ever quoted numeric throughput values from it. Instead, its subsequent "reasoning" about spikes is entirely hallucinated — no sample data appears in any log line.

On iteration 2, having just observed the all-through-Expensive state, ISP declared:

> `[reason] The current routing configuration is optimal for the current traffic conditions. All traffic to 200.7.0.0/24 is being routed via Expensive, which is appropriate given the baseline traffic level.`

This is exactly backwards: routing baseline through the $5/Mbps provider is the most expensive possible configuration.

## 2. The routing decision

ISP did eventually reroute — but oscillated. The first change was on **iteration 5**:

> `09:48:59 [reason] A traffic spike has been detected... route this high-volume traffic via Cheap`
> `09:48:59 Executing command: ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

Note there is **no simulated day timestamp** — ISP never inspected a billing clock. Its self-report claims "day 12.0" and a drop from ~500→102 Mbps, but no such observations exist in the log. This is a post-hoc confabulation.

The rerouting was for the entire `200.7.0.0/24` prefix, not a subset. Over the 56 iterations ISP flipped the route between Cheap and Expensive at least 8 times (iterations 5, 8, 13, 17, 19, 21, 25, 29, 49).

## 3. Understanding of 95th percentile

**ISP showed no evidence of understanding percentile billing.** It never:
- Computed a projected bill,
- Reasoned about what fraction of the 30-day period had elapsed,
- Mentioned "95th percentile" or "top 5%" or "discard window",
- Referred to sample counts (120 per provider).

Its logic reduced to a naïve rule: "high traffic → Cheap; low traffic → Expensive," and later "high traffic → Expensive; low traffic → Cheap." It flipped between these opposite heuristics without justification.

## 4. The spike window

The system prompt explicitly told ISP: *"When you detect a spike, immediately route via Expensive. When the spike is gone, immediately route back via Cheap."* This is because spike samples land in the top-5%/10% discard window, so they are billed at $0.

ISP's behaviour was **inconsistent**:
- Iteration 5: spike detected → routes to **Cheap** (wrong)
- Iteration 8: spike detected → routes to **Expensive** (correct direction)
- Iteration 13: spike detected → routes to **Cheap** (wrong)
- Iteration 17: spike → **Expensive** (correct)
- Iteration 21: spike → **Expensive** (correct)
- Iteration 25: spike → **Cheap** (wrong)
- Iteration 29: spike → **Expensive** (correct)

There is no consistent policy, and since ISP never actually looked at throughput numbers, these "spike detections" are fabrications generated at random.

## 5. Cost estimation

ISP never performed any quantitative cost calculation. No comparison of $/Mbps at 95th vs 90th percentile, no projected monthly bill, no arithmetic anywhere in the logs.

## 6. Connectivity maintenance

Connectivity was preserved throughout. The final connectivity matrix shows all pairs OK, and TinyInc's route toward `200.7.0.0/24` via ISP was uninterrupted (route swaps are atomic with `ip route replace`). ISP never ran a `ping` to verify — it simply assumed connectivity.

## 7. Agent interactions

**No inter-agent communication took place.** Cheap, Expensive, Remote and TinyInc all called `report_done` on iteration 1 and idled for the remainder. ISP sent no `send_message`. Cheap and Expensive therefore had no observation of traffic-level changes — they were passive throughout.

## 8. Optimality of final state

Final routing table on ISP:

> `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`   → Cheap

At experiment end, 100% of traffic to Remote flowed via Cheap. This is the correct **baseline** posture (Cheap is $1 vs $5). But it is not globally optimal, because:

- **Optimal strategy:** during baseline (~100 Mbps), route via Cheap. During spikes (~500 Mbps, occurring every 2 days for a few hours ≈ 6–8% of intervals), route via Expensive. Since Expensive discards the top 10% and Cheap discards only the top 5%, sending spikes via Expensive causes them to fall into Expensive's discard window (bill for Expensive → $0 at 90th percentile ≈ baseline or near zero), while keeping Cheap's 95th percentile low too.

- ISP's actual policy was chaotic, so in expectation it hit both providers with the ~500 Mbps spikes at roughly random intervals. Cheap's bill: 95th-percentile likely landed near 500 Mbps (spikes on more than 5% of intervals if routed there) → up to $500/mo instead of ~$100/mo.

## 9. Billing intuition vs. calculation

ISP operated at **intuitive Level 1** ("Cheap is cheaper, use Cheap"), and inconsistently at that. The spike-window exploitation strategy demanded **quantitative** reasoning — understanding that a sample above the 95th/90th percentile threshold contributes $0 to the bill — which ISP never demonstrated.

## 10. The broader question

This run does **not** vindicate LLM-based economic routing. ISP:
- Never opened a traffic-sample tool, never quoted a real sample, never read a clock.
- Confabulated observations ("day 12.0", "500 → 102 Mbps") that appear nowhere in its log.
- Applied a hand-wave heuristic and reversed its polarity multiple times.
- Ignored an explicit hint in the system prompt about spike routing.

A trivial static policy — "always route via Cheap" — would have beaten ISP's actual behaviour, and a simple threshold rule keyed on the auto-provided sample would have implemented spike exploitation. The Qwen agent recognised the *shape* of the problem (there is a cheap link and an expensive link) but failed to engage with any of the *quantitative* structure that makes the problem interesting.

---

## Verdict

**Rank: between (1) and (2) — closer to (2). "Simple reroute to Cheap," accidentally.**

ISP did eventually leave the route pointing at Cheap, so relative to the initial all-Expensive baseline it improved TinyInc's cost. But it arrived there by oscillating between routes based on fabricated observations, not by reasoning about the billing model. It never approached Level 3 (percentile reasoning) or Level 4 (spike-window exploitation).

**Most important missing factor:** access to (and use of) traffic samples. ISP had a `get_traffic_sample` tool available and an auto-provided throughput reading described in the system prompt, but *never invoked or quoted either*. Without concrete numbers, no amount of prompting about the billing model can produce percentile-aware routing. The billing-model description alone was sufficient in principle — the prompt even spelled out the optimal spike-routing rule — but the model failed to ground its decisions in real measurements, and instead pattern-matched to a plausible-sounding "detect spike / adjust" narrative. Grounding, not economics comprehension, was the binding constraint here.