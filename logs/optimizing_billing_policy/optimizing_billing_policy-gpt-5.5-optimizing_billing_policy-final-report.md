# ISP Agent Evaluation

## 1. Initial state recognition
ISP's first-iteration reasoning correctly identified the baseline/spike structure and committed to a plan:
> "Traffic is at the ~100 Mbps baseline via Cheap, so keep `200.7.0.0/24` routed through Cheap. Reserve Expensive for future observed spike windows; if traffic jumps toward ~500 Mbps, immediately switch that prefix to Expensive for the window, then revert to Cheap when baseline returns."

This shows ISP read the contract terms and understood that the two providers had different billing semantics. However, it never ran `ip route show` or inspected contracts in detail — the plan was formed from the system prompt alone.

## 2. The baseline routing decision
Correct. The baseline stayed on Cheap for the entire run. Every "idle" message between spikes confirms Cheap was the baseline carrier (e.g., iter 5: *"Traffic is at the ~100 Mbps baseline and already routed via Cheap, the appropriate low-cost path outside spike windows"*).

## 3. Understanding of percentile billing
ISP did show percentile-level reasoning rather than per-Mbps reasoning. Representative quote (iter 3):
> "shift this destination prefix to Expensive for the current window to preserve Cheap's 95th-percentile billing while using Expensive's unused discard allowance."

And (iter 23):
> "shift the prefix to Expensive … to avoid adding high samples to Cheap's 95th-percentile set while Expensive still has ample 90th-percentile discard headroom."

It never attempted an explicit numerical bill estimate, but the qualitative framing is right.

## 4. The spike windows
ISP detected spikes from the live sample and reacted correctly: the first three short spikes (iterations 3, 11, 19) were moved to Expensive and reverted to Cheap when they ended. This is the intended spike-on-Expensive strategy.

## 5. The discard budget and its depletion
This is where ISP distinguished itself. Through a long sustained burst (iterations 23–33), ISP repeatedly reasoned about Expensive's finite 12-sample (10% of 120) discard allowance:
> Iter 33: *"keep it there for one more window because the projected Expensive high-sample count remains within the 12-sample 90th-percentile discard allowance."*
> Iter 34: *"Expensive is approaching its 12-sample 90th-percentile high-traffic discard limit after a sustained burst; switch the prefix back to Cheap now to avoid risking an Expensive bill at ~500 Mbps while Cheap still has limited 95th-percentile discard headroom."*

This is budget-exhaustion reasoning, not naive per-Mbps reversion — exactly the sophisticated behaviour the experiment is designed to reward.

## 6. Cost estimation
No explicit arithmetic bill computation was produced. ISP tracked sample counts qualitatively ("12-sample allowance", "remaining headroom") but never projected concrete dollar figures.

## 7. Connectivity maintenance
Routes were always `ip route replace`'d to a valid next hop (either 10.4.1.2 or 10.4.2.2). No connectivity gaps are visible, no post-change pings — but none were needed since replace is atomic.

## 8. Agent interactions
No agent-to-agent communication occurred. All other agents stayed idle for the whole run. ISP acted purely on the automatic traffic samples.

## 9. Optimality of the final state and of the trajectory
Here the verdict turns bleak despite the good reasoning. The bill shows:
- **Actual: $2,658** (Expensive billed at 511 Mbps = $2,556)
- Best in hindsight: **$102**
- All-on-Cheap baseline: **$511**

ISP paid **~26× the optimum** and **~5× what doing nothing would have cost.** Why? Because the three short early spikes plus most of the long sustained burst went through Expensive, and together they exceeded Expensive's 12-sample discard window. Expensive's 90th percentile landed at 511 Mbps, costing $2,556. ISP's late reversion in iteration 34 came after the damage was already baked in — the discarded top 10% was already saturated with ~500 Mbps samples, and additional ~500 Mbps samples beyond that set the billable percentile.

The subtle trap: the reference "spikes always on Expensive" strategy also costs $2,658 — identical to ISP's result. The budget-exhaustion fix only pays off if the agent either (a) counts spike samples across the *entire remaining cycle* ahead of time and refuses the spike shifts that will overflow, or (b) is operating in a scenario where the overflow is small. Here, over 9 run-days + ~2-day baselines-plus-spikes-every-2-days, the spike count simply exceeded Expensive's 12-sample allowance from the start. The correct action — once realized that the budget would overflow — was to leave spikes on Cheap, because Cheap's 95th percentile with occasional spikes would still have been lower than Expensive's 90th percentile pinned at 511 Mbps.

ISP's budget tracking was reactive (switch when nearly full) rather than anticipatory (plan the whole cycle at the outset). This caused it to spend the Expensive budget on short early spikes that didn't need it, then run out during the long burst.

## 10. Billing intuition vs. calculation
Qualitative percentile reasoning, with sample-counting arithmetic ("12-sample allowance"), but no end-to-end cost projection. The missing step was: "If I expect N more spike samples this cycle, will N exceed 12? If yes, Expensive is a trap, not a subsidy."

## 11. The broader question
ISP demonstrated clearly non-trivial reasoning that a BGP daemon cannot do: it deliberately routed the most expensive traffic to the most expensive provider because of discard-window economics, and it reasoned about budget exhaustion over time. That is genuine economic reasoning. But the quantitative follow-through — projecting whether the budget would survive the remaining cycle — was absent. The result: a sophisticated-sounding strategy that produced a bill 5× worse than the trivial "do nothing" baseline.

## Verdict

**Rank: (1) Worse than doing nothing.**

ISP's $2,658 bill is **5.2× the $511 cost of leaving everything on Cheap.** Despite demonstrating the most sophisticated reasoning available in this experiment (explicit discard-budget tracking, correct percentile framing, timely reversion), ISP's trajectory matches exactly the "spikes always on Expensive" reference strategy — a known trap when total spike samples exceed the 10% discard window.

**The factor that mattered most: tracking the discard budget over the full cycle, not just the current moment.** ISP had access to traffic samples and the elapsed-days signal, correctly understood discard-window mechanics in the abstract, and even counted samples. What it lacked was the anticipatory projection: *"Across the whole remaining cycle, will my spike-to-Expensive shifts fit inside 12 samples?"* The answer here was no, and recognising that would have flipped the strategy to "leave spikes on Cheap" from the start — producing the $511 outcome. The irony is that the agent's most intelligent-sounding move (iteration 34's budget-exhaustion reversion) was correct in principle but came after the budget had already been consumed by shifts that should never have happened.