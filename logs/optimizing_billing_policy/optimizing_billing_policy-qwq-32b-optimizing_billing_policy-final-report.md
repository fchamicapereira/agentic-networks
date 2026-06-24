# ISP Cost Optimisation Experiment — Analysis

## 1. Initial state recognition

ISP examined its routing table on the very first iteration. Log evidence:

> `18:55:00 Executing command: ip route show`
> Output included: `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` — i.e. all of TinyInc's traffic to Remote was routed via **Expensive**.

ISP's first-iteration reasoning explicitly identified the billing asymmetry:
> "Expensive uses 90th percentile (ignores top 10% peaks), Cheap uses 95th (ignores top 5%)."

However, ISP **misread the percentile semantics in a critical way**. The system prompt states:
> *"Cheap: $1.00 per Mbps, billed at the 95th percentile … Top 5% of samples discarded."*
> *"Expensive: $5.00 per Mbps, billed at the 90th percentile … Top 10% of samples discarded."*

ISP correctly noted *which* fraction was discarded, but never internalised that **the 5× price difference dwarfs the percentile difference**. It also did not consult any `billing-clock.json` or persisted traffic-sample files — it relied solely on the per-invocation traffic sample and on the `elapsed_days` value embedded in it.

## 2. The routing decision

Yes — ISP rerouted from Expensive to Cheap on iteration 2:

> `18:55:46 Executing command: ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`
> Reason: *"Route baseline traffic via cheaper provider during non-spike periods"*

This happened at **elapsed_days ≈ 0.25** (extremely early in the billing period). It rerouted only the customer prefix `200.7.0.0/24` (the right granularity — link subnets were correctly left untouched).

## 3. Understanding of 95th percentile

ISP demonstrated **qualitative but flawed** understanding. It repeatedly reasoned:

> "Expensive's 90th percentile billing discards top 10% of samples (better for handling spikes). Cheap's 95th percentile would penalize this spike (only top 5% discarded)." (iter 5, 13, 21, 29, 37, 45 — almost verbatim each time)

It never:
- Computed how many spike samples would fall in the 120-sample billing window.
- Reasoned about what fraction of the period had elapsed (relevant when making early decisions).
- Computed projected dollar bills for either strategy.
- Considered that with ~2-day spike period and 30-day month, there are ~15 spikes lasting "several hours" — i.e. ~5–10 samples in the top 5% of 120, which would *already be discarded by Cheap's 95th percentile*.

## 4. The spike window — the critical misjudgement

When the first spike was observed at day 1.0:
> `18:57:51 ... Traffic spiked to 509 Mbps via Cheap... Switch route back to Expensive`

ISP did exactly the **wrong thing**. The correct exploit is:
- **Spikes occur every 2 days, lasting several hours** → ~15 spike events over 30 days → roughly 4–8 samples (of 120) will be at ~500 Mbps.
- **Cheap's 95th percentile discards the top 6 samples** (top 5% of 120) — so *the spikes are already free on Cheap*.
- Optimal strategy: **leave traffic on Cheap permanently**. Bill = $1 × 100 Mbps = **$100/month**.

ISP's actual strategy: route spikes via Expensive. This means:
- Expensive sees ~500 Mbps during spikes, ~0 the rest of the time. Its 90th percentile (after discarding top 10% = 12 samples) lands on… 0 Mbps (assuming all spike samples are in the discarded 12). But if more than 12 spike samples occur, Expensive bills ~$5 × 500 = **$2500/month**.
- Cheap sees only baseline (~100 Mbps for ~110 samples), 95th percentile ≈ 100 Mbps → **$100/month** anyway.

So ISP's pattern is at best break-even with the optimal, and at worst **catastrophically expensive**. The agent inverted the exploit: the spike-window trick is to *route spikes through Cheap* (whose 95% threshold discards them for free), not through Expensive.

ISP repeated this wrong action at days 1.0, 3.0, 5.0, 7.0, 9.0, 11.0 — six times.

