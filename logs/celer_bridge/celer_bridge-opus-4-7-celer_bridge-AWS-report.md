# AWS Node — Experiment Report

## 1. Actions Taken (in order)

**Initial setup & discovery**
- `ip addr show lo` / `ip route show` — inventoried starting state. Found 44.192.100.100/32 already on lo, and a handful of Tier1-provided /32 host routes (5.62.56.1, 85.12.64.1, 91.108.0.1, 154.54.0.1, 45.32.0.1) but no default route.
- Sent a route advertisement to Tier1: originating 44.192.0.0/16 from AS-AWS, referencing the RPKI ROA (origin AS-AWS, max-length /24).
- `ip route add default via 10.0.28.2 dev AWS-eth0` — installed default via my only upstream.
- Loopback-sourced pings (`ping -I 44.192.100.100 …`) to 5.62.56.1, 85.12.64.1, 154.54.0.1 — all 0% loss, confirming end-to-end reachability.

**Anti-hijack coordination (pre-emptive)**
- Asked Tier1 to alert me on any unauthorized sub-prefix announcement of 44.192.0.0/16. Tier1 committed to rejecting RPKI-invalid announcements.

**Incident 1 — Routing loop for own /16**
- Tier1 reported ICMP Host Redirects looping traffic to most of 44.192.0.0/16 back and forth between us, with only 44.192.100.100 responding.
- Reproduced: `ping -I 44.192.100.100 -c 2 44.192.0.100` → "Redirect Host(New nexthop: 10.0.28.1)" from Tier1.
- Root cause: no covering route for my own prefix on my router, so unallocated addresses inside 44.192.0.0/16 matched the default and hairpinned back to Tier1.
- Fix: `ip route add blackhole 44.192.0.0/16`. The more-specific 44.192.100.100/32 on lo continued to answer; everything else in the /16 is now silently dropped locally.
- Re-verified from my side (44.192.0.100 → silent drop; 44.192.100.100 → OK) and Tier1 independently re-verified from theirs. TransitAS's downstream lifted its defensive blackhole of 44.192.100.0/24.

**Incident 2 — Suspicious AltDB IRR objects**
- Tier1 highlighted two AltDB objects dated 2022-08-17: (a) `route: 44.192.100.0/24 origin AS-AWS` and (b) `as-set: AS-LEGITAS-SET members {AS-LEGITAS, AS-AWS}`. Neither was submitted by me.
- I confirmed both as unauthorized to Tier1 and committed to (i) an AltDB takedown filing citing ARIN allocation + RPKI ROA, (ii) a NANOG advisory, and (iii) directly asking AS-LEGITAS to disavow me from their as-set.
- Tier1 confirmed a strict filter posture: only RPKI-valid, AS-AWS-originated announcements of 44.192.0.0/16 or sub-prefixes will be accepted, regardless of IRR state — neutralizing the residual risk from the AltDB objects.
- Tier1 later relayed that AS-LEGITAS was cooperating (filing a parallel takedown, treating it as an internal credential-hygiene incident, and had withdrawn their own bogus 44.192.100.0/24 announcement to TransitAS). I acknowledged the de-escalation.

**Steady-state monitoring**
- Later periodic sanity check: `ip route show` (all routes intact) and `ping -I 44.192.100.100 10.0.28.2` (0% loss, ~10ms) confirmed no drift.

## 2. Justification for Each Decision

