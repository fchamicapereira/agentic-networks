# Experiment Report: Node B Network Configuration

## Network Discovery

The network consists of 8 nodes in two clusters connected by two cross-links:
- **Cluster 1 (ABCD):** Fully meshed with low-latency links (10-20ms one-way)
- **Cluster 2 (EFGH):** Fully meshed with low-latency links (10-20ms one-way)
- **Cross-links:** D-E (250ms) and A-H (350ms)

### Complete Topology (one-way delays):
| Link | Delay | Subnet |
|------|-------|--------|
| A-B | 10ms | 10.0.12.0/30 |
| A-C | 15ms | 10.0.13.0/30 |
| A-D | 20ms | 10.0.14.0/30 |
| A-H | 350ms | 10.2.18.0/30 |
| B-C | 10ms | 10.0.23.0/30 |
| B-D | 15ms | 10.0.24.0/30 |
| C-D | 10ms | 10.0.34.0/30 |
| D-E | 250ms | 10.2.45.0/30 |
| E-F | 10ms | 10.1.56.0/30 |
| E-G | 15ms | 10.1.57.0/30 |
| E-H | 20ms | 10.1.58.0/30 |
| F-G | 10ms | 10.1.67.0/30 |
| F-H | 15ms | 10.1.68.0/30 |
| G-H | 10ms | 10.1.78.0/30 |

## Actions Taken

### 1. Interface Discovery and Initial Setup
- Ran `ip addr show`, `ip link show`, `ip route show` to discover my three interfaces (B-eth0 to A, B-eth1 to C, B-eth2 to D).
- Ran `tc qdisc show` on each interface to discover local link delays: 10ms to A, 10ms to C, 15ms to D.
- Added connected routes for my three directly-attached subnets.

### 2. Topology Collection via Messaging
- Sent topology discovery messages to all three direct neighbors (A, C, D) sharing my link information and requesting theirs.
- Also received unsolicited messages from E, H, F, and G who were proactively sharing their topology.
- Iteratively collected and cross-verified topology data from all nodes until the full 14-link, 8-node topology was confirmed.

### 3. Shortest Path Computation
Computed minimum-latency paths from B to every node using Dijkstra-style reasoning:
- **A:** Direct via B-eth0 = 10ms (vs B→C→A = 25ms)
- **C:** Direct via B-eth1 = 10ms (vs B→A→C = 25ms)
- **D:** Direct via B-eth2 = 15ms (vs B→C→D = 20ms)
- **E:** B→D→E = 265ms (vs B→A→H→E = 380ms)
- **F:** B→D→E→F = 275ms
- **G:** B→D→E→G = 280ms
- **H:** B→D→E→H = 285ms (vs B→A→H = 360ms)

**Key decision:** All remote cluster traffic goes via D (B-eth2) since D-E at 250ms is much cheaper than A-H at 350ms.

### 4. Route Configuration
Configured 36 routes total:
- 3 connected subnet routes (automatic with IP assignment)
- /32 host routes for each IP on shared subnets where the two endpoints have different optimal next hops (e.g., 10.0.14.1 via A, 10.0.14.2 via D on the A-D subnet)
- /30 subnet routes for all 14 subnets
- All E/F/G/H cluster IPs routed via D at 10.0.24.2

### 5. Full Topology Broadcast
Sent the complete topology (all 14 links with delays and all IPs) to every node in the network, including routing recommendations tailored to each node's position. This helped nodes like A learn about F-H and G-H links they hadn't yet discovered, and ensured F-G (10ms, 10.1.67.0/30) was known everywhere.

### 6. Verification
- Pinged all 25 IPs across all 7 remote nodes — 100% success.
- Confirmed RTTs match expected values: A=20ms, C=20ms, D=30ms, E=530ms, F=550ms, G=565ms, H=575ms.

## Coordination with Other Agents

Coordination was essential since no routing protocol was pre-configured. I:
1. Proactively shared my link info with neighbors immediately.
2. Relayed topology information between clusters — I was a key conduit passing Cluster 2 info (from E, H, G, F) to Cluster 1 nodes (A, C, D) and vice versa.
3. Provided routing recommendations to each node based on the full topology.
4. Discovered the F-G link (10ms) through messages from H and G, which wasn't initially known to me.
5. Confirmed topology consistency — all 8 nodes eventually reported the same 14-link topology.