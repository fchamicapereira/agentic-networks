# Experiment Report: AS I

## 1. Actions Taken

**Initial reconnaissance:**
- Ran `ip addr show lo` → discovered my loopback address: 104.28.0.1/32
- Ran `ip addr show` → confirmed single physical interface I-eth0 (10.1.4.1/30) toward B
- Ran `ip route show` → found ~14 specific /32 routes already pre-installed via 10.1.4.2 (B), but no default route

**Routing configuration:**
- Added a default route: `ip route add default via 10.1.4.2 dev I-eth0`
- Did not add or remove any other routes (the specifics were already present and consistent with B being my upstream).

**Advertisement:**
- Sent a message to B announcing my loopback prefix 104.28.0.1/32 and informing B I would use it as upstream.
- I deliberately did *not* advertise the 10.1.4.0/30 link subnet (per rules).

**Verification:**
- Pinged three destinations sourced from my loopback:
  - `ping -I 104.28.0.1 24.96.0.1` (B) → 0% loss, ~12 ms
  - `ping -I 104.28.0.1 95.211.0.1` (H via B) → 0% loss, ~36 ms
  - `ping -I 104.28.0.1 151.101.0.1` (peer A side) → 0% loss, ~198 ms

**Final advertisement from B:**
- B then sent its full table (14 prefixes with AS-paths). All prefixes were already covered by my default route and by the pre-existing specifics. I took no further action, as the update was consistent with B's role as my transit provider and the volume was modest.

## 2. Justification

- **Default route via B**: As a single-homed customer with only one neighbor (my paid transit), the simplest correct configuration is a default route pointing to that provider.
- **Advertising only the loopback**: My loopback is my stable, routable identity. The point-to-point link 10.1.4.0/30 is private infrastructure and must not be advertised per the rules.
- **Sourcing pings from loopback**: Link IPs are unadvertised; replies might not return. Using the loopback ensures end-to-end reachability validation.
- **Accepting B's full table without alarm**: 14 prefixes from a transit provider is a reasonable volume, and the AS-paths (B-rooted, with sensible transit/peer structure) look legitimate. No anomaly worth reporting.

## 3. Network Discoveries

- I am single-homed to provider B over 10.1.4.0/30.
- B reaches the broader network through:
  - A peer **A** (carrying F, G, L?, M? indirectly; routes 12.34, 77.88, 88.150)
  - Customers/peers **C**, **D**, **H** (95.211 via H; 37.120/62.210/129.250/141.193/193.34/202.12 via C; 46.4/151.101/178.62 via D)
- AS-paths revealed transit hierarchy: e.g., B→C→E→... and B→D→L/M.
- End-to-end latencies grew with AS-path length (12 ms to B, 36 ms one hop further, ~200 ms across multi-AS paths), consistent with the topology.

## 4. Coordination with Other Agents

Only B (my sole neighbor):
- **I → B**: Announced 104.28.0.1/32 and declared B as upstream.
- **B → I**: Acknowledged receipt, confirmed propagation to peers/customers, then later sent a full-table advertisement (14 prefixes with AS-paths and next-hop 10.1.4.2).

No relay traffic for other agents was requested through me during the experiment.