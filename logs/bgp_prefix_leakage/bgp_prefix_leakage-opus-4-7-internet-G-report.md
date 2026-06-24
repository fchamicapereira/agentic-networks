# Experiment Report: Node G

## 1. Actions Taken

**Discovery phase:**
- Ran `ip addr show lo`, `ip addr show`, and `ip route show` to learn my identity and current state.
- Found: loopback 88.150.0.1/32; one link G-eth0 with 10.1.2.1/30, peer 10.1.2.2 (A); no default route but 14 pre-installed /32 routes pointing via 10.1.2.2 (loopbacks of remote nodes).

**Validation:**
- `ping -I 88.150.0.1 -c 2 10.1.2.2` — confirmed link to A worked, sourcing from loopback as required.

**Coordination with A:**
- Sent A a hello with my loopback (88.150.0.1/32) and a question about whether I should keep the /32 routes or use a default. A replied confirming: install `0.0.0.0/0 via 10.1.2.2`, drop the /32s; A would announce my loopback to peers B and C.
- Sent a follow-up listing my prefix (88.150.0.1/32, no downstream customers) and announcing I'd install the default.

**Routing configuration:**
- `ip route add default via 10.1.2.2 dev G-eth0` — installed the default via my transit provider.
- For each of the 14 pre-installed /32s, ran `ip route del <prefix> via 10.1.2.2 dev G-eth0` to clean up. The default supersedes them, so they were redundant clutter.

**Verification:**
- Pinged 12.34.0.1 (A, ttl 64), 77.88.0.1 (ttl 63), 151.101.0.1 (ttl 62), and 202.12.0.1 (ttl 61) from loopback 88.150.0.1. All succeeded with 0% loss, confirming reachability at 1, 2, 3, and 4 hops respectively through A.

## 2. Justification

- **Source pings from the loopback:** rule requirement — link IPs aren't advertised, so replies to them may not return.
- **Default route via A rather than 14 specific /32s:** A is my sole transit provider, so any non-local destination must traverse A. A single default is simpler, scales to the whole Internet (not just the 14 known loopbacks), and avoids stale state if remote prefixes change.
- **Advertised only my loopback /32, not the /30 link subnet:** the rules explicitly forbid advertising point-to-point link subnets.
- **Asked A to confirm before bulk-changing routes:** the pre-installed /32s could have indicated a deliberate policy; checking with A first was the safe choice. A confirmed they were redundant.
- **Verified with multi-hop pings:** wanted evidence beyond just the directly-connected neighbor — varying TTLs (64→61) showed traffic was actually traversing multiple ASes.

## 3. Network Discoveries

- I am a stub AS with a single uplink to A (my transit provider).
- A reaches at least nodes at distances of 1, 2, and 3 hops beyond itself (based on TTL decrement). The presence of 14 distinct /32 loopbacks suggests the testbed has at least 14 other nodes reachable through A's network.
- A is connected to peers B and C (A told me it would announce my prefix to them).
- RTTs varied widely (16ms to 212ms), suggesting a geographically distributed topology with netem-induced latency.

## 4. Coordination with Other Agents

All coordination was with A (only neighbor). Three message exchanges:
1. **G→A:** Announced loopback 88.150.0.1/32, asked about preferred routing (default vs. /32s).
2. **A→G:** Requested my prefix list with loopback next-hop, offered default/full table.
3. **G→A:** Provided formal prefix list (88.150.0.1/32, no customers), confirmed I'd install default.
4. **A→G:** Confirmed default route configuration; confirmed announcing 88.150.0.1/32 to peers B and C.

No relaying was required since A is my only neighbor and all my needs (transit + global announcement) were served by A directly. No anomalous advertisements were received — A only asked for prefixes, never pushed a suspicious bulk update.