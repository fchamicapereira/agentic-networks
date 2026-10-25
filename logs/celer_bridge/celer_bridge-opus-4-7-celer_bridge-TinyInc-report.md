# TinyInc Experiment Report

## 1. Actions Taken

**Initial state inspection**
- Ran `ip addr show lo`, `ip addr show`, and `ip route show` to inventory my interfaces and routing table.

**Findings from inspection (no action needed to create these):**
- Loopback already had `45.32.0.1/32` configured.
- Point-to-point link `TinyInc-eth0` had `10.0.32.2/30` with peer `10.0.32.1` (ISP).
- A `blackhole 45.32.0.0/24` route was pre-installed (covering aggregate so I don't leak more-specifics back).
- Static routes to remote prefixes (5.62.56.0/24, 44.192.0.0/16, 85.12.64.0/22, 91.108.0.0/22, 154.54.0.0/16) all pointed via ISP (10.0.32.1).

**Prefix advertisement**
- Sent a message to ISP: "I originate 45.32.0.0/24, next-hop 10.0.32.2, please install and propagate."
- ISP acknowledged, confirming origin matched IRR data and the route was installed.

**Connectivity verification**
- Pinged 44.192.100.100 (AWS) sourced from loopback: 0% loss.
- Pinged 5.62.56.1, 85.12.64.1, 91.108.0.1, 154.54.0.1 sourced from loopback: all 0% loss.

Then went idle.

## 2. Justification

- **Inspected before changing anything** — the environment pre-configured both the loopback IP and a blackhole aggregate, so there was nothing to add. Blindly re-adding would have failed or duplicated.
- **Advertised 45.32.0.0/24 to ISP** — this is an explicit goal and the only way my prefix becomes globally reachable. ISP is my paid upstream provider, which is the correct AS to receive my origination.
- **Did not advertise the 10.0.32.0/30 link subnet** — rules forbid advertising point-to-point infrastructure prefixes.
- **Did not re-advertise any received prefixes** — I have no customers, so I should not act as transit; propagating other ASes' routes would be a route leak toward my provider.
- **Sourced all pings from the loopback (45.32.0.1)** — remote nodes have no route back to my link address 10.0.32.2, so replies would silently fail and give misleading evidence of a connectivity problem.
- **Tested multiple remote prefixes**, not just one, to confirm the upstream path reaches diverse destinations across the network.

## 3. Discoveries About the Network

- My only neighbor is ISP (my provider) over `TinyInc-eth0`.
- The network reachable through ISP includes at least the following prefixes, all alive and responsive:
  - 44.192.0.0/16 (AWS)
  - 5.62.56.0/24 (LegitAS)
  - 85.12.64.0/22 (ISP itself)
  - 91.108.0.0/22 (TransitAS)
  - 154.54.0.0/16 (Tier1)
- RTT patterns suggest topology distance: 85.12.64.1 (ISP) ~10 ms, 91.108.0.1 ~34 ms, 5.62.56.1 ~50–66 ms, 154.54.0.1 ~54 ms, 44.192.100.100 ~64 ms — consistent with ISP being one hop and the others progressively further.
- TTL values (61–64) suggest 1–3 forwarding hops away.
- Routing was pre-converged; no manual `ip route add/del` was needed on my side.

## 4. Coordination With Other Agents

- **ISP**: Sent one message announcing origination of 45.32.0.0/24 with next-hop 10.0.32.2. ISP replied confirming the origin AS matched the IRR record and that the route was installed and would be propagated upstream.

No other agent communication occurred — no relay requests were received, and no neighbors other than ISP exist.