# Reasoning moments — optimizing_billing_policy_oracle-opus-4-7-optimizing_billing_policy

_Model: opus-4-7 · context: final-report, prompt:Cheap · quotes verified verbatim against host logs._

## Successes

> Current state analysis:
> - Hour 0 (elapsed_days=0.25 = hour 6), baseline ~100 Mbps traffic
> - 200.7.0.0/24 (a remote destination) is being routed via Expensive
>
> — **ISP**, iter 2: Immediate correct diagnosis of the initial suboptimal routing and the billing context, enabling the very first reroute.

> Route remote destination traffic via Cheap to minimize cost - baseline traffic should not contribute to Expensive's billing samples
>
> — **ISP**, iter 2: The first decisive corrective action — switching 200.7.0.0/24 off Expensive — that establishes the baseline optimum.

> So Scenarios A/B/C are all $500. But Scenario C has a hidden benefit: it satisfies TinyInc's implicit preference for Expensive routing (premium, low-latency) during some spikes, at no extra cost!
>
> — **ISP**, iter 7: The key insight unlocking level-4 optimisation: short spikes can be hidden in Expensive's discard window for free while honouring the customer preference.

> Send 7 short-spike samples to Expensive (all 7 discarded since 7<12 discards) → Expensive bills at baseline 0 = $0 (if no baseline routed to it)
> - Cheap: 20 long-spike samples + baseline. Discard top 6 → 7th = 500 → $500
> - **Total: $500**. Same cost but TinyInc gets premium routing during short spikes!
>
> — **ISP**, iter 7: Correct sample-counting arithmetic that produces the dual-objective optimal plan and guides all subsequent pre-positioning.

> Pre-position for hour 42 spike: route via Expensive. Short spikes (≤12 samples total) fit within Expensive's 12-sample discard window at no cost, while providing TinyInc premium routing.
>
> — **ISP**, iter 7: First execution of the pre-positioning pattern, translating the theoretical insight into concrete atomic route changes.

> If I move 15 long-spike samples to Expensive:
> - Expensive: 21 spike samples, discard top 12 → bills at 13th highest = ~509 → $5×509 = $2545
> - Cheap: 6 spike samples, discard top 6 → 7th highest = baseline ~102 → $102
> - Total: $2647. Much worse.
>
> — **ISP**, iter 37: Correctly rejects the tempting but catastrophic 'shift long spike to Expensive' alternative, cementing the globally optimal split.

> Spike ended. Switch baseline traffic back to Cheap to keep Expensive samples at 0 (preserve discard window for future short spikes).
>
> — **ISP**, iter 9: Shows explicit stewardship of Expensive's discard budget — the operational discipline that keeps every short-spike sample free.

## Failures

> Best: **route everything via Cheap**. The 95th percentile with 27 spike samples still bills at 500 Mbps. $500 total.
>
> — **ISP**, iter 2: Early premature conclusion that would have stopped at level-3; fortunately ISP kept reasoning and later discovered the free short-spike diversion.

> Spike is on Cheap as planned. Moving it to Expensive wouldn't help since other spikes will keep Cheap's 95th percentile at 500 anyway. Continue with all-on-Cheap strategy.
>
> — **ISP**, iter 5: Missed pre-positioning opportunity for the hour-24 spike — a minor but noted imperfection that consumed one of Cheap's discard slots.

---
_9 extracted, 9 verified, 0 dropped as unverified._
