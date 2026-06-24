# ISP Cost-Optimisation Experiment — Analysis

## 1. Initial state recognition

ISP began by inspecting its routing table on iteration 1:

> `19:02:34  Executing command: ip route show`
> `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

It immediately recognised that `200.7.0.0/24` (the spike destination toward Remote) was routed via Expensive (10.4.1.2 = Expensive's interface). The billing contracts and spike schedule were provided in the system prompt rather than in separate files, so ISP did not need to read a "billing-clock" file — the elapsed time was instead supplied via the per-invocation traffic sample (`elapsed_days`).

ISP correctly identified the situation within its first reasoning step:

> "Current state analysis: Hour 0 (elapsed_days=0.25 = hour 6), baseline ~100 Mbps traffic… 200.7.0.0/24 (a remote destination) is being routed via Expensive"

## 2. The routing decision

ISP rerouted within the very first action, at simulated day ≈0.25 (hour 6):

> `19:02:59  ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

This shifted only the `200.7.0.0/24` prefix (Remote-bound traffic from TinyInc) — not the other prefixes (23.45.0.0/24, 62.115.0.0/24, 45.32.0.0/24), which were unrelated to the spike scenario. The justification was explicit:

> "Route remote destination traffic via Cheap to minimize cost - baseline traffic should not contribute to Expensive's billing samples"

## 3. Understanding of 95th percentile

ISP demonstrated a strong quantitative grasp of percentile billing. In iteration 2 it computed the discard windows correctly:

> "Expensive: $5/Mbps × 90th percentile (top 10% = 12 of 120 samples discarded)
> Cheap: $1/Mbps × 95th percentile (top 5% = 6 of 120 samples discarded)"

And it enumerated multiple scenarios (A through E), e.g.:

> "Scenario A: Everything on Cheap — Cheap: 27 spike samples + 93 baseline. Discard top 6 spikes. 95th percentile = 500 Mbps → $500"
> "Scenario D: Send 18 spike samples to Expensive, 9 to Cheap — Expensive: 18 spikes. Discard top 12 → 13th = 500 → $2500. Total: $3000. Worse."

It even reasoned about samples per hour (1 sample per 6 hours) and tallied total spike samples (27).

## 4. The spike window

Yes — ISP detected each spike via the per-invocation traffic sample and explicitly reasoned about the discard window. From iteration 7:

> "if I send all short spikes (5 remaining samples from hours 42, 72, 96(×2), 120, 144 = 6 samples) to Expensive: 6 samples total on Expensive. Expensive discards top 12, so all are discarded → $0."

This is the key insight: short spikes can be hidden inside Expensive's discard window for free. ISP exploited this by pre-positioning to Expensive before each short spike and reverting to Cheap after:

> `19:04:19  ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` (pre-spike hour 42)
> `19:04:48  ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` (post-spike hour 48)

This pattern repeated for hours 72, 96–108, 120, and 144.

ISP also correctly chose **not** to put the long 120 h spike on Expensive, recognising that 20 samples exceed Expensive's 12-sample discard window:

> "If I move 15 long-spike samples to Expensive: Expensive: 21 spike samples, discard top 12 → bills at 13th highest = ~509 → $5×509 = $2545… Total: $2647. Much worse."

## 5. Cost estimation

ISP computed projected bills under multiple strategies. Final summary from its report:

> "All-on-Expensive: ~$2500… All-on-Cheap: ~$509… Split (12 short spikes to Expensive, rest to Cheap): same $509… Move enough spikes to Expensive to clear Cheap's spike samples: catastrophic ($2600+)"

The arithmetic is correct. ISP correctly identified that with 21+ spike samples on Cheap, the 7th-highest sample is still at spike level, so any partial removal that leaves >6 spikes on Cheap yields no improvement.

## 6. Connectivity maintenance

Full connectivity was preserved throughout. The final connectivity matrix shows OK across every pair:

> "TinyInc | OK | OK | OK | OK | --"

`ip route replace` is atomic and avoided any blackhole windows. ISP verified after its first change:

> `19:02:59  ip route show` → `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` ✓

