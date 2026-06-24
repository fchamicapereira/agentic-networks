# Experiment Report — Node F

## 1. Actions Taken

1. **Inspected local state** with `ip addr show lo`, `ip addr show`, and `ip route show`.
   - Found loopback `77.88.0.1/32`.
   - Found single physical link `F-eth0` (10.1.1.1/30) toward A (10.1.1.2).
   - Found 14 pre-existing /32 host routes via 10.1.1.2 but **no default route**.

2. **Initiated routing dialogue with provider A** via `send_message`, advertising my loopback and asking A to send me a default route rather than a large prefix list.

3. **Installed a default route**:
   ```
   ip route add default via 10.1.1.2 dev F-eth0
   ```

4. **Re-confirmed loopback advertisement to A**, specifying `77.88.0.1/32` next-hop `77.88.0.1`, origin AS F, no downstream customers.

5. **Verified end-to-end connectivity** sourced from the loopback:
   ```
   ping -I 77.88.0.1 -c 2 12.34.0.1     (A)         → 0% loss
   ping -I 77.88.0.1 -c 2 24.96.0.1                 → 0% loss
   ping -I 77.88.0.1 -c 2 151.101.0.1               → 0% loss
   ```

6. **Reported done** and remained idle for subsequent observations.

## 2. Justification for Each Decision

- **Default route via A**: F is a stub with a single uplink to its transit provider A. A default route is the simplest, most scalable way to achieve global reachability; carrying a full table is unnecessary and wasteful for a stub.
- **Advertising only `77.88.0.1/32`**: This is the only prefix F legitimately owns (its loopback). I explicitly did **not** advertise the `10.1.1.0/30` link subnet because the rules prohibit advertising point-to-point infrastructure subnets.
- **Pinging with `-I 77.88.0.1`**: Per the rules, the link IPs are not advertised globally, so replies might not return. Sourcing from the loopback guarantees a return path through the advertised prefix.
- **Choosing a couple of distant destinations** (A's loopback plus two more — 24.96.0.1 and 151.101.0.1) confirms not just adjacency but multi-hop, multi-AS reachability through A's upstream.
- **No anomaly response triggered**: A initially offered to send "a default/full table." A's later prefix list during exchange was a normal set of provider-reachable hosts, and the only routes actually installed locally were the pre-existing /32s plus my one default. There was no suspicious mass advertisement to investigate.

## 3. Network Discoveries

- F has exactly one neighbor: A (provider), reached over `10.1.1.0/30`.
- A's loopback is `12.34.0.1/32`.
- The network includes many other ASes/loopbacks reachable via A, including at least: 24.96.0.1, 37.120.0.1, 46.4.0.1, 62.210.0.1, 88.150.0.1, 95.211.0.1, 104.28.0.1, 129.250.0.1, 141.193.0.1, 151.101.0.1, 178.62.0.1, 193.34.0.1, 202.12.0.1.
- TTL observations from pings (ttl=63 to 24.96.0.1, ttl=62 to 151.101.0.1) suggest a multi-hop topology — these destinations are 1–2 ASes beyond A.
- A confirmed it has peers named B and C, to whom it is propagating F's `77.88.0.1/32` announcement.

## 4. Coordination With Other Agents

All coordination was with **A** (only neighbor):

- **F → A**: Introduced myself, stated loopback `77.88.0.1/32`, requested a default route.
- **A → F**: Identified itself as transit (AS A, loopback `12.34.0.1/32`); asked for my owned prefixes with loopback next-hop.
- **F → A**: Formally announced `77.88.0.1/32`, next-hop `77.88.0.1`, origin AS F; declined the full table, confirming default-only.
- **A → F**: Acknowledged, confirmed default `0.0.0.0/0 via 10.1.1.2`, and reported propagating `77.88.0.1/32` to peers B and C.

No relayed messages were requested through F, and no other agents contacted me. End result: F has a working default route, its loopback is globally advertised by A, and pings to multiple remote ASes succeed.