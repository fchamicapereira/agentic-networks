# G Node Experiment Report

## 1. Actions Taken

**Initial Discovery:**
- Ran `ip addr` / `ip route`: found 3 interfaces (G-eth0→E, G-eth1→F, G-eth2→H) but no routing table entries at all.
- Added directly-connected routes:
  - `ip route add 10.1.57.0/30 dev G-eth0` (E)
  - `ip route add 10.1.67.0/30 dev G-eth1` (F)
  - `ip route add 10.1.78.0/30 dev G-eth2` (H)
- Pinged each peer to measure latency: E=30ms, F=20ms, H=20ms (RTT).

**Information Exchange:**
- Sent topology/latency inquiries to E, F, H.
- Received full topology from E, plus local-link data from H and F.

**Route Installation (via best-latency paths):**
- `ip route add 10.1.56.0/30 via 10.1.67.1` (E-F subnet via F: 40ms vs 50ms via E)
- `ip route add 10.1.58.0/30 via 10.1.78.2` (E-H via H: 40ms vs 70ms via E, and avoids flaky E-H link)
- `ip route add 10.1.68.0/30 via 10.1.67.1` (F-H via F: 50ms, tie with H)
- `ip route add 10.2.18.0/30 via 10.1.78.2` (A-H via H, direct)
- `ip route add 10.2.45.0/30 via 10.1.57.1` (D-E via E, only sane path)
- `ip route add 10.0.{12,13,14,23,24,34}.0/30 via 10.1.57.1` (A/B/C/D cluster via E→D, 530–570ms vs 1020ms+ via H→A)
- `sysctl -w net.ipv4.ip_forward=1` (enable transit for neighbors using me as a router).

**Verification:** Pinged at least one IP on every node A–H. All replied.

## 2. Decision Justifications

- **Direct over indirect for E/F/H**: Latencies measured made direct links optimal (E-direct 30ms < via-F 40ms < via-H 70ms; F-direct and H-direct both 20ms, fastest).
- **E-F (10.1.56/30) via F**: 40ms via F direct < 50ms via E forwarding.
- **E-H (10.1.58/30) via H**: 40ms via H < 70ms via E. Also E-H was reported as flaky (80–1000ms variable), so routing around it saves variability.
- **A/B/C/D via E**: The A-cluster is only accessible through two inter-cluster links: D-E (500ms) and H-A (~1000ms, very jittery). G→E→D→{A,B,C,D} = 530–570ms RTT, beating G→H→A→... (≥1020ms). Only A's H-facing interface (10.2.18.1) itself is routed via H because that IP physically sits on H's side of the A-H link.
- **Enabled forwarding**: H and F announced they would route some destinations via G (e.g., H→G→E for 50ms vs direct E-H 80+ms). Without forwarding I'd drop those transit packets.

## 3. Network Discoveries

Complete topology (RTT):
- Core mesh: E-F 20ms, E-G 30ms, E-H 40–1000ms (flaky), F-G 20ms, F-H 30ms, G-H 20ms.
- A-cluster mesh: A-B 20ms, A-C 30ms, A-D 40ms, B-C (10.0.23/30), B-D 30ms, C-D 20ms.
- Inter-cluster bridges (both slow): D-E 500ms (10.2.45/30), H-A ~700–1400ms (10.2.18/30).
- Subnets all /30.
- No routing protocol running; every node had to be statically configured and no default routes existed at start.
- A transient routing loop existed at E for 10.2.18.0/30; resolved after E fixed its routes, after which 10.2.18.1 became reachable via G→H→A (645ms).

## 4. Coordination With Other Agents

- **E** supplied the full topology map (nodes, subnets, latencies) and recommended per-prefix next-hops from G's perspective, which I cross-checked and mostly adopted.
- **F** shared its neighbor set (E, G, H) and latencies; I confirmed direct links to F were optimal and told F to route the A-cluster via E.
- **H** shared its A-link details (10.2.18/30, very slow) and proposed routing E via G (50ms vs 80+ms); I confirmed and enabled IP forwarding to support that. H also revealed A's additional links to B and C.
- I relayed synthesized info back to each neighbor so they could optimize their own tables (e.g., telling F that direct E/H were better than via G, telling H to route E and F via me).
- Reported a routing loop on E for 10.2.18/30, which E then corrected.

Final state: G has full reachability to A, B, C, D, E, F, H with minimum-latency next-hops for every known /30.