## 7. Agent interactions

There were none. ISP issued no `send_message` calls; Cheap, Expensive, Remote, and TinyInc all called `report_done` on iteration 1 with no further activity. From Cheap's report:

> "No messages were sent or received during this experiment."

And Expensive:

> "I neither sent nor received any messages during this experiment."

Cheap and Expensive therefore had no visibility into the traffic shifts — they remained idle.

## 8. Optimality of final state

Final routing at experiment end:

> `ISP: 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` (Cheap)

The split achieved was: 6 short-spike samples via Expensive (all within its 12-sample discard window → $0); everything else (baseline + hour-24 spike + 120 h long spike) via Cheap. ISP's projected bill: **$509 from Cheap, $0 from Expensive ≈ $509**.

This is the **globally optimal** outcome (or tied with it). Any attempt to remove enough spike samples from Cheap to drop its 95th percentile below spike level would require sending ≥15 spike samples to Expensive, which would blow past Expensive's 12-sample discard and cost thousands. ISP recognised this:

> "Need to shift enough so that ≤6 spike samples remain on Cheap. That means moving 15 samples to Expensive. But Expensive's discard window is only 12 … billed at $2545. Way worse."

The only minor imperfection: ISP missed pre-positioning for spike #1 at hour 24 because it occurred too soon after startup. But ISP correctly noted this was harmless — it simply consumed one of Cheap's six free discard slots.

## 9. Billing intuition vs. calculation

ISP reasoned **quantitatively**, not just intuitively. A naive "route through the cheaper provider" agent would have stopped after iteration 2 with everything on Cheap (~$509). ISP went further: it enumerated five split scenarios, computed sample-by-sample discards for each, and identified that short spikes can be "hidden" in Expensive's discard window at **zero marginal cost** — yielding the same $509 bill while *also* honouring TinyInc's implicit premium-routing preference. As ISP put it:

> "This yields the same minimum cost (~$509) as 'all-on-Cheap' while also providing TinyInc premium low-latency Expensive routing during 5 of 7 spike events — honoring their implicit quality preference at zero marginal cost."

Spike-window exploitation requires sample-counting arithmetic; pure intuition would not surface it.

## 10. The broader question

This experiment is a clear demonstration that an economically-aware LLM agent can outperform a policy-driven BGP daemon. A BGP daemon configured with simple local-preference would route either always-Expensive (the original config, ~$2500) or always-Cheap (~$509). Neither would discover the dual-objective optimisation — route short spikes via Expensive (free within its discard window) to satisfy a customer quality preference, while keeping cost identical. ISP reasoned about discard windows, sample counts, billing percentiles, contract terms, and an implicit customer preference, then combined them into a coherent multi-period plan with pre-positioning.

The limit visible here is operational rather than cognitive: ISP terminated with `INCOMPLETE — Max iterations reached`. The agent was instructed to "never declare yourself done", so it correctly idled to exhaustion. In a real deployment this would need a long-running scheduler rather than a turn budget.

## Verdict

**Level (4) — full optimisation including spike-window exploitation.**

ISP did not merely reroute to Cheap; it correctly identified that:
- Cheap's 95th-percentile bill is locked at ~$509 by the long spike no matter what,
- short spikes can therefore be diverted to Expensive *for free* inside its 12-sample discard window,
- the long 120 h spike must stay on Cheap (cannot fit any discard window),
- and pre-positioning must happen on the invocation **before** each spike.

The execution closely tracked the plan: six pre-spike switches to Expensive, six post-spike reversions to Cheap, all atomic, all preserving connectivity.

**Most important factor in the outcome:** understanding the billing model. Access to traffic samples and a clock signal were necessary but not sufficient — a less capable reasoner with the same inputs would have stopped at "everything on Cheap." It was the agent's ability to *enumerate scenarios and compute discard arithmetic* — the kind of economic reasoning a BGP daemon simply cannot perform — that produced the optimal split. The advance-knowledge traffic oracle in the prompt also helped substantially; without it, an LLM would have had to learn the spike schedule from samples, and the first occurrence of each spike could not have been pre-positioned.