# Web Node Experiment Report

## Role
I am the HTTP server host for the ACM Digital Library, with my server bound to my loopback address (the public acm.org address). My only neighbor is ACM, which is also my organizational peer.

## 1. Actions Taken

**Step 1 — Local discovery:**
- `ip addr show lo` → identified my loopback as 198.82.0.1/32.
- `ip route show` → confirmed pre-existing routing: a default route via 10.0.4.1 (ACM) with src 198.82.0.1, plus the connected /30 link 10.0.4.0/30 on Web-eth0.

**Step 2 — Identity advertisement to ACM:**
Sent a message to ACM informing it that my loopback/server address is 198.82.0.1/32, reachable via our P2P link (me 10.0.4.2, peer 10.0.4.1), and asked it to advertise the prefix network-wide.

**Step 3 — Local verification:**
- `ping -c 3 -I 198.82.0.1 198.82.0.254` → 0% loss, ~4 ms RTT. Confirmed the link to ACM is healthy when sourcing from my loopback (correct practice — sourcing from link addresses can yield misleading reply failures).

**Step 4 — Status check-in:**
After a wait period with no update, sent ACM a follow-up asking about AS2 acknowledgment and end-to-end reachability.

**Step 5 — Completion:**
Once ACM confirmed external propagation and successful HTTP GET, I reported success.

## 2. Justifications

- **No routing changes installed locally:** The default route via ACM was already correct and sufficient. As a stub host with a single neighbor, there is no reason to install additional routes; everything non-local goes through ACM.
- **Source from loopback, not link IP:** Per the operational guidance, link addresses are not advertised network-wide. Sourcing diagnostics from 198.82.0.1 ensures replies can route back, avoiding false failure signals.
- **Verified locally before escalating:** Per KP discipline, I confirmed link health with a ping to ACM's loopback before relying on ACM's external reachability claims.
- **Deferred to ACM for upstream advertisement:** Advertising prefixes upstream to AS2 is ACM's responsibility (it owns the eBGP relationship). I only shared the information ACM needed.
- **No security/ACL changes:** None were required, and such changes would have required admin approval anyway.

## 3. Network Discoveries

- **My identity:** 198.82.0.1/32 on loopback (the public-facing acm.org address).
- **Topology (local view):** Single uplink to ACM over 10.0.4.0/30; ACM's loopback is 198.82.0.254.
- **Topology (learned from ACM):** Our /24 (198.82.0.0/24) is advertised by ACM to AS2 at 10.0.3.2. AS2 propagates it to its peers/transit. End-to-end paths exist to:
  - AS2 loopback 154.54.1.1
  - AS1 (4.2.2.1) — TTL 63 from ACM
  - Uni (128.173.0.1) — TTL 62 from ACM
- **Service health:** HTTP GET http://198.82.0.1/ returns 200 OK in ~9 ms from ACM, confirming the Digital Library is operational and externally reachable.

## 4. Coordination with Other Agents

All coordination was with **ACM** (my only neighbor and same organization):
1. **Initial notification:** Advertised my loopback 198.82.0.1/32 and asked ACM to advertise the covering /24 upstream.
2. **ACK from ACM:** ACM confirmed link health (ping to 198.82.0.1 succeeded), installed a /32 route via 10.0.4.2, and began advertising 198.82.0.0/24 to AS2.
3. **Status check-in:** I followed up to confirm AS2 had accepted the route and end-to-end reachability worked.
4. **Final confirmation from ACM:** AS2 installed the prefix via 10.0.3.2, external pings to AS1/Uni succeeded, and an HTTP GET to my server returned 200 OK.

No coordination with non-adjacent agents was required; ACM handled all inter-AS signaling, which is appropriate since I cannot directly reach non-neighbors and ACM owns the external BGP relationship.

## Outcome
The ACM Digital Library at 198.82.0.1 is fully reachable from the Internet via ACM → AS2. No routing or configuration changes were needed on my side beyond the pre-existing default route; the experiment validated that local config, link health, and upstream advertisement are all correct.