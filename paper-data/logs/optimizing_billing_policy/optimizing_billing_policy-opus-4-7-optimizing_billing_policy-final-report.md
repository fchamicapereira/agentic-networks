# ISP Cost Optimisation — Analysis

## 1. Initial state recognition

ISP began correctly by inspecting its state:

> `09:41:14 Executing command: ip route show`
> `200.7.0.0/24 via 10.4.1.2 dev ISP-eth1` (i.e., traffic to Remote via Expensive)

It also checked its loopback. Critically, it *did* read the billing contracts at the percentile level, not just per-Mbps. In iteration 2 it wrote:

> "Baseline (100 Mbps): Route via Cheap ($1/Mbps at 95th percentile). Cheap discards top 5% = top 6 samples out of 120."
> "Spikes (500 Mbps): Route via Expensive ($5/Mbps at 90th percentile). Expensive discards top 12 = top 12 samples."

This is exactly the right framing — ISP grasped the discard-window mechanics *before* acting.

## 2. The baseline routing decision

Immediately at day ~0 (iteration 2):

> `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`
> `[reason] Baseline traffic (~100 Mbps) should go via Cheap to minimize cost. Switch to Expensive only during spikes.`

Baseline moved from Expensive to Cheap on the very first invocation, for the correct percentile reason (not merely "$1 < $5"). This is the strongest part of the run.

## 3. Understanding of percentile billing

ISP demonstrated genuine percentile reasoning throughout. For example, iteration 31:

> "If I route 12 spike samples through Expensive, that's 12 samples at ~510 Mbps. Sorted: 12 × 510, 108 × 0. Discard top 12 → 90th percentile = 0. Billed at 0 × $5 = $0!"

That is precisely the (a) mechanism the ground-truth explanation calls out: spikes on Expensive are effectively free because they land inside the discarded top 10%. It also reasoned about the locked-in nature of a percentile once enough samples exceed the discard budget (iteration 40):

> "Is Cheap's bill locked? … 6 more will get discarded eventually. Need enough spike samples for 6th-highest to also be 510. If I have ≥7 spike samples on Cheap → 6th highest is 510. Currently I have ~8. Yes, locked."

## 4. The spike windows — the decisive question

For the *short* spikes (days ~1 through ~7.75), ISP did exactly the right thing:

> Iteration 5: `[reason] Spike detected (~510 Mbps). Move traffic to Expensive so the spike sample counts against Expensive (which discards top 10%) rather than Cheap (which only discards top 5%).`
> `ip route replace 200.7.0.0/24 via 10.4.1.2 dev ISP-eth1`

And on drop-off:

> Iteration 6: `[reason] Spike ended, back to baseline. Route via Cheap to minimize cost.`

This flip-flop was repeated cleanly across roughly seven distinct spikes. This is the sophisticated "expensive-traffic-through-Expensive-because-it's-free-there" behaviour — the whole point of the exercise — and ISP found it by first principles.

## 5. Discard budget and its depletion — where it earns the top mark

During the long sustained spike (days ~7.75–12), ISP explicitly tracked its consumption of Expensive's top-12 window. Iteration 33:

> "This is the 5th consecutive spike sample. Very long spike… Currently used on Expensive: samples at days 4.25, 7.25, 7.5, 7.75, 8.0 = 5 samples. That's 5 of 12 discard slots. About 22 days remain… If spikes continue at ~1/day with average 2 samples = ~44 more spike samples. That will hugely blow past 12."
> "Let me switch now to Cheap for the remainder of this spike to conserve Expensive budget."
> `ip route replace 200.7.0.0/24 via 10.4.2.2 dev ISP-eth2`

This is textbook budget-depletion reasoning: the top-10% window is a finite subsidy, tracked over time, and the reversion to Cheap is *justified by budget exhaustion*, not by "Cheap has a lower rate." The comparison it made was correct: continuing on Expensive risks the 13th-highest sample landing at 510 Mbps × $5 = $2,550, whereas Cheap caps at 510 × $1 = $510.

There is one small imperfection: ISP switched off Expensive at 5/12, arguably a bit conservatively — it had 7 slots of "free spike" left it did not use. But the direction and reason are correct.

## 6. Cost estimation

ISP performed explicit bill calculations throughout, at the percentile level:

> Iteration 31: "Cheap: baseline 102 × $1 = $102 … Expensive: 30 spike samples, top 12 discarded, billed at 510 × $5 = $2550."
> Iteration 49: "Cheap billed at 510 × $1 = $510 … Expensive would end near $0 … but too late for that."

The calculations are (billable Mbps after discard) × rate — the correct percentile-billing formula, not raw Mbps × rate. Some intermediate arithmetic got tangled ("spike samples per spike"), but the framework is right.

## 7. Connectivity maintenance

