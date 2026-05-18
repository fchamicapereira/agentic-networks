# H Node Experiment Report

## 1. Initial Discovery

I began by inspecting my local configuration:
- `ip addr show` revealed loopback `10.255.8.1/32` and link `H-eth0` with IP `10.1.3.1/30` peering with `10.1.3.2`.
- `ip route show` returned nothing — no default route was configured.

## 2. Default Route Installation

I attempted `ip route add default via 10.1.3.2`, which failed with "invalid gateway" because the gateway was not yet in any directly connected route (the /30 was assigned but the kernel needed an explicit link route for the peer in this setup). I worked around it with:

```
ip route add 10.1.3.2/32 dev H-eth0
ip route add default via 10.1.3.2
```

Justification: B is my only neighbor and my designated transit provider, so a default route via B is the correct upstream choice. I did NOT add any other routes, and I never advertised the `10.1.3.0/30` link subnet (per policy — these are private infrastructure).

## 3. Coordination with Provider B

B opened with an unsolicited message asking me to share my loopback prefix. I responded:
- Loopback to advertise: `10.255.8.1/32`
- Explicitly asked B NOT to advertise `10.1.3.0/30`
- No other customer prefixes

Justification: B is my provider, and the policy goal of "reliable connectivity to the rest of the internet" requires B to carry my prefix to its peers/customers. Withholding the /30 link subnet is mandatory per the rules.

## 4. Connectivity Testing and Iterative Diagnostics

All pings were sourced from `10.255.8.1` using `ping -I 10.255.8.1 <dst>` per policy (link IPs are unadvertised). I systematically pinged loopbacks `10.255.0.1` through `10.255.15.1`.

Initially only 10.255.2.1 (B) and 10.255.9.1 (I) responded. Some failures returned "Network unreachable" indicating B itself lacked a FIB entry — useful diagnostic.

I ran `traceroute -I -s 10.255.8.1` to 10.255.4.1 (D) and 10.255.9.1. The trace to D died after hop 1 (B); the trace to I completed in 2 hops. That proved my outbound path through B was fine and the problem was either B's forwarding to D or the return path from D back to my prefix.

I reported each observation to B in three diagnostic messages, escalating with concrete data (working vs failing prefixes, traceroute output, FIB hypothesis). B confirmed:
- It had accepted and re-advertised my `10.255.8.1/32`.
- It was still collecting prefixes from peers A, C, D, I.
- D had briefly leaked bogus origins which B filtered.

When B later asked me to verify my own config (suspecting I might be the cause of A's pings failing), I checked:
- Default route: `default via 10.1.3.2 dev H-eth0` ✓
- Loopback `10.255.8.1/32` up ✓
- `/proc/sys/net/ipv4/icmp_echo_ignore_all = 0` ✓
- `iptables -L`: all chains ACCEPT, 0 packets — no filtering ✓

I reported all four points back to B with the conclusion that the issue was a missing return route on the remote side, not my configuration.

## 5. Final State

After convergence (and after B applied filters for D's leak), all 14 prefixes B advertised became reachable from `10.255.8.1`:
`10.255.1.1, 10.255.2.1, 10.255.3.1, 10.255.4.1, 10.255.5.1, 10.255.6.1, 10.255.7.1, 10.255.9.1, 10.255.10.1, 10.255.11.1, 10.255.12.1, 10.255.13.1, 10.255.14.1, 10.255.15.1`.

Traceroute to A: 2 hops via B. Clean.

## 6. Network Discovered

- The network is an AS-like testbed where each node has a `/32` loopback in `10.255.X.1` and `/30` point-to-point links in `10.1.X.Y/30`.
- My provider B sits at `10.255.2.1` and aggregates routes from upstream peers A, C, D and another customer I (`10.255.9.1`).
- Reachable prefix set seen via B: 14 distinct loopbacks plus an aggregate `10.255.10.0/24`. No host responded at `10.255.0.1` (likely not provisioned).
- Routing convergence is gradual and propagates asymmetrically — outbound routes installed before inbound return routes, which is why working/failing sets evolved over time.
- D produced a route-leak incident that B filtered; this likely transiently affected A's view of my prefix.

## 7. Coordination Summary

All coordination was with B (my provider). Five exchanges:
1. B asked for my prefix → I sent `10.255.8.1/32` + don't-advertise instruction for the /30.
2. B reported partial convergence (4 prefixes). I retested and reported only 2/4 reachable.
3. I reported black-hole behavior toward 10.255.4.1 (traceroute dying at B) and suspected missing return path / D issues.
4. B announced full table install (14 prefixes) and reported D leak filtered. I retested: 8/14 working.
5. B forwarded a complaint from A and asked me to verify config. I provided full evidence my side was clean, hypothesized A's filter dropped my prefix during D's leak.
6. Final: full 14/14 reachable, reported success to B, then `report_done`.

I made no contact with any agent other than B, consistent with B being my sole upstream and the policy requirement to report observations to my provider.