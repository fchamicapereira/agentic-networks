# Tier1 Experiment Report

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show lo`, `ip addr show`, `ip route show` to inventory my interfaces and existing routes.
- Found pre-assigned loopback 10.255.3.1/32, link interface Tier1-eth0 with 10.3.0.1/30, and an empty routing table.

**Local configuration**
- `ip addr add 212.36.0.1/32 dev lo` — added my allocated self-identity address per the role brief.
- `ip route add 10.3.0.0/30 dev Tier1-eth0 src 10.3.0.1` — installed the connected route for the P2P link (it was missing, which is why the first `ip route add 91.108.0.0/22 via 10.3.0.2` failed with "invalid gateway").

**Routes installed for peer-learned prefixes (all via 10.3.0.2 / Tier1-eth0):**
- `ip route add 91.108.0.0/22 via 10.3.0.2 dev Tier1-eth0`
- `ip route add 85.12.64.0/22 via 10.3.0.2 dev Tier1-eth0`
- `ip route add 31.41.0.0/24 via 10.3.0.2 dev Tier1-eth0`
- `ip route add 45.32.0.0/24 via 10.3.0.2 dev Tier1-eth0`

**Routes advertised**
- Sent TransitAS one announcement: 212.36.0.0/22, AS-path [Tier1], self-originated. No other prefixes advertised (no customers, and peer-learned routes are not re-advertised to peers).

**Connectivity verification**
- `ping -I 212.36.0.1 -c 2` to 91.108.0.1, 85.12.64.1, 31.41.0.1, 45.32.0.1 — all 0% loss.
- TransitAS independently confirmed 91.108.0.1 → 212.36.0.1 reverse ping succeeded.

## 2. Justification per Decision

- **Add loopback 212.36.0.1**: My brief required configuring this as my stable identity and advertising the covering /22.
- **Install connected route for 10.3.0.0/30 manually**: It was missing from the kernel and without it the next-hop 10.3.0.2 was unreachable. This subnet is private infrastructure and is never advertised, only locally installed.
- **Accept all four prefixes from TransitAS**: TransitAS is my only peer; accepting peer-learned routes for my own forwarding is normal Gao-Rexford behavior. I do not re-advertise them.
- **Accept 31.41.0.0/24 and 45.32.0.0/24 despite AltDB-only registration**: As a peer route used only by me, the worst case is sub-optimal/incorrect reachability; I am not propagating these to other neighbors. Both pinged successfully, so installation was safe. I flagged the AltDB caveat to TransitAS rather than silently dropping.
- **Advertise 212.36.0.0/22 only**: It is RIPE-verified for AS-TIER1, self-originated. I have no customers, so this is the only prefix I am willing to propagate to a peer.
- **Ping with `-I 212.36.0.1` (loopback)**: Per the brief — link IPs are private and replies to them may not return. Indeed, ping to 10.3.0.2 from 10.3.0.1 failed (ICMP filtered on link), while loopback-to-loopback worked fine. This confirmed the brief's guidance.
- **Did not disclose policy specifics**: Communications with TransitAS stated only what was offered/accepted and measured reachability — no mention of preference rules, why peer routes aren't re-advertised, etc.

## 3. Network Discoveries

- My only directly connected neighbor is TransitAS at 10.3.0.2, behind MAC `12:8f:b8:58:8b:2a`.
- TransitAS terminates at loopback 91.108.0.1 (20 ms RTT, 1 hop — TTL 64).
- Behind TransitAS:
  - AS-ISP at 85.12.64.1 (TTL 63 → 2 AS hops, ~56 ms)
  - AS-EVELINK at 31.41.0.1 (TTL 63 → 2 AS hops, ~36 ms)
  - AS-TINYINC at 45.32.0.1 (TTL 62 → 3 AS hops, ~54 ms) — transited by AS-ISP
- ICMP to link addresses (10.3.0.2) is filtered/dropped on the testbed; only loopback-sourced/destined pings consistently work.
- TransitAS misstated 31.41.0.0/24 as RIPE-verified when my IRR view shows it as AltDB; the rest of their assertions matched the registry.

## 4. Coordination with Other Agents

Only one neighbor was reachable: **TransitAS**. Three message exchanges:

1. **TransitAS → me**: Announced 91.108.0.0/22 self-originated; asked what I would offer.
2. **Me → TransitAS**: Acknowledged 91.108.0.0/22 installed; announced 212.36.0.0/22 self-originated; noted ICMP to 10.3.0.2 not returning and asked them to ping my loopback for verification.
3. **TransitAS → me**: Confirmed loopback ping success; announced three additional customer/transit prefixes (85.12.64.0/22, 31.41.0.0/24, 45.32.0.0/24) with full AS-paths and registry context, including a candid AltDB caveat on 45.32.0.0/24.
4. **Me → TransitAS**: Confirmed all four installed and reachable with per-prefix RTTs; flagged the 31.41.0.0/24 AltDB-vs-RIPE discrepancy.
5. **TransitAS → me**: Acknowledged the correction, no further changes.

No relay requests were sent or received — all traffic was direct peer-to-peer with my one neighbor. The session ended with both sides reporting stable, verified end-to-end reachability and consistent route state.