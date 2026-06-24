# AS2 Experiment Report

## 1. Actions Taken

**Discovery (local state)**
- `ip addr show lo` → loopback 154.54.1.1/32
- `ip addr show` / `ip route show` → confirmed two interfaces (eth0 to AS1, eth1 to ACM), pre-existing routes to ACM's prefixes (137.54.0.1, 192.107.102.1, 198.82.0.1) and a default via AS1 (10.0.2.1).

**Routing changes**
- `ip route add 4.2.2.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1` — AS1's loopback.
- `ip route del default via 10.0.2.1 dev AS2-eth0` — removed the inappropriate default route.
- `ip route add 128.173.0.0/16 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1` — AS1 customer Uni aggregate.
- `ip route add 91.214.0.1/32 via 10.0.2.1 dev AS2-eth0 src 154.54.1.1` — AS1 customer EveLink.

**Verification pings (all 0% loss)**
- 4.2.2.1 (40 ms), 198.82.0.1 (34 ms), 128.173.0.1 (60 ms), 128.173.10.1 (64 ms), 91.214.0.1 (60 ms).

**Messages**
- Sent hello/advertisement to AS1 with my loopback + ACM customer prefixes.
- Sent hello to ACM advertising my loopback and offering transit.
- Sent a follow-up advertisement to AS1 listing ACM's three prefixes with next-hop 10.0.2.2.
- Sent an updated reachability list to ACM, clarifying I have no default upstream.

## 2. Justification

- **Advertising my loopback first**: stable end-to-end addressing needs every node to know it.
- **Installing only what neighbors advertised**: per the lab rules, routes are exchanged via messages; no routing daemon.
- **Removing the default via AS1**: AS1 is a peer (settlement-free), not a provider. Keeping a default through a peer would (a) imply they provide me transit, which they don't, and (b) cause traffic to be black-holed at AS1 for any destination outside AS1's customer cone.
- **Re-advertising ACM's prefixes to AS1 but not AS1's prefixes to AS1's neighbors**: standard valley-free routing — I announce customer routes to peers, and peer routes only to customers. This is also what AS1 explicitly asked for.
- **Telling ACM the real reachable set**: ACM was using 0.0.0.0/0 via me. Since I cannot reach the whole Internet, it would be misleading to leave them assuming full transit. I listed the prefixes that actually work so they understand the scope.
- **Volume of AS1's advertisement (5 prefixes)** was small and consistent with their expected role; no anomaly check beyond inspection was warranted.

## 3. Discoveries About the Network

- **Topology learned**: AS2 sits between AS1 (peer) and ACM (customer). AS1 has its own customers Uni (128.173.0.0/16, with downstream User 128.173.10.1) and EveLink (91.214.0.1). ACM originates 192.107.102.1, 198.82.0.1, 137.54.0.1.
- **Loopbacks**: AS1 = 4.2.2.1, AS2 = 154.54.1.1, ACM loopback = 192.107.102.1.
- **No upstream provider visible to AS2**: I am a transit ISP for ACM but have only peering with AS1, so I have no path to destinations outside the union {ACM cone ∪ AS1 cone ∪ AS1 itself}.
- **Latency profile**: ~30–40 ms one peer hop, ~60 ms two peer hops, ~64 ms three hops — consistent with the netem delay shaping on the links.

## 4. Coordination With Other Agents

- **AS1 (peer)**: Exchanged hellos, loopback addresses, and customer prefix lists. Both sides agreed explicitly on peering policy (no transit re-advertisement to other peers; only to customers). AS1 advertised 4.2.2.1/32, 128.173.0.0/16 (with 128.173.0.1, 128.173.10.1 covered), and 91.214.0.1/32 with next-hop 10.0.2.1.
- **ACM (customer)**: Exchanged hellos; ACM confirmed the three origin prefixes (192.107.102.1, 198.82.0.1, 137.54.0.1) and its default route via 10.0.3.1. I followed up with an honest reachability list so ACM understands what its default through me actually covers.
- **No KP WHY/FIX queries** were raised during this experiment — the network converged via the routing exchange alone.