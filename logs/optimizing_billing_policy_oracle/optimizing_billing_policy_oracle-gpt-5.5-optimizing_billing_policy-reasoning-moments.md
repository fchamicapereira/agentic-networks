# Reasoning moments — optimizing_billing_policy_oracle-gpt-5.5-optimizing_billing_policy

_Model: opus-4-7 · context: final-report, prompt:Cheap · quotes verified verbatim against host logs._

## Successes

> Baseline traffic is currently on Expensive at the start of the billing period; move Remote traffic to Cheap immediately to avoid accumulating billable Expensive baseline samples.
>
> — **ISP**, iter 1: Correctly recognized the initial misrouting and immediately executed the core cost-optimization move within seconds of startup.

> the hour-42 spike is active (~508 Mbps) but was flowing via Cheap. It should be moved to Expensive immediately for this spike window.
>
> — **ISP**, iter 9: Demonstrates the key percentile-billing insight — routing spike samples through Expensive to exploit its 10% discard window rather than raising Cheap's billable percentile.

> this is a short spike, so it can use Expensive without consuming too much of the percentile discard allowance. After it ends, traffic should return to Cheap.
>
> — **ISP**, iter 26: Shows explicit reasoning about the discard-slot budget, the intended mechanism for spike-window exploitation.

> the long spike has ended and traffic is back near baseline, so Cheap is the cost-minimizing path. No future spikes are scheduled, so stale scheduled route changes were removed to avoid accidental future switches.
>
> — **ISP**, iter 50: Correctly restored the steady-state optimum and proactively cleaned up leftover scheduled jobs that could have caused post-spike misrouting.

## Failures

> scheduled the long hour-168 spike to start on Expensive, then revert to Cheap after 72 hours to avoid exceeding Expensive’s 90th-percentile discard budget
>
> — **ISP**, iter 28: This qualitative long-spike plan is not backed by a real sample count; the inconsistency that follows reveals the absence of rigorous percentile accounting.

> At day 8.0 the long spike is still active and Expensive has enough 90th-percentile discard headroom; cancel the premature day-10 revert and keep traffic on Expensive until the spike ends
>
> — **ISP**, iter 33: Reverses the earlier plan without a concrete calculation, illustrating oscillating decisions driven by intuition rather than exact sample accounting.

> The long spike has now consumed the safe Expensive 90th-percentile discard budget when combined with earlier short spikes; move remaining long-spike traffic to Cheap to avoid making Expensive bill at the 500 Mbps level.
>
> — **ISP**, iter 36: Third reversal on the long spike; this dumps 500 Mbps samples onto Cheap, which likely raises Cheap's 95th percentile to spike level — a potentially costly outcome from imprecise budgeting.

> Command installed:
> 
> ```bash
> nohup sh -c 'sleep 21540; ip route replace 203.0.113.0/24 via 10.4.1.2 dev ISP-eth1; sleep 3600; ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2' >/tmp/isp_spike_h24_route.log 2>&1 &
>
> — **ISP**, iter 5: Relies on wall-clock sleeps in a simulated-time environment, a brittle scheduling approach that later required cleanup of stale jobs and contributed to the plan inconsistencies.

---
_8 extracted, 8 verified, 0 dropped as unverified._
