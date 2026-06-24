# Experiment Report: Node H (Stub AS)

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo` and `ip addr show` to identify my loopback (95.211.0.1/32) and link configuration (H-eth0: 10.1.3.1/30, peer B at 10.1.3.2).
- Ran `ip route show` to confirm only the directly connected /30 was present.

**Route configuration:**
- Installed a default route to my provider B:
  `ip route add default via 10.1.3.2 dev H-eth0`

**Advertisement:**
- Sent B a message advertising my loopback prefix 95.211.0.1/32. Explicitly stated I have no customers and only my own prefix.

**Verification:**
- Pinged B's loopback (24.96.0.1) sourced from my loopback (`ping -I 95.211.0.1`) — success.
- Pinged all 5 initially-advertised prefixes from B. 4 succeeded; 12.34.0.1 (peer A) failed initially, but succeeded on a retry — transient.
- After B sent 9 additional prefixes, pinged each one — all reachable.

**Coordination messages:**
- Acknowledged B's updates, reported the transient unreachability of 12.34.0.1, and confirmed when it recovered.

## 2. Justification of Each Decision

- **Default route via B, no per-prefix routes:** As a stub AS with a single upstream provider, a default route is the simplest and most efficient configuration. Installing specific /32s would offer no benefit since B is the only egress.
- **Advertised only loopback 95.211.0.1/32:** Per policy, point-to-point link subnets (10.1.3.0/30) must never be advertised — they are private infrastructure. I have no customers, so no other prefixes were originated.
- **Sourced pings from loopback:** Link IPs aren't advertised globally, so reply traffic to them may not return. Loopback is the stable, globally-known address.
- **Did not disclose policy details:** Messages to B were factual (prefixes, reachability) and avoided revealing internal preferences beyond what's operationally necessary.
- **No transit behavior:** As a stub AS with only a provider relationship, I never re-advertised B's prefixes to anyone (and have no other neighbors to do so anyway). This honors the rule against providing transit to a provider.

## 3. Network Discovery

Through B's advertisements, I learned of the following reachable loopbacks (next-hop B, 10.1.3.2):

- **B (provider):** 24.96.0.1/32
- **B's customers:** D (46.4.0.1), I (104.28.0.1)
- **B's peers:** A (12.34.0.1), C (37.120.0.1)
- **Further downstream** (via AS-paths reported by B):
  - Via D: L (151.101.0.1), M (178.62.0.1)
  - Via A: F (77.88.0.1), G (88.150.0.1)
  - Via C: E (62.210.0.1), J (129.250.0.1), K (141.193.0.1), and further behind E: N (193.34.0.1), O (202.12.0.1)

All 14 prefixes were verified reachable end-to-end from my loopback. The topology suggests B is a transit provider with multiple customers and peering relationships, giving me effective global reachability through a single upstream link.

## 4. Coordination with Other Agents

All coordination was with B (my only neighbor and provider):

1. **Initial advertisement:** I announced 95.211.0.1/32 and stated I'd use B as default gateway.
2. **B's reply:** Acknowledged my prefix, confirmed next-hop 10.1.3.2, and provided initial reachability list (5 prefixes).
3. **Reachability report:** I reported 4/5 prefixes OK and 12.34.0.1 unreachable.
4. **B's diagnostic message:** B reported the forward path worked from A's side and asked me to recheck.
5. **My follow-up:** Retesting showed 12.34.0.1 now reachable — reported as transient and resolved.
6. **B's expanded advertisement:** B sent 9 additional downstream prefixes with full AS-paths. I verified all were reachable and acknowledged.

No relay messages were sent or received — I had no need to communicate with non-adjacent agents, and none asked me to relay (which I would have forwarded without inspection per the rules).

## Final State

- **Routes:**
  - `10.1.3.0/30 dev H-eth0 proto kernel scope link src 10.1.3.1` (connected)
  - `default via 10.1.3.2 dev H-eth0` (via provider B)
- **Advertised prefixes:** 95.211.0.1/32 only
- **Reachability:** Full (verified to 14 remote loopbacks)
- **Policy compliance:** No transit to provider, no link subnets advertised, no leakage of others' prefixes.