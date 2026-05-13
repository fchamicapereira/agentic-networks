# Experiment Report: AS M (Stub)

## 1. Actions Taken

1. Inspected local config with `ip addr show` / `ip route show`. Found:
   - Loopback /32: 10.255.13.1
   - Single interface M-eth0: 10.1.8.1/30 toward D (peer 10.1.8.2)
   - No routes installed initially

2. Attempted `ip route add default via 10.1.8.2` — failed because the peer /30 was not yet recognized as on-link (kernel saw no route to 10.1.8.2). Worked around it with:
   - `ip route add 10.1.8.2/32 dev M-eth0`
   - `ip route add default via 10.1.8.2 dev M-eth0`

3. Messaged D announcing my prefix (10.255.13.1/32) and that I have no customers. D acknowledged and said it would propagate to A, B, E.

4. Verified link to D with `ping 10.1.8.2` — succeeded after initial ARP/convergence delay.

5. Probed all 14 advertised loopbacks (10.255.{1..15}.1, skipping .13). Only D (.4) and L (.12) initially responded; others timed out at hop 2.

6. Queried D about the partial reachability. D explained that transit /30s are not advertised globally — only loopback /32s — so the source IP of my pings (10.1.8.1) was unrouteable on the far side.

7. Re-ran pings with `ping -I 10.255.13.1 <dest>`. All 14 ASes reachable.

## 2. Justification

- **Default route via D**: As a stub with a single upstream, a default route is sufficient and minimal. No BGP daemon needed for my role.
- **Adding 10.1.8.2/32 as on-link**: Necessary workaround since the kernel rejected the default route until the next-hop was reachable. The /30 should have made it on-link automatically, but didn't in this environment.
- **Advertised only 10.255.13.1/32**: My only prefix; no customers — consistent with stub-AS rules (no transit, no re-export of D's routes).
- **Accepted D's "default is enough"**: No need for per-prefix routes; D handles all egress.
- **Sourcing from loopback**: Loopbacks are the globally advertised identifiers; transit /30s are link-local in routing terms.

## 3. Network Discoveries

- The network contains 15 ASes labeled A–O, each identified by a /32 loopback in 10.255.X.1 (X = AS index, M = 13).
- Transit links use /30 subnets (mine: 10.1.8.0/30) that are not redistributed globally.
- D is a transit provider with reachability to all other ASes (A, B, C, E, F, G, H, I, J, K, L, N, O via further hops).
- The link to D has a 10ms netem delay (RTT ≈ 20ms to D, ≈40ms transiting D).
- Convergence is not instantaneous — early pings failed, later succeeded as remote ASes installed routes.

## 4. Coordination With Other Agents

Only with D (my provider):
- **D → M**: Hello, announced it would advertise full table; asked for my prefix.
- **M → D**: Announced 10.255.13.1/32, no customers, default route installed.
- **D → M**: Acked my prefix, listed all 14 reachable AS loopbacks.
- **M → D**: Reported partial reachability (only L responding beyond D).
- **D → M**: Clarified that transit /30s are not globally advertised; instructed me to source pings from my loopback. This resolved the issue — full reachability confirmed.

No direct contact with any other AS, consistent with stub status.