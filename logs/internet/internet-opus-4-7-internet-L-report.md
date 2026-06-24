# Experiment Report — Node L (Stub AS)

## 1. Actions Taken

1. **Inspected local state**
   - `ip addr show lo` → discovered my loopback address `151.101.0.1/32`.
   - `ip route show` → confirmed only the directly connected link `10.1.7.0/30` was present.

2. **Installed default route**
   - `ip route add default via 10.1.7.2`
   - This points all non-local traffic to my provider D over the L–D point-to-point link.

3. **Advertised my loopback to provider D**
   - Sent a message to D announcing `151.101.0.1/32` as my originated prefix.
   - After D's reply asking for my loopback IP (messages had crossed), I re-sent an explicit confirmation that `151.101.0.1/32` is the only prefix I originate and I have no customers.

4. **Verified reachability**
   - `ping -I 151.101.0.1 -c 2 46.4.0.1` → 0% loss to D's loopback, confirming end-to-end connectivity sourced from my loopback.

5. **Received a list of globally reachable prefixes from D**
   - Took no action because the existing `0.0.0.0/0` default already covers all of them — installing /32s per destination would be redundant.

6. **Reported done**, then remained idle.

## 2. Justification for Each Decision

- **Default route via D, not per-prefix routes**: As a stub AS with a single upstream, a default route is the simplest and most scalable choice. D explicitly confirmed it suffices.
- **Advertised only my loopback `/32`**: Per the rules, point-to-point link subnets (`10.1.7.0/30`) must never be advertised — they are private infrastructure. The loopback is the only prefix that gives my AS a stable, externally reachable identity.
- **No customer prefixes advertised**: I have no customers, so there is nothing else to originate.
- **Did not propagate D's prefix list**: I am a stub; providing transit to anyone (especially back to a provider) is forbidden by policy, and I have no other neighbors regardless.
- **Did not disclose policies/contracts**: My messages to D stated only the technical facts (prefix to advertise, no customers). Relationship details were not disclosed beyond what D, as my provider, inherently knows.
- **Sourced ping from loopback**: Required by the rules, and necessary because link interface IPs are not advertised globally so replies to them may not return.

## 3. Discoveries About the Network

- I have exactly one directly connected neighbor: **D** on `L-eth0` (`10.1.7.1/30` ↔ `10.1.7.2/30`).
- D's loopback is `46.4.0.1/32`.
- D acts as my transit provider and offers reachability to at least these prefixes:
  `12.34.0.1, 24.96.0.1, 37.120.0.1, 62.210.0.1, 77.88.0.1, 88.150.0.1, 95.211.0.1, 104.28.0.1, 129.250.0.1, 141.193.0.1, 178.62.0.1, 193.34.0.1, 202.12.0.1`.
- Round-trip time to D's loopback: ~16–48 ms (variable, likely simulated link).

## 4. Coordination with Other Agents

Only with my single neighbor **D** (my provider):
- **L → D**: "I advertise 151.101.0.1/32; please provide transit; no customers."
- **D → L**: Confirmed installation of my prefix, declared its own loopback `46.4.0.1/32`, instructed me to use `10.1.7.2` as next-hop / install default route, and later shared a list of globally reachable prefixes available through it.
- No relay requests were received, and I sent none — as a stub with one neighbor, there were no other agents to coordinate with.

## Final Routing State

```
default via 10.1.7.2 dev L-eth0
10.1.7.0/30 dev L-eth0 proto kernel scope link src 10.1.7.1
```

Loopback `151.101.0.1/32` originated and advertised to D. Configuration is consistent with stub-AS policy: no transit provided, only own loopback announced, all egress via paid provider D.