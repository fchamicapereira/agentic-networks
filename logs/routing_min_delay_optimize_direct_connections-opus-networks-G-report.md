# Experiment Report: Node G Network Configuration

## Network Discovery

The network consists of 8 nodes split into two clusters connected by two cross-links:
- **Cluster 1 (ABCD):** A-B (10ms), A-C (15ms), A-D (20ms), B-C (10ms), B-D (15ms), C-D (10ms)
- **Cluster 2 (EFGH):** E-F (10ms), E-G (15ms), E-H (20ms), F-G (10ms), F-H (15ms), G-H (10ms)
- **Cross-links:** D-E (250ms), A-H (350ms)

All delays are one-way (netem qdisc). The two clusters are tightly connected internally but linked only by two high-latency bridges.

## Actions Taken

### 1. Interface Discovery and Initial Setup
- Ran `ip addr show`, `ip route show`, `ip link show` to discover my three interfaces: G-eth0 (to E, 15ms), G-eth1 (to F, 10ms), G-eth2 (to H, 10ms).
- Checked `tc qdisc show` on each interface to read configured delays.
- Verified IP forwarding was enabled (`/proc/sys/net/ipv4/ip_forward` = 1).
- Added connected routes for my three subnets since no routes existed initially.

### 2. Topology Discovery via Messaging
- Sent topology info to all three direct neighbors (E, F, H) requesting their link information.
- Received responses revealing the full network gradually: E shared its links including D-E (250ms), H shared its links including A-H (350ms), D and A shared the ABCD cluster topology.
- A revealed the previously unknown B-C link (10ms, subnet 10.0.23.0/30).
- Forwarded updated topology to all neighbors to ensure everyone had complete information, especially the B-C link and F-G link which some nodes were missing.

### 3. Route Configuration

**ABCD cluster subnets (via E at 10.1.57.1):**
All six ABCD subnets (10.0.12.0/30, 10.0.13.0/30, 10.0.14.0/30, 10.0.23.0/30, 10.0.24.0/30, 10.0.34.0/30) routed via E. Justification: G→E (15ms) + E→D (250ms) = 265ms is the fastest path to reach the ABCD cluster. The alternative via H→A (350ms) is far worse.

**D-E subnet (10.2.45.0/30):** Via E (15ms direct).

**E-F subnet (10.1.56.0/30):** Subnet route via E (for E's IP 10.1.56.1, 15ms), with a /32 host route for F's IP (10.1.56.2) via F (10ms). This optimizes both endpoints: reaching E directly costs 15ms, while reaching F directly costs 10ms.

**E-H subnet (10.1.58.0/30):** Subnet route via H (for H's IP 10.1.58.2, 10ms), with a /32 host route for E's IP (10.1.58.1) via E (15ms). Direct to each node is faster than routing through intermediaries.

**F-H subnet (10.1.68.0/30):** Subnet route via F (for F's IP 10.1.68.1, 10ms), with a /32 host route for H's IP (10.1.68.2) via H (10ms). Same split-optimization logic.

**A-H subnet (10.2.18.0/30):** Via H (10.1.78.2). Initially I tried routing via E→D→A (285ms theoretical) but D consistently sent ICMP redirects for this subnet, indicating D lacked a proper route to A for 10.2.18.0/30. The H path works reliably at ~320ms one-way (10ms to H, then H forwards to A).

### 4. Optimization of Shared Subnets
The key optimization insight was that subnets shared between two nodes should use host routes (/32) for the farther endpoint and subnet routes for the nearer one. This was applied to three subnets (E-F, E-H, F-H) reducing RTTs by 10-15ms per endpoint.

## Coordination with Other Agents

- **E, F, H (direct neighbors):** Exchanged full topology information. Advised on optimal routing directions.
- **D:** Repeatedly requested it add a route for 10.2.18.0/30 via A (10.0.14.1). D never resolved this, forcing the suboptimal H path for A's side of that subnet.
- **A:** Shared full topology, confirmed B-C link existence. Asked A to relay routing fix to D.
- **B, C:** Shared full topology including the F-G link they were missing. Received confirmation of B-C subnet details (10.0.23.0/30).

## Final Result
Full connectivity achieved to all 25 remote IPs across 7 nodes. All local-cluster routes optimized to minimum latency. Cross-cluster routes use the D-E bridge (250ms) which is superior to A-H (350ms) for all ABCD destinations except the 10.2.18.0/30 subnet where D's missing route forced fallback to the H path.