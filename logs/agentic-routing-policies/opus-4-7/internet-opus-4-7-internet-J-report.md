# J Stub AS Experiment Report

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show` and `ip route show` to inspect interfaces. Found:
  - J-eth0: 10.1.5.1/30, peer 10.1.5.2 (C)
  - Loopback: 10.255.10.1/32 → my originated prefix

**Routing configuration:**
- `ip route add 10.1.5.2/32 dev J-eth0` — added explicit link-scope route to peer (needed because /30 onlink wasn't auto-installed; first attempt at default route failed with "invalid gateway").
- `ip route add default via 10.1.5.2` — installed default route through provider C.

**Verification loop:**
- Pinged peer link IP 10.1.5.2 (succeeded after brief ARP delay).
- Pinged 10.255.3.1 (C's loopback) — success.
- Pinged each of A–O loopbacks (10.255.1.1 through 10.255.15.1) in batches with retries after waiting.
- Used `traceroute -n` to localize where unreachable traffic was dropped — packets died at C (10.1.5.2) for unreachable destinations.

## 2. Justifications

- **Default route via C only**: As a stub AS with a single upstream, no need for per-prefix routes; default suffices and matches the rule "Accept all routes from C."
- **Originate only 10.255.10.1/32**: Required by stub rules — never re-export learned routes.
- **Explicit /32 to peer**: The kernel rejected the gateway as not directly reachable; adding the peer's address as link-scoped route solved this.
- **Patience with retries**: Per the convergence rules, failed pings early in the experiment aren't proof of misconfiguration. I repeatedly waited and re-probed.
- **Escalated to C**: After repeated waits with no convergence improvement, asked C to verify its routes — as a stub I cannot influence transit decisions.

## 3. Network Discoveries

- Topology: I'm a single-homed stub off C.
- 15 ASes exist (A–O), each owning a 10.255.X.1/32 loopback.
- C is the apparent hub providing transit; its prefix table covered all known ASes.
- Reachable end-state from J: C, E, K, N, O (5 ASes).
- Unreachable from J: A, B, D, F, G, H, I, L, M (9 ASes). Traceroute showed packets to these ASes were dropped at C — indicating C lacked working forwarding entries to those destinations, despite advertising knowledge of them.
- Forward path from me to C worked; reverse path from C to many ASes did not — convergence/install failure upstream of me.

## 4. Coordination With Other Agents

- **C** (provider): 
  - C initiated contact requesting my prefix and offering full routes.
  - I responded with my prefix (10.255.10.1/32) and confirmed default-route installation.
  - C provided a full list of known ASes and confirmed default-via-C was sufficient.
  - I reported reachability gaps (A,B,D,F,G,H,I,L,M) and asked C to verify. C acknowledged routes installed and attributed early failures to peer-side convergence; later messages got no reply.
- No other agents contacted directly — appropriate for a stub AS that talks only to its provider.

## Final State

Local config correct and minimal per stub rules. Partial connectivity (5/14 remote ASes). Remaining unreachability is rooted at provider C's forwarding plane or further-upstream peers — outside the scope of what J can correct.