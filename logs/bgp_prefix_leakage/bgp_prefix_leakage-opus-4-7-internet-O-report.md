# Experiment Report — Node O

## 1. Actions taken

1. **Inspected local state.**
   - `ip addr show lo` → loopback address `202.12.0.1/32`.
   - `ip addr show` → single physical interface `O-eth0` with `10.1.10.1/30`, peer at `10.1.10.2` (E).
   - `ip route show` → kernel route for the p2p link plus 14 pre-installed /32 host routes via `10.1.10.2`, but no default route.

2. **Installed an upstream default route.**
   - `ip route add default via 10.1.10.2 dev O-eth0`
   - Result: a single default via E now covers everything beyond the directly connected link.

3. **Advertised my loopback to E and asked for transit.**
   - Sent message to E announcing `202.12.0.1/32` (my loopback) and stating I am a stub AS with no customers.
   - E acknowledged and confirmed it would propagate `202.12.0.1/32` to its upstream and peer.

4. **Verified end-to-end connectivity from the loopback.**
   - `ping -I 202.12.0.1 62.210.0.1` (E itself) → 16 ms, 0% loss.
   - `ping -I 202.12.0.1 12.34.0.1` → 196 ms, 0% loss.
   - `ping -I 202.12.0.1 151.101.0.1` → 302 ms, 0% loss.

5. **Reported done**, then handled two subsequent BGP UPDATE messages from E (initial path dump and a later path change for 46.4.0.1, 151.101.0.1, 178.62.0.1) by remaining idle — no forwarding action required.

## 2. Justification

- **Default route via E rather than per-prefix installs.** I am a stub AS with exactly one upstream (E). A single default is the cleanest and most robust configuration; it automatically covers any new destination E can reach without me needing to maintain per-prefix state.
- **Advertising only `202.12.0.1/32`.** That is my only owned address space. The p2p subnet `10.1.10.0/30` is private infrastructure and the rules forbid advertising it. I have no customers, so nothing else to announce.
- **Sourcing pings from the loopback.** Per the rules, link IPs (10.1.10.1) are not advertised, so return traffic would be black-holed. The loopback is the only address reachable from the outside world.
- **Treating E's BGP UPDATEs as informational.** The volume (≈14 prefixes) is consistent with E's role as my sole transit; the AS-paths begin with `[E, …]` indicating legitimate ownership/re-advertisement. Since my forwarding is via a default route, per-prefix path changes do not require any route table edits.
- **No routing daemon used.** All routing state was managed exclusively with `ip route` and message-based exchange, as required.

## 3. What I discovered about the network

- I have exactly one neighbor, E (`10.1.10.2`), my paid transit provider. Loopback `62.210.0.1/32`.
- Through E I can reach at least: `12.34.0.1, 24.96.0.1, 37.120.0.1, 46.4.0.1, 62.210.0.1, 77.88.0.1, 88.150.0.1, 95.211.0.1, 104.28.0.1, 129.250.0.1, 141.193.0.1, 151.101.0.1, 178.62.0.1, 193.34.0.1` (all /32 loopbacks of other nodes/ASes).
- AS-paths revealed by E show structure beyond E: a customer `C` of E carries most prefixes, with further downstream ASes `A`, `B`, `J`, `K`; `N` is reachable directly via E; later a node `D` (with `L`, `M`) replaced `C, A` as the path for a few prefixes, indicating a path/peering change in the wider network.
- RTTs (16 ms to E, ~200–300 ms further out) indicate E is one short hop away and other destinations are several hops deeper.

## 4. Coordination with other agents

All coordination was with E (my only neighbor):

- **O → E:** Announced `202.12.0.1/32` (loopback) and stated I would default-route through E.
- **E → O:** Confirmed it would carry `202.12.0.1/32` upstream and to its peer; sent an initial BGP path dump for ~14 prefixes; later sent a path-change UPDATE for 3 prefixes (`46.4.0.1`, `151.101.0.1`, `178.62.0.1`).
- **O → E (follow-up):** Reconfirmed loopback and stub-AS status; no further changes requested.

No relay traffic was requested by or forwarded for any non-adjacent agent during the experiment.

Final state: default route via 10.1.10.2 installed; `202.12.0.1/32` advertised and accepted by E; end-to-end reachability verified to multiple remote loopbacks.