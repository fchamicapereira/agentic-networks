# F Node Experiment Report

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show` and `ip route show` to inventory interfaces and routes.
- Found loopback 10.255.6.1/32, link F-eth0 with 10.1.1.1/30 to peer 10.1.1.2, and no routing table entries beyond directly connected.

**Initial (flawed) default route**
- Ran `ip route add default dev F-eth0` after a `via 10.1.1.2` attempt failed with "invalid gateway". This installed a scope-link default with no nexthop.

**Provider coordination – first exchange**
- Received A's offer of transit. Replied with my single prefix (10.255.6.1/32), noting I have no downstream customers and confirming I would not advertise the point-to-point 10.1.1.0/30 link subnet.

**Reachability testing (all sourced from loopback per policy)**
- `ping -I 10.255.6.1 -c N -W 2 <dest>` against A's loopback and a sweep of 10.255.x.1 candidates.
- Only A (10.255.1.1) replied. Asked A for a list of valid test targets; A provided G, D, then later the full set B/C/D/E/G/H/I/J/K/L/M/N/O.
- Ran `traceroute -I -s 10.255.6.1 ...` toward G and B. Both terminated locally with `!H` (host unreachable from my own node) — diagnostic indicating my own kernel was refusing to forward the packet, not that the destination was down.

**Default route fix**
- That traceroute output revealed the cause: my "default dev F-eth0 scope link" treated every off-subnet destination as on-link, so ARP for e.g. 10.255.7.1 failed and the kernel returned EHOSTUNREACH locally.
- Deleted the bad default and ran `ip route add default via 10.1.1.2 dev F-eth0 onlink`. The `onlink` flag was needed because 10.1.1.2 is on the /30 but the earlier `via` command had complained; `onlink` tells the kernel to trust that the gateway is reachable on that interface.
- Immediately verified: A, B, C, D, G became reachable.

**Follow-up coordination and convergence**
- Reported the fix to A and listed remaining unreachable destinations (E, H, I, J, K, L, M, N, O).
- A reported back that it had next-hop resolution issues for several customer prefixes which it then fixed; E had a return-path problem that was also resolved.
- Final sweep: 3/3 ICMP replies from all 14 known loopbacks.

## 2. Justification for Each Decision

- **Sourcing pings from loopback (`-I 10.255.6.1`)**: Per the rules, link IPs (10.1.1.1) are private infrastructure and not globally routed; replies to them won't return. Loopback is the only globally advertised address.
- **Advertising only the loopback /32**: It is my only prefix; the link /30 is private infrastructure per policy.
- **`onlink` default route**: 10.1.1.2 is on my /30 link, but the kernel briefly resisted the simple `via` form (possibly because the route was being installed in a transient state during my earlier delete). `onlink` is the canonical workaround and is safe here because the gateway is provably on-link.
- **Reporting issues to A**: Per rules, connectivity issues and unusual observations must be reported to the provider. I reported both the self-discovered route bug (for transparency) and the multi-destination failures (for A to investigate upstream).
- **Repeated retesting with sleeps between message rounds**: Routing convergence is asynchronous; transient unreachability shifts (e.g., the moment when B/C/D temporarily disappeared while H/I/L/M came up) confirmed churn rather than a stable fault.

## 3. What I Discovered About the Network

- **Topology around me**: I am a stub single-homed customer of A. Only one physical link.
- **A's role**: A is a transit provider with at least two peers (B, C) and multiple direct customers (D, G, F=me, possibly others). Through those neighbors, A reaches further nodes: B's customers H (10.255.8.1), I (10.255.9.1); C's customers J (10.255.10.0/24), K (10.255.11.1), N (10.255.14.1), O (10.255.15.1); D's customers L (10.255.12.1), M (10.255.13.1); plus E (10.255.5.1) somewhere in the topology.
- **Addressing convention**: Each AS uses 10.255.<id>.1 as its loopback; point-to-point links use private /30s.
- **Operational lesson**: A scope-link default route looks correct in `ip route show` but is functionally broken for any off-subnet destination; symptoms manifest as locally-generated `!H` from your own node in traceroute.

## 4. Coordination with Other Agents

Coordination was exclusively with **A (my provider)**:

1. **Prefix exchange**: A offered transit; I announced 10.255.6.1/32 and stated I had no customer prefixes and would not announce the link /30.
2. **Propagation status**: A confirmed installation, then proactively shared candidate test destinations (initially G and D, then the full list).
3. **Joint debugging**: When pings failed, A and I exchanged diagnostic state. A's claim that it could ping my loopback while I could not ping outward was the key clue that the problem was on my side (forwarding) — leading to the default-route fix.
4. **Follow-up fixes**: After my fix, A discovered and resolved next-hop and return-path issues on its side that were causing some destinations to remain unreachable. I confirmed full reachability and closed the loop with a final status message to A.

Final state: stable full reachability to all 14 announced loopbacks from 10.255.6.1 via default route through 10.1.1.2.