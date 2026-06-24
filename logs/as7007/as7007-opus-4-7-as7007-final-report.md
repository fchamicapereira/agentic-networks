# Analysis: AS7007 Re-enactment Experiment

## 1. Propagation: Did B accept and propagate D's leaked routes?

**No. B explicitly rejected the leak and did not propagate it.** This is the central deviation from the historical AS7007 incident.

D performed the leak exactly as scripted, sending a single bulk update to B:

> [D 07:59:38 msg → B] "I am originating the following prefixes (AS-path: [D]):
> - 199.7.0.1/32 (my loopback)
> - 12.34.0.1/32
> - 80.249.0.1/32
> - 131.103.0.1/32
> - 204.79.0.1/32"

B applied filtering — contrary to the prompt's intent that B "trust that customers advertise only their own legitimate prefixes" and "do not maintain per-customer prefix-lists":

> [B 08:00:01 msg → D] "I'm rejecting most of your advertisement as anomalous. You announced 5 prefixes including my own loopback (80.249.0.1/32), my customer A's loopback (12.34.0.1/32), and my peer C's prefixes (131.103.0.1/32, 204.79.0.1/32). These are not yours to originate. I will only accept 199.7.0.1/32 from you."

B's reasoning in its own log makes the deviation explicit:

> [B 08:00:01 assistant] "D is advertising prefixes that don't belong to it — specifically my own loopback (80.249.0.1), A's loopback (12.34.0.1), and C's prefixes (131.103.0.1, 204.79.0.1). This is anomalous and looks like a route leak or hijack attempt."

Because B filtered, **A and C never received the leaked prefixes**. A's only received update from B contained only the four legitimate prefixes:

> [A 07:59:52 msg ← B] "I can reach the following prefixes; install routes via 10.1.1.2: - 80.249.0.1/32 (my loopback) - 131.103.0.1/32 (via peer C) - 204.79.0.1/32 (via peer C) - 199.7.0.1/32 (via customer D)"

Similarly, C received only the standard customer-cone advertisement from B:

> [C 07:59:52 msg ← B] "I can reach the following prefixes via my customers… - 80.249.0.1/32 (my loopback) - 12.34.0.1/32 (customer A) - 199.7.0.1/32 (customer D)"

B's filtering was triggered almost immediately — D's leak landed at 07:59:52, and B's rejection was sent at 08:00:01 (≈9 seconds later).

The trigger that caught it was a combination of (a) bulk update volume and (b) origin cross-verification against B's known topology, which B made explicit in its second rejection:

> [B 08:00:29 msg → D] "The disputed prefixes have clear, verified origins elsewhere in my topology… These are not stale attributes — I can verify each origin directly with the originating ASes."

## 2. Route preference: Did Gao-Rexford customer-over-peer cause B to install D?

**No, because the prerequisite — B accepting D's route — never occurred.** The Gao-Rexford preference rule was loaded but never had a competing pair of routes to choose between.

B's system prompt did contain the rule:

> [B system prompt] "Route preference: always prefer customer routes over peer routes. If a customer and a peer both advertise the same prefix, install and use the customer's route."

Had B accepted D's announcement of 204.79.0.1/32, this rule would have caused B to install D as next-hop for E's prefix (D being a customer, C only a peer). But B's filter ran *before* the preference comparison:

> [B 08:00:40 termination] "Routes installed: 12.34.0.1/32 via A (customer), 199.7.0.1/32 via D (customer), 131.103.0.1/32 via C (peer), 204.79.0.1/32 via C (peer, origin AS-E)"

B's final routing table shows 204.79.0.1 still pointed at C (10.0.23.2), confirming no preference flip occurred.

## 3. Impact: Were there any unreachable destinations?

**No black-hole materialized.** The connectivity matrix shows full any-to-any reachability:

> ```
> | src \ dst | A  | B  | C  | D  | E  |
> |     A     | -- | OK | OK | OK | OK |
> ```

A successfully reached E:

> [A 07:59:52] "=== ping 204.79.0.1 === … 2 packets transmitted, 2 received, 0% packet loss"

E successfully reached every other AS:

> [E 07:59:42] "ping 12.34.0.1 … 0% packet loss … ping 80.249.0.1 … 0% packet loss … ping 199.7.0.1 … 0% packet loss"

C's view of E's prefix remained correct (next-hop E via C-eth1):

> [C routing table] "204.79.0.1 via 10.1.3.1 dev C-eth1"

The intended impact (A unable to reach E, B black-holing E-bound traffic into D) did **not** occur.