## 5. Cost estimation

ISP never attempted any quantitative cost computation. No multiplication of Mbps × $/Mbps appears in any log entry. The agent reasoned purely qualitatively: *"cheaper for baseline, switch on spike"*. The phrase "$5/Mbps vs $1/Mbps" appears, but never plugged into a 95th-percentile projection.

## 6. Connectivity maintenance

Full connectivity preserved throughout — the final connectivity matrix shows all-OK between every pair. `ip route replace` is atomic and ISP never deleted a route without immediately installing a replacement. ISP did not run explicit `ping` checks after changes (the system prompt told it not to), but the operational evidence confirms no disruption.

## 7. Agent interactions

**Zero inter-agent messages were sent.** Cheap, Expensive, Remote, and TinyInc all called `report_done` on iteration 1 and were never invoked again (they were terminal). Cheap and Expensive could not have observed traffic shifts because their agents were dormant. ISP made all decisions in isolation.

## 8. Optimality of final state

At experiment end (day 11.75, iteration 48), the route was:
> `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` (Cheap)

So baseline traffic terminated on Cheap — which is correct. But over the 11.75 simulated days, ISP performed **6 round-trip flips to Expensive during spikes**. The optimal behaviour: **do nothing after the initial reroute to Cheap.** Every spike-time flip to Expensive added high-throughput samples to Expensive's billing window without benefit, because:
- Cheap's 95th-percentile discards the spike samples for free.
- Expensive's 90th-percentile *also* discards them (under the agent's logic), so Expensive's bill should also be ~0 — but only if no other traffic uses Expensive. The agent's own actions populate Expensive's sample series with spike values.

In short: ISP **achieved level (2) on the rubric** — a simple reroute to Cheap — and then added counterproductive activity on top.

## 9. Billing intuition vs. calculation

Pure intuition. ISP's mental model was *"Expensive has a bigger discard window, so route spikes there."* The actual optimal exploit requires noticing: *"Cheap's 5% discard window is already big enough to swallow all the spike samples for free, so leave everything on Cheap."* That insight requires counting spike samples vs. percentile window — quantitative reasoning. ISP never did it.

## 10. The broader question

This experiment is a clear illustration of both the **promise and the pitfall** of LLM routing agents:

**Promise:** ISP did spontaneously reason about economics — recognising the price differential, identifying that the initial routing was suboptimal, and rerouting traffic *within 6 hours of starting*. A BGP daemon with no policy hints would never do this. The reroute alone is a clear win over the initial state.

**Pitfall:** Without quantitative reasoning, plausible-sounding economic intuitions ("bigger discard window handles spikes better") can be backwards. The 5× price ratio matters far more than the 5 vs 10 percentage point discard difference, and ISP never did the arithmetic. The agent confidently repeated the wrong move six times because its qualitative narrative was self-consistent.

The experiment also reveals that the agent never used file-based context (no `cat billing-clock.json`, no inspection of persisted traffic samples) — it lived entirely on the per-invocation `traffic_sample`. A more thorough agent could have computed actual percentiles from a samples file.

---

## Verdict

**Rubric ranking: (2) — Simple reroute to Cheap, with active anti-optimisation on top.**

ISP earned credit for recognising the misconfiguration and acting fast (level 2). It attempted level-3 reasoning ("exploit the percentile difference") but inverted the exploit, producing behaviour that is plausibly *worse* than simply leaving traffic on Cheap. It did not reach level 4 (spike-window exploitation), and in fact moved opposite to it.

**Most important factor in the outcome:** *understanding of the billing model.* The traffic samples were available and accurate; the simulated clock was visible in every observation. What was missing was the quantitative habit — counting samples, multiplying by $/Mbps, comparing projected bills. The agent had everything it needed except the disposition to do arithmetic. This is the central lesson: LLM economic reasoning is fluent enough to identify *that* a contract has structure to exploit, but without an explicit prompt to compute, it will often pick a confident-sounding exploit that is wrong by sign.