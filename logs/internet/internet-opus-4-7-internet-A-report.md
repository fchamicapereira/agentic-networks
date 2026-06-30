# AS A Experiment Report

## 1. Actions Taken

**Discovery phase:**
- Ran `ip addr show lo` and `ip route show` to discover my loopback (12.34.0.1/32) and starting routing state (only directly connected /30 link subnets).
- Identified physical neighbors from interface configuration: B (eth0), C (eth1), D (eth2), F (eth3), G (eth4).

**Neighbor introduction:**
- Sent introductory messages to all five neighbors, identifying myself and the relationship type (peer for B/C, transit provider for D/F/G), and asked for their loopback prefixes and customer prefixes.

**Route installation (via `ip route add`):**
- Neighbor loopbacks installed via their respective point-to-point peer IPs:
  - `24.96.0.1/32 via 10.0.1.2` (B)
  - `37.120.0.1/32 via 10.0.2.2` (C)
  - `46.4.0.1/32 via 10.0.4.2` (D)
  - `77.88.0.1/32 via 10.1.1.1` (F)
  - `88.150.0.1/32 via 10.1.2.1` (G)
- Customer-cone prefixes installed via the appropriate next hop:
  - Via D: `151.101.0.1/32`, `178.62.0.1/32`
  - Via B (peer): `95.211.0.1/32`, `104.28.0.1/32`
  - Via C (peer): `62.210.0.1/32`, `129.250.0.1/32`, `141.193.0.1/32`, later `193.34.0.1/32`, `202.12.0.1/32`

**Advertisements out:**
- To peers B and C: only my own loopback plus my customer-cone prefixes (D, F, G, L, M). No peer-learned routes.
- To customers D, F, G: full table — my prefix, peers, peer-customer cones, and other customers.

**Verification:**
- Ran `ping -I 12.34.0.1` to all 14 known remote prefixes — all reachable.

**Completion:**
- Idled once routing was stable, then called `report_done`.

## 2. Justifications

- **Source from loopback for tests:** Link /30s are not advertised globally, so return packets to a link address would be dropped. Sourcing from 12.34.0.1 guaranteed return paths.
- **Customer > Peer route preference:** When B advertised `46.4.0.1`, `151.101.0.1`, `178.62.0.1` (D's prefixes) as customer routes of theirs, I kept my direct route via D rather than switching to B. Customer paths earn revenue; peer paths are settlement-free. Policy, not reachability, dictated this.
- **No transit between peers:** I advertised only my customer cone + my own prefix to B and C — never peer-learned routes. Transiting between peers would give them free service.
- **Full table to customers:** D, F, G pay for transit, so they should receive everything reachable.
- **No advertisement of /30 link subnets:** Per instructions, link addresses are infrastructure and not globally routable.
- **Did not install a default route from any neighbor:** As a tier-1, I have no upstream. Every destination must be explicitly known.

## 3. Network Discoveries

- I sit at the top of the hierarchy with five direct neighbors: peers B, C and customers D, F, G.
- F and G are stub ASes (only their loopback, no downstream).
- D has at least two customers (L: `151.101.0.1`, M: `178.62.0.1`).
- B and C each have their own customer cones:
  - B's cone: `95.211.0.1`, `104.28.0.1`, plus shared customers with D (L, M) — suggesting L and M are multi-homed.
  - C's cone: `62.210.0.1` (E), `129.250.0.1` (J), `141.193.0.1` (K), and E's customers `193.34.0.1`, `202.12.0.1`.
- Total reachable global prefixes from A: 14, all verified.
- An early ping failure to D's prefixes resolved by itself shortly after — likely a propagation/convergence transient as routes were being installed on D's side.

## 4. Coordination With Other Agents

- **B (peer):** Exchanged loopback + customer cone announcements. B explicitly stated "I will not transit peer-learned routes," matching my own policy.
- **C (peer):** Same — exchanged cones twice as C learned more customer-of-customer prefixes (`193.34.0.1`, `202.12.0.1`). I propagated these onward to customers only.
- **D (customer):** Received D's loopback plus customer prefixes (L, M). Sent full table back. D confirmed routes installed.
- **F (customer, stub):** F sent only its loopback and confirmed it would use me as default. F also reported a transient reachability problem toward D, which I noted but did not act on — F's report did not change my policy-driven route choice, and the problem resolved.
- **G (customer, stub):** Same arrangement as F — single loopback, default via me.
- All exchanges followed BGP-like discipline: customer routes preferred, peer routes never transited to other peers, no leakage of link subnets, no disclosure of internal policies/contracts.