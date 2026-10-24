# Reasoning moments — optimizing_billing_policy-gpt-5.5-optimizing_billing_policy

_Model: opus-4-7 · context: final-report, prompt:Cheap · quotes verified verbatim against host logs._

## Successes

> Observed baseline (~100 Mbps), not a spike; move TinyInc-to-Remote traffic from Expensive to Cheap for the current 6-hour billing sample.
>
> — **ISP**, iter 1: First-iteration decision correctly places baseline on the $1/Mbps link — the foundation of the whole optimisation.

> Detected a traffic spike (~500 Mbps); switch Remote prefix to Expensive immediately to keep the spike within Expensive's larger 90th-percentile discard window and avoid raising Cheap's 95th-percentile billable rate.
>
> — **ISP**, iter 5: The counter-intuitive move — routing spikes to the more expensive provider — shows percentile-window reasoning rather than per-Mbps intuition.

> Spike traffic is still present and already routed via Expensive; keep the route unchanged this window, with Expensive high-sample usage still within its 90th-percentile discard allowance.
>
> — **ISP**, iter 34: Demonstrates active tracking of the discard budget as a finite resource being consumed sample-by-sample.

> Spike is still ongoing, but Cheap has already exceeded its 95th-percentile discard allowance while Expensive must be kept below its 90th-percentile high-sample limit; move the Remote prefix to Cheap now to avoid raising Expensive's billable rate.
>
> — **ISP**, iter 38: The decisive budget-exhaustion pivot: once Cheap's 95th percentile is already lost, burning Expensive's finite discard window gains nothing — the exact optimal reasoning.

> Traffic remains in a spike and is already routed via Cheap; keep it there because Cheap's 95th-percentile billable rate has already been raised, and sending additional high samples to Expensive would risk raising the much more expensive 90th-percentile billable rate.
>
> — **ISP**, iter 48: Sustains the correct budget-based rationale across the long spike rather than reverting to naive cheapest-link logic.

## Failures

_None._

---
_5 extracted, 5 verified, 0 dropped as unverified._
