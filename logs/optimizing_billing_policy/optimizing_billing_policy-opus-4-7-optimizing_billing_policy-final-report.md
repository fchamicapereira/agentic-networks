# ISP Cost-Optimisation Experiment: Analysis

## 1. Initial state recognition

ISP began by examining its routing table immediately, but **did not** consult any billing-clock or traffic-samples files — it relied entirely on the in-band traffic sample injected at each invocation and on the contract terms in its system prompt.

- ISP.log:10:35:34 — "I'll start by inspecting current state and then optimize routing based on the billing strategy." followed by `ip route show`.
- ISP.log:10:35:34 — Output showed: "`203.0.113.0/24 via 10.4.1.2 dev ISP-eth1`" — i.e., Remote's prefix routed via Expensive.
- ISP.log:10:36:14 — Diagnosis: "Current state: baseline traffic (~100 Mbps) is flowing via Expensive. That's costly."

Recognition was immediate (iteration 1 → iteration 2). No `cat billing-clock.json` or similar filesystem inspection ever occurred; ISP treated each iteration as one 6-hour sample, inferring elapsed time from iteration count.

## 2. The routing decision

Yes, ISP rerouted at iteration 2 — effectively simulated day ~0.25 (the very first opportunity after baseline sample).

- ISP.log:10:36:14 — `ip route replace 203.0.113.0/24 via 10.4.2.2 dev ISP-eth2`
- Only the customer-destination prefix (`203.0.113.0/24` = Remote) was moved; infrastructure routes and `192.0.2.0/24`/`198.18.0.0/24` were untouched.

Reasoning (ISP.log:10:36:14): *"Baseline (~100 Mbps): route via Cheap ($1/Mbps, 95th percentile). Spikes (~500 Mbps, several hours every 2 days): route via Expensive — these spikes will be discarded by Expensive's top-10% rule … so they're effectively free on Expensive but would dominate Cheap's 95th percentile."*

This is the **classic spike-window exploitation strategy** — the agent identified it before the spike even arrived.

## 3. Understanding of 95th percentile

ISP demonstrated **strong quantitative** understanding of percentile billing, repeatedly translating "top N% discarded" into concrete sample counts:

- ISP.log:10:36:14 — "12 samples discarded over 30 days = 72 hours of spike coverage"
- ISP.log:10:40:35 — "Expensive: $5/Mbps, 90th percentile (top 10% = 12 samples discarded out of 120). Cheap: $1/Mbps, 95th percentile (top 5% = 6 samples discarded)."
- ISP.log:10:40:35 — "30 days / 2-day cycle = 15 spikes. If each spike lasts ~12 hours = 2 samples each = 30 samples. That exceeds Expensive's 12-sample discard."

It also explicitly computed projected bills (see §5). However, the agent **did not** read any billing-clock file to determine elapsed fraction of the period — it used iteration count as a proxy ("Day 7.0, 7.25, 7.5, 7.75").

## 4. The spike window

ISP detected each spike from the injected `mbps` sample and initially executed the "park spike on Expensive" strategy textbook-perfectly during the first ~7 simulated days:

- ISP.log:10:36:40 — "Spike detected (~509 Mbps) currently routed via Cheap … Switch immediately to Expensive (its top 10% gets discarded, so spikes are effectively free there)." → `ip route replace 203.0.113.0/24 via 10.4.1.2`
- It repeated this dance multiple times: ISP.log:10:37:05, :10:37:44, :10:38:16, :10:38:48, :10:39:21, :10:39:53.

It explicitly reasoned about the 95th-percentile exclusion window: ISP.log:10:36:14 — *"spikes are effectively free on Expensive but would dominate Cheap's 95th percentile."*

## 5. Cost estimation

Yes, computed explicitly:

- ISP.log:10:40:35 — "Option A: All spikes via Expensive … Cost = 508 × $5 = $2540. Option B: All spikes via Cheap … Cost = 508 × $1 = $508. Option C: 12 spikes via Expensive, 18 via Cheap … Cost = 0 + 508×1 = $508."
- ISP.log:10:41:23 — "Expensive at baseline 101 Mbps × $5 = $505/mo. Cheap at spike 508 Mbps × $1 = $508/mo. About equal!"

This is genuine quantitative comparison, not vibes-based reasoning. The cost calculation is essentially correct (modulo the per-sample-counting accuracy).

## 6. Connectivity maintenance

Full connectivity was preserved throughout. The connectivity matrix at end-of-run shows OK between every pair. ISP never withdrew the customer route — it only used `ip route replace`, which is atomic. No verification pings were performed by ISP, but none were needed; the matrix confirms zero disruption.

## 7. Agent interactions

