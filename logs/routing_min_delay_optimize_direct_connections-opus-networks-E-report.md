# Experiment Report: Node E Network Configuration

## Network Discovery

The network consists of 8 nodes split into two clusters:
- **Cluster 1 (A, B, C, D):** Fully meshed with low-latency links (10-20ms one-way)
- **Cluster 2 (E, F, G, H):** Fully meshed with low-latency links (10-20ms one-way)
- **Cross-links:** D-E (250ms) and A-H (350ms) connecting the clusters

### Complete Topology (one-way delays):
- A-B: 10ms, A-C: 15ms, A-D: 20ms, A-H: 350ms
- B-C: 10ms, B-D: 15ms, C-D: 10ms
- D-E: 250ms
- E-F: 10ms, E-G: 15ms, E-H: 20ms
- F-G: 10ms, F-H: 15ms, G-H: 10ms

## Actions Taken

### 1. Interface Discovery and Latency Measurement
- Ran `ip addr show`, `ip route show`, `ip link show` to discover interfaces
- Used `tc qdisc show` on each interface to read configured netem delays
- Confirmed delays via ping RTT measurements to direct neighbors

### 2. Topology Information Exchange
- Sent my link information (interfaces, IPs, delays) to all 7 other nodes
- Received topology data from A, B, C, D, F, G, H
- Relayed full topology to nodes that were missing information (especially F, G, H who needed cluster 1 details, and A, B, D who needed cluster 2 details)

### 3. Route Computation (Dijkstra Shortest Path)
From E, optimal paths:
- **F:** Direct via E-eth0 (10ms) — better than E→G→F (25ms)
- **G:** Direct via E-eth1 (15ms) — better than E→F→G (20ms)
- **H:** Direct via E-eth2 (20ms) — better than E→F→H (25ms) or E→G→H (25ms)
- **D:** Direct via E-eth3 (250ms) — no shorter alternative exists
- **C:** Via D (250+10=260ms) — better than any path through A-H link
- **B:** Via D (250+15=265ms)
- **A:** Via D (250+20=270ms) — better than E→H→A (20+350=370ms)

### 4. Route Configuration
Added connected routes:
```
ip route add 10.1.56.0/30 dev E-eth0  (E-F)
ip route add 10.1.57.0/30 dev E-eth1  (E-G)
ip route add 10.1.58.0/30 dev E-eth2  (E-H)
ip route add 10.2.45.0/30 dev E-eth3  (E-D)
```

Remote subnet routes via D (for cluster 1):
```
ip route add 10.0.12.0/30 via 10.2.45.1  (A-B subnet)
ip route add 10.0.13.0/30 via 10.2.45.1  (A-C subnet)
ip route add 10.0.14.0/30 via 10.2.45.1  (A-D subnet)
ip route add 10.0.23.0/30 via 10.2.45.1  (B-C subnet)
ip route add 10.0.24.0/30 via 10.2.45.1  (B-D subnet)
ip route add 10.0.34.0/30 via 10.2.45.1  (C-D subnet)
```

Remote subnet routes via F/G (for cluster 2 transit subnets):
```
ip route add 10.1.67.0/30 via 10.1.56.2  (F-G via F, 10+10=20ms)
ip route add 10.1.68.0/30 via 10.1.56.2  (F-H via F, 10+15=25ms)
ip route add 10.1.78.0/30 via 10.1.57.2  (G-H via G, 15+10=25ms)
```

### 5. Handling the A-H Cross-Link Subnet (10.2.18.0/30)
This was the most complex issue. The subnet has A (10.2.18.1) and H (10.2.18.2) — nodes in different clusters. I used /32 routes to split them:
- `10.2.18.2/32 via 10.1.58.2` (H, direct, 20ms)
- `10.2.18.1/32` — initially via D (optimal at 270ms), but D lacked a route for this subnet and kept sending ICMP redirects

After multiple failed attempts to get D to add `ip route add 10.2.18.0/30 via 10.0.14.1`, I fell back to routing 10.2.18.1 via H (E→H→A = 20+350 = 370ms one-way), which worked at 640ms RTT.

### 6. System Configuration
```
sysctl -w net.ipv4.ip_forward=1          (enable forwarding for transit traffic)
sysctl -w net.ipv4.conf.all.send_redirects=0    (prevent sending ICMP redirects)
sysctl -w net.ipv4.conf.all.accept_redirects=0  (ignore received redirects)
```
Applied to all interfaces individually as well.

## Coordination with Other Agents

- **All nodes:** Exchanged full topology information (links, IPs, delays) to enable global route computation
- **D:** Sent multiple urgent messages requesting it add a route for 10.2.18.0/30 via A and disable ICMP redirects. D never resolved this issue during the experiment.
- **A:** Coordinated on the 10.2.18.0/30 routing issue; A confirmed it had proper return routes configured
- **H:** Coordinated on redirect suppression and the 10.2.18.1 routing workaround; disabled redirects so H could transit through E to reach cluster 1
- **F, G:** Shared complete topology so they could configure optimal routes; they helped identify the D redirect problem

## Final Result

Full IP connectivity achieved to all 7 nodes across all their interfaces. All routes are latency-optimal except 10.2.18.1 (A's H-facing IP), which uses a suboptimal path via H (640ms RTT) instead of the optimal D path (540ms RTT) due to D's missing route configuration. All other routes use minimum-latency paths through the D-E bridge link for inter-cluster traffic.