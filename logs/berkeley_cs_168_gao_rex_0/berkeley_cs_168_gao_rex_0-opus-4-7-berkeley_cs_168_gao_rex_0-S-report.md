# Experiment Report — Node S

## 1. Actions Taken

**Discovery / state inspection**
- `ip addr show lo` → discovered my loopback address `137.21.0.1/32`.
- `ip route show` → confirmed only the three directly connected /30 link subnets were present initially.

**Neighbor introductions (send_message)**
- Sent introduction messages to A, B, and C announcing `137.21.0.1/32` and asking each to share their prefixes.

**Routes installed**
- `ip route add 12.84.0.1/32 via 10.0.1.1 dev S-eth0` — A's loopback via the A link.
- `ip route add 89.248.0.1/32 via 10.0.2.2 dev S-eth1` — B's loopback via the B link.
- `ip route add 193.43.0.1/32 via 10.0.3.2 dev S-eth2` — C's loopback via the C link.
- `ip route add 206.81.0.1/32 via 10.0.3.2 dev S-eth2` — D's loopback via customer C (selected over the alternative paths from A and B).

**Advertisements sent**
- To A (provider): `137.21.0.1/32` and `193.43.0.1/32`, plus `206.81.0.1/32` (path [S,C,D]).
- To B (peer): same customer-cone set (mine + C + D).
- To C (customer): full reachability — my loopback, A's loopback, B's loopback, and D — so C can default-route to me.

**Verification**
- Sourced pings from my loopback (`ping -I 137.21.0.1 …`) to 12.84.0.1, 89.248.0.1, 193.43.0.1, and 206.81.0.1. All four succeeded.

## 2. Justification

- **Loopback discovery & advertisement**: needed a stable identity to make end-to-end reachable; this is the only address I advertise (point-to-point /30s are private).
- **Customer-preferred best path for D (206.81.0.1)**: three paths were offered — [A,D], [B,D], [C,D]. Standard BGP-style preference is **Customer > Peer > Provider** because traffic carried for a customer earns revenue, traffic via a peer is free, and traffic via a provider costs money. So I installed the route via C.
- **Selective re-advertisement (export policy)**:
  - To **provider A** and **peer B**: only my own loopback and my customer cone (C, D). Re-advertising A's or B's routes to each other (or back to A) would constitute providing transit to a provider/peer — forbidden by policy and a money loser.
  - To **customer C**: the full table, because C pays me for transit and expects reachability to the rest of the network.
- **No daemons used**: all routing changes done via `ip route add` and policy/state exchanged via `send_message`, as required.
- **No link subnets advertised**: only loopbacks shared, per the rule on private p2p infrastructure.

## 3. What I Discovered About the Network

- **Direct neighbors and their roles**: A = provider (AS A, loopback 12.84.0.1/32), B = peer (loopback 89.248.0.1/32), C = customer (loopback 193.43.0.1/32).
- **One indirect AS**: D, with loopback 206.81.0.1/32, sits behind C (as C's customer). D is also reachable via A and via B, suggesting D is multi-homed or that A/B have their own paths to D — but for my decision only the relationship class of the next-hop mattered.
- **Latencies observed** (from loopback): A ~20 ms, B ~20 ms, C ~30 ms, D via C ~65 ms. Reasonable values, no anomalies.
- **No bogus mass-advertisements were received** — each neighbor sent only a couple of prefixes, all consistent with their declared roles, so no anomaly investigation was required.

## 4. Coordination With Other Agents

- **A (provider)**: exchanged loopbacks and prefix lists. A advertised `12.84.0.1/32` and `206.81.0.1/32 [A,D]`. I advertised back my customer cone (S, C, D) so A can reach my customers — but I did NOT accept A's transit for D since I had a customer path.
- **B (peer)**: exchanged loopbacks and customer-cone prefixes only. B confirmed installing my routes and advertised its own loopback plus `206.81.0.1/32 [B,D]`. I advertised my customer cone back. Neither side provides transit to the other.
- **C (customer)**: C advertised its loopback and `206.81.0.1/32 [C,D]`. I committed to carrying full transit for C and told C it can use 10.0.3.1 as default next-hop. I sent C a list of currently reachable destinations.
- All non-adjacent communication would have used neighbor relaying (per the relay protocol), but in this experiment all relevant peers were direct neighbors so no relaying was required.

Final state: 4 installed `/32` routes via the correct next-hops, policy-compliant exports to each neighbor class, end-to-end reachability verified from my loopback, and revenue-maximizing path selection (D routed through paying customer C).