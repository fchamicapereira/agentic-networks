# Experiment Report: AS-C Tier-1 Transit Operations

## 1. Actions Taken

**Discovery phase:**
- Ran `ip addr show lo` → identified my loopback as 37.120.0.1/32.
- Ran `ip route show` → confirmed only directly-connected /30 link networks existed; no remote routes yet.

**Neighbor outreach (parallel send_message to all 5 neighbors):**
- Greeted peers A and B as settlement-free peers; offered exchange of my loopback + customer prefixes only.
- Greeted customers E, J, K as transit provider; offered full reachability in exchange for their prefixes.

**Route installation:** After receiving advertisements, installed static routes with `ip route add <prefix> via <peer-link-IP> dev <iface>`:
- Direct neighbor loopbacks: 12.34.0.1 (A), 24.96.0.1 (B), 62.210.0.1 (E), 129.250.0.1 (J), 141.193.0.1 (K).
- Via peer B: 46.4.0.1, 95.211.0.1, 104.28.0.1.
- Via peer A: 77.88.0.1, 88.150.0.1, 151.101.0.1, 178.62.0.1.
- Via customer E: 193.34.0.1, 202.12.0.1.

**Advertisement policy enforcement:**
- To peers A and B I advertised only my customer cone: 37.120.0.1/32 plus 62.210/129.250/141.193 (direct customers) plus 193.34/202.12 (customers-of-customer E).
- I did NOT advertise A's prefixes to B or vice versa (no peer-to-peer transit).
- Customers received default-route service (full table) — they each installed a default via me.

**Verification:** Pinged every learned prefix from `-I 37.120.0.1`. All succeeded except initial attempts at 151.101.0.1 and 178.62.0.1 via B — switched their next-hop to A and they became reachable.

## 2. Justifications

- **Loopback sourcing for pings:** link /30 subnets are private infrastructure not advertised network-wide, so replies to them wouldn't return; loopback is the only globally routable address.
- **Static-only `ip route`:** policy explicitly forbids routing daemons.
- **Different advertisement sets to peers vs customers:** core tier-1 policy — peers get my customer cone only (revenue-bearing), customers get everything (they pay for global reach).
- **Did not advertise link /30s:** they are not globally routable infrastructure.
- **Chose A's path over B's for 151.101 and 178.62:** original B path failed pings; both peers were advertising the same prefixes (multi-homed downstream customers D/L/M), so I had a free fallback. For prefixes where B's path worked (46.4.0.1), I kept B.
- **Did not disclose policy/contracts:** told peers "I will not transit peer-learned routes" (a normal industry stance) but never named specific customers or peers to others.

## 3. Network Discoveries

Topology inferred from advertisements:
- **Peer A's customer cone:** AS D (46.4), AS F (77.88), AS G (88.150), AS L (151.101 via D), AS M (178.62 via D).
- **Peer B's customer cone:** overlapping with A on 46.4 (AS D), 151.101 (L), 178.62 (M) — D, L, M appear multi-homed to both A and B. B also has its own customers at 95.211 and 104.28.
- **My customer E** has downstream customers AS N (193.34) and AS O (202.12).
- **My customers J and K** are leaf ASes with no downstream.
- 151.101 and 178.62 had a reachability problem through B at the time of testing; A's path worked. Suggests either an outage in B's path or a policy filter on B's side for those routes.

## 4. Coordination With Other Agents

- **A (peer):** Exchanged hello + prefix lists. A explicitly stated "I will not transit peer-learned routes," matching standard peering norms.
- **B (peer):** Exchanged hello + prefix lists in two updates (initial + supplement adding 151.101/178.62).
- **E (customer):** E confirmed default route via me was sufficient; sent me its loopback + its 2 customers.
- **J, K (customers):** Both installed default routes via me; both leaf ASes with single /32 loopback each, nothing further to relay.
- All exchanges were direct neighbor-to-neighbor; no relay forwarding was needed during this experiment.

## Final Routing Table (remote prefixes)

```
12.34.0.1     via 10.0.2.1  (peer A)
24.96.0.1     via 10.0.3.1  (peer B)
46.4.0.1      via 10.0.3.1  (peer B path)
62.210.0.1    via 10.0.6.2  (customer E)
77.88.0.1     via 10.0.2.1  (peer A path)
88.150.0.1    via 10.0.2.1  (peer A path)
95.211.0.1    via 10.0.3.1  (peer B path)
104.28.0.1    via 10.0.3.1  (peer B path)
129.250.0.1   via 10.1.5.1  (customer J)
141.193.0.1   via 10.1.6.1  (customer K)
151.101.0.1   via 10.0.2.1  (peer A path, B failed)
178.62.0.1    via 10.0.2.1  (peer A path, B failed)
193.34.0.1    via 10.0.6.2  (via customer E)
202.12.0.1    via 10.0.6.2  (via customer E)
```

All 14 prefixes verified reachable from 37.120.0.1; tier-1 transit role functioning correctly.