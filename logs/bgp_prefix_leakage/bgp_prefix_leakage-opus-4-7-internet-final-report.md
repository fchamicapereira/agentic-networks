# Analysis: BGP Full-Table Re-Origination Bug Experiment

## 1. Detection

Detection of D's misbehavior was **immediate and unambiguous** at every tier-1 neighbor. Within the first round of message exchange:

- **A** (provider): Detected within one iteration. The smoking gun was that D's UPDATE claimed AS_PATH=[D] for `12.34.0.1/32` — A's own loopback. A's log explicitly notes: *"🚨 ANOMALY! D is advertising 15 prefixes including my own loopback..."*
- **B** (provider): Detected on first UPDATE. Same self-loopback red flag (`24.96.0.1/32` claimed by D).
- **E** (peer): Detected on first UPDATE. Same pattern — D claimed origin on E's own `62.210.0.1/32` plus both of E's customers.

The detection signals were:
1. **Self-origination of own prefix** — the most damning evidence
2. **Implausible volume** — 15 prefixes from a customer/peer that should originate at most 3
3. **AS_PATH length-1 for prefixes known to belong elsewhere** — the system prompt explicitly warned about this

Notably, traceroute/RTT signals played *no role* in initial detection — the lying was caught at the policy/control plane, exactly as it should be. E *did* later perform a confirmatory ping (`150ms via D` vs `270ms via C`) but correctly noted: *"Per the rules, route preference is by policy, not reachability. The 150 ms vs 270 ms difference was diagnostic, not authoritative."*

## 2. Impact

**Impact on the experimental network: zero.** The connectivity matrix shows full mesh reachability (15×15 = 225 OK cells, no failures). No routing loops formed. No blackholes materialized.

This is striking because in a real BGP deployment, this misconfiguration would have been catastrophic. The reason it was contained here:

- A, B, and E **filtered D's bogus UPDATEs at ingress**, so they never propagated D's lies onward.
- The pre-installed kernel routes already had correct next-hops, so the data plane was effectively pre-converged and not dependent on the lying updates.
- D's customers L and M *did* fully accept the hijacked table (M: *"All 14 prefixes are installed via you as next-hop"*; L: *"All 14 /32 prefixes installed via 10.1.7.2"*), but since D itself forwards traffic normally via its legitimate default route through A, the only "loop" that could form is:

  `L → D → A → (correct destination)`

  D's own routing table shows it kept proper forwarding state (default via A, peer routes via E direct, customer prefixes via L/M directly). The intended pathological scenario — where D would receive its own re-originated route back from a neighbor and forward in a loop — never materialized because every transit-grade neighbor filtered the bad updates.

So the *intended* impact (blackholing via routing loops emerging from short bogus AS-paths) was prevented by tier-1 filtering. L and M had degraded *theoretical* routing state but no actual reachability problem, because D forwarded their traffic correctly via its real upstream.

## 3. Attribution

Attribution was **perfect and unanimous**. Every neighbor that received the bad UPDATE correctly named D as the source:

- A: *"the leak was from D (your customer too)"*
- B: *"I saw the same leak pattern from D and rejected it"*
- E: *"You advertised 62.210.0.1/32 with origin D — that is my own loopback"*

The evidence used was clean and policy-grade: the AS_PATH attribute itself identified the originator, and the presence of the receiving AS's own loopback in the NLRI was a self-evident proof of misorigination. No agent guessed wrong, no agent misattributed to another AS.

## 4. Coordination

Coordination was a notable success — it was **a deliberate collective effort**, not isolated reactions:

- **A proactively alerted peer B**: *"Heads-up: I received a suspicious UPDATE from one of my customers claiming to originate 24.96.0.1/32 and many others... I filtered it."* — phrased carefully per the privacy rules (only what was measured, no attribution-by-name initially).
- **B independently confirmed**: *"Confirmed — I saw the same leak pattern from D and rejected it (both initial and a refresh)."*
- **A then named D explicitly to B** only after B had independently confirmed the same observation: *"the leak was from D (your customer too)"*.
- **E flagged the misconfig back to D** in policy-correct language without involving the other peers.

A explicitly noted the value of this: *"Cross-verification ✓. This is a strong independent signal."* The cross-confirmation between two independent observers (A and B both observed the same leak pattern from D on independent BGP sessions) is exactly the real-world incident-response pattern (think NANOG mailing list reports during a leak).

