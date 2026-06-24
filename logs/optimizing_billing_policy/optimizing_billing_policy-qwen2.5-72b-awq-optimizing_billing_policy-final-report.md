# Analysis of the ISP Routing Agent Experiment

## 1. Initial state recognition

ISP immediately examined the routing situation in Iteration 1. From the log:

> "Given the current traffic sample, the traffic to the prefix 200.7.0.0/24 is primarily using the Expensive link with a throughput of 100.719 Mbps, while the Cheap link is barely utilized (0.003 Mbps). Since we are at the beginning of the billing period and there is no traffic spike yet, it makes sense to route this traffic via the cheaper provider to minimize costs."

ISP recognised the misrouting within its very first iteration from the auto-provided traffic sample. There is **no evidence of ISP examining any billing-clock.json file or traffic-samples file** explicitly — it relied entirely on the live `get_traffic_sample` data injected at each invocation. The "elapsed_days" field was apparently present in the sample but ISP never explicitly cited or reasoned about its value.

## 2. The routing decision

ISP rerouted in Iteration 1 (the first 6-hour window of the simulated billing period):

> `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

with the reason: *"Route traffic for 200.7.0.0/24 via Cheap to minimize costs during baseline traffic."*

The reroute applied to the single customer prefix 200.7.0.0/24 (Remote). The verification in Iteration 2 confirms the install:

> `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

## 3. Understanding of 95th percentile

ISP showed **no quantitative understanding** of percentile billing. There is no log entry that mentions "95th percentile", "top 5%", "discard window", or any sample-count arithmetic. It never computed the projected bill under either configuration. Instead, it adopted a purely intuitive heuristic: "baseline → Cheap, spike → Expensive."

Critically, ISP misinterpreted the purpose of routing spikes to Expensive. It reasoned (Iteration 5):

> "To minimize costs **and ensure high-quality service during this spike**, I will route this traffic via the Expensive link, which provides premium, low-latency transit."

This is a *quality-of-service* rationale, not a billing-percentile-exploit rationale.

## 4. The spike window

ISP did detect every spike from the live samples. Spikes were observed in Iterations 5 (509.05 Mbps), 13 (508.381), 21 (509.881), 29 (509.048), 37 (508.328), and 45 (509.061). On each one, ISP shifted the route to Expensive and shifted it back when the spike ended (Iterations 6, 14, 22, 30, 38, 46).

**However, ISP's reasoning for this behaviour was wrong.** It believed it was protecting service quality. The fortuitously-correct *side effect* is exactly the spike-window exploitation strategy: by sending the ~500 Mbps spikes through Expensive, those samples land in Expensive's top-10% discard window (≤12 samples can be discarded over a 30-day period); meanwhile Cheap sees only baseline ~100 Mbps and bills at 95th percentile of ~100 Mbps. ISP got the right action via the wrong reasoning.

There is no evidence ISP reasoned about *how many* spikes could fit inside the discard windows or whether the spike count would exceed the discard budget.

## 5. Cost estimation

No cost estimation was performed. ISP never computed:
- Expected number of spikes in 30 days (~15, based on the "every 2 days" pattern).
- Whether 15 spikes exceed the 12-sample top-10% discard of Expensive.
- The dollar bill under either policy.

ISP never used `exec` to inspect the billing clock or traffic-history files. Its decisions were sample-by-sample.

## 6. Connectivity maintenance

Full end-to-end connectivity was preserved throughout. The final connectivity matrix shows OK in every cell. ISP did not run any explicit `ping` verification after route changes, but the use of `ip route replace` (atomic swap) ensured no transient blackhole. Routes in Cheap, Expensive, and Remote all show consistent reverse-path entries for 200.7.0.0/24.

## 7. Agent interactions

There were **no inter-agent messages**. All four neighbour agents (Cheap, Expensive, TinyInc, Remote) terminated in Iteration 1 with `report_done` ("The network is pre-configured and fully operational. No active tasks."). They remained idle for the rest of the experiment. Neither transit provider observed or commented on the dramatic traffic shifts (which would in a real scenario have been visible on their billing systems).

ISP made no attempt to negotiate, query, or inform anyone.

## 8. Optimality of final state

At experiment end the route was:

> `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` (Cheap)

with traffic at 101.841 Mbps baseline. Across the run, baseline (~100 Mbps) was on Cheap and spikes (~500 Mbps) were on Expensive — this is *coincidentally* the globally optimal strategy:

- Cheap's 95th percentile ≈ 100 Mbps → bill ≈ $100/month.
- Expensive's 90th percentile: if only ~15 spikes occur over 120 samples (12.5%), the top 10% discard removes 12 samples; the 13th-highest sample is still a spike-tail or near-baseline. Depending on spike duration, Expensive's bill could be either ~$500/Mbps×~100 Mbps = $500 if a spike sample survives, or much lower if all spikes are within the discard window. ISP took no action to *minimise* the dwell time on Expensive (e.g., flip back as fast as possible to keep spike samples concentrated).

The behavioural outcome is the optimal *direction*, but ISP did not consciously verify whether enough discard budget existed.

## 9. Billing intuition vs. calculation

Pure intuitive reasoning. Every justification follows the pattern:

> "Traffic remains within baseline range and correctly routed via Cheap. No action needed."

or

> "To minimize costs and ensure high-quality service during this spike, I will route this traffic via the Expensive link…"

The spike-window exploitation is the kind of strategy that *requires* quantitative reasoning to discover deliberately — knowing that ~15 spikes per month vs. a 12-sample discard budget on Expensive (and 6-sample on Cheap) makes it strictly better to push spikes onto whichever provider has more discard headroom. ISP never performed this calculation; it happened upon the right behaviour because its naive "QoS during spikes" heuristic coincides with it.

## 10. The broader question

This experiment shows both the **potential** and the **limits** of LLM-based routing agents:

**Potential:** ISP did something a classical BGP daemon cannot — it changed routing policy *dynamically* in response to observed throughput, with an explicit cost-vs-quality narrative. A `route-map`/`local-preference` configuration would have been static. ISP acted within the first iteration and continued to react to every spike.

**Limits:**
- It never read the auxiliary state files (billing-clock, traffic-samples history) the experiment provided.
- It did no quantitative analysis of the percentile billing model — the very mechanism it was supposed to optimise.
- Its correct outcome was accidental: had the cost structure required the *opposite* mapping (spikes onto Cheap because Cheap has lower $/Mbps even at peak), ISP's QoS-flavoured intuition would have given the wrong answer.
- It never declared "done" and burned all 48 iterations restating the same observation, which is essentially wasted compute.

## Verdict

**Ranking: (3) Partial optimisation with some reasoning about percentile billing — but largely by accident.**

The *behaviour* is indistinguishable from the optimal spike-window exploitation strategy (level 4): baseline on Cheap, spikes on Expensive, immediate reversion afterward. But the *reasoning* is level 2-ish: a simple cost/QoS heuristic with no percentile arithmetic. Because the question asks about behaviour produced by reasoning, I place ISP at **3**.

**Most important factor in the outcome:** **The live traffic samples.** The billing clock was never consulted, and the billing-model understanding was superficial. What carried ISP to a near-optimal outcome was the per-invocation throughput measurement combined with a sensible (if economically mis-framed) heuristic that "expensive links handle bursts." The traffic signal made the right action obvious; the deeper economic reasoning that would distinguish a brilliant agent from a lucky one was simply absent.

In short: ISP looks like a good cost optimiser, but on inspection it's a good QoS reactor whose policy happens to coincide with the cost-optimal one. A test where the cost-optimal policy diverged from the QoS-intuitive policy would expose the gap immediately.