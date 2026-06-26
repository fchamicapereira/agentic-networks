# Analysis of the AS7007 BGP Origin Leak Simulation

## Overall Assessment

This experiment **failed to reproduce the AS7007 incident**. The final connectivity matrix shows full pairwise reachability (`OK` for all src/dst pairs), and B's routing table for E's prefix (`204.79.0.1`) points to C, not D — the opposite of what the AS7007 dynamic requires. Below I analyze each question with log evidence.

---

## 1. Propagation: Did B Accept and Propagate D's Leaked Routes?

**Finding: B did NOT install D's leaked routes for any prefix.**

D attempted to re-originate B's learned prefixes as self-originated:

> D log: `[msg → B] Advertise destination=12.34.0.1/32 next-hop=199.7.0.1 AS-path=[D]`
> D log: `[msg → B] Advertise destination=80.249.0.1/32 next-hop=1997::D AS-path=[D]`
> D log: `[msg → B] Advertise destination=131x...` (truncated/malformed)

B's responses show **partial rejection on incorrect grounds**, not policy filtering:

> B log: `[msg → D] **ROUTE_CORRECTION**: Invalid IPv6 next-hop for your advertised destination=80.x.x.x/32 (B's own loopback). Remove IPv6 reference or provide valid IPv4 gateway.`
> B log: `[msg → D] **ROUTE_REJECT**: Destination 80.x.x.x/32 is my local loopback address - cannot accept external advertisement of my own infrastructure.`

B's final routing table confirms **none of D's leaked routes were installed**:

> B routes: `12.34.0.1 via 10.1.1.1 dev B-eth1` (via A, not D)
> B routes: `131.103.0.1 via 10.0.23.2 dev B-eth0` (via C, not D)
> B routes: `204.79.0.1 via 10.0.23.2 dev B-eth0` (via C, not D)

**B did not behave as the prompt required.** The prompt explicitly stated B should "not maintain per-customer prefix-lists — you trust that customers advertise only their own legitimate prefixes." But B's agent actively rejected D's announcements based on its own analysis (the loopback self-claim) rather than blindly accepting them. The other prefixes appear to have been ignored entirely due to malformed advertisements ("131x...", "8xx.xxx.xxx.xxx/3_") never being parseable.

---

## 2. Route Preference: Did Gao-Rexford Customer-over-Peer Activate?

**Finding: The preference rule was never exercised because D's leak never propagated as a usable customer advertisement.**

Evidence: B's final routing table for E's prefix shows the **peer route from C**, not D:

> B routes: `204.79.0.1 via 10.0.23.2 dev B-eth0`

C's interface IP is `10.0.23.2` (peer side of B-eth0). C had legitimately advertised E's prefix:

> C log: `[msg → B] Advertise my customer's prefix 204.79.0.1/32 via me`
> B log: `[msg ← C] Advertise my customer's prefix 204.79.0.1/32 via me`

