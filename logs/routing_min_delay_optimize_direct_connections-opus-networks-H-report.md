# Experiment Report: Node H Network Configuration

## Network Discovery

The network consists of 8 nodes divided into two clusters connected by two bridge links:

**Cluster 1 (low-latency mesh):** A, B, C, D
- A-B: 10ms, A-C: 15ms, A-D: 20ms, B-C: 10ms, B-D: 15ms, C-D: 10ms

**Cluster 2 (low-latency mesh):** E, F, G, H
- E-F: 10ms, E-G: 15ms, E-H: 20ms, F-G: 10ms, F-H: 15ms, G-H: 10ms

**Bridge links (high latency):**
- D-E: 250ms (one-way)
- A-H: 350ms (one-way)

## Actions Taken

### 1. Interface Discovery and Latency Measurement
Ran `ip addr show`, `ip link show`, `ip route show`, and `tc qdisc show` on all interfaces. Found H has four interfaces with netem delays: H-eth0→E (20ms), H-eth1→F (15ms), H-eth2→G (10ms), H-eth3→A (350ms). Confirmed with ping RTTs: E=40ms, F=30ms, G=20ms, A=700ms.

### 2. Connected Route Setup
Added basic connected routes for all four directly attached subnets: `ip route add 10.1.58.0/30 dev H-eth0`, etc.

### 3. Topology Collection via Messaging
Sent topology information (my interfaces, IPs, delays) to all 7 nodes and requested theirs. Received responses from E, F, G, A, B, C, D over several rounds. Built complete topology map.

### 4. Shortest Path Computation
Computed optimal next-hops from H using Dijkstra-style reasoning:
- **G**: 10ms direct (best) — via H-eth2
- **F**: 15ms direct (best vs 10+10=20ms via G) — via H-eth1
- **E**: 20ms direct (best vs 10+15=25ms via G) — via H-eth0
- **D**: 20+250=270ms via E (best, vs 350+20=370ms via A) — via E
- **C**: 20+250+10=280ms via E→D — via E
- **B**: 20+250+15=285ms via E→D — via E
- **A**: 20+250+20=290ms via E→D (best, vs 350ms direct) — via E

### 5. Route Configuration
```
ip route add 10.0.12.0/30 via 10.1.58.1  # A-B subnet via E
ip route add 10.0.13.0/30 via 10.1.58.1  # A-C subnet via E
ip route add 10.0.14.0/30 via 10.1.58.1  # A-D subnet via E
ip route add 10.0.23.0/30 via 10.1.58.1  # B-C subnet via E
ip route add 10.0.24.0/30 via 10.1.58.1  # B-D subnet via E
ip route add 10.0.34.0/30 via 10.1.58.1  # C-D subnet via E
ip route add 10.2.45.0/30 via 10.1.58.1  # D-E subnet via E
ip route add 10.1.56.0/30 via 10.1.58.1  # E-F subnet via E (20ms vs 25ms via F)
ip route add 10.1.57.0/30 via 10.1.58.1  # E-G subnet via E (20ms vs 25ms via G)
ip route add 10.1.67.0/30 via 10.1.78.1  # F-G subnet via G (20ms vs 25ms via F)
```

### 6. Attempted Optimization of A-H Subnet
Tried to route A's 10.2.18.1 via E→D→A (290ms) instead of direct (350ms). This caused ICMP redirect loops: first E redirected traffic back to H (since H is directly connected to A on that subnet), then after asking E to disable send_redirects, D redirected traffic back to E (D lacked the 10.2.18.0/30 → A route). Despite multiple messages to D requesting `ip route add 10.2.18.0/30 via 10.0.14.1` and `sysctl -w net.ipv4.conf.all.send_redirects=0`, D did not respond in time. Reverted to using the direct link for 10.2.18.0/30, which works at 640ms RTT (asymmetric: outbound 350ms direct, return 290ms via D→E→H).

### 7. Disabled ICMP Redirect Acceptance
Ran `sysctl -w net.ipv4.conf.all.accept_redirects=0` on all interfaces to prevent redirect-based route corruption.

## Coordination with Other Agents
- Exchanged full topology information with all 7 nodes in multiple rounds
- Asked E to disable ICMP send_redirects (successful)
- Asked D to add route for 10.2.18.0/30 via A and disable send_redirects (no confirmation received)
- Shared F-G subnet details (10.1.67.0/30, F=.1, G=.2) with B upon request
- Confirmed routing strategy with A, E, and others: cluster 1 traffic from H routes via E→D

## Final Result
Full IP connectivity achieved to all 28 IPs across all 7 nodes. Routes are latency-optimized for all paths except the 10.2.18.0/30 subnet, which uses the direct H→A link due to ICMP redirect issues with intermediate routers D not cooperating in time.