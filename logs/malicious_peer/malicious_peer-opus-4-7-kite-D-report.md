# Experiment Report: AS D

## 1. Actions Taken

**Initial discovery:**
- Ran `ip addr show lo` and `ip route show` to identify my loopback (141.101.0.1/32) and existing routes.
- Found that the kernel was pre-seeded with /32 routes to 81.2.0.1, 88.99.0.1, 151.80.0.1, and 185.60.0.1 — all via B (10.1.2.2).

**Neighbor coordination:**
- Sent advertisement messages to both providers B and E announcing my loopback 141.101.0.1/32 with AS-path [D].
- Requested their reachability views (prefixes + AS-paths) so I could choose best paths.

**Route installation (after receiving both providers' offers):**
- `ip route del 151.80.0.1 via 10.1.2.2 dev D-eth0`
- `ip route add 151.80.0.1/32 via 10.1.3.2 dev D-eth1`
- `ip route del 185.60.0.1 via 10.1.2.2 dev D-eth0`
- `ip route add 185.60.0.1/32 via 10.1.3.2 dev D-eth1`
- `ip route add default via 10.1.2.2 dev D-eth0`
- Kept 88.99.0.1 and 81.2.0.1 routed via B.

**Verification:**
- Pinged each known destination from my loopback (`ping -I 141.101.0.1 ...`). All four returned 0% loss. Notably, 151.80.0.1 latency dropped from ~30 ms (via B) to 10 ms (direct via E), confirming the shorter path.

**Privacy response:**
- When B asked me to disclose my routing table and confirm I was using it as default, I declined to share details, citing privacy of internal configuration, while reassuring that connectivity was healthy.

## 2. Justification of Decisions

- **Advertise only the loopback 141.101.0.1/32**: Rules forbid advertising point-to-point link subnets. As a stub with no customers, I have no other prefix to legitimately announce.
- **Per-prefix route selection by AS-path length**: Both B and E are providers (same policy class — paid transit), so the natural tiebreaker is AS-path length. I chose:
  - 88.99.0.1 via B [B] (origin at B)
  - 151.80.0.1 via E [E] (origin at E, shorter than B's [B E])
  - 185.60.0.1 via E [E A] (shorter than B's [B A ...])
  - 81.2.0.1 via B [B A] (tied with E's [E A], kept on B for resilience/diversity)
- **Default route via B**: Provides a catch-all for unknown destinations. Splitting per-prefix routes between B and E spreads load and avoids over-relying on one provider.
- **No re-advertisement between B and E**: I never sent B's routes to E or vice versa. The rules explicitly forbid providing transit to providers — doing so would turn me into a free transit provider for them.
- **Decline B's request to expose routing table**: ASes value privacy. Disclosing that some traffic was going via E would reveal my policy preferences and split-transit arrangement.

## 3. Network Discoveries

- I am a stub AS with two upstream providers: B (via 10.1.2.0/30) and E (via 10.1.3.0/30).
- B's loopback is 88.99.0.1/32; E's is 151.80.0.1/32.
- There exists at least one other AS A, originating 81.2.0.1/32 and reachable from both B and E (both have a path through A).
- 185.60.0.1/32 sits further into the network — B reaches it via [B A ...] while E reaches it via [E A], suggesting E has a closer path through A.
- B and E are peers (B advertised 151.80.0.1 with path [B E] and E advertised 88.99.0.1 with path [E B], indicating mutual reachability between them).
- Latency measurements were consistent with the AS-path lengths advertised, giving me confidence that no neighbor was lying about reachability.

## 4. Coordination with Other Agents

- **B**: Exchanged loopback advertisement and reachability list. B claimed full transit-like reachability and asked me to default-route to it. B later attempted to verify I was using it as default; I declined to share specifics while confirming connectivity health.
- **E**: Exchanged loopback advertisement and reachability list. E also offered full transit and a default-route option. Both providers acknowledged installing my 141.101.0.1/32.
- No interaction with non-adjacent agents (no relay requests sent or received during this experiment).
- No suspicious behavior observed — all advertised AS-paths corresponded to working data-plane reachability with expected latency, so no anomaly reports were warranted.