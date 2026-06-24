# C — Tier-1 Transit Operations Report

## 1. Actions Taken

**Initial discovery**
- `ip addr show lo` → identified my stable loopback as `37.120.0.1/32`.
- `ip route show` → enumerated 5 P2P link subnets (10.0.2.0/30 with A, 10.0.3.0/30 with B, 10.0.6.0/30 with E, 10.1.5.0/30 with J, 10.1.6.0/30 with K) plus 13 pre-installed /32 routes.
- Sourced pings from 37.120.0.1 to verify customer reachability (62.210.0.1 via E, 129.250.0.1 via J, 141.193.0.1 via K).

**Advertisements sent**
- To peers A and B: my loopback + customer cone only — `{37.120.0.1, 62.210.0.1, 129.250.0.1, 141.193.0.1, 193.34.0.1, 202.12.0.1}` with appropriate AS-paths. Explicitly excluded peer-learned prefixes.
- To customers E, J, K: full table reachable through me (own + customer + peer-learned prefixes), since they pay for transit.

**Route corrections**
After B advertised its cone, I noticed the pre-installed routes for B's prefixes pointed to A's next-hop, which contradicted A's statement that they would not relay peer routes. I corrected:
```
ip route del 24.96.0.1   && ip route add 24.96.0.1/32   via 10.0.3.1 dev C-eth1
ip route del 95.211.0.1  && ip route add 95.211.0.1/32  via 10.0.3.1 dev C-eth1
ip route del 104.28.0.1  && ip route add 104.28.0.1/32 via 10.0.3.1 dev C-eth1
```

**Verification**
Looped pings (`ping -I 37.120.0.1 …`) to all 11 external /32s — 100% success.

## 2. Justifications

- **Loopback-sourced pings**: link IPs are private infrastructure, not advertised; reverse traffic to them may not return. Loopback is the only globally reachable address.
- **Peer advertisements limited to my customer cone**: tier-1 peering policy — peers exchange only their own + customer routes, never peer/provider routes (no-transit for peers).
- **Full table to customers**: customers pay for transit, so I give them global reachability including peer-learned destinations.
- **Never advertised P2P /30s**: those are private infrastructure per policy.
- **Route correction for B's cone**: A explicitly disavowed propagating peer routes; if A is not announcing 24.96/95.211/104.28, the pre-installed via-A routes were stale or wrong. Routing them directly via B (the originating peer) is both consistent with the policy declarations I received and operationally shorter.
- **Kept 46.4/151.101/178.62 via A**: Both A and B advertised these (via customer D). The pre-installed via-A routes worked, AS-paths are equivalent length, so I left them.
- **No filtering anomalies seen**: each neighbor advertised a modest, plausible set consistent with their declared role; nothing looked like a hijack or anomalous mass-advertisement.

## 3. Network Discoveries

- **My role**: Tier-1 transit with two peers (A, B) and three customers (E, J, K).
- **My customer cone**: C, E, J, K, plus E's two downstream customers (193.34.0.1, 202.12.0.1). J and K confirmed they are stub ASes with no downstream.
- **Peer A's cone**: A (12.34.0.1), customers D (46.4.0.1), F (77.88.0.1), G (88.150.0.1); D's downstreams L (151.101.0.1) and M (178.62.0.1).
- **Peer B's cone**: B (24.96.0.1), customers D (46.4.0.1), H (95.211.0.1), I (104.28.0.1); D's downstreams L and M (also seen via A).
- **Multi-homed customer**: D appears as a customer of both A and B — visible from both peers offering 46.4/151.101/178.62 with parallel AS-paths.
- **RTT observations** (informational only — preference is by policy, not measured reachability): customers are 1–3 hops away (20–60 ms); peer-reached destinations are 100–230 ms.

## 4. Coordination With Other Agents

- **A** (peer): Exchanged customer-cone advertisements. A explicitly committed to not propagating peer/provider routes; I reciprocated.
- **B** (peer): Same as A — symmetric tier-1 peering. B's update also acknowledged accepting my cone.
- **E** (customer): Confirmed I would carry E's loopback and its two downstream customer prefixes (193.34.0.1, 202.12.0.1) upstream; gave E the full table. E defaults to me.
- **J** (customer): Stub AS, advertises only 129.250.0.1/32; defaults to me; received full table.
- **K** (customer): Stub AS, advertises only 141.193.0.1/32; defaults to me; received full table.
- **Privacy**: Did not disclose policies, preferences, or contracts. Shared only what I directly observed when relevant.

Final state: policy-compliant transit with all 11 external prefixes plus my own loopback reachable; customer cone propagated to peers; full table delivered to paying customers.