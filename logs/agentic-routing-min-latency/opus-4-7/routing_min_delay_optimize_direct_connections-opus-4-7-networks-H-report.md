# H Node Experiment Report

## 1. Actions Taken

**Initial inspection:**
- `ip addr show` / `ip route show` — discovered 4 interfaces (eth0→E, eth1→F, eth2→G, eth3→A) with /30 link addresses, but no main-table routes populated.

**Bootstrap connectivity:**
- Added directly-connected routes for each link:
  ```
  ip route add 10.1.58.0/30 dev H-eth0   (E)
  ip route add 10.1.68.0/30 dev H-eth1   (F)
  ip route add 10.1.78.0/30 dev H-eth2   (G)
  ip route add 10.2.18.0/30 dev H-eth3   (A)
  ```
- Measured neighbor RTTs with ping: E=40ms (with initial jitter), F=30ms, G=20ms, A≈700–1400ms.

**Enabled forwarding:** `sysctl -w net.ipv4.ip_forward=1`

**Installed optimized routes:**
```
ip route add 10.1.58.1/32 dev H-eth0
ip route add 10.1.68.1/32 dev H-eth1
ip route add 10.1.78.1/32 dev H-eth2
ip route add 10.1.56.0/30 via 10.1.68.1 dev H-eth1   # E-F via F (30ms)
ip route add 10.1.57.0/30 via 10.1.78.1 dev H-eth2   # E-G via G (20ms)
ip route add 10.1.67.0/30 via 10.1.78.1 dev H-eth2   # F-G via G (40ms < 50ms)
ip route add 10.2.45.0/30 via 10.1.58.1 dev H-eth0   # D-E via E
ip route add 10.0.0.0/16  via 10.1.58.1 dev H-eth0   # A-cluster via E→D
```

**Bug fix:** Initially added `10.2.18.1/32 via 10.1.58.1` to force A's A-H interface through E→D path. F reported TTL-exceeded loops (E's return route for 10.2.18.0/30 pointed back at me). Removed that /32 override; accepted the slow 640ms direct path for 10.2.18.1 as unavoidable asymmetry.

## 2. Justification

- **Direct to E/F/G:** direct links were fastest or tied (E=40 vs via G+E=50; F=30 vs via G+F=40; G=20 direct).
- **Inter-cluster subnets through intermediate hops** where cheaper: 10.1.56/30 via F (30ms) beat via E (40ms); 10.1.57/30 via G (20ms) beat via E (40ms); 10.1.67/30 via G (40ms) beat via F (50ms).
- **All A-cluster traffic via E:** H→E→D→{A,B,C,D} = 540–585ms, dramatically better than direct H-A 700–1400ms. The 500ms E-D bridge is still cheaper than the 700–1000ms H-A bridge.
- **Summary route 10.0.0.0/16 via E:** consolidates six A-cluster /30s (10.0.12/30…10.0.34/30) into one entry.
- **Removed /32 override on A's 10.2.18.1:** even though routing it via E would save latency, asymmetric routing caused a loop and A hadn't installed reciprocal routes; reverted to direct link for that single address.

## 3. Network Discoveries

Full topology reconstructed from peer reports (E had the complete map):

**Cluster 1 {E,F,G,H}** — fast mesh:
- E-F 20ms (10.1.56/30), E-G 30ms (10.1.57/30), E-H 40ms (10.1.58/30)
- F-G 20ms (10.1.67/30), F-H 30ms (10.1.68/30), G-H 20ms (10.1.78/30)

**Cluster 2 {A,B,C,D}** — fast mesh:
- A-B 20ms (10.0.12/30), A-C 30ms (10.0.13/30), A-D 40ms (10.0.14/30)
- B-C (10.0.23/30), B-D 30ms (10.0.24/30), C-D 20ms (10.0.34/30)

**Inter-cluster bridges (both slow):**
- D-E 500ms (10.2.45/30) — the preferred bridge
- A-H 700–1400ms (10.2.18/30) — my direct link, avoided except for the subnet itself

## 4. Coordination with Other Agents

- **G:** exchanged neighbor lists and latencies; G confirmed G-E=30ms, G-F=20ms allowing me to compute transit paths.
- **F:** exchanged link latencies; F's TTL-exceeded report was critical in detecting my routing loop on 10.2.18.1.
- **E:** became the authoritative topology oracle — provided the complete subnet/IP mapping for all 13 links, confirmed symmetric routing preferences, and requested I enable `ip_forward` (already needed).
- **A:** shared its cluster's subnets and node IPs; agreed on the H↔A path via D-E being optimal (580ms vs 700–1000ms direct). Asked A to install reciprocal routes via D so return traffic also uses the fast path.

**Final verification:** successful pings to all 7 other nodes — direct neighbors at 20–40ms, A-cluster via E at 540–585ms, A's 10.2.18.1 at 640ms (slow-path unavoidable).