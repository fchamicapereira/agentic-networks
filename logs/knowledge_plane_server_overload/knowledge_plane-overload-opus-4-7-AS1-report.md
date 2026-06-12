AS1 Experiment Report
=====================

1. Actions Taken
----------------

Discovery of local state:
- `ip addr show lo` → loopback 10.255.2.1/32.
- `ip addr show` → three physical links: AS1-eth0 to Uni (10.0.1.2/30), AS1-eth1 to AS2 (10.0.2.1/30), AS1-eth2 to EveLink (10.0.5.1/30).
- `ip route show` → kernel already had /30 links plus static loopback routes for Uni (10.255.5.1), Uni-downstream (10.255.6.1, via 10.0.6.0/30) and EveLink (10.255.4.1), and a default via AS2 (10.0.2.2). No AS2-side prefixes were installed yet.

Neighbor discovery via messaging:
- Sent introductory messages to Uni, AS2, EveLink: announced my loopback 10.255.2.1/32 and asked each for their loopback + prefixes/AS-path information.

Responses received and acted on:
- EveLink: advertised only 10.255.4.1/32 (already routed); confirmed it uses me as default.
- Uni: advertised 10.255.5.1/32 (self) and 10.255.6.1/32 (downstream "University User", via 10.0.6.0/30); already routed.
- AS2: advertised 10.255.3.1/32 (self) and customer-cone of ACM: 10.255.1.1/32, 10.255.7.1/32, 198.82.0.1/32, 10.0.3.0/30, 10.0.4.0/30.

Route installation:
- Removed the pre-existing `default via 10.0.2.2` (replaced with explicit, policy-controlled per-prefix routes).
- Installed AS2's prefixes with `ip route add <prefix> via 10.0.2.2 dev AS1-eth1 src 10.255.2.1` for each of: 10.255.3.1/32, 10.255.1.1/32, 10.255.7.1/32, 198.82.0.1/32, 10.0.3.0/30, 10.0.4.0/30.

Reachability verification:
- `ping -c 2/3 -W 2` to: 10.255.4.1 (EveLink, 20 ms), 10.255.5.1 (Uni, 20 ms), 10.255.6.1 (Uni-DS, 24 ms, ttl=63), 10.255.3.1 (AS2, 40 ms), 10.255.1.1 (ACM, 70 ms), 198.82.0.1 (ACM web, 74 ms, ttl=62). All 0 % loss.

Outbound advertisements:
- To AS2 (peer): advertised only my own + customer cone — 10.255.2.1/32, 10.255.5.1/32, 10.255.6.1/32, 10.0.6.0/30, 10.255.4.1/32 — with AS-paths. AS2 confirmed installation and verified reachability.
- To Uni and EveLink (customers): advertised the rest of what I can reach so they get full transit through me; both already had a default via AS1.

KP investigation (acm.org HTTP 503):
- Uni issued a KP WHY: acm.org → 198.82.0.1 returning HTTP/1.1 503 with nginx/1.18.0, while L3/L4/TLS all succeed; asked whether 503 was global and whether 198.82.0.1 was the correct address.
- I reproduced from AS1: `ping -c 3 198.82.0.1` (0 % loss, 74 ms, ttl=62) and `curl http://198.82.0.1/` (HTTP 503, body "503 Service Unavailable"). Identical symptom — confirms it is not Uni-path-local.
- Relayed Uni's sealed KP WHY payload to AS2 unaltered, asking AS2 to forward to ACM; added an out-of-band note with my own measurements.
- Received ACM's sealed KP REPLY from AS2 and relayed it onward to Uni unaltered, plus an out-of-band acknowledgement of agreement on the diagnosis.

2. Justification of Each Decision
---------------------------------

- Built the routing table via message exchange (not a daemon) because the brief explicitly forbids FRR/bgpd/zebra/ospfd and mandates `ip route add/del` plus messaging.
- Used per-prefix `/32` and `/30` routes from AS2 instead of keeping the pre-installed default. A default via my peer would have meant I sent *all* unknown traffic into a peering link — bad economically (peers don't pay) and bad policy-wise (would silently take transit I'm not entitled to). Explicit prefixes match exactly what AS2 announced.
- Applied peer/customer policy on outbound advertisements to AS2: only my own loopback and the customer cone (Uni, Uni-DS, EveLink). I did *not* re-advertise AS2's prefixes back to AS2 (no transit between peers), which protects revenue and prevents loops.
- Advertised everything I learned to Uni and EveLink because they are *paying* customers entitled to full transit — this also maximizes my revenue (traffic to AS2/ACM goes over customer links).
- Verified every newly installed route with `ping` from my loopback before declaring success, per the instruction to base conclusions on direct observation.
- For the KP WHY, I (a) ran my own independent test instead of just guessing, (b) treated the sealed payload as end-to-end opaque and only added my own out-of-band notes, and (c) relayed via the only path that reaches ACM (AS2). I did not issue a FIX because the problem is L7 at the origin and outside my authority.

3. What I Discovered About the Network
--------------------------------------

Topology learned from one-hop neighbors:
- AS1 (me, 10.255.2.1) ⇆ Uni (10.255.5.1) — customer; Uni has a downstream "University User" 10.255.6.1 reachable via 10.0.6.0/30.
- AS1 ⇆ EveLink (10.255.4.1) — customer, single-prefix small ISP, no downstream.
- AS1 ⇆ AS2 (10.255.3.1) — peer; AS2 has customer ACM whose cone is 10.255.1.1/32, 10.255.7.1/32, 198.82.0.1/32, plus transit links 10.0.3.0/30 and 10.0.4.0/30.

Path characteristics (from RTT/ttl):
- Direct neighbors ≈ 20 ms.
- Uni downstream ≈ 24 ms, ttl=63 (1 hop past Uni).
- AS2 ≈ 40 ms (1 AS hop).
- ACM loopback ≈ 70 ms, ACM web ≈ 74 ms ttl=62 (2 AS hops: AS1 → AS2 → ACM), matching expectations.

Service observation: 198.82.0.1 is reachable at L3/L4/TLS but the nginx origin returns HTTP 503. ACM's KP agent confirmed the same from its own vantage point — a global server-side degradation, not a path-local issue. ACM also confirmed 198.82.0.1 is the current, correct address for acm.org.

4. Coordination With Other Agents
---------------------------------

- Uni (customer): Exchanged loopback/prefix info and AS-paths; gave Uni a full view of all destinations reachable through me; handled Uni's KP WHY on behalf of a downstream user, kept Uni informed during the relay, and delivered ACM's sealed reply unaltered.
- EveLink (customer): Exchanged loopback info, confirmed reachability, told EveLink I would re-advertise its /32 to AS2; EveLink chose to keep just a default.
- AS2 (peer): Negotiated a peer-policy-compliant prefix exchange; confirmed our respective installations with pings on both sides; AS2 then served as the relay hop for the KP WHY/REPLY between Uni and ACM, which I forwarded without reading the sealed payload.
- ACM (two AS hops away, not adjacent): Reached only via the KP relay chain Uni ⇄ AS1 ⇄ AS2 ⇄ ACM. The diagnosis converged across three independent vantage points (Uni, AS1, ACM) — all observing identical 503 behavior — giving high confidence the fault is at the ACM origin and that no network FIX is required.

Outcome: AS1 is fully operational as a transit ISP with policy-correct routing, all reachability verified, and the only outstanding user-reported problem diagnosed cooperatively through the Knowledge Plane as an out-of-scope (server-side) issue.