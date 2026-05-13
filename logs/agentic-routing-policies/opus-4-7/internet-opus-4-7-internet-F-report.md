# Experiment Report: AS F (Stub)

## 1. Actions Taken

1. **Inventoried local state**: Ran `ip addr show` and `ip route show` to discover my interfaces. Found:
   - Loopback prefix: 10.255.6.1/32
   - F-eth0: 10.1.1.1/30, peer at 10.1.1.2 (A)
   - No initial routes installed.

2. **Installed routing**: 
   - `ip route add 10.1.1.2/32 dev F-eth0` (link-scope route to next hop)
   - `ip route add default via 10.1.1.2` (default route through provider A)

3. **Coordinated with A**: Sent my prefix (10.255.6.1/32) and confirmed I had no customers.

4. **Verified data plane connectivity**: Tested with `ping -c 1 -W 2 <dst>` to each advertised AS prefix. Initially most failed.

5. **Diagnosed reachability gap**: Ran `traceroute` and saw packets stopped at hop 1 (A). After A's hint, retested with `ping -I 10.255.6.1 <dst>` — all 15 other ASes responded with 0% loss.

## 2. Justifications

- **Adding `10.1.1.2/32 dev F-eth0` first**: The initial `ip route add default via 10.1.1.2` failed with "Nexthop has invalid gateway" because the kernel hadn't yet auto-installed the connected subnet route (or it was momentarily missing). An explicit link-scoped host route to the peer resolved the gateway, after which the default route installed cleanly.
- **Single default route via A**: As a stub AS with one upstream, a default route is the simplest correct configuration — no need for per-prefix entries from A.
- **Advertising only 10.255.6.1/32 to A**: Per stub AS rules, I must never re-export A's routes. Only my own prefix is announced.
- **Sourcing pings from loopback**: The /30 transit link (10.1.1.0/30) is not globally advertised, so packets sourced from 10.1.1.1 had no return path. Using `-I 10.255.6.1` forces the source to my globally-advertised loopback, which all other ASes have routes for.

## 3. Network Discoveries

- The network has at least 15 ASes: A, B, C, D, E, F, G, H, I, J, K, L, M, N, O — each with a /32 loopback in 10.255.X.1/32 (X = AS index).
- A is my sole transit provider and reaches the full table.
- A's directly connected neighbors (per its message) include B, C, D, G — these are propagating my prefix further.
- Transit /30 subnets are not globally routable; only loopback /32s are advertised inter-AS. This is standard practice — saves table size and avoids leaking infrastructure addressing.
- Convergence happened in waves: A reachable immediately, G shortly after, then the rest once I corrected my source address (they were actually reachable all along — my probe technique was wrong).

## 4. Coordination with Other Agents

Only with **A** (my provider):
- A initiated contact, announcing its prefix 10.255.1.1/32 and the link addressing.
- I replied with my prefix and stub status.
- A sent incremental updates of learned prefixes (three messages covering all 15 ASes including a late addition of L).
- When I reported reachability failures, A correctly diagnosed the source-address issue rather than a control-plane problem, instructing me to use `ping -I 10.255.6.1`. That single hint resolved everything.

No direct communication with non-adjacent ASes was needed or appropriate — as a stub, all my external coordination flows through my provider.

## Final State

- Default route: `default via 10.1.1.2 dev F-eth0`
- Advertised: 10.255.6.1/32 only
- Verified: 0% loss to all 15 other ASes when sourced from loopback.