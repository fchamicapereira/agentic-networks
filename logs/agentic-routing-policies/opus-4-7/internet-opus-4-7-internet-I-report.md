# AS I Experiment Report

## 1. Actions Taken

1. **Inventory**: Ran `ip addr show` / `ip route show`. Confirmed:
   - Link interface I-eth0: 10.1.4.1/30 (peer 10.1.4.2)
   - Loopback prefix: 10.255.9.1/32
   - No initial routes beyond local connected.

2. **Initial default route attempt**: `ip route add default via 10.1.4.2` — failed with "invalid gateway" because the /30 connected route hadn't been auto-installed yet.

3. **Manual link route + default**:
   ```
   ip route add 10.1.4.2/32 dev I-eth0
   ip route add default via 10.1.4.2
   ```

4. **Announced my prefix to B** via message: `10.255.9.1/32`, no customer prefixes.

5. **Initial connectivity**: B's interface and loopback (10.255.2.1) reachable after ARP succeeded. Only H (10.255.8.1) reachable among the 14 other ASes despite default route being installed.

6. **Diagnosis**: A `ping -I 10.255.9.1 10.255.1.1` succeeded while default `ping 10.255.1.1` (sourced from 10.1.4.1) timed out. Root cause: remote ASes only have a route back to my loopback /32, not to my /30 link.

7. **Fix**: Reinstalled default route with explicit source:
   ```
   ip route del default via 10.1.4.2
   ip route add default via 10.1.4.2 src 10.255.9.1
   ```

8. **Verification**: All 14 remote loopbacks (A, B, C, D, E, F, G, H, J, K, L, M, N, O) responded to ping.

## 2. Justifications

- **Default route via B only**: As a stub AS with B as sole provider, a default route is sufficient and matches stub semantics (no need to install per-prefix routes).
- **Advertise only 10.255.9.1/32**: Stub policy — only originate my own prefix, never re-export B's routes.
- **`src 10.255.9.1` on default route**: Ensures locally-originated traffic uses the globally-advertised loopback as source IP. The /30 transit link is not advertised, so packets sourced from 10.1.4.1 are undeliverable on the return path.
- **No customer/peer advertisements**: I have neither customers nor peers.

## 3. Network Discoveries

- 15-AS topology (A–O), each AS identified by a `10.255.X.1/32` loopback.
- Inter-AS links use small /30s (mine: 10.1.4.0/30).
- Network qdisc uses `netem` with ~6 ms delay per hop (no loss).
- All ASes start with no routes and converge simultaneously; ARP and routing came online over the first ~30–60 seconds.
- Remote ASes only install routes to advertised /32 loopbacks — transit link /30s are not globally routable. This is a key constraint requiring source-address pinning on stub nodes.

## 4. Coordination with Other Agents

Only with B (my provider):
- **Sent**: prefix announcement `10.255.9.1/32`; later a diagnostic message asking about propagation when only H replied.
- **Received from B**: B's prefix (10.255.2.1) and next-hop confirmation; the full list of 14 other AS loopbacks B advertises to me (with an incremental update adding L=10.255.12.1); a hint to either use a default route or add the connected /30 with `src 10.1.4.1`.

The hint from B about adding `src` on the route was what led me to apply the same idea to the default route using my loopback as source, resolving the connectivity issue.