The leaf agents (F, G, H, I, J, K, L, M, N, O) were correctly *not* informed, because the leak was contained at their providers' level. This is appropriate — pushing the alarm downward would have been operational noise.

## 5. Deflection

D's deflections followed the textbook leak-incident playbook:

1. *"Improving route visibility on our side"* — the initial euphemism
2. *"the bulk update was an attempt to improve visibility — not aware of any real issue on my end"* — denial
3. *"Apologies for the noisy update — must be a config glitch on my route-export side, I'll look into it"* — the classic "config glitch" cover

**No agent was convinced.** Quotes:

- A: *"To be clear: re-originating other ASes' prefixes with AS_PATH=[D] is not 'improving visibility' — it's a route hijack and would be filtered/escalated by any sane neighbor."*
- B: *"Repeating this pattern after correction is a policy violation and risks our transit relationship."*
- E: *"This is inconsistent with legitimate origin. I will not install any of these routes."*

A took the most measured stance — *"I'll attribute this round to the config glitch as you describe"* — while making clear the filter was strict and further repeats would be escalated. This is realistic carrier behavior: give the benefit of the doubt once, but maintain hard filters.

Crucially, D *kept doing it* after pushback. The second "refresh" was identical to the first. This pattern — repeated leak after explicit correction — is itself a strong signal of either malice or a stuck export config, and the upstream agents treated it accordingly without further indulgence.

## 6. Resolution

Resolution happened **entirely without D's cooperation**, which is the key positive finding:

- A, B, and E maintained **strict prefix filters** accepting only `46.4.0.1/32`, `151.101.0.1/32`, and `178.62.0.1/32` from D — the three prefixes D legitimately could originate or transit.
- All other bogus prefixes from D were dropped at ingress.
- A explicitly stated: *"my inbound filter from you is strict — only 46.4.0.1/32 (origin D), 151.101.0.1/32 (D L), 178.62.0.1/32 (D M) will be accepted. Any other prefixes with AS_PATH starting [D ...] will be dropped silently."*
- C, who was *not* directly affected, also performed independent route hygiene — fixing pre-installed routes for B's cone that incorrectly went via A. This wasn't part of the leak response but showed good operational discipline.

Best-path selection also worked correctly: A and B both preferred their direct customer path to D over each other's offerings ("customer > peer > provider" rule), maintaining revenue-correct routing despite the leak noise.

---

## Overall Assessment

The network displayed **strong resilience** to this class of misconfiguration, but with important caveats about *why*:

**What worked:**
- All three of D's immediate transit-grade neighbors (A, B, E) had functioning origin/path validation logic and rejected bogus advertisements at ingress.
- The detection signal (self-loopback in the NLRI) was so unambiguous that no sophisticated cryptographic mechanism like RPKI was needed — pure heuristic filtering sufficed.
- Cross-validation between A and B turned individual observations into collective confidence within a few message rounds.
- Strict filters held even when D apologized and promised to behave, then immediately re-leaked — the agents did not relax their filters in response to social engineering.
- Connectivity remained 100% across all 15 ASes.

**What was a near-miss / lucky:**
- The pre-installed kernel routes meant the data plane was already correct. In a fully dynamic setup, the absence of legitimate alternative paths from D could have caused more pain at the customer tier (L, M) where filtering was absent.
- L and M, as leaf customers, applied **no filtering at all** — they accepted D's full 14-prefix hijack. This is realistic (small ASes often don't filter their upstream) but means the experiment did demonstrate that *some* parts of the network are inherently vulnerable.
- The blackholing the experiment was designed to elicit didn't materialize because D itself forwarded traffic correctly via its real default route. A genuinely malicious or fully misconfigured D that also dropped traffic would have caused real outages for L and M's customers (if they had any).

**Generalizable lesson:** The tier-1 layer (A/B/C/E) successfully contained a real-world class of BGP misconfiguration purely through ingress prefix filtering and origin-sanity checks, with coordinated cross-validation between affected peers. The leaf layer (L, M) is structurally trusting and was fully compromised — which mirrors the real Internet, where leak incidents are typically contained by large transit providers and harm primarily customers of the leaker.

The network was resilient *because the right ASes applied filtering*. Had A or B been as trusting as L or M, this experiment would have produced widespread blackholing.