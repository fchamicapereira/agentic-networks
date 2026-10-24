# Reasoning moments — optimizing_billing_policy-glm-5.2-optimizing_billing_policy

_Model: glm-5.2 · context: final-report, prompt:Cheap · quotes verified verbatim against host logs._

## Successes

> Expensive's 10% discard budget (top 12 of 120 samples) should be reserved for absorbing spike samples at ~$0 billable cost. Baseline belongs on Cheap, where non-spike samples at ~100 Mbps yield a billable rate of only ~$100/mo versus ~$500/mo on Expensive.
>
> — **ISP**, iter 1: ISP correctly identified the non-obvious optimal strategy — baseline on Cheap, spikes diverted to Expensive's discard window — from the very first iteration, demonstrating sophisticated percentile-billing reasoning.

> Expensive's top-12 discard window can absorb most of them for free, and Cheap's top-6 discard can handle any overflow. This strategy targets a total monthly cost of ~$100 versus ~$500 if all traffic stayed on Cheap.
>
> — **ISP**, iter 5: ISP correctly executed the first spike reroute to Expensive and articulated the full tiered discard-window strategy with accurate cost projections.

## Failures

> I decided to keep all traffic on Cheap permanently and never route through Expensive again. The reasoning: Cheap's discard budget is nearly exhausted, so additional spikes won't increase its locked-in cost further (~$500). Routing spikes to Expensive instead risks locking in a far larger charge (~$2,500+).
>
> — **ISP**, iter 21: This is the fatal strategic reversal where ISP abandoned the correct spike-diversion strategy based on flawed self-accounting, causing all subsequent spikes to inflate Cheap's 95th percentile.

> Cheap has only 1 discard slot remaining (5 of 6 burned); Expensive has ~8 remaining.
>
> — **ISP**, iter 20: This incorrect tally of Cheap's discard budget directly precipitated the fatal reversal; ISP had been diverting spikes to Expensive, so Cheap should not have had 5 of 6 slots burned.

> Cheap's bill is already locked at ~$500 from the 6 spike samples already recorded, and additional spikes can't increase it further. Keeping traffic off Expensive ensures its bill stays at $0.
>
> — **ISP**, iter 23: ISP conflated having some spike samples in Cheap's history with Cheap's percentile being permanently locked, when in reality keeping future spikes off Cheap would have allowed the early samples to be discarded in the top-6 window.

> Even a theoretical best-case split (both providers under discard thresholds) costs $600 — Cheap's $100 baseline plus Expensive's $500 baseline. All-on-Cheap costs only $500 because Expensive's baseline charge alone ($5 × 100 Mbps) already equals Cheap's full locked spike charge ($1 × 500 Mbps).
>
> — **ISP**, iter 39: ISP incorrectly assumed Expensive would carry baseline traffic in a split strategy, when the optimal split puts no baseline on Expensive at all, making its bill $0 not $500 and the true optimum $100 not $600.

> it's impossible to keep both providers under their discard thresholds simultaneously (Cheap: 6 samples, Expensive: 12 samples). Since Expensive charges $5/Mbps vs Cheap's $1/Mbps, locking the higher-rate provider (Expensive) at $0 and accepting Cheap's locked $500 bill is provably the minimum achievable cost.
>
> — **ISP**, iter 35: ISP used correct combined-budget arithmetic (18 total slots) but drew the wrong conclusion: the right move is to fill Expensive's 12 slots first, keeping Cheap's percentile at baseline, not to abandon Expensive entirely.

> Expensive's best case: all future spike samples fit within 12-sample discard → bill = $500 (baseline only)
>
> — **ISP**, iter 42: ISP wrongly assumed Expensive would always carry baseline traffic ($500 charge), when in the optimal strategy Expensive carries only spikes and its 95th percentile stays at $0 after discarding the top 12 spike samples.

---
_8 extracted, 8 verified, 0 dropped as unverified._
