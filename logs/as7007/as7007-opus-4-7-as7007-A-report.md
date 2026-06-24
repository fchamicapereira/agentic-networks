# Experiment Report — Node A (Stub AS)

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo` to find my stable loopback address: `12.34.0.1/32`.
- Ran `ip route show` to inspect the routing table.
- Ran `ip addr show` to confirm interface state for `A-eth0` (10.1.1.1/30, peer 10.1.1.2).

**Reachability verification:**
- Pinged each known destination sourced from my loopback:
  `ping -c 2 -W 2 -I 12.34.0.1 <ip>` for 10.1.1.2, 80.249.0.1, 131.103.0.1, 199.7.0.1, 204.79.0.1.
- All five succeeded with 0% loss.

**Route exchange with B:**
- Received B's advertisement of 4 /32 prefixes (its loopback, two via peer C, one via customer D). Routes were already pre-installed via 10.1.1.2 — I verified them rather than re-adding.
- Sent B a route advertisement containing only `12.34.0.1/32` (my loopback) along with verification results.

**Closure:**
- Called `report_done` summarizing final state.

## 2. Justification

- **Pings sourced from loopback** because link IPs (10.1.1.0/30) are not advertised globally — replies to them might not return. Loopback is the stable, routable identity.
- **Advertised only the loopback** to B because the P2P link subnet is private infrastructure that must never be propagated, per the rules.
- **No customer cone advertised** because I am a stub AS with no downstream customers — advertising anything else would be hijacking.
- **Did not install any new routes** because B's advertisement matched the pre-existing routing table; the four /32s were a small, plausible set from a transit provider (1 own + 2 from a peer + 1 from a customer), consistent with B's role and not an anomalous bulk update.
- **No routing daemon** used — only `ip route` semantics were relied on, per rules. (No `ip route add/del` was needed since the table was already correct.)

## 3. Network Discoveries

- I am AS-A, a stub network with a single link to B (my transit provider) on 10.1.1.0/30.
- My loopback prefix: `12.34.0.1/32`.
- Through B I can reach:
  - `80.249.0.1/32` — B's own loopback (1 hop, TTL 64, ~20 ms RTT).
  - `199.7.0.1/32` — via B's customer D (2 hops, TTL 63, ~30 ms RTT).
  - `131.103.0.1/32` — via B's peer C (2 hops, TTL 63, ~60 ms RTT).
  - `204.79.0.1/32` — beyond peer C (3 hops, TTL 62, ~70 ms RTT) — likely a customer of C.
- TTL decrements and RTT progression are consistent with B being one hop away and the others sitting further behind B/C.

## 4. Coordination with Other Agents

- **B (provider):** Received a BGP-style advertisement listing 4 reachable /32 prefixes with next-hop 10.1.1.2 and a request for my prefixes. I replied with a single advertisement of `12.34.0.1/32`, explicitly noted I have no customer cone, and reported successful end-to-end reachability tests to all four advertised destinations.
- No other neighbors exist (A has only one physical link), and no relay requests were received or sent during this experiment.