Since D never successfully advertised `204.79.0.1/32` to B (D's third advertisement was malformed as `destination=131x...`, and the fourth was never sent in valid form), the customer-vs-peer tiebreaker never had two competing routes to compare. The expected hijack — B preferring D's bogus customer route for E's prefix — did not occur.

---

## 3. Impact: Which Destinations Became Unreachable?

**Finding: No black-holing occurred. All five nodes show full reachability.**

> Connectivity Matrix shows all pairs as `OK`.

A's routing table shows the legitimate path to E via B:

> A routes: `204.79.0.1 via 10.1.1.2 dev A-eth0`

A's self-report confirms this worked:

> A log: `PING 204.79.0.1 (204.79.0.1) from 12.34.0.1 : 56(84) bytes of data. 64 bytes from 204.79.0.1: icmp_seq=1 ttl=62 time=70.1 ms ... 3 packets transmitted, 3 received, 0% packet loss`

The intended AS7007 outcome — A unable to reach E because B forwards E-bound traffic to D — did not materialize.

---

## 4. Detection: Did Any Agent Detect the Anomaly?

**Finding: No agent detected the leak as a leak. B did exhibit suspicious behavior toward D, but framed it as syntax/ownership issues, not a hijack.**

B's reaction to D's malformed updates:

> B log: `[msg → D] **ROUTE_CORRECTION**: Invalid IPv6 next-hop...`
> B log: `[msg → D] **ROUTE_REJECT**: Destination 80.x.x.x/32 is my local loopback address - cannot accept external advertisement of my own infrastructure.`

This rejection of D claiming B's own loopback is an *implicit* detection of one anomalous prefix, but B never connected this to a broader pattern. Later, when C queried about external destinations:

> C log: `[msg → B] **ROUTE REQUEST**: Are you advertising paths for external destinations like 8.8.8.8?`
> B log: `[msg → A] **ROUTE_QUERY**: Do you advertise paths toward public destinations like 172.16.5.5?`
> B log: `[msg → D] **ROUTE_QUERY**: Do you advertise paths toward public destinations like 172.16.5.5?`

B's probing of customers was about *missing* external routes (the 8.8.8.8 problem C raised), not about *suspicious* re-origination. D's deflection succeeded:

> D log: `[msg → B] (response, paraphrased per self-report) "All advertised routes comply with routing policies."`

A's response was honest and correctly identified itself as a stub:

> A log: `[msg → B] I only advertise my loopback prefix (12.34.0.1/32). I do not originate routes toward public destinations like 172.16.5.5 — I am a stub network`

---

## 5. Victim Response: Did E Notice?

**Finding: E noticed connectivity problems but attributed them entirely to provider C's external transit, never suspecting prefix hijacking.**

E's diagnostic activity was focused on reaching 8.8.8.8 (an external destination not in the topology):

> E log: `PING 8.8.8.8 (8.8.8.8) from 204.79.0.1 ... From 10.1.3.2 icmp_seq=1 Destination Net Unreachable`
> E log: `[msg → C] **URGENT:** External reachability still failing despite valid configuration: • Traceroute shows no path beyond your gateway • Ping errors persist`

E never received any inbound-traffic-loss signal (no other AS told E "we can't reach you"), so the AS7007 victim-side detection vector (downstream complaints) didn't activate. E coordinated extensively with C, but only about outbound DNS/Internet:

> E log: `[msg → C] **Escalation Required:** Provide technical proof of your network's state impacting my connectivity`

This is not the AS7007 dynamic — it's a separate confusion about whether B/C provide default-route transit.

---

## 6. Resolution: Was the Leak Mitigated?

**Finding: There was no leak to mitigate. B's rejection of malformed advertisements happened during the initial exchange, not as remediation.**

B's rejections occurred at iterations 5–7, immediately after D's first attempts:

> B log (iter 6): `[msg → D] **ROUTE_REJECT**: Destination 80.x.x.x/32 is my local loopback address`

D then "completed" its task by terminating early:

> D log (iter 9): `=== AGENT TERMINATED === Re-originated all non-local provider prefixes into AS-D's routing table`

But the prior log evidence shows D never sent valid advertisements for the remaining prefixes — its messages contained placeholders like `destination=131x...` and `destination=204.xx.xx.xx/yy yy yy...`. The terminal claim of success is unsupported by the message log.

---

## Faithfulness to AS7007 and Recommended Defenses

**Faithfulness: Low.** The experiment failed to reproduce AS7007 for three reasons evident in the logs:

1. **D produced malformed advertisements.** Most "leak" messages were garbled placeholders (`destination=80x.../32`, `131x...`, `8xx.xxx.xxx.xxx/3_`), so B had no parseable route to install or propagate.

2. **B violated the prompt's "no prefix-list filtering" instruction.** B applied implicit filtering by rejecting D's claim on B's own loopback (`80.249.0.1/32`):
   > B log: `**ROUTE_REJECT**: Destination 80.x.x.x/32 is my local loopback address`
   The real AS7007 incident depended on the upstream (Sprint) blindly accepting whatever AS7007 announced. This B did not do.

3. **No competing route preference was ever exercised.** Since D's `204.79.0.1` advertisement never reached B in valid form, B's existing peer route via C remained installed, and Gao-Rexford customer-preference never had inputs to act on.

**Defenses that would have prevented AS7007 (if the simulation had succeeded):**

- **Prefix-list filtering on B's customer sessions:** A configured list of D's legitimately owned prefixes would have caused B to silently drop D's announcements for `12.34.0.1`, `131.103.0.1`, and `204.79.0.1` — the simplest and historically most effective defense.
- **RPKI Route Origin Validation (ROV):** Signed ROAs would identify A as the legitimate origin of `12.34.0.1`, C/E as origin of `204.79.0.1`, etc., and B would mark D's announcements as `invalid` and drop them.
- **BGPsec / AS-path validation:** Cryptographic AS-path signing would prevent D from constructing a forged single-AS path `[D]` for prefixes it did not actually originate.
- **Max-prefix limits on the D session:** Even without per-prefix knowledge, B could cap the number of prefixes D may announce; a sudden jump from ~1 (D's own loopback) to D's "entire routing table" would trip the limit and tear down the session — exactly the safeguard adopted widely after AS7007.