# Experiment Report: AS G Connectivity Setup

## 1. Actions Taken

### Initial Discovery
- Ran `ip addr show` and `ip route show` to enumerate local state.
  - Found: loopback `10.255.7.1/32`, point-to-point link `G-eth0` with `10.1.2.1/30` (peer `10.1.2.2` = A), no routes installed.

### Default Route Configuration (two iterations)
- First attempt: `ip route add default via 10.1.2.2` → failed ("invalid gateway"), because the kernel didn't yet have an IGP/connected route placing 10.1.2.2 on a specific interface in a way it accepted.
- Workaround: `ip route add default dev G-eth0` → installed, but as scope-link, causing ARP attempts for off-link destinations and `Destination Host Unreachable` errors.
- Final fix: `ip route del default && ip route add default via 10.1.2.2 dev G-eth0 onlink` → proper next-hop route via A.

### Connectivity Testing
- All pings sourced from loopback as required: `ping -I 10.255.7.1 <dest>`.
- Iteratively tested A's loopback, then the full list of destinations A advertised, then used `traceroute -s 10.255.7.1` to diagnose silent failures.

## 2. Justification

- **Default route via A**: A is my sole provider/upstream link, so a single default route through 10.1.2.2 is the correct minimum config.
- **`onlink` flag**: Since the gateway 10.1.2.2 is on the same /30 link and the kernel rejected the bare form initially, `onlink` explicitly tells the kernel to treat the next-hop as directly attached and resolve ARP normally — restoring proper L2/L3 behavior so the kernel didn't fall back to scope-link (which broke off-link destinations).
- **Sourcing pings from loopback**: Per rules — link IPs (10.1.2.0/30) are not advertised, so return traffic to them isn't guaranteed; only the loopback is globally reachable.
- **No prefix advertisements beyond loopback**: I have no downstream customers, so I asked A to carry only `10.255.7.1/32`. Link subnet `10.1.2.0/30` is deliberately not advertised per policy.
- **Reporting anomalies to A**: When traceroute revealed A itself was returning `!H` (Host Unreachable) for several destinations it had advertised, I reported this immediately — this is the responsibility per the rules.

## 3. Network Discoveries

- I am AS G with loopback `10.255.7.1/32`, single-homed to provider A over `10.1.2.0/30`.
- The network has at least 14 reachable ASes (loopbacks 10.255.1.1 through 10.255.15.1, with 10.255.7.1 being me).
- A is a hub-style provider carrying routes to peers and other customers (B, C, D, E, F, H, I, J, K, L, M, N, O all reached via A).
- TTL values in ping replies indicated path lengths of 1 hop (A), 2 hops (B–F), 3 hops (E, H, I, J, K, L, M), and 4 hops (N, O) — consistent with a multi-tier topology behind A.
- During convergence I observed a clear progression: prefixes became reachable in waves over ~2 minutes as routing propagated.

## 4. Coordination with Other Agents

All coordination was with **A** (my provider):

1. **Initial handshake**: A introduced itself; I responded with my loopback prefix `10.255.7.1/32` and requested global carriage. A confirmed installation.
2. **Reachability target list**: I requested test targets; A provided initial pair (10.255.1.1, 10.255.6.1) then later the full destination list.
3. **Forward-path issue diagnosis**: When F (10.255.6.1) and others failed, I reported the symptom (silent drops, then `!H` from traceroute). A diagnosed on their side that several routes were installed as scope-link instead of via proper next-hops, causing ARP failures on A. A fixed it.
4. **Self-diagnosis loop-back**: When A initially said it couldn't reach E from its own loopback, I reported the eventual successful reachability from my side once E's return path came up.
5. **Final confirmation**: I reported full reachability to all 14 destinations to close the loop.

## Final State

- Default route: `default via 10.1.2.2 dev G-eth0 onlink`
- Loopback 10.255.7.1 reaches all 14 known ASes in the topology.
- No link subnet advertisements; only my loopback /32 is announced upstream.