# Experiment Report: AS-S (Stub AS)

## 1. Actions Taken

**Initial discovery**
- Ran `ip addr show` and `ip route show` to inventory local state. Found:
  - Loopback 10.255.5.1/32 on `lo`
  - Point-to-point link to A on S-eth0: 10.1.1.1/30 (peer 10.1.1.2)
  - No routes installed beyond connected.

**Routing configuration**
- Attempted `ip route add default via 10.1.1.2` — failed with "invalid gateway" because the kernel did not yet consider 10.1.1.2 directly reachable in the routing sense.
- Added an explicit on-link route: `ip route add 10.1.1.2/32 dev S-eth0`
- Then added the default route: `ip route add default via 10.1.1.2 dev S-eth0`
- Final routing table:
  ```
  default via 10.1.1.2 dev S-eth0
  10.1.1.2 dev S-eth0 scope link
  ```

**Advertisement to A**
- Sent A a message announcing my loopback 10.255.5.1/32, stated I have no customer prefixes, and confirmed default route.
- Did **not** advertise the 10.1.1.0/30 P2P subnet (per rules — link subnets are private infrastructure).

**Connectivity verification (always sourced from loopback)**
- `ping -I 10.255.5.1 10.255.1.1` (A's loopback)
- `ping -I 10.255.5.1 10.255.2.1` (B), `10.255.4.1` (E), `10.255.3.1`

**Troubleshooting cooperation with A**
- When B/E became unreachable, ran several rounds of `ping -I 10.255.5.1 -c N <ip>`, captured exact symptoms (ICMP unreachables from 10.1.1.2 vs. silent drops), and reported them factually to A.

## 2. Justification

- **Default-only routing via A.** A is my sole provider and only neighbor; a stub AS has nothing to gain from more specific routes. A default route maximizes reachability with minimum configuration and matches my role.
- **Advertising only the loopback.** Rules forbid advertising P2P link subnets. I have no customers, so I advertise nothing else. Anything more would either leak infrastructure or imply transit I do not provide.
- **No transit offered.** I have no customers and only one provider; offering transit would violate the provider-no-transit rule and is also pointless (it would just send A's traffic back through A).
- **Sourcing pings from the loopback.** Per rules, link-IPs are not advertised and replies may not return. Loopback-sourced tests are the only meaningful data-plane signal.
- **Sharing observations, not policy.** When reporting B/E unreachability to A, I described only measured symptoms (counts, ICMP type, source of replies). I did not disclose contract or policy details, in line with privacy rules.
- **Skeptical of A's "ARP aged out" explanation.** After A claimed only the first packet would fail, I retested with `-c 5`; all 5 still failed, so I pushed back with data rather than accepting the story. This corroborated something deeper was wrong (and eventually it did resolve).

## 3. Network Observations

- **Topology learned (partial):**
  - Direct neighbor: A (AS-A, loopback 10.255.1.1/32), my provider.
  - Via A I can reach: B (10.255.2.1, ~30ms), E (10.255.4.1, ~20ms), and 10.255.3.1 (~35ms).
- **No direct view beyond A.** Consistent with being a stub AS — I never learned the topology past A and didn't need to.
- **Transient data-plane issue on A's side.** For a period, A returned ICMP Destination Unreachable for 10.255.4.1 and silently dropped traffic to 10.255.2.1. A attributed this to ARP cache aging on its upstream interfaces and later pinned ARP entries to fix it. After that, all four remote loopbacks were reachable.
- **10.255.3.1** went from "down" (per A) to fully reachable during the experiment — its state was independent of the ARP issue, suggesting that node recovered on its own.
- **RTTs are stable and consistent with hop counts** (A: ~10ms, E: ~20ms via A, B: ~30ms via A, 10.255.3.1: ~35ms via A), suggesting a tree-like topology rooted at A from my perspective.

## 4. Coordination With Other Agents

Only A. The exchange:

1. **A → S:** Greeting, requested my prefixes, gave next-hop (10.1.1.2) and its loopback (10.255.1.1/32).
2. **S → A:** Announced 10.255.5.1/32, stated no customers, confirmed default route.
3. **A → S:** Confirmed install of 10.255.5.1/32 and that it is advertising my prefix upstream.
4. **S → A:** Asked which loopbacks were reachable via A so I could test.
5. **A → S:** Listed B (10.255.2.1), E (10.255.4.1), and 10.255.3.1 (latter reported as lossy/down).
6. **S → A:** Reported test failures with concrete data — ICMP Destination Unreachables sourced from 10.1.1.2, indicating a forward-path problem on A's router (not my return path).
7. **A → S:** Asked me to retest 10.255.4.1, citing a possible return-path problem reported by a peer.
8. **S → A:** Performed the requested test and reported both 10.255.4.1 (still unreachables) and 10.255.2.1 (silent drop). Pointed out that the unreachables originate from A's own router, so it cannot be a return-path issue on my side.
9. **A → S:** Acknowledged the issue was ARP aging on A's upstream interfaces; asked for a retest.
10. **S → A:** Retest still failing on `-c 5` runs; pushed back with data showing it wasn't a single-packet ARP race.
11. **A → S:** (Issue resolved between messages.)
12. **S → A:** Final retest showed full reachability to all four remote loopbacks; reported success.
13. **A → S:** Confirmed it had pinned ARP entries to prevent recurrence.

All coordination was strictly factual: I shared measurements and counts, never policy or contract details, and treated A's claims with appropriate skepticism — verifying with my own data-plane tests before accepting that the issue was resolved.