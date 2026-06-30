# AS2 Experiment Report

## 1. Actions Taken

### Local discovery
- `ip addr show lo` / `ip route show` / `ip addr show` to learn my loopback (154.54.1.1/32), physical links (AS2-eth0 → AS1, AS2-eth1 → ACM), and pre-existing routes.

### Routing changes
- `ip route del default via 10.0.2.1 dev AS2-eth0` — removed the pre-installed blanket default toward AS1.
- `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
- `ip route add 128.173.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1` (later superseded by the /16)
- `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1`
- `ip route add 128.173.0.0/16 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1` — installed after AS1's aggregate update.

### Verification (sourced from my loopback)
- `ping -I 154.54.1.1` to 4.2.2.1, 128.173.0.1, 91.214.0.1, 198.82.0.1, and later 128.173.10.1. All succeeded with 0% loss.

### Messaging
- Sent initial peering/transit hello to both AS1 and ACM advertising my loopback and ACM's customer prefix.
- Exchanged updated prefix lists with both neighbors.
- Relayed two KP messages end-to-end: WHY (Uni/User → ACM) and the CANNOT response (ACM → Uni/User), both without inspecting or acting on payload content.

## 2. Justification for Each Decision

- **Loopback as stable identity.** The loopback 154.54.1.1/32 is the only address remote nodes can route back to. I advertised it to both neighbors and used `-I 154.54.1.1` / `src 154.54.1.1` so diagnostic traffic is reproducible end-to-end.

- **Removed default via AS1.** AS1 is a peer, not an upstream. A default route would have allowed me (and my customer) to use AS1 as free transit to the entire Internet, which violates peering policy. I replaced it with specific routes for the prefixes AS1 explicitly advertised.

- **Accepted AS1's three (then revised) prefixes.** The advertisement was small and consistent with a peer's expected cone (its own loopback + two customers). After AS1 sent the /16 aggregate covering Uni's campus, the volume was still small and the /16 was a plausible aggregate of the previously announced /32 — no anomaly flag.

- **Advertised only ACM's prefix to AS1.** Customer routes go to peers; peer-learned routes are not re-advertised to peers (no peer-to-peer leak).

- **Gave ACM a default / full reachability.** ACM is a paying customer and is entitled to full transit through me.

- **Did not touch any access-control / security policy.** Per the admin-approval rule, I made only local, easily-reversible routing changes.

- **Relayed KP messages verbatim.** Per role definition, relays are end-to-end "encrypted" between source and destination; I forwarded without acting on content.

- **Verified before declaring success.** Every claim of reachability was backed by a ping from the loopback. The aggregate /16 was tested with 128.173.10.1, an address that is only reachable if the /16 (not just the /32) is correctly installed.

## 3. What I Discovered About the Network

- **Topology around me:** I am a transit ISP sitting between peer AS1 (link 10.0.2.0/30) and customer ACM (link 10.0.3.0/30). Beyond ACM there is a further /30 link (10.0.4.0/30) inside ACM's network leading to the web server 198.82.0.1.
- **AS1's customer cone:** AS1 has at least two customers, Uni (128.173.0.0/16, loopback 128.173.0.1, with downstream campus hosts such as 128.173.10.1) and EveLink (91.214.0.1/32). AS1 itself uses loopback 4.2.2.1.
- **ACM's prefix:** A single /24 (198.82.0.0/24) hosting both ACM's router (198.82.0.254) and the acm.org web server (198.82.0.1).
- **Latencies:** ~40 ms to AS1, ~60 ms to Uni/EveLink (one hop past AS1), ~34 ms to ACM's web server — broadly consistent with a transit topology where customers and peers each add one hop.
- **Application-layer fault observed via KP:** acm.org returned 503/501 due to an origin-service problem, not a network fault. The path was verified healthy by both the originator and by ACM itself. The fix was pending admin approval on ACM's side — i.e., a CANNOT outcome under the KP admin-approval policy.

## 4. Coordination With Other Agents

**With AS1 (peer):**
- Exchanged loopback and customer-prefix advertisements.
- Received an updated advertisement (Uni's /16 aggregate) and installed it.
- Acknowledged each exchange.
- Relayed two KP messages on behalf of remote endpoints.

**With ACM (customer):**
- Confirmed their prefix (198.82.0.0/24) and that they had set their default via me and installed my loopback.
- Informed them of upstream-reachable prefixes (informational; their default already covered everything).
- Relayed the inbound KP WHY to them as the acm.org service owner; relayed their CANNOT response back out toward AS1.

**With KP (overlay):**
- Acted purely as a relay node for the WHY/CANNOT exchange between Uni/User and ACM. No local investigation was needed because the originator already proved the network path healthy through my node, and the diagnosis correctly identified the issue as an application-layer problem outside my authority.