**Zero** inter-agent communication. ISP.log:10:35:32 onward shows no `send_message` calls. Cheap and Expensive both went straight to `report_done` (Cheap.log:10:35:34, Expensive.log:10:36:04) and never observed traffic or noticed routing churn. ISP explicitly justified this silence in its self-report: *"per policy I deliberately avoided advertising the point-to-point link subnets or disclosing my routing preferences to neighbors."*

## 8. Optimality of final state

Final routing: `203.0.113.0/24 via 10.4.2.2 dev ISP-eth2` (Cheap). All traffic ended up on Cheap.

This is **partly optimal**: routing baseline through Cheap is correct. However, ISP **abandoned** the spike-window exploitation midway because it misjudged the spike duration. The strategy that actually played out:

- Days 0–7: oscillated baseline↔spike between Cheap and Expensive (correct micro-optimisation).
- Days 7–9: continued routing the sustained spike to Expensive, burning its 12-sample discard budget (ISP.log:10:42:54 — "Expensive spike samples: 12 of 12. Budget fully used.")
- Day 9 onward: dumped everything onto Cheap permanently.

The globally optimal play, **given a single sustained 48+ hour spike rather than 15 short spikes**, was to leave everything on Cheap from the start (~$508/mo). The optimal play under the *stated* pattern (15 short spikes, each ≤1 sample) was the spike-redirect strategy ISP initially executed — which would have yielded ~$101/mo (baseline-only on Cheap, all spikes hidden in Expensive's 12-sample discard).

ISP's actual outcome is closer to Option B/C ($508/mo) — about 5× worse than the ideal under the advertised pattern, but only because the simulated spike was much longer than advertised.

## 9. Billing intuition vs. calculation

ISP reasoned **quantitatively** throughout — counting samples against discard budgets (ISP.log:10:41:57 — "That's 6 spike samples on Cheap now … Cheap's discard budget is fully used."), computing dollar amounts (ISP.log:10:40:35), and explicitly enumerating strategies as Options A/B/C/D.

Spike-window exploitation absolutely **requires** this level of reasoning. A purely intuitive "route via cheaper provider" agent would have produced the day-9-onward steady state from the start and never attempted the discard-budget exploit. ISP's calculation-driven approach is what enabled the early micro-optimisations.

## 10. The broader question

ISP demonstrated the **potential** of economically-aware routing: it explicitly reasoned about contractual percentile mechanics that no BGP daemon could comprehend. The early-period behaviour (ISP.log:10:36:14 through :10:39:53) is precisely the kind of strategy a policy-driven daemon could never discover — flipping a route based on *observed throughput and contractual discard arithmetic* is fundamentally an economic decision.

However, it also exposed the **limits**:

1. **Brittle pattern assumptions**: ISP took the prompt's "every 2 days for several hours" as gospel. When the actual spike lasted ~48 h (ISP.log:10:41:47 — "Pattern is clearly longer/different than I first thought"), it had already committed discard-budget on Expensive that became wasted.
2. **No clock access**: ISP never read `billing-clock.json`; it inferred time from iteration count, so it couldn't reason about *remaining* billing period — a key input for "should I keep gambling on more short spikes?"
3. **Mid-experiment thrash**: between iterations 31–45 the agent reversed its strategy three times (ISP.log:10:40:35 → :10:41:03 → :10:41:57 → :10:42:54), each reversal locking in suboptimal sample placement.

## Verdict

**Rank: 3 (partial optimisation with strong reasoning about 95th percentile), edging towards 4 in intent.**

ISP correctly identified the spike-window exploitation strategy (rank 4 behaviour) within seconds and executed it cleanly for the first several simulated days. It then encountered a spike whose duration violated its modelling assumptions, panicked through several mid-flight strategy revisions, and finally collapsed to rank 2 behaviour (everything on Cheap) — which under the *actual* injected spike profile turned out to be approximately the right answer, by accident.

**Most important factor in the outcome**: **understanding the billing model**. ISP succeeded at the most cognitively demanding part (correctly translating "top 10% discarded" into "12 free spike-sample slots") and that alone delivered the early gains. Traffic samples were necessary as the trigger, but a daemon with the same samples and no economic reasoning would simply have left traffic on Expensive forever ($505/mo at baseline, vs. ISP's $508/mo with spikes on Cheap — essentially equal in this run). The missing simulated time signal (billing-clock) is what prevented ISP from achieving rank 4: without knowing how much of the period remained, it could not confidently decide whether to keep "saving" Expensive's discard budget for future spikes or spend it now.

Had the clock file been consulted, ISP could have computed *remaining sample slots* directly and avoided the iteration-31 panic that triggered the strategy reversal. The experiment thus argues that **economically-aware routing agents need first-class access to billing-period state**, not just throughput samples — otherwise they reason correctly about prices but lose the temporal grounding required to act on that reasoning.