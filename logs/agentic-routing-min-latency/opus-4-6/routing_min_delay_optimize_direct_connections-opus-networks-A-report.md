# Experiment Report: Node A Network Configuration

## Network Discovery

The network consists of 8 nodes (A-H) arranged in two clusters bridged by two high-latency links:

**Cluster 1 (low-latency mesh):** A, B, C, D
- A-B: 10ms one-way (20ms RTT)
- A-C: 15ms one-way (30ms RTT)
- A-D: 20ms one-way (40ms RTT)
- B-C: 10ms (20ms RTT)
- B-D: 15ms (30ms RTT)
- C-D: 10ms (20ms RTT)

**Cluster 2 (low-latency mesh):** E, F, G, H
- E-F: 10ms (20ms RTT)
- E-G: 15ms (30ms RTT)
- E-H: 20ms (40ms RTT)
- F-G: 10ms (20ms RTT)
- F-H: 15ms (30ms RTT)
- G-H: 10ms (20ms RTT)

**Bridge links:**
- D-E: 250ms one-way (500ms RTT)
- A-H: 350ms one-way (700ms RTT)

**14 subnets total**, each /30, with IPs fully catalogued through cooperative discovery.

## Actions Taken

### 1. Interface and Latency Discovery
Ran `ip addr show`, `ip link show`, `ip route show`, and `tc qdisc show` on all four interfaces to determine my connections (A-eth0→B, A-eth1→C, A-eth2→D, A-eth3→H) and their netem delay settings (10ms, 15ms, 20ms, 350ms respectively).

### 2. Direct Route Installation
Added connected subnet routes: `ip route add 10.0.12.0/30 dev A-eth0` (and similarly for eth1-eth3) to establish basic connectivity with direct neighbors.

### 3. Topology Collection via Messaging
Sent topology announcements to all 7 nodes requesting their interfaces, IPs, and link delays. Received responses from B, C, D, E, F, G, and H over several rounds. Key discovery was F's revelation of the F-G link (10ms, subnet 10.1.67.0/30) which was initially unknown.

### 4. Shortest Path Computation (Dijkstra)
Computed optimal paths from A using RTT as the cost metric:
- **B**: 20ms direct (vs 40ms via C→B or 50ms via D→B)
- **C**: 30ms direct (vs 40ms via B→C)
- **D**: 40ms direct (vs 50ms via B→D or C→D)
- **E**: 540ms via A→D→E (vs 720ms via A→H→E)
- **F**: 560ms via A→D→E→F
- **G**: 570ms via A→D→E→G
- **H**: 580ms via A→D→E→H (vs 700ms direct!)

### 5. Route Installation
Installed 11 non-directly-connected routes:
- `10.0.23.0/30 via 10.0.12.2` (B-C subnet via B — optimizes access to B's IP on that link)
- `10.0.24.0/30 via 10.0.12.2` (B-D subnet via B — optimizes access to B's IP)
- `10.0.34.0/30 via 10.0.13.2` (C-D subnet via C — optimizes access to C's IP)
- All 7 cluster-2 subnets via D at `10.0.14.2`: 10.1.56.0/30, 10.1.57.0/30, 10.1.58.0/30, 10.1.67.0/30, 10.1.68.0/30, 10.1.78.0/30, 10.2.45.0/30

### 6. Critical Optimization: Rerouting A-H Subnet
Replaced the direct route for 10.2.18.0/30 (A-H link) with `ip route replace 10.2.18.0/30 via 10.0.14.2`, saving 120ms RTT (580ms via D→E→H vs 700ms direct). This was a non-obvious optimization since the subnet is physically attached to A.

### 7. Fixing Reachability for 10.2.18.0/30
After rerouting the A-H subnet via D, node E reported it couldn't reach 10.2.18.1. The issue was that intermediate nodes (D, E, and others) lacked routes to 10.2.18.0/30. Sent targeted messages to D, E, B, C, F, G, and H instructing them to add routes for this subnet through appropriate next hops.

## Coordination with Other Agents

- **All nodes**: Sent initial topology announcements and received their link information.
- **C**: Provided a comprehensive computed topology summary including shortest path calculations.
- **F**: Revealed the previously unknown F-G link.
- **G**: Confirmed topology and needed B-C subnet information, which I provided.
- **D & E**: Instructed to add routes for 10.2.18.0/30 to fix reachability after my rerouting decision.
- **B**: Informed about missing F-G link.
- **H**: Advised to reroute 10.2.18.0/30 via E→D→A instead of direct for lower latency.
- Shared complete shortest-path recommendations with every node, tailored to their perspective.

## Verification

Successfully pinged all 28 IPs across all 14 subnets in the network, confirming full connectivity with latency-optimal routing.