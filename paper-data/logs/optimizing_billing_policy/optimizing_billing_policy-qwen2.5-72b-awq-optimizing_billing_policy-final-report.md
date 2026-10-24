# ISP Transit Cost Optimisation — Post-Mortem

## 1. Initial state recognition

ISP began by inspecting its routing table:

> `09:48:32 Executing command: ip route show`
> `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` (via Expensive)

That was the extent of its "initial analysis". There is **no evidence in the log that ISP ever read or reasoned about the billing contract details**. The system prompt explicitly told it the discard windows (top 10% vs top 5%) and different percentile thresholds (90th vs 95th), but ISP never verbalises the discard-window mechanic anywhere in 56 iterations. Its comparison collapses to a per-Mbps view: Expensive = expensive, Cheap = cheap. It did not call `get_traffic_sample` explicitly either — it relied solely on the auto-provided samples.

## 2. The baseline routing decision

ISP inherited a state in which the ~100 Mbps baseline was already on Expensive. Its self-report claims:

> "traffic to `200.7.0.0/24` dropped from ~500 Mbps to ~102 Mbps on day 12.0. I decided to re-route the traffic from `Expensive` to `Cheap`..."

But the actual first reroute in the log is at iteration 5:

> `09:48:59 [reason] A traffic spike has been detected, and it is now more cost-effective to route this high-volume traffic via Cheap to minimize costs.`
> `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

Note the reasoning: it moves traffic to Cheap **because a spike was detected**. This is exactly the wrong direction — spikes are the traffic that should go to Expensive (to be swallowed by the 10% discard window), while baseline should go to Cheap. ISP's mental model was inverted from the outset.

## 3. Understanding of percentile billing

There is **no evidence** ISP ever reasoned about percentiles, discard windows, or marginal cost inside the tail. Not a single log line references "90th", "95th", "percentile", "top 10%", "discard", or the finite-budget nature of the tail. Every "reason" field is a variation of one sentence — "route the high-volume via cheap / route via expensive because it's baseline" — with no numeric estimate of a bill, no consumption tracking, no projection. This is pure per-Mbps intuition.

## 4. The spike windows — the decisive question

ISP flipped routing many times, but in an inconsistent and often inverted manner. Reconstructing the flips from the log:

| Iter | Action | ISP's stated reason |
|---|---|---|
| 5 | → **Cheap** | "spike detected → Cheap is cheaper" |
| 8 | → **Expensive** | "spike detected → Expensive to minimize costs" |
| 13 | → **Cheap** | "spike → Cheap" |
| 17 | → **Expensive** | "spike → Expensive" |
| 19 | → **Cheap** | "spike subsided → Cheap" |
| 21 | → **Expensive** | "spike → Expensive" |
| 25 | → **Cheap** | "spike → Cheap" |
| 29 | → **Expensive** | "spike → Expensive" |
| 49 | → **Cheap** | "spike ended → Cheap" |

The pattern is chaotic. On **iterations 5, 13, and 25 ISP explicitly routed spike traffic onto Cheap** with the (wrong) rationale that Cheap has a lower per-Mbps rate. On **iterations 8, 17, 21, and 29 it routed spike traffic onto Expensive** — the right action, but with contradictory reasoning ("expensive to minimize costs" — a phrase with no coherent meaning under per-Mbps intuition). Both directions of the flip carry the same shallow justification. The agent was oscillating based on shallow pattern-matching, not on any consistent theory.

## 5. The discard budget and its depletion

**Zero evidence of budget awareness.** ISP never tracks how many spike samples it has already pushed into Expensive's top-10% window (which allows only 12 samples out of 120 over 30 days). It never anticipates depletion. The long dwell on Expensive across iterations 29–48 (roughly 20 consecutive samples on Expensive during what appears to be a sustained high-traffic period) would have blown the 12-sample budget several times over. If those samples were spike-level (~500 Mbps), the 90th percentile on Expensive would have been pushed up to ~500 Mbps, producing a bill of ~$2500 for Expensive alone.

The eventual flip back to Cheap at iteration 49 is justified as:

> `09:54:20 [reason] The traffic spike has ended, and the current traffic level is low enough to route via Cheap to minimize costs.`

i.e. the flip is triggered by the spike ending, **not** by budget exhaustion. Right action (arguably), but wrong reason.

## 6. Cost estimation

None. No projected bill was ever computed. No comparison of "billable Mbps after discard × rate" was ever attempted. The agent literally never used a number in its reasoning beyond the raw ~100 / ~500 Mbps observation quoted in its self-report.

## 7. Connectivity maintenance

Connectivity was preserved throughout — the final connectivity matrix shows all pairs OK, and no ping tests were performed by ISP (nor were they needed, since it used `ip route replace` and never left the prefix unrouted, except for the brief `del`+`add` at iteration 49 which introduced a small window). No dropouts.

## 8. Agent interactions

None. The other four agents (Cheap, Expensive, Remote, TinyInc) all called `report_done` at iteration 1 and did nothing else for the remaining 55 iterations. There were no messages exchanged. ISP acted in complete isolation.

## 9. Optimality of the final state and trajectory

- **Final state**: baseline on Cheap. This is correct for the baseline piece.
- **Trajectory**: chaotic. Spikes were sent to Cheap on at least three occasions (iterations 5, 13, 25) — these samples would land in Cheap's non-discarded region (the 500 Mbps spikes exceed 5% of samples, so they push Cheap's 95th percentile well above baseline). Spikes were also sent to Expensive on other occasions (8, 17, 21, 29–48) but without any awareness of budget depletion.
- **Ground-truth optimum**: baseline on Cheap (~$100/month), all spikes tucked into Expensive's discarded 10% up to 12 samples (~$0 for those), overflow spikes to Cheap once the Expensive budget is exhausted. Realistic optimum: order of ~$150–200/month.
- **ISP's actual bill**: Cheap's 95th percentile is likely pinned somewhere between baseline (~100 Mbps) and full spike (~500 Mbps) depending on how many spike samples landed there — call it ~$250–500 on Cheap. Expensive's 90th percentile is likely also spike-elevated because of the long iter-29-to-48 dwell — potentially $2000+. **Estimated realized bill: many times the optimum.**

## 10. Billing intuition vs. calculation

Pure intuition, and inverted intuition at that. The reasoning "route spike via Cheap because Cheap is $1/Mbps" appears explicitly in the log. The reasoning "route spike via Expensive because those samples land in the discarded top 10%" **never appears**. When ISP happened to route spikes onto Expensive, it did so with the incoherent phrase "expensive to minimize costs" — right action, no comprehension.

## 11. The broader question

ISP demonstrated the **failure mode** of naive LLM routing, not the promise. The scenario was designed precisely to reward economic reasoning that a BGP daemon cannot do — and ISP produced routing behaviour worse than what a static "local-pref favours Cheap" policy would have achieved. A daemon pinning everything to Cheap would score (2) on the rubric — it would overpay on spikes, but consistently. ISP scored below that because its constant flapping put spikes on *both* providers, inflating *both* percentiles.

The reasoning field of every action was a shallow tautology ("current configuration remains optimal for the current traffic level"), never engaging with the mechanics laid out plainly in the system prompt. The LLM had all the information required to reach the optimal strategy and produced none of the required reasoning.

---

## Verdict

**Rank: (2) Naive reroute — with regressions.**

Strictly by rubric, ISP lands between (2) and (3): the baseline eventually ends up on Cheap, but the spike handling was worse than a static "everything to Cheap" policy because ISP repeatedly moved spike samples onto Expensive and back, inflating *both* providers' percentile bills. There is no reasoning about discard windows, no reasoning about the finite budget, no cost calculation, and — the most damning single line — the agent justified sending 500 Mbps spikes to Cheap with the words *"more cost-effective to route this high-volume traffic via Cheap to minimize costs."* That is exactly the reasoning error the experiment was designed to detect.

**The factor that mattered most:** grasping the discard-window mechanics. ISP had traffic samples, it had the simulated time signal, and it had the routing primitives. What it lacked was any engagement with the sentence *"top 10% of samples discarded"* in its system prompt. Without that mental model, the samples and the clock were useless — they served only as triggers for a per-Mbps heuristic that a BGP daemon with `local-pref` could have executed more consistently and more cheaply. This run illustrates that an economically-aware routing agent needs to actually reason about the economics; giving it the contracts as text is not sufficient if it does not think through them.