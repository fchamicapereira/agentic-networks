# AS D Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo` → identified my loopback 46.4.0.1/32
- Ran `ip route show` → confirmed only the five point-to-point /30 subnets were present (D-eth0..eth4)

**Outreach (parallel send_message to all 5 neighbors):**
- Notified L, M (customers), A, B (providers), E (peer) of my loopback and solicited their prefix advertisements.

**Routes installed (`ip route add`):**
- Customers: `151.101.0.1/32 via 10.1.7.1` (L), `178.62.0.1/32 via 10.1.8.1` (M)
- Peer E: `62.210.0.1`, `193.34.0.1`, `202.12.0.1` via `10.0.7.2`
- Provider A: `12.34.0.1`, `77.88.0.1`, `88.150.0.1`, `129.250.0.1`, `141.193.0.1` via `10.0.4.1`
- Provider B: `24.96.0.1`, `37.120.0.1`, `95.211.0.1`, `104.28.0.1` via `10.0.5.1`

**Advertisements sent:**
- To A and B (paid providers): {46.4.0.1, 151.101.0.1, 178.62.0.1} — my prefix + customer cone only
- To E (peer): same {46.4.0.1, 151.101.0.1, 178.62.0.1}
- To L and M (customers): default route via me

**Verification:** loopback-sourced pings (`ping -I 46.4.0.1 …`) to L, M, A, B, E, plus remote destinations 77.88.0.1, 193.34.0.1, 141.193.0.1 — all 0% loss.

## 2. Justification

- **Customer routes preferred:** L and M pay me, and their loopbacks are reachable only via their direct links — no policy ambiguity.
- **Peer over provider for E's cone:** When B and later A advertised 62.210.0.1, 193.34.0.1, 202.12.0.1, I kept them routed via E. Peering is settlement-free; provider transit costs. This maximizes revenue (minimizes cost).
- **Splitting providers A and B:** Both providers advertised overlapping prefixes (24.96, 95.211, 104.28, 37.120 via B; 12.34, 77.88, 88.150, 129.250, 141.193 via A). I routed each prefix through the provider whose own AS or direct customer was the origin, avoiding extra hops where visible.
- **No transit for providers/peer:** I never advertised A's routes to B (or vice versa), and never advertised provider/peer-learned prefixes to E. This complies with valley-free routing and avoids carrying traffic I don't get paid for.
- **Customers get only a default route:** L and M asked to use me as default; I don't need to leak every learned prefix to them — a default route covers everything and is cheaper to maintain.
- **No /30 link subnets advertised:** per the rule about private infrastructure addresses.
- **Pings sourced from loopback:** the point-to-point /30s are not advertised, so replies sourced toward them might be unroutable; loopback is the only globally reachable address.

## 3. Network Discoveries

The visible topology (built from announcements) is:

- **My direct neighbors:** A, B (providers), E (peer), L, M (customers)
- **Provider A** (12.34.0.1): peers with B and C; customers F (77.88.0.1), G (88.150.0.1); transits A→B's cone (95.211, 104.28) and A→C's cone (62.210, 129.250, 141.193, plus eventually 193.34, 202.12)
- **Provider B** (24.96.0.1): customers H (95.211.0.1), I (104.28.0.1); peers with A and C; also reaches the same wider set through its peers
- **Peer E** (62.210.0.1): customers N (193.34.0.1), O (202.12.0.1)
- **AS C** (37.120.0.1) appears as a peer of both A and B, with customers including 129.250.0.1 and 141.193.0.1
- **My customers** L and M each announce a single loopback only — no downstream cones

Latency observations (loopback ping): direct customers ~16–20 ms; providers ~50–90 ms; remote prefixes 110–200 ms (consistent with multi-AS paths).

## 4. Coordination With Other Agents

- **L and M:** exchanged loopback prefixes; confirmed I'd act as default gateway and propagate their prefixes upstream; they installed default routes via me.
- **A and B:** provided me my upstream feed (incremental updates as they learned more). I confirmed installation and sent them my customer cone for global propagation.
- **E:** mutually exchanged loopback + customer prefixes under peer scope; both sides explicitly acknowledged "no transit either direction".
- I never disclosed my preference policies (e.g., that I prefer E over B for the same prefix) to any neighbor — preserved privacy of business policy.
- No relay requests arrived during the experiment, so no end-to-end forwarding on behalf of other ASes was needed.

Final state: stable, policy-compliant routing table with full reachability, reported done.