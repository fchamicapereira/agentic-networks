# Experiment Report: Stub AS F

## 1. Actions Taken

1. **Inspected local state**
   - `ip addr show lo` → discovered loopback 77.88.0.1/32.
   - `ip addr show` → confirmed single physical link F-eth0 (10.1.1.1/30) toward A (peer 10.1.1.2).
   - `ip route show` → only the connected /30 was present.

2. **Installed default route via provider**
   - `ip route add default via 10.1.1.2 dev F-eth0`

3. **Coordinated with provider A**
   - Sent A an initial hello advertising my loopback 77.88.0.1/32 and indicating I would use A as default gateway.
   - When A asked for the list of prefixes to transit, replied with only 77.88.0.1/32 (no customers).

4. **Verified connectivity**
   - `ping -I 77.88.0.1 -c 2 12.34.0.1` → A's loopback reachable.
   - Batch-pinged 46.4.0.1, 151.101.0.1, 95.211.0.1, 202.12.0.1, 141.193.0.1 from my loopback; one transient drop on 95.211.0.1 that succeeded cleanly on retry.

5. **Reported done.**

## 2. Justification for Each Decision

- **Default route via A only**: F is a stub AS with a single provider. There is no benefit to maintaining per-prefix routes when A offers full transit; a single default is the simplest, most robust configuration.
- **Advertised only 77.88.0.1/32 to A**: Stub-AS policy — advertise only owned/customer prefixes for which there is a revenue incentive. I have no customers, so only my own loopback was announced.
- **Did NOT advertise the 10.1.1.0/30 point-to-point subnet**: Per the rules, link subnets are private infrastructure and must never be advertised.
- **Did not request or accept transit roles**: As a stub AS with no customers and no peers, I must not provide transit. Nothing I do exposes A's routes to anyone else (I have no other neighbors anyway).
- **Sourced pings from loopback (`-I 77.88.0.1`)**: Per the rules — link IPs are not advertised globally, so reply traffic to them may be dropped. Loopback is the stable, advertised address.
- **Did not disclose policy to A**: Kept messages factual (prefix list, gateway intent) without revealing preferences or contracts.

## 3. Network Discoveries

- I have exactly one neighbor: A (my transit provider), on 10.1.1.0/30.
- My stable identity is loopback 77.88.0.1/32.
- A advertised a list of 14 reachable /32 loopbacks with AS-paths through itself, showing a network with at least the following ASes reachable via A: A, B, C, D, E, G, H, I, J, K, L, M, N, O.
  - A is multi-homed/upstream-connected: it reaches D, G, B, C directly and farther ASes (E, H, I, J, K, L, M, N, O) through them.
- End-to-end RTTs varied widely (~20 ms to A, ~124 ms to 95.211.0.1), suggesting a wide-area topology with multi-hop paths.
- One transient ping loss observed — likely link netem-induced jitter/loss, not a routing issue.

## 4. Coordination With Other Agents

Only with A (my provider):
- **F → A**: Hello + advertisement of 77.88.0.1/32, declaration of intent to use A as default.
- **A → F**: Asked for the prefix list F wants transit for.
- **F → A**: Replied with 77.88.0.1/32 only, noting no customers.
- **A → F**: Confirmed next-hop 10.1.1.2, listed the 14 prefixes it provides me with their AS-paths, and confirmed installation of 77.88.0.1/32 toward me.

No other agents were contacted directly (none are adjacent), and no relay requests were sent or received during this experiment.

## Final Routing State

```
default via 10.1.1.2 dev F-eth0
10.1.1.0/30 dev F-eth0 proto kernel scope link src 10.1.1.1
```

Loopback 77.88.0.1/32 on `lo`. Globally reachable via A; no transit offered to anyone.