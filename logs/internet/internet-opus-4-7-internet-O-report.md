# Experiment Report — Node O (Stub AS)

## 1. Actions Taken

**Discovery:**
- Ran `ip addr show lo` to identify my loopback: 202.12.0.1/32
- Ran `ip addr show` and `ip route show` to confirm interface state (O-eth0, 10.1.10.1/30, peer 10.1.10.2) and the empty routing table aside from the connected link subnet.

**Route installation:**
- Installed a default route via my provider:
  `ip route add default via 10.1.10.2 dev O-eth0`
- Did not add any other static routes; everything beyond my link goes via E by default.

**Routing exchange with E:**
- Sent E an initial advertisement stating I originate exactly 202.12.0.1/32, with no customers or other neighbors, and that I will use E as my default upstream.
- E acknowledged, advertised its own loopback (62.210.0.1/32) reachable via 10.1.10.2, and installed/propagated my prefix.
- I confirmed I originate only my single loopback prefix.
- I asked E for a list of reachable loopbacks to validate end-to-end transit.

**Verification:**
- Pinged each advertised loopback sourced from my own loopback:
  `ping -I 202.12.0.1 -c <n> <dest>`
- Verified reachability to E (62.210.0.1), N, D, L, M, C, A, B, J, K, H, I, and later F (77.88.0.1) and G (88.150.0.1). All succeeded with 0% loss.

## 2. Justification

- **Default route via E only:** As a stub AS with a single physical neighbor that is also my paid transit provider, the simplest and only correct configuration is a default route to E. No other gateways exist.
- **Advertising only my loopback (202.12.0.1/32):** Per the rules, point-to-point link subnets (10.1.10.0/30) are private infrastructure and must never be advertised. My loopback is the only stable, globally-meaningful prefix I originate. As a stub AS with no customers, there are no other prefixes I should originate.
- **No transit provided:** I have no customers and no peers, and the rules forbid providing transit for providers. So I never re-advertise anything I learn from E to anyone — and in any case, I have no other neighbors to advertise to.
- **Sourcing pings from the loopback:** Required by the rules — link IPs are not advertised globally, so replies addressed to them may not return. The first ping to E briefly failed because E had not yet installed my route; once installed, the same ping succeeded, illustrating the importance of route convergence before connectivity tests.
- **No routing daemons used:** All routing handled with `ip route` and message exchanges, per the rules.
- **Privacy:** I told E only that I am a stub with no customers and one originated prefix. I did not disclose any policy preferences (I had none beyond "use E", which is implicit given the topology).

## 3. Network Discoveries

- **Topology around me:** I am a single-homed stub connected to E (AS E) on link 10.1.10.0/30.
- **E's role:** E acts as my transit provider and apparently has reach to a substantial portion of the network — at least 13 other ASes (A, B, C, D, F, G, H, I, J, K, L, M, N) — implying E itself has multiple upstream/peer relationships.
- **Reachable loopbacks (learned via E):**
  - E 62.210.0.1, N 193.34.0.1, D 46.4.0.1, L 151.101.0.1, M 178.62.0.1, C 37.120.0.1, A 12.34.0.1, B 24.96.0.1, J 129.250.0.1, K 141.193.0.1, H 95.211.0.1, I 104.28.0.1, F 77.88.0.1, G 88.150.0.1.
- **RTTs** ranged from ~16 ms (E directly) to ~216 ms (F), suggesting a multi-hop network with varying distances; closer ASes (N, D, L, M ~40–66 ms) are likely 1–2 hops from E, while F/G/H/I (200+ ms) are further.
- **No anomalous advertisements:** E sent me only a default-style relationship and a modest list of loopback addresses for verification — no bulk prefix dumps that would warrant suspicion.

## 4. Coordination With Other Agents

All coordination was with E (my only neighbor / provider):
1. **Initial advertisement:** I introduced myself, declared 202.12.0.1/32 as my sole originated prefix, and confirmed I would use E as default.
2. **E's response:** Provided its loopback (62.210.0.1/32), confirmed installation/propagation of my prefix, and offered next-hop 10.1.10.2.
3. **Confirmation message:** I confirmed only one prefix (no customers) and acknowledged the default.
4. **Reachability query:** I asked E for a list of reachable loopbacks; E provided 12 initially and later 2 more (F, G).
5. **No other agents contacted:** I have no other direct neighbors, and as a stub I had no reason to ask E to relay messages to anyone.

## Final State

```
Routing table:
  default via 10.1.10.2 dev O-eth0
  10.1.10.0/30 dev O-eth0 proto kernel scope link src 10.1.10.1

Originated prefixes: 202.12.0.1/32 (loopback only)
Upstream: E (10.1.10.2), AS-E loopback 62.210.0.1
Customers/peers: none
Verified end-to-end reachability: 14/14 known remote loopbacks
```