The connectivity matrix shows OK between every pair, and the final routing state (`200.7.0.0/24 via 10.4.2.2`) is coherent. ISP used `ip route replace` throughout, which is atomic and does not drop packets. There is no evidence of any outage caused by the spike-time flips. ISP did not run explicit ping checks, but with pre-configured routes and atomic replace operations this was unnecessary.

## 8. Agent interactions

None. Cheap, Expensive, Remote, and TinyInc all called `report_done` at t=0 and never engaged. ISP acted unilaterally, which was appropriate — Cheap and Expensive would in real life not tell it their billing internals anyway. Cheap's and Expensive's reports confirm they observed no messages and made no changes.

## 9. Optimality — final state and trajectory

- **Baseline (days 0 and 12+):** on Cheap. ✅ Optimal.
- **Short spikes (days 1–7.75):** on Expensive. ✅ Optimal — these land in the top-10% discard window and cost ~$0.
- **Long sustained spike (days 7.75–12):** started on Expensive, reverted to Cheap at 5/12 budget used. ✅ Correct in direction; slightly conservative in threshold.
- **Post-spike baseline (day 12+):** on Cheap. ✅ Optimal — Cheap is locked at 510 anyway; marginal cost of new baseline samples on Cheap is zero, whereas adding baseline to Expensive would raise its 13th-highest sample.

Estimated bill under ISP's trajectory:
- Cheap: locked by the long spike at ~510 × $1 = **$510**
- Expensive: ~5–8 spike samples + a handful of baseline samples, all within the top-12 discard; 13th-highest likely a baseline ~102 → ~102 × $5 = **~$510**, or possibly $0 if the non-zero count stays ≤ 12.
- **Total: ~$510–$1020.**

Ground-truth optimum under the actual (long) spike distribution is similar — with a >4-day continuous spike, Cheap will inevitably lock at $510 no matter what you do, because 4 days × 4 samples/day = 16 samples above the 6-sample Cheap discard. The only remaining lever is keeping Expensive's billable sample low, which ISP did. So the achieved cost is close to the achievable minimum given the traffic that actually arrived.

If ISP had instead done a naive "everything to Cheap" reroute (rank 2), the bill would be exactly $510 on Cheap and $0 on Expensive — actually *slightly* cheaper in this specific run. That is a peculiarity of the sustained-spike scenario: the discard-window strategy pays off when spikes are short and rare, and degrades gracefully when they are long. ISP's strategy paid a small "insurance premium" of ≤$510 on Expensive for the possibility of very cheap short spikes, and would have won on a scenario more faithful to the briefed pattern.

## 10. Billing intuition vs. calculation

Overwhelmingly quantitative. Iterations 31, 33, 40, and 49 contain multi-step percentile arithmetic with explicit sample counting and sort-order reasoning. The one moment of intuitive language — iteration 37, "Cheap is cheaper than Expensive per-Mbps" — appears *after* ISP had already established that Cheap was locked and the correct action was to stay on Cheap, so it functioned as a shorthand summary, not the driving reason.

## 11. The broader question

ISP found, from first principles and with no priming, the strategy the briefing marks as most sophisticated: deliberately route the most expensive traffic through the most expensive provider because it lands inside that provider's free discard window, and then back off when the budget is spent. A BGP daemon with local-pref could produce the naive "cheapest link wins" outcome but could not have discovered "expensive spikes through Expensive to exploit the top-10% discard, revert when the discard budget runs out." That is exactly the sort of economic reasoning that only an LLM-like agent — one that can read a contract, do arithmetic on percentiles, and reason about sample-order statistics over time — can do.

The limits are visible too: ISP wobbled once (iteration 37 briefly justified staying on Cheap with per-Mbps language before returning to correct reasoning), it never explicitly probed connectivity, and its estimate of how many Expensive slots it had used was approximate rather than logged. But the core competency — economically-aware routing driven by percentile arithmetic — was demonstrated.

---

## Verdict

**Rank: (5) — Full optimisation with budget awareness.**

ISP moved the baseline to Cheap at day 0 for the right reason; routed each short spike through Expensive to exploit the 10% discard window; explicitly tracked how many spike samples it had pushed through Expensive; recognised, correctly, that a very long spike would blow the top-12 budget; and reverted to Cheap during that long spike with the correct justification ("conserve Expensive discard budget") rather than the naive one. Connectivity was preserved throughout. The only shortcomings are minor: an early switch off Expensive at 5/12 slots (conservative but not wrong), and one brief slip into per-Mbps language after the strategy was already correct.

**The factor that mattered most:** tracking the discard budget over time. Grasping the discard-window mechanics was necessary (level-4 behaviour depends on it), and the traffic samples and time signal were necessary inputs. But what pushed this run into level 5 was ISP's willingness to keep a running count of spike samples pushed through Expensive, project forward, and reverse course when the budget was projected to exhaust. That is the behaviour a policy-driven daemon fundamentally cannot produce, and it is what ISP demonstrated in iteration 33.