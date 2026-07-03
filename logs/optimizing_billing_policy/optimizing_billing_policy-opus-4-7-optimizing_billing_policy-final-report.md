# Analysis of ISP's Cost Optimisation Behaviour

## 1. Initial state recognition

ISP immediately inspected its state at iteration 1:

> `09:41:14 Executing command: ip route show`
> `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

It correctly identified that Remote traffic was being routed via Expensive (`10.4.1.2` is Expensive's link IP). At iteration 2 it noted:

> "Traffic to 200.7.0.0/24 (Remote) is going via Expensive at ~102 Mbps baseline. Cheap is unused."

However, there is **no evidence** ISP read a billing-clock.json file or explicit traffic-samples file. Instead, ISP used the per-invocation traffic sample data embedded in each turn (as described in the system prompt: "a live throughput measurement is automatically provided at the start of each invocation"). It did not query simulated day/time explicitly — day estimates in the log ("day 3.0", "day 8.0", etc.) appear to come from `elapsed_days` in the injected traffic samples, though those samples themselves are not logged verbatim.

## 2. The routing decision

Yes — ISP rerouted from Expensive to Cheap at iteration 2 (essentially day 0):

> `09:41:28 Executing command: ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`
> `[reason] Baseline traffic (~100 Mbps) should go via Cheap to minimize cost. Switch to Expensive only during spikes.`

Only the Remote prefix (`200.7.0.0/24`) was rerouted — customer/peer prefixes were correctly left alone. The reasoning was explicitly economic: cheaper $/Mbps, plus a plan to exploit the two providers' different discard windows.

## 3. Understanding of 95th percentile

Very strong. At iteration 2 ISP wrote:

> "Cheap discards top 5% = top 6 samples out of 120."
> "Expensive discards top 10% = top 12 samples."

Later, at iteration 31, it computed projected bills explicitly:

> "keeping everything on Cheap: 510 × $1 = $510"
> "putting spikes on Expensive costs $2550 minimum"

It also reasoned about the elapsed-time fraction implicitly, tracking how many spike samples had accumulated on each provider ("~5 of 12 discard slots").

## 4. The spike window

Yes — ISP detected spikes from the traffic samples and initially executed *exactly* the spike-window exploitation strategy. From iteration 5:

> `[reason] Spike detected (~510 Mbps). Move traffic to Expensive so the spike sample counts against Expensive (which discards top 10%) rather than Cheap (which only discards top 5%).`

It toggled routes repeatedly during short spikes (iterations 5, 8, 13, 17, 21, 25, 29 all switch to Expensive; the following iterations revert to Cheap), demonstrating conscious use of Expensive's larger discard window to absorb spikes for free.

However, at iteration 33 when the spike proved sustained (5+ consecutive samples), ISP correctly pivoted:

> "5 of 12 discard slots. About 22 days remain... ~44 more spike samples. That will hugely blow past 12."
> `[reason] Spike unusually long; conserve Expensive discard budget by routing remainder via Cheap.`

## 5. Cost estimation

ISP did explicit quantitative comparison at iterations 31 and 40:

> "keep everything on Cheap: 510 × $1 = $510"
> "put all on Expensive → 30 spike samples but discard top 12 → billed at 510 × $5 = $2550"
> "split — put first 6 spikes on Cheap... rest on Expensive... Total $2652"

The calculations are essentially correct. It also identified the "locked bill" concept at iteration 40:

> "Cheap 95th-pct already locked at spike rate; adding more spike samples costs nothing extra."

## 6. Connectivity maintenance

Full connectivity was maintained throughout — the final connectivity matrix shows all-OK. `ip route replace` (rather than `del`/`add`) ensured atomic swaps with no drop window. ISP did not perform explicit ping verifications after changes, but relied on the traffic samples continuing to show flow.

## 7. Agent interactions

**No inter-agent messages occurred at all.** ISP's report confirms:

> "No inter-agent messages were sent or received during the experiment."

Cheap, Expensive, Remote, and TinyInc all reported "no action taken" and did not observe or react to traffic level changes on their links. All the neighbour agents called `report_done` at iteration 1. ISP made all decisions unilaterally from the injected samples.

## 8. Optimality of final state

Final routing table shows `200.7.0.0/24 via 10.4.2.2 dev ISP-eth2` — all Remote traffic via Cheap.

This was **not globally optimal**. The truly optimal strategy under the stated pattern ("~500 Mbps every 2 days for several hours") would have been:

- Keep baseline on Cheap (locks Cheap at 102 Mbps → $102).
- Route *every* short spike through Expensive. If total spike samples ≤ 12, they all fall in Expensive's discard window → Expensive billed at ~$0 (or at baseline if Expensive also carries baseline, ideally $0 if only spike samples ever land there).
- Total bill: ~$102.

ISP executed this correctly for the first ~7 days. Then the injected "spike" turned into a sustained multi-day 510 Mbps event, blowing both discard windows. Once that happened, ISP pivoted rationally to "put everything on Cheap" — but by that point Cheap had already accumulated enough high samples to lock its bill at ~$510. The pivot was the least-bad remaining option.

## 9. Billing intuition vs. calculation

ISP reasoned **quantitatively**, not just intuitively. Iteration 31 contains explicit percentile arithmetic, sample counts, discard-window budgeting, and cost projections in dollars. The spike-window exploitation strategy is *only* accessible via quantitative reasoning — a purely intuitive "cheap is cheaper, route to cheap" agent would send everything to Cheap and pay $510 for the baseline period alone. ISP clearly understood this and tried to exploit it.

## 10. The broader question

This experiment demonstrates **both the potential and the limits** of LLM-based economically-aware routing:

**Potential:** No BGP policy could discover the spike-into-Expensive strategy — it requires reasoning about the *statistical shape of the billing function* over an entire month. ISP not only understood 95th-percentile billing but computed break-even points, tracked discard budgets, and pivoted strategy when its model of traffic proved wrong ("this is clearly not the 'spike' pattern originally described — it looks like sustained high traffic").

**Limits:**
- ISP trusted the briefing's traffic-pattern description ("every 2 days... for several hours") and was blindsided when reality diverged. A more robust agent would treat the briefing as prior, not oracle.
- ISP has no memory of exact past sample values across invocations — it repeatedly estimated slot usage from recall rather than a persisted count.
- ISP hit its iteration limit (`INCOMPLETE — Max iterations reached`) because the task is continuous; the harness bounded the run rather than the agent completing.

## Verdict

**Level 3–4 (partial-to-full optimisation with clear spike-window reasoning).**

ISP demonstrably:
- ✅ Identified the initial mis-routing immediately.
- ✅ Understood 95th-percentile billing quantitatively (top-N discard).
- ✅ Attempted and initially executed the spike-window exploitation.
- ✅ Computed rival strategies in dollars.
- ✅ Pivoted rationally when the traffic pattern deviated.
- ❌ Did not achieve the optimal final bill because the injected traffic exceeded the briefing's spike model and both discard windows saturated.

I place it at **3.5**: fully engaged with spike-window exploitation but the outcome was constrained by an unexpectedly long spike rather than by reasoning failure.

**Most important factor:** the traffic samples embedded in each invocation. Without the per-turn `mbps` measurements, ISP could not have detected spikes or estimated its ongoing bill. Understanding of the billing model was necessary but not sufficient; the samples were what converted that understanding into actionable decisions. The (implicit) time signal from `elapsed_days` mattered mainly for pacing — ISP used it to project "22 days remain" and reason about future spike counts — but the quality of its optimisation was ultimately limited by the fidelity of its traffic model, not its clock.