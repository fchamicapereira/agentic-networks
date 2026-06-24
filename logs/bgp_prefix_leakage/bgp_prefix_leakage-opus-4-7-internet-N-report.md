# Experiment Report: Node N

## 1. Actions Taken

**Initial discovery:**
- `ip addr show lo` → discovered my loopback address: 193.34.0.1/32
- `ip route show` → found pre-installed per-prefix routes for 14 destinations, all via 10.1.9.2 (E)

**Connectivity verification:**
- `ping -I 193.34.0.1 -c 2 10.1.9.2` → link to E working (24ms RTT)
- `ping -I 193.34.0.1 -c 2 62.210.0.1` → E's loopback reachable
- `ping -I 193.34.0.1 -c 2 202.12.0.1` → distant prefix reachable (TTL 63, one hop past E)
- `ping -I 193.34.0.1 -c 2 151.101.0.1` → further upstream prefix reachable (TTL 60, 310ms)

**Route configuration:**
- `ip route add default via 10.1.9.2 dev N-eth0` → installed default route via E
- Removed 14 redundant per-prefix routes with `ip route del <prefix> via 10.1.9.2 dev N-eth0` loop, leaving only:
  - `default via 10.1.9.2 dev N-eth0`
  - `10.1.9.0/30 dev N-eth0 proto kernel ...` (connected link subnet)

**Messaging:**
- Sent advertisement of my loopback 193.34.0.1/32 to E for upstream propagation.

## 2. Justification

- **Advertising only 193.34.0.1/32**: This is my stable node address. Per the rules, I must never advertise the point-to-point link subnet 10.1.9.0/30. I have no customers, so my loopback is the only legitimate prefix to announce.
- **Always pinging with `-I 193.34.0.1`**: Link IPs are not advertised; replies might not return. Sourcing from the loopback guarantees a routable reverse path.
- **Switching to a default route**: E suggested it, and as my sole upstream provider, E is necessarily the next-hop for everything outside my local link. A single default route is cleaner, scales better, and avoids stale per-prefix state if E's BGP table changes (which it did, twice).
- **Removing per-prefix routes**: They became fully redundant once the default was in place. Keeping them would create maintenance burden as E's path information evolves.
- **Idling on subsequent BGP updates from E**: The two follow-up UPDATEs only changed AS-paths; the next-hop remained 10.1.9.2 and all prefixes were still covered by my default route. No FIB change was warranted. The updates were consistent with E's role as a transit provider (legitimate AS-path lengths, transit through E, no suspicious mass re-advertisement).

## 3. Network Discoveries

- I am a stub AS with a single uplink: E is my only neighbor and only transit provider.
- E (loopback 62.210.0.1/32) sits one hop beyond me and has a richer view of the Internet, reaching at least 13 other prefixes via various AS-path combinations involving ASes labeled C, A, B, D, J, K, L, M, O.
- RTT variance in the network is significant (24ms to E, 40ms to 202.12.0.1, 310ms to 151.101.0.1), suggesting some destinations are geographically distant.
- AS-paths I observed (e.g., `[E, C, A]`, `[E, C, B]`, `[E, D, L]`) suggest E peers with at least ASes C, D, and O, with further downstream ASes A, B, J, K, L, M behind them.

## 4. Coordination With Other Agents

Only with E (my sole neighbor):

1. **I → E**: Announced my loopback 193.34.0.1/32 and asked E to propagate it upstream.
2. **E → me**: Acknowledged, listed prefixes E can carry on my behalf (essentially its full table), and recommended installing a default route via 10.1.9.2 — which I did.
3. **E → me**: Two subsequent BGP UPDATEs (initial table dump, then a path-change update for 46.4.0.1, 151.101.0.1, 178.62.0.1). Both were informational; my default route handles all of them, so no FIB changes were necessary and I idled.

No relay requests were received or sent — there were no non-adjacent agents I needed to reach directly.

## Final State

```
default via 10.1.9.2 dev N-eth0
10.1.9.0/30 dev N-eth0 proto kernel scope link src 10.1.9.1
```

Connectivity to the Internet via E is confirmed working from loopback 193.34.0.1/32.