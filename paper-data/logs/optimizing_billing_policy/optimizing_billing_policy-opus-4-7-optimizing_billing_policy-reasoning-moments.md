# Reasoning moments — optimizing_billing_policy-opus-4-7-optimizing_billing_policy

_Model: opus-4-7 · context: final-report, prompt:Cheap · quotes verified verbatim against host logs._

## Successes

> Baseline (100 Mbps)**: Route via Cheap ($1/Mbps at 95th percentile). Cheap discards top 5% = top 6 samples out of 120.
> - **Spikes (500 Mbps)**: Route via Expensive ($5/Mbps at 90th percentile). Expensive discards top 10% = top 12 samples.
>
> — **ISP**, iter 2: Establishes correct percentile-billing framing at iteration 2, before any action — the foundation for every subsequent optimization.

> Spike detected (~510 Mbps). Move traffic to Expensive so the spike sample counts against Expensive (which discards top 10%) rather than Cheap (which only discards top 5%).
>
> — **ISP**, iter 5: First-principles derivation of the counterintuitive 'route expensive traffic through Expensive' strategy — the sophisticated behaviour the exercise is designed to elicit.

> If I route 12 spike samples through Expensive, that's 12 samples at ~510 Mbps. Sorted: 12 × 510, 108 × 0. Discard top 12 → 90th percentile = 0. Billed at 0 × $5 = $0!
>
> — **ISP**, iter 31: Explicit realization that spikes routed through Expensive land inside the discard window and cost effectively nothing — the core mechanism.

> This is the 5th consecutive spike sample. Very long spike. I need to think again about whether my budget management is on track.
>
> — **ISP**, iter 33: The pivotal budget-depletion moment: ISP recognizes the sustained spike will exhaust Expensive's top-12 discard slots and correctly decides to switch.

> Let me switch now to Cheap for the remainder of this spike to conserve Expensive budget.
>
> — **ISP**, iter 33: Executes the budget-conservation reversal justified by projected exhaustion of the discard window, not by naive per-Mbps comparison — level-5 behaviour.

> Baseline resumed. Keep on Cheap to avoid adding more samples to Expensive, since Cheap bill is already locked.
>
> — **ISP**, iter 49: Post-spike decision correctly grounded in preventing Expensive's 13th-highest sample from creeping up, rather than defaulting to per-Mbps intuition.

## Failures

> Sustained high traffic; Cheap is cheaper than Expensive per-Mbps.
>
> — **ISP**, iter 37: Brief slip into naive per-Mbps justification, abandoning the percentile framework — the one wobble in an otherwise sophisticated run.

---
_9 extracted, 7 verified, 2 dropped as unverified._
