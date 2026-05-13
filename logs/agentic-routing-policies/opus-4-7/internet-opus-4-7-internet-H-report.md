# H Stub AS Experiment Report

## 1. Actions Taken

1. **Inspected local state**: ran `ip addr show` and `ip route show`. Discovered:
   - Loopback prefix: `10.255.8.1/32` (my AS prefix)
   - Interface H-eth0: `10.1.3.1/30`, peer at `10.1.3.2` (provider B)
   - No routes installed initially.

2. **Installed default route to provider**:
   - First attempt: `ip route add default via 10.1.3.2` → failed ("invalid gateway") because the /30 connected subnet was not yet present in the kernel routing table.
   - Workaround: `ip route add 10.1.3.2/32 dev H-eth0` (link-scope route to peer), then `ip route add default via 10.1.3.2`. Succeeded.

3. **Coordinated with B**:
   - Sent: my prefix `10.255.8.1/32`, no customers, default installed.
   - Received from B: B's prefix `10.255.2.1/32` and the list of /32 loopbacks of all other ASes (A, C–O), confirming default-via-B is sufficient.

4. **Verified reachability** with `ping` and `traceroute` to each advertised /32. Retried periodically as the network converged.

5. **Reported status** when state stabilized (only B and I reachable, others timing out at B).

## 2. Justification

- **Default route only**: As a stub with a single upstream, a default via B is the minimal correct configuration. No need to install 13 specific /32s when one default covers them.
- **Peer /32 link route**: Needed to satisfy the kernel's nexthop reachability check before the connected /30 was usable; a clean way to bootstrap without re-adding the interface address.
- **Advertise only my own prefix**: Per stub-AS rules — never re-export learned routes. I told B exactly one prefix: `10.255.8.1/32`.
- **Patience on failed pings**: Per the convergence note, transient failure ≠ wrong config. I waited and retried rather than reconfiguring.
- **Reported `success=false`**: Goal was full reachability; only 2 of 15 ASes reachable. Configuration on my side is complete and correct, but the goal as stated was not met.

## 3. Network Discoveries

- Topology from my view: single uplink H ↔ B over `10.1.3.0/30`.
- Address plan: each AS has a `/32` loopback under `10.255.X.1/32` where X correlates with the AS letter (A=1, B=2, …, O=15).
- 15 ASes total (A through O).
- Initial ARP/forwarding to B took ~30–60 seconds to come up (peer interface and/or qdisc/netem delays).
- After link came up: only B (10.255.2.1) and I (10.255.9.1) became reachable. Traceroute to other prefixes showed packets reaching B (`10.1.3.2`) and then dying — i.e., B's transit paths to the rest of the network had not converged within the observation window. This is outside a stub's control.

## 4. Coordination With Other Agents

Only with B (my provider):
- B announced itself, gave next-hop `10.1.3.2`, requested my advertisement.
- I replied with my prefix `10.255.8.1/32` and confirmed default installed.
- B helped diagnose the early ARP failure (suggested adding the connected /30 route, which I had effectively done via the peer /32).
- B sent two table updates listing reachable /32s (first 13 entries with "L pending", then 14 including L=10.255.12.1).
- I sent two follow-ups reporting that only I was reachable despite B's advertisements, asking B to verify its own forwarding to the unreachable prefixes. No further responses received before stopping.

No contact with any other AS — appropriate, since as a stub I only speak to my provider.