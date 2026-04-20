# Experiment Report: Node F Network Configuration

## Network Discovery

The network consists of 8 nodes split into two clusters connected by two high-latency bridge links:
- **Cluster 1 (ABCD):** A-B 10ms, A-C 15ms, A-D 20ms, B-C 10ms, B-D 15ms, C-D 10ms
- **Cluster 2 (EFGH):** E-F 10ms, E-G 15ms, E-H 20ms, F-G 10ms, F-H 15ms, G-H 10ms
- **Bridge links:** D-E 250ms, A-H 350ms

Node F has three interfaces: F-eth0 (to E, 10ms), F-eth1 (to G, 10ms), F-eth2 (to H, 15ms). Latencies were confirmed via `tc qdisc show` on each interface.

## Actions Taken

### 1. Interface Discovery and Initial Route Setup
Ran `ip addr show`, `ip route show`, `ip link show`, and `tc qdisc show` on each interface. Found no pre-existing routes. Added connected subnet routes for all three interfaces (10.1.56.0/30, 10.1.67.0/30, 10.1.68.0/30).

### 2. Topology Collection via Messaging
Sent topology requests to all three direct neighbors (E, G, H). Received responses from all nodes including non-neighbors (A, B, C, D) who relayed messages through the network. Notably, several nodes (B, C, D) were initially unaware of the F-G direct link (10.1.67.0/30), listing F with only two interfaces. I corrected this with multiple nodes to ensure accurate global routing.

### 3. Route Configuration
Added routes for all 14 subnets in the network. Initial strategy:
- **EFGH cluster subnets:** Routed via the nearest direct neighbor
- **ABCD cluster subnets:** All routed via E (10.1.56.1) since E→D is the only viable bridge (250ms vs A-H at 350ms)
- **B-C subnet (10.0.23.0/30):** Added after learning about this link from A's topology message

### 4. Route Optimization with /32 Splits
Several /30 subnets span two different nodes, where each endpoint is optimally reached via a different next-hop. I split these into /32 host routes:

- **10.1.57.0/30 (E-G):** 10.1.57.1 (E) via F-eth0 (10ms), 10.1.57.2 (G) via F-eth1 (10ms) — saved 15ms vs routing G's IP through E
- **10.1.58.0/30 (E-H):** 10.1.58.1 (E) via F-eth0 (10ms), 10.1.58.2 (H) via F-eth2 (15ms) — saved 15ms vs routing H's IP through E
- **10.1.78.0/30 (G-H):** 10.1.78.1 (G) via F-eth1 (10ms), 10.1.78.2 (H) via F-eth2 (15ms) — saved 5ms vs routing H's IP through G
- **10.2.18.0/30 (A-H):** 10.2.18.2 (H) via F-eth2 (15ms), 10.2.18.1 (A) via F-eth2→H→A (365ms). Initially tried routing A's IP via E→D→A (280ms theoretical) but D had routing issues (ICMP redirects), and empirical testing showed 660ms RTT via E vs 645ms via H, so H was kept.

### 5. Verification
Ran comprehensive ping tests to all 25 IPs across all 8 nodes. All passed. RTTs confirmed optimal routing: E/G at 20ms, H at 30ms, D at 520ms, C at 540ms, B at 550ms, A at 560ms.

## Coordination with Other Agents
- Shared full topology with all nodes as information was gathered incrementally
- Corrected multiple nodes (B, C, D, G) about the existence of the F-G direct link
- Informed G about the B-C link they were missing
- Asked D and E to add proper routes for the 10.2.18.0/30 subnet to fix a redirect loop
- Received and incorporated topology data from all 7 other nodes

## Key Decision: Bridge Link Selection
All traffic to ABCD cluster routes via E→D (250ms) rather than H→A (350ms), saving 100ms per hop. The only exception is reaching A's 10.2.18.1 address, where the H→A path was empirically faster due to routing overhead through D.