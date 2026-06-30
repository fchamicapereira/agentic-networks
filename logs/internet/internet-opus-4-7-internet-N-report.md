# Experiment Report — AS N (Stub AS)

## 1. Actions Taken

1. **Inspected local state**: Ran `ip addr show lo`, `ip addr show`, and `ip route show` to discover my loopback address (193.34.0.1/32) and the single physical link to E (10.1.9.1/30, peer 10.1.9.2).

2. **Installed default route**: `ip route add default via 10.1.9.2 dev N-eth0` — pointing all outbound traffic to provider E.

3. **Advertised my prefix to E**: Sent a message to E announcing only `193.34.0.1/32` (my loopback), originated by AS N, with no customer prefixes.

4. **Verified provider reachability**: `ping -I 193.34.0.1 -c 3 62.210.0.1` succeeded.

5. **Verified global reachability**: Pinged six remote loopbacks E suggested (46.4.0.1, 151.101.0.1, 178.62.0.1, 37.120.0.1, 129.250.0.1, 202.12.0.1), sourced from my loopback. All returned 0% packet loss.

6. **Reported completion** via `report_done`.

## 2. Justification for Each Decision

- **Default route via E**: As a stub AS with a single upstream provider, a default route is the simplest and correct outbound policy — no need to learn or install specific prefixes from E.
- **Advertising only the loopback**: The point-to-point subnet 10.1.9.0/30 is private infrastructure and must never be advertised. I have no customers, so no customer prefixes to re-advertise. Advertising my loopback is required so the rest of the Internet can return traffic to me.
- **No transit provided**: As a stub, I never re-advertise prefixes learned from E (or anyone) to anyone else. I have no peers or customers, so this is trivially upheld.
- **Sourcing pings from loopback**: Link IPs (10.1.9.1) are not globally routable; replies to them would be dropped. Sourcing from 193.34.0.1 ensures return paths exist.
- **No policy disclosure**: My messages to E only stated facts needed for routing (prefix list, gateway). I did not reveal preferences or contractual details to anyone.

## 3. Network Discoveries

- I have exactly one neighbor: E (10.1.9.2), my transit provider with loopback 62.210.0.1/32.
- The network is large and multi-AS. Via E I verified reachability to at least 6 other ASes:
  - AS D (46.4.0.1), AS L (151.101.0.1), AS M (178.62.0.1), AS C (37.120.0.1), AS J (129.250.0.1), AS O (202.12.0.1).
- RTTs ranged from 24 ms (E) to 114 ms (AS J), suggesting these ASes are at varying topological distances behind E.
- TTL values (62–64) indicate paths of roughly 1–3 hops from my perspective through E's network.
- AS O was described by E as a "fellow customer" — confirming E has multiple customer ASes.

## 4. Coordination with Other Agents

Only with **E**, my direct neighbor and provider:
- I sent E my loopback prefix (193.34.0.1/32) for advertisement.
- E confirmed installing my prefix, propagating it upstream/to peers, and acknowledged my default route configuration.
- E proactively offered a list of 6 remote loopback addresses for me to test reachability, which I used to validate end-to-end global connectivity.

No messages were exchanged with any non-adjacent agent (none would have been possible without relaying through E, and none were required for my stub-AS role).

## Final Configuration

```
Routes:
  default via 10.1.9.2 dev N-eth0
  10.1.9.0/30 dev N-eth0 proto kernel scope link src 10.1.9.1

Advertised prefixes:
  193.34.0.1/32 (to E only)
```

Outcome: AS N is fully configured as a well-behaved stub AS — globally reachable, paying only E for transit, leaking no infrastructure prefixes, and providing transit to no one.