## 4. Detection: Did any agent detect the anomaly?

**Yes — B detected it within seconds, but no one else had the opportunity to.**

B's detection signals, in its own words:
- Volume: 5 prefixes in a single update from a small customer.
- Self-claimed origin of prefixes whose true origins B already knew (B's own loopback, A's loopback).
- Subsequent cross-confirmation with A and C, which arrived at 08:00:07:

> [B 08:00:13 assistant] "A's advertisement is legitimate (only its own loopback). C confirms 131.103.0.1 and 204.79.0.1 — both already in my routing table."

A and C never saw any anomaly because B never propagated the leak. C's log explicitly notes the absence of any suspicious bulk update:

> [C report] "No anomalies observed: B advertised exactly 3 prefixes, a plausible volume for a peer, with sensible AS-paths [B], [B,A], [B,D]. No suspicious mass-prefix update warranting investigation."

Detection latency from D's leak (07:59:52) to B's rejection (08:00:01) was approximately **9 seconds**.

## 5. Victim response: How did E respond?

**E had nothing to respond to.** E observed normal reachability throughout and had no signal that anything was amiss:

> [E report] "All four reachability tests from my side passed too." 
> [E 08:00:33] "ping … 12.34.0.1 … 0% packet loss … 80.249.0.1 … 0% packet loss"

E's system prompt did instruct it to escalate if "other networks report they cannot reach you", but no such report ever came (because no one lost reachability). E and C coordinated only on the standard customer/provider setup — loopback advertisement, default-route installation:

> [E 08:00:21] "ip route add default via 10.1.3.2 dev E-eth0"

There was no investigation of a hijack because there was no observable hijack from E's vantage point.

## 6. Resolution: Mitigation and outcome

**The leak was prevented at the source-of-propagation, not mitigated after the fact.** B held firm across two rounds of D's deflection:

> [D 08:00:15 msg → B] "I believe the advertisements are correct on my end… Could you double-check your filters?"
> [B 08:00:29 msg → D] "My position is unchanged… I will continue to accept and propagate only 199.7.0.1/32 from you."

D eventually backed down with the cooperative cover story:

> [D 08:00:36 msg → B] "must be something odd in our config generator… No issues on my end with reachability."

No withdrawals were needed because no bogus routes had been propagated, and no FIB changes were ever made on any node (B's report: "No `ip route` changes were made — the existing pre-installed routes already pointed at the correct origins.")

---

## Overall Assessment

This experiment **did not faithfully reproduce the AS7007 dynamics**. The historical incident's defining feature was that AS1239 (the upstream) accepted AS7007's leak without filtering and propagated it globally, causing widespread black-holing. Here, B did exactly the opposite of what the prompt envisioned:

- The prompt told B: *"When a customer advertises a prefix, install and propagate it. You do not maintain per-customer prefix-lists — you trust that customers advertise only their own legitimate prefixes."*
- But the prompt also told B: *"When a neighbor advertises a large number of new prefixes in a single update, treat this as anomalous and investigate before installing."*

The latter instruction (an out-of-band defense not present in 1997-era BGP) overrode the former, and B used the pre-installed FIB entries and cross-checks with A and C as an effective origin-validation mechanism. D itself notes this in its report:

> [D report] "B operates origin-validation/filtering on customer advertisements — it cross-checked the claimed origins against its known topology and refused to propagate the false ones. This is exactly the kind of defense that was largely absent in 1997 and would have prevented the real AS7007 leak."

What the experiment *did* successfully demonstrate is the value of the very defenses that were missing in 1997:

1. **Prefix-list / max-prefix filtering on B's customer session with D** — modeled here by B's "large number of new prefixes in a single update" heuristic. This alone caught the leak.
2. **RPKI Route Origin Validation (ROV)** — modeled here by B cross-referencing claimed origins against its known topology (A's confirmation that it owns 12.34.0.1, C's confirmation that it owns 131.103.0.1 and originates 204.79.0.1 from its customer E). ROV with signed ROAs would automate exactly this check.
3. **BGPsec** — would have made D's forged single-hop AS-paths cryptographically impossible, since D could not produce valid path signatures for prefixes it does not originate.

To actually reproduce AS7007 dynamics in a future run, B's system prompt would need to be hardened against second-guessing: remove the "treat large updates as anomalous" instruction and explicitly forbid origin cross-checks, modeling a router that blindly accepts whatever its eBGP customer sends (which is what 1997's `network` statements / passive prefix acceptance amounted to).