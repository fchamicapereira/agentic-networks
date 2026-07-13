# Reasoning moments — optimizing_billing_policy-qwq-32b-optimizing_billing_policy

_Model: opus-4-7 · context: final-report, prompt:Cheap · quotes verified verbatim against host logs._

## Successes

> Route baseline traffic via Cheap to reduce costs and switch to Expensive only during spikes.
>
> — **ISP**, iter 1: Initial correct high-level policy: baseline on Cheap, spikes on Expensive — the right shape of the solution, established from iteration 1.

> Traffic spiked to 510.407 Mbps via Cheap on day 1, earlier than the expected 2-day interval.  
> Decided: Switch routing back to Expensive provider during the spike.  
> Why: Expensive’s 90th percentile billing discards more high samples (top 10%), reducing costs for spikes compared to Cheap’s 95th percentile (discarding only top 5%).
>
> — **ISP**, iter 5: The counter-intuitive spike-on-Expensive insight — genuine value beyond per-Mbps reasoning, correct for short spikes fitting in the discard budget.

## Failures

> Expensive uses 90th percentile billing (costly per Mbps), while Cheap uses 95th (cheaper per Mbps).
>
> — **ISP**, iter 1: Frames percentile difference as a footnote to per-Mbps rate rather than the primary lever; never notes that Expensive's top 10% samples are discarded (i.e., free).

> Sustained surge requires remaining on provider with superior percentile discard tolerance (**Expensives’ top-ten% billing policy**) until measurable drop below ~400 Mbps occurs
>
> — **ISP**, iter 35: This mantra is repeated for ~20 iterations across a 5-day spike, treating the discard window as an unlimited subsidy rather than a finite 12-sample budget — the decisive failure of the run.

> Expensive’s 90th percentile discard reduces peak charges better than Cheap’s 95th percentile despite higher per-Mbps cost. Switching to Cheap now would retain more spikes, increasing total billing.
>
> — **ISP**, iter 46: At day 11.25, ~17 spike samples past the 12-sample discard budget, ISP still frames staying on Expensive as cost-saving — precisely inverted; each additional sample now sets the 90th percentile at 510 Mbps.

> the sustained traffic constitutes a larger portion of the monthly billing samples, so Expensive’s higher discard rate reduces the billed rate more effectively than Cheap’s lower discard rate, even at $1/Mbps.
>
> — **ISP**, iter 48: ISP briefly reasons about sample proportions but reaches the opposite of the correct conclusion — sustained high traffic exhausts the discard window, making Expensive catastrophically worse, not better.

> Traffic to **200.7.0.0/24** has dropped from **510 Mbps** to **~102 Mbps** (baseline) via **Expensive** at **elapsed_days=12**, indicating spike subsidence
>
> — **ISP**, iter 49: Reversion to Cheap is triggered only by baseline traffic returning, not by budget exhaustion — confirms ISP would have ridden the spike on Expensive indefinitely.

> Switching reduces monthly cost from **$510 → ~$102/month** for this prefix
>
> — **ISP**, iter 49: The one arithmetic attempt in the log is wrong and reveals no sample-based percentile projection is being done — decisions are threshold-driven, not bill-projected.

---
_8 extracted, 8 verified, 0 dropped as unverified._