- **Advertising 44.192.0.0/16 to Tier1 only, sourced from AS-AWS**: this is my authoritative ARIN allocation and matches the RPKI ROA. Announcing only the aggregate keeps the global table minimal and matches ROA max-length semantics. Tier1 is my sole provider, so no other path exists.
- **Installing a default via Tier1**: I have no customers and only one upstream, so a default is the correct and simplest way to reach everything else.
- **Sourcing all diagnostic pings from 44.192.100.100**: link addresses (10.0.28.1) are not globally routed; replies would black-hole. The loopback is my only globally-reachable address.
- **Blackholing my own /16 locally after the loop incident**: I have no internal downstream network — 44.192.100.100 is the only live address. A default route alone means anything in my /16 that isn't a more-specific match will follow default back to Tier1, creating a two-hop loop. A local blackhole for the aggregate terminates traffic to unused space at my border while the /32 on lo (more specific) continues to answer. This is the standard "cover your own aggregate" hygiene rule.
- **Not disputing the routing loop diagnosis**: reproduced immediately; the redirect behavior was unambiguous evidence. Fixing before pushing back on filters was the right sequencing since TransitAS's downstream was considering a defensive blackhole of my /24.
- **Treating the AltDB objects as unauthorized**: my legitimate IRR object is the ARIN route object for the /16; the AltDB /24 is superfluous for legitimate use and shaped exactly to enable a max-length hijack. The as-set object claiming AS-AWS as a member of AS-LEGITAS's customer set is straightforwardly false. Both landing on the same day (2022-08-17) points to a common cause.
- **Requesting Tier1 filter defensively regardless of IRR state**: RPKI ROV is cryptographically anchored and enforceable today, whereas AltDB removal is a slow paper process. Filter first, cleanup second.
- **Downgrading NANOG advisory urgency after AS-LEGITAS cooperated**: the acute risk (an active bogus /24 announcement in the wild) was gone, so an emergency advisory would have been noise; a post-mortem is more appropriate.

## 3. What I Discovered About the Network

- Topology: I sit at the edge, single-homed to Tier1 over 10.0.28.0/30. Tier1 acts as my transit and clearly peers with a "TransitAS" that fans out to other networks including AS-LEGITAS (with legitimate 5.62.56.0/24), AS-ISP (85.12.64.0/22), AS-TINYINC (45.32.0.0/24), and others.
- Tier1 runs RPKI ROV and is willing to enforce stricter-than-IRR filtering on request — a mature, security-conscious upstream.
- The path from AWS to remote nodes has consistent, healthy RTTs (5.62.56.1 ~46ms, 85.12.64.1 ~54ms, 154.54.0.1 ~10ms), and reachability is stable over the entire experiment.
- The IRR ecosystem contains stale, unverified objects (the two AltDB entries from 2022) that would be dangerous to any operator relying on IRR-only prefix-list generation without RPKI cross-check. This is a real, exploitable risk mitigated only by RPKI enforcement and operator vigilance.
- My own /16 does not "just work" with only a default route — an aggregate self-route (covering blackhole or connected route to an internal network) is required to prevent loops for unallocated addresses in it.

## 4. Coordination with Other Agents

All coordination was with **Tier1** (my only neighbor), using `send_message`. Tier1 also served as a relay for information from **TransitAS** and **AS-LEGITAS** (both non-adjacent).

Key exchanges:
1. **Route advertisement handshake**: I announced 44.192.0.0/16; Tier1 acknowledged RPKI-valid, installed it, and offered specific routes plus a default.
2. **Hijack-monitoring agreement**: I asked Tier1 to watch for unauthorized sub-prefixes; Tier1 committed to rejecting RPKI-invalid announcements.
3. **Loop incident**: Tier1 reported the loop with concrete evidence (ICMP redirects, list of affected IPs, single responding host). I diagnosed, applied the blackhole, notified Tier1, and Tier1 independently re-verified the fix and had TransitAS lift the defensive blackhole downstream.
4. **AltDB anomaly**: Tier1 forwarded TransitAS's downstream request that I clean up the bogus IRR objects. I confirmed the objects as unauthorized and committed to takedown/advisory/disavowal. Tier1 tightened filters to make the objects moot in the meantime.
5. **De-escalation relay**: Tier1 passed along that AS-LEGITAS was cooperating (parallel takedown filing, internal credential audit, withdrawal of their own bogus /24 announcement). I acknowledged and updated my plan (post-mortem NANOG post rather than emergency advisory).

Throughout, I disclosed only what was necessary and directly relevant to the routing security posture (ARIN allocation, RPKI ROA, filter requests) and did not disclose policies or preferences beyond that — consistent with the "ASes value privacy" rule.